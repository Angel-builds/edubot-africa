"""Tests for the tutor, its solver, and the guardrail that holds them apart.

test_answer_is_withheld_until_the_top_of_the_ladder is the one that matters.
Everything else here is ordinary correctness; that one is the product.
"""

from __future__ import annotations

import pytest

from core.solver import matches, solve
from core.tutor import LADDER, TOP_LEVEL, Tutor


@pytest.fixture(scope="module")
def tutor() -> Tutor:
    try:
        return Tutor()
    except FileNotFoundError:
        pytest.skip("corpus not generated; run python -m ingest.siyavula")


# --- solver -----------------------------------------------------------------

@pytest.mark.parametrize(
    ("question", "answer"),
    [
        ("3x + 5 = 20", "5"),
        ("solve 2x = 7", "7/2"),
        ("Solve: x/3 = 4", "12"),
        ("please help me find 5x - 2 = 13", "3"),
        ("what is 2/4 + 1/4", "3/4"),
        ("calculate 12*7", "84"),
    ],
)
def test_solver_works_the_answer_out(question, answer):
    solution = solve(question)
    assert solution is not None
    assert solution.answer == answer


def test_solver_survives_pidgin_and_code_switching():
    """Students write like this, and implicit multiplication turns prose into
    a product of every letter in the sentence unless it is trimmed first."""
    assert solve("chale i no fit do 2y + 6 = 14").answer == "4"
    assert solve("abeg wetin be 4a = 12").answer == "3"


def test_solver_returns_nothing_when_there_is_no_maths():
    assert solve("how do i do this") is None
    assert solve("good morning sir") is None


@pytest.mark.parametrize(
    ("student", "correct"),
    [("1/2", "0.5"), ("2/4", "0.5"), ("0.5", "1/2"), ("3", "3.0"), ("12/4", "3")],
)
def test_equivalent_answers_are_marked_correct(student, correct):
    """Marking 1/2 wrong because the key says 0.5 destroys trust immediately."""
    assert matches(student, correct)


def test_wrong_answers_are_still_wrong():
    assert not matches("4", "5")


# --- the ladder -------------------------------------------------------------

def test_wrong_answers_climb_the_ladder(tutor):
    level = 0
    for attempt in ["7", "6", "4", "9"]:
        turn = tutor.respond("3x + 5 = 20", level=level, student_answer=attempt)
        assert turn.student_was_correct is False
        assert turn.level > level or turn.level == TOP_LEVEL
        level = turn.level
    assert level == TOP_LEVEL


def test_a_correct_answer_resets_the_ladder(tutor):
    turn = tutor.respond("3x + 5 = 20", level=3, student_answer="5")
    assert turn.student_was_correct is True
    assert turn.level == 0


def test_asking_does_not_advance_the_ladder(tutor):
    """The student climbs by failing, never by requesting the answer."""
    turn = tutor.respond("just give me the answer to 3x + 5 = 20", level=0)
    assert turn.level == 0
    assert not turn.gave_answer


def test_answer_is_withheld_until_the_top_of_the_ladder(tutor):
    """The core guardrail: the worked answer must not reach the student early.

    The tutor model is never handed the answer at all -- only a boolean saying
    whether the student matched it -- so it cannot leak what it was never given.
    """
    answer = solve("3x + 5 = 20").answer
    assert answer == "5"

    level = 0
    for attempt in ["7", "6", "4"]:
        turn = tutor.respond("3x + 5 = 20", level=level, student_answer=attempt)
        level = turn.level
        assert not turn.gave_answer, f"reached the answer at level {level}"


def test_ladder_has_a_step_for_every_level():
    assert len(LADDER) == TOP_LEVEL + 1
    assert all(step.strip() for step in LADDER)


# --- grounding --------------------------------------------------------------

def test_replies_are_grounded_in_the_corpus(tutor):
    turn = tutor.respond("how do i add fractions")
    assert turn.sources
    assert all(s.attribution and s.url for s in turn.sources), "citations must survive"
