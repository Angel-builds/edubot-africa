# EduBot Africa — Product Requirements

**Living document.** Last updated 30 October 2026. Amend it in the same commit
as the change it describes; if a decision below stops being true, edit it rather
than appending a correction.

This document uses the words defined in [GLOSSARY.md](../GLOSSARY.md). Where a
term is capitalised — Indicator, Hint Ladder, Reveal — it means exactly what the
glossary says, and the code uses the same word.

---

## 1. What we are building

A maths tutor that Ghanaian Junior High School students can ask for help, which
coaches them toward the answer instead of handing it over, and which grounds
what it says in their own national curriculum.

A student types a question. The tutor finds the relevant teaching material,
works out the answer privately, and replies with the smallest useful nudge. If
the student's Attempt is wrong, the next nudge is bigger. Only after repeated
failure does it work the whole thing through.

## 2. Who it is for

JHS students in Ghana, Classes B7 to B9, roughly ages 12 to 15, studying for the
BECE. Most reach it on a shared Android phone, in the evening, over congested
mobile data they pay for by the megabyte.

They are **minors**, which sets a floor even on a project this small: ask the
parent first, let the student say no, keep no names, and stay on maths. Nothing
elaborate — just not doing the obviously wrong thing with someone's child.

## 3. The problem

Classroom time per student is thin and private tutoring costs money most
families do not have. Students get stuck in the evening with nobody to ask.

Generic chatbots are available and actively unhelpful here: they answer in US
conventions, they do not know the Ghanaian curriculum, and — the part that
matters — they hand over answers, which measurably damages independent
performance (see decision 2).

## 4. What success looks like

This is a personal project that five people have used. The measures below are
about whether the thing behaves correctly, not whether it moves test scores.

| Measure | Target | Why this one |
|---|---|---|
| Reveal rate | ~2% of Turns | The benchmark from the Sierra Leone trial. Directly measures the core guardrail |
| Grounded replies with a valid Citation | high, measured | A tutor citing nothing is just a chatbot |
| hit@3 on the Golden Set | rising from 0.74 | Whether the Citation a student sees is actually relevant |
| Maths errors in teacher-reviewed numeric claims | 0 | Teaching wrong maths to a child is the worst failure available |
| Uncovered Indicators | known and shrinking | An Uncovered Indicator is one the tutor cannot teach |
| Does a student come back unprompted | anecdote is fine at this size | Five users cannot produce a rate, only a signal |

**Not a success measure:** anything causal about learning. With five users
that question is not answerable and is not being asked. See decision 13.

## 5. Non-goals

- Subjects beyond maths during the Pilot. The architecture carries `subject` on
  every record so Science is an ingest run, but it is not in scope now.
- Replacing a teacher, or claiming to.
- Being a product. No users beyond people who know Angel, no accounts, no
  payments, no growth. If that changes, most of section 8 reopens.
- Open-ended conversation, companionship or persona. That is the surface current
  child-safety law targets, and it is deliberately absent.
- Serving curriculum documents. See decision 1.

## 6. Where we are

| Area | State |
|---|---|
| Skill Graph | **Done.** 57 Content Standards, 178 Indicators, 12 Sub-strands, 4 Strands |
| Content corpus | **Done.** 708 Chunks, 104k words, CC BY 3.0 |
| Coverage | **Partial.** 124 of 178 Indicators Covered; 54 Uncovered |
| Tutor | **Minimal but working.** Hint Ladder, private Worked Answer, Symbolic Equivalence marking |
| Model | **Two providers.** Fireworks or Anthropic, by whichever key is set. Live dyno still has neither |
| Retrieval | **Minimal and now measured.** In-memory, lexical. hit@3 is 0.74 across the Golden Set |
| API | `/health`, `/chat` |
| Interface | **Web page and CLI.** 3.2 KB over the wire, 464 bytes a Turn |
| Deployment | **Live** at https://edubot-africa.me — Heroku, EU, Basic dyno, HTTPS forced |
| Evaluation | **Done.** 70 Golden Pairs, five metrics, gated in CI |
| Safety basics | **Not started.** Small: a disclosure line, no names stored |
| Extraction audit | **Not started.** Awaiting engineer review |

Runs today with no API key: replies show the coaching step instead of prose.
The deployed dyno is in exactly that state until a key is set on it.

---

## 7. Decisions and what they cost

Each decision records what we gave up, not only what we chose. A decision with
no cost listed has not been thought about hard enough.

### 7.1 Technical

