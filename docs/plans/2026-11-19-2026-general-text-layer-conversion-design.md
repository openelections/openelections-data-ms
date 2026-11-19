# Design: 2026 general election text-layer county conversion

Date: 2026-11-19
Status: approved

## Goal

Convert the four 2026 general election county PDFs that carry an embedded text
layer into per-county OpenElections precinct CSVs, leaving the 78 scanned
counties for a later OCR phase.

Sources: `~/code/openelections-sources-ms/2026/general/<County>_2026_general.pdf`
(SEMS "Official Recapitulation" format: certification cover page, then a
landscape candidates-as-rows x precincts-as-columns crosstab; election date
2026-11-03).

## Input survey findings (verified 2026-11-19)

| County | Pages | Text layer |
|--------|-------|------------|
| Union  | 5     | born-digital, clean |
| Warren | 7     | born-digital, clean |
| Jasper | 5     | scan with noisy OCR text layer ("Elecuon", "Recapltulatlon") |
| Lee    | 13    | scan with noisy OCR text layer |

The other 78 PDFs are pure image scans (0 extractable chars) — later phase.

## Approach decision

Chosen: **deterministic geometry parse** with natural_pdf (repo convention for
text-layer PDFs). Rejected alternatives: adapting the 2024 vision-LLM pipeline
(spends model calls on text already in the file) and PaddleOCR (right tool for
the 78 scans, strictly worse here).

Escalation path for a county that fails gates after parser hardening (most
likely candidate: Lee): render pages and read as a vision model, then
PaddleOCR last. Keep the 2024-style "best attempt wins" ladder.

## Verification stance (user decision)

No official 2026 general county-totals CSV exists and the SoS site is
Cloudflare-blocked from this machine, so files are gated on internal checks
now and flagged "not yet checked against official totals"; re-verify once a
statewide general recap PDF is available in the sources repo.

## Verified parser facts (Union page-2 probe)

- natural_pdf `extract_table()` returns nothing — no ruled lines detected; the
  crosstab must be rebuilt from word/char coordinates.
- All chars report upright; pages are natively landscape (787.7 x 607.0).
- Certification blurb repeats at the top of every table page — exclude that
  region before parsing.
- Candidate/office labels occupy a left x-band (~x0 40-180); numeric cells
  cluster at an even ~45pt x-pitch; precinct headers are vertical char stacks
  above each column; TOTAL is the rightmost header column reading "TOTAL"
  vertically.
- Offices flow down pages; columns align per page.

## Parser rules

- Row-label column: leftmost x-band, rows ordered by y; numeric columns
  clustered by x0; precinct headers rebuilt from vertical char stacks; TOTAL
  column identified by its vertical header text.
- Office map (2024 precedent): `United States-Senate` -> `U.S. Senate`;
  `US House Of Rep NN` -> `U.S. House`, district NN.
- Party codes: `Democrat` -> DEM, `Republican` -> REP, `Libertarian` -> LIB,
  `Constitution` -> CON, Independent -> IND; `Nonpartisan` -> blank party
  (2024 judicial precedent).
- Jasper/Lee noisy text: difflib fuzzy matching for labels, digit cleanup on
  votes; every fuzzy guess must pass the same gates.
- Two-seat judicial races (the one approved judgment call): keep bare office
  label (`Court of Appeals` / `Chancery Court`) + district when only one seat
  of that district appears on the ballot; when two seats appear, append the
  printed seat qualifier to the office (`Court of Appeals Position 2`) so no
  two races share an office+district key. 2024 precedent had one seat per
  district (`Court of Appeals` + district only), so this only diverges when
  divergence is required.

## Gates (all must pass before a county CSV is written)

1. Row-sum vs TOTAL column: per candidate, sum of precinct cells equals the
   candidate's printed TOTAL.
2. Roster consistency: the same race's candidate list identical across the
   counties sharing it (US Senate everywhere; each county's US House district).
3. Structure: header column count == body cell count per page; all numeric
   cells parse; blank cell = 0 only when the row TOTAL still reconciles.

## Output conventions

- `2026/counties/20261103__ms__general__<county>__precinct.csv`
- Header: `county,precinct,office,district,candidate,party,votes` (2024/2026
  per-county precedent; no winner column, no TOTAL rows — totals are
  verification-only).
- Sorted by precinct, office, candidate; precinct names stripped of
  "Precinct", leading zeros, stray quotes.

## Amendment A (2026-11-19): hybrid header sourcing

Real-file probing invalidated one core assumption: the rotated header strip
(precinct names + the TOTAL label) is not recoverable from the text layers.

- Union: every char is `GlyphLessFont` — an invisible Tesseract OCR layer that
  skipped nearly all rotated glyphs (26 fragment chars for ~120 rendered
  glyphs); no "TOTAL" anywhere in the layer.
- Warren / Jasper / Lee: born-Helvetica text, but the rotated header glyph
  runs extract as broken garbage (e.g. Warren's right column strip reads
  `L.. QJ C. I\J ..`), i.e. glyph encoding without a usable Unicode mapping.

What remains reliably extractable: candidate/office row labels, and the
numeric grid (14 well-separated column clusters on Union p2).

Revised approach (user-approved): **hybrid**. The deterministic parser keeps
labels, the numeric grid, and all gates. For each table page, the header strip
is rendered to a PNG and read by the operator (Claude acting as a vision
model — no external model or OCR service). The read is recorded as a
committed JSON manifest per county at `2026/header-reads/20261103__ms__general__<county>__headers.json`
mapping each table page's ordered header labels (including which label is
TOTAL). The pipeline validates every manifest against the parsed grid
(count equality, nearest-center alignment) and keeps all other gates.
`vertical_headers` stays in the module as a non-load-bearing cross-check
utility; column alignment is manifest-driven, and the TOTAL column is
identified by the manifest label, not by `total_col`.

## Out of scope (later phases)

- The 78 scanned counties (PaddleOCR per CLAUDE.md).
- Consolidated statewide precinct file.
- Official county-totals cross-check once a statewide general recap exists.
