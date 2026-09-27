"""Parse the Mississippi SoS 2019 primary "certified/amended results" PDFs into
OpenElections county-level CSVs.

Two source PDFs, two layouts (both ruled crosstabs, so natural_pdf table
extraction is deterministic):

* Democratic ("...2019 PE AMENDED 8 27 2019.pdf"): county headers are horizontal
  text in the header row ("State of MS - Governor | Adams | Alcorn | ..."), the
  first office section (Governor) hangs off that header cell, later sections are
  bold rows in column 0. County blocks of ~19 columns; only the last block has a
  TOTALS column.
* Republican ("Republican Certified Election Results_2019 PE.pdf"): rotated
  county headers whose extracted text is reversed (like the 2026 recap PDFs),
  col 0 header is "Office", every section (including Governor) is a bold row.
  Note this PDF prints the Lieutenant Governor section header as "Lt.
  Governor" (the DEM PDF spells it out) -- normalize_office must accept the
  abbreviated form, or that whole section's rows fall under Governor.

Both files repeat the full office/candidate list once per county block, so the
parser carries the current office down each page and resets it to Governor at
each block start (where the DEM header cell doubles as the Governor header).
Blank cells (this PDF prints nothing, unlike 2023's explicit "X") are ambiguous
between "not on ballot" and "zero votes", so they are omitted: only rows with
actual votes are written.

Verification:
* TOTAL reconciliation: each candidate's county sum vs the printed TOTALS
  column passes for all 182 DEM candidates and all REP candidates except five
  State House races. Those five were verified cell-by-cell against rendered
  page images and the repo's precinct-level CSVs: the printed TOTALs are typos
  in the certified crosstab (Hopkins HD7 5540, Kinkade HD52 6638, Powell HD59
  13376, Mussiett HD87 4834, McLeod HD107 9858), while the county cells match
  the precinct data (HD7/HD59/HD107 have no other counties; Kinkade's Tate cell
  is empty, consistent with Tate's precinct file lacking HD52).
* DEM statewide sums match the published certified results exactly (Hood
  208634, Brown 33247, Williams 20844, Shuler Smith 20395, ...).
* Cross-check vs 2019/counties/ precinct CSVs (crosscheck_2019_primary.py):
  DEM values are either exact or consistently higher (incomplete precinct
  files, e.g. Jefferson/Holmes short by hundreds, Hood +50..140 in several
  counties; isolated precinct-file errors too, e.g. Mickens HD42 Winston 289
  vs 1076, Hughes LG Attala 31445 vs 3145). REP values match except a handful
  of cells where the certified crosstab itself disagrees with the precinct
  data -- visually confirmed the PDF really prints these values: Watson (SoS)
  Hinds 1877 vs precinct 7877 and Wayne 374 vs 347, Britton (SoS) Yazoo 1212
  vs 1232, Baker (AG) Tishomingo 761 vs 1431 and Washington 409 vs 1109, and
  a few +/-1-50 cells (Watson +50 in Jones/Marion/Marshall). The county CSV
  follows the certified crosstab in every such case. Full details:
  2019/20190806-primary-county-vs-precinct-discrepancies.md

Usage:
    uv run python extract_2019_primary_county_pdf.py <input.pdf> <output.csv> \
        --party DEM|REP [--blanks blanks.csv]
"""

import argparse
import csv
import difflib
import re
import sys

from natural_pdf import PDF

FIELDS = ["county", "office", "district", "party", "candidate", "votes"]

# Canonical 82-county spellings (matches the rest of the repo).
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

ORDINALS = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6, "7th": 7,
            "8th": 8, "9th": 9, "10th": 10, "11th": 11, "12th": 12, "13th": 13,
            "14th": 14, "15th": 15, "16th": 16, "17th": 17, "18th": 18,
            "19th": 19, "20th": 20, "21st": 21, "22nd": 22}

DISTRICT_RE = re.compile(r"0*(\d+)")


def clean_cell(cell):
    if cell is None:
        return ""
    return str(cell).replace("\r", " ").strip()


def one_line(label):
    """Collapse a (possibly multi-line) cell label to single-spaced text."""
    return re.sub(r"\s+", " ", label.replace("\n", " ")).strip()


# Signature = county letters sorted, so scrambled rotated-header extractions
# ('Adasm', 'Coivntgon') still match. Guard: must be unique across counties.
LETTER_SIGS = {}
for _c in CANONICAL_COUNTIES:
    _sig = "".join(sorted(_c.lower().replace(" ", "")))
    if _sig in LETTER_SIGS:
        raise SystemExit(f"ambiguous county letter signature {_sig}: "
                         f"{_c} vs {LETTER_SIGS[_sig]}")
    LETTER_SIGS[_sig] = _c


