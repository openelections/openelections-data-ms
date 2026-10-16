"""Parse a Mississippi "Official Recapitulation" primary PDF into OpenElections
county-level CSV.

The recap PDFs are a crosstab: counties run across the top as rotated column
headers, candidates are rows grouped under bold office-header rows, and each cell
is a vote count (or "X" when the candidate is not on the ballot in that county).
A final "TOTAL" column carries the statewide total and is used only to verify the
per-county sums.

Primary extraction is deterministic via NaturalPDF table extraction (the PDF has
ruling lines, so columns are unambiguous). An optional `--verify` pass renders
each page to an image and asks an `llm` vision model to re-read it, then reports
any cells that disagree with the deterministic parse.

Usage:
    uv run python parse_recap_pdf.py <input.pdf> <output.csv> --party DEM|REP \
        [--verify] [-m claude-haiku-4.5]
"""

import argparse
import csv
import re
import sys
from pathlib import Path

from natural_pdf import PDF

OFFICE_SENATE = "U.S. Senate"
OFFICE_HOUSE = "U.S. House"

HOUSE_RE = re.compile(r"US House Of Rep\s+0*(\d+)")
PARTY_WORDS = {"Democrat": "DEM", "Republican": "REP"}

# Canonical 82-county spellings (from 2023/20231107__ms__general__county.csv).
CANONICAL_COUNTIES = {
    "Adams", "Alcorn", "Amite", "Attala", "Benton", "Bolivar", "Calhoun",
    "Carroll", "Chickasaw", "Choctaw", "Claiborne", "Clarke", "Clay", "Coahoma",
    "Copiah", "Covington", "DeSoto", "Forrest", "Franklin", "George", "Greene",
    "Grenada", "Hancock", "Harrison", "Hinds", "Holmes", "Humphreys", "Issaquena",
    "Itawamba", "Jackson", "Jasper", "Jeff Davis", "Jefferson", "Jones", "Kemper",
    "Lafayette", "Lamar", "Lauderdale", "Lawrence", "Leake", "Lee", "Leflore",
    "Lincoln", "Lowndes", "Madison", "Marion", "Marshall", "Monroe", "Montgomery",
    "Neshoba", "Newton", "Noxubee", "Oktibbeha", "Panola", "Pearl River", "Perry",
    "Pike", "Pontotoc", "Prentiss", "Quitman", "Rankin", "Scott", "Sharkey",
    "Simpson", "Smith", "Stone", "Sunflower", "Tallahatchie", "Tate", "Tippah",
    "Tishomingo", "Tunica", "Union", "Walthall", "Warren", "Washington", "Wayne",
    "Webster", "Wilkinson", "Winston", "Yalobusha", "Yazoo",
}

# A single result row.
FIELDS = ["county", "office", "district", "party", "candidate", "votes"]


def _clean(cell):
    """Normalize a table cell to a stripped string ("" for None)."""
    if cell is None:
        return ""
    return str(cell).replace("\n", " ").strip()


def reverse_county(text):
    """County headers are rendered rotated, so the extracted string is reversed
    (e.g. 'smadA' -> 'Adams', 'reviR lraeP' -> 'Pearl River'). Casing is
    preserved by the reversal."""
    return text[::-1].strip()


def parse_office(label):
    """Return (office, district) for an office-header label, or None if the label
    is not an office header."""
    if "United States-Senate" in label:
        return OFFICE_SENATE, ""
    m = HOUSE_RE.search(label)
    if m:
        return OFFICE_HOUSE, str(int(m.group(1)))
    return None


def split_candidate(label, expected_party):
    """Split a candidate-row label 'Name ... Democrat' into (name, party_abbr),
    or None if the trailing word is not a party word."""
    parts = label.rsplit(None, 1)
    if len(parts) == 2 and parts[1] in PARTY_WORDS:
        abbr = PARTY_WORDS[parts[1]]
        if abbr != expected_party:
            print(f"  ! party mismatch: row says {parts[1]} but file is "
                  f"{expected_party}: {label!r}", file=sys.stderr)
        return parts[0].strip(), abbr
    return None


