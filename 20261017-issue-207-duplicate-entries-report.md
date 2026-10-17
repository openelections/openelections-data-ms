# Issue #207 — duplicate_entries across 37 files (2003–2024)

Resolution report for the full-suite `duplicate_entries` failures listed in
issue #207. Method: 300 duplicate groups (36–37 failing files) were split into
(1) information-free repeats, removed outright; (2) rows mislabeled by the
upstream entry process, relabeled to their true precinct/candidate/county; and
(3) two double-captured precinct blocks from the 2006 scan, collapsed to the
first copy (see "Open follow-up" below).

## How each duplicate was arbitrated

- **County-total reconciliation.** For every numeric-vs-numeric pair the
  candidate's per-precinct sums must equal the certified consolidated county
  total (from the consolidated county files, from the certified 2015
  statewide recap, or from SoS certified PDFs). Every relabel below was
  confirmed this way; the validation script shows the four fixed gaps
  ( Pike SH98, Walthall State Treasurer) reconciling and zero new gaps.
- **Block-boundary evidence.** In each precinct-file duplicate, one copy sits
  inside the row band of a *neighboring block that is missing exactly those
  rows* — i.e. the entry process captured the next block's rows under the
  previous block's label. Relabeling the copy to that block makes every
  affected precinct's candidate set complete.

## Resolutions by file

**Mislabeled precinct rows** (both the consolidated and per-county copies):

| file | misplaced copy | true home |
|---|---|---|
| 2014 general (Covington) | Magee 305, Gerrard 21, Washer 10 @ Mt Olive | Okahay |
| 2014 general (Humphreys) | Ray 5, Shoemake 1 @ Belzoni South 4bs | Belzoni South 5bs |
| 2015 general (Madison) | Bryant 1046 @ Ridgeland #4 | Ridgeland Recreation Center |
| 2015 general (Lauderdale) | Fitch 521, McFarland 75 @ 563-Valley | 564-Vimville |
| 2015 general (Hinds) | Walley 15 @ Jackson prec 90 | Jackson prec 89 |
| 2015 primary | Slater @ South Starkville 44→Sturgis/North Bradley; Short 44, Slater 43 @ Mountain Creek→North Brandon; Slater 30 @ Pine Grove Beat 4→Poplarville Beat 1; Slater 36 @ American Legion→Big Level; Slater 52 @ White Oak→Zion Hill/New Haven; Myers 108 @ Magnolia Comm Ctr (kept in county) |
| 2008 general | Taylor 339 @ Biloxi # 10→New Hope; McCain 498 @ Granby 11→South Prentiss 12 |
| 2008 primary (Pike) | the whole second copy of (01) Progress Library (rows 15–25) → (02) St. James Church |
| 2011 primary | Hollowell 0, Reeves 3, Hosemann 3 @ Grace Methodist → Greenville Industrial College; Bryant 39, Holliday 1 @ County Agent → Mars Hill; the second Governor band @ Beat One North (Bryant 6 + three zeros) → Beat One South |

**Mislabeled candidate names:**

- 2015 Walthall: the extra `David McRae` rows at Varnel (16) and West
  Tylertown (2) are those precincts' `Lynn Fitch` votes — McRae
  101+24+4=129, Fitch 167+16+2=185, both matching the certified county
  totals.
- 2015 Pike SH 98: the `Tasha Dillon 108` copy at Magnolia Comm Ctr. is
  `David W. Myers` (Myers 1635+108=1743, Dillon 1653−108=1545).

**Mislabeled counties** (certified SoS totals):

- 2012 general: the first Jefferson president set (4267/2507/54/20/10/6) is
  **Jefferson Davis** county — verified against the SoS certified 2012
  presidential tabulation (sos.ms.gov); Jefferson's certified set
  (3951/468/3/6/3/2) was already present.
- 2011 general: the second Jefferson insurance set (Chaney 2475, Fondren
  2591, Washer 180) is **Jefferson Davis** county — verified against the SoS
  certified 2011 Insurance Commissioner tabulation (via web.archive.org).
- 2007 general: Jolly Matthews' three `Total` rows are **Forrest 1699 /
  Lamar 67 / Total 1766** (1699+67=1766; matches Toby Barker's 2889+66=2955).
- 2003 primary: Naugher's second `SH15 Total 3737` row is the **SH16**
  (Lee county) total that the file otherwise lacks.

**Removed as information-free** (second identical copy, or blank/`x`/`X`
cells where the numeric twin exists): 2014, 2015 primary files and county
copies (Rankin, Quitman, DeSoto, Scott, Lawrence), 2015 county-file blank
`Total` rows, 2019 Adams blank votes, 2024 Adams verbatim repeats and Bolivar
`X`-vs-vote pairs.

**2006 Jasper/Forrest double-captured blocks:** BEAT 1 HOLDERS-WALDRUP (Jasper)
and DIXI/EAT/WES (Forrest) each appear twice with OCR-variant values; no other
precinct is missing rows, so these are scans of the same block twice. The
first copy was kept and its duplicate removed — no certified Jasper/Forrest
2006 primary county totals were available online during the fix (the SoS no
longer hosts pre-2009 results and archive.org was offline).

## Open follow-up

1. **2006 Jasper/Forrest**: when the 2006 Democratic primary certified county
   totals (or the county recaps) are findable again, verify the retained
   first copies:
   - Jasper BEAT 1 HOLDERS-WALDRUP: Bowlin 3, Fleming 2, O'Keefe 0, Starr 4
     (rejected: O'Keefe 2, Starr 2)
   - Forrest DIXI: Taylor 41, Bowlin 10, Fleming 6, O'Keefe 16, Starr 8
     (rejected: 39/10/11/15/5)
   - Forrest EAT: Taylor 22, Bowlin 0, Fleming 22, O'Keefe 3, Starr 0
     (rejected: 27/0/13/12/2)
   - Forrest WES: Taylor 5, Bowlin 0, Fleming 2, O'Keefe 3, Starr 0
     (rejected: 19/4/5/10/1)
2. `2012/20121106__ms__general.csv` ends at Wayne County (no trailing
   newline); the file appears truncated at creation — Wilkinson through Yazoo
   president/general rows are a separate, pre-existing gap (issue #23's
   general-election item may cover it).
3. Pre-existing, unrelated to duplicates: the 2015 Hinds precinct rows sum
   ~3k-5k above the certified county totals for statewide races (the
   canvas-vs-certified conflict tracked in issue #91), and small pre-existing
   gaps exist in Rankin/Stone/Walthall/Madison (2015 primary/general) and
   Yalobusha/Washington (2011 primary). None were introduced or changed by
   this fix (validated against the pre-fix tree).
4. The PR-scoped Data Tests workflow only checks *added* files, which is why
   duplicates survived on master; consider also testing modified files.

## Sources

- [SoS certified 2012 presidential totals](https://sos.ms.gov/elections/electionresults/2012General/certified%20results/President%20and%20Vice%20President.pdf)
- [SoS certified 2011 Insurance Commissioner totals](https://sos.ms.gov/links/elections/results/statewide/Insurance%20Commissioner_Statewide%20-%20General%20Election%202011%20Results.pdf) (fetched via web.archive.org)
- Consolidated county files in this repo (2014/2015 general+primary, 2008
  general+primary, 2011 primary, 2007, 2003), checked per the
  county-total reconciliation described above.