"""Assertions on the grounded content corpus and its indicator coverage.

The licence checks are the important ones. A non-commercial chunk entering the
corpus is not a bug you notice at runtime -- it is one you discover when someone
asks whether the project can ever charge for anything.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CHUNKS = Path("corpus/chunks.jsonl")
COVERAGE = Path("corpus/coverage.json")
GRAPH = Path("corpus/skill_graph.jsonl")

PERMITTED_LICENCES = {"CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-4.0"}
MIN_WORDS = 20


@pytest.fixture(scope="module")
def chunks() -> list[dict]:
    if not CHUNKS.exists():
        pytest.skip(f"{CHUNKS} not generated; run python -m ingest.siyavula")
    return [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines() if line]


@pytest.fixture(scope="module")
def coverage() -> dict:
    if not COVERAGE.exists():
        pytest.skip(f"{COVERAGE} not generated; run python -m ingest.map_indicators")
    return json.loads(COVERAGE.read_text(encoding="utf-8"))


def test_every_chunk_is_permissively_licensed(chunks):
    """No non-commercial material may enter the corpus."""
    bad = {c["licence"] for c in chunks} - PERMITTED_LICENCES
    assert bad == set()


def test_every_chunk_carries_attribution(chunks):
    """CC BY compliance is not optional."""
    for c in chunks:
        assert c["attribution"].strip()
        assert "CC BY" in c["attribution"]
        assert c["url"].startswith("https://")
        assert c["retrieved"]


def test_chunk_ids_are_unique(chunks):
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_chunks_are_substantial(chunks):
    assert all(c["word_count"] >= MIN_WORDS for c in chunks)


def test_chunks_carry_heading_path(chunks):
    """Heading paths make citations precise, which is a phase-5 eval metric."""
    assert all(c["heading_path"] for c in chunks)


def test_no_site_chrome_leaked(chunks):
    noise = ("Home Practice", "We use this information", "Toggle navigation", "Sign up")
    leaked = [c["id"] for c in chunks if any(n in c["text"] for n in noise)]
    assert leaked == []


def test_subject_present_on_every_chunk(chunks):
    assert {c["subject"] for c in chunks} == {"mathematics"}


def test_grades_align_with_jhs(chunks):
    """Siyavula grades 7-9 are the reason this source was chosen over a US one."""
    assert sorted({c["grade"] for c in chunks}) == [7, 8, 9]


def test_coverage_accounts_for_every_indicator(coverage):
    nodes = [json.loads(line) for line in GRAPH.read_text(encoding="utf-8").splitlines() if line]
    indicators = {n["code"] for n in nodes if n["level"] == "indicator"}
    assert set(coverage["indicators"]) == indicators
    assert coverage["indicators_total"] == len(indicators)
    assert coverage["indicators_covered"] + coverage["indicators_uncovered"] == len(indicators)


def test_coverage_records_its_method(coverage):
    """The mapping is lexical, and the file must say so rather than imply more."""
    assert "lexical" in coverage["method"].lower()
    assert "review" in coverage["method"].lower()


def test_uncovered_list_matches_the_per_indicator_flags(coverage):
    flagged = {c for c, v in coverage["indicators"].items() if not v["covered"]}
    assert flagged == set(coverage["uncovered"])


def test_mapped_chunks_reference_real_indicators(chunks, coverage):
    known = set(coverage["indicators"])
    for c in chunks:
        assert set(c["indicators"]) <= known
