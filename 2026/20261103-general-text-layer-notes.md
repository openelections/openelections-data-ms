# 2026 general — text-layer conversion notes (2026-11-20, Task 9)

Forty-one counties of the 2026-11-03 Mississippi general election are converted
from the SoS "Official Recapitulation" county PDFs with the text-layer
pipeline (`src/extract_2026_general_text_pdf.py`, `src/batch_extract_2026_general_text.py`)
— four with usable text layers, thirty-seven pure image scans run operator-vision
(Issaquena the pilot, the six 3-page counties, twenty-five Tier-1 five-page
counties, Alcorn the first Tier-2 seven-page county), all riding the same
pipeline and batch runner:

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
| Adams (scan) | 13 x 19 | 247 | 246 (10 table-A rows x 19+TOTAL, 3 table-B rows x 19+TOTAL; X cells on Drake/Blackwell) | whole grid operator-read; landscape-genuine; two-table two-group split |
| Attala (scan) | 11 x 20 | 220 | 219 (10 table-A rows x 19+TOTAL, Lancaster x 19+TOTAL; X cells on McDonald) | whole grid operator-read; landscape-genuine; clean section boundary, no carry |
| Carroll (scan) | 13 x 14 | 182 | 195 (10 table-A rows x 14+TOTAL, 3 table-B rows x 14+TOTAL) | whole grid operator-read; ROTATE_270; carry row Mitchell M. Lundy Jr. |
| Chickasaw (scan) | 15 x 15 | 225 | 240 (10 table-A rows x 15+TOTAL, 5 table-B rows x 15+TOTAL) | whole grid operator-read; ROTATE_270; carry row Gray Tollison |
| Choctaw (scan) | 13 x 12 | 156 | 169 (10 table-A rows x 12+TOTAL, 3 table-B rows x 12+TOTAL) | whole grid operator-read; ROTATE_90; carry row Kiley Catledge Kirk |
| Coahoma (scan) | 12 x 18 | 216 | 186 (8 table-A rows x 18+TOTAL, 4 X-celled rows, Tisdell/Webster table-B carry) | whole grid operator-read; landscape-genuine; Circuit 11 carries Nowell + Quitman's roster |
| Copiah (scan) | 13 x 18 | 234 | 247 (10 table-A rows x 18+TOTAL, 3 Place 2 rows x 18+TOTAL) | whole grid operator-read; ROTATE_270; clean boundary |
| Covington (scan) | 12 x 15 | 180 | 192 (10 table-A rows x 15+TOTAL, 2 table-B rows x 15+TOTAL) | whole grid operator-read; ROTATE_90; two 800-dpi digit repairs |
| Franklin (scan) | 12 x 14 | 168 | 180 (10 table-A rows x 14+TOTAL, 2 table-B rows x 14+TOTAL) | whole grid operator-read; ROTATE_270; Hampton carry; no Circuit 6-1 section |
| George (scan) | 16 x 21 | 336 | 352 (11 table-A rows x 21+TOTAL, 5 table-B rows x 21+TOTAL) | whole grid operator-read; landscape-genuine; Chancery 16 has FOUR Places |
| Greene (scan) | 12 x 13 | 156 | 168 (10 table-A rows x 13+TOTAL, 2 table-B rows x 13+TOTAL) | whole grid operator-read; ROTATE_270; Tiebauer carry |
| Grenada (scan) | 16 x 13 | 208 | 190 (10 table-A rows x 13+TOTAL, 6 table-B rows x 13+TOTAL; CoA 1 X-celled) | whole grid operator-read; ROTATE_270; Chancery 3 both candidates carry |
| Holmes (scan) | 13 x 16 | 208 | 221 (11 table-A rows x 16+TOTAL, 2 table-B rows x 16+TOTAL) | whole grid operator-read; landscape-genuine; NO local sections print |
| Kemper (scan) | 10 x 14 | 140 | 150 (10 table-A rows x 14+TOTAL) | whole grid operator-read; landscape-genuine; all-local table B declared local_only |
| Lafayette (scan) | 19 x 18 | 342 | 361 (11 table-A rows x 18+TOTAL, 8 table-B rows x 18+TOTAL) | whole grid operator-read; ROTATE_90; Benton late-header shape |
| Lawrence (scan) | 13 x 13 | 169 | 182 (10 table-A rows x 13+TOTAL, 3 Place 2 rows x 13+TOTAL) | whole grid operator-read; ROTATE_90; PDF pages SHUFFLED (footer 'Page: 1' cert prints last) |
| Leake (scan) | 14 x 19 | 266 | 266 (10 table-A rows x 19+TOTAL, 4 table-B rows x 19+TOTAL; McDonald X-celled) | whole grid operator-read; ROTATE_270; Posey carry; Chancery 11 place-spread acceptance |
| Lowndes (scan) | 11 x 20 | 220 | 214 (6 table-A rows x 20+TOTAL, X-celled judicial rows, Easterling table-B) | whole grid operator-read; landscape-genuine; Circuit 16 == Noxubee; no CoA section |
| Montgomery (scan) | 16 x 14 | 224 | 208 (10 table-A rows x 14+TOTAL, 6 table-B rows x 14+TOTAL; CoA X-celled) | whole grid operator-read; landscape-genuine; Chancery 3 == x3, Circuit 5 == x5 |
| Newton (scan) | 11 x 17 | 187 | 198 (10 table-A rows x 17+TOTAL, Posey x 17+TOTAL) | whole grid operator-read; landscape-genuine; Chancery 2 == x3, Circuit 8 == Leake |
| Perry (scan) | 13 x 16 | 208 | 221 (11 table-A rows x 16+TOTAL, 2 Circuit 12 rows x 16+TOTAL) | whole grid operator-read; ROTATE_270; Chancery 13 P1/P2, Circuit 12 |
| Smith (scan) | 11 x 18 | 198 | 209 (10 table-A rows x 18+TOTAL, Sorey x 18+TOTAL) | whole grid operator-read; landscape-genuine; Chancery 2 == x4, Circuit 13 == x3 |
| Stone (scan) | 15 x 15 | 225 | 240 (11 table-A rows x 15+TOTAL, 4 Circuit 2 rows x 15+TOTAL) | whole grid operator-read; ROTATE_90; Chancery 13 == Perry; Circuit 2 has FOUR Places |
| Sunflower (scan) | 12 x 17 | 204 | 182 (10 table-A rows x 17+TOTAL, 3 X-celled Circuit 4 rows) | whole grid operator-read; landscape-genuine; Chancery 7 P2 accepted; Circuit 4 three places |
| Tate (scan) | 15 x 19 | 285 | 300 (11 table-A rows x 19+TOTAL, 4 table-B rows x 19+TOTAL) | whole grid operator-read; landscape-genuine; Chancery 3 == x4; NO local sections |
| Calhoun (scan) | 19 x 10 | 190 | 209 (11 p2 rows x 10+TOTAL, 8 p3 rows x 10+TOTAL) | single-table + table B; per-page rotations differ (p2 r90 / p3 r270); full late-header p3 |
| Jefferson (scan) | 12 x 12 | 144 | 156 (10 table-A rows x 12+TOTAL, Hampton + Harris-Irving x 12+TOTAL) | whole grid operator-read; ROTATE_90; Hampton split x3 |
| Jefferson Davis (scan) | 14 x 17 | 238 | 252 (10 table-A rows x 17+TOTAL, 4 Circuit 14 rows x 17+TOTAL) | whole grid operator-read; landscape-genuine; Circuit 14 == Copiah/Lawrence |
| Wilkinson (scan) | 12 x 9 | 108 | 120 (10 p2 rows x 9+TOTAL, Hampton + Drake p3) | single-table + 2-row table B; Chancery 4 == x4, Circuit 6-1 only |
| Alcorn (scan, Tier 2) | 17 x 17 | 289 | 306 (10 table-A rows x 17+TOTAL, 7 table-B rows x 17+TOTAL) | 7-page sheet; streak-crossed East Corinth column repaired by TOTAL arithmetic; Chancery 1/Circuit 1 == Lee |

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
U.S. Senate (all thirty-six), U.S. House 1 (eight counties), House 2
(fourteen counties), House 3 (eight counties), House 4 (George, Greene,
Perry, Stone — the same Ezell/Hulum/Boyanton roster, identical), Court of
Appeals 1 (nine counties, identical), Court of Appeals 2 Place 1
(fourteen counties), Court of Appeals 4 Position 2 (five counties,
identical), Court of Appeals 5 Position 1 (four counties, identical),
Chancery Court Places 1-4 district 1 (Lee + Union), Chancery 2 (Jasper +
Covington + Newton + Smith, identical), Chancery 3 (Carroll + Grenada +
Montgomery + Tate, identical), Chancery 4 (Adams + Franklin), Chancery 6
(Attala + Choctaw + Kemper), Chancery 7 (Quitman + Coahoma Place 1 vs
Sunflower Place 2 — accepted place spread), Chancery 13 (Perry + Stone --
Sheila Havard Smallwood Place 1 / Schmidt, John D. Smallwood, Vaughn
Place 2, identical), Chancery 15 (Claiborne + Copiah + Lawrence),
Chancery 18 (Benton + Lafayette -- identical), Circuit 5 (five counties,
identical), Circuit 8 (Leake + Newton, identical), Circuit 13 (Jasper +
Covington + Smith -- Sullivan / Sorey, identical), Circuit 14 (Copiah +
Lawrence, identical), Circuit 16 (Noxubee + Lowndes, identical), Circuit
18 (George + Greene, identical), Circuit 22 (Humphreys + Holmes,
identical). All identical rosters read clean. The thirty-six-county batch
carries exactly eight advisory records and zero blocking ones: four
`roster_subset` chains (Circuit Court 9; Circuit Court 3; Circuit 11:
Coahoma's roster adds W. Hunter Nowell Place 1 to Quitman's; Circuit 6:
Franklin prints no Place 1 section because no Franklin precinct is in
Drake's sub-district) and four `roster_divergence_accepted` records
(Chancery Court 9, 11, 14 and 7 — place spreads across the districts'
counties).

All thirty-six per-county files are gated on internal PDF reconciliation
only and have **not** been checked against official county totals; when a
2026 general statewide recap PDF becomes available, build the official
county CSV and re-verify all thirty-six.

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

## Scan-county phase: Adams, Attala, Carroll, Chickasaw, Choctaw (Tier 1's first five)

The first five of the ~35 five-page sheets (Tier 1, alphabetical), 1030 CSV
data rows, every row's cross-page cell sum refereed against its printed
county TOTAL (11-15 rows each, 65 rows verified), `run_gates` 0 problems
per county, the sixteen-county batch exit 0.

**The Tier-1 sheet anatomy.** Every one of the five is the same two-table
shape: p1 the certification/signature page (declared
`local_only_pages`), p2+p3 a table A split into column groups (11 columns,
then the remainder + the printed TOTAL column) carrying the state-office
sections, p4+p5 table B over the same column split carrying the continuation
row(s) and the local sections. Orientations pinned per county:
Adams/Attala LANDSCAPE-GENUINE (raw renders read upright directly, like
Quitman/Claiborne), Carroll/Chickasaw ROTATE_270, Choctaw ROTATE_90 —
confirming the two-transposes-plus-landscape rotation triad the assessment
predicted. SoS naming is not uniform in this tier: Adams and Choctaw ship
as `Adams_2026_general.pdf`/`Choctaw_2026_general.pdf` with no "County", so
`county_pdf` now resolves both spellings plus a unique prefix match (with a
unit test; a no-match county still reports ERROR source_missing).

**Four of five tables carry a section across the table-A/table-B boundary**
— the SEMS row-block split prints a section's header as the LAST box of
table A and its row starts table B ahead of the local zone (the Warren p5
carry pattern, seen per county): Adams' Ashunda Hampton, Carroll's Mitchell
M. Lundy Jr., Chickasaw's Gray Tollison, Choctaw's Kiley Catledge Kirk.
Attala's boundary fell cleanly BETWEEN sections (Circuit 5 Place 1's row
block completes table A; Place 2's section opens table B with its own
header) — no carry.

