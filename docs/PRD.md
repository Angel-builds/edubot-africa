# EduBot Africa — Product Requirements

**Living document.** Last updated 20 October 2026. Amend it in the same commit
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

They are **minors**, which sets the safety floor: parental consent, student
assent, pseudonymous identifiers, short retention, a named human for anything
that looks like a crisis, and maths-only scope with no companionship behaviour.

## 3. The problem

Classroom time per student is thin and private tutoring costs money most
families do not have. Students get stuck in the evening with nobody to ask.

Generic chatbots are available and actively unhelpful here: they answer in US
conventions, they do not know the Ghanaian curriculum, and — the part that
matters — they hand over answers, which measurably damages independent
performance (see decision 2).

## 4. What success looks like

Honest about what a 15-student Pilot can and cannot show.

| Measure | Target | Why this one |
|---|---|---|
| Reveal rate | ~2% of Turns | The benchmark from the Sierra Leone trial. Directly measures the core guardrail |
| Grounded replies with a valid Citation | high, measured | A tutor citing nothing is just a chatbot |
| Maths errors in teacher-reviewed numeric claims | 0 | Teaching wrong maths to a child is the worst failure available |
| Uncovered Indicators | known and shrinking | An Uncovered Indicator is one the tutor cannot teach |
| Session completion, unprompted return | measured | Engagement is the demonstrated failure mode in this market |

**Not a success measure:** anything causal about learning. See decision 13.

## 5. Non-goals

- Subjects beyond maths during the Pilot. The architecture carries `subject` on
  every record so Science is an ingest run, but it is not in scope now.
- Replacing a teacher. Every positive result in this field came from a
  supervised, timetabled deployment with an adult present.
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
| Retrieval | **Minimal.** In-memory, lexical. Bare equations now retrieve, topically |
| API | `/health`, `/chat` |
| Interface | CLI only. No web app yet |
| Deployment | Not deployed |
| Safety and consent | **Not started.** Blocks the Pilot |
| Extraction audit | **Not started.** Needs a human |

Runs today with no API key: replies show the coaching step instead of prose.

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
*Bought:* a project that can be public, and later commercial, without a
licensing problem. A schema check enforces it rather than trusting discipline.
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
*Gave up:* mapping quality. Every mapping is a candidate needing human review.
*Bought:* an honest Coverage report. At a permissive threshold every Indicator
appeared Covered, which was false confidence — a method reporting no gaps
against another country's curriculum is broken, not thorough.

**7. Siyavula CC BY, not Khan Academy or OpenStax.**
Grades 7–9 line up with B7–B9, and the licence permits adaptation and commercial
use. Khan Academy and most OpenStax titles are CC BY-**NC**.
*Gave up:* volume, and South African sequencing that does not match Ghana's.
*Bought:* a corpus with no licence ceiling on what the project can become.

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
*Bought:* a tutor a family can afford to let a child use daily.

### 7.3 Measurement and honesty

**13. The Pilot is a feasibility study, and we will say so.**
Fifteen students cannot support a causal claim about learning. The statistics
live in the offline evaluation, where n is 200–400 items rather than 15 people.
*Gave up:* the headline. "Improved learning outcomes by X%" is not available.
*Bought:* claims that survive being questioned. Reveal rate across logged Turns,
and maths errors in teacher-reviewed claims, are defensible numbers.
*Note:* Follow-up Clarification rate is ambiguous in direction — fewer can mean
clearer explanations or a disengaged student. If reported, it is reported with
that caveat and a confidence interval.

**15. Word-poor questions are expanded from their own structure.**
An equals sign beside a letter means solving for an unknown; a slash between
digits means fractions. Those words are added to the query when the student's
question has almost none of its own.
*Gave up:* precision. The added terms are topical, so the Citation is about the
right area rather than the right paragraph.
*Bought:* Grounded replies for the most common question a student asks — a bare
equation — with no database and no embeddings. Expansion only fires below two
indexable words, so ordinary questions score exactly as before.
*Guarded by:* a test asserting every term it can emit exists in the corpus. A
term the corpus has never seen contributes nothing, and silently achieving
nothing is the failure this is most at risk of.

### 7.4 Process

**14. Nothing the pipeline cannot trust is dropped silently.**
Every extraction failure is written to a rejects file with its page number.
*Gave up:* clean output.
*Bought:* the ability to notice. Two bugs in this project produced internally
consistent, plausible, passing output that was wrong — one rewrote an Indicator
into the wrong Class. Both were caught because failures were recorded.

---

## 8. Open questions

| Question | Blocks | Owner |
|---|---|---|
| Written permission from NaCCA | commercial use, not the Pilot | Angel |
| Who reviews the 124 candidate mappings | citation quality | Angel |
| Extraction audit of 20 Indicators | trust in the Skill Graph | Angel, needs a human |
| Consent wording, and the named safeguarding adult | the Pilot, hard blocker | Angel |
| Ghana Data Protection Act registration | deployment beyond a consented family Pilot | needs local advice |
| Supabase account and region | phase 2 | Angel |

## 9. What comes next

Ordered by what unblocks the most.

1. **A web interface** — students cannot use a CLI
2. **Deploy** — a URL, so the Pilot can happen at all
3. **Golden set and evaluation** — makes every later change measurable, and
   would tell us whether expansion helps precision or only recall
4. **Safety and consent** — hard blocker on the Pilot
5. **Practice questions** — generated per Indicator, verified offline

## 10. Changelog

| Date | Change |
|---|---|
| 2026-10-20 | First version. Captures decisions made through the working tutor |
| 2026-10-20 | Decision 15: query expansion for word-poor questions. Bare equations now retrieve |
