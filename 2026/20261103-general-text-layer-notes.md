# 2026 general — text-layer conversion notes (2026-11-20, Task 9)

Four counties of the 2026-11-03 Mississippi general election are converted
from the SoS "Official Recapitulation" county PDFs with the text-layer
pipeline (`src/extract_2026_general_text_pdf.py`, `src/batch_extract_2026_general_text.py`)
— plus the first scan-county pilot (Issaquena, section below), whose CSV
and operator manifest ride the same pipeline and batch runner:

| county | rows x precincts | CSV data rows | operator cells applied | how the manifest drives it |
| --- | --- | --- | --- | --- |
| Union | 18 x 20 | 360 | 0 | layer grid parses; operator supplies header labels only |
| Warren | 11 x 23 | 253 | 0 | layer grid parses; operator headers, carried pages, 5 cell-token repairs |
| Jasper | 11 x 13 | 143 | 154 (11 rows x 13 vote cells + 1 printed TOTAL each) | whole grid operator-read |
| Lee | 17 x 33 | 561 | 578 (17 rows x 33 vote cells across three 11-column groups + 17 printed TOTAL reads) | whole grid operator-read |
| Issaquena (scan pilot) | 10 x 5 | 50 | 60 (10 rows x 5 vote cells + 1 printed TOTAL each) | whole grid operator-read; raw portrait render |

Every per-county CSV regenerates byte-identical from its manifest at every
Task 9 boundary (`cmp` verified).

## Method evolution

* **Where the text layer works** the grid is deterministic geometry
  (natural_pdf word/char geometry, no OCR, no vision model): find_table_top's
  floors find the data block, cells bind to detected column centers, merged
  row blocks and cross-page office carry reassemble the multi-page rolling
  crosstab. Union is the pure case; Warren the same plus the narrow-tail
  retry its two narrow column tails (p4/p7, Porters Chapel + TOTAL) needed,
  the `carry_pages` declaration for the Circuit Court 9-2 row group, and 5
  render-verified `cell_token_repairs`.
  **Amendment A: header labels are never read from geometry** — in every case
  the county's operator header manifest
  (`2026/header-reads/20261103__ms__general__<county>__headers.json`) names
  each page's columns left-to-right, read by the operator-vision pass
  (`read_by: operator-vision`, 300 dpi header strips with 600 dpi zooms;
  paths under the manifests' `procedure`/notes).
* **Where the layer's digits are corrupt** (Jasper, Lee: an OCR text layer
  whose cells decode as junk or letter debris) the manifest declares
  `operator_supply_pages` and supplies every row as `operator_rows` keyed on
  the declared labels — identity from the printed ballot, cells from the page
  renders, each row's cross-page cell sum refereed against its printed county
  TOTAL. Jasper's parse is fully supplied (p2-p5); Lee's is fully supplied
  (p2-p9, its remaining pages declared `local_only_pages`).
* **Render evidence** lives under the gitignored `cache/2026-general-text/`
  (header strips, `operator-verify/<county>/` per-row strips at 600 dpi, 800-1300 dpi
  cell zooms), referenced from the manifests' notes so every value's read is
  reproducible.

## The Sullivan 283 adjudication (Jasper)

The prior phase's reference grid misread Matthew G. Sullivan's Holders cell
as 280; the print reads 283 (600/1200 dpi renders) and only 283 makes his row
sum to the printed county TOTAL 4984 (4050 + 934). The cell was adjudicated
to the printed 283 and the row reconciles; Stanley Sorey's Holders 280 is
unmoved (his own row arithmetic is exact, 4945). Full evidence and the
verdict table for all 11 rows:
`2026/20261103__ms__general__jasper__discrepancies.md` (resolved-by-print).

## X cells — position evidence, never values

A body cell printed `X` (common on the local-races tables, occasionally
in-scope) reads as **column-position evidence only, never a votes value**: no
number is invented for it, and a blank becomes 0 only when that row's printed
TOTAL equals the sum of its present cells (the blank-is-zero rule the
printed-TOTAL gate referees). Warren's manifest states the same rule for
Chaney's X cell.

## Local-office rows

