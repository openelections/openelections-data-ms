"""Build a repo-format 2019 primary precinct CSV from the extractor's raw CSVs.

Merges BOTH parties' raw CSVs (cache/2019-<county>-d/ and -r/) into one
`2019/counties/20190806__ms__primary__<county>__precinct.csv`, drops phantom
UNKNOWN-office rows and TOTAL rows, normalizes precinct names, and writes the
CRLF `candidate,office,district,party,county,precinct,votes` layout ordered
precinct-major (precinct, then ballot office order, R before D) to match the
repo's existing county files. Prints a per-office sum check against the county
CSVs (crosstabs) for every candidate of every party it processed.

Usage:
    uv run python build_2019_precinct_from_raw.py <County>
"""
import csv, re, sys, unicodedata
from collections import Counter, defaultdict

COUNTY = sys.argv[1]
COUNTY_CSVS = {"D": "2019/20190806__ms__democratic__primary__county.csv",
               "R": "2019/20190806__ms__republican__primary__county.csv"}
OUT = f"2019/counties/20190806__ms__primary__{COUNTY.lower()}__precinct.csv"

BASE_OFFICE_RE = re.compile(
    r"^(governor|lieutenant governor|lt governor|secretary of state|"
    r"attorney general|state auditor|state treasurer|"
    r"commissioner of agriculture|commissioner of insurance|"
    r"public service commissioner|transportation commissioner|"
    r"district attorney|state senate|state house)")


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


def base_office(s):
    """Core office name ('attorney general', 'state senate', ...) or None."""
    s = re.sub(r"\s+", " ", norm(s)).strip()
    s = re.sub(r"^state of mississippi\s+", "", s)
    m = BASE_OFFICE_RE.match(s)
    return m.group(1) if m else None


def clean_precinct(s):
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*\(\d+\)$", "", s)              # trailing "(3)" box numbers
    s = re.sub(r"^0+(\d)", r"\1", s)               # strip leading zeros
    return s.strip(" -")


# rosters: candidate -> (office, district, party); office order from the
# county CSVs (ballot order; DEM first, then any REP-only offices appended)
roster = {}
office_order = {}
for party in ("R", "D"):
    with open(COUNTY_CSVS[party], newline="") as f:
        for row in csv.DictReader(f):
            if row["county"] != COUNTY:
                continue
            roster[row["candidate"]] = (row["office"], row["district"], party)
            key = (row["office"], row["district"])
            office_order.setdefault(key, len(office_order))
if not roster:
    sys.exit(f"no {COUNTY} rows in the county CSVs")

rows_out = []
seen = set()
for party in ("R", "D"):
    raw = f"cache/2019-{COUNTY.lower()}-{party.lower()}/" \
          f"{COUNTY.lower()}_{party.lower()}_precinct_raw.csv"
    try:
        f = open(raw, newline="")
    except FileNotFoundError:
        if party == "D":
            print(f"(no DEM raw at {raw}; building {party} rows only)")
        continue
    with f:
        for r in csv.DictReader(f):
            office_raw = r["office_raw"]
            if "UNKNOWN" in office_raw.upper():
                continue
            cand = r["candidate"].strip()
            if cand not in roster:
                continue                        # local-office rows etc.
            office, district, cand_party = roster[cand]
            # gate: the row's own office label must be the same office the
            # roster says this candidate ran for (catches local-office rows
            # that share a statewide candidate's name)
            raw_base = base_office(office_raw)
            if raw_base is None or raw_base != base_office(office):
                print(f"  ! dropped ({party}; office_raw {office_raw!r} != "
                      f"roster {office!r}): {cand} {r['precinct']} {r['votes']}")
                continue
            votes = r["votes"].strip()
            if votes.upper() in ("X", ""):
                votes = "0"
            if not votes.replace(",", "").strip().isdigit():
                print(f"  ! bad votes {r}")
                continue
            votes = str(int(votes.replace(",", "")))
            prec = clean_precinct(r["precinct"])
            if prec.upper() == "TOTAL":
                continue
            key = (prec, office, district, cand)
            if key in seen:
                print(f"  ! duplicate row {key} (page {r['page']}); keeping first")
                continue
            seen.add(key)
            rows_out.append({
                "candidate": cand, "office": office, "district": district,
                "party": cand_party, "county": COUNTY,
                "precinct": prec, "votes": votes,
            })

# unify case variants of the same precinct name ('Mccall' vs 'McCall' from
# different pages) -- keep the spelling used by the most rows, which is also
# the one the county's existing files use
spell = defaultdict(Counter)
for r in rows_out:
    spell[r["precinct"].casefold()][r["precinct"]] += 1
canon = {k: c.most_common(1)[0][0] for k, c in spell.items()}
for r in rows_out:
    r["precinct"] = canon[r["precinct"].casefold()]

# order: precinct, then ballot office order (R before D within an office)
rows_out.sort(key=lambda r: (r["precinct"],
                             office_order[(r["office"], r["district"])],
                             0 if r["party"] == "R" else 1))

with open(OUT, "w", newline="") as f:
    w = csv.writer(f, lineterminator="\r\n")
    w.writerow(["candidate", "office", "district", "party", "county",
                "precinct", "votes"])
    w.writerows([[r["candidate"], r["office"], r["district"], r["party"],
                  r["county"], r["precinct"], r["votes"]] for r in rows_out])
print(f"wrote {len(rows_out)} rows to {OUT}")

# sum check vs county CSVs
sums = defaultdict(int)
for r in rows_out:
    sums[(r["party"], r["office"], r["district"], r["candidate"])] += int(r["votes"])
bad = ok = 0
for cand, (office, district, party) in roster.items():
    exp = None
    with open(COUNTY_CSVS[party], newline="") as f:
        for row in csv.DictReader(f):
            if row["county"] == COUNTY and row["candidate"] == cand:
                exp = int(row["votes"])
                break
    got = sums.get((party, office, district, cand), 0)
    if exp == got:
        ok += 1
    else:
        bad += 1
        print(f"  ! {cand} ({party} {office} {district}): precinct file {got} "
              f"vs crosstab {exp}")
print(f"sum check vs crosstab: {ok} exact, {bad} differ")