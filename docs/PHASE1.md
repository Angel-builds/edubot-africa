# Phase 1 — Corpus and Skill Graph

## Objective

Turn the Ghanaian JHS maths curriculum into two machine-readable artifacts: a **skill graph** (what a student must learn, as a queryable hierarchy) and a **grounded content corpus** (openly licensed prose that teaches it, mapped onto that hierarchy).

**Definition of done.** `python -m ingest.nacca_taxonomy` emits a complete, validated skill graph; `python -m ingest.siyavula` emits licence-tagged content chunks each mapped to at least one curriculum indicator; both are versioned, date-stamped, and covered by tests that run in CI.

**Cost: zero.** No accounts, no API spend, no deployment. This phase is parsing and data modelling.

---

## Why this phase is the spine

Nothing downstream works without it, and one decision here determines whether the project can ever expand beyond maths.

| Downstream phase | What it needs from Phase 1 |
|---|---|
| 2 — Retrieval | Indicator codes as the metadata filter on hybrid search |
| 3 — Eval gate | Strand tags, so scores report per-slice instead of one misleading aggregate |
| 5 — Tutor | An indicator to ground each answer against and cite |
| 6 — Practice items | Items are generated *conditioned on* a specific indicator |
| 9 — Pilot | "Weak strand" student profiles are expressed in these codes |
| Later — Science | Ingest a corpus, write an eval set, change no code — **only if `subject` is a field from day one** |

That last row is the one to protect. Every table, every function signature, every chunk record carries `subject` even though the pilot ships maths alone. It costs nothing now and is expensive to retrofit.

---

## The legal boundary — read before writing any code

This governs every decision below, so it comes first rather than as a footnote.

NaCCA's curriculum PDFs are free to download but carry an explicit notice:

> *"All rights reserved. No part of this publication may be reproduced without prior written permission from the Ministry of Education, Ghana."*

Ghana's Copyright Act 2005 (Act 690) s.8 exempts enactments, court decisions, commission reports and news from protection. **Curricula are not on that list.** s.13 gives corporate bodies 70 years. The s.19 teaching exceptions are narrow and purpose-limited — they do not cover ingesting and redistributing a work through a product.

**What may be stored and served:**

- Indicator and content-standard **codes** (`B7.1.1.1.1`)
- **Short functional titles** — a few words naming the skill, written in your own words where possible
- Structural relationships (which sub-strand a standard belongs to)
- Your own explanatory prose
- Openly licensed prose, with attribution (Siyavula CC BY, TESSA CC BY-SA)

**What must not be stored or served:**

- Verbatim exemplar prose from the curriculum
- The PDFs themselves, or any long extract
- WAEC past-question text scraped from pasco sites — no public licence exists, and those sites' own terms add a second problem
- Any commercially published approved textbook

Practical consequences: `corpus/raw/` and `*.pdf` are already gitignored. The extractor reads a local PDF and emits only codes and short titles. There is no "download the curriculum" feature, now or later.

**Do this early and it costs nothing:** email `info@nacca.gov.gh` asking for written permission. It is the mechanism the notice itself specifies, NaCCA has been publicly pro-AI since the October 2025 Ministry/PlayLab launch, and a written yes removes the entire question before there is anything to lose.

---

## Part A — The skill graph

### A1. Source acquisition

```
https://nacca.gov.gh/wp-content/uploads/2022/10/MATHEMATICS-CCP-B7-B9.pdf
5.6 MB · 259 pages · landscape A4
```

Download to `corpus/raw/` (gitignored). Record URL, SHA-256, retrieval date, and curriculum edition in a committed `corpus/MANIFEST.json`.

**Do not skip the manifest.** NaCCA moves and removes files without notice — the Social Studies curriculum URL that Google still indexes is already a 404. A revised basic-school curriculum went to the Ministry in July 2026 and is not yet Cabinet-approved, so a second edition is coming. Version from the start and swapping editions later is an ingest re-run rather than a re-architecture.

