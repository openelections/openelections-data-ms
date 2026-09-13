"""Cross-check the parsed 2019 primary county CSVs against the precinct-level
CSVs already in 2019/counties/. The precinct files are independently sourced,
so matching sums verify the PDF parse cell-by-cell (for the offices the
precinct files cover: statewide + State Senate + State House).

Usage: uv run python crosscheck_2019_primary.py
"""

import csv
import glob
import os
import re
import sys
from collections import defaultdict

COUNTIES_DIR = os.path.join(os.path.dirname(__file__), "2019", "counties")

# Precinct files don't cover these, or name them differently.
PRECINCT_OFFICE_MAP = {
    "state house": "state house of rep",
    "state house of rep": "state house of rep",
    "state senate": "state senate",
}


def name_key(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def office_key(office, district):
    low = office.lower().strip()
    for raw, canon in PRECINCT_OFFICE_MAP.items():
        if low == raw:
            return canon, str(int(district)) if district else ""
    return low, str(int(district)) if district else ""


def load_precinct():
    agg = defaultdict(int)
    for path in glob.glob(os.path.join(COUNTIES_DIR,
                                       "20190806__ms__primary__*__precinct.csv")):
        county = re.search(r"primary__(.+)__precinct", path).group(1)
        with open(path) as f:
            for row in csv.DictReader(f):
                if row["county"]:
                    county = row["county"]
                party = {"D": "DEM", "R": "REP"}.get(row["party"].strip().upper(),
                                                     row["party"].strip().upper())
                office, district = office_key(row["office"], row["district"])
                key = (county.lower(), office, district,
                       name_key(row["candidate"]), party)
                if not row["votes"].strip().isdigit():
                    continue
                agg[key] += int(row["votes"])
    return agg


def load_parsed(path):
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            office, district = office_key(row["office"], row["district"])
            rows.append((row["county"].lower(), office, district,
                         name_key(row["candidate"]), row["party"],
                         int(row["votes"]), row))
    return rows


def main():
    precinct = load_precinct()
    print(f"precinct aggregation: {len(precinct)} (county, office, candidate) keys")
    ok = True
    checked = 0
    for path in sys.argv[1:]:
        rows = load_parsed(path)
        missing = unmatched = 0
        for cl, office, district, cand, party, votes, raw in rows:
            pk = (cl, office, district, cand, party)
            if pk not in precinct:
                missing += 1
                continue
            checked += 1
            if precinct[pk] != votes:
                ok = False
                print(f"  ! {raw['county']} / {raw['candidate']} "
                      f"({raw['office']} {raw['district']}): parsed {votes} "
                      f"!= precinct sum {precinct[pk]}")
        if missing:
            print(f"  {path}: {missing} parsed rows have no precinct counterpart "
                  f"(offices/counties the precinct files don't cover)")
    print(f"checked {checked} parsed values against precinct sums; "
          + ("all match" if ok else "MISMATCHES FOUND"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())