"""Arbitrate 2019 general county-CSV vs precinct-file discrepancies against
the per-county general recap scans (PaddleOCR markdown in
cache/2019-general-<county>/paddle/, fetched by extract_2019_general_paddle.py).

For each county this compares, race by race and precinct by precinct:
  * the recap's printed per-precinct cells (and printed TOTAL, where present),
  * the precinct file's rows,
  * the county-CSV value,

and proposes fixes to the precinct file where a printed cell equals the file's
deficit (printed TOTAL == county-CSV value pins the CSV side).

Usage:
    uv run python arbitrate_2019_general.py                # report, all counties
    uv run python arbitrate_2019_general.py Hinds Bolivar  # specific counties
    uv run python arbitrate_2019_general.py --fix Hinds    # apply proposed fixes
"""

import csv
import difflib
import glob
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from crosscheck_2019_general import (COUNTIES_DIR, COUNTY_CSV, NAME_ALIASES,
                                     PARTY_MAP, name_key, normalize_office)

MD_CACHE = Path(__file__).resolve().parent.parent / "cache"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"\s+", " ", s).strip().lower()


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def parse_int(v):
    v = (v or "").replace(",", "").replace("\n", "").strip()
    return int(v) if v.isdigit() else None


PARTIES = ("democrat", "republican", "constitution", "independent",
           "libertarian")


LABEL_RE = re.compile(
    r"state of mississippi|state senate|state house|district attorney|"
    r"commissioner|supervisor|constable|justice court|election commissioner|"
    r"school district|chancery|circuit clerk|coroner|sheriff|tax assessor")


def parse_page(md):
    """One OCR page -> list of sections; each section is a dict with
    'label', 'precincts' (header cells) and 'rows' [(name, party, [vals])]."""
    md = md.replace("\\n", " ")
    sections = []
    headers = None
    cur = None
    orphans = []   # candidate rows read before the page's first label row
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", md, re.S):
        cells = []
        for attrs, body in re.findall(r"<td([^>]*)>(.*?)</td>", tr, re.S):
            m = re.search(r'colspan="?(\d+)', attrs)
            n = int(m.group(1)) if m else 1
            cells.extend([strip_tags(body)] + [""] * (n - 1))
        if not cells:
            continue
        first, rest = cells[0], cells[1:]
        low = norm(first)
        # 'Voles cast' (OCR) and other misreads of the lead header cell
        if "cast in the county" in low or (
                low.startswith("names of election") or "nations of election"
                in low or "of election" in low and "prec" in low):
            hs = rest
            while hs and not hs[-1].strip():
                hs.pop()
            headers = hs
            if cur:
                cur["precincts"] = hs
            continue
        # section-label rows: OCR sometimes puts the label in a later cell
        # (p009 of Bolivar: ['', 'State Senate 12-District 12', ...]) —
        # accept any row with exactly one non-empty cell that looks like an
        # office label (the 'Names of Election Precincts' header is excluded
        # by the keyword gate)
        nonempty = [c for c in cells if c.strip()]
        if len(nonempty) == 1 and LABEL_RE.search(norm(nonempty[0])) \
                and "cast in the county" not in low:
            cur = {"label": re.sub(r"\s+", " ", nonempty[0].strip()),
                   "precincts": headers, "rows": list(orphans)}
            orphans = []
            sections.append(cur)
            continue
        if not any(c.strip() for c in rest):
            if low:
                cur = {"label": re.sub(r"\s+", " ", first.strip()), "precincts":
                       headers, "rows": list(orphans)}
                orphans = []
                sections.append(cur)
            continue
        # candidate row: "Name Party" + value cells
        name = first
        party = ""
        vals = list(rest)
        if not first.strip() and vals and not parse_int(vals[0]) \
                and not LABEL_RE.search(norm(vals[0])) \
                and any(c.strip() for c in vals):
            # OCR split the lead cell: ['', 'Tom Weathersby', 'Republican',
            # values...] — the name (and sometimes the party) are lead cells,
            # not values
            name = vals.pop(0)
            if vals and norm(vals[0]) in PARTIES:
                party = vals.pop(0)
        m = re.match(r"^(.*?)\s+(Democrat|Republican|Constitution|"
                     r"Independent|Libertarian)\s*$", name.strip(), re.I)
        if m:
            name, party = m.group(1).strip(), m.group(2)
        # 4th element: True when the row was buffered as an orphan (read
        # before its section label) — load_ocr re-resolves those rows to
        # their real race via the county-CSV roster, since a first-row-of-
        # page orphan may continue the *previous* page's section
        row = (re.sub(r"\s+", " ", name.strip()), party, vals, False)
        if cur is not None:
            cur["rows"].append(row)
        elif headers is not None:
            orphans.append(row)
    return sections