def normalize_county(text, rotated):
    """Return the canonical county name for a header-cell string, or None."""
    if rotated:
        text = "".join(text.split())[::-1]
    text = one_line(text)
    if not text or text.upper() in ("TOTALS", "TOTAL"):
        return None
    if text.lower() == "claireborn" or text.lower() == "clairborne" or text == "Claiborne":
        return "Claiborne"
    if text in CANONICAL_COUNTIES:
        return text
    sig = "".join(sorted(text.lower().replace(" ", "")))
    if sig in LETTER_SIGS:
        if LETTER_SIGS[sig] != text:
            print(f"  ! scrambled county header {text!r} -> {LETTER_SIGS[sig]}",
                  file=sys.stderr)
        return LETTER_SIGS[sig]
    match = difflib.get_close_matches(text, CANONICAL_COUNTIES, n=1, cutoff=0.75)
    if match:
        print(f"  ! fuzzy county match: {text!r} -> {match[0]}", file=sys.stderr)
        return match[0]
    return None


def normalize_office(label):
    """Map a raw office-header label to (office, district), or None if it is
    not a recognizable office header."""
    l = one_line(label)
    low = l.lower()

    m = re.match(r"state of ms\s*-\s*governor", low)
    if m:
        return "Governor", ""
    if low == "governor":
        return "Governor", ""
    if "lieutenant gov" in low or re.search(r"\blt\.?\s+gov", low):
        return "Lieutenant Governor", ""
    if "secretary of state" in low:
        return "Secretary Of State", ""
    if "attorney general" in low:
        return "Attorney General", ""
    if re.search(r"\bauditor\b", low):
        return "State Auditor", ""
    if re.search(r"\btreasurer\b", low):
        return "State Treasurer", ""
    if "agriculture" in low:
        return "Commissioner Of Agriculture & Commerce", ""
    if "insurance" in low:
        return "Commissioner Of Insurance", ""

    for prefix, out in (("public service commissioner", "Public Service Commissioner"),
                        ("transportation commissioner", "Transportation Commissioner")):
        if low.startswith(prefix):
            m = re.search(r"(northern|central|southern)", low)
            if m:
                return f"{out}-{m.group(1).title()} District", ""
            return None

    m = re.match(r"district attorney[,\s]+(?:district\s+)?(\d+|[a-z]+)", low)
    if m:
        tok = m.group(1)
        n = int(tok) if tok.isdigit() else ORDINALS.get(tok)
        if n is None:
            raise ValueError(f"unrecognized DA district: {l!r}")
        return "District Attorney", f"{n:02d}"

    m = re.match(r"state\s+sen[a-z]*[,\s]+(?:district\s+)?0*(\d+)", low)
    if m:
        return "State Senate", str(int(m.group(1)))

    m = re.match(r"state\s+house\b[,\s]*(?:of\s+representatives|of\s+reps?)?\b"
                 r"[,\s]*(?:district\s+)?0*(\d+)", low)
    if m:
        return "State House Of Rep", str(int(m.group(1)))

    return None


def parse_pdf(pdf_path, party):
    """Extract result rows. Returns (rows, totals, blanks) where rows/blank
    entries are dicts over FIELDS (blank cells get votes=None) and totals maps
    (office, district, candidate) -> printed TOTAL (when a TOTALS column is
    present for the block)."""
    pdf = PDF(str(pdf_path))
    layout = detect_layout(pdf)
    print(f"  layout: {layout}")
    if layout == "rep":
        return parse_pdf_rep(pdf, party)
    return parse_pdf_dem(pdf, party)


def detect_layout(pdf):
    for page in pdf.pages:
        table = page.extract_table()
        if table is not None and list(table):
            first = clean_cell(list(table)[0][0])
            if first.startswith("State of MS"):
                return "dem"
            return "rep"
    raise SystemExit("no table found in PDF")


# --- Republican layout (rotated county headers) -----------------------------
#
# extract_table cannot be used for the county columns: the rotated header text
# physically crosses the column ruling lines, so the detected grid splits single
# counties into several columns (and repeats fragments of neighboring labels).
# The data columns are instead rebuilt from the page's vertical ruling lines,
# and county names come from the blocks being contiguous alphabetical runs of
# the 82 counties -- verified visually on each block's first page (blocks start
# at Adams, Hancock, Lincoln and Simpson, 22/20/21/19 counties).

