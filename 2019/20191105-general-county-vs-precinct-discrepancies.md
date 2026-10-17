# 2019 general: county CSV vs precinct files — discrepancies

Date: 2026-09-14
Sources compared:

- `2019/20191105__ms__general__county.csv` — 2,278 rows (2,276 plus the two
  SD50 revote rows found during this check), parsed from the
  statewide general recapitulation crosstab (SoS).
- `2019/counties/20191105__ms__general__<county>__precinct.csv` — 82
  pre-existing (2020-vintage) precinct files, covering every office on each
  county's ballot (including local offices the county CSV doesn't carry).

Crosscheck: `crosscheck_2019_general.py` (aggregates each precinct file by
county/office/district/candidate and compares to the county CSV; normalizes
party spellings, office-name variants like 'District Attorney' + district '1'
vs 'District Attorney 01', and OCR name variants via NAME_ALIASES).

## Results

Structural file defects found and fixed first (before value arbitration):

| County | Defect | Fix |
|---|---|---|
| Jackson | 10 (office, district, party) groups with every candidate name blank (SD47/51/52 R, HD109–114) | filled from the county CSV's roster (65 rows) |
| Monroe | rows labeled 'State Senate' 16 are really State House 16 | relabeled (values already matched) |
| Newton | rows labeled 'State Senate' 78 are really State House 78 | relabeled (values already matched) |
| Calhoun | Benjamin A. Suber (SD 8) labeled Democrat | R (county CSV and sum agree) |
| Coahoma | Cedric Burnett (HD 9) labeled Republican | D |
| Simpson/Smith/Stone | Secretary of State party labels swapped (DuPree printed Republican, Watson printed Democrat) | swapped to match the county CSV (the candidate values already matched) |
| crosscheck | PSC/Transportation district fallback doubled the ' district' suffix | regex fixed in crosscheck_2019_general.py |

## Arbitration

Every remaining value mismatch is arbitrated against the **per-county general
recap scans** (`https://www.sos.ms.gov/elections/electionresults/
2019General/County%20Recaps/<County>.pdf`, fetched with a curl UA — the
server 403s browser UAs and Akamai rate-limits parallel fetches; a literal
space in the filename must be %20-encoded). These are image PDFs; PaddleOCR-VL
markdown was fetched by `extract_2019_general_paddle.py` (with the same
padding preprocessing as the primary pipeline — the scans run their last
precinct column against the page edge, which PaddleOCR drops otherwise) and
compared by `arbitrate_2019_general.py`.

Arbitration convention (as in the primary and runoff rounds): a proposed
precinct-file correction is applied only when the recap's printed TOTAL for
that candidate equals the county-CSV value AND the printed per-precinct
cells account for the entire difference.

*(per-county arbitration results below)*

### Per-county arbitration results

All 41 batch counties were OCR'd and arbitrated (Rankin's 36-page padded PDF
had to be split into two halves — uploads over ~14 MB are rejected by the
endpoint). Cells = individual value corrections verified against the recap
(usually one printed cell misread by the 2020-vintage file, recovered via the
printed TOTAL); rows = rows added (whole races, plus name fills and race
relabels tracked in the tables above); relabels = rows whose office/party/
candidate label was corrected with values unchanged.

