"""Extract county-level 2023 Mississippi primary election results from the
Secretary of State's statewide "Official Recapitulation" PDF -- a single
document (per party) that is a repeating grid of (office, candidate, party)
rows x (county columns) tables: each page shows ~11 counties as columns,
cycling through all ~82 counties for one set of races before moving on to
the next set of races. The last page of each county cycle adds a final
TOTAL column.

Unlike the precinct-level recap sheets in extract_2024_general_pdf.py:
  - these pages are already right-side up (no rotation needed)
  - each row already prints its own party, so no roster-based candidate/
    party matching is needed -- office, candidate, party, county, and votes
    are all read directly off the page
  - there's no independent "official county totals" CSV to verify against
    (this document *is* the source of county-level truth) -- the TOTAL
    column instead gives an internal self-consistency check, the same way
    a PDF's own TOTAL row worked in the precinct-level pipeline

District races (State Senate/House) print "X" in county columns outside
that district's counties and the real count only in counties the district
covers, with the TOTAL column holding the true district-wide total.

Usage:
    uv run python extract_2023_primary_county_pdf.py <pdf_path> \\
        -o cache/primary2023/gop_county.csv [--start-page N] [--end-page N]
"""

import argparse
import csv
import io
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import llm

from extract_2024_general_pdf import render_raw_pages, call_with_fallback, _call_model

FIELDS = ["county", "office", "district", "party", "candidate", "votes"]

# Only strips the specific "<office> NN-District NN" shape used by State
# Senate/House headers (the district number is printed twice -- once before
# the hyphen, once after "District" -- so the backreference anchors on an
# exact repeat rather than guessing). Other multi-part headers, e.g.
# "Public Service Commissioner-Central District" (a geographic qualifier,
# not a repeated number) or judicial-style names, are NOT split -- they're
# kept as the full printed string in `office`, the same way judicial race
# names are kept whole (unsplit) in extract_2024_general_pdf.py, rather
# than risk a wrong guess at office/district boundaries.
_NUMERIC_DISTRICT_RE = re.compile(r"\s+(\d+)-District\s+\1\s*$", re.IGNORECASE)


def split_office_district(office_raw):
    """'State Senate 06-District 06' -> ('State Senate', '06').
    'State Of Mississippi-Governor' -> ('Governor', '').
    'Public Service Commissioner-Central District' -> unchanged, no split."""
    office = re.sub(r"^State Of Mississippi-", "", office_raw).strip()
    m = _NUMERIC_DISTRICT_RE.search(office)
    if not m:
        return office, ""
    district = m.group(1)
    office = office[:m.start()].strip()
    return office, district


def build_prompt(carry_office=None):
    lines = [
        "This image is a page from an official Mississippi 2023 primary "
        "election recapitulation report. It is a table: bold section "
        "headers name an office (e.g. 'State Of Mississippi-Governor', "
        "'State Senate 06-District 06'), and each row below a header is one "
        "candidate for that office, with the candidate's party printed "
        "immediately after their name. Columns are county names, read "
        "vertically at the top of the table; the last page for a given set "
        "of offices also has a final 'TOTAL' column.",
        "",
        "Extract ALL data from this page as CSV rows with exactly these "
        "columns: office,candidate,party,county,votes",
        "",
        "IMPORTANT:",
        "- office is the most recent bold section header above this "
        "candidate's row, exactly as printed (e.g. 'State Of "
        "Mississippi-Governor', 'State Senate 06-District 06').",
        "- candidate is ONLY the person's name -- do not include the office.",
        "- party is printed immediately after the candidate's name "
        "(e.g. Republican, Democrat).",
        "- county is the column header for that vote count, exactly as "
        "printed at the top of the table, including 'TOTAL' if this page "
        "has a TOTAL column.",
        "- votes as a plain integer, or X if the cell shows X (district "
        "races print X for counties outside that district).",
        "- Emit one CSV row per (candidate, county) cell -- a page with 11 "
        "county columns and 3 candidates should produce 33 rows.",
        "- Before answering, look specifically at the LAST few lines of "
        "the table at the bottom of the page. Is the very last thing on "
        "the page a bold office header, with the page ending before any "
        "candidate name/row was printed under it? This happens when a "
        "race's header fits at the bottom of a page but its data doesn't. "
        "If so, you MUST emit one extra final line for it, exactly in "
        "this form: ORPHAN_HEADER,<the exact header text> -- do not skip "
        "this, it is easy to miss but important.",
        "- no markdown, no explanation, no other text -- only CSV data "
        "rows (and an ORPHAN_HEADER line if this page ends with one).",
    ]
    if carry_office:
        lines += [
            "",
            "A race's bold header can fall at the very bottom of one page "
            "with no room left for its candidate rows, which then continue "
            "on a later page with no header visible at all -- if this "
            f"page's first row(s) have no office header above them, they "
            f"continue the office from an earlier page, which was: "
            f"{carry_office!r}. Use that office for those rows.",
        ]
    return "\n".join(lines)


