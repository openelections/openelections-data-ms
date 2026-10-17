# 2024 general — source reconciliation and regeneration

Tracking the changes made to the committed 2024 Mississippi general election
CSVs while bringing them in line with the sources in
`~/code/openelections-sources-ms/2024/general/`.

Sources:

| File | What it is |
|---|---|
| `2024 Official Statewide Results.pdf` | text-layer PDF; President, U.S. Senate, U.S. House, and the 7 judicial contests — **statewide totals only, no precincts** |
| `2024ElectionRecapSheets.csv` | SoS consolidated recap; the source of `20241105__ms__general__county.csv` |
| 82 county PDFs | official recapitulation scans — the precinct-level source |

## What was missing, and why

Two independent defects, both now fixed:

1. **The consolidated precinct file had no judicial races.** `src/statewide_generator.py`
   filtered every row against a hardcoded federal/statewide allow-list, which
   silently dropped all four Supreme Court and three Court of Appeals contests.
   22,120 rows → 29,878.
2. **The per-county precinct files labeled all judicial contests `Supreme Court`
   or `Court of Appeals`** — collapsing two seats into one label per county
   (Northern District has both Position 1 and Position 2) and breaking joins
   against the county CSV, which uses the full printed names.

Local races were the last gap: they exist in every county PDF but appeared in
only 14 counties' committed files (Election Commissioner, School Board, Tax
Assessor, Coroner, Yazoo-Mississippi Delta Levee Board/Commissioner, and
others). The second pass added them for all 82 counties from the county PDFs
(29,878 rows); a third pass re-read 61 of those counties with a different
backend and took the file to 39,618 rows. Both are described below.

## Changes made

### 1. Judicial office labels normalized — 82 files, 6,660 rows

`src/normalize_2024_general_offices.py` (`cache/2024/reports/judicial-office-normalization.csv`
holds the full before/after audit trail — the report CSVs live under `cache/`
because a non-data CSV inside a year directory is picked up by the CI glob).

Each generic row is relabeled by matching its candidate against the county's
official roster in `20241105__ms__general__county.csv`: a candidate can only run
for one office in a county, so the mapping is deterministic. The `district`
column already carried the judicial district number, and it was checked against
the district embedded in the resolved office name.

`Supreme Court` and `Court of Appeals` → 7 real contests, 100% unambiguous:

| Rows | Resolved office |
|---:|---|
| 2,685 | Central District-Supreme Court District 1(Central) Position 3 |
| 1,232 | Southern District-Supreme Court District 2(Southern) Position 2 |
| 602 | Northern District-Supreme Court District 3(Northern) Position 1 |
| 602 | Northern District-Supreme Court District 3(Northern) Position 2 |
| 816 | Court Of Appeals 05-District 5 Position 2 |
| 371 | Court Of Appeals 02-District 2 Position 2 |
| 352 | Court Of Appeals 03-District 3 Position 1 |

0 ambiguous candidates, 0 unknown candidates, 0 district mismatches. No vote
value was altered — this is a relabeling only.

### 2. Consolidated precinct file regenerated — 22,120 → 29,878 rows

`src/statewide_generator.py` now carries every office through; the allow-list is
opt-in (`--legacy-statewide-only`). Regenerated with:

```bash
uv run python src/statewide_generator.py generate_consolidated \
    2024 "20241105__ms__general__*__precinct.csv" \
    20241105__ms__general__precinct.csv
```

No rows were lost: every one of the 22,120 original rows is present in the new
file. The glob is scoped to `20241105` because `2024/counties/` also holds the
20240312 primary precinct files.

## Verification

`src/crosscheck_2024_general.py` sums every per-county precinct file per
(office, candidate) and compares against the certified county totals. After the
third pass, 1,795 checks:

| Status | Count | Meaning |
|---|---:|---|
| OK | 1,323 | precinct sum equals the certified county total |
| MISSING_OFFICIAL | 452 | local races — no certified county total exists |
| MISMATCH | 20 | **Pike and Tunica only** |

