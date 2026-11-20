# Assessment: 2026 general election scan-county PDFs (78 image-only files)

Date: 2026-11-20
Method: programmatic sweep of all 78 PDFs (page/layer/image structure) + operator
vision reads of rendered sample pages (8 counties read visually; the rest share
programmatic profiles with read samples). No OCR run (per direction: the
operator reads as a vision model; PaddleOCR deferred).

## Sweep findings (all 78)

- **Zero text characters in every file** — pure image scans; the deterministic
  word-geometry parser has nothing to consume. Every cell must come from
  operator vision reads (or OCR, deferred).
- The **fully operator-supplied county path** built for Lee/Jasper applies
  wholesale: `operator_supply_pages` on every content page + `operator_rows`
  carrying identity + grid, judged by the printed-TOTAL gates.
- Image composition varies (single full-page scans vs tiled strip scans —
  e.g. Stone 333 image objects, Prentiss 308, Amite 321): no functional
  impact on rendering or reading.
- **Scan resolution tiers** (max embedded image width): ~500 DPI (Adams,
  Grenada, Harrison, Jefferson, Jones, Lafayette, Marion, Smith, Bolivar) —
  excellent; ~200-300 DPI (the bulk) — fully legible; ~100-130 DPI (Forrest,
  Jackson, Sunflower ~850px; Hancock, Newton, Jefferson Davis ~1,100px) —
  still legible in visual samples.
- **Orientation varies by county and includes both 90° variants**: landscape
  sheets render upright for Adams/Hancock/DeSoto/Forrest-class counties;
  portrait sheets hide a rotated landscape table that reads upright after a
  90° rotation one way for Harrison/Hinds-class and the other way for
  Amite-class. Rotation must be detected per county (one glance each) and
  recorded in the manifest — the 2024 runbook's per-PDF rotation landmine.

## Visual reads (rendered page 2 of each sample)

| County | Pages | Read | DPI tier | Findings |
|---|---|---|---|---|
| Adams | 5 | yes | ~516 | column-split, crisp; precinct names carry "Precinct" suffix; House D2 (Eller REP / G. Thompson DEM / Foster IND); CoA D4 P2; Chancery D4 Places 1-3 |
| Hinds | 51 | yes | ~200 | portrait, rotation opposite Amite's; 3 column groups per page pair incl. **State House Of Rep 70-District 70** (state legislative, in scope) with X cells for out-of-district precincts; the largest county by far (51 pages) |
| Harrison | 16 | yes | ~500 | column-split, pristine; House D4 (Ezell/Hulum/Boyanton); CoA D5 P1; Chancery D8 Places 1-3 (shared with Hancock) |
| DeSoto | 16 | yes | ~216 | crisp; House D1; CoA D1 P1/P2 (same D1 roster as Union/Lee); Chancery D17 P1/P2 |
| Hancock | 13 | yes | ~131 | grainy but fully legible; same ballot as Harrison (Chancery D8 shared roster) |
| Forrest | 9 | yes | ~100 | fully legible despite lowest DPI; House D4; CoA D5 P1; Chancery D13 Place 2 has THREE candidates; wrapped "Place 1" label variant present (parser handles) |
| Amite | 7 | yes | ~253 | tiled scan; rotation opposite Harrison's; House D2; Chancery D4 Places 1-3; CoA D4 |
| Issaquena | 3 | yes | ~212 | whole grid + TOTAL on one page; Chancery D9-2 and Circuit D9-1 shared with Warren; plus a LOCAL race (Tax Assessor Collector — out of scope) |
| Bolivar, Simpson, Pike, Wilkinson | 10/7/10/3 | programmatic only | 2216-2737 / 3296 / 2216 / 2216 px | profiles match read samples (same format family); no red flags |

## Ballot-coverage implications for the next phase

1. **State-legislative races are on some scan-county ballots** (Hinds: State
   House District 70 with three Independents). The repo keeps federal +
   statewide + state-legislative offices, so these must be captured. The
   `State Senate`/`State House` patterns deleted from `parse_office` during
   Task 3's hardening must be restored — this time against observed printed
   labels — before the 78-county phase.
2. **X cells mark out-of-district precincts** for districted races (Hinds p2
   is dense with them). The Warren-built X-cell rule (position evidence,
   never a value; blanks become 0 only when the row's printed total proves
   it) handles this unchanged.
3. **Judicial districts cross county lines** (Chancery D8: Harrison+Hancock;
   D9: Warren+Issaquena; D4: Adams+Amite), and district races must stay
   consistent across counties — the existing cross-county roster gate covers
   them. New shared rosters will surface as more counties convert.
4. **Precinct-name conventions vary by county** ("Dist. 1, Bellemont
   Precinct" in Adams vs bare names elsewhere) — `precinct_norm` handles the
   suffix; commas inside names remain the classic landmine (they are present
   in Adams's header cells).

## Conversion route (no OCR)

For each of the 78: operator vision reads of the header strips + numeric
grids + TOTAL pages (rendered at 200 dpi, rotating per the county's detected
orientation, zooming per-cell as done for Lee/Jasper), recorded in the
manifest via `operator_rows` with `operator_supply_pages` set for every
content page; all gates, the roster gate, and byte-deterministic CSV
generation run unchanged. Pipeline additions needed first (small):

1. Restore + generalize the `State Senate`/`State House` office patterns
   (render-verified only).
2. A manifest rotation hint per county/page (`render_rotation`) used by the
   operator reading flow; rendering itself stays pdfplumber + PIL.

## Proposed order (small pilots first, Hinds last)

- Tier 0 pilots: Issaquena (3 pp), Sharkey (3), Noxubee (3), Quitman (3),
  Benton (3), Claiborne (3), Humphreys (3) — smallest grids; Issaquena's
  page-2-only layout exercises the single-page fast path.
- Tier 1 (5 pp): the bulk (~40 counties).
- Tier 2 (7-10 pp): Alcorn, Clarke, Itawamba, Monroe, Pike, Bolivar, etc.
- Tier 3 (13-16 pp): Hancock, Pearl River, DeSoto, Harrison, Madison, Rankin.
- Tier 4: Hinds (51 pp — column groups x row blocks, several State House
  districts, the largest single grid).

## Volume observation (for planning)

A 33-precinct county (Lee) took roughly a dozen full-page reads plus zooms.
The 78 counties' combined content pages are on the order of 300; at 2-4
page-reads per precinct-column group the operator-reading work is the
dominant cost, with Hinds alone likely comparable to ~6-10 ordinary
counties. Legibility risk is low everywhere sampled — even ~100 DPI renders
were clean; per-cell zooms remain available for any doubtful digit, with the
printed-TOTAL arithmetic as the referee per row.
