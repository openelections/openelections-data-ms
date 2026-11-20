# 2026 general — text-layer conversion notes (2026-11-20, Task 9)

Four counties of the 2026-11-03 Mississippi general election are converted
from the SoS "Official Recapitulation" county PDFs with the text-layer
pipeline (`src/extract_2026_general_text_pdf.py`, `src/batch_extract_2026_general_text.py`):

| county | rows x precincts | CSV data rows | operator cells applied | how the manifest drives it |
| --- | --- | --- | --- | --- |
| Union | 18 x 20 | 360 | 0 | layer grid parses; operator supplies header labels only |
| Warren | 11 x 23 | 253 | 0 | layer grid parses; operator headers, carried pages, 5 cell-token repairs |
| Jasper | 11 x 13 | 143 | 154 (11 rows x 13 vote cells + 1 printed TOTAL each) | whole grid operator-read |
| Lee | 17 x 33 | 561 | 578 (17 rows x 33 vote cells across three 11-column groups + 17 printed TOTAL reads) | whole grid operator-read |

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
identified, all clean: 0 roster problems.

These four per-county files are gated on internal PDF reconciliation only and
have **not** been checked against official county totals; when a 2026 general
statewide recap PDF becomes available, build the official county CSV and
re-verify all four.

## Next phase

The remaining 78 county PDFs (82 in
`~/code/openelections-sources-ms/2026/general/` minus these four) are scanned
images: per `CLAUDE.md`, convert them with PaddleOCR-VL via the AI Studio
cloud endpoint (whole-PDF async job, per-page markdown, pattern from
`openelections-data-al`), reusing this pipeline's gates and manifest shape —
token repairs and operator rows referee whatever the OCR markdown still
misreads, and `batch_extract_2026_general_text.py`'s status.json/resume and
roster-gate shape carries over to the scan phase's runner.
