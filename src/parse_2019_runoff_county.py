"""Parse the 2019 primary RUNOFF "Official Recapitulation" PDFs into the
OpenElections county-level CSV `2019/20190827__ms__primary_runoff__county.csv`.

Sources (both electronic text-layer PDFs, so natural_pdf table extraction is
deterministic — no OCR needed):
    ~/code/openelections-sources-ms/2019/REP Official Recap 8-27-19.pdf
    ~/code/openelections-sources-ms/2019/DEM Official Recap 8-27-19.pdf

Layout (see ocr-primary-pdf-runbook.md for the family): counties run across the
top as rotated column headers whose extracted text is REVERSED ("smadA" ->
"Adams", "LATOT" -> "TOTAL"); candidates are rows grouped under office-header
rows, with "X" where the candidate was not on the ballot in that county. Each
party PDF repeats its 82 counties in three page groups (11-county blocks, the
last block 5 counties + TOTAL); every page of a group repeats the group's full
office-section sequence, and the state TOTAL column appears only on each
group's final page.

Page-boundary quirks handled here (they look like missing/misattributed rows
if ignored):
  * A section header can print at the bottom of a page with its candidate rows
    at the top of the NEXT page (REP p9 "State Senate 08" -> p10 Griffin/Suber;
    REP p17 "State House 88" -> p18 Staples; DEM p9 "State House 63" -> p10
    Dixon/Foster). The current office therefore carries across pages.
  * The printed TOTAL cells for REP Governor and Attorney General are empty on
    p9 (their only group-final page), so those two totals cannot be
    reconciled internally — their sums are checked against published results
    instead.

Usage:
    uv run python parse_2019_runoff_county.py
"""

import csv
import re
import sys
from pathlib import Path

from natural_pdf import PDF

SOURCES = {
    "REP": Path.home() / "code/openelections-sources-ms/2019/REP Official Recap 8-27-19.pdf",
    "DEM": Path.home() / "code/openelections-sources-ms/2019/DEM Official Recap 8-27-19.pdf",
}
OUTPUT = Path(__file__).resolve().parent.parent / "2019/20190827__ms__primary_runoff__county.csv"

PARTY_WORDS = {"Republican": "REP", "Democrat": "DEM"}

# Canonical 82-county spellings (same list as parse_recap_pdf.py).
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

# Office-header labels -> (office, district); office names match the 2019
# primary county CSVs so cross-file joins work. Districts are zero-stripped.
STATEWIDE_OFFICES = {
    "State Of Mississippi-Governor": ("Governor", ""),
    "State Of Mississippi-Attorney General": ("Attorney General", ""),
}
# "State Senate 08-District 08" / "State House Of Rep 10-District 10"
LEGISLATIVE_RE = re.compile(
    r"^(State Senate|State House Of Rep)\s+0*(\d+)-District\s+0*(\d+)$")
# District commissions spell the district out in the office name itself and
# print no trailing district number.
COMMISSIONER_RE = re.compile(
    r"^((?:Public Service|Transportation) Commissioner-[A-Za-z ]+ District)$")


def _clean(cell):
    """Normalize a table cell to a stripped string ("" for None)."""
    if cell is None:
        return ""
    return str(cell).replace("\n", " ").strip()


def parse_office(label):
    """Return (office, district) for an office-header label, else None."""
    if label in STATEWIDE_OFFICES:
        return STATEWIDE_OFFICES[label]
    m = LEGISLATIVE_RE.match(label)
    if m:
        office, dist, dist2 = m.group(1), m.group(2), m.group(3)
        if dist != dist2:
            print(f"  ! district mismatch in header: {label!r}", file=sys.stderr)
        return office, str(int(dist))
    m = COMMISSIONER_RE.match(label)
    if m:
        return m.group(1), ""
    return None