def section_key(label):
    """OCR section label -> county-CSV (office, district), or None."""
    low = norm(label)
    low = re.sub(r"^state of mississippi[- ]*", "", low)
    m = re.match(r"state senate (\d+)", low)
    if m:
        return ("state senate", str(int(m.group(1))))
    m = re.match(r"state house(?: of rep(?:resentative)?s?)?\s*(\d+)", low)
    if m:
        return ("state house", str(int(m.group(1))))
    m = re.match(r"district attorney\s*(\d+)", low)
    if m:
        return (f"district attorney {int(m.group(1)):02d}", "")
    m = re.match(r"(public service|transportation) commissioner[-\s]+"
                 r"(central|northern|southern)", low)
    if m:
        # all-lowercase district word, matching load_county_csv and
        # normalize_office
        return (f"{m.group(1)} commissioner-{m.group(2)} district", "")
    for frag, office in [
            ("governor", "governor"),
            ("lieutenant governor", "lieutenant governor"),
            ("secretary of state", "secretary of state"),
            ("attorney general", "attorney general"),
            ("state auditor", "state auditor"),
            ("state treasurer", "state treasurer"),
            ("commissioner of agriculture", "commissioner of agriculture & commerce"),
            ("commissioner of insurance", "commissioner of insurance")]:
        if frag in low:
            if frag == "governor" and "lieutenant" in low:
                continue
            return (office, "")
    return None


def prec_key(s):
    """Normalized precinct name for file<->OCR matching."""
    s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
    s = re.sub(r"\bprecinct\b", " ", s)
    s = re.sub(r"^dist(RICT)?\.? ", "", s)
    return re.sub(r"\s+", " ", s).strip()


def load_county_csv():
    psc = {}
    rows = []
    with open(COUNTY_CSV, newline="") as f:
        for row in csv.DictReader(f):
            m = re.match(r"^(Public Service|Transportation) "
                         r"Commissioner-(\w+) District$", row["office"])
            if m:
                entry = psc.setdefault(row["county"].lower(), {})
                entry["PSC" if m.group(1) == "Public Service" else "TRANS"] \
                    = m.group(2)
            office = row["office"].strip().lower()
            district = row["district"].strip()
            if district.isdigit():
                district = str(int(district))
            m = re.match(r"^(public service|transportation) "
                         r"commissioner-(\w+) district$", office)
            if m:
                office = f"{m.group(1)} commissioner-{m.group(2).lower()} district"
                district = ""
            elif re.match(r"^district attorney \d+$", office):
                district = ""
            rows.append((row["county"].lower(), office, district,
                         name_key(row["candidate"]), row["party"],
                         int(row["votes"]), row))
    return rows, psc


def load_precinct_cells(county, psc):
    """One county's precinct file -> {(office, district, cand, party):
    {prec_key: votes}}, the path, a sample raw row per key (for spelling when
    appending), and {prec_key: raw precinct name} across all rows."""
    fn = glob.glob(os.path.join(COUNTIES_DIR,
                   f"20191105__ms__general__{county.replace(' ', '_')}"
                   f"__precinct.csv"))[0]
    with open(fn, newline="") as f:
        header = next(csv.reader(f))
    col = {h.strip().lower(): i for i, h in enumerate(header)}
    swapped = col.get("county") == 0
    cells = {}
    samples = {}
    prec_names = {}
    with open(fn, newline="") as f:
        for row in csv.reader(f):
            if len(row) <= col["votes"]:
                continue
            val = row[col["votes"]].strip()
            if not val.isdigit():
                continue
            prec = prec_key(row[col["precinct"]])
            prec_names.setdefault(prec, row[col["precinct"]])
            office, district = normalize_office(
                row[col["office"]], row[col["district"]], psc.get(county))
            party = PARTY_MAP.get(row[col["party"]].strip().upper(),
                                  row[col["party"]].strip().title())
            cand = name_key(row[col["candidate"]])
            cand = NAME_ALIASES.get(cand, cand)
            k = (office, district, cand, party)
            cells.setdefault(k, {})[prec] = int(val)
            samples.setdefault(k, row)
    return cells, fn, samples, prec_names


