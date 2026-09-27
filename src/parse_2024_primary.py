"""Parse the PaddleOCR markdown of the 2024 primary statewide recap scans
(cache/2024-primary/paddle-{d,r}/) into 2024/20240312__ms__primary__county.csv.

Grid structure (counties as columns, 11 per page; the last grid page carries a
TOTAL column):
  - header row "Votes cast in the State of Mississippi on the 12th day of
    March 2024" followed by the county-name cells (rotated text)
  - office-section rows: "United States-President", "United States-Senate",
    "US House Of Rep 01-1st Congressional District", ...
  - candidate rows: name (+ merged party label or separate party cell), then
    one cell per county column; 'x'/'X' = not on ballot
Every candidate's county cells sum to the printed TOTAL column value; that
reconciliation gates each row.

Output office naming follows the repo's conventions (2024 general county CSV /
2019 primary county CSV): President, U.S. Senate, U.S. House + district.

Usage:
    uv run python parse_2024_primary.py            # parse + verify, write CSV
"""

import csv
import difflib
import html
import re
import unicodedata
from pathlib import Path

CACHE = Path("cache/2024-primary")
OUT = Path("2024/20240312__ms__primary__county.csv")

# printed TOTAL column values (read off the rendered last grid pages) -- the
# reconciliation gate for every row
PRINTED_TOTALS = {
    "D": {"President": {"Joseph R. Biden Jr.": 91053},
          "U.S. Senate": {"Ty Pinkins": 82264},
          "U.S. House 1": {"Dianne Dodson Black": 12147,
                           "Bronco Williams": 2138},
          "U.S. House 2": {"Bennie G. Thompson": 44295},
          "U.S. House 4": {"Craig Elliot Raybon": 9720}},
    "R": {"President": {"Ron DeSantis": 4042, "Nikki R. Haley": 13437,
                        "Vivek Ramaswamy": 1096, "Donald J. Trump": 229198},
          "U.S. Senate": {"Ghannon Burton": 61387, "Dan Eubanks": 34238,
                          "Roger F. Wicker": 152086},
          "U.S. House 1": {"Trent Kelly": 68842},
          "U.S. House 2": {"Ron Eller": 14991, "Andrew Scott Smith": 11493,
                           "Taylor Turcotte": 5675},
          "U.S. House 3": {"Michael Guest": 66559},
          "U.S. House 4": {"Carl Boyanton": 13432, "Mike Ezell": 52028,
                           "Michael McGill": 5493}},
}

OFFICE_MAP = {
    "united states president": ("President", ""),
    "united states senate": ("U.S. Senate", ""),
}
HOUSE_RE = re.compile(r"us house of rep\s*0?(\d+)", re.I)

