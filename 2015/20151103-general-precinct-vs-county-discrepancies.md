# 2015 general — precinct sums vs county totals (issue #91)

Data: `2015/20151103__ms__general__precinct.csv` (consolidated precinct file, 46,182 rows)
compared to `2015/20151103__ms__general.csv` (county file). Candidates matched on
normalized names (with middle-initial fallbacks), offices on name+district, parties
normalized. Official arbiter: the SoS **2015 General county Official Recapitulation**
PDFs (recovered from the Wayback Machine capture of
`sos.ms.gov/elections/electionresults/2015General/county Recaps/…` and stored in the
sibling sources repo at `~/code/openelections-sources-ms/2015/general-county-recaps/`).

## 1. Mis-labeled county-total rows inside the precinct data — 60 rows, verified

- DeSoto: precinct `600 DE SOTO MS` (23 rows) and `600 DESOTO MS` (10 rows)
- Holmes: precinct `HOLMES MS` (27 rows)

For 58/60 (race, candidate) slots the row's votes are *exactly* the county file's
certified county total (2 are name variants of the same value). These rows are county
TOTAL rows mis-typed as precincts, so the county sums run double in comparisons
(e.g. Holmes Governor: precinct rows sum 3220 vs certified county total 1610 — the
per-precinct rows alone sum exactly 1610). They should be dropped.

## 2. Hinds — the issue's named county: the county file is wrong, precinct data is right

Official Hinds recap (Hinds.pdf p.2 for Bolton–Clinton p.11–12 for Precinct 94–Tinnin,
printed county TOTALs on p.12): Bryant **22403**, Gray **33548**, O'Hara **1012**;
AG Hood **43464** / Hurst **14335**; SA Pickering **22280** / Pritchett **34082** /
Walley **646**; etc. Our consolidated precinct rows match these printed totals exactly
for all 8 flagged statewide offices (and spot-checked precincts: Bolton 192/428/9 ✓).

The county `2015/20151103__ms__general.csv` Hinds rows (Bryant 19530, Gray 30734,
AG Hood 40014…) are **2.8k–6k short per candidate** on every flagged office — that is
the cause of the issue's "Hinds does not match statewide" and of most of the precinct
file's statewide excess (+7.2k on Governor ≈ Hinds 5.8k + Simpson 1.4k + small residuals).
Fix direction: rebuild the Hinds rows of the county file from the official recap.

## 3. Simpson — same direction: county file short, precinct data = official

Official Simpson recap (Simpson.pdf pp.2–4; printed TOTAL p.4): Bryant **5656**,
Gray **2077**, O'Hara **87** — our precinct per-precinct cells match every page-2
precinct (Bowie 139/79/2 ✓ …) and the TOTAL exactly. County file: 4827/1677/72 (short).

## 4. Candidate-value transpositions in the precinct data

- **Clay**: Governor Bryant/Gray rows are transposed per precinct. Official Cairo:
  Gray 112, Bryant 135, O'Hara 4; ours has Bryant 112 / Gray 135. Same through
  Pine Bluff (official Gray 185/Bryant 81; ours Bryant 170?), Cedar Bluff, etc.
  The county file has the official attribution (Bryant 3601/Gray 3547).
- **Lafayette**: same reversal (official Oxford 1: Gray 514/Bryant 952; ours Bryant
  514/Gray 992 — also with digit drift, 952 vs 992). County file attribution correct.
- **Covington**: per-precinct transposition only. A full-resolution read of the
  official recap (p.2) settles it: Collins = Gray 402 / Bryant 658 / O'Hara 16, and
  the officially-attributed county totals are Bryant 4471 / Gray 1838 — as the
  county file has them. Only the per-county precinct rows were transposed
  (ours Bryant 402 / Gray 658), fixed by the label swap; no 638-vs-658 drift exists.
- **Leflore**: State Auditor Pickering/Pritchett rows transposed (ours Pickering 3932
  vs county file 2822; officially Pritchett carries the larger number in this county).

## 5. Party-label swaps in the precinct data (values correct)

- **Amite**: `Stacey E. Pickering` rows are labeled `Democrat` and `Jocelyn 'Joce'
  Pepper Pritchett` rows `Republican` (values match the official recap exactly, e.g.
  Amite River: Pickering 93 ✓ / Pritchett 119 ✓). Also `Joceyln` vs `Jocelyn` spelling.
- Senate-district rows statewide (from the certified-party cross-check):
  SD29 (Blount/Broadwater), SD37 (Dearing/Sojourner), SD42 (Johnny Ishmel Henry),
  SD5 (J.P. Wilemon Jr.) have candidate rows split across the wrong party labels;
  the certified rows use one party per candidate.

## 6. Junk rows: turnout labels, X cells, write-in handling

