"""Talk to the tutor from a terminal.

    uv run python -m core.cli
    uv run python -m core.cli "3x + 5 = 20"

Type an answer to climb the hint ladder. Type 'quit' to leave.
"""

from __future__ import annotations

import sys

from core import llm
from core.tutor import Tutor


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    tutor = Tutor()

    print("EduBot - JHS maths tutor.  Ctrl-C or 'quit' to leave.")
    if not llm.available():
        print("No ANTHROPIC_API_KEY set: replies show the coaching step instead of prose.")
    print()

    question = " ".join(argv) if argv else input("question> ").strip()
    if not question:
        return 0

    level = 0
    turn = tutor.respond(question, level=level)
    print(f"\n{turn.reply}\n")

    while True:
        try:
            reply = input("your answer> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not reply or reply.lower() in {"quit", "exit"}:
            return 0

        turn = tutor.respond(question, level=turn.level, student_answer=reply)
        print(f"\n{turn.reply}\n")
        if turn.student_was_correct:
            question = input("next question> ").strip()
            if not question or question.lower() in {"quit", "exit"}:
                return 0
            turn = tutor.respond(question)
            print(f"\n{turn.reply}\n")


if __name__ == "__main__":
    raise SystemExit(main())