def extract_page(model, img, page_num, carry_office):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    resp = _call_model(
        model, build_prompt(carry_office),
        [llm.Attachment(content=buf.getvalue(), type="image/png")],
        stage=f"page {page_num}",
    )
    return resp.text()


def extract_page_with_fallback(models_and_names, img, page_num, carry_office, warnings):
    text, used_model = call_with_fallback(
        models_and_names,
        lambda model: extract_page(model, img, page_num, carry_office),
        f"p{page_num}",
        warnings,
    )
    if text is None:
        warnings.append(
            f"p{page_num}: FAILED on every model in the ladder -- page skipped, data incomplete"
        )
    return text, used_model


def parse_page_rows(text):
    """Parse raw CSV lines into (office, candidate, party, county, votes_str)
    tuples, plus a list of raw lines that couldn't be parsed, plus an
    orphan_header string (or None) -- a trailing bold office header this
    page printed with no candidate rows under it (see the ORPHAN_HEADER
    prompt instruction), which parsed_rows can't otherwise represent since
    it has no data to anchor a row to. office is read as everything before
    the last 4 fields, so an office string with an embedded comma (e.g. a
    geographic qualifier) doesn't break the split."""
    rows = []
    unparsed = []
    orphan_header = None
    for line in text.strip().splitlines():
        line = line.strip().strip("`")
        if not line:
            continue
        if line.upper().startswith("ORPHAN_HEADER,"):
            orphan_header = line.split(",", 1)[1].strip()
            continue
        parts = next(csv.reader([line]), None)
        if not parts:
            continue
        parts = [p.strip() for p in parts]
        if len(parts) < 5:
            unparsed.append(line)
            continue
        if any(p.lower() in ("office", "candidate", "party", "county", "votes") for p in parts):
            continue
        votes, county, party, candidate = parts[-1], parts[-2], parts[-3], parts[-4]
        office = ", ".join(parts[:-4])
        if not office:
            unparsed.append(line)
            continue
        rows.append((office, candidate, party, county, votes))
    return rows, unparsed, orphan_header


# A candidate's minority (office, district) rows are only treated as drift
# (not a second, genuinely different candidate who happens to share a name)
# when the majority pairing has a decisive lead over the runner-up. Chosen
# from real data: a clean 2-way drift (e.g. 72 rows vs 11) clears this easily,
# while a genuine same-name homonym case (e.g. 83 rows vs 72, two different
# real people on the same ballot) stays well under it and is correctly left
# alone -- see extract_2023_primary_county_pdf.py's John Caldwell case,
# who is both a State Senate candidate (83 rows, a clean full cycle) AND,
# separately, a different John Caldwell whose data splits 72/11 between
# District Attorney and Transportation Commissioner. Merging by simple
# majority alone would have wrongly folded the Senate candidate in too.
DRIFT_MAJORITY_RATIO = 3


def reconcile_drifted_offices(rows, warnings):
    """A candidate should appear under exactly one (office, district) pairing.
    The carry-forward-office mechanism above (build_prompt's `carry_office`)
    handles a *single* orphaned header correctly, but a candidate's row can
    still drift onto the wrong office or district if a page's own guess is
    itself wrong -- that guess then becomes the next page's carry-forward
    context, compounding the error across a whole run of pages. Observed on
    real data: a low-turnout candidate with almost no non-X votes anywhere
    in their cycle gives the model no visual anchor to self-correct, and
    the resulting phantom office/district (all-X except a stray TOTAL, or
    vice versa) is invisible to verify_party's INTERNAL_MISMATCH check,
    since a pairing with no real votes AND no TOTAL never enters
    extracted_sum or pdf_total at all. This drift isn't limited to the
    district number within one office (e.g. 58 vs 74) -- it can cross into
    an entirely unrelated office (e.g. most of a Transportation
    Commissioner candidate's rows landing under District Attorney).

    Fix: group by (party, candidate) across ALL rows (real votes and TOTAL
    alike -- a candidate's true office/district should be the same label on
    nearly every one of their ~83 rows, drift or not), and relabel every
    row in a group to whichever (office, district) pairing is the majority
    label -- but only when it leads the runner-up by DRIFT_MAJORITY_RATIO;
    otherwise this is more likely two different real candidates who share a
    name, and the data is left untouched. Every decision (merge or
    left-ambiguous) is logged since this is a best-effort correction, not a
    certainty."""
    groups = defaultdict(list)
    for row in rows:
        groups[(row["party"], row["candidate"])].append(row)

    merged = {}
    order = []
    for (party, candidate), group_rows in groups.items():
        ranked = Counter((r["office"], r["district"]) for r in group_rows).most_common()
        canonical_office, canonical_district = ranked[0][0]

        if len(ranked) > 1:
            top_count = ranked[0][1]
            runner_up_count = ranked[1][1]
            if top_count >= DRIFT_MAJORITY_RATIO * runner_up_count:
                other = sorted(pair for pair, _ in ranked[1:])
                warnings.append(
                    f"office/district drift: {candidate!r} ({party}) seen under "
                    f"{sorted(pair for pair, _ in ranked)} -- reconciled to "
                    f"{(canonical_office, canonical_district)!r} (majority vote; "
                    f"merged from {other})"
                )
            else:
                warnings.append(
                    f"ambiguous office/district split for {candidate!r} ({party}): "
                    f"{ranked} -- no clear majority (possibly two different "
                    f"candidates sharing a name), left unmerged for manual review"
                )
                for row in group_rows:
                    key = (row["county"], row["office"], row["district"], candidate, party)
                    if key not in merged:
                        merged[key] = row["votes"]
                        order.append(key)
                continue

        for row in group_rows:
            key = (row["county"], canonical_office, canonical_district, candidate, party)
            votes = row["votes"]
            if key not in merged:
                merged[key] = votes
                order.append(key)
            elif merged[key] != votes:
                if merged[key] == "X" and votes != "X":
                    merged[key] = votes  # prefer a real vote over a placeholder X
                elif votes == "X":
                    pass  # keep the existing real value
                else:
                    warnings.append(
                        f"drift merge conflict: {candidate!r} / {row['county']} "
                        f"({canonical_office}) -- kept {merged[key]!r}, dropped {votes!r}"
                    )

    return [
        {"county": c, "office": o, "district": d, "party": p, "candidate": cand, "votes": merged[(c, o, d, cand, p)]}
        for (c, o, d, cand, p) in order
    ]