# The statewide recap prints each House section header once (where the
# section STARTS) but repeats the current section's header on later pages;
# a section that spans a page break leaves its tail rows at the top of the
# next page under the PREVIOUS page's carried-over header. Michael Guest
# (MS-3) is the only such candidate: his row tops every R House page after
# the 03-3rd header's page, right above the reprinted 04-4th header, so the
# carried state pins him to district 4. The per-county PDFs and the 2024
# general county CSV both put him in district 3, so pin it here.
CANDIDATE_OFFICE_OVERRIDES = {
    "Michael Guest": ("U.S. House", "3"),
}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def page_table(md):
    """Parse one page's markdown table -> (headers, rows); rows are
    ('office', text) or ('cand', name, [value cells])."""
    rows = []
    headers = None
    header_pending = False
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", md, re.S):
        cells = []
        for attrs, body in re.findall(r"<td([^>]*)>(.*?)</td>", tr, re.S):
            m = re.search(r'colspan="?(\d+)', attrs)
            n = int(m.group(1)) if m else 1
            cells.extend([strip_tags(body)] + [""] * (n - 1))
        if not cells:
            continue
        first = cells[0]
        rest = cells[1:]
        low = norm(first)
        if low.startswith(("votes cast in the state of mississippi",
                           "votes cast in the county of")):
            while rest and not rest[0]:
                rest.pop(0)
            while rest and not rest[-1]:
                rest.pop()
            headers = rest
            header_pending = len(headers) <= 2
            continue
        if header_pending and len([c for c in cells if c]) >= 3 \
                and not any(c.replace(",", "").strip().isdigit() for c in cells):
            while cells and not cells[-1]:
                cells.pop()
            headers = cells
            header_pending = False
            continue
        header_pending = False
        if not low or low.startswith(("official recap", "names of counties",
                                      "names of election")):
            # the office label can sit in a NON-FIRST cell with an empty
            # leading cell (Madison R p5: <td></td><td>United States-Senate
            # </td><td colspan=11></td>) -- otherwise the section's rows
            # fall under the previous page's office
            for c in rest:
                clow = norm(c)
                if (HOUSE_RE.search(clow) or clow in OFFICE_MAP) and not any(
                        x.replace(",", "").strip().isdigit() for x in rest):
                    rows.append(("office", c))
                    break
            continue
        # office section row: a label with no NUMERIC cells (the spanning
        # cell can carry a stray party label, e.g. p007 R's
        # <td>United States-President</td><td colspan=12>Republican</td>)
        if (HOUSE_RE.search(low) or low in OFFICE_MAP) and not any(
                c.replace(",", "").strip().isdigit() for c in rest):
            rows.append(("office", first))
            continue
        # OCR can merge the office header with the FIRST candidate row into
        # one <tr>: <td>office</td>[<td></td>]<td>cand</td><td>party</td>
        # <td>v1</td>... -- split it back into an office row + candidate row
        if (HOUSE_RE.search(low) or low in OFFICE_MAP):
            name = vals = None
            for i, c in enumerate(rest):
                cs = c.strip()
                if not cs:
                    continue
                if cs.replace(",", "").isdigit() or norm(cs) in \
                        ("democrat", "republican"):
                    break
                name, vals = cs, rest[i + 1:]
                break
            if vals and norm(vals[0]).strip() in ("democrat", "republican"):
                vals = vals[1:]
            rows.append(("office", first))
            if name:
                rows.append(("cand", name, vals))
            continue
        # candidate row: strip a separate party-label cell
        vals = list(rest)
        if len(vals) >= 2 and not vals[0] \
                and norm(vals[1]).strip() in ("democrat", "republican"):
            vals.pop(0)
        if vals and norm(vals[0]).strip() in ("democrat", "republican"):
            vals.pop(0)
        m = re.match(r"^(.*?)(?:\s+(?:Democrat|Republican)\s*)$", first, re.I)
        name = (m.group(1) if m else first).strip()
        if not name:
            continue
        rows.append(("cand", name, vals))
    return headers, rows


def office_key(label):
    low = norm(label)
    if low in OFFICE_MAP:
        return OFFICE_MAP[low]
    m = HOUSE_RE.search(low)
    if m:
        return (f"U.S. House", str(int(m.group(1))))
    return (None, None)


def county_roster():
    """The 82 county names, from the 2024 general county CSV."""
    with open("2024/20241105__ms__general__county.csv", newline="") as f:
        return sorted({row["county"] for row in csv.DictReader(f)})


