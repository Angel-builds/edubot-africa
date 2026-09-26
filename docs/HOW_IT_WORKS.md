# How it works

A reading guide to the working tutor. Five small files, in the order worth
reading them.

## Run it first

```bash
uv run python -m core.cli "3x + 5 = 20"
```

It works with **no API key**. Without one, replies show the coaching step
itself instead of friendly prose, which is the fastest way to see the machinery.
With `ANTHROPIC_API_KEY` set, the same step is phrased by the model.

## The one idea

Almost everything is ordinary deterministic Python. The language model has
exactly one job: **phrase a hint in friendly English**. It does not decide the
answer, does not decide whether the student was right, and does not decide how
much help to give.

```
student question
      │
      ├─► core/solver.py    works out the answer with SymPy      ──┐  PRIVATE
      │                                                            │
      ├─► core/retrieve.py  finds 2 curriculum passages            │
      │                                                            │
      └─► core/tutor.py     picks the coaching step                │
                │                                                  │
                │   passes on: step + passages + "was it right?"   │
                │   never passes on: ◄──────────────────────────────┘
                ▼
          core/llm.py       one API call, phrasing only
```

The dashed line is the product. The tutor model is never handed the answer, so
it cannot leak a solution it was never given. Prompting alone does not survive a
determined 14-year-old across several turns; withholding structurally does.

## The files

### `core/tfidf.py` — how text is scored

Term frequency × inverse document frequency, ~60 lines. A word that appears in
one chunk matters more than a word that appears in all of them. Vectors are
normalised to unit length, so the dot product *is* the cosine similarity.

Read `fit()` and `cosine()`. That is the whole idea.

### `core/retrieve.py` — finding relevant passages

Loads `corpus/chunks.jsonl` into memory, vectorises once, then scores the
question against all 708 chunks. Instant at this size, and needs no database.

Phase 2 replaces this with Supabase + pgvector. The interface — `search(question, k)`
returning `Result` objects — is what stays.

### `core/solver.py` — the private side

SymPy, never the model. Two reasons:

1. Models make arithmetic slips, and a tutor that confidently teaches wrong
   maths to a 13-year-old is worse than no tutor.
2. `matches()` compares by **symbolic equivalence**, so `1/2`, `0.5` and `2/4`
   all mark correct. String comparison would mark two of those wrong and the
   student would stop trusting it within about two questions.

The fiddly part is `_maths_only()`. Students write *"chale i no fit do 2y + 6 = 14"*,
and SymPy's implicit multiplication happily reads that prose as a product of
every letter in the sentence. Trimming to the maths is what stops it returning a
confident, meaningless answer.

### `core/tutor.py` — the hint ladder

```python
LADDER = [
    "Ask what the student has tried so far...",       # level 0
    "Name the idea the question is about...",         # level 1
    "Point to the method or formula...",              # level 2
    "Work through the first step only...",            # level 3
    "Work through the whole solution...",             # level 4  ← the answer
]
```

The student climbs by **failing**, never by asking. Level 5 exists, so the
capability is there — it just is not the opening move. Getting it right resets
to level 0.

That ordering is the design. Bastani et al. (PNAS 2025, ~1,000 students) found
unguarded GPT-4 during maths practice improved in-session performance **+48%**
while leaving students **−17% worse on the unassisted exam**. A guardrailed
variant erased the harm.

### `core/llm.py` — the only API call

About 30 lines. One stateless `messages.create`. `available()` returns False
when no key is set, and the caller falls back to a template — which is why the
whole thing runs before you spend anything.

## Where the state lives

Nowhere. `respond(question, level, student_answer)` is a pure function of its
arguments, and the caller remembers `level`. The HTTP API works the same way:
`POST /chat` takes a level and returns the next one.

That is deliberate — it is the same choice the Messages API makes, and it means
there is no session store to reason about yet.

## What this version does not do

Honest list, so nothing here surprises you later:

- **Bare equations retrieve nothing.** `3x + 5 = 20` has no words of three or
  more letters, so the query vector is empty. The solver still handles it; the
  reply is just ungrounded. Hybrid search in phase 2 is what fixes this.
- **Only linear equations and plain arithmetic.** No word problems, no geometry.
- **No conversation memory** beyond the level integer.
- **The 124 chunk→indicator mappings are unreviewed**, so citations point at
  topically related content, not verified-aligned content.
- **No practice-question generation** yet — that is phase 6.

## Test it

```bash
uv run pytest tests/test_tutor.py -v
```

The test that matters is `test_answer_is_withheld_until_the_top_of_the_ladder`.
Everything else is ordinary correctness; that one is the product.