| County | Cells fixed | Rows added | Notes |
|---|---|---|---|
| adams | 0 | 79 | DA-06 race appended |
| alcorn | 2 | 0 | |
| amite | 2 | 84 | DA-06 + PSC/TRANS Southern appended; file line endings normalized |
| attala | 1 | 80 | DA-05 + PSC/TRANS Northern appended |
| bolivar | 69 | 112 | PSC/TRANS Central appended; DA-11; several shifted runs |
| calhoun | 0 | 10 | Suber SD8 relabeled R (10 rows) |
| chickasaw | 1 | 60 | DA-03 + PSC/TRANS Northern appended |
| clarke | 2 | 0 | |
| coahoma | 1 | 77 | DA-11 + PSC/TRANS Central appended; Burnett HD9 relabeled D |
| copiah | 1 | 76 | DA-22 + PSC/TRANS Central appended |
| covington | 2 | 45 | DA-13 + PSC/TRANS Southern appended |
| desoto | 7 | 124 | DA-17 + PSC/TRANS Northern appended |
| forrest | 3 | 0 | DA-12 (DeCarlo Hood) |
| george | 1 | 0 | |
| grenada | 2 | 0 | |
| hancock | 9 | 1 | Edwardsville dropped-cell recovery (HD122) |
| harrison | 1 | 0 | SD50 rows added (revote) |
| hinds | 82 | 10 | shifted-block recovery (precincts 75–82, byram 2/3); PSC/TRANS Central appended |
| holmes | 2 | 1 | DA-21 |
| jackson | 92 | 128 | 65 blank-candidate fills; SD47/HD109–114 relabels; DA-19 |
| jasper | 1 | 68 | DA-13 + PSC/TRANS Central appended |
| jones | 2 | 0 | |
| lamar | 1 | 0 | |
| lauderdale | 1 | 160 | DA-10 + PSC/TRANS Central appended |
| lawrence | 1 | 0 | Collins Armory 26→28 — misread identically by both passes (see quirks) |
| leake | 1 | 76 | PSC/TRANS Central appended |
| lee | 2 | 144 | DA-01 (John Weddle, 36 rows) + PSC/TRANS Northern appended |
| lowndes | 2 | 80 | DA-16 (Scott Colom, 20 rows) + PSC/TRANS Northern appended; Belton SD17 Hunt 2→32 |
| madison | 8 | 1 | five manual page-render fixes; merged-header quirk (see below) |
| monroe | 0 | 2 | SD16→HD16 relabel |
| montgomery | 2 | 60 | DA-05 (Doug Evans, 15 rows) + PSC/TRANS Northern appended |
| neshoba | 35 | 116 | Kilgore→Branning SD18 rename (27 rows); DA-08; PSC/TRANS Central appended |
| newton | 21 | 64 | SD78→HD78 relabel (20 rows); PSC/TRANS Central appended |
| oktibbeha | 2 | 80 | DA-16 (Scott Colom, 20 rows) + PSC/TRANS Northern appended |
| pearl_river | 3 | 1 | Seymour SD47 poplarville 2 row; Chaney mill creek 2 216→316 |
| pike | 22 | 100 | Amos/Chaney rows carried PSC candidates' values; DA-14; PSC/TRANS Southern appended |
| pontotoc | 2 | 0 | Suber algoma 14→314 |
| rankin | 3 | 1 | Hickingbottom east crossgates 1→4; Cole south richland 312→313 (Pisgah/Plagah quirk); Wallace HD77 dry creek row |
| simpson | 0 | 46 | SoS party labels swapped back (46 rows) |
| smith | 38 | 36 | SoS party labels swapped back (36 rows); King shady grove 28→288 |
| stone | 33 | 30 | SoS party labels swapped back (30 rows); Fitch/Cole/McLeod cells |
| warren | 1 | 0 | Collins brunswick 21→24 |
| winston | 2 | 48 | Green county agent 467→497; DA-05 (Doug Evans, 12 rows) + PSC/TRANS Northern appended |
| yazoo | 1 | 0 | Hughes eden 3→38 |

Totals: 44 files changed; ~330 individual cell corrections; ~2,300 rows
added (whole DA/PSC/Transportation races reconciled against the recaps,
candidate-name fills, and the SD50 revote rows); ~200 label corrections.
Every appended race's printed cells sum exactly to its county-CSV value.

### County-CSV defects found during arbitration