Local-office rows are out of scope by the repo's no-local-offices convention
and leave the parse loudly, never silently: Union dropped 2 rows, Warren 19,
both recorded whole under `dropped_local_rows` (Warren's p5/p6 also carry the
local-races table — the sections' rows drop via the unknown-header route).
Jasper's and Lee's local tables sit on operator-supplied/declared-local
pages, so their skips are recorded as page scope (`skipped_local_pages` /
`operator_supply_pages`) rather than row drops.

## Gating (internal only)

Each county passed the pipeline's internal reconciliation: per-candidate
precinct cells sum to the manifest-designated printed TOTAL column, every
label/center alignment is exact, and `run_gates` reports zero problems (the
CSV is withheld otherwise — `main()` never writes past a held gate). The
batch stage then re-parses all four counties and runs the cross-county
roster gate (`check_roster_shared_races`): every (office, district) race two
or more counties print must carry the identical (candidate, party) roster —
U.S. Senate (all four), U.S. House 1 and Court of Appeals Position 1/2
(Lee + Union), Chancery Court Places 1-4 district 1 (Lee + Union). All
identified, all clean: 0 roster problems. The Issaquena pilot then adds the
gate's first advisory `roster_subset` record (Circuit District 9 against
Warren) — with the five-county batch, a family whose rosters form a strict
subset chain records advisory rather than blocking ("Scan-county pilot:
Issaquena" below).

These four per-county files are gated on internal PDF reconciliation only and
have **not** been checked against official county totals; when a 2026 general
statewide recap PDF becomes available, build the official county CSV and
re-verify all four. The Issaquena pilot sits in the same position: gated on
its manifest's printed TOTALs, awaiting the same official cross-check.

## Scan-county pilot: Issaquena

The first county of the 78-scan phase (the assessment's Tier-0 pilot; no OCR
run — the operator reads as a vision model, PaddleOCR-VL deferred): a pure
image scan with zero embedded text characters, converted wholesale by an
operator-vision read of the rendered pages. The sheet is 3 pages: p1 the
certification banner/signature block, p2 one portrait crosstab carrying the
whole grid (5 precincts + the printed TOTAL column, banner printed on the
sheet itself), p3 all-local rows (Election Commissioner Districts 1/2/5 — out
of scope; p1 and p3 are the declared `local_only_pages`, the run's 2 skipped
local pages; a local Tax Assessor Collector section on p2 prints no candidate
rows beside it). The raw portrait render reads directly — no transpose needed
for p2 (p1's signature block runs the other way, skipped regardless).

Shape: 10 candidate rows x 5 precincts = 50 data rows, 60 operator cells (10
rows x 6 cells: 5 precinct cells + 1 printed TOTAL each; every row's cell sum
equals its printed TOTAL exactly). Races: U.S. Senate (Colom/Hyde-Smith/
Pinkins), U.S. House 2 (Eller/Bennie G. Thompson/Foster), Court of Appeals 2
Place 1 (McDonald), Chancery Court 9-2 (Barnes, Lawson), Circuit Court 9-1
(Terrett). `run_gates`: 0 problems; the CSV regenerates byte-identical from
its manifest at the --force batch.

**Circuit D9 roster_subset adjudication.** The cross-county roster gate's
first advisory record: Warren's Circuit District 9 ballot carries Place 1
(Toni Walker Terrett) and Place 2 (M. James 'Jim' Chaney Jr.); Issaquena's
sheet prints only the Place 1 section — no P2 section appears on it at all.
Issaquena's roster is a strict subset of Warren's, so the refined gate
classifies the family as `roster_subset` (advisory: printed and stored in
status.json, but not blocking) rather than a `roster_mismatch`; every other
shared race reads identical rosters. Warren's Place 2 rows stay Warren's own.

The remaining 77 scan counties follow the same operator-read route (tier
order in `2026/20261103-general-scan-counties-assessment.md`; Hinds last).

## Next phase

The remaining 77 county PDFs (82 in
`~/code/openelections-sources-ms/2026/general/` minus the five converted so
far) are scanned images, taken in the assessment's tier order. The Issaquena
pilot shows the operator-read route works end to end; whether PaddleOCR-VL
via the AI Studio cloud endpoint (whole-PDF async job, per-page markdown,
pattern from `openelections-data-al`) joins the ladder is deferred until
operator-only costs force it, reusing this pipeline's gates and manifest
shape — token repairs and operator rows referee whatever an OCR/visual read
still misreads, and `batch_extract_2026_general_text.py`'s
status.json/resume and roster-gate shape (with its advisory roster_subset
class) carries over to the scan phase's runner.