**The Adams adjudication — the carried row's section identified from
outside the sheet.** Adams' table B leads with "Ashunda Hampton
(Nonpartisan)" under the precinct-header zone with no header box, table A
ending at Chancery 4 Place 3's Debbra K. Halford. Her countywide
all-values pattern (no X cells, unlike the Circuit Place rows around her)
ruled Circuit out, and the independent press coverage of the campaign
(the Enterprise-Journal's "Halford, Hampton running for lone contested
chancellor's seat") identifies her as **Debbra K. Halford's opponent for
Chancery Court 4, Place 3** — the SEMS split cut the Place 3 section
between its two candidates, Halford printed in table A and Hampton carried
to table B with the header NOT repeated. Both rows' arithmetic verifies
independently (4547 / 4252), matching the reported close district race.
Adams' Chancery 4 sections are a first-year-in-district consequence of the
2025 judicial redistricting (Adams newly in Chancery District 4) — no
other converted county prints Chancery 4 yet; Amite, Franklin, Jefferson,
Pike and Wilkinson carry the same district in later tiers.

**The Chancery 14 disjoint place partition (second roster_divergence_accepted).**
Chickasaw's portion of Chancery District 14 elects Place 1 only (Rodney P.
Faver, sole candidate); Noxubee's elects Place 3 only (Paula Drungole-Ellis,
sole candidate) — the disjoint shape first adjudicated for Chancery 9,
declared under `accepted_roster_divergences` in Chickasaw's manifest.

