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
SENATE_RE = re.compile(r"State Senate\s+0*(\d+)")
# 2015 general prints State House as "State House Of Rep 01-District 01" (the
# federal House prints "US House Of Rep"); the leading word disambiguates them.
STATEHOUSE_RE = re.compile(r"State House Of Rep\s*0*(\d+)")
STATEOFFICE_RE = re.compile(
    r"State Of Mississippi-(Governor|Lieutenant Governor|Secretary Of State|"
    r"Attorney General|State Auditor|State Treasurer)$"
)
OFFICE_OUT = {
    "Governor": "Governor",
    "Lieutenant Governor": "Lieutenant Governor",
    "Secretary Of State": "Secretary of State",
    "Attorney General": "Attorney General",
    "State Auditor": "State Auditor",
    "State Treasurer": "State Treasurer",
    "Agriculture & Commerce": "Commissioner of Agriculture & Commerce",
    "Insurance": "Commissioner of Insurance",
}
STATE_COMMISH_RE = re.compile(
    r"State Of Mississippi-Commissioner Of (Agriculture & Commerce|Insurance)$")
# offices recognized but not emitted to the county file (repo convention:
# District Attorney + judicial races are local; PSC/Transportation are
# district-level and only emitted when the year's county file wants them)
SKIP_OFFICES = ("District Attorney", "Judicial")
RE_DISTRICT_OFFICE = re.compile(
    r"(District Attorney|Public Service Commissioner|Transportation Commissioner)"
    r"\s*0*\d*\s*-(?P<dist>[A-Za-z0-9 ]+)\s*(?:District)?\s*$")
RE_JUDICIAL = re.compile(r"^(Chancery|Circuit) Court\b")
PARTY_WORDS = {"Democrat": "DEM", "Republican": "REP", "Reform": "REF",
               "Libertarian": "LIB", "Independent": "IND", "Constitution": "CON",
               "Write-in": "WI", "Nonpartisan": "NON", "Green": "GRE"}

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
    m = STATEHOUSE_RE.match(label)
    if m:
        return "State House", str(int(m.group(1)))
    m = SENATE_RE.search(label)
    if m:
        return "State Senate", str(int(m.group(1)))
    m = STATE_COMMISH_RE.search(label)
    if m:
        return OFFICE_OUT[m.group(1)], ""
    m = STATEOFFICE_RE.match(label)
    if m:
        return OFFICE_OUT[m.group(1)], ""
    m = RE_DISTRICT_OFFICE.search(label)
    if m:
        office = m.group(1)
        dist = m.group("dist").replace(" District", "", 1).strip()
        return office, dist
    if RE_JUDICIAL.match(label):
        return "Judicial", label
    return None


def split_candidate(label, expected_party):
    """Split a candidate-row label 'Name ... Democrat' into (name, party_abbr),
    or None if the trailing word is not a party word."""
    parts = label.rsplit(None, 1)
    if len(parts) == 2 and parts[1] in PARTY_WORDS:
        abbr = PARTY_WORDS[parts[1]]
        if expected_party and abbr != expected_party:
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

    # The doc repeats its office sections once per county chunk (sheets come in
    # groups of 8 chunk page sets). A section row band that does not fit on the
    # sheet wraps to the top of the NEXT sheet carrying the same county chunk,
    # before that sheet's first office header. Those wrapped rows belong to the
    # last section seen on the previous same-chunk sheet (e.g. the 2015 recap's
    # State Treasurer rows print atop the Ag/Insurance group's chunk pages, and
    # SH46's Strachan row wraps onto the next group's sheets while SH46's other
    # candidate prints in place).
    pending_office = {}  # chunk id -> (office, district) awaiting its wrapped rows
    chunk_ids = {}  # county-set tuple -> chunk id, learned in encounter order

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

        chunk_id = None
        saw_header = False
        if county_by_col:
            ckey = tuple(county_by_col[ci] for ci in sorted(county_by_col))
            if ckey not in chunk_ids:
                chunk_ids[ckey] = len(chunk_ids)
            chunk_id = chunk_ids[ckey]

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
                saw_header = True
                continue

            cand = split_candidate(label, party)
            if cand is None:
                continue
            name, abbr = cand

            # Wrapping rows before this sheet's first office header come from
            # the previous same-chunk sheet's last section; decide the office
            # they land in before any skip, since the carried office may be a
            # skipped section (e.g. a DA band cut at the sheet bottom).
            if not saw_header and chunk_id in pending_office:
                row_office, row_district = pending_office[chunk_id]
            else:
                row_office, row_district = current_office, current_district
            if row_office is None:
                print(f"  ! candidate before any office header: {name!r}",
                      file=sys.stderr)
                continue
            if row_office in SKIP_OFFICES:
                continue

            key = (row_office, row_district, name)
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
                    "office": row_office,
                    "district": row_district,
                    "party": abbr,
                    "candidate": name,
                    "votes": votes,
                })
                summed[key] = summed.get(key, 0) + votes

            if total_col is not None and total_col < len(row):
                tval = _clean(row[total_col])
                if tval.isdigit():
                    totals[key] = int(tval)

        # A sheet's last section is the one whose row band may wrap onto the
        # next same-chunk sheet's top.
        if chunk_id is not None and current_office is not None:
            pending_office[chunk_id] = (current_office, current_district)

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
    ap.add_argument("--party", default="", choices=["", "DEM", "REP"],)
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
