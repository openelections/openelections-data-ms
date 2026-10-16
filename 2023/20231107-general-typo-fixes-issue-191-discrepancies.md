# 2022/2023 general — issue #191 typo investigation

Issue: https://github.com/openelections/openelections-data-ms/issues/191
("2022 and 2023 General Election Typo Fixes", filed 2024-12-19 by peter-redistricting-data-hub)

Arbiter for every item: the Secretary of State's per-county **Official Recapitulation**
PDFs (Statewide Election Management System crosstabs — precincts as columns, candidates
as rows), downloaded from `https://sos.ms.gov/elections/electionresults/2023General/<County>.pdf`
and `.../2022General/Official Recaps/<County> County.pdf` (all image-only scans; read as
rendered page images, with column identity anchored on rows whose values are already
source-verified). Source copies kept in `~/code/openelections-sources-ms/` (`2023/*.pdf`,
`2022/Marion.pdf`).

## Summary of what the issue got right and wrong

- All four **2023 vote "swaps"** the issue proposed were already in place in the
  consolidated file (values date to the original import, commit 88a1361) — checked, and
  the source confirms them — **except** that for two of them the issue's *proposed values
  were themselves misassigned*; the official PDFs place the votes at different precincts
  than either the issue or the current file. Two corrections below.
- The **rename chains** were real and not yet applied on master: Noxubee (3), Lowndes (3),
  Calhoun (9), and the Marion 2022 renames in the consolidated file (the 2022 county file
  had already been fixed).

## Items in order

### 1. Pearl River 2023, State House 93 (R) Timmy Ladner — no change needed
Issue: Springhill 3 should be 403 (was 0), "Stephollow 3" 110, Sycamore 5 → 0.
Source (Pearl River.pdf p.8–10, HD93 row, TOTAL 1718): Carriere 5=60, Ceasar 4=522,
Poplarville 3=64, Progress 3=133, Salem 4=426, **Springhill 3=403, Steep Hollow 3=110**,
every other column X (Sycamore 5 prints X). County TOTAL 1718 = sum of our rows.
The file (precinct spellings "Springhill 3"/"Steep Hollow 3") already matched exactly.
The issue's "Stephollow" is the RDH spelling of "Steep Hollow".

### 2. Madison 2023, State Senate 21 (D) Bradford J. Blackmon — FIX APPLIED
Issue: Sunnybrook 0→241, "Lighthouse Church" 241→0.
Source (Madison.pdf p.13, SD21 block, TOTAL 7785): the 247 prints in **The Lighthouse
Church** column; the Sunnybrook Retirement Village column prints X. Sunnybrook is in
State Senate 25 (Michel 374), not 21.
**The issue's proposed value 241 was wrong** — the official sheet's Lighthouse Church
cell reads 247, and the SD21 row TOTAL (7785) confirms 247 in Madison. Our file had 247
but under Sunnybrook. Fix: moved the row to The Lighthouse Church (total-preserving).

### 3. Madison 2023, State House 73 (R) Jill Ford — FIX APPLIED (different from issue)
Issue: Vertical Church 0→635, Twin Lakes 635→0.
Source (Madison.pdf p.17, HD73 row, columns Ridgecrest..Victory, TOTAL 8408): **635
prints in the Twin Lakes Baptist Church column; the Vertical Church column prints X.**
Sunnybrook holds 373. Our file had 635 under Vertical Church — i.e., the repo already
carried the issue's proposed (wrong) fix. Fix: moved the row to Twin Lakes Baptist
Church (total-preserving; county total 8408 unchanged, re-verified).

### 4. Harrison 2023, State House 121 (D) John W. DeDeaux — FIX APPLIED (different from issue)
Issue: East Biloxi 0→481, "Harrison-:-E Orange Grove" 481→0.
Source: **the 481 prints in the E Pass Christian column** (Harrison.pdf p.22, D121 block
continuation; E Biloxi column prints X — p.23 is all X for it too). The printed
county TOTAL for D121 DeDeaux is 2426, matching our row sum.
Additionally, the official pages show this is not an isolated cell: the three precincts
[E Orange Grove, E Pass Christian, East Biloxi] have their votes **right-cycled**
in every county-office row of the file (Chancery Clerk, Circuit Clerk, Coroner,
County Attorney, Sheriff, Tax Assessor, Tax Collector all confirmed against
Harrison.pdf p.22–26; e.g. Chancery Clerk officially 529/746/289 for the three).
State/district rows for the same precincts (Governor, …, SD48/49/50, HD115, DA 02,
HD121 Crawford) are correct and were verified against p.2, 8, 10, 12, 13, 17, 18.
Fix: relabeled the county-office rows plus the D121 DeDeaux row
(E Orange Grove→East Biloxi, E Pass Christian→E Orange Grove, East Biloxi→E Pass
Christian; 25 rows, total-preserving). HD121 Crawford's E Pass Christian=520 was
confirmed correct and untouched.

