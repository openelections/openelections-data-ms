# Jasper 2026 general precinct generation notes (2026-11-19)

Status: **CSV not generated.** The parser fixes and the finalized header
manifest are in place, the Circuit Court 13 Place 2 row (Stanley Sorey) is
fully supplied and gate-clean, and the county parse's manifest/alignment
problems are all resolved — but the OCR text layer's digit tokens on p2/p3
corrupt or drop cells for the other ten candidates, so the printed-TOTAL gate
(58 problems) holds the county, as the runbooks require. Nothing was
written under `--allow-gate-failures`: writing this CSV now would publish
OCR digits we can already see disagree with the print.

Companion files:

- `2026/header-reads/20261103__ms__general__jasper__headers.json` — finalized
  (draft flag removed): labels unchanged, plus `page_min_columns {"3": 2}`,
  `operator_supply_pages [4, 5]`, and the `operator_rows` entry for Stanley
  Sorey (provenance in-file).
- `cache/2026-general-text/jasper_run_phaseD.txt` — the gate loop verbatim
  (58 problems), `jasper_run_phaseD_fuzzy_tail.txt` — the `--fuzzy` variant
  (89 problems: fuzzy turns more junk into fake numeric tokens, so it is
  worse, not better; not used for the county run).

## What landed

| commit | change |
| --- | --- |
| f214813 | Fix 1 grid anchor widened to the first three data lines (race-header lines excluded); Fix 2 `page_min_columns` |
| c30276b | Fix 3 `operator_cells` + (amendment) `operator_rows` + `operator_supply_pages` |
| this commit | manifest finalization + run + this note |

Parser/test count at each commit boundary: 150 → 166 → 166, all green; Union
and Warren county parses byte-identical throughout (their committed CSVs are
untouched).

## Fix 1 — widened grid anchor (p2)

Jasper p2's first data line carries only 3 clean OCR digits (x 464..745), so
the one-line anchor span dropped the five real left clusters (x 281..429).
The anchor reference now measures the union span of the first THREE data
lines (race-header lines excluded — their "Position/Place" qualifier digits
are the Union phantom geometry). p2 yields exactly its 11 real columns
(c285.2, c328.3, c376.4, c423.0, c467.9, c511.8, c559.8, c608.4, c652.8,
c695.4, c738.2), and the x~246 "'1'-debris" phantom (three members around the
fragment lines y≈353/490/523) still drops — pinned
(`JasperTextLayerTests`, `MultiLineAnchorTests`, `GridCentersTests`).

## Fix 2 — declared floor 2 (p3)

p3's min3 table top lands on Guest's row (y=308.2), losing the four rows
above it. `page_min_columns {"3": 2}` makes a second, authoritative attempt
at floor 2: the top moves to the page's true first data line
(Scott Colom's row, y=200.296) and the page yields its three columns
(283.1, 331.6, 369.5 = Rose Hill, Stringer, TOTAL). Prose false-tops stay
caught downstream by the column-count/roster/total gates — the false-top
lines under this floor are candidate-row lines by construction, and the
count gate binds the page's columns to the declared labels.

## Fix 3 — operator cells / operator rows (Sorey's row)

p4/p5 are unusable at ANY floor (p4: no cluster reaches the 3-member floor —
17 clean tokens among 11 columns; p5: min2's first "table" line is the
Circuit Court office header itself). They are declared
`operator_supply_pages` (never extracted, recorded, never a
page_missing/column_count problem), and the in-scope row arrives through
`operator_rows`, keyed on the declared labels' column-order index —
including p5's TOTAL column at index 2 (the operator's read of the printed
TOTAL cell is the row's total; there is no separate total override, exactly
as the review required — the DRAFT note's "already captured via the TOTAL
column" was wrong: the layer reads that cell as the non-numeric token
'494t').

Applied-then-recorded applications (13 vote cells + 1 total cell = 14
records in `pd["operator_cells_applied"]`, printed by the CLI as
"14 operator cells applied"):