Every MISMATCH is confined to two counties and is described in
`20241105-general-county-vs-precinct-discrepancies.md`. The third pass cleared
Adams' two, which were the duplicated Supreme Court rows, and introduced none.
All other 80 counties reconcile exactly for every certified race.

`MISSING_OFFICIAL` is not new damage: it is mostly the local races that now
exist in the precinct files and have no certified counterpart to match, and it
grew from 64 to 452 as those races arrived. For a local race the PDF's own
printed TOTAL is the only gate; see "What counts as verified" in the runbook.

## Process notes

- The PaddleOCR-VL AI Studio backend (`src/paddleocr_client.py`) is implemented
  and preferred, but its endpoint was unreachable from this network on
  2026-09-27 (TLS handshake blackholed). The extraction therefore runs on the
  vision-model ladder; see `ocr-2024-general-runbook.md`.
- Local races have no certified county total to verify against, so they are
  gated on the PDF's own printed TOTAL for the contest instead.

## Second pass (2026-09-27): local races for all 82 counties

The local-race extraction is a full re-read of all 82 county PDFs, because the
committed files have local races in only 14 counties and the federal/statewide
rows have to come out of the same read to keep each county internally
consistent. It also re-reads the federal races, which is how several committed
defects turned up (below).

Pipeline: `src/batch_extract_2024.py` → per-county intermediates in
`cache/2024/intermediate/` → `src/normalize_2024_local_offices.py` → staged
files in `2024/counties-staging/` → `src/merge_2024_general_staging.py` →
`2024/counties/` → `src/statewide_generator.py generate_consolidated` → the
consolidated precinct file.

### Gates, and three holes that were open

`verify_2024` decides a county by comparing each contest's extracted precinct
sum against the PDF's own printed TOTAL, and against the certified county total
where one exists. A county merges only if every contest lands on `OK`,
`NO_OFFICIAL_DATA` or `PHANTOM_OFFICE`. Three ways a wrong read could still get
through were found and closed:

