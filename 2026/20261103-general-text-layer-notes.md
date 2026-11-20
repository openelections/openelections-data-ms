# 2026 general — text-layer conversion notes (2026-11-20, Task 9)

Ten counties of the 2026-11-03 Mississippi general election are converted
from the SoS "Official Recapitulation" county PDFs with the text-layer
pipeline (`src/extract_2026_general_text_pdf.py`, `src/batch_extract_2026_general_text.py`)
— four with usable text layers, six pure image scans run operator-vision
(Issaquena the pilot, then the six-county phase, sections below), all riding
the same pipeline and batch runner:

| county | rows x precincts | CSV data rows | operator cells applied | how the manifest drives it |
| --- | --- | --- | --- | --- |
| Union | 18 x 20 | 360 | 0 | layer grid parses; operator supplies header labels only |
| Warren | 11 x 23 | 253 | 0 | layer grid parses; operator headers, carried pages, 5 cell-token repairs |
| Jasper | 11 x 13 | 143 | 154 (11 rows x 13 vote cells + 1 printed TOTAL each) | whole grid operator-read |
| Lee | 17 x 33 | 561 | 578 (17 rows x 33 vote cells across three 11-column groups + 17 printed TOTAL reads) | whole grid operator-read |
| Issaquena (scan pilot) | 10 x 5 | 50 | 60 (10 rows x 5 vote cells + 1 printed TOTAL each) | whole grid operator-read; raw portrait render |
| Sharkey (scan) | 10 x 10 | 100 | 110 (10 rows x 10 vote cells + 1 printed TOTAL each) | whole grid operator-read; ROTATE_270 |
| Noxubee (scan) | 10 x 7 | 70 | 80 (10 rows x 7 vote cells + 1 printed TOTAL each) | whole grid operator-read; ROTATE_90 |
| Quitman (scan) | 11 x 10 | 110 | 104 (8 full rows x 10 cells, 2 X-cell rows on partials, Webster row on p3) | whole grid operator-read; landscape-genuine sheet |
| Benton (scan) | 19 x 5 | 95 | 114 (19 rows x 5 vote cells + printed TOTALs across p2/p3) | whole grid operator-read; two-page extension table; ROTATE_270 |
| Claiborne (scan) | 10 x 12 | 120 | 140 (10 rows x 12+2 cells + printed TOTALs on both pages) | whole grid operator-read; landscape-genuine sheet |
| Humphreys (scan) | 10 x 13 | 130 | 150 (10 rows x 11+2 cells + printed TOTALs on both pages) | whole grid operator-read; two-page extension table; ROTATE_90 |

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
batch stage then re-parses every county and runs the cross-county roster
gate (`check_roster_shared_races`): every (office, district) race two or
more counties print must carry the identical (candidate, party) roster —
U.S. Senate (all eleven), U.S. House 1 (Benton + Lee + Union), House 2
(six counties), House 3 (Jasper + Noxubee), Court of Appeals 1 (Benton +
Lee + Union) and Court of Appeals 2 Place 1 (six counties), Chancery Court
Places 1-4 district 1 (Lee + Union). All identical rosters read clean. The
eleven-county batch carries exactly three advisory records and zero
blocking ones: two `roster_subset` chains (Circuit Court 9: Warren
[Terrett, Chaney] vs Issaquena/Sharkey [Terrett]; Circuit Court 3: Benton's
six-candidate roster vs Union's five) and one `roster_divergence_accepted`
(Chancery Court 9 — the disjoint place partition, next section).

All ten per-county files are gated on internal PDF reconciliation only and
have **not** been checked against official county totals; when a 2026 general
statewide recap PDF becomes available, build the official county CSV and
re-verify all ten.

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

## Scan-county phase: Sharkey, Noxubee, Quitman, Benton, Claiborne, Humphreys

Six Tier-0 scan counties converted with the Issaquena recipe (no OCR; the
operator reads the renders and the manifests supply the grids wholesale).
Each is a 3-page sheet: p1 the certification/signature block (declared
`local_only_pages`), p2 a table page, p3 either all-local rows (Sharkey:
School Board 5 + Election Commissioner District 1; Noxubee: Supervisor 02 +
Constable S-Southern District) or a table continuation over the same
precinct columns (Benton: 5 precincts on both pages; Claiborne: 11 + the
5-B tail; Humphreys: 11 + the Putnam/Silver City tail; Quitman: the
continuation row + local sections). Every row's cross-page cell sum
referees against its printed county TOTAL on the sheet where the row prints
(19/19 rows on the two-page counties); `run_gates`: 0 problems per county;
the batch re-ran all eleven counties clean.

**Orientation families confirmed.** The two transposes the assessment
predicted, now pinned per county: Sharkey/Benton rotate upright with
ROTATE_270, Noxubee/Humphreys with ROTATE_90, and Quitman/Claiborne are
LANDSCAPE-GENUINE sheets (the raw 2420x1870 render reads upright directly,
no transpose). Render evidence: `cache/2026-scan-assessment/six/` and its
`verify/` strips.

**The Quitman catch — the whole-section loss the per-row gate can't see.**
The in-session transcription read p3 as all-local, but the name-strip re-read
exposed a section header box as p2's LAST row block: "Circuit Court
11-3-Circuit District 11-3" prints with no rows under it, and its candidate
row (Charles E. Webster, Nonpartisan) starts p3 above the local zone — the
Warren p5/p7 section-continuation pattern. Its row is all zeros and X marks
(Crenshaw/Crowder/District 3 North/District 3 South/North Lambert/North West
Marks/Sledge print 0; Lambert/South West Marks/West Lambert print X), TOTAL
0 — in scope (Circuit Court is a kept office) and invisible to every
arithmetic gate, because a wholly missing section breaks no row's own TOTAL.
Both Circuit 11-2 rows (Stephanie 'Nikki' Morris-Harris, David L. Tisdell)
print X in every column but Lambert, South West Marks and West Lambert; only
those cells plus the printed TOTAL are supplied and the X-marked blanks
become 0 under the row's own printed TOTAL (109+100+118 = 327; 51+77+79 =
207). Lesson applied to the remaining tiers: every declared-local or
trailing page must be checked for continuation rows before it is labeled
local-only, and any section header whose rows are absent on its own page
needs its continuation page found.