| Defect | Fix |
|---|---|
| State Senate 50 (Harrison) missing from the county CSV entirely | SD50 was **not a normal general race**: the Aug 2019 Republican primary ended in a one-vote margin, a court vacated it, and a revote was held Nov 5 in 5 precincts (Biloxi #11, Howard Creek, Margaret Sherry, New Hope, Saucier) while the other 11 precincts' Aug 6 totals carried over (hence the file's zero rows). DeLano 1,468 / Newman 1,138, both Republican (confirmed by the Sun Herald/AP reporting and the per-county recap). Two rows added to the county CSV. |
| Neshoba precinct file's SD18 rows carry candidate "Steven S Kilgore" | Jenifer B. Branning ran **unopposed** in SD18 (the 3-county county-CSV sum, 13,197, equals her reported total; Kilgore ran in SD18 in 2011 and is the DA-8 candidate in 2019). 27 rows renamed; the remaining 257-vote deficit is arbitrated against the recap. |

### Whole races missing from the precinct files

The 2020-vintage precinct files omit whole races in many counties — Public
Service Commissioner, Transportation Commissioner, and District Attorney
races. Where the recap's printed cells for a missing race sum to the
county-CSV value (with matching printed TOTAL), the arbiter appends the
whole race. All such reconciled races were appended: District Attorney races
in Adams (06), Attala/Montgomery/Winston (05), Chickasaw (03), Coahoma (11),
Copiah (22), Covington (13), Desoto (17), Forrest (12), Holmes (21), Jackson
(19), Jasper (13), Lauderdale (10), Lee (01), Leake (08), Lowndes/Oktibbeha
(16), Neshoba/Newton (08), Pearl River (15), Pike (14), Rankin (20 partial —
dry creek), Yazoo (21); plus PSC/Transportation Commissioner races in 21
counties across all three districts.

Races the recaps don't reconcile remain gaps (see the final tally).

## PaddleOCR quirks hit during arbitration

Each of these defeated the parser until handled in
`arbitrate_2019_general.py` (`parse_page`/`load_ocr`); all are fixed there:

- **No-colspan lead header with a separate party cell**: on some pages the
  lead header cell carries no colspan, yet candidate rows emit
  `[name][party][values...]` — the party word lands on the first precinct
  header and every value shifts one right (Bolivar p006–p007, six races).
  Fix: drop a leading party cell from values.
- **Phantom empty header cells**: Bolivar p006's header row has an empty cell
  mid-row while values are continuous. Handled by order-based alignment
  (numeric cells map in order onto named headers) whenever the counts line
  up; strict positional alignment otherwise, which keeps 'x'
  (not-on-ballot) cells aligned. The count guard also refuses order-based
  alignment when a value cell went missing (a printed 0 read as blank).
- **Section labels in the second cell**: Bolivar p009 emits
  `['', 'State Senate 12-District 12', '', ...]`, with the first candidate
  row even read *before* its label. Parser accepts single-non-empty-cell
  label rows in any position (keyword-gated so 'Names of Election
  Precincts' isn't mistaken for one) and buffers orphan candidate rows into
  the following label's section.
- **First rows of a page continue the previous page's section**: Forrest
  p010 opens with DeCarlo Hood's District Attorney 12 row *before* the
  'State Senate 34' label, so buffering it into the following label's
  section put Hood's cells in the wrong race (and a copied value polluted
  the Barnett row). Since a candidate runs for only one office per county,
  `load_ocr` now resolves orphan rows against the county-CSV roster — Hood's
  row landed in DA-12 and its parsed cells sum to exactly his certified
  6,726.
- **Split lead cells**: Copiah p006 emits
  `['', 'Tom Weathersby', 'Republican', values...]` — name and party as two
  extra lead cells. Parser pops them; the positional fallback then aligns
  values to the *named* headers only (skipping empty lead cells).
- **Header-row misreads**: 'Voles cast in the County' (Clarke p008) broke
  header detection; matching loosened to 'cast in the county'.
- **Dropped value cells**: a trailing 'x' cell dropped mid-table leaves a
  short row; strict positional would misalign it — caught by the
  count-guarded alignment and, where unrecoverable, left for manual review.
  Interior cells near the page edge can vanish entirely: Hancock p008
  dropped the Edwardsville cell in both State House 122 rows (verified
  against the rendered page: Anderson 232 — whose precinct-file value "32"
  was a leading-digit drop of the same number — and McDonald 33, confirmed
  by the printed TOTALs).
- **Merged cells**: Hancock p008's McKnight row read Edwardsville's 'x' and
  Fenton's '384' as one cell ('x 384'), hiding a printed value; and p009's
  HD95 row dropped South Bay's 'x', shifting Standard's 88 into South Bay —
  both settled against page renders.
