"""Verify extracted 2024 general election precinct CSVs against the official
county-level totals, with an internal cross-check against each PDF's own TOTAL row.

Three numbers are compared per candidate:
  - extracted sum: sum of all non-TOTAL precinct rows in the intermediate CSV
  - pdf total: the TOTAL row the model read off the last page (if any)
  - official total: the vote count in 2024/20241105__ms__general__county.csv

extracted sum != pdf total   -> OCR likely misread a precinct's digits
extracted sum == pdf total
    but != official total    -> systematic error (missing precinct page,
                                 candidate misattribution, or a genuine source
                                 discrepancy)
both match                   -> OK

Usage:
    uv run python verify_2024.py <intermediate_csv> --county Adams \
        --county-csv 2024/20241105__ms__general__county.csv

    uv run python verify_2024.py --batch cache/2024/intermediate \
        --county-csv 2024/20241105__ms__general__county.csv \
        -o cache/2024/verification_report.md
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

OFFICE_PRES = "President"
_PRESIDENT_RUNNING_MATE_RE = re.compile(r"^(.*?)\s+for\s+President\b", re.IGNORECASE)


def standardize_candidate(candidate, office):
    """Office-specific candidate name normalization, shared between extraction
    and verification so both sides of a comparison use the same key. The
    official county CSV lists President candidates by their full ticket
    ('Kamala D. Harris for President and Tim Walz for Vice President'); keep
    just the presidential candidate's own name."""
    if office == OFFICE_PRES:
        m = _PRESIDENT_RUNNING_MATE_RE.match(candidate)
        if m:
            return m.group(1).strip()
    return candidate


