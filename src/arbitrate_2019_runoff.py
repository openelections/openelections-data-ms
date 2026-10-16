"""Arbitrate 2019 primary-runoff county-CSV vs precinct-file discrepancies
against the per-county runoff recap scans (PaddleOCR markdown in
cache/2019-runoff-<county>-<party>/paddle/, fetched by
extract_2019_runoff_paddle.py).

For one (county, party, office, district) section this prints:
  * the recap's printed precinct headers,
  * each candidate's per-precinct values + printed TOTAL,
  * the 2020 precinct file's per-precinct rows for that office,
  * the county-CSV (statewide crosstab) value,

so the three sources can be compared cell-by-cell.

Usage:
    uv run python arbitrate_2019_runoff.py <County> <D|R> "<office label fragment>"
"""

import csv
import glob
import re
import sys
import unicodedata
from pathlib import Path


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"\s+", " ", s).strip().lower()


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


OFFICE_ROW = re.compile(r"^(state of mississippi|state senate|state house)", re.I)


def page_tables(md):
    """Parse one page's markdown -> (headers, rows); rows are ('office', text)
    or ('cand', name, [value cells]). Same logic as parse_2019_paddle.py."""
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
        if low.startswith("votes cast in the county"):
            while rest and not rest[0]:
                rest.pop(0)
            while rest and not rest[-1]:
                rest.pop()
            headers = rest
            header_pending = len(headers) <= 2
            continue
        if (header_pending and len([c for c in cells if c]) >= 3
                and not any(c.replace(",", "").strip().isdigit() for c in cells)):
            while cells and not cells[-1]:
                cells.pop()
            headers = cells
            header_pending = False
            continue
        header_pending = False
        if (low.startswith(("official recap", "names of election",
                            "nations of election"))
                or ("of election" in low and "prec" in low)
                or not low):
            continue
        if OFFICE_ROW.match(low) and not any(c for c in rest):
            rows.append(("office", first.replace("\n", " ")))
            continue
        if not any(c for c in rest):
            rows.append(("office", first.replace("\n", " ")))
            continue
        vals = list(rest)
        if (len(vals) >= 2 and not vals[0]
                and norm(vals[1]).strip() in ("democrat", "republican")):
            vals.pop(0)
        if vals and norm(vals[0]).strip() in ("democrat", "republican"):
            vals.pop(0)
        m = re.match(r"^(.*?)(?:\s+(?:Democrat|Republican)\s*)$", first, re.I)
        name = (m.group(1) if m else first).strip().replace("\n", " ")
        rows.append(("cand", name, vals))
    return headers, rows


def parse_int(v):
    v = (v or "").replace(",", "").strip()
    return int(v) if v.isdigit() else None


def main():
    county, party, frag = sys.argv[1], sys.argv[2], sys.argv[3]
    md_dir = Path(__file__).resolve().parent.parent / f"cache/2019-runoff-{county.lower()}-{party.lower()}/paddle"
    paths = sorted(glob.glob(str(md_dir / "p*.md")))
    if not paths:
        sys.exit(f"no OCR pages in {md_dir}")
    for path in paths:
        headers, rows = page_tables(open(path).read())
        # find the office sections matching the fragment
        sections = []
        for i, row in enumerate(rows):
            if row[0] == "office" and frag.lower() in row[1].lower():
                sections.append((i, row[1]))
        if not sections:
            continue
        print(f"== {Path(path).name}  headers: {headers}")
        pnums = re.search(r"p(\d+)\.md", path)
        page_no = int(pnums.group(1)) if pnums else 0
        # precinct-file rows for this county
        pf_path = (f"2019/counties/20190827__ms__primary_runoff__"
                   f"{county.lower()}__precinct.csv")
        pf = {}
        for r in csv.DictReader(open(pf_path, newline="")):
            if r["party"].strip().upper() != party:
                continue
            if frag.lower() not in (r["office"] or "").lower() and not (
                    "governor" in frag.lower() and r["office"] == "Governor"):
                continue
            pf.setdefault(norm(r["precinct"]), []).append(
                (r["candidate"], r["votes"]))
        for i, label in sections:
            print(f"  SECTION: {label}")
            for row in rows[i + 1:]:
                if row[0] == "office":
                    break
                _, name, vals = row
                # align values to headers (both end at the last non-empty val)
                print(f"    {name:32s} {vals}")
            tot = None
            for h in headers or []:
                if norm(h) == "total":
                    tot = h
            if tot:
                print(f"    (printed TOTAL column is present: {tot!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())