# 2024 general — rows wearing the wrong office label

A SEMS "Official County Recapitulation" sheet prints each contest's office in a
band above its candidate rows. When that band is missing, blank, or unreadable,
nothing in the extraction can tell — the model simply reports whichever office
it can reach, and the row arrives in the CSV wearing an office it does not
belong to. This report covers the cases found while re-extracting all 82
counties on 2026-09-27.

The failure is silent by construction: `verify_2024` compares a row against the
*certified* totals, and a local row has no certified total, so a mislabeled row
lands on `NO_OFFICIAL_DATA` — which the batch **accepts**. Choctaw's two
invented presidential candidates would have been published that way. Two
guards now catch them (`PHANTOM_OFFICE` in `verify_2024`, plus the committed-file
resolution in `normalize_2024_local_offices.py`); see
`ocr-2024-general-runbook.md` for the mechanism.

## Choctaw — a genuine source gap (unresolved)

Choctaw's PDF has 7 pages: a certification cover, pages 2–3 carrying the
federal races, pages 4–5 the local races, and **pages 6–7 a standalone table
with no office band at all**. Verified by rendering at 300 dpi: the label
column goes straight from "Votes cast in the County of Choctaw, Mississippi on
the 5th day of November 2024" to the first candidate row. Nothing is printed
between them.

| Page | Candidate | Party | Precincts with votes | Printed TOTAL |
|---|---|---|---|---:|
| 6/7 | Omine Rachel Miller Ashford | Independent | East Weir 103, Panhandle 112, Southwest Ackerman 102 | **317** |
| 6/7 | Nola Bryant | Independent | East Weir 106, Panhandle 84, Southwest Ackerman 150 | **340** |

The extraction read both candidates correctly — the sums match the printed
TOTALs exactly — but reported their office as `President`, and Choctaw's
certified President roster has neither name. **The office is undeterminable
from this document.** The three precincts are a subset of the six left
uncovered by Election Commissioner districts 1, 3 and 5 (`{Bywy, Chester}`,
`{French Camp, Keneo, West Weir}`, `{Dist. 5}`), so the contest is plausibly an
EC district 2 or 4 or a school-board district, but nothing on the page says
which.

**Disposition:** the 24 rows are kept with `office=Unknown` so the votes survive
rather than being dropped, and they need manual identification. This follows the
same convention the extraction uses for a blank band it can detect
(`_is_document_title`).

## Alcorn and Amite — mislabeled, and recoverable

These look the same but are not: the candidates are already in the committed
precinct files, so the office can be restored from the county's own data.

| County | Candidate | Extraction said | Committed says |
|---|---|---|---|
| Alcorn | Charles Seago | `President` | `School Board` \| `4` \| `NP` |
| Amite | Veronica Faye Christian | `Election Commissioner` (precinct rows), `Southern District-Supreme Court District 2(Southern) Position 2` (TOTAL) | `School Board` \| `4` |
| Amite | Cindy Wilson Newman | same as above | `School Board` \| `4` |

Amite is the instructive one: the *same* candidate came back under two
different offices in one file, because two different bands were missed. This is
why candidate identity is resolved against the committed file **before** any
office label is considered — and why the phantom rule must run *after* that
lookup, not before. Running it first relabels exactly these rows to `Unknown`
and throws away a recoverable answer.

## Chickasaw — a contest split across office labels, and a page-7 gap

`Casey Lancaster` and `Whitney Morgan` are a two-candidate contest whose office
band is blank on **both** of its pages (verified by rendering page 6 at 400 dpi:
nothing is printed between the document's own header band and the first
candidate row — no faint text, no clipped glyphs). The extraction filed the
contest under **three different labels**:

| Rows | Office recorded | Sum |
|---|---|---:|
| Page 6's 11 precinct rows | `Federal General Election` (the document title, from the blank band) | Lancaster 363, Morgan 165 |
| TOTAL column | `U.S. House` | Lancaster **434**, Morgan **232** |