### A2. The annotation scheme

The curriculum ships with its own identifier system, which is the single most useful thing about it:

```
B7 . 1 . 1 . 1          content standard
│    │   │   └── standard number within the sub-strand
│    │   └────── sub-strand
│    └────────── strand
└─────────────── class (Basic 7 = JHS 1)

B7 . 1 . 1 . 1 . 1      indicator (adds indicator number)
```

Four columns run across the page — **Strand → Sub-strand → Content Standard → Indicators and Exemplars** — plus a fifth for core competencies, themselves coded (`CP` critical thinking and problem solving, `PL` personal development and leadership, and others).

**Maths scope, which doubles as the count to assert against:**

| Element | Scope |
|---|---|
| Strands | Number; Algebra; Geometry and Measurement; Handling Data |
| Sub-strands | Number & Numeration Systems; Number Operations; Fractions, Decimals & Percentages; Ratios & Proportion; Patterns & Relationships; Algebraic Expressions; Variables & Equations; Shapes & Space; Measurement; Position & Transformation; Data; Chance or Probability |
| Content standards | **B7 = 21, B8 = 18, B9 = 18 — 57 total** (measured, not assumed) |
| Indicators | **178 unique** (measured) |

A few hundred nodes is small. This is a data-quality problem, not a scale problem.

### A3. Target schema

One record per node, `subject` present on every one:

```json
{
  "code": "B7.1.1.1.1",
  "subject": "mathematics",
  "level": "indicator",
  "class": "B7",
  "strand": {"number": 1, "title": "Number"},
  "sub_strand": {"number": 1, "title": "Number and Numeration Systems"},
  "parent": "B7.1.1.1",
  "title": "Model number quantities up to 100,000,000",
  "core_competencies": ["CP", "PL"],
  "source": {
    "document": "MATHEMATICS-CCP-B7-B9",
    "edition": "2020",
    "page": 14,
    "retrieved": "2026-09-20"
  }
}
```

`page` earns its place: when a title looks wrong six weeks from now, you want to find it in seconds rather than re-reading 259 pages.

### A4. Extraction approach — settled by diagnostic

**Decision: `pdfplumber`, column-position based. No vision model.**

A diagnostic on pages 34, 121 and 201 (spanning B7/B8/B9) confirmed that word x-positions separate the three columns cleanly on every page tested:

```
PAGE 34    standard -> B7.1.1.1     indicator -> B7.1.1.1.3
PAGE 121   standard -> B8.1.1.1     indicator -> B8.1.1.1.4, B8.1.1.1.5
PAGE 201   standard -> B9.1.2.4     indicator -> B9.1.2.3.4
```

The hybrid vision fallback originally proposed here is unnecessary. Dropping it removes an API key, a per-page cost and a source of nondeterminism, and keeps the whole extractor free and re-runnable inside CI.

**Column boundaries need both signals, and neither works alone.** The table's ruled vertical lines give exact positions, but exemplar cells contain *nested tables* whose rules are indistinguishable from the real column separators — page 47 has rules at `[95, 226, 262, 539, 609, 745]`, where 262 and 539 belong to a nested table. Taking the first two interior rules there put an entire indicator title in the competency column and dropped it.

The header words fix which rules matter, but cannot supply position: on page 235 `INDICATORS` sits 113pt right of its own column rule. So the header chooses the rule, the rule gives the x. A page without both the ruled table and the header row is not a content page and is skipped.

### A5. Known defects — measured

Counted across all 259 pages, so these are observed rather than anticipated:

| Defect | Measured | Impact |
|---|---|---|
| Duplicated maths glyphs (`𝑥𝑥` = U+1D465 twice) | **1,093** | Low — lives in exemplar prose, which is not stored |
| Code format variants | **44 of 408 tokens (~11%)** | Normalisable; see A6 |
| Nested tables inside exemplar cells | present on sampled pages | **High** — their rules mimic column separators; see A4 |
| Figures with no text layer | throughout | None — figures are not stored |
| Source-document code typo | at least 1 confirmed | **High** — see below |

