# EduBot Africa

A maths tutor for Ghanaian Junior High School students, grounded in the national
curriculum. These are the words we use — in conversation, in the PRD, in commit
messages, and in the code. If a word here appears in the codebase meaning
something else, the code is wrong.

## Language

### The curriculum

**Strand**:
One of the four broad areas of JHS maths: Number, Algebra, Geometry and
Measurement, Handling Data.
_Avoid_: topic, section, unit

**Sub-strand**:
A named area within a Strand, such as "Fractions, Decimals and Percentages".
There are twelve.
_Avoid_: subtopic, chapter

**Content Standard**:
What a student should know by the end of a Sub-strand. There are 57.
_Avoid_: objective, outcome, goal

**Indicator**:
A single teachable skill belonging to a Content Standard — the smallest unit the
tutor works with. There are 178.
_Avoid_: learning outcome, competency, skill

**Indicator Code**:
The curriculum's own identifier for an Indicator, such as `B7.1.1.1.3`, reading
as Class.Strand.Sub-strand.Standard.Indicator.
_Avoid_: id, reference, tag

**Class**:
A JHS year group: B7, B8 or B9.
_Avoid_: grade (that word belongs to the Siyavula source, not to Ghana), year

**Skill Graph**:
The whole curriculum as a queryable hierarchy of Content Standards and
Indicators. It holds codes, short titles and structure — never curriculum prose.
_Avoid_: taxonomy, tree, curriculum map

### The content

**Chunk**:
One passage of openly licensed teaching prose, with the headings it sat under
and the licence it came with. The unit the tutor retrieves and cites.
_Avoid_: passage, extract, snippet, document, result

**Citation**:
A Chunk shown to the student as the basis for what the tutor said.
_Avoid_: source, reference

**Attribution**:
The exact credit line a Chunk's licence requires us to display.
_Avoid_: credit, byline

**Coverage**:
Whether an Indicator has any Chunk that teaches it. An Indicator with no Chunk
is **Uncovered**, and the tutor cannot teach it.
_Avoid_: mapped, matched, linked

### The tutoring

**Turn**:
One exchange: what the student said, and what the tutor said back.
_Avoid_: message, interaction, round

**Attempt**:
A student's proposed answer to the question in play.
_Avoid_: response, submission, guess

**Hint Ladder**:
The five escalating degrees of help, from "what have you tried?" up to a full
worked solution. A student climbs it by failing, never by asking.
_Avoid_: scaffold, levels, steps

**Hint Level**:
How far up the Hint Ladder this student has climbed for the current question,
0 to 4.
_Avoid_: level (ambiguous — see Node Kind), stage, depth

**Node Kind**:
Whether a Skill Graph entry is a Content Standard or an Indicator.
_Avoid_: level, type

**Reveal**:
Giving the student the final answer. Only permitted at the top of the Hint
Ladder. The share of Turns that Reveal is a headline quality measure.
_Avoid_: solve for them, give away, tell

**Worked Answer**:
The answer computed privately, used to mark an Attempt. It is never placed in
the tutor's prompt, so the tutor cannot Reveal what it was never given.
_Avoid_: solution, key, ground truth

**Symbolic Equivalence**:
Judging `1/2`, `0.5` and `2/4` to be the same Attempt. How marking is done.
_Avoid_: fuzzy match, normalisation

**Grounded**:
A tutor reply is Grounded when what it claims is traceable to a retrieved Chunk.
_Avoid_: sourced, backed, supported

### The evaluation

**Golden Set**:
A fixed list of questions paired with the Chunks that ought to answer them,
written by hand so that a change to retrieval can be measured instead of
guessed at. Seventy Golden Pairs.
_Avoid_: test set, benchmark, eval set

**Golden Pair**:
One question in the Golden Set, together with every Chunk judged relevant to
it and how relevant each one is. A Golden Pair with no relevant Chunk is a
question the corpus cannot answer, and the correct behaviour there is to cite
nothing at all.
_Avoid_: example, case, sample

**Relevance Grade**:
How useful a Chunk is to a Golden Pair's question: 2 if it teaches the skill
being asked about, 1 if it is the same topic and genuinely useful.
_Avoid_: label, rating, score (a score is the Retriever's, not a judgement)

**Score Floor**:
A minimum retrieval score below which a Chunk is not cited at all. There is
none yet; deciding where one should sit is part of what the Golden Set is for.
_Avoid_: cutoff, threshold (threshold belongs to Indicator mapping)

### The pilot

**Pilot**:
The handful of people — five so far, from a family and community network — who
have actually used it. A sanity check that it works for real students, not a
study of whether it teaches.
_Avoid_: study, trial, experiment, RCT, cohort

**Engineer Review**:
A step the pipeline cannot settle on its own, needing someone to look at the
output and judge it. Extraction accuracy and Citation quality both need one.
_Avoid_: manual check, human pass, QA
