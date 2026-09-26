"""TF-IDF vector search, hand-rolled.

Small enough to read in one sitting, which is the point: this is the piece that
decides which curriculum passage the tutor sees, so it should not be a black box.

It is also what `ingest/map_indicators.py` uses, so retrieval and mapping score
text the same way.
"""

from __future__ import annotations

import math
import re
from collections import Counter

Vector = dict[str, float]

TOKEN = re.compile(r"[a-z]{3,}")

STOPWORDS = {
    "and", "the", "for", "with", "that", "this", "are", "you", "can", "will",
    "from", "each", "have", "has", "was", "were", "its", "into", "than", "then",
    "any", "all", "how", "who", "use", "used", "using", "given", "give", "make",
    "out", "our", "their", "them", "they", "there", "these", "those", "such",
    "also", "when", "what", "which", "where", "some", "more", "most", "other",
    "example", "following", "below", "above", "learner", "learners",
}


def stem(word: str) -> str:
    """Crude suffix stripping, enough to align 'fraction' with 'fractions'."""
    for suffix in ("ising", "izing", "ies", "ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokenise(text: str) -> list[str]:
    return [stem(t) for t in TOKEN.findall(text.lower()) if t not in STOPWORDS]


def fit(documents: list[list[str]]) -> tuple[list[Vector], dict[str, float]]:
    """Build L2-normalised TF-IDF vectors, and return the IDF table with them.

    The IDF table is needed later to put a query into the same space.
    """
    total = len(documents)
    appearances: Counter[str] = Counter()
    for tokens in documents:
        appearances.update(set(tokens))
    idf = {term: math.log((total + 1) / (n + 1)) + 1.0 for term, n in appearances.items()}
    return [_vector(tokens, idf) for tokens in documents], idf


def project(tokens: list[str], idf: dict[str, float]) -> Vector:
    """Put a query into an already-fitted space, ignoring unseen terms."""
    return _vector([t for t in tokens if t in idf], idf)


def _vector(tokens: list[str], idf: dict[str, float]) -> Vector:
    counts = Counter(tokens)
    weights = {t: (1 + math.log(c)) * idf.get(t, 0.0) for t, c in counts.items()}
    norm = math.sqrt(sum(w * w for w in weights.values())) or 1.0
    return {t: w / norm for t, w in weights.items()}


def cosine(a: Vector, b: Vector) -> float:
    """Both vectors are unit length, so the dot product is the cosine."""
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())
