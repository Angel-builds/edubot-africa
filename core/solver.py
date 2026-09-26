"""Work out the answer with SymPy, never with the language model.

Two reasons this is a separate module rather than something the model does:

1. Models make arithmetic slips. A tutor that confidently teaches wrong maths to
   a 13-year-old is worse than no tutor.
2. The tutor prompt never receives the answer -- only whether the student's
   attempt matched it. Withholding solutions by prompting alone does not survive
   a determined teenager across several turns; withholding them structurally does.

So this runs on the private side of that line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    standard_transformations,
)

TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,  # lets "3x" mean 3*x
    convert_xor,                          # lets "x^2" mean x**2
)

# Students write "solve 2x = 7", and without stripping the verb the left-hand
# side parses as a variable called `solve` multiplied by 2x.
LEAD_IN = re.compile(
    r"^\s*(please\s+)?(can you\s+)?(help me\s+)?"
    r"(solve|evaluate|calculate|work out|workout|find|simplify|what is|whats|what's)\b[:\s]*",
    re.IGNORECASE,
)

# A word of two or more letters is prose, not a variable. JHS variables are
# single letters, and implicit multiplication would otherwise turn
# "chale i no fit do 2y + 6 = 14" into a product of every letter in the sentence.
PROSE = re.compile(r"[a-zA-Z]{2,}")

# The first equation or arithmetic expression in a sentence of student text.
EQUATION = re.compile(r"[-+0-9a-zA-Z^*/(). ]*=[-+0-9a-zA-Z^*/(). ]*")
ARITHMETIC = re.compile(r"[-+0-9^*/(). ]{3,}")


@dataclass
class Solution:
    """What the solver worked out. Never shown to the tutor model."""

    kind: str          # "equation" or "arithmetic"
    question: str
    answer: str

    def __str__(self) -> str:
        return self.answer


def _maths_only(side: str) -> str:
    """Drop any prose preceding the expression, keeping what follows the last word."""
    last = None
    for match in PROSE.finditer(side):
        last = match
    return side[last.end():] if last else side


def _parse(text: str):
    return sympy.parse_expr(text.strip(), transformations=TRANSFORMS, evaluate=True)


def solve(text: str) -> Solution | None:
    """Solve the first equation or evaluate the first expression found in `text`."""
    text = LEAD_IN.sub("", text)
    equation = EQUATION.search(text)
    if equation and "=" in equation.group(0):
        left, _, right = equation.group(0).partition("=")
        left = _maths_only(left)
        if not left.strip():
            return None
        try:
            roots = sympy.solve(sympy.Eq(_parse(left), _parse(right)))
        except (sympy.SympifyError, SyntaxError, TypeError, ValueError):
            return None
        if roots:
            answer = ", ".join(str(r) for r in roots)
            return Solution("equation", equation.group(0).strip(), answer)
        return None

    expression = ARITHMETIC.search(text)
    if expression and any(op in expression.group(0) for op in "+-*/^"):
        try:
            value = _parse(expression.group(0))
        except (sympy.SympifyError, SyntaxError, TypeError, ValueError):
            return None
        if value.free_symbols:
            return None
        return Solution("arithmetic", expression.group(0).strip(), str(sympy.nsimplify(value)))

    return None


def matches(student_answer: str, correct: str) -> bool:
    """Compare by symbolic equivalence, not string equality.

    Without this, 1/2, 0.5 and 2/4 are all marked wrong and the student stops
    trusting the tutor within about two questions.
    """
    try:
        difference = sympy.simplify(_parse(student_answer) - _parse(correct))
    except (sympy.SympifyError, SyntaxError, TypeError, ValueError):
        return student_answer.strip() == correct.strip()
    return difference == 0