**Chickasaw independently corroborates the Benton late-header adjudication.**
Chickasaw's Circuit 3 pairing prints EXACTLY Union's: Place 1 Gray
Tollison, Place 2 (Bart M. Adams, Shirley C. Byers, Steven Patrick Jubera),
Place 3 Kent E. Smith — and its family roster is identical to Union's, so
the roster gate adds no record. (Lafayette's sheet, converted in the next
batch, turned out to print Benton's pairing — see the third Tier-1
section: the Circuit 3 seat divergence is a two-versus-two print
difference, still per-county as printed.)

**Judicial districts crossing county lines in this batch** (all read
clean as identical rosters): Court of Appeals 1 gains Chickasaw and
Choctaw (five counties now print Derek Dewayne Hopson Jr. / John Weddle /
Donna M. Barnes); Chancery 6 (Attala + Choctaw: Doug S. Crosby / Kiley
Catledge Kirk) and Circuit 5 (Attala + Carroll + Choctaw: Joseph H. 'Joey'
Loper Jr. / Alan D. 'Devo' Lancaster) print identical rosters — the
cross-county join checks the pipeline expects on districted judicial races.
The Court of Appeals 2 Position 1 row prints X position marks on Attala's
sheet (the CoA 2 sub-district covers only part of Attala — eight of twenty
precinct columns carry values; twelve carry X), the first X-celled row in a
shared-race roster family: the X-marked blanks read as 0 under the row's
own printed TOTAL (1182+750 = 1932) and the family roster still reads
identical across the CoA-2 counties. Also of note: Chickasaw's Court of
Appeals Position 1 printed totals land on the same number (Hopson 2807,
Weddle 2807 — an exact printed tie, each row's arithmetic verified).

Sheet-scope observations recorded in the manifests: Adams' and Attala's
five-page sheets end at their last printed section (Adams at the local
County Court Judge, Attala at the Kosciusko school trustees) with no other
local sections (Election Commissioner, Coroner, Justice Court) printing on
pages 1-5 — the row stream is exactly what the sheet prints, per the
source-fidelity convention; the official-totals re-verification phase will
hold the county-level check.

## Scan-county phase: Coahoma, Copiah, Covington, Franklin, George (Tier 1's second five)

Five more five-page sheets, 1134 CSV data rows, 65 more rows refereed
against printed TOTALs (129 Tier-1 rows total), `run_gates` 0 problems per
county, the twenty-one-county batch exit 0 with six advisory roster records
(two new subsets below).

**The section-boundary variety continues to hold the sheet's shape codes.**
Three of the five fell cleanly between sections (Copiah, Covington, George);
Coahoma's and Franklin's split a section's candidates across the
table-A/table-B boundary with the header printed once at table A's end and
NOT repeated: Coahoma's Circuit 11-2 section cut between Stephanie 'Nikki'
Morris-Harris (table A) and David L. Tisdell (table B, the leading carry
row), and Franklin's Chancery 4 Place 3 section cut between Debbra K.
Halford and Ashunda Hampton — the exact split Adams' sheet printed.
Hampton's assignment is now confirmed by a SECOND county's independent
print of the same section (the press identification from the Tier-1 first
batch stands).

**Operator-read rosters now cross-validate.** Covington's sheet prints
Jasper's Chancery 2 and Circuit 13 sections under the same headers — and
the roster gate reads both families IDENTICAL (Roy Noble Lee Jr. / Gerald
M. Martin / David Shoemake; Matthew G. Sullivan / Stanley Sorey), which
independently confirms the earlier operator transcriptions of Jasper's
rosters against a county read weeks later. Coahoma likewise confirms
Quitman's Chancery 7-1 (Catherine Farris-Carter) and Circuit 11-2 (Morris-
Harris + Tisdell) and 11-3 (Charles E. Webster). This is the roster gate
doing exactly what it was built for: no arithmetic gate could have checked
one county's names against another's.

