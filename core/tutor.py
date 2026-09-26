"""The tutor: a hint ladder over retrieved curriculum content.

The shape of a turn:

    question ──► solver (private)  ─── answer, never passed on ───┐
             └─► retriever ──► curriculum passages ──┐            │
                                                     ▼            ▼
                        level + passages + "was the student right?"
                                                     │
                                                     ▼
                                             llm phrases a hint

The student climbs the ladder by *failing*, never by asking. Level 5 is a full
worked solution, so the capability is there -- it just is not the opening move.
That ordering is the whole design: unguarded answer-giving improves in-session
performance and leaves students worse on their own (Bastani et al., PNAS 2025).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core import llm
from core.retrieve import Result, Retriever
from core.solver import Solution, matches, solve

LADDER = [
    "Ask what the student has tried so far. Do not explain anything yet.",
    "Name the idea the question is about, and ask a question that checks they understand it.",
    "Point to the method or formula that applies, without applying it.",
    "Work through the first step only, and leave the next step for the student.",
    "Work through the whole solution step by step, then give a similar practice question.",
]

TOP_LEVEL = len(LADDER) - 1

SYSTEM = """You are EduBot, a maths tutor for Ghanaian Junior High School
students (B7-B9, ages 12-15).

Rules you must follow:
- Follow the COACHING STEP exactly. Never jump ahead of it.
- Never state the final answer unless the coaching step tells you to.
- Use Ghanaian conventions: GH¢ and pesewas, British spelling (colour, metre,
  practise, maths), BODMAS, metric units, standard form.
- The student may write in Pidgin or mix in Twi. Understand it, answer in clear
  simple English, and never correct how they write.
- Two or three short sentences. Warm, never condescending.
- Ground what you say in the CURRICULUM EXTRACT when it is relevant."""


@dataclass
class Turn:
    """What the tutor says back, plus the state the caller needs to keep."""

    reply: str
    level: int
    sources: list[Result] = field(default_factory=list)
    student_was_correct: bool | None = None

    @property
    def gave_answer(self) -> bool:
        return self.level >= TOP_LEVEL


class Tutor:
    def __init__(self, retriever: Retriever | None = None) -> None:
        self.retriever = retriever or Retriever()

    def respond(
        self,
        question: str,
        level: int = 0,
        student_answer: str | None = None,
    ) -> Turn:
        """One turn. `level` is the caller's memory of how far the student has climbed."""
        worked = solve(question)
        sources = self.retriever.search(question, k=2)

        correct = None
        if student_answer and worked:
            correct = matches(student_answer, worked.answer)
            # Getting it right ends the ladder; getting it wrong advances it.
            level = 0 if correct else min(level + 1, TOP_LEVEL)

        reply = self._phrase(question, level, sources, correct)
        return Turn(reply=reply, level=level, sources=sources, student_was_correct=correct)

    def _phrase(
        self,
        question: str,
        level: int,
        sources: list[Result],
        correct: bool | None,
    ) -> str:
        """Build the prompt and hand it to the model.

        Note what is NOT in the prompt: the worked answer. The model is told
        only whether the student was right, so it cannot leak a solution it was
        never given.
        """
        passages = "\n\n".join(f"{s.cite()}\n{s.text}" for s in sources)
        extract = passages or "(nothing relevant found)"
        verdict = {
            True: "The student's answer was CORRECT. Confirm it and offer a harder one.",
            False: "The student's answer was WRONG. Do not say what the right answer is.",
            None: "The student has not attempted an answer yet.",
        }[correct]

        user = (
            f"STUDENT SAID:\n{question}\n\n"
            f"COACHING STEP (step {level + 1} of {len(LADDER)}):\n{LADDER[level]}\n\n"
            f"ATTEMPT SO FAR:\n{verdict}\n\n"
            f"CURRICULUM EXTRACT:\n{extract}"
        )

        if not llm.available():
            return _without_a_model(level, sources, correct)
        return llm.say(SYSTEM, user)


def _without_a_model(level: int, sources: list[Result], correct: bool | None) -> str:
    """Runs with no API key, so the mechanism is visible before you spend anything."""
    lines = ["[no ANTHROPIC_API_KEY set - showing the coaching step itself]", ""]
    if correct is True:
        lines.append("That is correct.")
    elif correct is False:
        lines.append("That is not right yet - let us look again.")
    lines.append(f"Step {level + 1} of {len(LADDER)}: {LADDER[level]}")
    if sources:
        lines += ["", "Grounded in:"] + [f"  {s.cite()}  (score {s.score})" for s in sources]
    return "\n".join(lines)


def explain_answer(question: str) -> Solution | None:
    """The private side of the line, exposed only for tests and marking."""
    return solve(question)
