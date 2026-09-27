"""Build the 2024 general election county-level CSV from the recap sheets.

The recap sheets CSV (2024ElectionRecapSheets.csv) has federal and judicial
races but not local offices. This script converts it to the standard format.

Local offices will need to be added from the individual county PDFs.

Usage:
    uv run python build_2024_county_csv.py \
        ~/code/openelections-sources-ms/2024/general/2024ElectionRecapSheets.csv \
        2024/20241105__ms__general__county.csv
"""

import argparse
import csv
import re
from pathlib import Path

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

OFFICE_MAP = {
    "United States-President": "President",
    "United States-Senate": "U.S. Senate",
}

HOUSE_RE = re.compile(r"US House Of Rep 0*(\d+)")

PARTY_MAP = {
    "Democrat": "DEM",
    "Republican": "REP",
    "Libertarian": "LIB",
    "Constitution": "CON",
    "Green": "GRN",
    "Independent": "IND",
}

FIELDS = ["county", "office", "district", "party", "candidate", "votes"]


def normalize_office(office_str):
    """Normalize office name to standard format."""
    office_str = office_str.strip()

    # Check predefined mappings
    if office_str in OFFICE_MAP:
        return OFFICE_MAP[office_str], ""

    # US House
    match = HOUSE_RE.search(office_str)
    if match:
        district = str(int(match.group(1)))
        return "U.S. House", district

    # Statewide judicial races (no district)
    if "Supreme Court" in office_str or "Court Of Appeals" in office_str:
        return office_str.strip(), ""

    return office_str, ""


def normalize_party(party_str):
    """Normalize party name to abbreviation."""
    party_str = party_str.strip()
    return PARTY_MAP.get(party_str, party_str[:3].upper() if party_str else "")


def clean_candidate_name(name):
    """Clean up candidate name string."""
    name = name.strip()
    # Remove "Presidential Electors for " prefix
    name = re.sub(r"^Presidential Electors for ", "", name)
    # Remove trailing party name if present
    for party_word in PARTY_MAP.keys():
        if name.endswith(f" {party_word}"):
            name = name[:-len(party_word)].strip()
    return name


def convert_recap_sheets(input_csv, output_csv):
    """Convert recap sheets CSV to standard format."""
    rows = []

    with open(input_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row["County"].strip()
            if county not in CANONICAL_COUNTIES:
                continue

            office_raw = row["Office"]
            candidate_raw = row["Candidate"]
            party_raw = row["Party"]
            votes = row["County Total"]

            office, district = normalize_office(office_raw)
            candidate = clean_candidate_name(candidate_raw)
            party = normalize_party(party_raw)

            rows.append({
                "county": county,
                "office": office,
                "district": district,
                "party": party,
                "candidate": candidate,
                "votes": int(votes) if votes.isdigit() else 0,
            })

    # Sort and write
    rows.sort(key=lambda r: (r["county"], r["office"], r["district"], r["party"], r["candidate"]))

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    counties = len(set(r["county"] for r in rows))
    offices = set(r["office"] for r in rows)
    print(f"Converted {len(rows)} rows")
    print(f"Counties: {counties}")
    print(f"Offices: {sorted(offices)}")
    print(f"Wrote {output_csv}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_csv", help="Path to 2024ElectionRecapSheets.csv")
    ap.add_argument("output_csv", help="Output path for county CSV")
    args = ap.parse_args()

    convert_recap_sheets(args.input_csv, args.output_csv)


if __name__ == "__main__":
    main()
