"""Cross-check the 2019 general election county CSV
(2019/20191105__ms__general__county.csv) against the 82 per-county
precinct-level CSVs in 2019/counties/.

The precinct files cover every office on the county ballot (including local
offices the county CSV doesn't carry), so matching sums verify the county CSV
cell-by-cell where coverage exists.

Office-name normalization needed (county CSV -> precinct files):
  'District Attorney 01'             <- 'District Attorney' + district '1'
  'Public Service Commissioner-Central District'
                                     <- 'Public Service Commission(er)' +
                                        district 'Central'
  'Transportation Commissioner-Northern District'
                                     <- 'Transportation Commissioner' +
                                        district 'Northern'
Party spellings vary ('D'/'Democrat', 'R'/'Republican', 'C'/'Constitution',
'L'/'LIB'/'Libertarian', 'IND'/'Independent', plus the typos 'Repubilcan' and
'Republic.an').

Usage: uv run python crosscheck_2019_general.py [county_csv]
"""

import csv
import glob
import os
import re
import sys
from collections import defaultdict

COUNTIES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "2019", "counties")
COUNTY_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "2019",
                          "20191105__ms__general__county.csv")

# Misspelled candidate names in the precinct files (name_key'd), discovered
# from orphan keys. Each file's whole column carries the same typo (e.g. the
# Simpson/Smith/Stone files spell every name one letter off), so these are
# transcription variants, not different people.
NAME_ALIASES = {
    "delberthoseman": "delberthosemann",   # Lieutenant Governor
    "jayhugues": "jayhughes",              # Lieutenant Governor
    "ardleleegreen": "addieleegreen",      # State Treasurer
    "johnydupree": "johnnydupree",         # Secretary of State
    "tommyladner": "timmyladner",          # HD 93 (Stone)
    "jelftate": "jefftate",                # SD 33 (Clarke)
    "chelkhtaylor": "cheikhtaylor",        # HD 38 (Clay/Lowndes/Oktibbeha)
    "theresagillespleisom": "theresagillespieisom",  # HD 7 (DeSoto)
    "phillipgunn": "philipgunn",           # HD 56 (Hinds/Madison)
    "hillmanteromefrazler": "hillmanteromefrazier",  # SD 27 (Hinds)
    "stephenastevehome": "stephenastevehorne",       # HD 81 (Lauderdale)
    "garyachims": "garyachism",            # HD 37 (Lowndes)
    "dennybedwell": "dannybedwell",        # SD 17 (Lowndes, Libertarian)
    "joelborngar": "joelbomgar",           # HD 58 (Madison)
    "bobbyedalley": "bobbyedailey",        # HD 10 (Panola)
    "janistripiettpatterson": "janistriplettpatterson",  # HD 3 (Prentiss)
    "bradywillamson": "bradywilliamson",   # HD 10 (Tallahatchie)
}

PARTY_MAP = {
    "D": "Democrat", "R": "Republican", "C": "Constitution",
    "L": "Libertarian", "LIB": "Libertarian", "IND": "Independent",
    "DEMOCRAT": "Democrat", "REPUBLICAN": "Republican",
    "REPUBILCAN": "Republican", "REPUBLIC.AN": "Republican",
    "CONSTITUTION": "Constitution", "INDEPENDENT": "Independent",
    "LIBERTARIAN": "Libertarian",
}

PSC_OFFICE = re.compile(r"^Public Service Commission(er)?$",
                        re.I)
TRANS_OFFICE = re.compile(r"^Transportation Commissioner$", re.I)
DA_OFFICE = re.compile(r"^District Attorney(?:\s+(\d+))?$", re.I)