1. **A contest the model skipped entirely left no trace.** Verification builds
   its key set from the rows that are *present*, so a contest with no rows
   contributes no key and cannot disagree with anything — the county passes with
   the contest silently missing. `normalize_2024_local_offices.py` now compares
   the staged file's contests against the committed file's roster and reports
   any the staged file has lost. This is how Amite's lost `Election
   Commissioner|1` was caught: the county had passed, and no other gate could
   see the gap.
2. **`PHANTOM_OFFICE` accepts a whole real contest.** It is meant for a row
   wearing a certified office for a candidate outside the certified roster —
   which is exactly what a *real* uncertified contest looks like when the
   model guesses a certified office for its TOTAL row. On Chickasaw this
   accepted both halves of a contest that the gate should have questioned; see
   `20241105-general-phantom-office-discrepancies.md`.
3. **Duplicate rows were resolved first-wins.** When a model emits the same
   precinct twice on one page with different values, the extraction kept
   whichever it read first (see below).

The lost-contest check is only as complete as the committed roster it compares
against: a county whose committed file has no local races at all (Chickasaw is
one — 5 contests, no locals) cannot have a lost local contest detected this
way. Nothing else can see one either, because the only record of a local
contest's existence is the page it is printed on.

### Conflicting duplicate rows, resolved against the printed TOTAL

The failure mode that dominated the first run: the model reports a page's
precincts twice with two different sets of values, and the first-wins dedup
kept the wrong set. Copiah's U.S. House is the clearest case — page 4 was read
twice, and for *both* candidates the second set is the one the page prints:

| Candidate | first set (kept) | second set (what the page prints) | printed TOTAL |
|---|---:|---:|---:|
| Bennie G. Thompson | 3,320 | 3,643 | 5,810 |
| Ron Eller | 4,458 | 4,170 | 5,934 |

Keeping the first set left Thompson 323 short and Eller 288 over, so every rung
of the ladder failed and the county lost every race it had read, the federal
ones included. `resolve_conflicting_duplicates` in
`src/extract_2024_general_pdf.py` now adopts the alternate reading for a
candidate's conflicting rows **only when it lands exactly on that candidate's
printed TOTAL while the kept-first reading does not**, so it cannot invent a
reconciliation that was not there. A contest already summing correctly, one
with no printed TOTAL to check against, or one where neither reading
reconciles is left exactly as it was and still fails the ladder as before.

### Precinct-name reconciliation

One precinct arrives under several spellings because the OCR confusion is per
page, which splits a contest's rows across phantom precincts.
`reconcile_precinct` folds spellings that are *not* spelling differences before
measuring the edit distance — case, punctuation, spacing, the OCR ligatures
(`rn`/`m`), and now the `Dist.`/`District` and `Prec.`/`Precinct`
abbreviations the sheets use interchangeably within one county. Benton is the
case that forced the abbreviation folding: its five precincts are printed as
`Ashland Precinct District 3` in one contest's band and `Ashland Precinct Dist.
3` in another, and the committed Benton file itself carries both `Hickory Flat
Prec Dist 5` and `Hickory Flat Prec District 5` for one precinct.

The compass words are now compared explicitly. "North Okolona 006" and "South
Okolona 006" are one letter apart, so the edit-distance rule alone would merge
them; the only thing preventing it was that both happen to be in the committed
file, which returns early. In a county whose committed file lists one of a
pair, that merge would have moved one precinct's votes onto another. Requiring
the compass words to agree makes the guarantee hold on its own. Distance is
still capped at one edit: Clarke's three variants of the committed
`Souinlovie` are each two edits away, and so are `North`/`South Okolona 006`,
so distance 2 would risk real merges — the residual is surfaced in the
normalizer's not-reconcilable report instead of guessed at.

### Counties carried over from the first run

Seven counties were left out of the re-run because the first pass had already
recorded them `PASSED`, and the batch skips a `PASSED` county rather than
re-reading it. That verdict is not automatically the same as the current gates'
verdict, so each was checked against what the first pass could see:

| County | First-pass model | Still current? |
|---|---|---|
| Amite, Benton, Calhoun, Chickasaw, Clarke, Clay | `deepseek-v4.1-flash:cloud` | yes — the resolver is the only gate added since, and it would not change any of them |
| Perry | `qwen3.5:397b-cloud` | **no** — a rung outside the current `MODEL_LADDER` |

The resolver would not change the first six: its warning logs show no
conflicting duplicate at all for Benton, Calhoun, Chickasaw and Clay, and the
two conflicts that do appear are ones it deliberately leaves alone — Clarke's
`Donald J. Trump / Union` (639 kept, 646 dropped) sits in a contest already
summing to its printed TOTAL, and Amite's conflicts are all a numeric reading
against an `X` one, which it never resolves because an `X` is not a vote count.
The skip is therefore benign for six of the seven.

Perry is the exception, and what makes it unlike the rest is the model, not the
county: a `PASSED` from a retired rung is a verdict from a different gate-era, so
it is re-extracted with `--force --only Perry` after the batch ends. Amite is
also re-extracted, but for the opposite reason — it passed under the current
gates and *still* lost a contest, which is exactly the shape of the
lost-contest hole described above.

The lost-contest check is the right instrument for the other five as well, and
it runs for every county after the batch completes: it compares each staged
file's contests against the committed roster and names any that went missing.
A county it flags is re-extracted; a county it does not is left as it is.

### Source-verified corrections

`src/fix_2024_general_structural.py` applies values read directly off a source
PDF that the extraction missed, and refuses to write unless the corrected
contest still reconciles against its own printed TOTAL. Its first correction is
Chickasaw's blank-band contest, whose second page was never read: the contest's
precinct detail sat 71 and 67 votes short of its printed TOTAL 434 / 232, and
page 7 supplies the missing `Woodland 015` (71 / 67) plus three `X` cells.
`20241105-general-phantom-office-discrepancies.md` has the analysis.

## Third pass (2026-09-27): the same 61 counties, re-read by a layout backend

The second pass read the PDFs page by page through a vision model. This pass
re-reads them with **OpenParser** (`api.openparser.dev`), which takes the whole
county PDF in one call and returns positioned text elements instead of prose —
`src/extract_2024_general_openparser.py`. The two backends disagree in places,
and because a disagreement between two independent reads of one source is
exactly where a defect shows up, every difference was resolved against a
rendered page rather than against the committed file.

61 of the 82 counties are cached; the remaining 21 returned HTTP 402
(insufficient credits) and are untouched by this pass, so they still carry the
second pass's output. That mixture is safe only because every county passes the
same gates. **Superseded by the fourth pass below**, which re-read those 21 and
installed them.

```bash
uv run python src/extract_2024_general_openparser.py --cached-only --write
uv run python src/batch_extract_2024.py ...          # → 2024/counties-staging/
uv run python src/normalize_2024_local_offices.py --indir 2024/counties-staging --write
uv run python src/merge_2024_general_staging.py --write --backup-dir cache/2024/committed-backup
uv run python src/statewide_generator.py generate_consolidated \
    2024 "20241105__ms__general__*__precinct.csv" 2024/20241105__ms__general__precinct.csv