| page | column label | precinct | old | new |
| --- | --- | --- | --- | --- |
| 4 | Antioch | Antioch | missing | 193 |
| 4 | Bay Springs Beat 3 | Bay Springs Beat 3 | missing | 526 |
| 4 | Bay Springs Beat 4 | Bay Springs Beat 4 | missing | 428 |
| 4 | Claiborne | Claiborne | missing | 240 |
| 4 | Heidelberg | Heidelberg | missing | 746 |
| 4 | Holders | Holders | missing | 280 |
| 4 | Louin | Louin | missing | 372 |
| 4 | Montrose | Montrose | missing | 169 |
| 4 | Moss | Moss | missing | 233 |
| 4 | Moss East | Moss East | missing | 172 |
| 4 | Paulding | Paulding | missing | 649 |
| 5 | Rose Hill | Rose Hill | missing | 414 |
| 5 | Stringer | Stringer | missing | 523 |
| 5 | TOTAL | (row total) | missing | 4945 |

Independent spot-check (this session, fresh 600-dpi renders,
`cache/2026-general-text/spot/spot_p4_rows.png` / `spot_p5_rows.png`):
p4's Sorey row prints 193 | 526 | 428 | 240 | 746 | 280 | 372 | 169 | 233 |
172 | 649 and p5's prints 414 | 523 | 4945 under the Rose Hill / Stringer /
TOTAL stacks — the operator read is confirmed, and the arithmetic anchor
holds (4008 + 937 = 4945 = the printed TOTAL cell). The Sorey row is the
only candidate row with zero gate problems; its 13 cells all re-key through
the manifest labels (p4/p5's labels equal p2/p3's precinct names, so
`operator_cell_unknown_precinct` stays silent by right).

## Per-candidate extracted sums vs printed totals (all 11)

The parse fragments under this layer (each fragment is what
`parse_county_from_pages` merged; "dropped" fragments are rows the layer
could not attribute to an office — recorded whole in
`pd["dropped_local_rows"]`, never merged):

| candidate | printed total | parsed fragments (sum / printed-total cell if any) | verdict |
| --- | --- | --- | --- |
| Scott Colom (DEM) | 3488 | p2 "Scott Colom": 3 cells, sum 711 (Heidelberg 8 (print: 864), Montrose 101 (print: 109), Paulding 602 ✓); p3 "Scott colom Demo": Rose Hill 2 (print: 248), total cell 3 (print: 3488) | not reconcilable |
| Cindy Hyde-Smith (REP) | 2609 | "cindy Hyde-smlth": 9 cells, sum 2951 (e.g. Antioch 156 ✓, Holders 152 ✓, Moss East 130 ✓, Paulding 217 ✓; Louin 764 (print: 164), Heidelberg 1281 (print: 128), Bay Springs Beat 4 20 (print: 203)); p3 total cell mangled ('zsol') | not reconcilable |
| Ty Pinkins (IND) | 108 | "Plnklns Inde": 11 cells, sum 54; "Ty Plnklns": Stringer 1 (print: 14), total cell 1081 (print: 108) | not reconcilable |
| Michael A. Chiaradio (DEM) | 3383 | "l'llchael A. Chlaradlo": 7 cells, sum 1187; "l,llchael A. Chlaradlo De": Stringer 42 ✓, total cell 3383 ✓ | p2 cells incomplete |
| Michael Guest (REP) | 2736 | "lVlchael Guest": 6 cells, sum 1040; "Guest": Rose Hill 267 ✓ + Stringer 573 ✓, total 2736 ✓ | p2 cells incomplete (needs 1896 from 5 garbled/missing) |
| Erik Klehle (LIB) | 51 | "Erlk Liberta rlan": 7 cells, sum 24; "Erlk Ki6hle Liberta rla n": Rose Hill 3 ✓ + Stringer 3 ✓, total 51 ✓ | p2 cells incomplete |
| Roy Noble Lee Jr. (NP) | 4951 | p3 "Chancery court 2-Chancary Dlstrict 2 Plac€": Rose Hill 409, total 4951 ✓; p2 row dropped (5 cells, sum 927 — office unattributable in the layer) | not reconcilable |
| Gerald M. Martin (NP) | 4952 | dropped p3 "M. lvlartln": 410, 50, total 4952 ✓; dropped p2 "Gerald Martln": 191, 52 | not reconcilable |
| David Shoemake (NP) | 4970 | dropped p2 "David Shoemake": 24, 76, 1; dropped p3 "Davld  Shoemake": 416, 51, total 497 (print: 4970) | not reconcilable |
| Matthew G. Sullivan (NP) | 4984 | dropped p2 "l'latthew Sullivan"; dropped p3 "Matthew G, Sullivan": Stringer 1, total 49 (print: 4984) | not reconcilable |
| Stanley Sorey (NP) | 4945 | operator row: 13/13 cells, sum 4945 = printed total | **reconciles** |