def name_key(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _word_dist(d):
    """'Southern District'/'southern district' -> 'Southern'; '' stays ''."""
    d = d.strip()
    if d.lower().endswith(" district"):
        d = d[:-len(" district")]
    return d.title() if d else ""


def normalize_office(office, district, county_psc_districts=None):
    """Return the county-CSV spelling of (office, district)."""
    low = office.strip().lower()
    d = district.strip()
    if PSC_OFFICE.match(low):
        dist = _word_dist(d) or (county_psc_districts or {}).get("PSC", "")
        return (f"public service commissioner-{dist.lower()} district", "") \
            if dist else (low, "")
    if TRANS_OFFICE.match(low):
        dist = _word_dist(d) or (county_psc_districts or {}).get("TRANS", "")
        return (f"transportation commissioner-{dist.lower()} district", "") \
            if dist else (low, "")
    if DA_OFFICE.match(low):
        m = DA_OFFICE.match(low)
        dist = d or (m.group(1) if m else "")
        if dist:
            return f"district attorney {int(dist):02d}", ""
        return (low, "")
    return low, str(int(d)) if d else ""


def load_precinct(psc_by_county):
    agg = {}
    for path in sorted(glob.glob(os.path.join(
            COUNTIES_DIR, "20191105__ms__general__*__precinct.csv"))):
        county = re.search(r"general__(.+?)__precinct", path).group(1)
        # one file name misspells the county; county names in the CSVs use
        # spaces, file names use underscores
        county = county.replace("_", " ").replace("clairborne", "claiborne")
        # the county CSV spells it 'Jeff Davis' (as in the primary CSVs)
        county = county.replace("jefferson davis", "jeff davis")
        with open(path, newline="") as f:
            header = next(csv.reader(f))
            cols = {h.strip().lower(): i for i, h in enumerate(header)}
            if "candidate" not in cols or "votes" not in cols:
                print(f"  ! {path}: unrecognized header {header}",
                      file=sys.stderr)
                continue
            swapped = cols.get("county") == 0  # county-first layout
            for row in csv.reader(f):
                if len(row) <= cols["votes"]:
                    continue
                val = row[cols["votes"]].strip()
                if not val or not val.isdigit():
                    continue
                county_name = (row[cols["county"]].strip().lower()
                               if swapped else county)
                office, district = normalize_office(
                    row[cols["office"]], row[cols["district"]],
                    psc_by_county.get(county_name))
                party = PARTY_MAP.get(row[cols["party"]].strip().upper(),
                                      row[cols["party"]].strip().title())
                cand = name_key(row[cols["candidate"]])
                cand = NAME_ALIASES.get(cand, cand)
                key = (county_name, office, district, cand, party)
                if key in agg:
                    agg[key] += int(val)
                else:
                    agg[key] = int(val)
    return agg


def main():
    # which PSC / Transportation districts each county has, for files whose
    # district column is empty
    psc_by_county = {}
    with open(COUNTY_CSV, newline="") as f:
        for row in csv.DictReader(f):
            m = re.match(r"^(Public Service|Transportation) "
                         r"Commissioner-(\w+) District$", row["office"])
            if m:
                entry = psc_by_county.setdefault(row["county"].lower(), {})
                entry["PSC" if m.group(1) == "Public Service" else "TRANS"] \
                    = m.group(2)
    precinct = load_precinct(psc_by_county)
    print(f"precinct aggregation: {len(precinct)} (county, office, candidate)"
          f" keys")
    rows = []
    path = sys.argv[1] if len(sys.argv) > 1 else COUNTY_CSV
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            cand = name_key(row["candidate"])
            cand = NAME_ALIASES.get(cand, cand)
            office = row["office"].strip().lower()
            district = row["district"].strip()
            if district.isdigit():
                district = str(int(district))
            # the county CSV spells PSC/Transportation districts inside the
            # office name and keeps 'District Attorney NN' whole
            m = re.match(r"^(public service|transportation) "
                         r"commissioner-(\w+) district$", office)
            if m:
                office = f"{m.group(1)} commissioner-{m.group(2).lower()} district"
                district = ""
            elif re.match(r"^district attorney \d+$", office):
                district = ""
            rows.append((row["county"].lower(), office, district, cand,
                         row["party"], int(row["votes"]), row))
    ok = True
    checked = matched = 0
    for cl, office, district, cand, party, votes, raw in rows:
        pk = (cl, office, district, cand, party)
        if pk not in precinct:
            continue
        checked += 1
        if precinct[pk] == votes:
            matched += 1
        else:
            ok = False
            print(f"  ! {raw['county']} / {raw['candidate']} "
                  f"({raw['office']} {raw['district']}): parsed {votes} "
                  f"!= precinct sum {precinct[pk]}")
    csv_keys = {(cl, office, district, cand, party)
                for cl, office, district, cand, party, _, _ in rows}
    orphans = {k: v for k, v in precinct.items() if k not in csv_keys}
    # local offices aren't in the county CSV by design; only report orphans
    # for offices the county CSV carries
    csv_offices = {(office, district) for _, office, district, _, _ in
                   csv_keys}
    for (cl, office, district, cand, party), v in sorted(orphans.items()):
        # find county-CSV offices for this county with same district to spot
        # name variants
        if office.startswith(("district attorney", "public service",
                              "transportation")):
            matches = [o for (o, d) in csv_offices
                       if o.startswith(office.split("-")[0].split()[0].lower())]
        else:
            matches = [o for (o, d) in csv_offices if o == office]
        if not matches:
            continue  # genuinely local: no county-CSV counterpart expected
        ok = False
        print(f"  ! precinct key with no county-CSV counterpart: "
              f"{(cl, office, district, cand, party)} (sum {v})")
    print(f"checked {checked} of {len(rows)} county-CSV values "
          f"({len(rows) - checked} not covered by precinct files): "
          f"{matched} match" + (", 0 mismatches" if ok else ", MISMATCHES"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())