def load_roster(county):
    """{name_key: (office, district)} for one county from the county CSV —
    a candidate runs for only one office per county, so this resolves OCR
    rows whose section label was lost (first rows of a page that continue
    the previous page's section)."""
    roster = {}
    with open(COUNTY_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["county"].lower() != county.lower():
                continue
            office = row["office"].strip().lower()
            district = row["district"].strip()
            if district.isdigit():
                district = str(int(district))
            m = re.match(r"^(public service|transportation) "
                         r"commissioner-(\w+) district$", office)
            if m:
                office = f"{m.group(1)} commissioner-{m.group(2).lower()} district"
                district = ""
            elif re.match(r"^district attorney \d+$", office):
                district = ""
            roster.setdefault(name_key(row["candidate"]), (office, district))
    return roster


def load_ocr(county):
    """All OCR pages for a county -> {(office, district): merged race}, where
    a merged race has 'label', 'precincts' (all header cells seen),
    'total' (printed TOTAL, when a header named TOTAL carries a value) and
    'rows' {cand_key: (party, {prec: value})}.

    Races are split across pages by the recap sheets; values are aligned to
    headers positionally within each page's table (the name/party cells span
    the same number of header cells as the page's 'votes cast' lead cell, so
    no cell needs popping)."""
    slug = county.lower().replace(" ", "_")
    md_dir = MD_CACHE / f"2019-general-{slug}" / "paddle"
    roster = load_roster(county)
    races = {}
    for path in sorted(glob.glob(str(md_dir / "p*.md"))):
        for sec in parse_page(open(path).read()):
            key = section_key(sec["label"])
            if key is None:
                continue
            r = races.setdefault(key, {"label": sec["label"],
                                       "precincts": set(), "total": None,
                                       "rows": {}})
            for h in sec["precincts"]:
                if norm(h) not in ("total", "totals") and prec_key(h):
                    r["precincts"].add(prec_key(h))
            for name, party, vals, is_orphan in sec["rows"]:
                # orphan rows were read before their label; the label may
                # belong to the section that *follows* it while the row
                # continues the previous page's section — resolve the row's
                # real race from the county-CSV roster
                rr = r
                if is_orphan:
                    ck0 = name_key(name)
                    ck0 = NAME_ALIASES.get(ck0, ck0)
                    rkey = roster.get(ck0)
                    if rkey is None:
                        c0 = match_candidate(ck0, list(roster))
                        if c0:
                            rkey = roster[c0]
                    if rkey is not None and rkey != key:
                        rr = races.setdefault(
                            rkey, {"label": f"{rkey[0]} {rkey[1]}".strip(),
                                   "precincts": set(), "total": None,
                                   "rows": {}})
                        for h in sec["precincts"]:
                            if norm(h) not in ("total", "totals") and prec_key(h):
                                rr["precincts"].add(prec_key(h))
                cells = {}
                row_total = None
                # pages whose lead header cell carries no colspan emit the
                # party as a separate cell before the values; drop it
                if vals and norm(vals[0]) in PARTIES:
                    vals = vals[1:]
                named = [h for h in sec["precincts"] if prec_key(h)
                         and norm(h) not in ("total", "totals")]
                has_total = any(norm(h) in ("total", "totals")
                                for h in sec["precincts"])
                nums = [parse_int(v) for v in vals]
                n_nums = sum(n is not None for n in nums)
                # Alignment: order-based (numeric cells map in order to the
                # named headers) when the counts line up — that survives
                # phantom empty header cells; strict positional otherwise,
                # which keeps 'x' (not-on-ballot) cells aligned. The count
                # guard also refuses order-based alignment when a value cell
                # went missing (a printed 0 read as blank), where positional
                # is the correct reading.
                if n_nums == len(named) or (has_total
                                            and n_nums == len(named) + 1):
                    vn = [n for n in nums if n is not None]
                    for h, v in zip(named, vn):
                        cells[prec_key(h)] = v
                    if len(vn) == len(named) + 1:
                        row_total = vn[-1]
                else:
                    # positional: vals are pure value cells (name/party are
                    # always popped) — align them to the named headers in
                    # order, skipping empty lead cells; a TOTAL header right
                    # after the named ones carries the row total
                    for i, v in enumerate(vals):
                        iv = parse_int(v)
                        if iv is None:
                            continue
                        if i < len(named):
                            cells[prec_key(named[i])] = iv
                        elif i == len(named) and has_total:
                            if row_total is None:
                                row_total = iv
                ck = name_key(name)
                ck = NAME_ALIASES.get(ck, ck)
                party = party.strip().title()
                # OCR name/party variants (p006 read 'William E. Godfrey' as
                # 'William F. Godfrey  Democrat'); fold on name closeness
                match = ck
                if match not in rr["rows"]:
                    for k2 in rr["rows"]:
                        if difflib.SequenceMatcher(None, ck, k2).ratio() > 0.8:
                            match = k2
                            break
                if match in rr["rows"]:
                    row = rr["rows"][match]
                    row["cells"].update(cells)
                    if row["total"] is None:
                        row["total"] = row_total
                    if party and not row["party"]:
                        row["party"] = party
                else:
                    rr["rows"][match] = {"party": party, "cells": cells,
                                         "total": row_total}
    return races


def match_precinct(fprec, pkeys):
    if fprec in pkeys:
        return fprec
    cands = difflib.get_close_matches(fprec, pkeys, n=1, cutoff=0.8)
    if cands:
        return cands[0]
    # looser fallback (OCR header misreads like 'South Centith' for 'South
    # Corinth'): same first word and >= 0.7 overall
    first = fprec.split()[0] if fprec.split() else ""
    same_first = [k for k in pkeys if k.split()[:1] == [first]]
    cands = difflib.get_close_matches(fprec, same_first, n=1, cutoff=0.7)
    if cands:
        return cands[0]
    # last resort: scrambled OCR names ('Spainiovie' for 'Souinlovie')
    cands = difflib.get_close_matches(fprec, pkeys, n=1, cutoff=0.7)
    return cands[0] if cands else None


def match_candidate(ckey, names):
    if ckey in names:
        return ckey
    close = difflib.get_close_matches(ckey, list(names), n=1, cutoff=0.8)
    return close[0] if close else None


def main():
    fix = "--fix" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--fix"]
    csv_rows, psc = load_county_csv()
    counties = sorted({r[0] for r in csv_rows})
    if args:
        counties = [c.lower().replace("_", " ") for c in args]
    mismatches = 0
    fixes = []      # (fn, pk, fprec, fval, pval) cell corrections
    appends = []    # (fn, pk, {prec_key: printed value}) missing rows
    deletes = []    # (fn, pk, fprec, fval) spurious 'x' rows to zero out
    ctx = {}        # fn -> (psc districts, sample rows, precinct names)
    for county in counties:
        races = load_ocr(county)
        if not races:
            print(f"== {county}: no OCR yet, skipping")
            continue
        cells, fn, samples, prec_names = load_precinct_cells(county, psc)
        ctx[fn] = (psc.get(county, {}), samples, prec_names)
        # fold OCR precinct-name variants ("Foster Mound" for "Foster
        # Mount") into the file's spellings
        file_precs = {p for fc in cells.values() for p in fc}
        for r in races.values():
            r["precincts"] = {match_precinct(k, file_precs) or k
                              for k in r["precincts"]}
            for row in r["rows"].values():
                row["cells"] = {match_precinct(k, file_precs) or k: v
                                for k, v in row["cells"].items()}
        county_rows = [r for r in csv_rows if r[0] == county]
        n_cands = sum(len(r["rows"]) for r in races.values())
        print(f"== {county}: {len(races)} OCR races, {n_cands} candidate rows")
        for cl, office, district, cand, party, votes, raw in county_rows:
            pk = (office, district, cand, party)
            if pk not in cells:
                # whole race absent from the file (the 2020-vintage files
                # omit PSC/Transportation Commissioner and District Attorney
                # races in many counties) — propose adding every printed
                # precinct when the recap reconciles to the county CSV
                race = races.get((office, district))
                if race:
                    c = match_candidate(cand, list(race["rows"]))
                    if c is not None:
                        prow = race["rows"][c]
                        if prow["total"] == votes \
                                and sum(prow["cells"].values()) == votes:
                            appends.append((fn, pk, raw,
                                            dict(prow["cells"])))
                            print(f"  + {raw['candidate']} "
                                  f"({raw['office']} {raw['district']}): "
                                  f"PROPOSE ADD whole race "
                                  f"({len(prow['cells'])} rows, printed "
                                  f"cells sum to csv {votes})")
                continue
            fcells = cells[pk]
            ftotal = sum(fcells.values())
            if ftotal == votes:
                continue
            mismatches += 1
            race = races.get((office, district))
            if not race:
                print(f"  ! {raw['candidate']} ({raw['office']} "
                      f"{raw['district']}): csv {votes} != file {ftotal} "
                      f"[no OCR section]")
                continue
            c = match_candidate(cand, list(race["rows"]))
            if c is None:
                print(f"  ! {raw['candidate']} ({raw['office']} "
                      f"{raw['district']}): csv {votes} != file {ftotal} "
                      f"[candidate not in OCR]")
                continue
            prow = race["rows"][c]
            pcells = prow["cells"]
            # a dropped TOTAL header can leave the row total posing as a
            # precinct cell (Hinds: 'utica 2' carrying the county-CSV
            # total); reassign it before diffing
            if len(pcells) > 1:
                for pprec, pval in list(pcells.items()):
                    if pval == votes and pprec not in fcells:
                        del pcells[pprec]
                        if prow["total"] is None:
                            prow["total"] = pval
            diffs = []       # printed value present and different
            unprinted = []   # file value where the recap prints nothing (x)
            missing = []     # printed precinct with no file row at all
            for fprec, fval in fcells.items():
                if fprec in pcells:
                    if pcells[fprec] != fval:
                        diffs.append((fprec, fval, pcells[fprec]))
                elif pcells:
                    # no printed counterpart: either the recap prints 'x'
                    # (zero) or its header/cell was dropped by OCR — the
                    # printed TOTAL arbitrates via the subset solution
                    unprinted.append((fprec, fval))
            for pprec, pval in pcells.items():
                if pprec not in fcells:
                    missing.append((pprec, pval))
            print(f"  ! {raw['candidate']} ({raw['office']} "
                  f"{raw['district']}): csv {votes} != file {ftotal} "
                  f"(printed cells for {len(pcells)}/{len(fcells)} file "
                  f"precincts"
                  + (f", printed TOTAL {prow['total']}" if prow["total"]
                     is not None else "") + ")")
            for fprec, fval, pval in diffs:
                print(f"      {fprec}: file {fval} vs printed {pval}")
            for fprec, fval in unprinted:
                print(f"      {fprec}: file {fval}, recap prints none (x)")
            for pprec, pval in missing:
                print(f"      {pprec}: MISSING from file, printed {pval}")
            gap = votes - ftotal
            total_ok = prow["total"] == votes
            psum = sum(pcells.values())
            # The printed TOTAL is the referee. Once every printed cell is
            # in place, whatever remains must come from the file's unprinted
            # ('x') cells — but those are a mix of genuinely dropped printed
            # cells (the file value is right) and spurious file rows (the
            # printed x means zero). Find the unique subset of unprinted
            # values that reconciles the TOTAL; ambiguity or no printed
            # TOTAL means manual review.
            solution = None
            if prow["total"] is not None:
                residual = prow["total"] - psum
                vals = [f for _, f in unprinted]
                if residual == 0:
                    solution = []
                elif 0 < residual <= sum(vals):
                    hits = [m for m in range(1, 1 << len(vals))
                            if sum(v for i, v in enumerate(vals)
                                   if m >> i & 1) == residual]
                    if len(hits) == 1:
                        solution = [i for i in range(len(vals))
                                    if hits[0] >> i & 1]
            if solution is not None and (diffs or missing
                    or len(solution) < len(unprinted)):
                for fprec, fval, pval in diffs:
                    fixes.append((fn, pk, fprec, fval, pval))
                if missing:
                    appends.append((fn, pk, raw, {p: v for p, v in missing}))
                for i, (fprec, fval) in enumerate(unprinted):
                    if i not in solution:
                        deletes.append((fn, pk, fprec, fval))
                parts = [f"{len(diffs)} cell fix(es)"] if diffs else []
                if missing:
                    parts.append(f"add {len(missing)} missing row(s)")
                if len(solution) < len(unprinted):
                    parts.append(f"zero {len(unprinted) - len(solution)}"
                                 f" spurious 'x' row(s)")
                print(f"      -> PROPOSE: {', '.join(parts)} "
                      f"(printed TOTAL {prow['total']} reconciles)")
            elif diffs:
                pdiff = sum(p - f for _, f, p in diffs)
                # unprinted ('x') cells are acceptable when the printed
                # cells plus the file's unprinted values reconcile to the
                # printed TOTAL — that implicitly confirms them
                reconciles = not unprinted or (
                    prow["total"] is not None
                    and psum + sum(f for _, f in unprinted) == prow["total"])
                if pdiff == gap and total_ok and reconciles:
                    for fprec, fval, pval in diffs:
                        fixes.append((fn, pk, fprec, fval, pval))
                    print(f"      -> PROPOSE FIX: set to printed values "
                          f"(closes gap {gap:+d}"
                          + (f"; {len(unprinted)} unprinted 'x' cell(s) "
                             f"reconcile to printed TOTAL"
                             if unprinted else "") + ")")
                else:
                    print(f"      .. printed diffs sum {pdiff:+d} vs gap "
                          f"{gap:+d} — needs review")
            elif missing and total_ok and psum == votes:
                appends.append((fn, pk, raw, {p: v for p, v in missing}))
                print(f"      -> PROPOSE ADD {len(missing)} missing row(s) "
                      f"(printed cells sum to csv {votes})")
    if fix and (fixes or appends or deletes):
        by_file = defaultdict(list)
        for fn, pk, fprec, fval, pval in fixes:
            by_file[fn].append(("fix", pk, fprec, fval, pval))
        for fn, pk, raw_row, adds in appends:
            by_file[fn].append(("add", pk, raw_row, adds))
        for fn, pk, fprec, fval in deletes:
            by_file[fn].append(("fix", pk, fprec, fval, 0))
        for fn, fl in by_file.items():
            rewrite_file(fn, fl, *ctx[fn])
        print(f"applied fixes to {len(by_file)} files; re-run crosscheck")
    elif fixes or appends or deletes:
        print(f"\n{len(fixes)} cell fixes, {len(appends)} row-appends, "
              f"{len(deletes)} zeroings proposed; re-run with --fix to apply")
    return 0


def rewrite_file(fn, fl, psc, samples, prec_names):
    """Apply ('fix', pk, fprec, fval, pval) cell corrections (pval 0 zeroes
    a spurious 'x' row) and ('add', pk, {prec_key: value}) missing-row
    appends to one precinct file."""
    with open(fn, newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    col = {h.strip().lower(): i for i, h in enumerate(header)}
    changed = 0
    appended = 0
    for entry in fl:
        if entry[0] == "fix":
            _, pk, fprec, fval, pval = entry
            n = 0
            for row in rows[1:]:
                if len(row) <= col["votes"]:
                    continue
                office_d, cand_k, party_k = (
                    normalize_office(row[col["office"]],
                                     row[col["district"]], psc),
                    name_key(row[col["candidate"]]),
                    PARTY_MAP.get(row[col["party"]].strip().upper(),
                                  row[col["party"]].strip().title()))
                k = (office_d[0], office_d[1], cand_k, party_k)
                if k == pk and prec_key(row[col["precinct"]]) == fprec \
                        and row[col["votes"]].strip() == str(fval):
                    row[col["votes"]] = str(pval)
                    changed += 1
                    n += 1
            if n != 1:
                print(f"  !! {fn}: {pk} {fprec}: matched {n} rows, skipped")
        else:
            _, pk_key, raw_row, adds = entry
            # sample row of the same candidate when the file has one;
            # otherwise any data row as a column template
            sample = samples.get(pk_key)
            if sample is None:
                sample = rows[1] + [""] * max(0, len(header) - len(rows[1]))
            n_added = 0
            for prec, val in adds.items():
                new_row = list(sample)
                new_row[col["precinct"]] = prec_names.get(prec, prec)
                new_row[col["candidate"]] = raw_row["candidate"]
                new_row[col["office"]] = raw_row["office"]
                new_row[col["district"]] = raw_row["district"]
                new_row[col["party"]] = raw_row["party"]
                new_row[col["votes"]] = str(val)
                rows.append(new_row)
                appended += 1
                n_added += 1
            print(f"  {fn}: appended {n_added} row(s) for {pk_key}")
    nl = "\r\n" if "\r\n" in open(fn, newline="").read() else "\n"
    with open(fn, "w", newline="") as f:
        csv.writer(f, lineterminator=nl).writerows(rows)
    print(f"  {fn}: {changed} cells fixed, {appended} rows appended")


if __name__ == "__main__":
    sys.exit(main())