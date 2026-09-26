#!/usr/bin/env python3
"""Render a project Markdown doc as styled HTML, for printing to PDF.

No dependencies, so it runs anywhere the repo does. Pair it with headless
Chrome to produce the PDF:

    python tools/md2html.py docs/PHASE1.md /tmp/spec.html "subtitle line"
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\
        --headless --no-pdf-header-footer \\
        --print-to-pdf=spec.pdf file:///tmp/spec.html

Supports the subset this project's docs use: headings, tables, fenced code,
blockquotes, nested lists, links and inline emphasis.
"""

from __future__ import annotations

import html
import re
import sys

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
@media print {
  h1,h2,h3 { break-after: avoid; }
  table, pre, blockquote, tr { break-inside: avoid; }
}
:root {
  --ink:#16181d; --muted:#5b6472; --rule:#dfe3ea;
  --accent:#1c4f8b; --bg-soft:#f6f8fb; --code-bg:#f2f4f8;
}
* { box-sizing: border-box; }
body { font-family:"Charter","Iowan Old Style",Georgia,serif; color:var(--ink);
       font-size:10.4pt; line-height:1.58; margin:0; -webkit-font-smoothing:antialiased; }
h1 { font-size:22pt; line-height:1.18; margin:0 0 4pt; letter-spacing:-0.015em; font-weight:700; }
.subtitle { color:var(--muted); font-size:10pt; margin:0 0 4pt; }
.rule-top { border:0; border-top:2.5px solid var(--accent); margin:10pt 0 16pt; }
h2 { font-size:14.5pt; margin:22pt 0 7pt; padding-bottom:4pt;
     border-bottom:1px solid var(--rule); letter-spacing:-0.01em; font-weight:700; }
h3 { font-size:11.6pt; margin:15pt 0 5pt; font-weight:700; }
h4 { font-size:10.6pt; margin:12pt 0 4pt; font-weight:700; color:var(--muted); }
p { margin:0 0 8pt; }
ul, ol { margin:0 0 9pt; padding-left:17pt; }
li { margin:0 0 3.5pt; }
li > ul, li > ol { margin-top:3.5pt; }
a { color:var(--accent); text-decoration:none; border-bottom:0.5px solid #b9cbe0; }
strong { font-weight:700; }
blockquote { margin:0 0 10pt; padding:6pt 12pt; border-left:3px solid var(--rule);
             color:var(--muted); font-style:italic; }
blockquote p:last-child { margin-bottom:0; }
code { font-family:"Menlo","SF Mono",Consolas,monospace; font-size:8.6pt;
       background:var(--code-bg); padding:1px 4px; border-radius:3px; border:0.5px solid #e3e7ee; }
pre { font-family:"Menlo","SF Mono",Consolas,monospace; font-size:7.6pt; line-height:1.42;
      background:var(--bg-soft); border:1px solid var(--rule); border-left:3px solid var(--accent);
      border-radius:4px; padding:9pt 11pt; overflow:hidden; white-space:pre; margin:0 0 10pt; }
pre code { background:none; border:0; padding:0; font-size:inherit; }
table { border-collapse:collapse; width:100%; margin:0 0 11pt; font-size:9.1pt; }
th { text-align:left; background:var(--bg-soft); font-weight:700;
     border-bottom:1.5px solid var(--accent); padding:5pt 7pt; line-height:1.35; }
td { border-bottom:0.5px solid var(--rule); padding:5pt 7pt; vertical-align:top; line-height:1.42; }
tr:last-child td { border-bottom:1px solid var(--rule); }
hr { border:0; border-top:1px solid var(--rule); margin:18pt 0; }
"""

_stash: list[str] = []


def _keep(fragment: str) -> str:
    _stash.append(fragment)
    return f"\x00{len(_stash) - 1}\x00"


def inline(text: str) -> str:
    """Inline markdown. Code spans are stashed first so nothing rewrites them."""
    text = re.sub(r"`([^`]+)`", lambda m: _keep(f"<code>{html.escape(m.group(1))}</code>"), text)
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?=[^\s*])([^*]+?)(?<=\S)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: _stash[int(m.group(1))], text)


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def convert(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    stack: list[tuple[str, int]] = []
    i, n = 0, len(lines)

    def close(to_indent: int = -1) -> None:
        while stack and stack[-1][1] > to_indent:
            out.append(f"</{stack.pop()[0]}>")

    while i < n:
        line, stripped = lines[i], lines[i].strip()

        if stripped.startswith("```"):
            close()
            i += 1
            buf: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(buf))}</code></pre>")
            continue

        if not stripped:
            close()
            i += 1
            continue

        if re.match(r"^(---+|\*\*\*+)$", stripped):
            close()
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith(">"):
            close()
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(quote))}</p></blockquote>")
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            close()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            i += 1
            continue

        if (stripped.startswith("|") and i + 1 < n
                and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip())):
            close()
            head = cells(stripped)
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i].strip()))
                i += 1
            table = ["<table><thead><tr>"]
            table += [f"<th>{inline(c)}</th>" for c in head]
            table.append("</tr></thead><tbody>")
            for row in rows:
                row += [""] * (len(head) - len(row))
                body = "".join(f"<td>{inline(c)}</td>" for c in row[: len(head)])
                table.append(f"<tr>{body}</tr>")
            table.append("</tbody></table>")
            out.append("".join(table))
            continue

        item = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if item:
            indent = len(item.group(1))
            tag = "ul" if item.group(2) in ("-", "*", "+") else "ol"
            while stack and stack[-1][1] > indent:
                out.append(f"</{stack.pop()[0]}>")
            if not stack or stack[-1][1] < indent:
                stack.append((tag, indent))
                out.append(f"<{tag}>")
            elif stack[-1][0] != tag:
                out.append(f"</{stack.pop()[0]}>")
                stack.append((tag, indent))
                out.append(f"<{tag}>")
            out.append(f"<li>{inline(item.group(3))}</li>")
            i += 1
            continue

        close()
        para = [stripped]
        i += 1
        while i < n and lines[i].strip() and not re.match(
            r"^(\s*)([-*+]|\d+\.)\s+|^#{1,6}\s|^\||^```|^>|^(---+|\*\*\*+)$", lines[i]
        ):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")

    close()
    return "\n".join(out)


def main() -> int:
    source, destination = sys.argv[1], sys.argv[2]
    subtitle = sys.argv[3] if len(sys.argv) > 3 else ""

    with open(source, encoding="utf-8") as fh:
        md = fh.read()

    title = "Document"
    first = re.match(r"^#\s+(.*)$", md.split("\n")[0])
    if first:
        title = first.group(1)
        md = "\n".join(md.split("\n")[1:])

    subtitle_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""
    page = (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>\n"
        f'<body><div class="doc">\n<h1>{html.escape(title)}</h1>\n{subtitle_html}\n'
        f'<hr class="rule-top">\n{convert(md)}\n</div></body></html>'
    )
    with open(destination, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"wrote {destination} ({len(page)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