- **The row TOTAL posing as a precinct cell**: when the TOTAL header is
  lost, its value can land under a precinct-named column (Hinds: 'utica 2'
  = 12,202, the exact county-CSV total) or under the header row itself
  (George: 'Names of Election Precincts' = 2,725). The arbiter reassigns a
  non-file cell equal to the county-CSV total to the printed TOTAL.
- **Shifted blocks in the 2020-vintage file**: several Hinds races had a
  run of file rows (precincts 75–82) whose values were slid one precinct
  over, and byram 2/3 pairs swapped — all recovered cell-by-cell from the
  recap. The arbiter now resolves diffs + missing rows + spurious 'x' rows
  together whenever they uniquely reconcile to the printed TOTAL.
- **Scrambled OCR names**: 'Spainiovie' for 'Souinlovie' (Clarke),
  'Baulah' for 'Beulah', 'Addle' for 'Addie' — matched via difflib fallbacks
  (same-first-word ≥0.7, then all-keys ≥0.7).
- **A misread both passes share**: the 2020-vintage file and the new
  PaddleOCR pass can misread the same digit identically, leaving every
  printed cell in agreement while the printed TOTAL still disagrees.
  Lawrence p002 read Jennifer Riley Collins's Armory cell as 26 in both
  passes, but the recap's TOTAL (1,826 = the certified value) exceeded the
  cell sum by 2; a page render shows a clear 8 (vs the open-top 6 in Lynn
  Fitch's 67 on the same column). The printed TOTAL was the only detector.
- **Merged header cells shift the whole page's columns**: Madison p002
  merged 'Magnolia Heights' and 'Mark Apartments' into one header cell, so
  every parsed value slid one column left and the last column fell out of
  the parse — the file was right in that run, and each race's small residual
  surfaced one cell elsewhere. Each was settled against a page render
  (Fitch/DuPree 194→197, Collins 324→327, Green 494→497, Michel China Grove
  A M E Church 92→902).
- **A header misread that looks like a missing precinct**: Rankin p010's
  Pisgah header was read as 'Plagah' on one page (the same precinct prints
  as Pisgah on the other four pages of its block), so the arbiter saw a
  missing 'Plagah' row plus a file 'Pisgah' cell with no printed value. The
  render shows the recap itself prints Pisgah, and only the neighboring
  South Richland cell (312 vs 313) was actually wrong.
- **Race-key case mismatches**: PSC/Transportation Commissioner keys were
  built with three different district-word casings (OCR lowercase,
  county-CSV Title-case, file district column as-is), so those races
  silently fell to '[no OCR section]'. All key builders now emit the same
  lowercase form; the fix unlocked the reconciled whole-race appends above.
- Digit noise as in earlier rounds (Amite Walls 282→202, Copiah Crystal
  Springs South 2 for 72) — caught by the printed-TOTAL reconciliation gate.

## Final tally

`crosscheck_2019_general.py` final state:

```
checked 2013 of 2278 county-CSV values (265 not covered by precinct files): 2013 match, 0 mismatches
```

Every county-CSV value that has a precinct-file counterpart now matches its
precinct-file sum, and every appended race's printed cells sum to its
county-CSV value. The 265 uncovered values are all PSC / Transportation
Commissioner / District Attorney races that the 2020-vintage files omit
whole (in 41 counties never OCR'd for this check, plus ~20 OCR'd counties
whose recap pages for those races parsed incompletely — printed TOTAL
matching but cell sums short, e.g. Yazoo's PSC-Central, so the
reconciliation gate correctly refused to append). Legislative and statewide
races are fully covered: no uncovered value is a Senate, House, or
statewide-office row.

Data-quality lint of all 82 general precinct files passes: no duplicate
rows, no missing values, no short rows, no mixed line endings within a file.

## Reproducing

```sh
uv run python crosscheck_2019_general.py
uv run python fix_2019_general_structural.py        # structural fixes above
# recap download + OCR:
curl -s -A curl/8.7.1 -o cache/2019-general-arb/<County>.pdf \
  "https://www.sos.ms.gov/elections/electionresults/2019General/County%20Recaps/<County>.pdf"
uv run python extract_2019_general_paddle.py        # all 41 arbitration counties
uv run python arbitrate_2019_general.py             # report
uv run python arbitrate_2019_general.py --fix       # apply verified fixes
```