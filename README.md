# EduBot Africa

An AI maths tutor grounded in the Ghanaian JHS curriculum (NaCCA Common Core
Programme, B7–B9), built for students on shared Android phones and metered data.

> **Status:** Phase 1 — corpus and skill graph. No AI code yet, by design.

## What makes it different

Most AI tutors answer the question. The evidence says that is the wrong move:
in a ~1,000-student RCT ([Bastani et al., PNAS 2025](https://www.pnas.org/doi/10.1073/pnas.2422633122)),
unguarded GPT-4 during maths practice improved in-session performance **+48%**
while leaving students **−17% worse on the unassisted exam**. A guardrailed
variant erased that harm.

So EduBot withholds solutions by construction, not by prompting:

- **A hint ladder.** The first turn on a new problem asks the student what they
  tried. Full worked solutions sit at level 5, reached after failed attempts —
  never on request.
- **A two-model split.** A private solver computes the answer for grading; the
  tutor model only ever receives `{student_is_correct, error_type}`. Prompting
  alone does not survive a determined 14-year-old across multiple turns.
- **Real arithmetic.** Every computation routes through SymPy. The model writes
  the expression, the tool evaluates it, the model narrates the result. Grading
  is by symbolic equivalence, so `1/2`, `0.5` and `2/4` all mark correct.

## Curriculum and licensing

NaCCA's curriculum PDFs are free to download but marked *all rights reserved*,
and WAEC past questions carry no public licence. EduBot therefore uses the
curriculum as **taxonomy, not content** — NaCCA's `B7.1.1.1` annotation scheme
becomes a skill graph — grounds explanatory prose on openly licensed sources
(Siyavula CC BY, TESSA CC BY-SA), and **generates original practice items**
conditioned on indicator code and BECE question style.

## Stack

| Layer | Choice |
|---|---|
| API | FastAPI on Fly.io `jnb` (Johannesburg — the only Africa region) |
| Store | Supabase Postgres + pgvector, HNSW index |
| Retrieval | Hybrid: vector + tsvector + `pg_trgm`, fused by RRF |
| Model | Claude Haiku 4.5, Anthropic SDK behind a thin `Model` protocol |
| Frontend | Static PWA on Cloudflare Pages, <100KB first paint |

## Development

```bash
uv sync                                   # install
uv run pytest                             # test
uv run ruff check .                       # lint
uv run uvicorn api.main:app --reload      # serve on :8000
curl localhost:8000/health                # {"ok": true, ...}

uv run python -m ingest.nacca_taxonomy    # rebuild the skill graph
uv run python -m ingest.siyavula          # fetch + chunk the CC BY corpus
uv run python -m ingest.map_indicators    # map chunks to indicators, report gaps
```

The extractor needs `corpus/raw/MATHEMATICS-CCP-B7-B9.pdf`, which is gitignored —
see `corpus/MANIFEST.json` for the source URL and checksum. The generated
`corpus/skill_graph.jsonl` is committed, so tests run without it.

Copy `.env.example` to `.env` for local configuration.

## Layout

```
api/      FastAPI service — routes, config
core/     tutor, solver, retrieval, model protocol
ingest/   curriculum -> skill graph, open corpora -> chunks
db/       SQL migrations (pgvector, HNSW, hybrid search, RLS)
evals/    golden datasets + retrieval metrics, gated in CI
web/      static PWA
docs/     pre-registration, eval results, safety, consent
```

## Roadmap

| Phase | |
|---|---|
| 0 | Foundations — FastAPI, Docker, Fly, pytest, CI ✅ |
| 1 | Corpus and skill graph ✅ — 57 standards, 178 indicators, 708 CC BY chunks |
| 2 | Supabase and hybrid retrieval |
| 3 | The eval gate — golden set, recall@k/MRR/nDCG in CI |
| 4 | Retrieval improvement loop |
| 5 | The tutor — hint ladder, SymPy solver |
| 6 | Practice items |
| 7 | Frontend |
| 8 | Safety and consent |
| 9 | Pilot and measurement |

Full plan, including the measurement design and child-safety posture, in
`docs/` and the project plan.