### 5. Noxubee 2023 precinct renames — FIX APPLIED (as proposed)
Issue chain: District 3 Central→Mashulaville, Mashulaville→Noxubee Alliance Bldg,
Noxubee Human Resource Bldg→Noxubee Civic Center.
Source (Noxubee.pdf p.2): official columns are Brooksville, Cliftonville, Mashulaville,
Noxubee Alliance Bldg, Noxubee Civic Center, Prairie Point, Shuqualak, Summerville.
Value vectors (Governor/LG/SOS/AG/Auditor) confirm each chain step; the other five
precincts already matched (Governor and Auditor rows re-verified; Noxubee Governor
TOTAL 2951 and Auditor 787 match).

### 6. Lowndes 2023 precinct renames — FIX APPLIED (as proposed)
Issue chain: First Assembly→Hunt, Hunt→Immanuel, Immanuel→Lion Hills.
Source (Lowndes.pdf p.2–3): official columns include Hunt, Immanuel, Lion Hills and
have no First Assembly; Governor and Secretary of State rows confirm all three chain
steps by value (Hunt 817/24/15 = old "First Assembly", etc.).

### 7. Calhoun 2023 — "9 precinct names are swapped" — FIX APPLIED (derived; issue had no detail)
Source (Calhoun.pdf p.2–3): official columns are Banner #3, Bruce #3, Calhoun City #1,
Calhoun City #4, Derma #4, Derma #5, Northeast Calhoun #2, Pittsboro #1, Pittsboro #2,
Vardaman #5 — the same name set as our file, so this was a **value shuffle, not a
renaming**. Each precinct was matched by its vote vector across Governor (3 candidates),
Secretary of State (2) and State Auditor (2) — 7-dimensional, all matches unique and
bijective; Vardaman #5 is the one unchanged column (exactly 9 swapped, as the issue says).
Derived mapping (current label → official label):
Banner #3→Derma #5, Bruce #3→Derma #4, Calhoun City #1→Banner #3,
Calhoun City #4→Northeast Calhoun #2, Derma # 4→Pittsboro #1, Derma # 5→Pittsboro #2,
Northeast Calhoun #2→Calhoun City #1, Pittsboro # 1→Bruce #3, Pittsboro # 2→
Calhoun City #4, Vardaman #5 unchanged (306 rows).
This also normalizes the "# 4"-style spacing to the recap's "#4" spellings.
Note: a stale unmerged branch `fix2022-23` contains two *different*, mutually
contradictory Calhoun mappings; both were discarded in favor of the PDF-arbitrated one.
County totals unchanged (all 10 vectors bijective); Governor TOTAL 1631 and
DA 3 Creekmore 3845 match the printed TOTALs.

### 8. Marion 2022 precinct renames — FIX APPLIED in consolidated file (already fixed in county file)
Issue chain: Courthouse→Civil Defense, Jefferson School→Kokomo, Kokomo→Little Rock,
Little Rock→MLK Dr. `2022/counties/20221108__ms__general__marion__precinct.csv` already
carried the corrected names; `2022/20221108__ms__general__precinct.csv` did not.
Source (Marion.pdf, p.2–3, 2022 General): all 22 precincts' Guest/Young values match the
official columns exactly (e.g. Civil Defense 163/58, Kokomo 219/65, Little Rock 142/98,
MLK Dr. 7/49). Fix applied to the consolidated file only (8 rows, total-preserving).
Precinct spelling: our "Carley" differs from the recap's printed "Carey", but the county's
own 2016 precinct registry (`MS 2016 HD by precinct/Marion Co - no splits.xlsx`:
"202 - Carley") spells it Carley, so it is kept.

## Checks run after the fixes
- Every candidate/county/office total in both edited files is unchanged vs. commit HEAD
  (all corrections are total-preserving relabelings) — all 2022/2023 general fixes.
- Per-county sums re-verified against the printed county TOTAL columns: Pearl River
  Ladner 1718, Noxubee Presley 2951 / White 787, Lowndes Presley 9382 / White 9036,
  Calhoun Presley 1631 / Creekmore 3845, Harrison DeDeaux 2426 / Crawford 4126,
  Madison Blackmon 7785 / Ford 8408 — all match.
- No duplicate (county, precinct, office, district, candidate, party) rows introduced.
- `src/verifier.py`: only the pre-existing consolidated-file complaints
  ("county doesn't match filename", office-name spellings) remain, same as before.

### 9. Jackson County 2023, District Attorney 19 — FIX APPLIED (issue #208)
The consolidated file had `Jackson,Grace Baptist Church,District Attorney,19,
Angel Myers McIlrath,REP` **twice**: 963 and 1142.
Source (Jackson County 2023 Official Recapitulation, p.5, chunk
Big Point..Gulf Park Estates; county TOTAL on p.5 and p.7): officially
**Gautier South = 963, Grace Baptist Church = 1142**, county TOTAL 22978. There was no
Gautier South DA row in the file at all — the "Grace 963" row was Gautier South's result
under the wrong label (every other cell of the DA row's chunk matches ours bit-for-bit).
Fix: relabeled the "Grace … 963" row to Gautier South (total-preserving). Post-fix:
no duplicate result keys remain in the file, and the Jackson McIlrath sum equals
the printed county TOTAL 22978.

## Spotted in passing, not changed (out of scope)
- The 2022 consolidated file still lists only U.S. House races (its per-county county
  CSVs are the same); if the source recaps' legislative rows are wanted downstream,
  that's a separate import.