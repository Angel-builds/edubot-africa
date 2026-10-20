"""Find the curriculum passages most relevant to a student's question.

Phase 2 replaces this with Supabase + pgvector + hybrid search. Until then it
loads the corpus into memory and scores with TF-IDF: 708 chunks is small enough
that this is instant, and it needs no database, no API key and no network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from core.expand import MIN_OWN_TOKENS, maths_terms
from core.tfidf import cosine, fit, project, tokenise

CHUNKS = Path("corpus/chunks.jsonl")


@dataclass
class RetrievedChunk:
    """A Chunk that matched a question, with everything needed to cite it."""

    text: str
    heading: str
    grade: int
    url: str
    attribution: str
    indicators: list[str]
    score: float

    def cite(self) -> str:
        return f"[Grade {self.grade}: {self.heading}]"


class Retriever:
    """Loads the corpus once, then answers queries against it."""

    def __init__(self, path: Path = CHUNKS) -> None:
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is missing. Run: python -m ingest.siyavula"
            )
        self.chunks = [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line
        ]
        # Headings carry real signal ("Adding fractions"), so they are indexed
        # alongside the body text rather than kept only for display.
        documents = [
            tokenise(" ".join(c["heading_path"]) + " " + c["text"]) for c in self.chunks
        ]
        self.vectors, self.idf = fit(documents)

    def search(self, question: str, k: int = 3) -> list[RetrievedChunk]:
        tokens = tokenise(question)
        if len(tokens) < MIN_OWN_TOKENS:
            # A bare equation has no words of its own; read them off its shape.
            tokens += tokenise(" ".join(maths_terms(question)))
        query = project(tokens, self.idf)
        scored = sorted(
            ((cosine(query, vec), i) for i, vec in enumerate(self.vectors)),
            reverse=True,
        )[:k]
        return [self._retrieved(i, score) for score, i in scored if score > 0]

    def _retrieved(self, index: int, score: float) -> RetrievedChunk:
        chunk = self.chunks[index]
        return RetrievedChunk(
            text=chunk["text"],
            heading=" > ".join(chunk["heading_path"][-2:]),
            grade=chunk["grade"],
            url=chunk["url"],
            attribution=chunk["attribution"],
            indicators=chunk["indicators"],
            score=round(score, 4),
        )
