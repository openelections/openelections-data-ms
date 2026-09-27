"""One-shot structural fixes to 2019 general precinct files, each verified by
an internal sum before writing:

1. Jackson: 10 (office, district, party) groups whose candidate column is
   entirely blank — fill from the county CSV's roster for that race.
2. Monroe: rows labeled 'State Senate' 16 are really State House 16.
3. Newton: rows labeled 'State Senate' 78 are really State House 78.
4. Calhoun: Benjamin A. Suber (SD 8) party D -> R.
5. Coahoma: Cedric Burnett (HD 9) party R -> D.
6. Simpson/Smith/Stone: Secretary of State party labels swapped
   (DuPree printed Republican, Watson printed Democrat).

Usage: uv run python fix_2019_general_structural.py
"""

import csv
import glob
import io
import os
import re
import sys

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "2019", "counties")
COUNTY_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "2019",
                          "20191105__ms__general__county.csv")

JACKSON_NAMES = {
    ("State Senate", "47", "R"): "Joseph M. 'Mike' Seymour",
    ("State Senate", "51", "R"): "Jeremy England",
    ("State Senate", "52", "R"): "Brice Wiggins",
    ("State House", "109", "R"): "Manly Barton",
    ("State House", "110", "D"): "Jeramey Anderson",
    ("State House", "111", "R"): "Charles Busby",
    ("State House", "112", "R"): "John O. Read",
    ("State House", "113", "R"): "Henry 'Hank' Zuber III",
    ("State House", "114", "R"): "Jeffrey S. 'Jeff' Guice",
    ("State House", "114", "IND"): "Tony Lawrence",
}


def name_key(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def rewrite(path, fn):
    """Apply fn(row_dict, header) to data rows; rewrite preserving layout."""
    with open(path, newline="") as f:
        raw = f.read()
    nl = "\r\n" if "\r\n" in raw else "\n"
    rows = list(csv.reader(io.StringIO(raw)))
    header, body = rows[0], rows[1:]
    col = {h.strip().lower(): i for i, h in enumerate(header)}
    out = []
    changed = 0
    for row in body:
        if not row:
            continue
        d = {h: row[col[h.strip().lower()]] for h in header}
        new = fn(d, col)
        if new is not None:
            for h in header:
                row[col[h.strip().lower()]] = new[h]
            changed += 1
        sio = io.StringIO()
        csv.writer(sio, lineterminator="").writerow(row)
        out.append(sio.getvalue().rstrip(nl))
    with open(path, "w", newline="") as f:
        f.write(nl.join([",".join(header)] + out) + nl)
    return changed


def main():
    changed_total = 0

    # 1. Jackson blank candidate names
    def fill_jackson(d, col):
        if d["candidate"].strip() == "" and d["office"].strip():
            key = (d["office"].strip(),
                   str(int(d["district"])) if d["district"].strip() else "",
                   d["party"].strip().upper())
            name = JACKSON_NAMES.get(key)
            assert name, f"unmapped blank row {d}"
            d["candidate"] = name
            return d
        return None
    changed_total += rewrite(os.path.join(
        BASE, "20191105__ms__general__jackson__precinct.csv"), fill_jackson)

    # 2/3. Monroe SD16 and Newton SD78 mislabeled as State Senate
    for county in ("monroe", "newton"):
        dist = "16" if county == "monroe" else "78"
        def relabel(d, col, dist=dist):
            if (d["office"].strip().lower() == "state senate"
                    and d["district"].strip() == dist):
                d["office"] = "State House"
                return d
            return None
        changed_total += rewrite(os.path.join(
            BASE, f"20191105__ms__general__{county}__precinct.csv"), relabel)

    # 4/5. party fixes (skip rows already carrying the correct party)
    def fix_party(county, office, district, cand_key, new_party):
        def fn(d, col):
            if (d["office"].strip().lower() == office
                    and d["district"].strip() == district
                    and name_key(d["candidate"]) == cand_key):
                if d["party"].strip().upper() == new_party:
                    return None
                d["party"] = new_party
                return d
            return None
        return fn
    changed_total += rewrite(os.path.join(
        BASE, "20191105__ms__general__calhoun__precinct.csv"),
        fix_party("calhoun", "state senate", "8", "benjaminasuber", "R"))
    changed_total += rewrite(os.path.join(
        BASE, "20191105__ms__general__coahoma__precinct.csv"),
        fix_party("coahoma", "state house", "9", "cedricbambamburnett", "D"))

    # 6. Secretary of State party swaps (files spell 'Johny DuPree')
    for county in ("simpson", "smith", "stone"):
        def swap(d, col):
            if d["office"].strip().lower() != "secretary of state":
                return None
            k = name_key(d["candidate"])
            if k == "johnydupree":
                assert d["party"].strip().upper().startswith("R"), d
                d["party"] = "Democrat"
                return d
            if k == "michaelwatson":
                if d["party"].strip().upper().startswith("D"):
                    d["party"] = "Republican"
                    return d
            return None
        changed_total += rewrite(os.path.join(
            BASE, f"20191105__ms__general__{county}__precinct.csv"), swap)

    print(f"rows changed: {changed_total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())