```

| | |
|---|---:|
| Counties re-read | 61 |
| Rows, before → after (consolidated file) | 29,878 → 39,618 |
| Merge operations against the committed files | +10,502 −722 ~13 |
| Net row change in the 61 files | +9,740 |
| Crosscheck mismatches cleared / introduced | 2 / 0 |

The merge's `+10,502 −722` nets to +9,780 against the file-level +9,740. The
40-row difference is pre-existing duplicate rows in the committed files: the
merge keys rows on `(precinct, office, district, candidate, party)`, so
duplicates collapse and are invisible to both its `added` and `removed`
buckets, while the file row count falls by all 40. There are exactly 40 —
Adams 32, Bolivar 8.

### What the re-read changed

Most of the +10,502 rows are the local races, which the committed files were
missing. The rest are corrections to rows that already existed. The full
per-row audit is `cache/2024/reports/staging-vs-committed-changes.csv`; all 13
value changes are listed here, and each was confirmed against a rendered page:

| County | Contest | Precinct | Change |
|---|---|---|---|
| Alcorn | Election Commissioner | North Corinth | Bobby McDaniel 946 → **948** |
| Amite | Election Commissioner | Oneil / Riceville | Janet Bateman Touchstone 280 → `X` on Oneil, `X` → **280** on Riceville |
| Amite | Election Commissioner | Street / Vance Park | Bateman 211 → `X` on Street; Annette Wicker `X` → **146** on Vance Park |
| Bolivar | School Board North 01 | Mound Bayou / West Cleveland | John Coleman `X` → **289** on Mound Bayou, 289 → `X` on West Cleveland |
| Bolivar | Election Commissioner | Shaw | Ora (Dean) Martin Jackson `X` → **445** |
| Bolivar | School Board West 01 | Stringtown | Kenneth Bell `X` → **26**; Linda Carter `X` → **3** |
| Bolivar | School Board West 01 | West Rosedale | Kenneth Bell `X` → **0**; Linda Carter `X` → **1** |
| Bolivar | School Board C004 | West Central Cleveland | Lucille Holmes `X` → **13** |

Four of these are **misassignments rather than corrections**: a value the
committed file had put on one precinct belongs to another, so the fix shows up
as a matching `+`/`−` pair (Bateman Oneil → Riceville, Coleman West Cleveland →
Mound Bayou). The rest fill in an `X` where the sheet prints a number.

Three corrections are not value changes but are worth recording:

- **Attala `Danice Dees` → `Janice Dees`.** The source prints Janice; the
  committed name was wrong.
- **Bolivar `Beverley Janoush` → `Beverely Janoush`.** The committed spelling
  was the wrong one — the source (and the sheet's own summary line, against its
  printed TOTAL 963) reads `Beverely`. The re-read also recovered 956 votes the
  committed file had marked `X` (West Cleveland 851, West Central Cleveland
  105), which is what took this candidate's total from 7 to 963.
- **Attala `Andre Liboth` / `Libroth` — left alone.** The precinct grid prints
  `Andre Liboth` and the county summary page prints `Andre Libroth`; the source
  disagrees with itself. The file keeps `Liboth`, matching the grid page the
  per-precinct rows come from and the committed file, rather than choosing
  between two readings the source does not settle.

### What this pass did *not* touch

- **The 21 uncached counties.** They came back HTTP 402 (OpenParser credits), so
  they were neither re-read nor installed, and they still carry the second
  pass's output. Any defect in them survives. *(Closed by the fourth pass below,
  which re-read and installed all 21.)*
- **The vision ladder itself.** `MODEL_LADDER` in `src/batch_extract_2024.py` is
  unchanged, and a county not in the OpenParser cache still goes through it.
- **A cached response is only as good as the model that wrote it.** `--cached-only`
  re-parses; it never re-asks. A response cached from a model that has since been
  retired needs a fresh call before it can be trusted again.

### Precinct renames the re-read accepted

The normalizer reports 186 precinct renames. These are the committed file's
noisy OCR spellings being replaced by what the sheet prints — Bolivar
`Estepaje` → `Eastgate`, `Longspout` → `Longshot`, `Rienova` → `Renova`,
`Stone` → `Skene`, `Winsonville` → `Winstonville`, `Orchaw` → `East Rosedale`,
`Morrison Chapel` → `Morrison Chapel Church`; DeSoto `Southhaven` →
`Southaven`; Kemper `Little Rock Community Center` → `Little Rock Comm Ctr`;
Humphreys `- 3ls 3030` → `- 31s 3030`; Pike `(11) St. James Miss. Baptist
Church` → `(11) St. James Miss. Bapt. Church`. The 2022 committed file for
Bolivar carries the spellings this pass produced, which is the independent
confirmation that the committed 2024 file was the noisy one.

The normalizer's not-reconcilable report is the other half of this: a name it
could not fold is surfaced rather than guessed at. The residual is 8 counties,
and each entry pairs an `extra` name against the committed one it replaced —
`Cleveland` for Bolivar's seven renames, `Southaven Library`/`Southaven South`
for DeSoto's pair, and so on. A name appearing as `extra` with its counterpart
*also* reported as `missing` is a precinct still split and needs a look.

### Scratch and report files

The per-row and per-office audit CSVs this pass produced live in
`cache/2024/reports/` (git-ignored) rather than beside the data, because the
CI data tests glob every `.csv` under a four-digit year directory and a
non-data CSV there fails `duplicate_entries`. `2024/` holds only the three
committed data CSVs and these Markdown reports.

## Fourth pass (2026-09-27): the remaining 21 counties

The third pass could not touch 21 counties — they returned HTTP 402
(insufficient credits). Once credits were available they were re-read the same
way, through OpenParser, and installed. **All 82 counties have now been read by
both approaches**, so no county carries an earlier pass's output any more.

The backend preference for this pass was Mistral (`mistral-ocr-4`), per the
instruction to use it, with the ladder falling through to
`aws-textract-tables-layout` only when Mistral's read fails the gates — see
"What the two backends disagreed about" below for the four counties where it
does.

```bash
uv run python src/extract_2024_general_openparser.py --only <21 counties> --write
uv run python src/normalize_2024_local_offices.py \
    --indir cache/2024/staging-21 --counties-dir 2024/counties \
    --certified-csv 2024/20241105__ms__general__county.csv \
    --write --log cache/2024/reports/local-office-normalization-21.csv
