"""Extract the maths skill graph from the NaCCA Common Core Programme PDF.

Only codes, short titles and structure are emitted. Exemplar prose, figures and
worked examples are deliberately discarded: the source PDF is marked
all-rights-reserved and must not be reproduced.

Extraction is positional. Column boundaries come from the table's ruled
vertical lines rather than from the header text, because the header row is not
reliably aligned with the data columns -- on page 235 the "INDICATORS" header
sits at x=335 while the actual column rule is at x=222.

Parents are repaired conservatively. An indicator's printed parent is trusted
whenever that standard exists somewhere in the document; only genuine orphans
are re-parented from column context. Page 201 prints indicator B9.1.2.3.4 under
standard B9.1.2.4, and no B9.1.2.3 exists anywhere -- that is a typo in the
source document, and it is the case this rule is for.

Usage:
    python -m ingest.nacca_taxonomy [--pdf PATH] [--out PATH] [--rejects PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import pdfplumber

from ingest.schemas import (
    MATHS_STRANDS,
    MAX_TITLE_CHARS,
    CurriculumNode,
    Reject,
    Source,
    StrandRef,
)

DOCUMENT = "MATHEMATICS-CCP-B7-B9"
EDITION = "2020"

DEFAULT_PDF = Path("corpus/raw/MATHEMATICS-CCP-B7-B9.pdf")
DEFAULT_OUT = Path("corpus/skill_graph.jsonl")
DEFAULT_REJECTS = Path("corpus/rejects.jsonl")

CODE_TOKEN = re.compile(r"B\s?\.?\s?[789][\d\.\s]{2,14}")

# Exemplars begin here; everything after is prose we do not store.
EXEMPLAR = re.compile(r"E\.?\s?g\.?\s?\d", re.IGNORECASE)

COMPETENCY = re.compile(r"\(([A-Z]{2})\)")
SUB_STRAND = re.compile(r"Sub-?strand\s*(\d)\s*[:\-]?\s*([A-Za-z][A-Za-z ,&'()/-]{2,60})", re.I)

MIN_RULE_HEIGHT = 80


def normalise_code(token: str) -> str | None:
    """Strip separators, re-segment positionally, emit canonical form.

    Covers every variant observed: 'B.9.1.2.1', trailing dots, 'B71.2.2.2',
    and codes broken across a line.
    """
    digits = re.sub(r"\D", "", token)
    if len(digits) < 4 or digits[0] not in "789":
        return None
    digits = digits[:5]
    return "B" + digits[0] + "." + ".".join(digits[1:])


def column_bounds(page) -> tuple[float, float] | None:
    """Column separator x-positions, taken from the table's vertical rules."""
    xs = sorted(
        e["x0"] for e in page.edges
        if e["orientation"] == "v" and e.get("height", 0) > MIN_RULE_HEIGHT
    )
    merged: list[float] = []
    for x in xs:
        if not merged or x - merged[-1] > 4:
            merged.append(x)
    if len(merged) < 4:
        return None
    return merged[1], merged[2]


def column_text(page, mid: float, right: float) -> dict[str, str]:
    """Group words into the three columns, preserving reading order."""
    lines: dict[str, dict[float, list[tuple[float, str]]]] = {
        "standard": defaultdict(list),
        "indicator": defaultdict(list),
        "competency": defaultdict(list),
    }
    for w in page.extract_words():
        if w["x0"] < mid - 4:
            key = "standard"
        elif w["x0"] < right - 4:
            key = "indicator"
        else:
            key = "competency"
        lines[key][round(w["top"])].append((w["x0"], w["text"]))

    out = {}
    for key, rows in lines.items():
        out[key] = " ".join(
            " ".join(t for _, t in sorted(rows[top])) for top in sorted(rows)
        )
    return out


def split_on_codes(text: str) -> list[tuple[str, str]]:
    """Split a column into (raw_code, following_text) pairs."""
    matches = list(CODE_TOKEN.finditer(text))
    return [
        (m.group(0), text[m.end(): matches[i + 1].start() if i + 1 < len(matches) else len(text)])
        for i, m in enumerate(matches)
    ]


def clean_title(raw: str) -> str:
    """The skill name only, stopping before any exemplar prose."""
    cut = EXEMPLAR.search(raw)
    if cut:
        raw = raw[: cut.start()]
    raw = " ".join(raw.split())
    raw = re.sub(r"^[\d\s.;:]+", "", raw)
    return raw.strip(" .;:")[:MAX_TITLE_CHARS].strip()