BLOCK_SIZES = [22, 20, 21, 19]
ALPHABETICAL = sorted(CANONICAL_COUNTIES, key=lambda c: c.lower().replace(" ", ""))


def cluster(values, tol):
    out = []
    for v in sorted(values):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(g) / len(g) for g in out]


def rep_grid(page):
    """Column x-boundaries and row y-boundaries from the ruling lines. Only
    lines with enough total coverage are kept, so stray narrow boxes (e.g. the
    yellow highlight on some header cells) don't create phantom columns."""
    def line_positions(thickness, get_key, get_span):
        groups = {}  # key -> list of (span_start, span_end)
        for r in page.rects:
            if thickness(r) > 3:
                continue
            key = get_key(r)
            for gk in list(groups):
                if abs(gk - key) <= 3:
                    key = gk
                    break
            groups.setdefault(key, []).append(get_span(r))
        out = []
        for key in sorted(groups):
            cover, end = 0, None
            for s0, s1 in sorted(groups[key]):
                if end is None or s0 > end:
                    cover += s1 - s0
                    end = s1
                elif s1 > end:
                    cover += s1 - end
                    end = s1
            if cover > 300:
                out.append(key)
        return out

    return (line_positions(lambda r: r.width, lambda r: r.x0,
                           lambda r: (r.top, r.bottom)),
            line_positions(lambda r: r.height, lambda r: r.top,
                           lambda r: (r.x0, r.x1)))


def parse_pdf_rep(pdf, party):
    counties_by_block = []
    start = 0
    for size in BLOCK_SIZES:
        counties_by_block.append(ALPHABETICAL[start:start + size])
        start += size
    assert start == len(ALPHABETICAL)

    rows, blanks, totals = [], [], {}
    current = ("Governor", "")
    warned = set()

    for pno, page in enumerate(pdf.pages, start=1):
        bounds, ybounds = rep_grid(page)
        if len(bounds) < 3 or len(ybounds) < 3:
            continue  # title / blank page
        block = (pno - 2) // 16  # 16 pages per block, first data page is p2
        if block >= len(counties_by_block):
            print(f"  ! p{pno}: page outside known blocks", file=sys.stderr)
            continue
        counties = counties_by_block[block]
        n_data = len(bounds) - 2  # col 0 = Office; rest are counties (+TOTAL)
        expect = len(counties) + (1 if block == len(BLOCK_SIZES) - 1 else 0)
        if n_data != expect:
            print(f"  ! p{pno}: {n_data} data columns, expected {expect}",
                  file=sys.stderr)

        bolds = [c for c in page.chars if c.bold]
        for ri in range(len(ybounds) - 1):
            y0, y1 = ybounds[ri], ybounds[ri + 1]
            if y1 - y0 < 10:
                continue
            band = [c for c in page.chars if y0 <= (c.top + c.bottom) / 2 - 0 < y1]
            if not band:
                continue
            # column-0 label
            label_chars = sorted((c for c in band if c.x0 < bounds[1]),
                                 key=lambda c: (round(c.top), c.x0))
            label = "".join(c.text for c in label_chars).strip()
            if not label:
                continue
            if re.sub(r"[^a-z]", "", label.lower()) == "office":
                continue  # the rotated "Office" header-cell text
            is_bold = all(c.bold for c in label_chars)
            if is_bold:
                flat = one_line(label)
                norm = normalize_office(flat)
                if norm is None:
                    if flat not in warned:
                        print(f"  ! p{pno}: unrecognized office header {flat!r}",
                              file=sys.stderr)
                        warned.add(flat)
                    continue
                current = norm
                continue

            office, district = current
            name = one_line(label)
            for k, county in enumerate(counties):
                if k + 1 >= len(bounds) - 1:
                    break
                x0, x1 = bounds[k + 1], bounds[k + 2]
                cell = [c for c in band if x0 <= (c.x0 + c.x1) / 2 < x1]
                text = "".join(c.text for c in sorted(cell, key=lambda c: c.x0))
                val = text.strip().replace(",", "")
                rec = {"county": county, "office": office, "district": district,
                       "party": party, "candidate": name, "votes": None}
                if val == "" or val.upper() == "X":
                    blanks.append(rec)
                    continue
                if not val.isdigit():
                    print(f"  ! p{pno}: non-numeric vote {val!r} for {name} / "
                          f"{county}", file=sys.stderr)
                    continue
                rec["votes"] = int(val)
                rows.append(rec)

            # TOTAL column (last block only)
            if block == len(BLOCK_SIZES) - 1 and len(bounds) > 2:
                x0, x1 = bounds[-2], bounds[-1]
                cell = [c for c in band
                        if x0 <= (c.x0 + c.x1) / 2 < x1 and c.x0 > bounds[1]]
                text = "".join(c.text for c in sorted(cell, key=lambda c: c.x0))
                tval = text.strip().replace(",", "")
                if tval.isdigit():
                    totals[(office, district, name)] = int(tval)

    return rows, totals, blanks


