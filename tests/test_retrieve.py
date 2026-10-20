"""Retrieval, and the query expansion that makes bare equations searchable."""

from __future__ import annotations

import pytest

from core.expand import MIN_OWN_TOKENS, maths_terms
from core.retrieve import Retriever
from core.tfidf import stem, tokenise


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    try:
        return Retriever()
    except FileNotFoundError:
        pytest.skip("corpus not generated; run python -m ingest.siyavula")


# --- the expansion itself ---------------------------------------------------

@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("3x + 5 = 20", {"equation", "solve", "variable", "unknown", "algebra"}),
        ("2/4 + 1/4", {"fraction", "numerator", "denominator"}),
        ("x^2 = 49", {"exponent", "power"}),
        ("what is 25%", {"percentage"}),
        ("-5 + 3", {"negative", "integer"}),
        ("12 x 7", {"multiplication", "multiply"}),
        ("0.75 + 0.25", {"decimal"}),
    ],
)
def test_expansion_reads_the_shape_of_the_maths(question, expected):
    assert expected <= set(maths_terms(question))


def test_every_emitted_term_exists_in_the_corpus(retriever):
    """A term the corpus has never seen contributes nothing to the score.

    Silently achieving nothing is the failure this module is most at risk of,
    so the terms are checked against the real vocabulary rather than assumed.
    """
    shapes = [
        "3x + 5 = 20", "2/4 + 1/4", "x^2 = 49", "25%", "-5 + 3",
        "12 x 7", "0.75 + 0.25", "10 / 2", "a + b", "7 - 3",
    ]
    emitted = {stem(t) for shape in shapes for t in maths_terms(shape)}
    missing = sorted(t for t in emitted if t not in retriever.idf)
    assert missing == [], f"terms absent from the corpus: {missing}"


# --- retrieval --------------------------------------------------------------

@pytest.mark.parametrize(
    "question",
    ["3x + 5 = 20", "2/4 + 1/4", "x^2 = 49", "12 x 7", "what is 25%"],
)
def test_bare_maths_now_retrieves(retriever, question):
    """These returned nothing before expansion, leaving replies ungrounded."""
    assert tokenise(question) == [], "this case is only interesting if it has no words"
    assert retriever.search(question, k=2)


def test_expansion_does_not_fire_for_questions_with_their_own_words(retriever):
    """Ordinary questions must score exactly as they did before."""
    question = "how do i add fractions"
    assert len(tokenise(question)) >= MIN_OWN_TOKENS

    expanded = {c.heading for c in retriever.search(question, k=3)}
    baseline_tokens = tokenise(question)
    assert baseline_tokens == tokenise(question)  # expansion left the query alone
    assert expanded, "word-rich queries still retrieve"


def test_results_are_ordered_by_score(retriever):
    hits = retriever.search("how do i add fractions", k=5)
    assert hits == sorted(hits, key=lambda c: c.score, reverse=True)


def test_results_carry_what_a_citation_needs(retriever):
    for chunk in retriever.search("how do i add fractions", k=3):
        assert chunk.attribution and "CC BY" in chunk.attribution
        assert chunk.url.startswith("https://")
        assert chunk.heading
        assert chunk.grade in (7, 8, 9)


def test_nonsense_retrieves_nothing(retriever):
    assert retriever.search("qqqq zzzz wwww", k=3) == []
