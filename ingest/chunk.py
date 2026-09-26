"""Heading-aware semantic chunking.

Splits on the document's own structure rather than on a fixed character count.
A worked example cut in half retrieves well and teaches badly, so paragraphs are
only ever grouped, never split, and a chunk closes when the heading changes or
the word budget is reached -- whichever comes first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ~200-500 tokens at roughly 1.3 tokens per word.
TARGET_WORDS = 300
MAX_WORDS = 400
MIN_WORDS = 30

# A heading change only ends a chunk once the chunk is worth keeping. Siyavula's
# Grade 8 pages carry very fine-grained sub-headings, and flushing on every one
# produced 25-word fragments that retrieve poorly and teach nothing.
MIN_WORDS_BEFORE_HEADING_BREAK = 120


@dataclass
class Passage:
    """One paragraph, with the heading path in force where it appeared."""

    heading_path: tuple[str, ...]
    text: str

    @property
    def words(self) -> int:
        return len(self.text.split())


@dataclass
class Chunked:
    heading_path: list[str]
    text: str
    word_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.word_count = len(self.text.split())


def group(passages: list[Passage]) -> list[Chunked]:
    """Group consecutive passages into chunks that share a heading path."""
    chunks: list[Chunked] = []
    buffer: list[Passage] = []

    def flush() -> None:
        if not buffer:
            return
        text = " ".join(p.text for p in buffer)
        if len(text.split()) >= MIN_WORDS:
            chunks.append(Chunked(heading_path=list(buffer[0].heading_path), text=text))
        buffer.clear()

    for passage in passages:
        if passage.words > MAX_WORDS:
            # A single oversized paragraph stands alone rather than being cut.
            flush()
            if passage.words >= MIN_WORDS:
                chunks.append(
                    Chunked(heading_path=list(passage.heading_path), text=passage.text)
                )
            continue

        pending = sum(p.words for p in buffer)
        changed = buffer and buffer[0].heading_path != passage.heading_path
        if changed and pending >= MIN_WORDS_BEFORE_HEADING_BREAK:
            flush()
        elif pending + passage.words > TARGET_WORDS:
            flush()
        buffer.append(passage)

    flush()
    return chunks
