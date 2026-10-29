"""Run the Golden Set through the Retriever and print what happened.

    python -m evaluation.report          # k = 3, what the tutor actually uses
    python -m evaluation.report 5        # k = 5

Deterministic and offline: no API key, no network, so CI can gate on it.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from core.retrieve import Retriever
from evaluation.metrics import (
    ceiling_at_k,
    hit_at_k,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)

GOLDEN_SET = Path("evaluation/golden_set.jsonl")

# What the tutor asks for in production, so the score is the one that matters.
DEFAULT_K = 3


@dataclass
class Scored:
    """One Golden Pair, run."""

    pair: dict
    retrieved: list[str]
    top_score: float

    @property
    def is_negative(self) -> bool:
        """A pair whose correct outcome is that nothing is relevant."""
        return not self.pair["relevant"]


def load_pairs(path: Path = GOLDEN_SET) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def run(k: int = DEFAULT_K, path: Path = GOLDEN_SET) -> list[Scored]:
    retriever = Retriever()
    scored = []
    for pair in load_pairs(path):
        # Ask for more than k so MRR can see a relevant Chunk sitting just
        # outside the window the tutor would have used.
        results = retriever.search(pair["question"], k=max(k, 10))
        scored.append(
            Scored(
                pair=pair,
                retrieved=[r.id for r in results],
                top_score=results[0].score if results else 0.0,
            )
        )
    return scored


def summarise(scored: list[Scored], k: int) -> dict[str, float]:
    """Aggregate the positive pairs. Negatives are measured separately."""
    positives = [s for s in scored if not s.is_negative]
    if not positives:
        return {}
    n = len(positives)
    return {
        "pairs": n,
        f"hit@{k}": sum(hit_at_k(s.retrieved, s.pair["relevant"], k) for s in positives) / n,
        f"recall@{k}": sum(recall_at_k(s.retrieved, s.pair["relevant"], k) for s in positives) / n,
        f"ceiling@{k}": sum(ceiling_at_k(s.pair["relevant"], k) for s in positives) / n,
        "mrr": sum(reciprocal_rank(s.retrieved, s.pair["relevant"]) for s in positives) / n,
        f"ndcg@{k}": sum(ndcg_at_k(s.retrieved, s.pair["relevant"], k) for s in positives) / n,
    }


def _table(title: str, rows: dict[str, dict[str, float]], k: int) -> None:
    print(f"\n{title}")
    print(f"  {'':34} {'n':>3}  {'hit':>6} {'recall':>6} {'ceil':>6} {'mrr':>6} {'ndcg':>6}")
    for label, m in rows.items():
        print(
            f"  {label:34} {m['pairs']:>3.0f}  {m[f'hit@{k}']:>6.2f} {m[f'recall@{k}']:>6.2f} "
            f"{m[f'ceiling@{k}']:>6.2f} {m['mrr']:>6.2f} {m[f'ndcg@{k}']:>6.2f}"
        )


def _grouped(scored: list[Scored], field: str, k: int) -> dict[str, dict[str, float]]:
    buckets: dict[str, list[Scored]] = defaultdict(list)
    for s in scored:
        if not s.is_negative:
            buckets[s.pair[field]].append(s)
    return {label: summarise(group, k) for label, group in sorted(buckets.items())}


def _floor_sweep(scored: list[Scored]) -> None:
    """What a minimum-score floor would cost and buy.

    The tutor currently cites anything scoring above zero, so a question with
    no answer in the corpus still gets three confident Citations. A floor fixes
    that -- but only if answerable questions score higher than unanswerable
    ones, which is a property of the corpus, not a thing we can assume.
    """
    negatives = [s for s in scored if s.is_negative]
    positives = [s for s in scored if not s.is_negative]
    print("\n  a minimum-score floor would cost and buy:")
    print(f"    {'floor':>6}  {'false groundings cut':>20}  {'answerable questions lost':>25}")
    for floor in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35):
        cut = sum(1 for s in negatives if s.top_score < floor)
        lost = sum(1 for s in positives if 0.0 < s.top_score < floor)
        print(f"    {floor:>6.2f}  {cut:>12}/{len(negatives):<7}  {lost:>17}/{len(positives):<7}")


def main() -> None:
    k = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_K
    scored = run(k)

    overall = summarise(scored, k)
    _table(f"Golden Set at k={k}", {"all positive pairs": overall}, k)
    _table("By strand", _grouped(scored, "strand", k), k)
    _table("By class", _grouped(scored, "class", k), k)
    _table("By style", _grouped(scored, "style", k), k)

    negatives = [s for s in scored if s.is_negative]
    if negatives:
        grounded = [s for s in negatives if s.retrieved]
        print(f"\nNo-answer pairs ({len(negatives)}): questions with no Chunk that teaches them")
        print(f"  cited something anyway   {len(grounded)}/{len(negatives)}")
        print("  top score each:")
        for s in sorted(negatives, key=lambda s: -s.top_score):
            print(f"    {s.top_score:.4f}  {s.pair['question'][:62]}")
        best_true = max(
            (s.top_score for s in scored if not s.is_negative and s.retrieved), default=0.0
        )
        worst_true = min(
            (s.top_score for s in scored if not s.is_negative and s.retrieved), default=0.0
        )
        print(f"\n  for comparison, answerable questions scored {worst_true:.4f}-{best_true:.4f}")

        _floor_sweep(scored)

    missed = [
        s for s in scored if not s.is_negative and not hit_at_k(s.retrieved, s.pair["relevant"], k)
    ]
    if missed:
        print(f"\nMissed entirely at k={k} ({len(missed)}):")
        for s in missed:
            rank = next((i for i, c in enumerate(s.retrieved, 1) if c in s.pair["relevant"]), None)
            where = f"first relevant at rank {rank}" if rank else "not in top 10 at all"
            print(f"  {s.pair['id']}  {s.pair['question'][:58]:60} {where}")


if __name__ == "__main__":
    main()
