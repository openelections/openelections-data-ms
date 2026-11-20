# Jasper 2026 general precinct generation notes (2026-11-19)

Status: **CSV generated.** `2026/counties/20261103__ms__general__jasper__precinct.csv`
(11 candidates x 13 precincts = 143 data rows) from a fully operator-supplied
grid: the OCR text layer is unusable for the cells on every in-scope page, so
`2026/header-reads/20261103__ms__general__jasper__headers.json` declares
`operator_supply_pages: ["2", "3", "4", "5"]` and carries all 11 rows as
`operator_rows` keyed on the declared labels. Run output:

```
Jasper: 11 candidate rows, 13 precincts, 0 local rows dropped, 0 skipped local
pages, 4 operator-supplied pages, 154 operator cells applied, 0 gate problem(s)
  wrote 2026/counties/20261103__ms__general__jasper__precinct.csv
```

(154 = 11 rows x (13 vote cells + 1 printed-TOTAL cell read).)

## The conversion (Task 8, item 3)

The phase-D stop (58 gate problems under the layer parse) held because p2/p3's
digit tokens are corrupt beyond token repair and still read as clean numbers
(print 864 → layer "8", 109 → "101", 164 → "764", 4970 → "497"), and p4/p5
parse nothing at any floor. The conversion supplies every row the way the
already-verified Sorey row was supplied:

- **Render verification first**: all 11 rows re-read from fresh renders —
  p2 600 dpi row strips in three column segments each
  (`cache/2026-general-text/operator-verify/jasper/jas_p2_<candidate>_{a,b,c}.png`),
  p3 tail strips (`jas_p3_<candidate>_t.png`), full pages at 300 dpi for
  orientation (`jas_p{2,3,4,5}_full300.png`), and Sorey's p4/p5 strips
  (`jas_p4_sorey_{a,b,c}.png`, `jas_p5_sorey_t.png`).
- **Per-row printed-TOTAL referee**: 10 of the 11 rows reconciled exactly
  against the printed county TOTALs on the first pass; Matthew G. Sullivan's
  row did not with the prior phase's reference grid — his Holders cell's
  grid value (280) was a misread of the printed **283**, which alone makes his
  13 cells + p3 cells sum to the printed TOTAL 4984 (4050 + 934). Adjudicated
  by the coordinator from the render (jas_p2_sullivan_b.png, and the 1200 dpi
  cell zoom with same-column font references); written up in
  `2026/20261103__ms__general__jasper__discrepancies.md` (resolved-by-print).
  Every other printed cell in the grid matched the reference grid byte-for-byte.
- Sorey's row is **unmoved** from the finalized pre-conversion manifest: his
  Holders cell does print 280 and his own row arithmetic is exact
  (4008 + 937 = 4945); re-confirmed on the fresh strips.
- `page_min_columns {"3": 2}` was dropped: it existed only to move p3's layer
  table top (Fix 2) and p2-p5 are no longer parsed. The two layer pins for why
  the layer is unusable stay in the test file (`JasperTextLayerTests`).

## Verification of the generated CSV (`cache/verify_jasper_csv.py`)

- 143 data rows = 11 candidates x 13 precincts (Antioch, Bay Springs Beat 3,
  Bay Springs Beat 4, Claiborne, Heidelberg, Holders, Louin, Montrose, Moss,
  Moss East, Paulding, Rose Hill, Stringer — Moss East new vs the 2026
  primary's 12); zero duplicates on (precinct, office, candidate).
- Per-candidate CSV sums == printed county TOTALs, **11/11**: Colom 3488,
  Hyde-Smith 2609, Pinkins 108, Chiaradio 3383, Guest 2736, Klehle 51,
  Lee Jr. 4951, Martin 4952, Shoemake 4970, Sullivan 4984, Sorey 4945.
- Offices/districts: `U.S. Senate` (district ""), `U.S. House` ("3");
  two-seat suffixes per the multi-seat rule — `Chancery Court Place 1/2/3`
  (district 2, three places on the ballot) and `Circuit Court Place 1/2`
  (district 13); parties `DEM/REP/IND/LIB` + `""` for the Nonpartisan
  judicial rows.
- Ballot order in every precinct: Colom, Hyde-Smith, Pinkins, Chiaradio,
  Guest, Klehle, Lee Jr., Martin, Shoemake, Sullivan, Sorey (operator_rows
  insertion order).
- Senate roster `{Scott Colom/DEM, Cindy Hyde-Smith/REP, Ty Pinkins/IND}`
  matches the committed Union, Warren and Lee CSVs.

## Phase-D record (what the conversion replaced)

The fixes that made the county's manifest/alignment problems resolvable before
the grid was supplied are retained below for the record; the CSV they could
not produce now exists through the operator grid.

| commit | change |
| --- | --- |
| f214813 | Fix 1 grid anchor widened to the first three data lines; Fix 2 `page_min_columns` |
| c30276b | Fix 3 `operator_cells` + `operator_rows` + `operator_supply_pages` |
| 7247589 | manifest finalization + Sorey-only run + the original version of this note |
| this commit | whole-grid `operator_rows` conversion (Sullivan adjudication) + CSV |

Parser/test count at each Task 8 boundary: 150 → 166 → 181 → 182, all green;
Union and Warren county parses byte-identical throughout (their committed
CSVs are untouched), and Lee's operator-grid CSV (generated in the same task)
is byte-identical at every boundary.