def parse_pdf(pdf_path, party):
    """Deterministically extract result rows and per-candidate printed totals.

    Returns (rows, totals) where rows is a list of dicts (FIELDS) and totals maps
    (office, district, candidate) -> printed TOTAL int (or None if absent)."""
    pdf = PDF(str(pdf_path))
    rows = []
    totals = {}
    summed = {}  # (office, district, candidate) -> running per-county sum
    current_office = None
    current_district = ""
    bad_counties = set()

    for page in pdf.pages[1:]:  # skip the title page
        table = page.extract_table()
        data = table.to_list() if hasattr(table, "to_list") else table

        # Locate the county-header row ("Votes cast in the State ..."), which
        # carries the reversed county names across columns 1..N.
        county_by_col = {}  # column index -> county name ("" marks TOTAL/blank)
        total_col = None
        for row in data:
            if _clean(row[0]).startswith("Votes cast in the State"):
                for ci in range(1, len(row)):
                    name = _clean(row[ci])
                    if not name:
                        continue
                    rev = reverse_county(name)
                    if rev == "TOTAL":
                        total_col = ci
                    else:
                        county_by_col[ci] = rev
                        if rev not in CANONICAL_COUNTIES:
                            bad_counties.add(rev)
                break

        # Walk the body rows in order, tracking the current office.
        for row in data:
            label = _clean(row[0])
            if not label or label.startswith("Votes cast in the State") \
                    or label.startswith("Official Recapitulation") \
                    or label == "Names of Counties":
                continue

            office = parse_office(label)
            if office is not None:
                current_office, current_district = office
                continue

            cand = split_candidate(label, party)
            if cand is None:
                continue
            name, abbr = cand
            if current_office is None:
                print(f"  ! candidate before any office header: {name!r}",
                      file=sys.stderr)
                continue

            key = (current_office, current_district, name)
            for ci, county in county_by_col.items():
                if ci >= len(row):
                    continue
                val = _clean(row[ci])
                if val == "" or val.upper() == "X":
                    continue
                if not val.lstrip("-").isdigit():
                    print(f"  ! non-numeric vote {val!r} for {name} / {county}",
                          file=sys.stderr)
                    continue
                votes = int(val)
                rows.append({
                    "county": county,
                    "office": current_office,
                    "district": current_district,
                    "party": abbr,
                    "candidate": name,
                    "votes": votes,
                })
                summed[key] = summed.get(key, 0) + votes

            if total_col is not None and total_col < len(row):
                tval = _clean(row[total_col])
                if tval.isdigit():
                    totals[key] = int(tval)

    if bad_counties:
        print(f"  ! WARNING: unrecognized county names: {sorted(bad_counties)}",
              file=sys.stderr)

    return rows, totals, summed


def reconcile(totals, summed):
    """Compare per-candidate per-county sums to the printed TOTAL column."""
    ok = True
    for key, printed in sorted(totals.items()):
        office, district, name = key
        got = summed.get(key, 0)
        tag = f"{name} ({office}{'-' + district if district else ''})"
        if got != printed:
            ok = False
            print(f"  ! TOTAL mismatch {tag}: summed {got} != printed {printed}",
                  file=sys.stderr)
    if ok:
        print(f"  ✓ total reconciliation passed for {len(totals)} candidates")
    return ok


def write_csv(rows, output_path):
    rows.sort(key=lambda r: (r["county"], r["office"], r["district"],
                             r["candidate"]))
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def verify_with_llm(pdf_path, rows, model_name):
    """Render each data page to an image, ask an llm vision model to read the
    grid, and report cells that disagree with the deterministic parse."""
    import llm

    model = llm.get_model(model_name)
    pdf = PDF(str(pdf_path))
    # Index deterministic rows by (county, office, district, candidate) -> votes.
    det = {(r["county"], r["office"], r["district"], r["candidate"]): r["votes"]
           for r in rows}

    prompt = (
        "This page is a crosstab of Mississippi primary results: counties are "
        "column headers (rotated text) across the top, candidates are rows under "
        "bold office headers (US Senate, US House district N). Cells are vote "
        "counts; 'X' means not on the ballot. Output ONLY CSV lines, no header, "
        "as: county,office,district,candidate,votes . Use office='U.S. Senate' "
        "(district blank) or 'U.S. House' (district 1-4). Skip 'X' cells and skip "
        "the TOTAL column."
    )

    mismatches = 0
    for i, page in enumerate(pdf.pages[1:], start=2):
        img = page.render(resolution=150)
        tmp = Path(f"/tmp/recap_verify_p{i}.png")
        img.save(tmp)
        resp = model.prompt(prompt, attachments=[llm.Attachment(path=str(tmp))])
        for line in resp.text().strip().splitlines():
            rec = next(csv.reader([line]), None)
            if not rec or len(rec) != 5:
                continue
            county, office, district, candidate, votes = (c.strip() for c in rec)
            if not votes.lstrip("-").isdigit():
                continue
            key = (county, office, district, candidate)
            if key in det and det[key] != int(votes):
                mismatches += 1
                print(f"  ! verify p{i}: {key} llm={votes} parsed={det[key]}",
                      file=sys.stderr)
    if mismatches == 0:
        print("  ✓ llm verification found no disagreements")
    else:
        print(f"  ! llm verification flagged {mismatches} cell(s) to review",
              file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("output_csv")
    ap.add_argument("--party", required=True, choices=["DEM", "REP"])
    ap.add_argument("--verify", action="store_true",
                    help="cross-check each page with an llm vision model")
    ap.add_argument("-m", "--model", default="claude-haiku-4.5",
                    help="llm model for --verify (default: claude-haiku-4.5)")
    args = ap.parse_args()

    print(f"Parsing {args.pdf_path} ...")
    rows, totals, summed = parse_pdf(args.pdf_path, args.party)
    counties = {r["county"] for r in rows}
    print(f"  extracted {len(rows)} rows across {len(counties)} counties")

    reconcile(totals, summed)

    write_csv(rows, args.output_csv)
    print(f"  wrote {args.output_csv}")

    if args.verify:
        print("Verifying with llm vision model ...")
        verify_with_llm(args.pdf_path, rows, args.model)


if __name__ == "__main__":
    main()