# PaddleOCR drops the Washington (10th) column's values on grid page 9 of the
# padded Democratic scan -- the header survives and Wayne's value slides into
# Washington's slot, leaving Wayne blank. Values read off the 250-dpi render;
# each reconciles the printed TOTAL column exactly. Keyed (party, page) ->
# {candidate: {county: value or 'X'}} -- fills the row's missing trailing
# cell(s), or patches a misread value.
CELL_FILLS = {
    ("D", 9): {
        "Joseph R. Biden Jr.": {"Washington": 2088},
        "Ty Pinkins": {"Washington": 1935},
        "Dianne Dodson Black": {"Washington": "X"},
        "Bronco Williams": {"Washington": "X"},
        "Bennie G. Thompson": {"Washington": 2109},
        "Craig Elliot Raybon": {"Washington": "X"},
    },
    # the unpadded Republican scan clips its LAST county column on every
    # grid page: the final digit(s) are cut off (or the whole cell is lost).
    # Every entry below was read off the 250-dpi renders
    # (cache/2024-primary/renders/r/) and reconciles the printed TOTAL.
    ("R", 3): {  # Claiborne
        "Ron DeSantis": {"Claiborne": 0}, "Nikki R. Haley": {"Claiborne": 6},
        "Vivek Ramaswamy": {"Claiborne": 0},
        "Donald J. Trump": {"Claiborne": 138},
        "Ghannon Burton": {"Claiborne": 22}, "Dan Eubanks": {"Claiborne": 13},
        "Roger F. Wicker": {"Claiborne": 110}, "Trent Kelly": {"Claiborne": "X"},
        "Ron Eller": {"Claiborne": 75},
        "Andrew Scott Smith": {"Claiborne": 28},
        "Taylor Turcotte": {"Claiborne": 29},
    },
    ("R", 4): {  # Grenada
        "Ron DeSantis": {"Grenada": 11}, "Nikki R. Haley": {"Grenada": 49},
        "Vivek Ramaswamy": {"Grenada": 4},
        "Donald J. Trump": {"Grenada": 1602},
        "Ghannon Burton": {"Grenada": 427}, "Dan Eubanks": {"Grenada": 217},
        "Roger F. Wicker": {"Grenada": 1016}, "Trent Kelly": {"Grenada": "X"},
    },
    ("R", 5): {  # Jefferson
        "Ron DeSantis": {"Jefferson": 1}, "Nikki R. Haley": {"Jefferson": 6},
        "Vivek Ramaswamy": {"Jefferson": 1},
        "Donald J. Trump": {"Jefferson": 120},
        "Ghannon Burton": {"Jefferson": 13}, "Dan Eubanks": {"Jefferson": 15},
        "Roger F. Wicker": {"Jefferson": 101},
        "Trent Kelly": {"Jefferson": "X"}, "Ron Eller": {"Jefferson": 51},
        "Andrew Scott Smith": {"Jefferson": 47},
        "Taylor Turcotte": {"Jefferson": 20},
    },
    ("R", 6): {  # Lowndes
        "Ron DeSantis": {"Lowndes": 65}, "Nikki R. Haley": {"Lowndes": 198},
        "Vivek Ramaswamy": {"Lowndes": 18},
        "Donald J. Trump": {"Lowndes": 3675},
        "Ghannon Burton": {"Lowndes": 1160}, "Dan Eubanks": {"Lowndes": 474},
        "Roger F. Wicker": {"Lowndes": 2326}, "Trent Kelly": {"Lowndes": 3850},
        "Ron Eller": {"Lowndes": "X"}, "Andrew Scott Smith": {"Lowndes": "X"},
        "Taylor Turcotte": {"Lowndes": "X"},
    },
    ("R", 7): {  # Pearl River
        "Ron DeSantis": {"Pearl River": 85}, "Nikki R. Haley": {"Pearl River": 226},
        "Vivek Ramaswamy": {"Pearl River": 33},
        "Donald J. Trump": {"Pearl River": 5427},
        "Ghannon Burton": {"Pearl River": 946},
        "Dan Eubanks": {"Pearl River": 1136},
        "Roger F. Wicker": {"Pearl River": 3623},
        "Trent Kelly": {"Pearl River": "X"}, "Ron Eller": {"Pearl River": "X"},
        "Andrew Scott Smith": {"Pearl River": "X"},
        "Taylor Turcotte": {"Pearl River": "X"},
    },
    ("R", 8): {  # Stone
        "Ron DeSantis": {"Stone": 37}, "Nikki R. Haley": {"Stone": 137},
        "Vivek Ramaswamy": {"Stone": 13}, "Donald J. Trump": {"Stone": 2369},
        "Ghannon Burton": {"Stone": 302}, "Dan Eubanks": {"Stone": 416},
        "Roger F. Wicker": {"Stone": 1845}, "Trent Kelly": {"Stone": "X"},
        "Ron Eller": {"Stone": "X"}, "Andrew Scott Smith": {"Stone": "X"},
        "Taylor Turcotte": {"Stone": "X"},
    },
    ("R", 9): {  # Wayne
        "Ron DeSantis": {"Wayne": 26}, "Nikki R. Haley": {"Wayne": 65},
        "Vivek Ramaswamy": {"Wayne": 7}, "Donald J. Trump": {"Wayne": 2225},
        "Ghannon Burton": {"Wayne": 304}, "Dan Eubanks": {"Wayne": 359},
        "Roger F. Wicker": {"Wayne": 1646}, "Trent Kelly": {"Wayne": "X"},
        "Ron Eller": {"Wayne": "X"}, "Andrew Scott Smith": {"Wayne": "X"},
        "Taylor Turcotte": {"Wayne": "X"},
    },
    ("R", 15): {  # Pearl River (HD3/HD4 pass)
        "Michael Guest": {"Pearl River": "X"},
        "Carl Boyanton": {"Pearl River": 1152}, "Mike Ezell": {"Pearl River": 4261},
        "Michael McGill": {"Pearl River": 332},
    },
    ("R", 16): {  # Stone
        "Michael Guest": {"Stone": "X"}, "Carl Boyanton": {"Stone": 482},
        "Mike Ezell": {"Stone": 1887}, "Michael McGill": {"Stone": 196},
    },
    ("R", 17): {  # Wayne
        "Michael Guest": {"Wayne": "X"}, "Carl Boyanton": {"Wayne": 344},
        "Mike Ezell": {"Wayne": 1870}, "Michael McGill": {"Wayne": 96},
    },
}