**Two 800-dpi digit repairs (operator-row form of cell_token_repairs).**
Covington's first-pass reads failed two rows' TOTAL checks: Roy Noble Lee
Jr.'s Williamsburg cell prints 187 (first-pass 167) and Gerald M. Martin's
Seminary/West Collins cell prints 988 (first-pass 986) — re-read at 800 dpi
and confirmed by each row's printed TOTAL. Both repairs are documented in
the manifest's procedure/operator_rows_note text.

**Franklin's sheet omits Circuit 6 Place 1 entirely** (no Carmen Brooks
Drake section on any page) because no Franklin precinct is inside Place 1's
sub-district — SEMS drops a place's whole section when no county precinct
votes in it, so the family roster is {Debra W. Blackwell} against Adams'
{Carmen Brooks Drake, Debra W. Blackwell}: an advisory roster_subset. The
roster_subset signal plus a missing-section note in the manifest is the
template for reading such omissions.

**George's Chancery 16 has FOUR Places on one county's sheet** (P1 with
three candidates, P2-P4 one each) and Circuit 18's two Places; the county
also opens the U.S. House District 4 family (Mike Ezell / Jeffrey Hulum
III / Carl Boyanton) and Court of Appeals 5 Position 1 (Anthony 'Tony'
Lawrence), each waiting on later tiers (Harrison, Forrest) to complete.