Run shape: 21 candidate rows, 13 precincts, 13 unattributable junk rows
dropped, 2 operator-supplied pages, 14 operator cells applied, 58 gate
problems (6 total_mismatches, 20 missing_precinct_cells, 14 missing_total,
14 unknown_party, 4 within-page duplicate_cell records).

## Verification that is possible now

- **No duplicates**: the 21 merged rows have unique ballot identities
  (`_merge_key`); the layer's double-printed fragments show up only as the
  4 recorded within-page duplicate_cell overwrites (kept-value/overwritten
  recorded per cell, held as conflicts).
- **Operator values**: independently render-verified this session (above).
- **Moss East**: render-verified new-2026 spelling (prior Task 8 render pass;
  manifest truncation_note), matching no primary/2024 list — the county's
  2026 13-precinct set is carried in the manifest and bound by the alignment.

## What is NOT verifiable yet (and why)

- **Ballot order, Place suffixes, Senate roster vs Union/Warren CSVs**: the
  CSV write is held. When the county parses, `multi_seat_keys` will suffix
  Chancery Court P1/P2/P3 and Circuit Court P1/P2 per the two-seat rule
  (today the Circuit family shows one in-scope seat only because Sullivan's
  parsed rows fall in the dropped set); the roster gate compares against
  Union/Warren at batch stage.
- **The ten other candidates' cells**: this OCR text layer's digit tokens are
  corrupted for many cells (dropped digits, digit swaps, whole-cell losses),
  and wrong tokens can still read as clean numbers — the printed-TOTAL gate
  catches those rows, which is exactly its job. Two paths per the runbooks:
  an operator render sweep of p2/p3 cells (each candidate's 13 cells ≈ 260
  reads, plus the mangled labels' render-verified spellings for
  `LABEL_REPAIRS`), or a PaddleOCR-VL re-extraction of this PDF per the AL
  toolchain pattern. `--fuzzy` is not a path: it raises 58 → 89 gate
  problems (it converts junk like 'l'/'I' into fake numeric tokens).

## Manifest divergences from the DRAFT worth stating

- `page_min_columns`, `operator_supply_pages`, `operator_rows` added;
  `draft` removed. Column labels identical to the DRAFT (no label changed).
- The DRAFT's "the row's printed TOTAL on p5 is already captured via the
  TOTAL column" was incorrect: p5's layer token at the TOTAL position is
  "494t", not numeric. The operator_rows entry supplies that read (4945),
  which the amendment's position-index contract covers explicitly; the
  printed-TOTAL gate then judges the row and passes with the arithmetic
  anchor 4008 + 937 = 4945.
- p4/p5's local-race rows (Everline Jefferson Gilmore, Jean Barnes Wheaton)
  are not recorded under `dropped_local_rows` anymore: their pages are
  operator-supplied and never parse. The no-local-offices scope is
  unchanged; the skip is recorded under `pd["operator_supply_pages"]`.
