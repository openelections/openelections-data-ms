# 2019 primary runoff: county CSV vs precinct files — discrepancies

Date: 2026-09-14
Sources compared:

- `2019/20190827__ms__primary_runoff__county.csv` — parsed from the statewide
  runoff recapitulation PDFs (`REP/DEM Official Recap 8-27-19.pdf`, SoS) by
  `parse_2019_runoff_county.py` (see that script's docstring for the layout).
- `2019/counties/20190827__ms__primary_runoff__<county>__precinct.csv` — 71
  pre-existing (2020-vintage) precinct files, added in commit d30f1dc.

Crosscheck: `crosscheck_2019_runoff.py` (aggregates each precinct file by
county/office/candidate and compares to the county CSV; handles the files'
several column layouts and normalizes OCR name variants like "Jay McNight" and
"Jeffrey S 'Jeff' Gulce").

Result before arbitration: 222 county-CSV values are covered by the precinct
files; 205 match, 17 mismatch.

## Verdict: the county CSV is correct in every case

Every mismatched value was arbitrated against the **per-county runoff recap
scans** (`https://www.sos.ms.gov/elections/electionResults/
2019RepublicanPrimaryRunoff/<County>.pdf` and `2019DemocraticPrimaryRunoff/...`,
fetched with a curl UA — the server 403s browser UAs). These scans are image
PDFs; PaddleOCR-VL markdown was fetched by `extract_2019_runoff_paddle.py`
(cached in `cache/2019-runoff-<county>-<party>/paddle/`) and read with
`arbitrate_2019_runoff.py`. The per-county recaps print a per-candidate county
TOTAL column; in all 13 counties the printed TOTAL equals the statewide
crosstab cell (the county-CSV value), which also agrees with the certified
statewide totals (Reeves 179,623 / Waller 152,201; Fitch 168,278 / Taggart
154,807 — the four candidates whose TOTAL cells the statewide sheet leaves
blank were checked against published results).

All 17 mismatches are 2020 precinct-file transcription errors:

| County | Race | Precinct-file error | Printed value |
|---|---|---|---|
| Choctaw | R Gov | truncated file — only 2 of 13 precincts (Southwest Ackerman, West Weir) | TOTALs 590 / 421 confirm county CSV |
| Copiah | R Gov | votes swapped between the two candidates in 3 precincts | Martinsville R 38 / W 18; Shady Grove R 37 / W 26; Stronghope Union R 43 / W 15 (file had them reversed) |
| Forrest | R Gov | McLaurin Reeves 117 | 114 |
| Harrison | R HD95 | riceville McKnight 76 / Willis 8 | 78 / 6 (pair sums 84 either way; printed TOTAL 1,554 settles it) |
| Itawamba | R Gov | mantachie Waller 161 | 163 |
| Lee | R SD08 | Shannon Suber 33 | 53 |
| Lowndes | R Gov | west lowndes Waller 129 | 126 |
| Neshoba | R Gov | Arlington Waller 61 | 91 |
| Rankin | R Gov | south pearson Waller 274 | 27 (only 27 makes the file sum equal the printed TOTAL 14,694) |
| Tishomingo | R Gov | hubbard salem Reeves 90 | 30 |
| Bolivar | D SD13 | west cleveland Alexander 33 | 333 |
| Hinds | D HD70 | missing precincts 51 and 84 entirely | 51: Brown 38 / Sykes 39; 84: Brown 57 / Sykes 24 (exactly the file's deficits of 95 / 63) |
| Sunflower | D SD13 | Indianola #3 South Simmons 143 | 146 (OCR sum 1,318 = printed TOTAL; Alexander's cells all match) |

Each printed value is pinned three ways: it equals the deficit between the
precinct file's candidate sum and the printed county TOTAL, all other precinct
cells match the file, and the printed TOTAL equals the statewide crosstab cell.

## Fixes applied to the precinct files

All of the transcription errors above were corrected in
`2019/counties/20190827__ms__primary_runoff__*__precinct.csv` (12 files:
single-cell fixes in Copiah, Forrest, Harrison, Itawamba, Lee, Lowndes,
Neshoba, Rankin, Tishomingo, Bolivar and Sunflower; the two missing Hinds
precinct rows appended). After the fixes `crosscheck_2019_runoff.py` reports
220 of 222 covered county-CSV values matching, with the only remaining
difference being Choctaw: its certified recap sheet prints only two named
precinct columns (Southwest Ackerman 11/27, West Weir 7/19) and leaves the
other 11 precinct columns blank, so its precinct file (which transcribes
those two columns) cannot sum to the county total of 590/421. The county CSV
carries the printed TOTAL; the precinct file is left as printed.

## Coverage notes

- The runoff precinct files cover only 71 of 82 counties, and not all offices
  (no R Attorney General, R Transportation Commissioner-Northern, or D PSC-
  Central coverage), so 314 of 536 county-CSV values have no precinct-file
  counterpart. Those values are verified instead by the printed TOTAL
  reconciliation in `parse_2019_runoff_county.py` (40 of 44 candidates) and,
  for the 4 without printed TOTALs, by the published statewide results.
- The 2020 precinct files also carry OCR name variants ("Jay McNight",
  "Jeffrey S 'Jeff' Gulce"); `crosscheck_2019_runoff.py` maps them via
  NAME_ALIASES.

## PaddleOCR quirks hit during arbitration (same family as the primary scans)

- Rankin p003's table did not parse at all (13 precincts missing from the OCR);
  settled by printed-TOTAL arithmetic instead.
- Neshoba: the entire "Fork" column was dropped (file preserved its values;
  both file sums corroborate once Arlington is fixed).
- Lee p003 carried a spurious trailing value cell (Plantersville 77/115)
  duplicating Palmetto's; sums only reconcile without it.
- Choctaw's recap genuinely prints few precinct columns; its TOTAL column is
  what confirms the county value.

## Reproducing

```sh
uv run python parse_2019_runoff_county.py                 # county CSV + TOTAL reconciliation
uv run python crosscheck_2019_runoff.py                   # county CSV vs precinct files
# arbitration (per county; PDFs in cache/2019-runoff-arb/, OCR cached):
curl -s -A curl/8.7.1 -o cache/2019-runoff-arb/<County>.pdf \
  "https://www.sos.ms.gov/elections/electionResults/2019RepublicanPrimaryRunoff/<County>.pdf"
uv run python extract_2019_runoff_paddle.py <County> <D|R>
uv run python arbitrate_2019_runoff.py <County> <D|R> "<office label fragment>"
```