## Scan-county phase: Greene, Grenada, Holmes, Kemper, Lafayette (Tier 1's third five)

Five more five-page sheets, 1054 CSV data rows, 70 more rows refereed
against printed TOTALs (199 Tier-1 rows total), `run_gates` 0 problems per
county, the twenty-six-county batch exit 0 with the same six advisory
roster records.

**Lafayette prints Benton's late-header shape, not Union's — the Circuit 3
seat divergence is two-versus-two.** Lafayette's table B opens with
Shackelford/Watts (Chancery 18 Place 2's carried rows, no header above)
and then the p4 header boxes label the row blocks ABOVE them (identically
to Benton's p3 print): Circuit 3 pairs as Place 1 = Bob Whitwell, Place 2
= Gray Tollison, Place 3 = the Adams/Byers/Jubera block with Kent E.
Smith's row continuing past the mid-block Place 3 header. So the
Union/Chickasaw pairing (P1 Tollison, no Whitwell) and the Benton/Lafayette
pairing (P1 Whitwell) are TWO INDEPENDENT PRINTS EACH of the same Circuit
3 section list — the per-county-as-printed disposition stands, the
seat-blind family roster reads identical across all four Circuit 3
counties, and the existing roster_subset record is unchanged. Chancery 18's
rosters (Hicks/Liddy seat 1, Shackelford/Watts seat 2) also read identical
across Benton and Lafayette, both by seat.

**The gate caught an all-local table B.** Kemper's p4/p5 carry ONLY the
local School Board 5 section, so no operator cells exist for them — the
manifest-shape gate refused the run ("page 4 is declared operator-supplied
but no operator_cells/operator_rows entry supplies it") until the pages
were re-declared `local_only_pages` like a scan county's all-local tail.
The gate's supply-page coverage check works exactly as designed: an
operator-supply page that would silently produce nothing holds the county.

**Grenada carries BOTH Court of Appeals districts.** Its CoA 1 sections
print X position marks with values in only two precinct columns (Mt. Nebo
Young and Geeslin Friendship — the county's D1 sub-district), while the
CoA 2 row (McDonald) covers the rest (X at Mt. Nebo only; the
arithmetic-confirmed clipped Geeslin cell reads 38). The CoA 1 family
roster reads identical across seven counties; the X-celled rows' blanks
become 0 under each row's own printed TOTAL.

**Holmes' sheet carries NO local sections at all** — the five pages end at
Circuit 22's two rows (its election commissioners' signatures are on p1),
the first county whose recap prints only the state offices; recorded per
the source-fidelity convention in the manifest's local_note. Circuit 22's
roster (Tim Howard / Akillie Malone Oliver) reads identical against
Humphreys'. Holmes also prints the first 'Chancery Court 11 Place 3'
variant label form (Places 1 and 3 on the ballot, no Place 2 section).

**Carry rows this batch:** Greene's Eric Tiebauer (the Circuit 18 Place 1
section split between its candidates — Thompson in table A, Tiebauer in
table B) and Grenada's Chancery 3 Place 1 carry BOTH candidates (Miller +
Westfaul) from the p3-bottom header. Greene's Circuit 18 roster reads
identical against George's, which independently cross-confirms George's
table-B transcription; Grenada's Chancery 3 roster reads identical against
Carroll's, its Circuit 5 roster against the four Circuit 5 counties, and
Kemper's Chancery 6 roster matches Attala/Choctaw (third county).

## Scan-county phase: Lawrence, Leake, Lowndes, Montgomery, Newton (Tier 1's fourth five)

Five more five-page sheets, 1066 CSV data rows, 62 more rows refereed
against printed TOTALs (261 Tier-1 rows total), `run_gates` 0 problems per
county, the thirty-one-county batch exit 0 with seven advisory roster
records (one new: the Chancery 11 place spread).

**The first shuffled PDF.** Lawrence's five pages are NOT in SEMS order:
the PDF runs table A group 1, table A tail, table B group 1, table B tail,
then the certification page — whose own footer prints "Page: 1". The
manifest keys every page by PDF index and records the shuffle in its
procedure note; a local_only declaration also needs its page declared
under `pages` (with an empty label list) or the shape gate objects — the
Lawrence run hit exactly that on the first attempt and was fixed, no data
changes. The per-row TOTAL referee was unaffected because the manifests
key cells positionally per declared page.

**A place spread that is not disjoint — Chancery 11 gains the third
accepted-divergence shape.** Leake's recap prints Chancery 11 Place 2
only (Cynthia Lee Brewer / Rhonda Cecilia Cooper) AND the district's
shared Place 3 (Gene D. Berry / David Bridges / Alan Rhea — identical to
Holmes' P3 roster, both by seat); Holmes' portion prints Place 1 only
(Robert G. Clark III) plus the same Place 3. The three-roster family
record (Holmes / Leake / now Lowndes for Chancery 14) is accepted under
manifest-declared `accepted_roster_divergences` with the note explaining
that each county's roster = its own portions' places plus any shared ones,
the shared members reading identical. Chancery 14's accepted record now
carries Lowndes too (Lowndes prints Place 2 Studdard + the shared Place 3
Drungole-Ellis; Noxubee Place 3; Chickasaw Place 1).

**New county-line intersections, all reading identical** (the roster
gate's exact-string comparisons at work again): Lawrence's Circuit 14
roster matches Copiah's four names (Mike Taylor / Brendon Adams / Matt
Kitchens / Albert Turnage) and its Chancery 15 matches Claiborne/Copiah;
Newton's Chancery 2 matches Jasper/Covington's three names and its
Circuit 8 matches Leake's two (Caleb E. May / Christopher Morgan Posey);
Lowndes' Circuit 16 matches Noxubee's three (Kitchens / Howard /
Easterling) and its House 1 matches the six-county roster;
Montgomery's Chancery 3 matches Carroll/Grenada's four and its Circuit 5
makes five counties printing Loper/Lancaster identically; Grenada's own
Chancery 3/Circuit 5/CoA-1/CoA-2 reads stay clean against them all. Also
of note: Lowndes' sheet prints NO Court of Appeals section at all (the
row stream starts at U.S. Senate) — recorded in its manifest per the
source-fidelity convention alongside its X-celled judicial rows
refereeing exactly (Studdard 13043, Drungole-Ellis 3836).

## Scan-county phase: Perry, Smith, Stone, Sunflower, Tate (Tier 1's fifth five)

Five more five-page sheets, 1120 CSV data rows, 65 more rows refereed
against printed TOTALs (326 Tier-1 rows total), `run_gates` 0 problems per
county, the thirty-six-county batch exit 0 with eight advisory roster
records (one new: Chancery 7's place spread with Sunflower).

**Chancery 7 becomes a third disjoint place spread.** Sunflower's portion
of Chancery District 7 elects Place 2 only (Willie J. Perkins Sr., W. M.
Sanders) while Quitman's and Coahoma's portions elect Place 1 only
(Catherine Farris-Carter, the identical roster both print) — the same
shape as Chancery 9 and 14, declared under `accepted_roster_divergences`
in Sunflower's manifest.

**Chancery 13's roster cross-validates across Perry and Stone** — both
counties independently print Sheila Havard Smallwood (Place 1) and the
George Schmidt / John D. Smallwood / Zachary Monroe Vaughn contested
Place 2, names identical (a new shared judicial family). Stone also pairs
with Perry on House 4 (Ezell/Hulum/Boyanton) and Court of Appeals 5
(Lawrence), and Smith joins Jasper/Covington's Circuit 13 (Sullivan/Sorey)
and the four-county Chancery 2, while Tate completes Chancery 3's
four-county identical roster (Miller/Westfaul P1, Howell P2, Lundy Jr.
P3) and joins the nine-county CoA 1 and eight-county House 1 families.
Sunflower's Circuit 4 section prints THREE Places (Richard A. Smith,
Margaret Carey-McCrady, Carol White Richard) whose X-celled rows cover
disjoint precinct groups within the county — a split-district layout
whose every row's TOTAL arithmetic referees exactly. Holmes-style
no-locals sheet: Tate's five pages print no local sections at all
(recorded per source fidelity).

## Scan-county phase: Calhoun, Jefferson, Jefferson Davis, Wilkinson, Alcorn (the stragglers + Tier 2's first county)

The "Jefferson pair" resolved: the SoS ships **Jefferson_County** and
**Jefferson_Davis_County** files (the earlier sweep's `split("_")[0]` merged
both into "Jefferson"); the county "Jefferson Davis" uses the 2024-general
file's slug (`jefferson_davis`) and `county_pdf` now matches county names
across the underscore/space boundary (unit-tested). Three more 5-page sheets
plus the two 3-page stragglers (both single-table p2 + small table B), then
Alcorn — the first of the 7-page Tier-2 sheets. 1009 CSV data rows, 77 more
rows refereed against printed TOTALs (403 Tier-1 rows total), `run_gates` 0
problems per county, the forty-one-county batch exit 0 with eight advisory
roster records.

**The Circuit 3 pairing is now three-versus-two.** Calhoun's p3 prints the
FULL Benton late-header shape (Shackelford/Watts atop the page above the
Chancery 18 Place 2 box; Whitwell/Tollison above Place 1/Place 2's boxes;
the Place 3 box between Jubera and Smith) — pairing Circuit 3 as
P1=Whitwell, P2=Tollison, P3={Adams/Byers/Jubera/Smith}, exactly Benton's
and Lafayette's print. The seat-blind family roster is identical across all
five Circuit 3 counties, so the roster_subset record is unchanged. Also
Calhoun's own rotation QUIRK: p2 reads upright after ROTATE_90 but p3 after
ROTATE_270 (the two sheets scanned in opposite rotations), recorded in the
manifest.

**The Hampton split is now four counties.** Wilkinson's p3 opens with
Ashunda Hampton's continuation row exactly as Adams/Franklin/Jefferson
print it (Halford's row completing table A), and it also opens the
inverse-omission case: Wilkinson prints Circuit 6-1 only (Carmen Brooks
Drake; no Place 2 section because no Wilkinson precinct is in Blackwell's
sub-district — the roster gate records the subset against Adams' printed
union). The Chancery 4 roster (Davis P1, Wayne Smith P2, Halford/Hampton
P3) now reads identical across FOUR counties; Circuit 14 gains Jefferson
Davis (Taylor P1 / Brendon Adams-Matt Kitchens-Albert Turnage P2, identical
to Copiah and Lawrence); Chancery 2 reaches five counties (Roy Noble Lee
Jr. / Gerald M. Martin / David Shoemake); CoA 4 reaches seven counties.

**Streak-damaged cells repaired by TOTAL arithmetic (Alcorn).** Alcorn's
scan streak crosses the East Corinth column of p2, eating each cell's final
glyph (Kelly's row — which verifies cleanly — prints "63[0]" in the 800 dpi
strip). Seven rows failed the first-pass TOTAL check; the failing cell in
each was the streaked East Corinth cell, and its true value is the one that
makes the row's cross-page cell sum equal its printed TOTAL: Colom 308,
Hyde-Smith 600, Baucom 8, Johnson 280, D. Barnes 707, Brad Tennison 710
(plus Baucom's streak-crossed Wenasoga cell 8 on p3). The pipeline gate
subsequently caught ONE bad repair — Pinkins' row, whose first-pass East
value of 15 was in fact correct (a first-pass addition slip, not a bad
glyph — the gate refused to write until it was reverted), demonstrating the
repair-then-arithmetic workflow self-corrects end to end. All 17 rows now
sum exactly.

**Alcorn's judicial families complete the northern shared rosters:**
Chancery 1 (Brad Tennison P1 / Michael Malski P2 / Jacqueline Mask P3 /
Stephen T. Bailey P4) and Circuit 1 (John R. White P1 / Josh Wise P2 /
Kelly L. Mims P3 / Michael P. 'Chip' Mills Jr. P4) read identical against
Lee (and Chancery 1 against Union), CoA 1 reaches ten counties. The 7-page
sheet's extra pair of pages (p6/p7) carries only the local School Board 5
row's two column groups — declared local_only pages like Kemper's tail.

The remaining 41 scan counties follow the same operator-read route (tier
order below; seven-page Tier-2 counties next, Hinds last).

## Next phase

The remaining 41 county PDFs (82 in
`~/code/openelections-sources-ms/2026/general/` minus the forty-one converted so
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