def split_candidate(label, expected_party):
    """Split a candidate-row label 'Name Republican' into (name, party_abbr),
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

    Returns (rows, totals, summed): rows is a list of FIELDS dicts; totals maps
    (office, district, candidate) -> printed state TOTAL (only where the sheet
    prints one); summed maps the same keys -> sum of extracted county cells."""
    pdf = PDF(str(pdf_path))
    rows = []
    totals = {}
    summed = {}
    current_office = None
    current_district = ""
    bad_counties = set()
    prev_labels = None
    orphan_office = None  # (office, district) governing a page's leading rows

    for page_num, page in enumerate(pdf.pages[1:], start=2):
        table = page.extract_table()
        data = table.to_list() if hasattr(table, "to_list") else table

        # Every page of a county group repeats the group's section sequence.
        # A page whose label sequence differs from the previous page's starts
        # a new group, and a section cut at the previous page's bottom
        # continues here (carry the office). Within a group, the leading
        # orphan rows belong to the same cut section as on the previous page.
        labels = tuple(_clean(r[0]) for r in data)
        new_group = labels != prev_labels
        prev_labels = labels
        if not new_group and orphan_office is not None:
            current_office, current_district = orphan_office

        # County-header row: carries the reversed county names across columns.
        county_by_col = {}  # column index -> county name ("" marks TOTAL)
        total_col = None
        for row in data:
            if _clean(row[0]).startswith("Votes cast in the State"):
                for ci in range(1, len(row)):
                    name = _clean(row[ci])
                    if not name:
                        continue
                    rev = name[::-1].strip()
                    if rev == "TOTAL":
                        total_col = ci
                    else:
                        county_by_col[ci] = rev
                        if rev not in CANONICAL_COUNTIES:
                            bad_counties.add(rev)
                break
        else:
            print(f"  ! p{page_num}: no county header row", file=sys.stderr)
            continue

        # Walk the body rows in order; the current office carries across
        # pages and page groups (a section header at a page bottom continues
        # at the top of the next page or group).
        page_orphan_office = None
        saw_office = False
        for row in data:
            label = _clean(row[0])
            if not label or label.startswith("Votes cast in the State") \
                    or label.startswith("Official Recapitulation") \
                    or label == "Names of Counties":
                continue

            office = parse_office(label)
            if office is not None:
                current_office, current_district = office
                saw_office = True
                continue

            cand = split_candidate(label, party)
            if cand is None:
                print(f"  ! p{page_num}: unrecognized row label {label!r}",
                      file=sys.stderr)
                continue
            name, abbr = cand
            if current_office is None:
                print(f"  ! p{page_num}: candidate before any office header: "
                      f"{name!r}", file=sys.stderr)
                continue
            if not saw_office and page_orphan_office is None:
                page_orphan_office = (current_office, current_district)

            key = (current_office, current_district, name)
            for ci, county in county_by_col.items():
                if ci >= len(row):
                    print(f"  ! p{page_num}: short row for {name} / {county}",
                          file=sys.stderr)
                    continue
                val = _clean(row[ci])
                if val == "" or val.upper() == "X":
                    continue
                if not val.isdigit():
                    print(f"  ! p{page_num}: non-numeric vote {val!r} for "
                          f"{name} / {county}", file=sys.stderr)
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
                    if key in totals and totals[key] != int(tval):
                        print(f"  ! inconsistent printed TOTAL for {name}: "
                              f"{totals[key]} vs {tval}", file=sys.stderr)
                    totals[key] = int(tval)

        orphan_office = page_orphan_office

    if bad_counties:
        print(f"  ! WARNING: unrecognized county names: {sorted(bad_counties)}",
              file=sys.stderr)

    return rows, totals, summed


def reconcile(totals, summed):
    """Compare per-candidate sums of all extracted county cells to the printed
    state TOTAL (printed on each group-final page)."""
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


def write_csv(all_rows, output_path):
    all_rows.sort(key=lambda r: (r["county"], r["office"], r["district"],
                                 r["candidate"]))
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(all_rows)


def main():
    all_rows = []
    ok = True
    for party, pdf_path in SOURCES.items():
        print(f"== {party}: {pdf_path.name}")
        rows, totals, summed = parse_pdf(pdf_path, party)
        print(f"  {len(rows)} rows, {len(totals)} printed totals, "
              f"{len(summed)} candidates")
        if not reconcile(totals, summed):
            ok = False
        all_rows.extend(rows)

    # Candidates whose printed TOTAL is missing (REP Governor/AG, empty on the
    # sheet): surface their sums so they can be checked against published
    # results.
    write_csv(all_rows, OUTPUT)
    print(f"wrote {len(all_rows)} rows to {OUTPUT}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())