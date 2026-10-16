"""Cross-check the 2019 primary RUNOFF county CSV against the runoff
precinct-level CSVs in 2019/counties/. The precinct files are independently
sourced, so matching sums verify the PDF parse cell-by-cell (for the offices
the precinct files cover: R Governor, SD 1/3/8/37/51, HD 10/87/88/95/105/106/
114; D SD 8/10/13/22, HD 63/70 — the runoff precinct files do not cover R
Attorney General, R Transportation Commissioner-Northern, or D PSC-Central).

Usage: uv run python crosscheck_2019_runoff.py [county_csv]

The runoff precinct files come in several layouts (all internally
consistent), detected from the header row:
  page,candidate,office,district,party,county,precinct,votes   (most files)
  candidate,office,district,party,county,precinct,votes        (grenada, hinds)
  county,precinct,office,district,candidate,party,votes        (copiah, pike)
  16,candidate,office,...                                      (noxubee: stray
                                                                page header)
"""

import csv
import glob
import os
import re
import sys
from collections import defaultdict

COUNTIES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "2019", "counties")

# OCR variants of candidate names in the precinct files (name_key'd).
NAME_ALIASES = {
    "jaymcnight": "jaymcknight",           # HD 95
    "jeffreysjeffgulce": "jeffreysjeffguice",  # HD 114
}

PARTY_MAP = {"R": "REP", "D": "DEM"}


def name_key(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def office_key(office, district):
    low = office.lower().strip()
    if low == "state house":
        low = "state house of rep"
    return low, str(int(district)) if district.strip() else ""


def load_precinct():
    agg = defaultdict(int)
    for path in sorted(glob.glob(os.path.join(
            COUNTIES_DIR, "20190827__ms__primary_runoff__*__precinct.csv"))):
        county = re.search(r"runoff__(.+?)__precinct", path).group(1)
        with open(path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            # Drop a stray page-number cell in the header (noxubee).
            header = [h for i, h in enumerate(header) if h.strip() or i == 0]
            cols = {h.strip().lower(): i for i, h in enumerate(header)}
            if "candidate" not in cols or "votes" not in cols:
                print(f"  ! {path}: unrecognized header {header}", file=sys.stderr)
                continue
            for row in reader:
                if not row or not row[cols["votes"]].strip():
                    continue
                val = row[cols["votes"]].strip()
                if not val.isdigit():
                    continue  # 'X' (not on ballot) etc.
                county_name = (row[cols["county"]].strip() if
                               row[cols["county"]].strip() else county)
                party = PARTY_MAP.get(row[cols["party"]].strip().upper(),
                                      row[cols["party"]].strip().upper())
                office, district = office_key(row[cols["office"]],
                                              row[cols["district"]])
                cand = name_key(row[cols["candidate"]])
                cand = NAME_ALIASES.get(cand, cand)
                agg[(county_name.lower(), office, district, cand, party)] \
                    += int(val)
    return agg


def load_county(path):
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            office, district = office_key(row["office"], row["district"])
            cand = name_key(row["candidate"])
            cand = NAME_ALIASES.get(cand, cand)
            rows.append((row["county"].lower(), office, district,
                         cand, row["party"], int(row["votes"]), row))
    return rows


def main():
    precinct = load_precinct()
    print(f"precinct aggregation: {len(precinct)} (county, office, candidate) keys")
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "2019", "20190827__ms__primary_runoff__county.csv")
    rows = load_county(path)
    ok = True
    checked = matched = 0
    for cl, office, district, cand, party, votes, raw in rows:
        pk = (cl, office, district, cand, party)
        if pk not in precinct:
            continue  # offices/counties the precinct files don't cover
        checked += 1
        if precinct[pk] == votes:
            matched += 1
        else:
            ok = False
            print(f"  ! {raw['county']} / {raw['candidate']} "
                  f"({raw['office']} {raw['district']}): parsed {votes} "
                  f"!= precinct sum {precinct[pk]}")
    # Precinct keys with no county-CSV counterpart (name or office mismatches
    # the alias map didn't catch).
    csv_keys = {(cl, office, district, cand, party)
                for cl, office, district, cand, party, _, _ in rows}
    orphans = set(precinct) - csv_keys
    for pk in sorted(orphans):
        ok = False
        print(f"  ! precinct key with no county-CSV counterpart: {pk} "
              f"(sum {precinct[pk]})")
    print(f"checked {checked} of {len(rows)} county-CSV values "
          f"({len(rows) - checked} not covered by precinct files): "
          f"{matched} match" + (", 0 mismatches" if ok else ", MISMATCHES"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())