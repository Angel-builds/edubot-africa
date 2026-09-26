# Extraction audit

Twenty indicators sampled across every strand and year group, to be checked by
hand against `corpus/raw/MATHEMATICS-CCP-B7-B9.pdf`.

This is the one check automation cannot do. Every structural assertion in
`tests/test_taxonomy.py` passes on output that is internally consistent but
wrong, and that failure mode has already occurred twice in this project: an
over-eager parent repair rewrote `B7.4.1.1.1` as `B8.4.1.1.1`, and nested-table
column rules silently discarded whole indicator titles. Both produced clean,
plausible, passing output.

**Sample:** stratified by (class x strand), 2 per cell, seed `20260926`.
Re-running the generator reproduces exactly this list.

## How to check

For each row, open the PDF at the given page and confirm:

1. The code printed on the page matches the code here.
2. The title here is the indicator's own wording, not the content standard's
   and not exemplar text.
3. The strand and sub-strand match the page's section headers.

Tick the box if all three hold. If any fail, write what you saw in Notes and
open an issue -- a single genuine mismatch means the extractor needs another
look, not a patched row.

| Code | Page | Strand | Title | OK | Notes |
|---|---|---|---|---|---|
| `B7.1.1.1.3` | 34 | Number | Round (off, up, down) whole numbers more than 1,000,000,000 to the nea | ☐ | |
| `B7.1.1.1.4` | 35 | Number | Round decimals to the nearest tenth, hundredth, thousandths, etc | ☐ | |
| `B7.2.1.1.1` | 57 | Algebra | Extend a given relation presented with and without symbolic materials  | ☐ | |
| `B7.2.3.1.1` | 71 | Algebra | Translate word problems to linear equations in one variable and vice v | ☐ | |
| `B7.3.2.1.1` | 89 | Geometry and Measureme | Calculate the perimeter of given shapes whose dimensions are in two un | ☐ | |
| `B7.3.2.3.5` | 101 | Geometry and Measureme | Convert vectors in the column (component) form to the 𝒙𝒙 Magnitude–Bea | ☐ | |
| `B7.4.1.1.3` | 109 | Handling Data | - Organise and present data from a survey into a table and/or chart, a | ☐ | |
| `B7.4.2.1.1` | 116 | Handling Data | Demonstrate understanding of likelihood of a single outcome occurring  | ☐ | |
| `B8.1.1.1.2` | 120 | Number | Skip count forwards and backwards in 10,000s, 100,000s, 500,000s, etc | ☐ | |
| `B8.1.1.1.4` | 121 | Number | Express integers of any size into standard form | ☐ | |
| `B8.2.2.1.4` | 150 | Algebra | Factorise given expressions involving the four operations and use the  | ☐ | |
| `B8.2.3.1.2` | 151 | Algebra | Solve simple linear inequalities | ☐ | |
| `B8.3.1.2.2` | 157 | Geometry and Measureme | Construct scalene triangles, isosceles triangles, equilateral triangle | ☐ | |
| `B8.3.3.1.1` | 181 | Geometry and Measureme | Understand rotation and identify real-life situations involving rotati | ☐ | |
| `B8.4.1.1.2` | 184 | Handling Data | - Select and justify a method to collect data (quantitative and qualit | ☐ | |
| `B8.4.2.1.2` | 192 | Handling Data | Express the probabilities of the events as fractions, decimals, percen | ☐ | |
| `B9.1.2.1.1` | 198 | Number | Multiply and divide given numbers by powers of 10 including decimals a | ☐ | |
| `B9.1.3.1.1` | 202 | Number | Review fractions and solve problems involving basic operations on frac | ☐ | |
| `B9.2.1.1.1` | 210 | Algebra | Construct a table of values for two linear relations and graph the rel | ☐ | |
| `B9.2.2.1.2` | 215 | Algebra | Substitute values into given formulae to evaluate it and use it to sol | ☐ | |

## Result

- Checked: ___ / 20
- Mismatches: ___
- Auditor: ___
- Date: ___

A clean audit is worth recording here, not just in a commit message: it is the
evidence that the 57 standards and 178 indicators mean what they claim.