**The defect that actually matters.** On page 201 the content standard is `B9.1.2.4`, but the indicator beneath it is printed `B9.1.2.3.4`. No `B9.1.2.3` exists anywhere in the document. This is an error in NaCCA's own publication, not in extraction.

It matters because a regex over flattened text would silently invent a phantom parent and attach a real indicator to it. Column-aware extraction knows the true parent from the left-hand column and can repair the code. This is the single strongest argument for the positional approach over text matching.

**The broader point:** almost all the feared damage — mangled notation, figures, nested tables — sits in the exemplar column, which the legal boundary excludes from storage anyway. The extraction problem is materially smaller than it first appears.

### A6. Normalisation

Normalise to canonical `B{class}.{strand}.{sub}.{standard}[.{indicator}]`:

1. Strip all separators, keep the leading `B` and the digit run
2. Re-segment positionally — the first digit after `B` is the class (7, 8 or 9)
3. Re-emit with dots
4. Assert the result matches `^B[789](\.\d+){3,4}$`
5. Assert every indicator's parent standard exists in the graph
6. Assert strand and sub-strand numbers agree with the parent's

**Rule 0, which overrides all of the above: column position wins over the printed code.** The left-hand column establishes the true parent for every indicator on the page. Where the printed indicator code disagrees with its column parent, the code is repaired and the repair is logged to `rejects.jsonl` for review — never applied silently.

Rules 5 and 6 are what catch merged-cell damage. Anything that fails goes to a `rejects.jsonl` with its page number, for the human pass — never silently dropped.

### A7. Human verification

Pull a stratified sample of 20 indicators — spanning all four strands and all three classes, weighted toward pages the validator flagged — and check each against the PDF by hand. Record the result in `docs/EXTRACTION_AUDIT.md` with the date and the sample.

This is the only step that catches *plausible but wrong* extraction, which automated checks cannot. Twenty indicators is roughly twenty minutes and it is the difference between a graph you trust and one you hope about.

---

## Part B — The content corpus

The skill graph says what to teach. It deliberately contains no prose to teach with. Part B supplies that from openly licensed sources.

### B1. Source

**Siyavula, unbranded editions — CC BY.** The branded editions are CC BY-ND, which forbids adapting; the unbranded ones are CC BY and permit adaptation and commercial use. **Confirm the licence on the specific file you download** and record it in the manifest. Getting this wrong is the kind of error that is cheap now and expensive later.

Secondary: **TESSA (CC BY-SA)** for teaching approaches — how to explain a concept rather than what the concept is. Useful for the tutor's hint ladder in Phase 5.

Explicitly excluded: Khan Academy and most OpenStax titles are **CC BY-NC**. Non-commercial is incompatible with anything you might later charge for, and retrofitting a corpus swap is far worse than choosing correctly now.

### B2. Chunking

Target 200–500 tokens. Split on semantic boundaries — a worked example, a definition, a rule — not fixed character counts, which cut worked examples in half and produce chunks that retrieve well and teach badly.

Each chunk stores its heading path. A chunk that knows it came from *Fractions → Equivalent fractions → Worked example 3* can be cited precisely, and citation precision is a Phase 5 eval metric.

### B3. Mapping chunks to indicators — the hard part

Siyavula is written to the South African curriculum. Ghana's CCP orders and emphasises topics differently, so alignment is not one-to-one. Some indicators will have several good chunks; some will have none, and **the gaps matter more than the matches** — an indicator with no grounded content is one the tutor cannot teach, and you want that visible in a report rather than discovered by a student.

A workable sequence:

1. Embed indicator titles and chunks, take top-k candidates per indicator
2. Have an LLM score each candidate pair for genuine alignment, with a structured verdict
3. Review everything above threshold by hand — the volume is a few hundred pairs, which is an afternoon
4. Emit `coverage.json`: indicators with no chunk above threshold, by strand

