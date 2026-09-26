"""Ingest Siyavula's open maths textbooks into licence-tagged chunks.

Siyavula publishes Grade 7-9 mathematics under CC BY 3.0: "All Siyavula
textbook content made available on this site is released under the terms of a
Creative Commons Attribution License." Grades 7-9 line up directly with Ghana's
B7-B9, which is why this is the grounding corpus rather than a US source.

Embedded videos, simulations and presentations are explicitly excluded from
that licence, so only prose paragraphs are taken.

Fetched HTML is cached under corpus/raw/siyavula/ (gitignored) so that repeated
runs cost nothing and do not hammer their servers. Requests are serialised with
a delay; this is someone else's free educational resource.

Usage:
    python -m ingest.siyavula [--grades 7 8 9] [--out PATH] [--refresh]
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from ingest.chunk import Passage, group
from ingest.schemas import Chunk

BASE = "https://www.siyavula.com"
SOURCE_ID = "siyavula-za-mathematics"
LICENCE = "CC-BY-3.0"
ATTRIBUTION = (
    "Siyavula Education, Mathematics Grade {grade} (South Africa), "
    "CC BY 3.0, https://www.siyavula.com/read/za/mathematics/grade-{grade}"
)

CACHE = Path("corpus/raw/siyavula")
DEFAULT_OUT = Path("corpus/chunks.jsonl")

USER_AGENT = "EduBot-Africa/0.1 (educational research; +https://github.com/Angel-builds/edubot-africa)"
DELAY_SECONDS = 1.0

BLOCK_TAGS = re.compile(r"(?is)<(script|style|nav|footer|header|noscript|form)[^>]*>.*?</\1>")
HEADING_OR_PARA = re.compile(r"(?is)<(h[123]|p)[^>]*>(.*?)</\1>")
TAGS = re.compile(r"<[^>]+>")

# Site chrome that appears inside <p> on every page.
CHROME = re.compile(
    r"Home Practice|We use this information to present|Sign up|Log in|"
    r"Terms and Conditions|Privacy Policy|Past papers|Toggle navigation",
    re.I,
)


def fetch(path: str, refresh: bool = False) -> str | None:
    """Fetch a page, caching it under corpus/raw/siyavula/."""
    key = hashlib.sha256(path.encode()).hexdigest()[:16]
    cached = CACHE / f"{key}.html"
    if cached.exists() and not refresh:
        return cached.read_text(encoding="utf-8", errors="replace")

    request = urllib.request.Request(BASE + path, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  fetch failed {path}: {exc}")
        return None

    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(body, encoding="utf-8")
    time.sleep(DELAY_SECONDS)
    return body


def content_pages(grade: int, refresh: bool) -> list[str]:
    """Chapter TOCs list the numbered sub-pages that hold the actual prose."""
    toc = fetch(f"/read/za/mathematics/grade-{grade}", refresh)
    if toc is None:
        return []
    chapters = sorted(
        set(re.findall(rf'href="(/read/za/mathematics/grade-{grade}/[a-z0-9-]+)"', toc))
    )

    pages: list[str] = []
    for chapter in chapters:
        body = fetch(chapter, refresh)
        if body is None:
            continue
        subs = sorted(set(re.findall(rf'href="({re.escape(chapter)}/[a-z0-9-]+)"', body)))
        pages.extend(subs or [chapter])
    return sorted(set(pages))


def passages(page_html: str) -> list[Passage]:
    """Walk headings and paragraphs in order, tracking the heading path."""
    body = BLOCK_TAGS.sub(" ", page_html)
    path: list[str] = ["", "", ""]
    out: list[Passage] = []
    seen_heading = False

    for tag, raw in HEADING_OR_PARA.findall(body):
        text = " ".join(html.unescape(TAGS.sub(" ", raw)).split())
        if not text:
            continue
        tag = tag.lower()
        if tag.startswith("h"):
            level = int(tag[1]) - 1
            path[level] = text
            for deeper in range(level + 1, 3):
                path[deeper] = ""
            seen_heading = True
            continue

        # Everything before the first heading is site chrome.
        if not seen_heading or CHROME.search(text) or len(text.split()) < 12:
            continue
        out.append(Passage(heading_path=tuple(p for p in path if p), text=text))

    return out


def ingest(grades: list[int], refresh: bool) -> list[Chunk]:
    retrieved = date.today()
    chunks: list[Chunk] = []

    seen_text: set[str] = set()
    for grade in grades:
        pages = content_pages(grade, refresh)
        print(f"grade {grade}: {len(pages)} content pages")
        index = 0
        for path in pages:
            page_html = fetch(path, refresh)
            if page_html is None:
                continue
            for piece in group(passages(page_html)):
                # Chapter intros repeat verbatim across a chapter's sub-pages.
                fingerprint = hashlib.sha256(piece.text.encode()).hexdigest()
                if fingerprint in seen_text:
                    continue
                seen_text.add(fingerprint)
                digest = hashlib.sha256(
                    f"{path}|{index}|{piece.text[:120]}".encode()
                ).hexdigest()[:16]
                try:
                    chunks.append(
                        Chunk(
                            id=digest,
                            source_id=f"{SOURCE_ID}-g{grade}",
                            grade=grade,
                            heading_path=piece.heading_path,
                            text=piece.text,
                            url=BASE + path,
                            licence=LICENCE,
                            attribution=ATTRIBUTION.format(grade=grade),
                            retrieved=retrieved,
                            chunk_index=index,
                            word_count=piece.word_count,
                        )
                    )
                    index += 1
                except ValueError:
                    continue  # too short to be useful
    return chunks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest Siyavula CC BY maths content.")
    ap.add_argument("--grades", type=int, nargs="+", default=[7, 8, 9])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--refresh", action="store_true", help="bypass the local cache")
    args = ap.parse_args(argv)

    chunks = ingest(args.grades, args.refresh)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk.model_dump(mode="json")) + "\n")

    words = sum(c.word_count for c in chunks)
    print(f"chunks     {len(chunks):5d}")
    print(f"words      {words:5d}  (mean {words // max(len(chunks), 1)} per chunk)")
    print(f"written    {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
