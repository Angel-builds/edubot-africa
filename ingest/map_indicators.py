"""Map openly licensed chunks onto curriculum indicators, and report the gaps.

This is deliberately a *lexical* mapping -- TF-IDF cosine, hand-rolled so that
CI needs no extra dependency and every run is deterministic. It is not semantic
alignment and does not pretend to be. Siyavula is written to the South African
curriculum, so the vocabulary overlaps heavily but the sequencing does not, and
a term-frequency match is evidence of topical relatedness, nothing stronger.

Every mapping it produces is therefore a *candidate* requiring human review
before the tutor is allowed to cite it. The genuinely useful output is
coverage.json: the indicators with no candidate at all. An indicator with no
grounded content is one the tutor cannot teach, and that belongs in a report
rather than being discovered by a student mid-session.

Upgrading this to embeddings plus an LLM judge is a phase-4 task, once an API
key exists and the retrieval eval set can measure whether it actually helps.

Usage:
    python -m ingest.map_indicators [--threshold 0.25] [--top-k 5]
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

GRAPH = Path("corpus/skill_graph.jsonl")
CHUNKS = Path("corpus/chunks.jsonl")
COVERAGE = Path("corpus/coverage.json")

# Calibrated by inspecting the top-1 score distribution, not validated against
# labels. At 0.08 every one of the 178 indicators "matched" something, which is
# false confidence: the weakest hits paired "find the back bearing" with
# "Rounding to significant figures" and "scalar multiplication of vectors" with
# "Adding algebraic terms". Topical matches begin around 0.25, where the top
# hits are genuinely right ("associative property" -> "The associative
# (grouping) property"). A method that reports no gaps against a different
# country's curriculum is broken, not thorough.
DEFAULT_THRESHOLD = 0.25

TOKEN = re.compile(r"[a-z]{3,}")

# Words that carry no topical signal in this corpus. IDF handles most of the
# curriculum's stock verbs on its own; these are the ones frequent enough in
# prose to still dominate a short indicator title.
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


def tf_idf(documents: list[list[str]]) -> tuple[list[dict[str, float]], dict[str, float]]:
    """L2-normalised TF-IDF vectors, plus the IDF table used to build them."""
    n = len(documents)
    seen: Counter[str] = Counter()
    for tokens in documents:
        seen.update(set(tokens))
    idf = {term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in seen.items()}

    vectors: list[dict[str, float]] = []
    for tokens in documents:
        counts = Counter(tokens)
        vector = {t: (1 + math.log(c)) * idf.get(t, 0.0) for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vector.values())) or 1.0
        vectors.append({t: v / norm for t, v in vector.items()})
    return vectors, idf


def project(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """Put a query into the same space as an already-fitted corpus."""
    counts = Counter(t for t in tokens if t in idf)
    vector = {t: (1 + math.log(c)) * idf[t] for t, c in counts.items()}
    norm = math.sqrt(sum(v * v for v in vector.values())) or 1.0
    return {t: v / norm for t, v in vector.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Map chunks to curriculum indicators.")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args(argv)

    nodes = load(GRAPH)
    chunks = load(CHUNKS)
    indicators = [n for n in nodes if n["level"] == "indicator"]

    # Chunks are the fitted corpus; indicator titles are projected into it.
    chunk_tokens = [tokenise(f"{' '.join(c['heading_path'])} {c['text']}") for c in chunks]
    chunk_vectors, idf = tf_idf(chunk_tokens)

    per_chunk: dict[str, list[str]] = defaultdict(list)
    coverage: dict[str, dict] = {}

    for node in indicators:
        query = project(tokenise(f"{node['sub_strand']['title']} {node['title']}"), idf)
        ranked = sorted(
            ((cosine(query, vec), i) for i, vec in enumerate(chunk_vectors)),
            reverse=True,
        )[: args.top_k]
        hits = [(s, i) for s, i in ranked if s >= args.threshold]

        for _, i in hits:
            per_chunk[chunks[i]["id"]].append(node["code"])

        coverage[node["code"]] = {
            "title": node["title"],
            "class": node["class"],
            "strand": node["strand"]["title"],
            "sub_strand": node["sub_strand"]["title"],
            "candidates": [
                {"chunk_id": chunks[i]["id"], "score": round(s, 4),
                 "heading": " > ".join(chunks[i]["heading_path"][-2:])}
                for s, i in hits
            ],
            "covered": bool(hits),
        }

    for chunk in chunks:
        chunk["indicators"] = sorted(per_chunk.get(chunk["id"], []))
    CHUNKS.write_text(
        "".join(json.dumps(c) + "\n" for c in chunks), encoding="utf-8"
    )

    uncovered = [c for c, v in coverage.items() if not v["covered"]]
    by_strand: Counter[str] = Counter(coverage[c]["strand"] for c in uncovered)

    COVERAGE.write_text(
        json.dumps(
            {
                "method": (
                    "lexical TF-IDF cosine; every candidate requires human "
                    "review before citation. Threshold calibrated by inspecting "
                    "the score distribution, not validated against labels."
                ),
                "threshold": args.threshold,
                "top_k": args.top_k,
                "indicators_total": len(indicators),
                "indicators_covered": len(indicators) - len(uncovered),
                "indicators_uncovered": len(uncovered),
                "uncovered_by_strand": dict(by_strand),
                "uncovered": sorted(uncovered),
                "indicators": coverage,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    mapped_chunks = sum(1 for c in chunks if c["indicators"])
    print(f"indicators      {len(indicators):5d}")
    print(f"  covered       {len(indicators) - len(uncovered):5d}")
    print(f"  uncovered     {len(uncovered):5d}   {dict(by_strand)}")
    print(f"chunks          {len(chunks):5d}")
    print(f"  with mapping  {mapped_chunks:5d}")
    print(f"written         {COVERAGE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
