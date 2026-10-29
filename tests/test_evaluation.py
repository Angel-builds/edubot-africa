"""Two jobs: check the metrics are arithmetically right, and stop retrieval
quality sliding without anyone noticing.

The gates are set just under what the Retriever scores today. They are a
ratchet against regression, not a target -- the numbers themselves are
discussed in PRD decision 18.
"""

import json
from functools import lru_cache
from math import log2
from pathlib import Path

import pytest

from evaluation.metrics import (
    ceiling_at_k,
    hit_at_k,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)
from evaluation.report import DEFAULT_K, load_pairs, run, summarise

# --------------------------------------------------------------- the metrics

RETRIEVED = ["a", "b", "c", "d"]
RELEVANT = {"c": 2, "e": 1}


def test_hit_sees_a_relevant_chunk_inside_the_window():
    assert hit_at_k(RETRIEVED, RELEVANT, 3) == 1.0


def test_hit_ignores_a_relevant_chunk_outside_the_window():
    """'c' sits at rank 3, so at k=2 the student never saw it."""
    assert hit_at_k(RETRIEVED, RELEVANT, 2) == 0.0


def test_recall_is_the_share_of_relevant_chunks_found():
    assert recall_at_k(RETRIEVED, RELEVANT, 3) == 0.5


def test_recall_refuses_to_answer_when_nothing_is_relevant():
    with pytest.raises(ValueError):
        recall_at_k(RETRIEVED, {}, 3)


def test_reciprocal_rank_counts_from_one():
    assert reciprocal_rank(RETRIEVED, RELEVANT) == pytest.approx(1 / 3)


def test_reciprocal_rank_is_zero_when_nothing_relevant_was_returned():
    assert reciprocal_rank(["x", "y"], RELEVANT) == 0.0


def test_ndcg_against_a_hand_worked_value():
    # Returned grades are [0, 0, 2], so DCG = (2**2 - 1) / log2(3 + 1) = 1.5.
    # The ideal ordering is [2, 1], so IDCG = 3 / log2(2) + 1 / log2(3).
    ideal = 3 / log2(2) + 1 / log2(3)
    assert ndcg_at_k(RETRIEVED, RELEVANT, 3) == pytest.approx(1.5 / ideal)


def test_ndcg_is_one_for_the_ideal_ordering():
    assert ndcg_at_k(["x", "y"], {"x": 2, "y": 1}, 2) == pytest.approx(1.0)


def test_ndcg_rewards_putting_the_teaching_chunk_first():
    relevant = {"x": 2, "y": 1}
    assert ndcg_at_k(["x", "y"], relevant, 2) > ndcg_at_k(["y", "x"], relevant, 2)


def test_ceiling_shows_when_k_makes_full_recall_impossible():
    assert ceiling_at_k({"a": 2, "b": 1, "c": 1, "d": 1}, 3) == 0.75
    assert ceiling_at_k({"a": 2}, 3) == 1.0


# ------------------------------------------------------------ the golden set


def test_every_golden_pair_names_chunks_that_exist():
    """A Golden Pair pointing at a Chunk id that is gone measures nothing."""
    known = {
        json.loads(line)["id"]
        for line in Path("corpus/chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    }
    for pair in load_pairs():
        unknown = set(pair["relevant"]) - known
        assert not unknown, f"{pair['id']} names missing chunks: {unknown}"


def test_golden_pair_ids_are_unique():
    ids = [p["id"] for p in load_pairs()]
    assert len(ids) == len(set(ids))


def test_relevance_grades_are_one_or_two():
    for pair in load_pairs():
        assert all(g in (1, 2) for g in pair["relevant"].values()), pair["id"]


def test_the_golden_set_covers_every_strand_and_class():
    pairs = load_pairs()
    assert {p["strand"] for p in pairs} == {
        "Number",
        "Algebra",
        "Geometry and Measurement",
        "Handling Data",
    }
    assert {p["class"] for p in pairs} == {"B7", "B8", "B9"}


def test_the_golden_set_includes_questions_with_no_answer():
    """Without these, nothing measures the tutor citing sources that do not fit."""
    assert sum(1 for p in load_pairs() if not p["relevant"]) >= 5


# ------------------------------------------------------------- the ratchet


@lru_cache
def _scored():
    """The corpus is parsed and vectorised once for the whole module."""
    return tuple(run(DEFAULT_K))


@lru_cache
def _overall():
    return summarise(list(_scored()), DEFAULT_K)


def test_hit_at_three_does_not_regress():
    assert _overall()[f"hit@{DEFAULT_K}"] >= 0.70


def test_mrr_does_not_regress():
    assert _overall()["mrr"] >= 0.62


def test_ndcg_does_not_regress():
    assert _overall()[f"ndcg@{DEFAULT_K}"] >= 0.48


def test_no_strand_collapses():
    """Algebra is the weakest at about 0.43. This catches it getting worse."""
    from evaluation.report import _grouped

    by_strand = _grouped(list(_scored()), "strand", DEFAULT_K)
    for strand, metrics in by_strand.items():
        assert metrics[f"hit@{DEFAULT_K}"] >= 0.40, strand
