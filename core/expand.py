"""Supply the topic words a bare equation does not contain.

"3x + 5 = 20" is a perfectly clear question and contains not one searchable
word. Scoring it against the corpus returns nothing, so the reply comes back
ungrounded even though the corpus has a chapter on exactly this.

The shape of the maths tells us what it is about. An equals sign with a letter
on one side means solving for an unknown; a slash between digits means
fractions. So we read those features and add the words the student did not need
to write.

This is query expansion, and it is deliberately conservative: it only fires when
the question has almost no words of its own, so ordinary questions like "how do
i add fractions" score exactly as they did before.

Every term emitted here was checked to exist in the corpus. A term the corpus
has never seen contributes nothing, and silently achieving nothing is worse than
not trying.
"""

from __future__ import annotations

import re

# Below this many indexable words, the question cannot retrieve on its own.
MIN_OWN_TOKENS = 2

VARIABLE = re.compile(r"(?<![a-zA-Z])[a-zA-Z](?![a-zA-Z])")
FRACTION = re.compile(r"\d\s*/\s*\d")
DECIMAL = re.compile(r"\d\.\d")
POWER = re.compile(r"\^|\*\*")
PERCENT = re.compile(r"%|\bpercent\b", re.IGNORECASE)
TIMES = re.compile(r"\d\s*[*x×]\s*\d", re.IGNORECASE)
NEGATIVE = re.compile(r"(^|[\s(])-\s*\d")


def maths_terms(text: str) -> list[str]:
    """Topic words implied by the structure of the expression."""
    terms: list[str] = []

    has_equals = "=" in text
    has_variable = bool(VARIABLE.search(re.sub(r"\b(x)\b(?=\s*\d)", " ", text)))

    if has_equals and has_variable:
        terms += ["equation", "solve", "variable", "unknown", "algebra"]
    elif has_equals:
        terms += ["equation", "solve"]
    elif has_variable:
        terms += ["expression", "variable", "algebra", "term"]

    if FRACTION.search(text):
        terms += ["fraction", "numerator", "denominator"]
    if DECIMAL.search(text):
        terms += ["decimal"]
    if POWER.search(text):
        terms += ["exponent", "power"]
    if PERCENT.search(text):
        terms += ["percentage"]
    if NEGATIVE.search(text):
        terms += ["negative", "integer"]

    if "+" in text:
        terms += ["addition"]
    if re.search(r"\d\s*-\s*\d", text):
        terms += ["subtraction"]
    if TIMES.search(text):
        terms += ["multiplication", "multiply"]
    if "/" in text and not FRACTION.search(text):
        terms += ["division", "divide"]

    return terms
