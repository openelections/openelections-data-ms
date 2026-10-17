# 2024 general — county-vs-precinct discrepancies (Pike, Tunica)

`src/crosscheck_2024_general.py` sums every committed per-county precinct file
per (office, candidate) and compares it to the certified total in
`2024/20241105__ms__general__county.csv`. Of **1,954** per-candidate checks
(up from 1,795 once the local races were extracted from the last 21 counties),
**1,323 reconcile exactly**, **611 are local races with no certified total**, and
**20 mismatch — all of them in two counties**.

| County | Mismatches | Pattern |
|---|---:|---|
| Pike | 14 | precinct sum is **~21% higher**, non-uniformly |
| Tunica | 6 | precinct sum is **exactly 1 lower**, every contest |

Every other county reconciles exactly for every certified race, and
`MISSING_PRECINCT` is 0 — no precinct row names a precinct the source lacks.

Two caveats on the "1,323 reconcile exactly" figure, both pre-existing and
neither a precinct-vs-county issue in the data:

- **The 611 `MISSING_OFFICIAL` entries are the local races** (Election
  Commissioner, School Board, School Trustee, Tax Assessor, Coroner, Levee
  Board, Constable, Justice Court, and the local ballot measures). The certified
  county CSV does not carry them at all, so the precinct files are now the only
  source for them and there is nothing to reconcile against.
- **Jefferson Davis is skipped entirely.** The crosscheck pairs a precinct file
  with a certified county by turning the county name into a filename slug
  (`Jeff Davis` → `jeff_davis`) and comparing it to the file's slug
  (`jefferson_davis`), so the two never match, it prints `! no official totals
  for jefferson_davis`, and it `continue`s past the file. Its 340 rows and **20
  candidate-contests are therefore outside the 1,954 checks** and have never
  been compared to the certified totals. This is a filename convention
  mismatch, not a data divergence: the file's own `county` column reads
  `Jeff Davis`, the same spelling the certified CSV uses. `merge_2024_general_staging.py`
  already resolves this county by its `county` column for the same reason (its
  docstring notes the slug/file split), and the crosscheck's pairing is the
  thing that should follow suit; until it does, Jefferson Davis is the one
  county whose federal, statewide and judicial rows are unverified against the
  county CSV.

Adams was the third county here until the 2026-09-27 OpenParser re-read, and its
two mismatches are now cleared; its section is kept below because the failure
mode is instructive.

## Adams — duplicated judicial rows (an extraction defect) — **resolved**

Both mismatches were in the same contest, and both were exactly double:

| Candidate | precinct sum (before) | certified | ratio |
|---|---:|---:|---:|
| David P. Sullivan | 10,618 | 5,309 | 2.00 |
| Dawn H. Beam | 8,472 | 4,236 | 2.00 |

The cause was visible in the file itself: the contest held 76 rows but only 44
distinct `(precinct, candidate)` keys — 32 rows were duplicates, spread over
**16 of the contest's 22 precincts**, and every other key in the county appeared
exactly once. The crosscheck sums rather than dedupes, so it saw double.

**But this was not a mechanical duplication, and de-duplicating would not have
fixed it.** The 16 duplicated precincts covered only part of the contest, and
the 6 that appeared once were a small, unrepresentative remainder:

| Candidate | total | one copy of each duplicated precinct | + singly-listed precincts | certified |
|---|---:|---:|---:|---:|
| David P. Sullivan | 10,618 | 4,758 | **5,860** | 5,309 |
| Dawn H. Beam | 8,472 | 3,757 | **4,715** | 4,236 |

So collapsing the duplicates lands on 5,860 against a certified 5,309 — still
551 high. The file had both a duplication problem and a wrong precinct set, and
the raw total being *exactly* 2× certified was a coincidence of the two, not a
clean doubling to halve.

The OpenParser re-read of the county resolves it: the fresh file carries no
duplicate keys, and both candidates now sum to **5,309 and 4,236 exactly** —
the certified totals. The three phantom precincts the committed file also
carried (`Dist. 1, Contribute Precinct`, `Dist. 3, Maryland Precinct`,
`Dist. 3, Nos Bluffs Precinct`) are gone with them. The same county produced the
office-label-in-the-precinct-column failure mode that
`extract_2024_general_pdf.py` now drops rows for; both trace to the same
judicial table being read badly in the original run.

## Pike — a genuine conflict between two certified documents

Pike's 14 mismatches are not a doubling and not OCR noise. They are a
consistent **~21% over-count** across every race:

| Office | Candidate | precinct sum | certified | diff |
|---|---|---:|---:|---:|
| U.S. House | Michael Guest | 11,345 | 9,425 | +1,920 |
| U.S. Senate | Roger F. Wicker | 8,205 | 6,719 | +1,486 |
| U.S. Senate | Ty Pinkins | 7,130 | 5,898 | +1,232 |
| President | Donald J. Trump | 7,943 | 6,504 | +1,439 |
| President | Kamala D. Harris | 7,402 | 6,091 | +1,311 |
| Southern District-Supreme Court Dist. 2 Position 2 | David P. Sullivan | 6,992 | 5,972 | +1,020 |
| Southern District-Supreme Court Dist. 2 Position 2 | Dawn H. Beam | 5,958 | 4,893 | +1,065 |