An earlier version of this report said page 7's precinct value had been
"consumed as the TOTAL". That is wrong, and the difference matters. The model
read page 6's precinct rows and the printed TOTAL correctly (434 / 232, exactly
as printed), but it **skipped page 7's precinct rows entirely**: `Woodland 015`
(71 / 67) and the `X` cells for `Sparta 012`, `Van Vleet 013` and
`West Okolona 014`. So the gap is an unread page, not a misassigned value —
and it is recoverable from the source, which is what the hand-correction below
does.

Neither candidate is on Chickasaw's certified U.S. House roster, which is what
the phantom-office gate keys on; the `U.S. House` TOTAL with no precinct rows
under it is what `TOTAL_WITHOUT_ROWS` catches.

**The office is not printed, so it stays `Unknown`** — but the contest's
identity is narrower than Choctaw's, and the evidence is worth recording:

- Its district is exactly `{Anchor 001, Northwest Houston 007, Southeast
  Houston 010, Woodland 015}` — the same four precincts as the *printed*
  `Chickasaw County School Board Dist 5` contest (Richard J. Earnest, printed
  TOTAL 413 = 125 + 4 + 237 + 47).
- No other contest on the ballot covers that set: EC District 1 is `{001, 002,
  003, 007, 013}`, EC District 3 `{004, 005, 006, 011, 013, 014}`, EC District
  5 `{009, 010}`, and Okolona School Board County Position 1 `{003, 004, 006,
  014}`. Only School Board District 5 matches.
- Four independently-run vision models (`claude-sonnet-45`, `gemini-flash-3`,
  `gemini-pro-25`, `gemini-pro-3`, in `test/`) each read the blank-band contest
  as `School Board`, district 5. They had no visible band to copy from, so this
  is inference rather than transcription — but it is the same inference the
  precinct set points to.
- Ballotpedia lists Richard Earnest as a sitting member of the five-member
  Chickasaw County School District board, so the printed District 5 contest is
  a real school-board seat.

**Disposition:** the 22 precinct rows are kept as `Unknown` (precinct sums 363
and 165) so the votes survive, and the source-fidelity rule is why: the
district-set match is strong but it is an inference, not a printed label, and
`School Board` is a claim the document does not make. `fix_2024_general_
structural.py` adds page 7's rows (`Woodland 015` 71 / 67, plus the three `X`
cells) so the contest's precinct detail sums to its printed TOTAL 434 / 232
instead of sitting 71 and 67 short. Whether the two sheets are one three-way
contest for District 5 or two contests with identical districts is unresolved
and needs the county's own canvass.

## Attala — summary furniture reported as candidates

The sheets print `Write-In Totals` and `Contest Totals` rows under each
contest's TOTAL column, and Attala's read turned them into candidates (11 rows
across President, U.S. Senate, U.S. House and two Supreme Court contests). Each
carries that contest's own total, so treating them as candidates would inflate
the contest — they arrive on TOTAL rows, which `merge_county` already drops and
the normalizer now drops as well. `CANDIDATE_JUNK_RE` remains as a backstop for
one that turns up on a real precinct row.

Adjacent to them, and also TOTAL-only, is a real named write-in:
`Cornel West / Melina Abdullah`, `Independent`, 15 votes. It is real data rather
than furniture, but with no precinct rows it is dropped along with the rest of
the TOTAL column.

## Unrelated, found in passing: a one-vote miss on Choctaw

Choctaw's fresh read has `Chase Oliver (LIB) extracted=6, pdf_total=7,
official=7` — a single missing precinct vote on a candidate whose cells are
almost all 0 or 1. `INTERNAL_MISMATCH` counts as a bad read, so this escalates
like any other. Per the runbook, a small isolated mismatch that survives the
ladder is usually a real defect on the page and wants manual review rather than
another model.

## Note on the three stale counties

`perry.csv`, `pike.csv` and `tunica.csv` in `cache/2024/intermediate/` are
leftovers from an earlier pilot run (16:06–16:12), not this run's output. The
phantom rows reported for Perry (`Sherry Dean Hartfield`, `Janet B. Mayo`,
`Dianna Cooley Clark` under `U.S. House`) and the 11-row two-column shift in
Pike come from those files. They are replaced when this run reaches those
counties.
