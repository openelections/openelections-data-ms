"""Parse the 2024 general election statewide recap PDF into a county-level CSV.

The statewide PDF has a text layer (ruled tables), so it can be parsed
deterministically without OCR. This produces the county-level totals CSV
needed for verification of precinct-level OCR extraction.

Usage:
    uv run python parse_2024_general_statewide.py \
        "2024/general/2024 Official Statewide Results.pdf" \
        2024/20241105__ms__general__county.csv
"""

import argparse
import csv
import re
from pathlib import Path

from natural_pdf import PDF

OFFICE_MAP = {
    "United States-President": "President",
    "United States-Senate": "U.S. Senate",
    "US House Of Rep": "U.S. House",
}

# Canonical 82-county spellings
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

FIELDS = ["county", "office", "district", "party", "candidate", "votes"]


def reverse_county(text):
    """County headers are rendered rotated, so the extracted string is reversed."""
    return text[::-1].strip()


def parse_office(label):
    """Return (office, district) for an office header label."""
    label = label.strip()

    if "United States-President" in label or "President" in label:
        return "President", ""

    if "United States-Senate" in label or "U.S. Senate" in label:
        return "U.S. Senate", ""

    # US House: "US House Of Rep 01-1st Congressional District"
    house_match = re.search(r"US House Of Rep 0*(\d+)", label)
    if house_match:
        district_num = str(int(house_match.group(1)))
        return "U.S. House", district_num

    return None


def parse_candidate(label):
    """Parse a candidate row label into (name, party).

    Examples:
    - "Presidential Electors for Kamala D. Harris for President and Tim Walz for Vice President Democrat"
    - "Presidential Electors for Donald J. Trump for President and J.D. Vance for Vice President Republican"
    - "Presidential Electors for Chase Oliver for President and Mike ter Maat for Vice President Libertarian"
    """
    label = label.strip()

    # Party is typically the last word
    party_map = {
        "Democrat": "DEM",
        "Republican": "REP",
        "Libertarian": "LIB",
        "Constitution": "CON",
        "Green": "GRN",
    }

    party = None
    for party_word, abbr in party_map.items():
        if label.endswith(party_word):
            party = abbr
            label = label[:-len(party_word)].strip()
            break

    if not party:
        # Try to find party abbreviation at end
        for abbr in ["DEM", "REP", "LIB", "CON", "GRN"]:
            if label.endswith(abbr):
                party = abbr
                label = label[:-len(abbr)].strip()
                break

    # Clean up the candidate name
    # Remove "Presidential Electors for " prefix
    label = re.sub(r"^Presidential Electors for ", "", label)
    label = re.sub(r"^Candidate for ", "", label)

    return label.strip(), party


def parse_pdf(pdf_path):
    """Extract county-level results from the statewide PDF."""
    pdf = PDF(str(pdf_path))
    rows = []

    for page in pdf.pages[1:]:  # skip cover page
        table = page.extract_table()
        data = table.to_list() if hasattr(table, "to_list") else table

        # Find county header row
        county_by_col = {}
        total_col = None

        for row in data:
            if row[0] and "Votes cast in the State" in str(row[0]):
                for ci in range(1, len(row)):
                    name = str(row[ci] or "").strip()
                    if not name:
                        continue
                    rev = reverse_county(name)
                    if rev == "TOTAL":
                        total_col = ci
                    elif rev in CANONICAL_COUNTIES:
                        county_by_col[ci] = rev
                break

        # Process body rows
        current_office = None
        current_district = ""

        for row in data:
            label = str(row[0] or "").strip()
            if not label or label.startswith("Votes cast") or label.startswith("Official"):
                continue

            # Check if this is an office header
            office = parse_office(label)
            if office:
                current_office, current_district = office
                continue

            # Check if this is a candidate row
            if current_office:
                candidate_name, party = parse_candidate(label)
                if party and candidate_name:
                    # Extract votes for each county
                    for ci, county in county_by_col.items():
                        if ci >= len(row):
                            continue
                        val = str(row[ci] or "").strip()
                        if val.upper() == "X" or not val:
                            continue
                        if val.lstrip("-").isdigit():
                            rows.append({
                                "county": county,
                                "office": current_office,
                                "district": current_district,
                                "party": party,
                                "candidate": candidate_name,
                                "votes": int(val),
                            })

    return rows


def write_csv(rows, output_path):
    """Write rows to CSV, sorted by county/office/candidate."""
    rows.sort(key=lambda r: (r["county"], r["office"], r["district"], r["party"], r["candidate"]))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("output_csv")
    args = ap.parse_args()

    print(f"Parsing {args.pdf_path} ...")
    rows = parse_pdf(args.pdf_path)

    counties = {r["county"] for r in rows}
    offices = {r["office"] for r in rows}

    print(f"  extracted {len(rows)} rows")
    print(f"  counties: {len(counties)}")
    print(f"  offices: {sorted(offices)}")

    write_csv(rows, args.output_csv)
    print(f"  wrote {args.output_csv}")


if __name__ == "__main__":
    main()