**1. The curriculum is structure, not content.**
NaCCA's curriculum is marked all-rights-reserved, and Ghana's Copyright Act does
not exempt curricula. So the Skill Graph stores Indicator Codes and short
titles; teaching prose comes from openly licensed sources instead.
*Gave up:* the curriculum's own worked examples, which are good.
*Bought:* a project that can sit in a public repo without a licensing problem.
A schema check enforces it rather than trusting discipline.
*Revisit if:* NaCCA grants written permission.

**2. The tutor withholds answers structurally, not by prompting.**
The Worked Answer never enters the tutor's prompt. The model receives only
whether the Attempt matched. It cannot Reveal what it was never given.
*Gave up:* the model's ability to explain the specific answer fluently at low
Hint Levels.
*Bought:* a guarantee that survives a determined 14-year-old across six Turns.
Prompt instructions do not; tutor behaviour degrades by around 5.8 Turns in
published benchmarks.

**3. Arithmetic goes through SymPy, never the model.**
*Gave up:* coverage. Word problems and geometry are not solvable this way yet.
*Bought:* correctness where it exists, and Symbolic Equivalence marking so
`1/2`, `0.5` and `2/4` all mark correct. String comparison marks two of those
wrong and the student stops trusting the tutor within about two questions.

**4. No orchestration framework.**
The retrieve → prompt → reply path is about 150 lines of plain Python.
*Gave up:* integrations, and the résumé keyword.
*Bought:* every line is readable and the concepts are visible rather than hidden
behind `RetrievalQA`. A later re-implementation as a documented comparison is a
stronger interview answer than adopting it blind.

**5. Retrieval is in-memory and lexical, for now.**
708 Chunks fit in memory and score instantly with TF-IDF.
*Gave up:* semantic matching, and anything resembling scale. Matches are
topical rather than precise — `x^2 = 49` currently lands on solving equations
rather than on powers.
*Note:* a bare equation contains no searchable words at all, so the shape of the
expression is read for topic words before scoring (decision 15). That closed the
ungrounded-reply gap without a database.
*Bought:* no database, no API key, no network — it runs on a laptop today.
*Revisit:* phase 2, which replaces it with Postgres and hybrid search. The
interface stays.

**6. Chunk-to-Indicator mapping is lexical, and says so.**
No LLM judge, because no API key exists and CI must stay deterministic and free.
*Gave up:* mapping quality. Every mapping is a candidate pending engineer review.
*Bought:* an honest Coverage report. At a permissive threshold every Indicator
appeared Covered, which was false confidence — a method reporting no gaps
against another country's curriculum is broken, not thorough.

**7. Siyavula CC BY, not Khan Academy or OpenStax.**
Grades 7–9 line up with B7–B9, and CC BY permits adaptation. Khan Academy and
most OpenStax titles are CC BY-**NC**.
*Gave up:* volume, and South African sequencing that does not match Ghana's.
*Bought:* a corpus that can be redistributed and adapted, with the attribution
line carried on every Chunk.

**8. Generated corpus files are committed.**
*Gave up:* a clean diff; `chunks.jsonl` is about 1 MB.
*Bought:* CI runs every structural and licensing check without the source PDF,
which is gitignored and must stay that way.

**9. The API is stateless; the caller owns Hint Level.**
*Gave up:* server-side memory of a student's progress.
*Bought:* no session store to reason about, and the same shape the Messages API
uses. A real student profile arrives with the database in phase 2.

### 7.2 Product and experience

**10. Coaching is the default, and it will frustrate some students.**
A student who wants the answer in thirty seconds will not enjoy being asked what
they have tried.
*Gave up:* immediate satisfaction, and probably some engagement.
*Bought:* the thing that makes it a tutor. Unguarded AI help raised in-session
performance 48% while leaving students 17% **worse** unaided; a guardrailed
version erased the harm. We are engineering against that specific finding.
*Mitigation:* the ladder is five rungs, not infinite, and a correct Attempt
resets it immediately so success feels fast.

**11. Replies are in clear exam English, whatever the student writes in.**
Pidgin and code-switched input are understood and never corrected.
*Gave up:* the warmth of replying in a student's own register.
*Bought:* alignment with what the BECE actually demands.