- **Pike**: State House 53/96/97/98 and State Senate 37/38 contain `Registered` and
  `Ballots` rows (pure turnout rows, not candidates) plus `Write-in` rows — explaining
  every Pike race delta exactly (SH96 +1747, SH97 +4420, SH98 +8863, SD37 +1119,
  SD38 +4540 = Registered+Ballots+Write-in sums). The other Pike deltas are write-in
  sums only. Turnout rows should be removed from a results file.
- **Tishomingo**: 26 State House 1/21 rows have literal `X` votes. And our
  `Springhill` precinct's LG/SOS/AG (+ Pickering's SA row) rows contain **Paden's**
  values (our Springhill = Paden 44/137/45/139/102/90; official Springhill =
  92/245/93/258/180/194), reproducing the county deltas exactly (LG 176, SOS 185,
  AG 182). Name typos: `Charles E. Grahm`, `Jocelyn 'Joyce' Pepper Pritchett`.
- **Write-in rows** exist in the precinct data (DeSoto, Jackson, Pike, Rankin and
  others) but the county file has none — every county where certified totals include
  write-in votes shows that small systematic delta (DeSoto −49/−65/−268…; Jackson
  −11…−308; Rankin +1…+253).

## 7. Remaining duplicate-key groups (4)

- `Hinds,Jackson prec 90,State Auditor,District 19?? — Lajena Walley (Ref)` rows 15 & 2
- `Lauderdale,563 - Valley,State Treasurer` — Lynn Fitch 53 & 521; Viola McFarland 11 & 75
- `Madison,Ridgeland #4,Governor` — Phil Bryant 145 & 1046

For Lauderdale and Madison, keeping **both** rows reproduces the county file exactly
(12729/15443; 18937), i.e. the double-keyed pair appears to be legitimate
(same-named split precincts/ballot styles); for Hinds' `Jackson prec 90` (ours 631 vs
county 615) one row of the pair looks spurious — needs the official recap.

## 8. Remaining county mismatches not yet source-arbitrated

