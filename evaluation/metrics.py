"""Retrieval metrics, written out by hand.

Four numbers, because they answer different questions:

  hit@k      Did the student get *any* genuinely relevant Chunk? This is the
             headline. A reply with one good Citation is grounded; a reply with
             three mediocre ones is not.
  recall@k   How much of the relevant material did we surface? Bounded above by
             k / len(relevant), so a pair with four relevant Chunks can never
             score 1.0 at k=3. That ceiling is reported rather than hidden.
  MRR        How far down the list the first relevant Chunk sat. Rank matters:
             the tutor quotes what comes first.
  nDCG@k     Like MRR but graded, so putting the Chunk that *teaches* the skill
             above one that merely mentions the topic scores higher.

No scikit-learn, no numpy. Each of these is two lines of arithmetic, and seeing
them written out is the point -- see PRD decision 4.
"""

from __future__ import annotations

from math import log2

# Relevance grades used in the Golden Set.
TEACHES = 2  # this Chunk teaches the skill the question asks about
RELATED = 1  # same topic, genuinely useful, not the direct answer


def hit_at_k(retrieved: list[str], relevant: dict[str, int], k: int) -> float:
    """1.0 if any relevant Chunk made the top k, else 0.0."""
    return float(any(c in relevant for c in retrieved[:k]))


def recall_at_k(retrieved: list[str], relevant: dict[str, int], k: int) -> float:
    """Share of the relevant Chunks that made the top k."""
    if not relevant:
        raise ValueError("recall is undefined when nothing is relevant")
    found = sum(1 for c in retrieved[:k] if c in relevant)
    return found / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: dict[str, int]) -> float:
    """1/rank of the first relevant Chunk, counting from 1. Zero if none."""
    for position, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in relevant:
            return 1 / position
    return 0.0


def dcg(grades: list[int]) -> float:
    """Discounted cumulative gain: a grade is worth less the further down it sits."""
    return sum((2**g - 1) / log2(i + 1) for i, g in enumerate(grades, start=1))


def ndcg_at_k(retrieved: list[str], relevant: dict[str, int], k: int) -> float:
    """DCG of what we returned, over the DCG of the best possible ordering."""
    actual = dcg([relevant.get(c, 0) for c in retrieved[:k]])
    ideal = dcg(sorted(relevant.values(), reverse=True)[:k])
    return actual / ideal if ideal else 0.0


def ceiling_at_k(relevant: dict[str, int], k: int) -> float:
    """The best recall@k this pair allows. Reported so recall is not misread."""
    return min(len(relevant), k) / len(relevant)