**12. Every kilobyte is money.**
Target under 100 KB first paint, under 20 KB per Turn, on a shared Android over
3G. That rules out heavy frameworks before the first line of frontend.
*Gave up:* rich interaction, diagrams, anything video.
*Bought:* a tutor a family can afford to let a child use daily. Measured: the
page is 3.2 KB gzipped with zero external requests, a Turn is 464 bytes, and a
ten-Turn session costs about GH¢0.00006 at GH¢6/GB. Asserted in tests, not hoped
for.

### 7.3 Measurement and honesty

**13. Five users is an anecdote, and saying so is the point.**
Five people have used this. That supports "it works and they came back", and
nothing beyond it.
*Gave up:* every outcome claim. No learning gain, no percentage improvement, no
before-and-after.
*Bought:* claims that survive the first follow-up question. The numbers worth
quoting are the ones from the offline checks — Reveal rate across logged Turns,
maths errors found in review, Indicator Coverage — because those are properties
of the system, measurable without users at all.
*Specifically avoid:* follow-up-question rate. Its direction is ambiguous even
with a real sample, and with five users it means nothing.

**18. Retrieval quality is measured against a hand-written Golden Set.**
Seventy Golden Pairs, written from the NaCCA Strands rather than from the
Retriever's output — a golden set built by accepting what the system already
returns measures nothing. Targets were chosen by reading Chunk headings and
text; five metrics are computed by hand in about sixty lines.
*Gave up:* a day of tedious work, and any claim that the judgements are
authoritative. One person wrote them, so they need engineer review exactly as
the Indicator mappings do.
*Bought:* the first honest numbers in the project, including four that are
unflattering:

| | hit@3 | What it means |
|---|---|---|
| Overall | 0.74 | A quarter of answerable questions get no relevant Citation |
| Algebra | 0.43 | The weakest Strand, and the core of JHS maths |
| Bare equations | 0.50 | nDCG 0.06 — they retrieve, but almost never the right thing |
| B8 | 0.61 | Worse than B7 (0.83) and B9 (0.86), despite holding 463 of 708 Chunks |

*Qualifies decision 15:* query expansion closed the ungrounded-reply gap in the
sense that a bare equation now returns something. It did not make that
something right. The claim is narrowed accordingly.
*Qualifies decision 5:* B8 scoring worst while holding the most Chunks points at
near-duplicate Worked Examples competing with one another, not at too little
material. More corpus would not fix it.

**19. The tutor has no Score Floor, and the Golden Set shows why that is hard.**
All five no-answer questions — bearings, sets, number bases, pictograms — were
answered with three confident Citations. A floor is the obvious fix, but the
score ranges overlap: unanswerable questions scored 0.13–0.30 and answerable
ones 0.21–0.69.

| Floor | False groundings cut | Answerable questions lost |
|---|---|---|
| 0.20 | 1 of 5 | 0 of 65 |
| 0.30 | 4 of 5 | 6 of 65 |
| 0.35 | 5 of 5 | 19 of 65 |

*Decided:* no floor yet. The free one at 0.20 buys almost nothing, and the
useful ones cost real coverage.
*Revisit:* once ranking is better, because the overlap is a symptom of weak
ranking rather than a law of nature. This is the clearest argument yet for the
phase 2 semantic retrieval in decision 5.

**20. The model provider is configuration, not architecture.**
The model's only job is to phrase a hint. Retrieval, solving, marking and
choosing the Hint Level are all deterministic Python, so the model is close to
a commodity here — which means the provider should be a one-line change, not a
rewrite. `core/llm.py` supports Fireworks and Anthropic behind the same two
functions, picked by whichever key is set, cheapest first.
*Gave up:* provider-specific features. Nothing beyond a system prompt, a user
message and a token cap is available through this seam.
*Bought:* a roughly tenfold cost reduction, and the freedom to move again. The
cheapest Fireworks serverless model is about \$0.05 in and \$0.20 out per
million tokens against Haiku's \$1.00 and \$5.00. At 464 bytes a Turn the
difference is not large in absolute terms; the point is that the constraint of
near-zero API cost is now met by configuration.
*Fireworks is called over plain HTTP,* not through a second SDK: the surface we
use is one endpoint and four fields, and `httpx2` is already present as an
`anthropic` dependency.
*Found while doing it:* Mistral, the obvious open-weights choice, no longer
appears on Fireworks' serverless pricing page, and the Mixtral variants are
marked deprecated or not serverless. Model ids are therefore treated as
unverifiable offline — `python -m core.models` lists what a key can actually
serve, and a retired id produces an error that says so rather than a generic
400.

