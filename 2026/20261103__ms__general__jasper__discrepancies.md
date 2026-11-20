# Jasper 2026 general — operator-grid discrepancy report (2026-11-19, Task 8)

Status: **RESOLVED-BY-PRINT (adjudicated 2026-11-19).** The coordinator read
the render directly (`jas_p2_sullivan_b.png`: 242 | 765 | 283 | 369 | 170,
unambiguous) and the printed-TOTAL referee agrees (only 283 yields
Σ = 4984); the adjudicated value 283 is in the manifest's Sullivan
`operator_rows` entry, and the county CSV was generated from the whole-grid
conversion. The report below is the pre-adjudication evidence, kept as the
record of why the cell changed.

The original plan was to convert the
whole Jasper grid to `operator_rows` (the p2/p3 layer digits are corrupt
beyond token repairs) and generate the CSV. Before writing any manifest rows,
every page strip was re-rendered and each row's cross-page cell sum was
checked against its printed county TOTAL. Ten of the eleven rows reconcile
exactly and every one of their 143 printed cells matches the grid. **One
cell does not**: Matthew G. Sullivan's Holders cell. Nothing was written
into `2026/header-reads/20261103__ms__general__jasper__headers.json` for the
other ten rows and the PDF/CSV was not regenerated; the manifest is
byte-identical to commit 7247589, still carrying only the Sorey
`operator_rows` entry.

## The cell

| | value |
| --- | --- |
| office / district / seat | Circuit Court, district 13, Place 1 (Matthew G. Sullivan, Nonpartisan) |
| page / column index | p2, position 5 (label `Holders`) |
| grid value (prior phase) | **280** |
| printed value (re-read this session) | **283** |
| printed county TOTAL (p3 TOTAL column) | 4984 |
| row sum with the grid's 280 | 4981 (3 short) |
| row sum with the printed 283 | **4984 (exact)** |

Render evidence (this session, committed nowhere — `cache/` is gitignored):

- `cache/2026-general-text/operator-verify/jasper/jas_p2_sullivan_b.png` —
  Sullivan's full 600 dpi row strip (p2 columns Claiborne/Montrose incl.
  Holders): reads `242 | 765 | 283 | 369 | 170`.
- `cache/2026-general-text/operator-verify/jasper/jas_p2_sullivan_holders_1200.png`
  — the cell at 1200 dpi, unambiguous `283`.
- Font references from the same column at the same zoom (finaldigit glyph
  contrast): `jas_p2_lee_holders_1200.png` (280), `jas_p2_martin_holders_1200.png`
  (282), `jas_p2_shoemake_holders_1200.png` (280). The '3' glyph in Sullivan's
  cell is the open double-loop 3, not the closed oval 0 printed two rows away
  in Lee/Shoemake — this is not a scan artifact or a misread 0.
- Arithmetic anchor: the row's own printed TOTAL (p3 TOTAL column, 4984) is
  the referee. Only 283 makes the 13 cells plus the two p3 cells sum to it
  (4050 + 934). The independent Sorey row on the same column group (p4, same
  Holders cell position) prints 280 and reconciles at 4945, so the column
  rule/geometry is not the culprit.

## The verdict table (11 rows, 143 cells, 600 dpi re-read)

Every row's printed TOTAL is the last column of its p3/p5 strip; cells sum
from p2 (11 columns) plus p3 (Rose Hill, Stringer):

| candidate | printed TOTAL | this re-read | verdict |
| --- | --- | --- | --- |
| Scott Colom | 3488 | 3488 (3184 + 304) | reconciles |
| Cindy Hyde-Smith | 2609 | 2609 (1803 + 806) | reconciles |
| Ty Pinkins | 108 | 108 (85 + 23) | reconciles |
| Michael A. Chiaradio | 3383 | 3383 (3102 + 281) | reconciles |
| Michael Guest | 2736 | 2736 (1896 + 840) | reconciles |
| Erik Klehle | 51 | 51 (45 + 6) | reconciles |
| Roy Noble Lee Jr. | 4951 | 4951 (4028 + 923) | reconciles |
| Gerald M. Martin | 4952 | 4952 (4036 + 916) | reconciles |
| David Shoemake | 4970 | 4970 (4042 + 928) | reconciles |
| Matthew G. Sullivan | 4984 | **4981** with the grid's 280 / **4984** with the printed 283 | **discrepancy** |
| Stanley Sorey | 4945 | 4945 (4008 + 937; p4/p5 operator row, re-confirmed) | reconciles (already in the manifest) |

Full-page orientation renders: `jas_p2_full300.png`, `jas_p3_full300.png`,
`jas_p4_full300.png`, `jas_p5_full300.png`; the four 600 dpi strips per row
(`jas_p2_<candidate>_{a,b,c}.png`, `jas_p3_<candidate>_t.png`) and Sorey's
(`jas_p4_sorey_{a,b,c}.png`, `jas_p5_sorey_t.png`) carry the cell reads.

## Why the pipeline stopped instead of writing

The printed-TOTAL gate would hold the county with the grid's 280 (sum 4981
vs the row's own printed total 4984), and the constraint that operator
values are not edited by the parser-side work leaves the alternative —
substituting the printed 283 — as an operator decision. The two readings
disagree by exactly one digit and only the printed one is self-consistent,
so the requested adjudication is: accept the printed 283 (the evidence
supports it), after which the ten remaining rows can be converted to
`operator_rows` and the county gates clean.