def load_official_totals(county_csv_path, county):
    """Return {(office, district, candidate, party): votes} for one county.

    A primary's county-totals CSV (unlike the 2024 general's) carries an
    'X' row for every county a district race doesn't cover -- not a real
    total to compare against, and not an int()-able value."""
    totals = {}
    with open(county_csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if row["county"] != county:
                continue
            if row["votes"].strip().upper() == "X":
                continue
            candidate = standardize_candidate(row["candidate"], row["office"])
            key = (row["office"], row["district"], candidate, row["party"])
            totals[key] = int(row["votes"])
    return totals


def verify_county(intermediate_csv, official_totals):
    """Return a list of dicts: office, district, candidate, party, extracted_sum,
    pdf_total, official_total, status."""
    extracted_sum = {}
    pdf_total = {}
    has_any_total_row = False

    with open(intermediate_csv, newline="") as f:
        for row in csv.DictReader(f):
            key = (row["office"], row["district"], row["candidate"], row["party"])
            votes = row["votes"]
            if row["precinct"].strip().upper() == "TOTAL":
                has_any_total_row = True
                if votes.upper() != "X" and votes.lstrip("-").isdigit():
                    pdf_total[key] = int(votes)
                continue
            if votes.upper() == "X":
                continue
            if votes.lstrip("-").isdigit():
                extracted_sum[key] = extracted_sum.get(key, 0) + int(votes)

    all_keys = set(extracted_sum) | set(pdf_total) | set(official_totals)
    results = []
    for key in sorted(all_keys):
        office, district, candidate, party = key
        esum = extracted_sum.get(key)
        ptotal = pdf_total.get(key)
        official = official_totals.get(key)

        if official is None:
            status = "NO_OFFICIAL_DATA"
        elif esum is None:
            status = "MISSING_FROM_EXTRACTION"
        elif ptotal is not None and esum != ptotal:
            status = "INTERNAL_MISMATCH"
        elif esum != official:
            status = "OFFICIAL_MISMATCH"
        else:
            status = "OK"

        results.append({
            "office": office,
            "district": district,
            "candidate": candidate,
            "party": party,
            "extracted_sum": esum,
            "pdf_total": ptotal,
            "official_total": official,
            "status": status,
        })

    return results, has_any_total_row


def summarize(results):
    counts = defaultdict(int)
    for r in results:
        counts[r["status"]] += 1
    return counts


def print_results(county, results, has_any_total_row):
    print(f"{county}:")
    if not has_any_total_row:
        print("  ! no TOTAL row found in extraction -- internal check unavailable")
    for r in results:
        tag = f"{r['candidate']} ({r['party']}) - {r['office']}{'-' + r['district'] if r['district'] else ''}"
        if r["status"] == "OK":
            print(f"  ✓ {tag}: {r['extracted_sum']}")
        else:
            print(
                f"  ! {tag}: {r['status']} "
                f"extracted={r['extracted_sum']} pdf_total={r['pdf_total']} "
                f"official={r['official_total']}"
            )
    counts = summarize(results)
    print(f"  {dict(counts)}")


def _slug_to_county(county_slug):
    """Reverse a filename slug ('desoto', 'jeff_davis') back to its canonical
    county name ('DeSoto', 'Jeff Davis'). str.title() alone mangles internal
    capitals like DeSoto -> Desoto, so match against the canonical roster."""
    from parse_recap_pdf import CANONICAL_COUNTIES
    guess = county_slug.replace("_", " ").title()
    for name in CANONICAL_COUNTIES:
        if name.lower().replace(" ", "_") == county_slug:
            return name
    return guess


def batch_verify(intermediate_dir, county_csv):
    """intermediate_dir contains files named {county_slug}.csv.
    Returns {county: (results, has_any_total_row)}."""
    out = {}
    for path in sorted(Path(intermediate_dir).glob("*.csv")):
        stem = path.stem
        county = _slug_to_county(stem)
        official = load_official_totals(county_csv, county)
        results, has_total = verify_county(path, official)
        out[county] = (results, has_total)
    return out


def write_report(all_results, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("# 2024 General Election Precinct Extraction Verification\n\n")
        f.write("| County | OK | Internal mismatch | Official mismatch | Missing | No official data |\n")
        f.write("|---|---|---|---|---|---|\n")
        for county, (results, has_total) in sorted(all_results.items()):
            counts = summarize(results)
            f.write(
                f"| {county} | {counts['OK']} | "
                f"{counts['INTERNAL_MISMATCH']} | {counts['OFFICIAL_MISMATCH']} | "
                f"{counts['MISSING_FROM_EXTRACTION']} | {counts['NO_OFFICIAL_DATA']} |\n"
            )
        f.write("\n## Details (non-OK candidates)\n\n")
        for county, (results, has_total) in sorted(all_results.items()):
            bad = [r for r in results if r["status"] != "OK"]
            if not bad and has_total:
                continue
            f.write(f"### {county}\n\n")
            if not has_total:
                f.write("- no TOTAL row found in extraction\n")
            for r in bad:
                tag = f"{r['candidate']} ({r['party']}) - {r['office']}{'-' + r['district'] if r['district'] else ''}"
                f.write(
                    f"- **{r['status']}** {tag}: extracted={r['extracted_sum']} "
                    f"pdf_total={r['pdf_total']} official={r['official_total']}\n"
                )
            f.write("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("intermediate_csv", nargs="?")
    ap.add_argument("--county")
    ap.add_argument("--county-csv")
    ap.add_argument("--batch", help="directory of intermediate CSVs to verify")
    ap.add_argument("--county-csv-batch", default="2024/20241105__ms__general__county.csv")
    ap.add_argument("-o", "--output", default="cache/2024/verification_report.md")
    args = ap.parse_args()

    if args.batch:
        all_results = batch_verify(args.batch, args.county_csv_batch)
        for county, (results, has_total) in sorted(all_results.items()):
            print_results(county, results, has_total)
            print()
        write_report(all_results, args.output)
        print(f"Report written to {args.output}")
    else:
        if not (args.intermediate_csv and args.county and args.county_csv):
            ap.error("single-file mode requires intermediate_csv, --county, --county-csv")
        official = load_official_totals(args.county_csv, args.county)
        results, has_total = verify_county(args.intermediate_csv, official)
        print_results(args.county, results, has_total)


if __name__ == "__main__":
    main()