uv run python src/merge_2024_general_staging.py \
    --staging-dir cache/2024/staging-21 --counties <21 counties> \
    --write --backup-dir cache/2024/committed-backup
uv run python src/statewide_generator.py generate_consolidated \
    2024 "20241105__ms__general__*__precinct.csv" 2024/20241105__ms__general__precinct.csv
```

| | |
|---|---:|
| Counties re-read | 21 |
| Rows, before → after (consolidated file) | 39,618 → 42,781 |
| Merge operations against the committed files | +3,336 −173 ~0 |
| Net row change in the 21 files | +3,163 |
| Backends: Mistral / Textract | 17 / 4 |

The merge's `+3,336 −173` nets to +3,163, exactly the file-level change, because
unlike the third pass no committed duplicate row collapsed in the accounting.

### The two gate changes this pass forced

Both are in the gate that decides a county: `check()` in
`src/parse_2024_general_county_textlayer.py`.

**1. A contest with no printed TOTAL is now compared against the certified
county CSV.** The sheet prints its TOTAL column only on the last page of a
contest, so every contest a page break cuts in half reports `printed is None` —
and that branch was the gate's one place that reported without comparing. It
printed the detail and moved on. Two defect shapes hid there:

- **A doubled page**, which is invisible to internal reconciliation because the
  duplicated page carries no TOTAL to disagree with. Mistral's Wayne read summed
  seven contests to exactly twice the certified total (Jack Wilson 2,570 against
  a certified 1,285; Craig Elliot Raybon 5,708 against 2,854), and passed.
- **A contest read at the wrong magnitude**, which Walthall's Mistral read shows
  at ×2.0 on the Supreme Court pair and a low reading on U.S. House (3,149
  against a certified 5,068), and Yalobusha's at ×0.9 on four contests.

The certified county total stands in for the printed TOTAL here, which is what
makes the check able to catch a doubled page: the sheet's own arithmetic agrees
with itself whether or not a page was counted twice. Only an independent
document can see it.

**2. A contest the extraction never produced at all is now a failure.** The
per-contest loop iterates the contests the extraction *produced*, so a contest
it never produced contributes no key and cannot disagree with anything. Mistral's
Simpson read has **not a single row for Michael Guest's U.S. House race**
(certified 9,176) or for the two Southern District Supreme Court seats, and every
contest it did read reconciles — so the gate returned `OK` over a sheet missing a
quarter of its rows. The presence check compares the certified roster against the
contests present and fails the county for any certified candidate with no row.

Presence needs name matching that tolerates the sheet's spelling from the
certified CSV's — the sheet drops the generational suffix the certified CSV
carries, and sets a middle initial the certified CSV spells out. `same_candidate`
folds those (suffixes and single-letter initials are noise; the remaining tokens
must match exactly or as a subset) and was validated before it gated anything:
against **all 82 counties' intermediates it reports 0 false positives**
(`cache/2024/scratch/validate_presence.py`). Applied to the installed files, no
county is missing a certified candidate.

Both changes are exempt for the two `KNOWN_SOURCE_CONFLICTS` counties, whose
sheet-vs-CSV disagreement is documented rather than fixed — a conflict county's
certified roster would otherwise be reported missing in its entirety. That
exemption is now tested case-insensitively (`is_known_source_conflict`), because
`--only tunica` reaches the gate with the caller's spelling, and a
case-sensitive `in` silently withdrew the exemption for it — turning a
documented pass into a failure that reads as a data problem.

### What the two backends disagreed about

Laddering Mistral first and falling through only on a gate failure means the two
backends were compared exactly where it matters. Four counties were installed
from Textract because Mistral's read is provably damaged:

| County | Mistral's defect | Textract's read |
|---|---|---|
| Simpson | U.S. House race absent entirely (0 rows vs a certified 9,176) | 9,176, present |
| Walthall | U.S. House 3,149 vs certified 5,068; Supreme Court pair at ×2.0 | reconciles |
| Yalobusha | four contests 0.88–0.96× certified, no printed TOTAL to check them | reconciles |
| Wayne | seven contests at exactly ×2.0 (a doubled page) | reconciles |

The other 17 were installed from Mistral. Tunica is the marginal case: **both**
backends produce the same file, gate-OK only through the `KNOWN_SOURCE_CONFLICTS`
carve-out, and the committed values are unchanged — see
`20241105-general-county-vs-precinct-discrepancies.md`.

### Every row this pass removed, accounted for

The merge removes 173 keys from the 21 committed files. A removal is the shape a
*correct* change takes here too, since the merge keys rows on
`(precinct, office, district, candidate, party)` and a renamed precinct or a
requoted candidate name shows up as one key out and one key in with every vote
value unchanged. So each removal was traced to an equal-vote replacement
(`cache/2024/scratch/verify_removals.py`), giving three classes and no residue:

| Cause | Rows | Detail |
|---|---:|---|
| Candidate quote style | 142 | `Robert P. "Bobby" Chamberlin` → `'Bobby'` |
| Precinct renamed | 31 | Smith 15 (`Lorena-Sophia` → `Lorena - Spinola`), Wayne 16 (`Chappara/Diamond` → `Chapparal/Diamond`) |
| **Unexplained** | **0** | — |

The quote-style rows are **not a change this pass makes deliberately** — no code
canonicalizes candidate names, and none was added. They are what the re-read
produces: the extraction writes `Robert P. 'Bobby' Chamberlin`, and the
committed files this pass replaces carried the escaped `""Bobby""` form. The
single-quoted spelling is the one with the witnesses:

- **Both backends read it that way**, in the counties that carry the name — 110
  occurrences across the 94 cached OpenParser responses (Textract 65, Mistral
  45) and not one double-quoted form.
- **The earlier vision pass read it that way too**: all 33 intermediates for
  counties carrying the name have it single-quoted, none double-quoted, which is
  why the 61 already-installed files publish it that way.
- **The certified `20241105__ms__general__county.csv` writes it that way**, in
  all 33 of its rows — it is that file's only quoted nickname.

So the committed `""Bobby""` form was the outlier (194 rows repo-wide, against
2,166 single-quoted), and publishing the re-read makes the 82 counties agree with
each other and with the certified CSV instead of leaving nine split off.

This is per-candidate agreement, not a repo-wide quote normalization: names with
no certified or committed counterpart keep whatever the read produced.
`Wealthia ""Susie"" White` is a local race with no certified entry, so its 24
rows still carry the escaped form, and double-quoted nicknames appear elsewhere
in the repo for other people (2023 carries `"Bubba"` 97 times, `"Jase"` 62).
What this pass settles is the one name where an authoritative spelling exists and
the two halves of the 2024 data disagreed about it.

The 31 renamed rows are the two precinct findings below, and both are
replacement-by-source-spelling: the same 31 rows are also the merge's additions
under the published names.

### Precinct names: two aliases, two committed misreads

Four precinct names needed a decision, and each was settled from a rendered page
plus the repo's own history rather than from either read alone. Two are entries
in `PRECINCT_ALIASES` (`src/normalize_2024_local_offices.py`), because the
extraction reads the sheet faithfully and it is the *committed* file that
disagrees:

- **Tunica `Milton Landing` → `Mhoon Landing`** and **`Vernon Park` → `Verner
  Park`.** Page 7 at 600 dpi prints the headers the repo uses, and each pair is
  one printed column read two ways rather than two precincts: their rows are
  disjoint and together fill exactly the 19 contests every other Tunica precinct
  has (8 + 11 rows for both pairs), and their sums land on the committed column
  exactly (267 + 134 = 401; 1,006 + 413 = 1,419). Neither fold is reachable by
  `reconcile_precinct`: `milton` is two substitutions from `mhoon`, and the
  ligature fold that turns both `Verner` and `Vernon` into `Vemer`/`Vemon`
  leaves those two *two* edits apart rather than one.
- **Walthall `4th Distrct West Tylertown` → `4th District West Tylertown`.** The
  one entry here that is not a misread at all: the sheet prints the typo
  (`Distrct`, beside the separate precinct `4th District Tylertown`) and the
  extraction reads it faithfully. Every Walthall file in the repo from 2015 to
  2026 instead spells it `4th District West Tylertown`, so publishing the
  printed typo would be its only occurrence in the data and would break a decade
  of cross-year joins. `reconcile_precinct` cannot make the fold on its own — it
  folds the *target's* `District` to `Dist` while the source's `Distrct` stays
  as it is, leaving the canonical forms three characters apart.

The other two go the opposite way, and are entries in
`COMMITTED_PRECINCT_MISREADS` — a **guard rather than a repair**, because in
both cases `reconcile_precinct`'s one-edit rule folds the file's correct spelling
*onto* the committed misread:

- **Wayne `Chappara/Diamond`** is a dropped `l`. The 2024 source prints
  `Chapparal/Diamond`, both 2024 backends read it that way, and the repo spells
  it `Chapparal` 544 rows to this 123. The 2018 runoff, 2020 and 2022 files carry
  `Chappara/Diamond` too — the same misread copied forward, not four independent
  witnesses.
- **Smith `Lorena-Sophia`.** The sheet prints `Lorena - Spinola` (rendered page 2
  at 600 dpi), the county has no precinct named Sophia, and the repo's older
  files (2012, 2014, 2015 general, 2015 primary, 2026 primary) all spell it
  `Spinola`; `Sophia` appears only in 2022, 2023 general, the 2024 primary and
  the 2024 general. The distance rule cannot reach it either way, so the entry
  keeps a future variant from being folded onto the misread.

### Rows an earlier pass dropped, restored

Wayne's committed file carries **no `X` rows at all**, but the source prints them:
`Jack Wilson X 122 X 204 X X X X 184 228 101` for Court Of Appeals 03-District 3
Position 1, and the same shape on District 5. The earlier pipeline dropped them
and covered only the 6 (and 16) precincts where the contest was on the ballot;
this pass emits the full 22 with `X` where the sheet prints it. That is the
repo's convention — the consolidated file carries 8,147 `X` rows, and the same
district races in other counties already carry them (Court Of Appeals 02 has 151,
Court Of Appeals 03 has 36) — so Wayne was the outlier and is now consistent.
Because an `X` is not a vote count, the contest's vote total is unchanged
(1,285 and 7,133).

The reverse also holds: the normalizer drops `Over Vote` and `Under Vote` rows,
which are not candidates. Tippah is where this is visible (42 rows, two per
precinct); the committed files omit them too, and none of the 82 installed files
or the consolidated file contains one.

### Verification of the installed data

| Check | Result |
|---|---|
| `crosscheck_2024_general.py` | 1,954 per-candidate checks: 1,323 OK, 611 `MISSING_OFFICIAL` (local races with no certified total), 20 `MISMATCH`, **`MISSING_PRECINCT` 0** |
| The 20 mismatches | Pike 14 (~21% high) and Tunica 6 (−1 uniform) — both documented source conflicts, both unchanged |
| Presence vs the certified roster | 0 of 82 counties missing a certified candidate |
| CI `duplicate_entries`, `file_format`, `missing_values`, `vote_breakdown_totals` | pass on all 83 touched 2024 files (82 county + consolidated) |
| Row counts | 42,781 data rows across the 82 files, with one header each and no blank lines; the consolidated file matches the county files exactly (0 rows differ) |

The CI suite reports pre-existing failures in **other years** (35 in
`duplicate_entries`, 1 in `file_format`) — none of them in a file this work
touched, and none in `2024/`. The `file_format` failure is in
`2023/counties-staging-dem-primary/`, a staging directory from an earlier
session. Under CI's changed-files scope neither would run.

### Deviations from `CLAUDE.md` this work confirms

- **Column order.** `CLAUDE.md` documents
  `county,precinct,office,district,party,candidate,votes`; every committed
  precinct file, and therefore every file this pass writes, is
  `county,precinct,office,district,candidate,party,votes`. The sibling repos
  (`openelections-data-al`, `-ga`, `-tn`) follow the documented order, so
  Mississippi is the outlier; the regeneration matches the files it replaces
  rather than changing the convention. The county-level files differ again
  (`county,office,district,party,candidate,votes`), so Mississippi is not
  internally consistent either.
- **Local offices.** `CLAUDE.md` says "only federal, statewide, and state
  legislative offices — no local offices". This work deliberately does the
  opposite, per the scoping decision to cover all races including local ones;
  local contests are now the single largest part of the 2024 general precinct
  data (611 of 1,954 crosscheck entries have no certified counterpart).
- **`uv.lock`.** `CLAUDE.md` says the lock is committed. It is not tracked:
  `git ls-files` shows no `uv.lock`, and `pyproject.toml` is untracked as well.