def parse_pdf_dem(pdf, party):
    rows, blanks, totals = [], [], {}
    prev_counties = None
    current = ("Governor", "")  # first section hangs off the header cell
    warned_labels = set()

    for pno, page in enumerate(pdf.pages, start=1):
        table = page.extract_table()
        if table is None:
            print(f"  ! p{pno}: no table", file=sys.stderr)
            continue
        data = [list(r) for r in table]
        if not data:
            continue

        # Header row -> county columns (and possible TOTALS column).
        rotated = False
        counties, total_col = {}, None
        for ci in range(1, len(data[0])):
            raw = clean_cell(data[0][ci])
            if not raw:
                continue
            name = normalize_county(raw, rotated=False)
            if name is None:
                name = normalize_county(raw, rotated=True)
                if name is not None:
                    rotated = True
            if name is None and raw.upper() in ("TOTALS", "TOTAL"):
                total_col = ci
            elif name is not None:
                counties[ci] = name
        if not counties:
            continue  # title page
        block_start = counties != prev_counties
        if block_start:
            current = ("Governor", "")
            prev_counties = dict(counties)

        for row in data[1:]:
            label = clean_cell(row[0])
            if not label:
                continue
            flat = one_line(label)
            # Office sections are bold rows in column 0; identify them by
            # content (normalize_office's patterns are specific enough that
            # no candidate name matches) rather than by bold runs, which
            # extract unreliably from these cells.
            norm = normalize_office(flat)
            if norm is not None:
                current = norm
                continue
            # candidate row
            office, district = current
            name = flat
            for ci, county in counties.items():
                if ci >= len(row):
                    continue
                val = clean_cell(row[ci]).replace(",", "")
                rec = {"county": county, "office": office, "district": district,
                       "party": party, "candidate": name, "votes": None}
                if val == "" or val.upper() == "X":
                    blanks.append(rec)
                    continue
                if not val.isdigit():
                    print(f"  ! p{pno}: non-numeric vote {val!r} for {name} / "
                          f"{county}", file=sys.stderr)
                    continue
                rec["votes"] = int(val)
                rows.append(rec)

            if total_col is not None and total_col < len(row):
                tval = clean_cell(row[total_col]).replace(",", "")
                if tval.isdigit():
                    totals[(office, district, name)] = int(tval)

    return rows, totals, blanks


def reconcile(totals, rows):
    """Per-candidate county sums vs the printed TOTALS column."""
    summed = {}
    for r in rows:
        key = (r["office"], r["district"], r["candidate"])
        summed[key] = summed.get(key, 0) + r["votes"]
    ok = True
    for key, printed in sorted(totals.items()):
        got = summed.get(key)
        tag = f"{key[2]} ({key[0]}{'-' + key[1] if key[1] else ''})"
        if got != printed:
            ok = False
            print(f"  ! TOTAL mismatch {tag}: summed {got} != printed {printed}",
                  file=sys.stderr)
    if ok:
        print(f"  ✓ TOTAL reconciliation passed for {len(totals)} candidates")
    return ok


def write_csv(rows, path):
    out = [r for r in rows if r["votes"] is not None]
    out.sort(key=lambda r: (r["county"], r["office"], r["district"], r["candidate"]))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)


def write_blanks(blanks, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(blanks)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("output_csv")
    ap.add_argument("--party", required=True, choices=["DEM", "REP"])
    ap.add_argument("--blanks", help="write blank-cell report CSV here")
    args = ap.parse_args()

    print(f"Parsing {args.pdf_path} ...")
    rows, totals, blanks = parse_pdf(args.pdf_path, args.party)
    counties = {r["county"] for r in rows} | {r["county"] for r in blanks}
    print(f"  {len(rows)} vote rows, {len(blanks)} blank cells, "
          f"{len(counties)} counties")

    reconcile(totals, rows)

    write_csv(rows, args.output_csv)
    print(f"  wrote {args.output_csv}")
    if args.blanks:
        write_blanks(blanks, args.blanks)
        print(f"  wrote {args.blanks}")


if __name__ == "__main__":
    main()