The decisive fact: **the PDF's own printed TOTAL for Michael Guest is 11,345**,
which equals the precinct sum exactly. The extraction is faithful to the
document; the document disagrees with the certified county totals. Per the
project's reconciliation rule, the crosstab's printed TOTAL matching the
extracted sum proves the *reading* is right even where the totals conflict —
there is nothing for OCR to fix here.

So Pike is a **source-level conflict between two certified documents**, of the
same kind already documented for the 2024 primary in
`20240312-primary-noxubee-county-vs-statewide-discrepancies.md`. Note also that
Pike is one of the counties with an amended filing in this cycle
(`Pike Updated.pdf`), so a superseded precinct document is the likely origin.

**Decision:** keep the precinct file's cells as printed, and keep
`20241105__ms__general__county.csv` as the statewide recap prints it, exactly as
the Noxubee precedent does. The 2026-09-27 OpenParser re-read **reproduces the
same printed TOTAL**, which confirms the conflict, so the decision is now final
rather than provisional. That leaves a visible county-vs-precinct difference
that originates in the sources rather than in this data. `KNOWN_SOURCE_CONFLICTS`
in `src/extract_2024_general_openparser.py` names Pike for this reason.

## Tunica — a uniform off-by-one

All six Tunica mismatches are exactly one vote low, across unrelated contests:

| Office | Candidate | precinct sum | certified |
|---|---|---:|---:|
| President | Kamala D. Harris | 1,836 | 1,837 |
| U.S. House | Bennie G. Thompson | 1,920 | 1,921 |
| U.S. Senate | Ty Pinkins | 1,797 | 1,798 |
| Northern District-Supreme Court Dist. 3 Pos. 1 | Robert P. Bobby Chamberlin | 2,001 | 2,002 |
| Northern District-Supreme Court Dist. 3 Pos. 2 | Jimmy Maxwell | 2,018 | 2,019 |
| Court Of Appeals 02-District 2 Position 2 | Latrice Westbrooks | 1,985 | 1,986 |

A uniform −1 across every contest is the signature of a whole-ballot
difference, not a digit misread (which would hit one candidate, not all six
identically). The likely explanation, from the original investigation: Tunica's
PDF is not a single document — it mixes Electionware "Summary Results Report"
county-total pages (1–4) with SEMS precinct pages (5–9). The certified total
1,837 matches the Electionware pages, while the SEMS precinct rows sum to
1,836.

This one is **resolved, and the conflict is real**: Tunica was re-read on
2026-09-27 (OpenParser credits were available by then), and the fresh read
reproduces 1,836 for Kamala D. Harris — the same value the precinct rows summed
to before. Both backends produced it independently, and the −1 is uniform across
all six certified contests, which no digit misread can be.

The re-read also settles where the sheets' own arithmetic sits, which is the
fact this disposition turns on: **Mistral and Textract each print a TOTAL column
for these contests, and every printed TOTAL equals the precinct sum** (1,985 for
Latrice Westbrooks, 2,001 for Robert P. 'Bobby' Chamberlin, 1,836 for Harris)
while the certified county CSV says 1,986, 2,002 and 1,837. So the sheet's own
arithmetic agrees with the extraction, the extraction is faithful to the
document, and the document disagrees with the certified county CSV. Per the
project's reconciliation rule a printed TOTAL that matches the extracted sum
proves the reading is right, so **the precinct file keeps 1,836** and the county
CSV keeps 1,837 — the same disposition as Pike, and recorded as such in
`KNOWN_SOURCE_CONFLICTS`
(`src/parse_2024_general_county_textlayer.py`).