**Two pages, one row? No — two pages, same rows.** Benton, Claiborne and
Humphreys' p3 tables REPRINT the whole roster under the same section
headers for their tail columns: the operator_rows carry cells on both
supply pages, and both printed TOTAL columns are supplied (they agree per
row; agreeing duplicates record no conflict).

**The Benton late-header-box adjudication (Circuit D3 seat pairing).**
Benton's p3 prints its section header boxes ONE ROW BLOCK LATE —
Shackelford/Watts above the "Chancery Court 18-… Place 2" box, Bob Whitwell
above the "Circuit Court 3-… Place 1" box, Gray Tollison above "Place 2",
and the "Place 3" box mid-block between Steven Patrick Jubera and Kent E.
Smith. Read as printed, Benton pairs Circuit District 3 as Place 1 =
Whitwell, Place 2 = Tollison, Place 3 = Adams + Byers + Jubera + Smith;
Union's sheet (text layer, re-verified from its own p4 render) pairs the
same roster as Place 1 = Tollison, Place 2 = Adams/Byers/Jubera, Place 3 =
Smith, with no Whitwell section at all. Both pairings are kept per-county
as printed (the source-fidelity convention), documented in Benton's
manifest; the family-level roster gate records the difference as an
advisory `roster_subset` (Benton's roster is Union's plus Whitwell, so the
union IS printed by a county). Chancery 18's split is unambiguous: Place 1
complete on p2 (Jenessa Carter Hicks, Sarah J. Liddy), Place 2's rows carry
to p3 (Jennifer L. Shackelford, Michael Watts).

**Chancery District 9 — the disjoint place partition (first
roster_divergence_accepted).** Humphreys' portion of Chancery District 9
elects Place 1 only (Bennie L. Richard, sole candidate); Warren/Issaquena/
Sharkey's portions elect Place 2 only (Vicki Roach Barnes, Penny B.
Lawson). No county prints both Places, so the seat-blind (office, district)
family gate sees two incomparable rosters — neither a subset of the other's
— which it reports as a blocking `roster_mismatch`. It is not a reading
error: every county's own recap prints exactly its ballot's Place, all
under one certified district, and every row's TOTAL arithmetic verifies
against its own sheet. The batch gained the manifest-declared acceptance
(`accepted_roster_divergences: [{office, district, note}]`, declared in
Humphreys' manifest with the full rationale; the runner downgrades the
matching record to an advisory `roster_divergence_accepted` with the
original rosters kept on the record as evidence and attached to
status.json). This shape will recur across the judicial districts
(Chancery 8 Harrison/Hancock, D4 Adams/Amite, and others), so future scan
counties whose sheet prints a disjoint place of a shared district declare
it the same way.

**Printed-name corrections from the verify reads** (the roster gate's
exact-string comparison would have caught the shared-race divergences):
Noxubee's Circuit 16 Place 2 candidate prints "Lee J. 'Jay' Howard" (quoted
nickname, not "Lee J. Jay Howard"); Claiborne's Circuit D7 candidate prints
"Tomika T. Harris-Irving" (not "Tonika"); Benton's Chancery 18 Place 1
prints "Jenessa Carter Hicks" (not "Janessa"). The shared-race rosters
(U.S. Senate, House 1/2/3, Court of Appeals 1 and 2 Place 1) verified
IDENTICAL to the committed counties' strings, which is also an independent
check on the transcriptions: the batch's three advisory records are exactly
the ones predicted before the run.

The remaining 71 scan counties follow the same operator-read route (tier
order in `2026/20261103-general-scan-counties-assessment.md`; Hinds last).

## Next phase

The remaining 71 county PDFs (82 in
`~/code/openelections-sources-ms/2026/general/` minus the eleven converted so
far) are scanned images, taken in the assessment's tier order. The Issaquena
pilot shows the operator-read route works end to end; whether PaddleOCR-VL
via the AI Studio cloud endpoint (whole-PDF async job, per-page markdown,
pattern from `openelections-data-al`) joins the ladder is deferred until
operator-only costs force it, reusing this pipeline's gates and manifest
shape — token repairs and operator rows referee whatever an OCR/visual read
still misreads, and `batch_extract_2026_general_text.py`'s
status.json/resume and roster-gate shape (with both advisory classes —
roster_subset and the manifest-accepted roster_divergence — carries over)
runs the scan phase's runner.
