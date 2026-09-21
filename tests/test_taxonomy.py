"""Structural assertions on the committed skill graph.

These run in CI, where the source PDF is deliberately absent -- it is
all-rights-reserved and gitignored. The graph itself holds only codes, short
titles and structure, so it is safe to commit and is what CI validates.

Counts here were measured against the document, not taken from secondary
sources. An earlier plan asserted 54 standards split 19/18/17; the document
actually contains 57 split 21/18/18, and every extra was confirmed by hand to
carry real curriculum text.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

GRAPH = Path("corpus/skill_graph.jsonl")
REJECTS = Path("corpus/rejects.jsonl")

CANONICAL = re.compile(r"^B[789](\.\d+){3,4}$")

EXPECTED_STANDARDS = {"B7": 21, "B8": 18, "B9": 18}
EXPECTED_INDICATORS = 178
MAX_TITLE_CHARS = 300


@pytest.fixture(scope="module")
def nodes() -> list[dict]:
    if not GRAPH.exists():
        pytest.skip(f"{GRAPH} not generated; run python -m ingest.nacca_taxonomy")
    return [json.loads(line) for line in GRAPH.read_text(encoding="utf-8").splitlines() if line]


@pytest.fixture(scope="module")
def standards(nodes) -> list[dict]:
    return [n for n in nodes if n["level"] == "standard"]


@pytest.fixture(scope="module")
def indicators(nodes) -> list[dict]:
    return [n for n in nodes if n["level"] == "indicator"]


def test_standard_counts_per_class(standards):
    counts = Counter(n["class"] for n in standards)
    assert dict(counts) == EXPECTED_STANDARDS
    assert len(standards) == sum(EXPECTED_STANDARDS.values()) == 57


def test_indicator_count(indicators):
    assert len(indicators) == EXPECTED_INDICATORS


def test_every_code_is_canonical(nodes):
    bad = [n["code"] for n in nodes if not CANONICAL.match(n["code"])]
    assert bad == []


def test_no_orphan_indicators(standards, indicators):
    known = {n["code"] for n in standards}
    orphans = [n["code"] for n in indicators if n["parent"] not in known]
    assert orphans == []


def test_indicator_code_agrees_with_its_parent(indicators):
    mismatched = [
        n["code"] for n in indicators if not n["code"].startswith(n["parent"] + ".")
    ]
    assert mismatched == []


def test_four_strands_present(nodes):
    assert sorted({n["strand"]["number"] for n in nodes}) == [1, 2, 3, 4]
    assert all(n["strand"]["title"] for n in nodes)


def test_every_node_has_a_sub_strand_title(nodes):
    missing = [n["code"] for n in nodes if not n["sub_strand"]["title"]]
    assert missing == []


def test_twelve_distinct_sub_strands(nodes):
    pairs = {(n["strand"]["number"], n["sub_strand"]["number"]) for n in nodes}
    assert len(pairs) == 12


def test_strand_and_substrand_agree_with_code(nodes):
    for n in nodes:
        parts = n["code"].split(".")
        assert n["strand"]["number"] == int(parts[1]), n["code"]
        assert n["sub_strand"]["number"] == int(parts[2]), n["code"]


def test_subject_present_on_every_node(nodes):
    """Guards the ability to add Science without a schema migration."""
    assert {n["subject"] for n in nodes} == {"mathematics"}


def test_titles_are_short_and_non_empty(nodes):
    assert all(n["title"].strip() for n in nodes)
    assert max(len(n["title"]) for n in nodes) <= MAX_TITLE_CHARS


def test_no_exemplar_prose_leaked_into_titles(nodes):
    """The legal boundary, asserted in code rather than trusted to discipline."""
    leaked = [n["code"] for n in nodes if re.search(r"E\.?\s?g\.?\s?\d", n["title"], re.I)]
    assert leaked == []


def test_every_node_carries_provenance(nodes):
    for n in nodes:
        assert n["source"]["document"] == "MATHEMATICS-CCP-B7-B9"
        assert n["source"]["page"] > 0
        assert n["source"]["retrieved"]


def test_rejects_are_recorded_not_dropped():
    """Nothing the extractor could not trust may vanish silently."""
    if not REJECTS.exists():
        pytest.skip("rejects file not generated")
    rejects = [json.loads(line) for line in REJECTS.read_text().splitlines() if line]
    assert len(rejects) <= 3, "reject count grew; investigate before raising this bound"
    for r in rejects:
        assert r["reason"] and r["raw"] and r["page"] > 0

    # The one known reject is a typo in the source document: page 201 prints
    # indicator B9.1.2.3.4 under standard B9.1.2.4, and no B9.1.2.3 exists.
    typo = [r for r in rejects if r["raw"] == "B9.1.2.3.4"]
    assert len(typo) == 1
    assert typo[0]["repaired_to"] == "B9.1.2.4.4"