Small per-office deltas (precinct sum vs county file), counties with the flagged
offices: Tishomingo (AG/LG/SOS/Auditor, = item 6), Tallahatchie (LG −10, SOS
Graham −74/Walker +35, Auditor −4), Winston (Auditor −306), Sunflower (SH31 −159),
Tippah (AgComm +289), Tate (Gov/LG −20), Itawamba (AgComm +38), Lee (AgComm +11),
Lincoln (LG +10, AgComm +2), Marion (AgComm +10), Marshall (LG +9),
Jefferson (AgComm +36, Ins −50, Auditor +13/−50), Harrison (8 statewide offices,
each −1), Madison (Gov, explained by the Ridgeland #4 pair above),
Lauderdale (Treasurer, ditto).

## 9. State Treasurer statewide puzzle

The county file's TOTAL rows give Viola McFarland as `Ref` with 134014 and
Lynn Fitch 511465; the precinct file's rows for Jackson County scramble the two
candidates (ours Fitch 9555 vs county-file 19244; McFarland 14839 vs 3753). The
Jackson County source is a Circuit-Clerk *fax* (DEC-01-2015, header on the PDF) whose
state-office blocks appear partially duplicated/reversed between the State Auditor and
State Treasurer sections — needs a careful re-read of `jackson_2015.pdf` (pp.2–4) or a
full OCR pass before fixing.

## Statewide reconciliation (after removing the 60 total-as-precinct rows)

| office | precinct-file sum | county-file TOTAL row | delta |
|---|---:|---:|---:|
| Governor | 725,396 | 718,185 | +7,211 |
| Lt Governor | 718,128 | 711,283 | +6,845 |
| Secretary of State | 717,895 | 710,785 | +7,110 |
| Attorney General | 722,690 | 716,161 | +6,529 |
| State Auditor | 714,744 | 708,880 | +5,864 |
| State Treasurer | 654,309* | 645,479 | +8,830* |
| Ag & Commerce | 702,521 | 704,913 | −2,392 |
| Insurance | 577,488 | 585,257 | −7,769 |

*includes McFarland name-variant splits. These deltas ≈ the Hinds/Simpson county-file
shortages (± small residuals); State House/State Senate statewide sums match the
certified rows for 122 of 132 slots (the exceptions are Pike's junk rows, DeSoto/Jackson
write-ins, and the ±1…−11 transcription residuals).

## Recommendation

Precinct-file fixes (drop 60 total-as-precinct rows, delete Pike turnout rows, fill
Tishomingo `X`/Springhill gaps, swap Clay/Covington/Lafayette/Leflore candidate rows,
correct Amite + SD29/37/42/5 party labels, resolve the Jackson Treasurer scramble
against the fax) and county-file fixes (Hinds + Simpson rows from the official recaps,
Covington swap, add write-in rows where the recaps carry them). Every official recap
PDF needed for arbitration is in `~/code/openelections-sources-ms/2015/general-county-recaps/`.

## APPLIED (precinct-file side; branch issue-91-precinct-fixes; src/fix_2015_general_precincts.py)

Applied to the individual per-county files only (`2015/counties/`); the consolidated
`2015/20151103__ms__general__precinct.csv` will be regenerated from them in a later
step, and the county file is intentionally untouched for now. Write-in rows were kept.

- Dropped: DeSoto `600 DE SOTO MS`/`600 DESOTO MS` (33), Holmes `HOLMES MS` (27);
  turnout rows in the office field (DeSoto 86, Pike 58, Rankin 49) plus Pike's
  candidate-field `Registered`/`Ballots` rows; Tishomingo's 26 `X` rows.
- Candidate spellings unified to the certified spellings (matched by unique
  edit-distance/suffix within office+district): ~2,700 rows across ~70 files —
  Grahm/Graham, Finch/Fitch, Hoseman/Hosemann, Joceyln/'Joyce'/'Jocelyn Pepper'/
  'J Pepper' Pritchett variants, O'Harra, Rober Gray, Rnady Walker, Tabe Reeves,
  Rosa S./'Walker' Williams, Hyde-Simth/Hyd-Smith, Andy Hyde-Smith (Alcorn, merged
  into the certified row), Cathy Toole variants, Addie Voting Precinct Lee Green,
  Sam C. Mims IV / 'Sam Mims V' (SH97), 'Sampson Jackson', 'Michael Watson' (SD51),
  'Terry Burton', 'Philip Moran' (SD46), 'Tommy Gollott', 'Boyd Kendall',
  'Johnny Ishmel Henry', 'Karl Malinski Gibbs', 'Bryant W. Clark', 'Lataisha M.
  Jackson', 'Jerry R. Turner', 'Randy P. Boyd', 'Gary A. Chism', middle initials
  and ", Jr./, Sr./, III" variants, etc. Unmatched real local candidates (PSC,
  Transportation, DA 1/12/13/17, supervisors, constables, judges, school boards,
  the Initiative 42 rows, `Kathy Sikes`, `Rosa B. Walker`'s original) are documented
  but left as-is.
- Party labels corrected to the certified party per candidate (~340 rows): the
  Amite-area State Auditor cluster (Amite/Attala/Benton/Bolivar/Greene — Pickering
  rows labeled Democrat, Pritchett rows Republican), Hinds SD27
  (Frazier/Downing) and SD29 (Blount/Broadwater), Itawamba SD5 (Wilemon),
  Pike SD37 (Dearing/Sojourner), House 5 (Marshall Faulkner), 16 (Oktibbeha
  Turner), 23 (Grenada Beckett), 27 (Madison Walker/Gill), 53 (Franklin
  Mangold), 87 (Lamar P.B. Johnson IV), 100 (Lamar Morgan), the Hinds (112),
  Pearl River (32) and Alcorn (6) McFarland rows (canvasses print them Reform),
  and Rankin's 5 stray-label rows. Each slot verified: ours' by-candidate totals
  equal the certified totals exactly, with the votes split across two party
  spellings — so only labels moved.
- Transposed-candidate label swaps (values stay in place; verified cell-level
  against the official recaps): Clay (Governor, all 14 precincts), Covington
  (Governor 17, State Auditor 17), Lafayette (Governor 18, State Auditor 18),
  Leflore (State Auditor 18).
- Tishomingo `Springhill`'s LG/SOS/AG/SA rows restored to the printed Springhill
  column (official p.3) instead of the duplicated Paden values; its two State
  Auditor Pritchett cells corrected to the printed values (Iuka 315, Coles Mill 67).

Post-fix state: 0 duplicate-key groups in the county files' content; per-candidate
statewide sums now differ from the certified TOTAL rows only by the still-unfixed
county-file rows (Hinds, Simpson — deferred) plus ~40 per-cell residuals ≤ ±385
(DeSoto ±1–29, Jefferson ±36–50, Jackson Co. AG/SA ±264–385, Itawamba 29,
Lee/Lincoln/Marion ≤ ±10, Marshall LG −9, Tallahatchie ≤ ±74, Tate −20,
Sunflower SH31 −159, Tippah AgComm −289, Winston SA −306, Harrison = county file
short by exactly 1 on all eight offices — also a county-file slip). Those
per-cell residuals are the remaining precinct-side work: each needs its county
recap block read (PDFs staged) or, for Jackson Co.'s State Treasurer/State Auditor,
a careful re-read of the fax (see item 9 above).