# pages where a dropped cell sits BEFORE the last county and the tail value
# slides left into its slot (D p9); on the R pages the drop IS the last
# county, so zipping headers to the short row is already correct
SHIFT_REPAIR_PAGES = {("D", 9)}


all_rows = []


def main():
    roster = county_roster()
    for party in ("D", "R"):
        # the padded run is preferred (the unpadded scans clip their last
        # county column), but the padded R read came back structurally
        # garbled (office headers absorbed the first candidate row of every
        # section), so the R party uses the cleaner unpadded read and takes
        # its edge-column losses as render-verified fills instead
        prefer = "paddle_pad" if party == "D" else "paddle"
        cache = CACHE / f"{prefer}-{party.lower()}"
        page_files = sorted(cache.glob("p*.md"))
        if not page_files:
            raise SystemExit(f"no markdown under {cache}")
        # collect {(office, district): {candidate: {county: votes}}}
        data = {}
        totals = {}
        warnings = []
        headers = None
        office = None
        for pf in page_files:
            page = int(re.search(r"p(\d+)\.md", pf.name).group(1))
            hs, rows = page_table(pf.read_text())
            if hs:
                # trim trailing padding cells; snap misread county headers to
                # the roster (e.g. 'Grenade'->'Grenada', 'Okttibeba'->'Oktibbeha')
                while hs and not hs[-1].strip():
                    hs.pop()
                for i, h in enumerate(hs):
                    if not h.strip() or h in roster \
                            or h.strip().upper() == "TOTAL":
                        continue
                    close = difflib.get_close_matches(h, roster, n=1, cutoff=0.7)
                    if close:
                        warnings.append(f"p{page}: county header {h!r} snapped "
                                        f"to {close[0]!r}")
                        hs[i] = close[0]
                    else:
                        warnings.append(f"p{page}: county header {h!r} matches "
                                        f"no roster county; kept as is")
                headers = hs
            if not headers:
                warnings.append(f"p{page}: no headers parsed; skipped")
                continue
            fills = CELL_FILLS.get((party, page), {})
            for row in rows:
                if row[0] == "office":
                    office = row[1]
                    continue
                _, cand, vals = row
                if office is None:
                    warnings.append(f"p{page}: candidate {cand!r} before any "
                                    f"office row; skipped")
                    continue
                o, d = CANDIDATE_OFFICE_OVERRIDES.get(cand) \
                    or office_key(office)
                if o is None:
                    warnings.append(f"p{page}: unknown office {office!r}; "
                                    f"{cand!r} skipped")
                    continue
                vals = list(vals)
                while vals and not vals[-1]:
                    vals.pop()
                # a dropped value cell shifts the tail left; on the D p9
                # fills page the drop is known to sit just before the LAST
                # county, whose value survives (render-verified) -- reinsert
                # the blank
                if (party, page) in SHIFT_REPAIR_PAGES \
                        and len(vals) == len(headers) - 1:
                    warnings.append(f"p{page}: {cand!r}: reinserting dropped "
                                    f"cell before the last county")
                    vals = vals[:-1] + [""] + vals[-1:]
                if len(vals) != len(headers):
                    warnings.append(f"p{page}: {cand!r} {len(vals)} cells vs "
                                    f"{len(headers)} headers")
                for h, v in zip(headers, vals):
                    v = v.strip()
                    county = h.strip()
                    if not county:
                        continue
                    if county.upper() == "TOTAL":
                        if v.isdigit():
                            totals[(o, d, cand)] = int(v)
                        continue
                    if v.upper() == "X":
                        continue
                    if not v.isdigit():
                        warnings.append(f"p{page}: {cand!r} {county!r}: "
                                        f"non-numeric {v!r}")
                        continue
                    data.setdefault((o, d), {}) \
                        .setdefault(cand, {})[county] = int(v)
                # render-verified fills for dropped/misread cells
                fill = fills.get(cand)
                if fill:
                    for county, v in fill.items():
                        key = (o, d)
                        if v == "X":
                            data.get(key, {}).get(cand, {}).pop(county, None)
                        else:
                            data.setdefault(key, {}).setdefault(cand, {})[county] = v
                        old = data.get(key, {}).get(cand, {}).get(county)
                        warnings.append(f"p{page}: {cand!r} {county!r} filled "
                                        f"with {v} (render-verified)"
                                        + (f", was {old}" if old is not None and old != v else ""))
        # verify: cell sums vs printed TOTALs
        print(f"=== party {party} ===")
        seen = {c for cands in data.values() for cells in cands.values()
                for c in cells}
        unknown = seen - set(roster)
        missing = set(roster) - seen
        if unknown:
            warnings.append(f"counties not on the roster: {sorted(unknown)}")
        if missing:
            warnings.append(f"roster counties never seen: {sorted(missing)}")
        bad = 0
        for (o, d), cands in sorted(data.items()):
            for cand, cells in sorted(cands.items()):
                tot = totals.get((o, d, cand))
                printed = PRINTED_TOTALS.get(party, {}).get(f"{o} {d}", {}) \
                    .get(cand)
                s = sum(cells.values())
                ok = (tot is None or s == tot) and \
                     (printed is None or s == printed)
                if not ok:
                    bad += 1
                print(f"  {'OK ' if ok else '!! '}{o} {d} {cand}: "
                      f"{len(cells)} counties, sum {s}, "
                      f"printed TOTAL {tot if tot is not None else '-'}"
                      f"{'' if printed is None else f' (expected {printed})'}")
        for w in warnings:
            print(f"  ! {w}")
        print(f"  {bad} unreconciled candidates")
        if bad or unknown or missing:
            raise SystemExit(f"party {party}: refusing to write the CSV with "
                             f"unreconciled data")
        # emit the county CSV rows for this party
        party_code = "DEM" if party == "D" else "REP"
        out_rows = []
        for (o, d), cands in sorted(data.items()):
            for cand, cells in sorted(cands.items()):
                for county, votes in sorted(cells.items()):
                    out_rows.append((county, o, d, party_code, cand, votes))
        all_rows.extend(out_rows)
    _write()


def _write():
    all_rows.sort(key=lambda r: (r[0], r[1], r[2], r[4]))
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["county", "office", "district", "party", "candidate",
                    "votes"])
        w.writerows(all_rows)
    print(f"wrote {len(all_rows)} rows to {OUT}")


if __name__ == "__main__":
    main()