Step 4 is the deliverable people skip and then regret. It tells you where to write your own explanations, and it is honest input to the Phase 3 eval set.

A chunk may map to several indicators, and should.

### B4. Provenance

Every chunk carries `source`, `licence` (SPDX identifier), `attribution` (the exact string the licence requires), `url`, `retrieved`, `chunk_index`. CC BY compliance is not optional, and assembling attribution retroactively across thousands of chunks is miserable.

---

## Deliverables

| Path | |
|---|---|
| `ingest/nacca_taxonomy.py` | PDF → skill graph, with normalisation and validation |
| `ingest/siyavula.py` | Open prose → licence-tagged chunks |
| `ingest/chunk.py` | Shared semantic chunking |
| `ingest/schemas.py` | Pydantic models for nodes and chunks |
| `corpus/skill_graph.jsonl` | Committed — codes and short titles only |
| `corpus/chunks.jsonl` | Committed if size permits, else generated |
| `corpus/MANIFEST.json` | Sources, SHA-256, licences, retrieval dates |
| `corpus/coverage.json` | Indicators lacking grounded content |
| `corpus/rejects.jsonl` | Extraction failures with page numbers |
| `tests/test_taxonomy.py` | Structural assertions, run in CI |
| `docs/EXTRACTION_AUDIT.md` | The 20-indicator hand check |

---

## Verification

Automated, wired into the existing CI job:

- Graph contains exactly **57 content standards**, split **B7 = 21, B8 = 18, B9 = 18**
- Graph contains **178 unique indicators**
- All 235 nodes carry a sub-strand title; 12 distinct sub-strands
- Every code matches `^B[789](\.\d+){3,4}$` after normalisation
- Every indicator's parent standard exists; strand and sub-strand numbers agree with the parent
- Exactly 4 strands, each with at least one sub-strand
- Every node carries `subject`
- Every chunk carries a licence, an attribution string and a retrieval date
- No chunk text appears in the skill graph — the legal boundary, asserted in code
- `rejects.jsonl` is empty, or every entry is listed as accepted in the audit doc

Manual:

- 20 stratified indicators verified by hand against the PDF, recorded in `docs/EXTRACTION_AUDIT.md`
- `coverage.json` reviewed — gaps are a known list, not a surprise

---

## Risks

| Risk | Response |
|---|---|
| Merged cells attach indicators to the wrong parent | Parent/child consistency assertions; this is the defect most likely to look correct and be wrong |
| Titles carry too much verbatim prose | Cap title length; rewrite anything long in your own words |
| Siyavula alignment is weaker than hoped | `coverage.json` makes it measurable; write your own prose for the gaps |
| Downloaded Siyavula file turns out to be CC BY-ND | Verify licence per file before ingest, not after |
| Source document contains more code typos than the one found | Column position overrides printed codes; every repair is logged, not silent |
| Curriculum edition changes mid-project | Manifest + edition field; re-ingest rather than re-architect |
| Extraction quality is judged by eye and drifts | The 20-indicator audit, dated and committed |

---

## Sequencing

1. ~~Diagnostic~~ — **done.** Approach settled: `pdfplumber`, column-positional
2. ~~Decide extraction approach~~ — **done.** No vision model
3. **Schema** — `ingest/schemas.py` first, so the extractor has a target
4. **Extractor** — column detection from the header row, failures to `rejects.jsonl`
5. **Normaliser + validators** — the assertions above, including Rule 0
6. **Hand audit** of 20 indicators
7. **Siyavula ingest** and chunking
8. **Mapping** and `coverage.json`
9. **Tests into CI**, commit

---

## Open decisions

- ~~Extraction approach~~ — **settled by diagnostic: `pdfplumber`, no vision model**
- **Whether to email NaCCA now** — free, non-blocking for a consented family pilot, and it removes the licensing question permanently
- **Chunk size** — 200–500 tokens is the starting range; Phase 3's retrieval metrics will tell you what it should actually be, and this is exactly the kind of parameter the eval gate exists to settle