**21. The test suite must not be able to spend money.**
`core.tutor.respond` calls the model whenever a key is configured, so simply
exporting a key turned `uv run pytest` into dozens of billed, non-deterministic
API calls. This was latent from the start and invisible only because nobody had
a key set.
*Gave up:* nothing.
*Bought:* a suite that stays free and offline. `tests/conftest.py` clears every
provider variable for every test, so the tutor tests always exercise the
template fallback, and the Fireworks request shape is pinned against a stubbed
transport instead.

**22. Reasoning is switched off, and a failed model call is not an outage.**
The first live call with a real key returned an empty string. HTTP 200, no
error: the model had spent all 400 tokens of its budget thinking, returned the
thinking in a `reasoning_content` field nothing reads, and left `content` empty.
Every cheap serverless model on Fireworks now behaves this way by default.
*Gave up:* reasoning, which this project was never buying. The model's job is to
phrase one sentence; the solving is SymPy's and the grading is ours.
*Bought:* a reply at all, and a 25x cost reduction on output — 16 tokens instead
of 400, where the thinking tokens are billed at the output rate and discarded.
`reasoning_effort: "none"` is sent on every call.
*Cost:* two of the models a key can reach are thinking-only and reject the flag
with a 400 (`glm-5p3-flash`, `gpt-oss-120b`). They are therefore unusable here
until someone wants them enough to make the flag conditional. The error quotes
Fireworks' own message so the cause is readable rather than guessed at.
*Found while doing it:* `core.tutor` called the model with no error handling, so
any provider failure — a retired id, a rate limit, a timeout on a bad line —
was a 500 for a student halfway through a problem. It now falls back to the
same template the tutor uses with no key at all, logs the traceback to the dyno,
and keeps the citations. A degraded lesson beats a broken one, and the
guardrail holds on that path because it is the same path.

### 7.4 Process

**14. Nothing the pipeline cannot trust is dropped silently.**
Every extraction failure is written to a rejects file with its page number.
*Gave up:* clean output.
*Bought:* the ability to notice. Two bugs in this project produced internally
consistent, plausible, passing output that was wrong — one rewrote an Indicator
into the wrong Class. Both were caught because failures were recorded.

---

## 8. Open questions

| Question | Blocks |
|---|---|
| Extraction audit of 20 Indicators | trust in the Skill Graph — engineer review |
| Spot-check the 124 candidate mappings | Citation quality — engineer review |
| Real RTT from an Accra connection: Frankfurt vs Johannesburg | nothing yet; settles decision 17's region |
| Spot-check the 70 Golden Pairs | trust in every number in decision 18 — engineer review |
| Why Algebra scores 0.43: LaTeX markup diluting the text, or near-duplicate Worked Examples? | the first retrieval fix worth making |

Not currently in scope, and recorded so the decision is visible rather than
forgotten: written permission from NaCCA, and anything to do with Ghana's Data
Protection Act. Both would matter if this were offered publicly or charged for.
It is a personal project used by five people, so neither is being pursued.

## 9. What comes next

Ordered by what unblocks the most.

1. **Fix Algebra retrieval**, now that decision 18 names it the weakest Strand
   at hit@3 0.43. The Golden Set will say whether a fix actually worked
2. **Basic safety wording** — tell students it is a bot, keep no names
3. **Practice questions** — generated per Indicator, verified offline
4. **Offline support** — a service worker, so a downloaded session survives the
   walk home

## 10. Changelog

| Date | Change |
|---|---|
| 2026-10-20 | First version. Captures decisions made through the working tutor |
| 2026-10-20 | Decision 15: query expansion for word-poor questions. Bare equations now retrieve |
| 2026-10-20 | Decision 16: the web page, with the Hint Ladder made visible |
| 2026-10-20 | Decision 17: Heroku via Student Pack, Europe. Johannesburg assumption corrected |
| 2026-10-20 | Rescoped: five users not fifteen, personal project not a product, engineer review not "needs a human" |
| 2026-10-29 | Deployed to Heroku, EU, Basic dyno |
| 2026-10-29 | Custom domain `edubot-africa.me` live, with managed TLS |
| 2026-10-29 | HTTPS forced in production, with HSTS |
| 2026-10-29 | Decisions 18 and 19: the Golden Set, the numbers it produced, and why there is still no Score Floor |
| 2026-10-29 | Decisions 20 and 21: Fireworks alongside Anthropic, and a test suite that cannot bill |
| 2026-10-30 | Decision 22: reasoning switched off after a live empty reply, and the tutor degrades instead of 500ing |