def extract_pdf(pdf_path, model_ladder, resolution=200, start_page=None, end_page=None):
    """Extract all rows from the statewide county-totals PDF. Returns
    (rows, warnings, page_models). rows includes county == 'TOTAL' rows
    (dropped by callers the same way precinct-level TOTAL rows are)."""
    models_and_names = [(llm.get_model(name), name) for name in model_ladder]

    raw_pages = render_raw_pages(pdf_path, resolution=resolution)
    if start_page or end_page:
        lo = start_page or 1
        hi = end_page or len(raw_pages)
        raw_pages = [(n, img) for n, img in raw_pages if lo <= n <= hi]

    rows = []
    warnings = []
    seen_keys = {}
    page_models = {}
    carry_office = None

    for page_num, img in raw_pages:
        text, used_model = extract_page_with_fallback(
            models_and_names, img, page_num, carry_office, warnings
        )
        if text is None:
            continue
        page_models[page_num] = used_model
        parsed_rows, unparsed, orphan_header = parse_page_rows(text)
        for line in unparsed:
            warnings.append(f"p{page_num}: could not parse line {line!r}")
        # An orphan header (a bold office header with no candidate rows
        # under it on this page) takes priority over the last real row's
        # office: it means THIS page's trailing context is that header,
        # not whatever race happened to have the last completed row.
        if orphan_header:
            carry_office = orphan_header
        elif parsed_rows:
            carry_office = parsed_rows[-1][0]

        for office_raw, candidate, party, county, votes_raw in parsed_rows:
            office, district = split_office_district(office_raw)

            votes = votes_raw if votes_raw.upper() == "X" else votes_raw
            if votes_raw.upper() != "X" and not votes_raw.lstrip("-").isdigit():
                warnings.append(
                    f"p{page_num}: non-numeric votes {votes_raw!r} for "
                    f"{candidate} / {county}"
                )
                continue

            dedup_key = (county, office, district, candidate, party)
            prior = seen_keys.get(dedup_key)
            if prior is not None:
                if prior != votes:
                    warnings.append(
                        f"p{page_num}: duplicate row for {candidate} / {county} "
                        f"({office}) -- kept first value {prior!r}, dropped {votes!r}"
                    )
                else:
                    warnings.append(
                        f"p{page_num}: duplicate row for {candidate} / {county} "
                        f"({office}) -- dropped repeated identical value"
                    )
                continue
            seen_keys[dedup_key] = votes

            rows.append({
                "county": county,
                "office": office,
                "district": district,
                "party": party,
                "candidate": candidate,
                "votes": votes,
            })

    rows = reconcile_drifted_offices(rows, warnings)
    return rows, warnings, page_models


def write_csv(rows, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("-m", "--model", default="qwen3.5:397b-cloud", nargs="+",
                     help="model, or space-separated fallback ladder (first = primary)")
    ap.add_argument("-r", "--resolution", type=int, default=200)
    ap.add_argument("--start-page", type=int, help="1-indexed, inclusive")
    ap.add_argument("--end-page", type=int, help="1-indexed, inclusive")
    args = ap.parse_args()

    model_ladder = args.model if isinstance(args.model, list) else [args.model]
    print(f"Extracting {args.pdf_path} with {model_ladder} "
          f"(pages {args.start_page or 1}-{args.end_page or 'end'}) ...")
    rows, warnings, page_models = extract_pdf(
        args.pdf_path, model_ladder, resolution=args.resolution,
        start_page=args.start_page, end_page=args.end_page,
    )
    print(f"  extracted {len(rows)} rows from {len(page_models)} pages")
    for w in warnings:
        print(f"  ! {w}", file=sys.stderr)

    write_csv(rows, args.output)
    print(f"  wrote {args.output}")


if __name__ == "__main__":
    main()