The committed file already carried 1,836, so this pass changed no Tunica vote
value; what changed is that the discrepancy is now confirmed by two independent
reads of the source rather than inferred from one. (Note that Tunica's cached
intermediate happens to report these contests with *no* printed TOTAL, which
routes them through the gate's no-TOTAL branch; that cache entry predates this
pass and no longer reflects either backend's current read.)

## Duplicate rows in the committed data (Adams, Bolivar)

Separately from the certified-total comparison, a scan of the committed files
for repeated `(precinct, office, district, candidate, party)` keys — the check
CI's `duplicate_entries` test performs — finds **40 duplicate rows in two
counties**:

| County | Extra rows | Contest(s) |
|---|---:|---|
| Adams | 32 | Southern District Supreme Court Dist. 2 Pos. 2 |
| Bolivar | 8 | Election Commissioner; all four school-trustee districts |

These were inherited by the consolidated
`2024/20241105__ms__general__precinct.csv` (40 duplicate rows among its 29,878),
so the published statewide file failed `duplicate_entries`. Adams was the
duplication described above; Bolivar's 8 were the local-race counterpart — the
same re-extraction defect landing on a different table.

Confirmed against the real test suite rather than an approximation of it: with
`~/code/openelections-data-tests/run_tests.py` pointed at the 83 committed 2024
general precinct files, `duplicate_entries` failed on exactly three of them —
`20241105__ms__general__precinct.csv` (40), Adams (32) and Bolivar (8) — while
the other three tests passed. (The Bolivar pair was the same key carrying two
different values, `299` and `X`, so it was a conflict rather than a repetition;
Adams' was a verbatim repeat.)

**All 40 are now gone.** The 2026-09-27 OpenParser re-read covers Adams and
Bolivar (both were in the cached 61), and neither its intermediates nor its
normalized output repeats a row. Re-run against the installed files, all four
CI tests pass on the 83 2024 general precinct files. The count that was
predicted here — a merge-operation total of +10,502 −722 against a net file
change of +9,740 — is exactly reconciled by these rows: the merge keys rows on
`(precinct, office, district, candidate, party)`, so a pre-existing duplicate
collapses in its accounting while the file row count falls by all 40.

## Why these were not caught earlier

`verify_2024.py` compares the extracted sum against the PDF's own printed
TOTAL and against the certified county total. Adams and Tunica both passed the
*internal* check (their sums matched something), so a verification report alone
does not surface them — only the county-vs-precinct crosscheck does. That is
why `crosscheck_2024_general.py` is the scoreboard for whether the committed
data is right, and `verify_2024.py` is only the per-page gate during
extraction.

## Status

Resolved and installed on 2026-09-27: Adams' two mismatches and all 40 duplicate
rows (Adams 32, Bolivar 8), across the 61 counties the OpenParser backend
returned. Pike's 14 and Tunica's 6 remain, and both are source-level rather than
extraction defects; both are now confirmed from a second independent read, so
neither is provisional.

**Coverage is now complete: all 82 counties have been re-read.** The 21 counties
that returned HTTP 402 on the first attempt — Jones, Sharkey, Simpson, Smith,
Stone, Sunflower, Tallahatchie, Tate, Tippah, Tishomingo, Tunica, Union,
Walthall, Warren, Washington, Wayne, Webster, Wilkinson, Winston, Yalobusha,
Yazoo — were re-read once credits were available and installed the same day;
the fourth pass in `20241105-general-source-reconciliation.md` covers them. No
county still carries an earlier pass's output.

The one gap that remains is the crosscheck's pairing of Jefferson Davis, above:
its 20 candidate-contests are not checked by `crosscheck_2024_general.py` at all.
That is a defect in the checker rather than in the data, and it is the only
county for which the federal/statewide/judicial reconciliation is missing.

## What the regeneration changes — a rehearsal on ten counties

Running `src/merge_2024_general_staging.py` in report-only mode against the ten
counties extracted first, then normalizing a copy of them and checking the
result against the same conditions CI enforces, is how the following was
established before anything was installed:

- **Adams' 32 duplicate rows are removed** and no staged file carries a
  duplicate row of its own, so the 40 duplicates described above go away with
  the regeneration. Office canonicalization was the risk here — two rows that
  are distinct as read can collide once their office labels are canonicalized —
  and across these ten counties it does not happen.
- **Amite loses `Election Commissioner|1`** (22 rows, 1,240 votes). Amite
  passed verification, and this is precisely the hole the lost-contest check
  was added for: the contest contributes no rows to the extraction, so it
  contributes no key to the verification report either, and every gate that
  compares *values* is blind to it. Only the committed roster can see it. The
  committed EC 1 rows are themselves defective (two phantom precincts and a
  leaked U.S. Senate value), so restoring them verbatim is not the fix —
  Amite is re-extracted.
- **Carroll's staged file is corrupt** (`Salem` doubled, a precinct named
  `430 School`), which is the failure mode it is being re-extracted for. It
  does not reach `2024/counties/` while it fails, so a failed county costs
  coverage rather than correctness — it keeps its committed file, and its local
  races stay missing.

Both of those were resolved by the re-extraction that followed: the installed
Amite file now carries `Election Commissioner|1` (22 rows) alongside 3 and 5,
and Carroll's installed file has no doubled `Salem` and no `430 School` — 20
rows for each of its precincts, one contest apiece.

The rehearsal also caught a documentation error worth recording: `CLAUDE.md`
gives the results-CSV column order as
`county,precinct,office,district,party,candidate,votes`, but every committed
precinct file — and therefore the convention the pipelines must emit — is
`county,precinct,office,district,candidate,party,votes`, with `candidate`
before `party`.

This is a repo-wide deviation, not a typo in `CLAUDE.md`. The sibling
OpenElections repos follow the documented order — `openelections-data-al`,
`-ga` and `-tn` all emit `county,precinct,office,district,party,candidate,votes`
— so Mississippi is the outlier. It is also internally inconsistent: the
Mississippi precinct files put `candidate` first while
`2024/20241105__ms__general__county.csv` puts `party` first
(`county,office,district,party,candidate,votes`). The re-extraction emits
`candidate,party`, matching the precinct files it replaces, so the regeneration
does not change the deviation either way. Aligning Mississippi with the org
convention is a separate, repo-wide decision and is deliberately not made here.