def scan(pdf_path: Path) -> tuple[list[dict], dict[tuple[str, int, int], str]]:
    """Single pass over the PDF, yielding raw (code, title, page, comps) records."""
    records: list[dict] = []
    sub_titles: dict[tuple[str, int, int], str] = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            bounds = column_bounds(page)
            if bounds is None:
                continue
            cols = column_text(page, *bounds)
            comps = sorted(set(COMPETENCY.findall(cols["competency"])))
            whole = f"{cols['standard']} {cols['indicator']}"

            # Standards may be printed in either of the first two columns.
            for column in ("standard", "indicator"):
                for raw_code, tail in split_on_codes(cols[column]):
                    code = normalise_code(raw_code)
                    if code is None:
                        continue
                    records.append(
                        {
                            "code": code,
                            "title": clean_title(tail),
                            "page": page_no,
                            "comps": comps,
                            "column": column,
                        }
                    )

            for num, name in SUB_STRAND.findall(whole):
                codes_here = [normalise_code(c) for c, _ in split_on_codes(whole)]
                for c in codes_here:
                    if c:
                        parts = c.split(".")
                        sub_titles.setdefault(
                            (parts[0], int(parts[1]), int(num)), " ".join(name.split())
                        )
                        break

    return records, sub_titles


def build(records: list[dict], sub_titles: dict) -> tuple[list[CurriculumNode], list[Reject]]:
    rejects: list[Reject] = []
    retrieved = date.today()

    standards = {r["code"] for r in records if len(r["code"].split(".")) == 4}

    # Document order of standards, for re-parenting genuine orphans.
    order: list[tuple[int, str]] = sorted(
        {(r["page"], r["code"]) for r in records if len(r["code"].split(".")) == 4}
    )

    def preceding_standard(page: int, klass: str) -> str | None:
        best = None
        for p, code in order:
            if p <= page and code[:2] == klass:
                best = code
        return best

    nodes: dict[str, CurriculumNode] = {}
    for r in records:
        code, parts = r["code"], r["code"].split(".")
        if not r["title"]:
            rejects.append(
                Reject(page=r["page"], reason="no title recoverable before exemplar text", raw=code)
            )
            continue
        level = "standard" if len(parts) == 4 else "indicator"
        parent = None

        if level == "indicator":
            printed = ".".join(parts[:4])
            if printed in standards:
                parent = printed
            else:
                # Genuine orphan: the printed parent exists nowhere in the document.
                fallback = preceding_standard(r["page"], code[:2])
                if fallback is None:
                    rejects.append(
                        Reject(
                            page=r["page"],
                            reason="orphan indicator, no parent found",
                            raw=code,
                        )
                    )
                    continue
                repaired = f"{fallback}.{parts[4]}"
                rejects.append(
                    Reject(
                        page=r["page"],
                        reason=f"printed parent {printed} does not exist; re-parented from "
                        f"column context",
                        raw=code,
                        repaired_to=repaired,
                    )
                )
                code, parts, parent = repaired, repaired.split("."), fallback

        strand_n, sub_n = int(parts[1]), int(parts[2])
        try:
            node = CurriculumNode(
                code=code,
                level=level,
                **{"class": code[:2]},
                strand=StrandRef(number=strand_n, title=MATHS_STRANDS.get(strand_n)),
                sub_strand=StrandRef(
                    number=sub_n, title=sub_titles.get((code[:2], strand_n, sub_n))
                ),
                parent=parent,
                title=r["title"],
                core_competencies=r["comps"],
                source=Source(
                    document=DOCUMENT, edition=EDITION, page=r["page"], retrieved=retrieved
                ),
            )
        except Exception as exc:  # noqa: BLE001 - recorded, never silent
            rejects.append(Reject(page=r["page"], reason=str(exc)[:200], raw=code))
            continue

        # Keep the first occurrence; later pages repeat the standard as the table continues.
        nodes.setdefault(code, node)

    return sorted(nodes.values(), key=lambda n: n.code), rejects


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Extract the NaCCA maths skill graph.")
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--rejects", type=Path, default=DEFAULT_REJECTS)
    args = ap.parse_args(argv)

    if not args.pdf.exists():
        print(f"missing source PDF: {args.pdf}", file=sys.stderr)
        print("download into corpus/raw/ (gitignored); see corpus/MANIFEST.json", file=sys.stderr)
        return 1

    records, sub_titles = scan(args.pdf)
    nodes, rejects = build(records, sub_titles)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for node in nodes:
            fh.write(json.dumps(node.model_dump(by_alias=True, mode="json")) + "\n")
    with args.rejects.open("w", encoding="utf-8") as fh:
        for reject in rejects:
            fh.write(json.dumps(reject.model_dump(mode="json")) + "\n")

    standards = [n for n in nodes if n.level == "standard"]
    indicators = [n for n in nodes if n.level == "indicator"]
    by_class: dict[str, int] = defaultdict(int)
    for n in standards:
        by_class[n.class_] += 1

    split = "  ".join(f"{k}={by_class[k]}" for k in sorted(by_class))
    print(f"standards  {len(standards):4d}   {split}")
    print(f"indicators {len(indicators):4d}")
    print(f"rejects    {len(rejects):4d}  -> {args.rejects}")
    print(f"written    {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
