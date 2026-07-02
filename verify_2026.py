"""Verify extracted 2026 primary precinct CSVs against the official county-level
totals, with an internal cross-check against each PDF's own TOTAL row.

Three numbers are compared per candidate:
  - extracted sum: sum of all non-TOTAL precinct rows in the intermediate CSV
  - pdf total: the TOTAL row the model read off the last page (if any)
  - official total: the vote count in 2026/20260310__ms__{party}__primary__county.csv

extracted sum != pdf total   -> OCR likely misread a precinct's digits
extracted sum == pdf total
    but != official total    -> systematic error (missing precinct page,
                                 candidate misattribution, or a genuine source
                                 discrepancy)
both match                   -> OK

Usage:
    uv run python verify_2026.py <intermediate_csv> --county Adams --party DEM \
        --county-csv 2026/20260310__ms__democratic__primary__county.csv

    uv run python verify_2026.py --batch cache/2026/intermediate \
        --dem-csv 2026/20260310__ms__democratic__primary__county.csv \
        --rep-csv 2026/20260310__ms__republican__primary__county.csv \
        -o cache/2026/verification_report.md
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load_official_totals(county_csv_path, county):
    """Return {(office, district, candidate): votes} for one county."""
    totals = {}
    with open(county_csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if row["county"] != county:
                continue
            key = (row["office"], row["district"], row["candidate"])
            totals[key] = int(row["votes"])
    return totals


def verify_county(intermediate_csv, official_totals):
    """Return a list of dicts: office, district, candidate, extracted_sum,
    pdf_total, official_total, status."""
    extracted_sum = defaultdict(int)
    pdf_total = {}
    has_any_total_row = False

    with open(intermediate_csv, newline="") as f:
        for row in csv.DictReader(f):
            key = (row["office"], row["district"], row["candidate"])
            votes = row["votes"]
            if row["precinct"] == "TOTAL":
                has_any_total_row = True
                if votes.upper() != "X" and votes.lstrip("-").isdigit():
                    pdf_total[key] = int(votes)
                continue
            if votes.upper() == "X":
                continue
            if votes.lstrip("-").isdigit():
                extracted_sum[key] += int(votes)

    all_keys = set(extracted_sum) | set(pdf_total) | set(official_totals)
    results = []
    for key in sorted(all_keys):
        office, district, candidate = key
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


def print_results(county, party, results, has_any_total_row):
    print(f"{county} ({party}):")
    if not has_any_total_row:
        print("  ! no TOTAL row found in extraction -- internal check unavailable")
    for r in results:
        tag = f"{r['candidate']} ({r['office']}{'-' + r['district'] if r['district'] else ''})"
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


def batch_verify(intermediate_dir, dem_csv, rep_csv):
    """intermediate_dir contains files named {county_slug}__{dem,rep}.csv.
    Returns {(county, party): (results, has_any_total_row)}."""
    party_csv = {"DEM": dem_csv, "REP": rep_csv}
    out = {}
    for path in sorted(Path(intermediate_dir).glob("*.csv")):
        stem = path.stem
        if "__" not in stem:
            continue
        county_slug, party_slug = stem.rsplit("__", 1)
        party = party_slug.upper()
        if party not in party_csv:
            continue
        county = _slug_to_county(county_slug)
        official = load_official_totals(party_csv[party], county)
        results, has_total = verify_county(path, official)
        out[(county, party)] = (results, has_total)
    return out


def write_report(all_results, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("# 2026 Primary Precinct Extraction Verification\n\n")
        f.write("| County | Party | OK | Internal mismatch | Official mismatch | Missing | No official data |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for (county, party), (results, has_total) in sorted(all_results.items()):
            counts = summarize(results)
            f.write(
                f"| {county} | {party} | {counts['OK']} | "
                f"{counts['INTERNAL_MISMATCH']} | {counts['OFFICIAL_MISMATCH']} | "
                f"{counts['MISSING_FROM_EXTRACTION']} | {counts['NO_OFFICIAL_DATA']} |\n"
            )
        f.write("\n## Details (non-OK candidates)\n\n")
        for (county, party), (results, has_total) in sorted(all_results.items()):
            bad = [r for r in results if r["status"] != "OK"]
            if not bad and has_total:
                continue
            f.write(f"### {county} ({party})\n\n")
            if not has_total:
                f.write("- no TOTAL row found in extraction\n")
            for r in bad:
                tag = f"{r['candidate']} ({r['office']}{'-' + r['district'] if r['district'] else ''})"
                f.write(
                    f"- **{r['status']}** {tag}: extracted={r['extracted_sum']} "
                    f"pdf_total={r['pdf_total']} official={r['official_total']}\n"
                )
            f.write("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("intermediate_csv", nargs="?")
    ap.add_argument("--county")
    ap.add_argument("--party", choices=["DEM", "REP"])
    ap.add_argument("--county-csv")
    ap.add_argument("--batch", help="directory of intermediate CSVs to verify")
    ap.add_argument("--dem-csv", default="2026/20260310__ms__democratic__primary__county.csv")
    ap.add_argument("--rep-csv", default="2026/20260310__ms__republican__primary__county.csv")
    ap.add_argument("-o", "--output", default="cache/2026/verification_report.md")
    args = ap.parse_args()

    if args.batch:
        all_results = batch_verify(args.batch, args.dem_csv, args.rep_csv)
        for (county, party), (results, has_total) in sorted(all_results.items()):
            print_results(county, party, results, has_total)
            print()
        write_report(all_results, args.output)
        print(f"Report written to {args.output}")
    else:
        if not (args.intermediate_csv and args.county and args.party and args.county_csv):
            ap.error("single-file mode requires intermediate_csv, --county, --party, --county-csv")
        official = load_official_totals(args.county_csv, args.county)
        results, has_total = verify_county(args.intermediate_csv, official)
        print_results(args.county, args.party, results, has_total)


if __name__ == "__main__":
    main()
