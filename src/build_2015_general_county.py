"""Build 2015/20151103__ms__general.csv from the certified statewide recap PDF.

Replaces the issue-#91 county file with a parse of
"2015 Statewide Recapitulation.pdf" (text-layer crosstab, see
parse_recap_pdf.py). Conventions kept from the existing file:

- header county,office,district,party,candidate,votes; CRLF line endings
- party title-cased (Rep/Dem/Ref/Lib/Ind)
- PSC/Transportation districts embedded in the office name with a blank
  district column ("Public Service Commissioner-Central District"), matching
  the 2019/2023 county files
- counties ascending, then offices in the ballot order the document prints
  them, district numeric ascending inside an office, candidates in the
  document's row order within an office/district
- a TOTAL block at the end of the file (statewide totals from the doc's
  printed TOTAL column), ordered the same way as the county rows
- District Attorney / judicial sections are parsed for the TOTAL gate but not
  emitted (repo convention: no local races, no ballot measures)

Usage: uv run python src/build_2015_general_county.py [output.csv]
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import parse_recap_pdf as prp

PDF_PATH = Path.home() / "code/openelections-sources-ms/2015/2015 Statewide Recapitulation.pdf"
DEFAULT_OUT = Path(__file__).parent.parent / "2015/20151103__ms__general.csv"

FIELDS = ["county", "office", "district", "party", "candidate", "votes"]

PARTY_OUT = {"DEM": "Dem", "REP": "Rep", "REF": "Ref", "LIB": "Lib", "IND": "Ind",
             "CON": "Con", "GRE": "Gre", "WI": "Wi", "NON": "Non"}


def display(office, district):
    """PSC/Transportation keep the district inside the office name."""
    if office in ("Public Service Commissioner", "Transportation Commissioner"):
        return f"{office}-{district} District", ""
    return office, district


def ordered_rows(rows, totals):
    """Return (county_rows, total_rows) in the file's sort order."""
    office_seq = {}   # display office -> order of first appearance in the doc
    cand_seq = {}     # (office, district, candidate) -> row order in the doc
    party_of = {}     # (office, district, candidate) -> party abbreviation

    for r in rows:
        off, dist = display(r["office"], r["district"])
        office_seq.setdefault(off, len(office_seq))
        key = (off, dist, r["candidate"])
        cand_seq.setdefault(key, len(cand_seq))
        party_of[key] = r["party"]

    def sort_key(office, district, candidate, county=""):
        return (
            county,
            office_seq[office],
            int(district) if str(district).isdigit() else 0,
            cand_seq[(office, district, candidate)],
        )

    county_rows = []
    for r in rows:
        off, dist = display(r["office"], r["district"])
        county_rows.append({
            "county": r["county"],
            "office": off,
            "district": dist,
            "party": PARTY_OUT[r["party"]],
            "candidate": r["candidate"],
            "votes": r["votes"],
        })
    county_rows.sort(key=lambda r: sort_key(r["office"], r["district"],
                                            r["candidate"], r["county"]))

    total_rows = []
    for (office, district, candidate), votes in totals.items():
        off, dist = display(office, district)
        if off not in office_seq:
            continue  # skipped offices (DA/judicial) have no county rows
        total_rows.append({
            "county": "TOTAL",
            "office": off,
            "district": dist,
            "party": PARTY_OUT[party_of[(off, dist, candidate)]],
            "candidate": candidate,
            "votes": votes,
        })
    total_rows.sort(key=lambda r: sort_key(r["office"], r["district"],
                                           r["candidate"]))
    return county_rows, total_rows


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT

    print(f"Parsing {PDF_PATH} ...")
    rows, totals, summed = prp.parse_pdf(PDF_PATH, "")
    counties = {r["county"] for r in rows}
    print(f"  extracted {len(rows)} rows across {len(counties)} counties")
    ok = prp.reconcile(totals, summed)
    if not ok:
        sys.exit("  !! TOTAL reconciliation failed; not writing the county file")

    county_rows, total_rows = ordered_rows(rows, totals)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in county_rows + total_rows:
            writer.writerow(r)
    print(f"  wrote {out_path}: {len(county_rows)} county rows, "
          f"{len(total_rows)} TOTAL rows")


if __name__ == "__main__":
    main()