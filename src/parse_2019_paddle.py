"""Parse PaddleOCR markdown for a 2019 primary recap scan into the raw CSV
the build_2019_precinct_from_raw.py builder expects, then run the same
verification as extract_2019_primary_precinct.py (internal TOTAL check +
crosstab check).

Markdown structure (from the AI Studio per-page output): one <table> per page;
a row whose first cell starts with "Votes cast in the County" holds the page's
precinct column headers (last real one may be TOTAL); office sections appear as
rows like "State Of Mississippi-Governor" whose other cells are empty; candidate
rows carry the name (party label either merged into the first cell or as its own
cell) followed by one cell per header column.

PaddleOCR's table detection sometimes drops the LAST data column of a page (the
values only -- headers survive), so every candidate row on the page comes back
one cell short. When at least half a page's candidate rows are short, this
parser re-submits just that page cropped to the table body (no cover text),
which reads all columns, and merges the recovered values in by row order.

Usage:
    uv run python parse_2019_paddle.py <County> <D|R>
"""

import csv
import difflib
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

COUNTY, PARTY = sys.argv[1], sys.argv[2]
CACHE = Path(f"cache/2019-{COUNTY.lower()}-{PARTY.lower()}")
# padded run (right-edge white margin) is preferred: the unpadded scans lose
# their last precinct column to PaddleOCR's table detection
MD_DIR = CACHE / ("paddle_pad" if (CACHE / "paddle_pad" / ".complete").exists()
                  else "paddle")
REC_DIR = MD_DIR / "recover"
RAW = CACHE / f"{COUNTY.lower()}_{PARTY.lower()}_precinct_raw.csv"
COUNTY_CSV = (f"2019/20190806__ms__democratic__primary__county.csv" if PARTY == "D"
              else "2019/20190806__ms__republican__primary__county.csv")

OFFICE_ROW = re.compile(r"^state of mississippi\b", re.I)

# Hand-read fills for pages whose last data column the recovery re-OCR could
# not recover (the endpoint is flaky AND nondeterministic; some pages failed
# every attempt). Values were read from 300dpi renders of the printed column
# and are cross-checked below by the internal TOTAL check (row sum vs printed
# TOTAL) and the crosstab check -- a wrong digit shows up in both.
# Keyed (COUNTY, PARTY, page) -> {normalized candidate name: value(s)}; the
# value fills the page's missing trailing header cell(s).
OVERRIDES = {
    ("Bolivar", "D", 5): {        # last header: Gunnison -- values verified on
                                  # the 300dpi render; each equals the
                                  # candidate's deficit vs the printed TOTAL
        "Addie Lee Green": 95, "Rickey L. Cole": 98, "Robert E. Amos": 91,
        "Dorothy 'Dot' Benford": 52, "Ryan Brown": 37, "Bruce Burton": 12,
        "De'Keilther A. Stamps": 11, "Willie L. Simmons": 115,
        "Marcus L. Wallace": 21, "Brenda F. Mitchell": 106,
    },
    ("Scott", "D", 2): {          # last header: Beat 3/Eastwest Morton -- the
        # recovery read mangled this column; values read off the printed
        # cells on the 300dpi render and cross-checked against the printed
        # p3/p4 rows (each row: p2 sum + Steele + p3 sum == printed TOTAL)
        "Michael Brown": 50, "William Bond Compton Jr.": 5, "Jim Hood": 289,
        "Robert J. Ray": 5, "Robert Shuler Smith": 41, "Gregory Wash": 6,
        "Welsha P. Williams": 16, "Albert Wilson": 7, "Day Hughes": 387,
        "Johnny DuProc": 282, "Maryra Hodges Hunt": 118,
        "Jennifer Riley Collins": 400,
    },
    ("Scott", "D", 3): {          # last header: Beat 5/Sebastopol -- printed
        # cells read off the 300dpi render; each p3 row reconciles exactly
        # against the printed p4 section-final page (Steele + p2 + p3 == TOTAL)
        "Michael Brown": 10, "William Bond Compton Jr.": 0, "Jim Hood": 29,
        "Robert J. Ray": 1, "Robert Shuler Smith": 7, "Gregory Wash": 1,
        "Welsha P. Williams": 2, "Albert Wilson": 2, "Day Hughes": 46,
        "Johnny DuProc": 27, "Johnny DuPree": 27, "Maryra Hodges Hunt": 16,
        "Jennifer Riley Collins": 44,
    },
    ("Scott", "D", 5): {          # last header: Beat 3/Eastwest Morton
        "Addie Lee Green": 379, "Rickey L. Cole": 382, "Robert E. Arnos": 383,
        "Robert E. Amos": 383, 'Dorothy "Dak" Benford': 164,
        'Dorothy "Dot" Benford': 164, "Ryan Brown": 109, "Bruce Burton": 62,
        "De'Kether A. Stamps": 60, "De'Keither A. Stamps": 60,
        "Willie L. Simmons": 183, "Marcus L. Wallace": 206, "Mike Marlow": 386,
    },
    ("Scott", "D", 9): {          # last header: Beat 5/Sebastopol (scan clips
        "Tom Miles": 0,           # the printed digits; read off the digit
        "Joe C. Bradford": 54,    # tops -- only the roster rows matter)
    },
    ("Simpson", "R", 3): {        # last header: Sumrall -- the OCR drops the
        # last column on each section's second page (11 headers, 10 values,
        # unshifted).  Values read off the printed 300dpi render; each equals
        # the candidate's deficit vs the printed section-final TOTAL.
        "Robert Foster": 49, "Tate Reeves": 135, "Bill Waller Jr.": 61,
        "Delbert Hosemann": 208, "Shane Quick": 29, "Sam Britton": 115,
        "Michael Watson": 118, "Mark Baker": 81, "Lynn Fitch": 96,
        "Andy Taggart": 65, "Shad White": 219,
    },
    ("Simpson", "R", 5): {        # last header: Magee 4 North -- same drop;
        # each value reconciles the printed p7 section-final row
        # (p5 + p6 + Weathersby == printed TOTAL)
        "Eugene S. 'Buck' Clarke": 120, "David McRae": 177,
        "Andy Gibson": 291, "Mike Chaney": 292, "Dane Maxwell": 198,
        "Kevin Schulz": 68, "Tom King": 129, "Tony Smith": 115,
        "Chad Toney": 38, "Chris Caughman": 281,
    },
    ("Simpson", "R", 6): {        # last header: Sumrali (misread Sumrall)
        "Eugene S. 'Buck' Clarke": 77, "David McRae": 161, "Andy Gipson": 234,
        "Mike Chaney": 232, "Dane Maxwell": 162, "Kelvin Schulz": 63,
        "Tom King": 104, "Tony Smith": 72, "Chad Toney": 53,
        "Chris Caughman": 221,
    },
}

# Section-final pages where the OCR shifted values onto the wrong rows (an
# office header absorbed the candidate row below it, shifting every row under
# it up by one and duplicating the last row).  Keyed
# (COUNTY, PARTY, page) -> {OCR'd row name: (printed candidate name, values)
# or None to drop a duplicated row}.  Values were read off the 300dpi render
# and are cross-checked by the internal TOTAL check and the crosstab check.
ROW_FIXES = {
    ("Simpson", "R", 7): {
        # printed: Chaney 75|5136, Maxwell 54|3528, Schulz 18|1346; the OCR
        # attached Chaney's values to the merged Insurance+PSC office-header
        # row, Maxwell's to the Chaney row, Schulz's to the Maxwell row, and
        # emitted Schulz's row twice
        "State Of Mississippi-Commissioner Of Insurance, Public Service "
        "Commissioner-Southern District": ("Mike Chaney", ["75", "5136"]),
        "Mike Chaney": ("Dane Maxwell", ["54", "3528"]),
        "Dane Maxwell": ("Kelvin Schulz", ["18", "1346"]),
        "Kelvin Schulz": None,
    },
}

# Digit fixes where the OCR read a wrong value in a cell that survives in
# BOTH reads (verified on the 300dpi render). Keyed
# (COUNTY, PARTY, page, candidate, normalized header) -> value.
CELL_FIXES = {
    ("Scott", "D", 2, "Gregory Wash", "beat 1 north forest"): "22",  # read 72
    # printed p5 cell is 108 (300dpi render); OCR read 109 -- proven by the
    # printed p6 section-final arithmetic (Amos EM printed 383, not 363);
    # p5 misreads the candidate name as 'Robert E. Arnos'
    ("Scott", "D", 5, "Robert E. Arnos", "beat 2 high hill"): "108",
    ("Scott", "D", 5, "Robert E. Amos", "beat 2 high hill"): "108",
    # printed p6 cell is 60 (300dpi row strip); OCR read 50
    ("Scott", "D", 6, "Willie L. Simmons", "beat 5 langs mill"): "60",
    # p6 Sebastopol cells (scan-edge-clipped last column): OCR misreads the
    # half-clipped digits.  Derived from the printed p7 section-final rows
    # (printed p5 + printed p6 non-Sebastopol verified cell-by-cell at
    # 300dpi; printed TOTAL - Steele - printed p5 - printed p6 = Sebastopol)
    ("Scott", "D", 6, "Bruce Burton", "beat 5 sebastopol"): "35",     # read 19
    ("Scott", "D", 6, "Addie Lee Green", "beat 5 sebastopol"): "43",  # read 41
    ("Scott", "D", 6, "Mike Marlow", "beat 5 sebastopol"): "46",      # read 44
    # printed p8 cell is 48 (300dpi row strip); OCR read 40 -- rightmost
    # column digits are clipped at the scan edge
    ("Scott", "R", 8, "Hampton Gardner", "beat 3 eastwest morton"): "48",
    # printed p9 cell is 67 (300dpi row strip); OCR read 57
    ("Scott", "R", 9, "Tyler McCaughn", "beat 5 salem"): "67",
    # scan-edge-clipped Sebastopol/Eastwest-Morton cells whose printed value
    # is pinned by the printed section-final row (Steele + TOTAL verified
    # against the render, all other cells verified cell-by-cell):
    # printed Taggart p2 EM = 73 (OCR 79; clipped 3 read as 9)
    ("Scott", "R", 2, "Andy Taggart", "beat 3 eastwest morgan"): "73",
    # printed Bailey p6 Sebastopol = 134 (OCR 114; clipped 3 read as 1);
    # p6 misreads the candidate name as 'Brent Belley'
    ("Scott", "R", 6, "Brent Belley", "beat 5 sebastopol"): "134",
    ("Scott", "R", 6, "Brent Bailey", "beat 5 sebastopol"): "134",
    # printed McCaughn p9 Sebastopol = 90 (OCR 88; clipped 0 read as 8)
    ("Scott", "R", 9, "Tyler McCaughn", "beat 5 sebastopol"): "90",
}

# Consistent precinct-header misreads: the same wrong name is printed by OCR
# on several pages, so consensus snapping (which only fixes one-off misreads)
# can't touch it.  Verified against the printed sheet / other pages of the
# same PDF.  Keyed (COUNTY, PARTY) -> {misread header: correct header}.
HEADER_FIXES = {
    ("Scott", "D"): {"Beat 4/North Norton": "Beat 4/North Morton"},
}

BASE_OFFICE_RE = re.compile(
    r"^(governor|lieutenant governor|lt governor|secretary of state|"
    r"attorney general|state auditor|state treasurer|"
    r"commissioner of agriculture|commissioner of insurance|"
    r"public service commissioner|transportation commissioner|"
    r"district attorney|state senate|state house)")


def base_office(s):
    """Core office name ('attorney general', ...) or None (same gate the
    builder applies -- keeps local-office same-name rows out of the sums)."""
    s = re.sub(r"\s+", " ", norm(s)).strip()
    s = re.sub(r"^state of mississippi\s+", "", s)
    m = BASE_OFFICE_RE.match(s)
    return m.group(1) if m else None


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


def load_roster():
    name_office = {}
    with open(COUNTY_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["county"] == COUNTY:
                name_office[row["candidate"]] = (row["office"], row["district"])
    return name_office


def strip_tags(s):
    import html
    s = re.sub(r"<[^>]+>", "", s)          # <br> etc.
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def page_tables(md):
    """Parse one page's markdown -> (headers, rows) where rows is a list of
    ('office', text) or ('cand', name, [value cells]) in table order."""
    rows = []
    headers = None
    header_pending = False
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", md, re.S):
        cells = []
        for attrs, body in re.findall(r"<td([^>]*)>(.*?)</td>", tr, re.S):
            m = re.search(r'colspan="?(\d+)', attrs)
            n = int(m.group(1)) if m else 1
            # text once + (n-1) blanks: a colspan'd label spans the label
            # columns (name + party), it does not duplicate content
            cells.extend([strip_tags(body)] + [""] * (n - 1))
        if not cells:
            continue
        first = cells[0]
        rest = cells[1:]
        low = norm(first)
        if low.startswith("votes cast in the county"):
            while rest and not rest[0]:
                rest.pop(0)                 # colspan padding of the label cell
            while rest and not rest[-1]:
                rest.pop()                  # trailing blank padding columns
            headers = rest
            # a rowspan'd label cell can push the real precinct-name row into
            # its own <tr> (Smith D p6): the votes-cast row then only carries
            # the "Names of Election Precincts" banner, and the precinct names
            # follow as the next row
            header_pending = len(headers) <= 2
            continue
        if (header_pending and len([c for c in cells if c]) >= 3
                and not any(c.replace(",", "").strip().isdigit()
                            for c in cells)):
            # the deferred precinct-name header row (all text, no values)
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
            continue                                  # cover / spacer rows
        if OFFICE_ROW.match(low) and not any(c for c in rest):
            rows.append(("office", first))
            continue
        if not any(c for c in rest):
            rows.append(("office", first))            # local office section header
            continue
        # candidate row: drop a separate party-label cell (and the colspan
        # padding blank that can sit between the name cell and it)
        vals = list(rest)
        if (len(vals) >= 2 and not vals[0]
                and norm(vals[1]).strip() in ("democrat", "republican")):
            vals.pop(0)
        if vals and norm(vals[0]).strip() in ("democrat", "republican"):
            vals.pop(0)
        m = re.match(r"^(.*?)(?:\s+(?:Democrat|Republican)\s*)$", first, re.I)
        name = (m.group(1) if m else first).strip()
        rows.append(("cand", name, vals))
    return headers, rows


def _grid_crop(img):
    """Crop to the table's horizontal band: the ruled table's vertical lines
    are the tallest dark structures in the column profile, so the columns
    they span give the table's x-range. The table sits left of center in some
    counties and right of center in others, so fixed fractional crops lose
    either the name column or the last value columns; this adapts."""
    import numpy as np

    a = np.asarray(img.convert("L"))
    dark = a < 245
    col_frac = dark.mean(axis=0)
    if col_frac.max() < 0.05:
        return None
    hit = np.where(col_frac > 0.45 * col_frac.max())[0]
    if not len(hit):
        return None
    left, right = int(hit.min()), int(hit.max())
    w, h = img.size
    return (max(0, left - 10), 0, min(w, right + 10), h)


def _table_variants(img):
    """Candidate table-body crops, best guess first."""
    out = []
    gc = _grid_crop(img)
    if gc:
        out.append(gc)
    w, h = img.size
    out.append((0, int(h * 0.28), int(w * 0.76), int(h * 0.97)))
    out.append((0, int(h * 0.18), int(w * 0.85), int(h * 0.99)))
    return out


def fetch_recovery_md(page, out_path, rows, headers):
    """Re-OCR one page cropped to the table body only (no cover header, no
    instruction text block): PaddleOCR's table detection then keeps the last
    data column that the full-page read dropped. The endpoint is
    nondeterministic (the same crop can yield different row merges), so each
    crop variant is scored by how many of the page's short candidate rows it
    would fill, the best read is cached, and the loop stops early once every
    short row is filled."""
    import io

    import extract_2019_paddle as ex
    from natural_pdf import PDF
    from PIL import Image, ImageOps

    if out_path.exists():
        return
    REC_DIR.mkdir(parents=True, exist_ok=True)
    pdf = PDF(ex.SOURCES_DIR / f"{COUNTY} Primary "
              f"{'REP' if PARTY == 'R' else 'DEM'}.pdf")
    img = pdf.pages[page - 1].render(resolution=200).convert("RGB")
    bbox = ImageOps.invert(img.convert("L")).getbbox()
    if bbox:
        img = img.crop(bbox)
    img = img.rotate(-90, expand=True)
    want = sum(1 for r in rows if r[0] == "cand" and len(r[2]) < len(headers))
    tmp = out_path.with_suffix(".pdf")
    best_count, best_md = -1, None
    variants = _table_variants(img)
    for attempt, crop in enumerate(variants * 2):
        job_name = f"jobid_rec_p{page:03d}.txt"
        if attempt >= len(variants):
            (CACHE / job_name).unlink(missing_ok=True)   # fresh job = new roll
        tab = img.crop(crop)
        tab = ImageOps.expand(tab, border=40, fill="white")
        buf = io.BytesIO()
        tab.save(buf, format="PDF")
        tmp.write_bytes(buf.getvalue())
        pages = ex.fetch_pdf(tmp, PARTY, ex.token(), CACHE,
                             job_name=job_name)
        _, trows = page_tables(pages[0])
        rec_cand = [r for r in trows if r[0] == "cand"]
        j = 0
        filled = 0
        for row in rows:
            if row[0] != "cand":
                continue
            _, name, vals = row
            while (j < len(rec_cand)
                   and difflib.SequenceMatcher(None, norm(name),
                                               norm(rec_cand[j][1])).ratio()
                   < 0.55):
                j += 1
            if j >= len(rec_cand):
                break
            tvals = rec_cand[j][2]
            j += 1
            if len(vals) < len(headers) and len(tvals) > len(vals):
                filled += 1
        print(f"  p{page}: crop variant {attempt % len(variants)} "
              f"(attempt {attempt // len(variants) + 1}) fills {filled}/{want} "
              f"short rows")
        if filled > best_count:
            best_count, best_md = filled, pages[0]
        if want and filled >= want:
            break
    if best_md is not None:
        (REC_DIR / f"p{page:03d}.md").write_text(best_md)
    tmp.unlink()


def main():
    roster = load_roster()
    warnings = []
    rows_out = []
    page_files = sorted(MD_DIR.glob("p*.md"))
    if not page_files:
        sys.exit(f"no markdown under {MD_DIR}")

    # ---- pass 1: parse every page, flag systematically short ones ----
    pages = {}
    for pf in page_files:
        page = int(re.search(r"p(\d+)\.md", pf.name).group(1))
        md = pf.read_text()
        if "votes cast in the county" not in norm(md):
            continue                                  # cover/signature page
        headers, rows = page_tables(md)
        if headers:
            fixes = HEADER_FIXES.get((COUNTY, PARTY), {})
            headers = [fixes.get(h, h) for h in headers]
        pages[page] = (headers, rows)
    # ---- header normalization: snap OCR misreads to names the PDF itself
    # prints on other pages. Every precinct's column header repeats once per
    # office section, so a real name appears several times across the PDF
    # while a misread appears once. Also drop phantom mid-row blank header
    # cells on pages whose header row is longer than the modal one (PaddleOCR
    # sometimes splits a column boundary, shifting every value from the blank
    # rightward onto the wrong precinct).
    page_headers = {p: h for p, (h, _) in pages.items() if h}
    freq = Counter()
    for hs in page_headers.values():
        for name in hs:
            if name.strip() and name.strip().upper() != "TOTAL":
                freq[name] += 1
    canonical = {n for n, c in freq.items() if c >= 2}
    modal = Counter(len(h) for h in page_headers.values()).most_common(1)[0][0]
    for page, (headers, rows) in sorted(pages.items()):
        if not headers:
            continue
        blanks = [i for i, h in enumerate(headers) if not h.strip()]
        if blanks and len(headers) > modal:
            for i in blanks:
                warnings.append(f"p{page}: dropping phantom blank header at "
                                f"position {i} ({len(headers)} cols vs modal "
                                f"{modal})")
            headers[:] = [h for h in headers if h.strip()]
        for i, h in enumerate(headers):
            if not h.strip() or h in canonical or h.strip().upper() == "TOTAL":
                continue
            close = difflib.get_close_matches(h, canonical, n=1, cutoff=0.7)
            if close:
                warnings.append(f"p{page}: header {h!r} snapped to "
                                f"{close[0]!r}")
                headers[i] = close[0]
            else:
                warnings.append(f"p{page}: header {h!r} appears once in the "
                                f"PDF and matches no other header; kept as is")

    short_pages = []
    for page, (headers, rows) in sorted(pages.items()):
        if not headers:
            continue
        ncand = sum(1 for r in rows if r[0] == "cand")
        nshort = sum(1 for r in rows if r[0] == "cand"
                     and len(r[2]) < len(headers))
        if ncand and nshort * 2 >= ncand:
            short_pages.append(page)
    if short_pages:
        print(f"short-row pages (recovering last column): "
              f"{[f'p{p:03d}' for p in short_pages]}")

    def _ovr_for(page, name):
        ovr = OVERRIDES.get((COUNTY, PARTY, page), {})
        if norm(name) in {norm(k) for k in ovr}:
            return ovr
        close = difflib.get_close_matches(norm(name), [norm(k) for k in ovr],
                                          n=1, cutoff=0.6)
        return ovr if close else {}

    def _is_roster_row(name, office_ctx):
        """True when a candidate row is a state-office (roster) row.  The
        proximity match alone isn't enough: a same-name local candidate
        (Scott D p11 Chancery-Clerk 'Michael Robinson' vs Gov 'Michael
        Brown', 0.76 similarity) must not count, so require the row's
        office context to agree with the roster office."""
        if name in roster:
            match = name
        else:
            close = difflib.get_close_matches(name, list(roster),
                                              n=1, cutoff=0.75)
            if not close:
                return False
            match = close[0]
        return base_office(office_ctx or "") == base_office(roster[match][0])

    def _overrides_cover(page, headers, rows):
        """True when every SHORT ROSTER candidate row on the page is covered
        by an override -- local-office rows are dropped at build time, so
        their missing trailing cells never matter."""
        ovr = OVERRIDES.get((COUNTY, PARTY, page), {})
        if not ovr:
            return False
        office = None
        for row in rows:
            if row[0] == "office":
                office = row[1]
                continue
            if len(row[2]) >= len(headers):
                continue
            if not _is_roster_row(row[1], office):
                continue
            if not _ovr_for(page, row[1]):
                return False
        return True

    # ---- pass 2: re-OCR short pages table-only, merge recovered values ----
    for page in short_pages:
        headers, rows = pages[page]
        if _overrides_cover(page, headers, rows):
            print(f"  p{page}: all short rows covered by hand-read overrides; "
                  f"skipping recovery OCR")
            continue
        office = None
        has_state_short = False
        for r in rows:
            if r[0] == "office":
                office = r[1]
                continue
            if (r[0] == "cand" and len(r[2]) < len(headers)
                    and _is_roster_row(r[1], office)):
                has_state_short = True
                break
        if not has_state_short:
            warnings.append(f"p{page}: short rows are all local-office "
                            f"candidates; skipping recovery OCR")
            continue
        out_path = REC_DIR / f"p{page:03d}.md"
        try:
            fetch_recovery_md(page, out_path, rows, headers)
        except Exception as exc:
            warnings.append(f"p{page}: recovery fetch failed: {exc}")
            continue
        theaders, trows = page_tables(out_path.read_text())
        rec_cand = [r for r in trows if r[0] == "cand"]
        if not rec_cand:
            warnings.append(f"p{page}: recovery has no candidate rows; "
                            f"skipping merge")
            continue
        # the recovery read can drop rows (office headers, occasionally a
        # candidate) and truncates names, so align recovery rows to main rows
        # in order by name
        j = 0
        for i, row in enumerate(rows):
            if row[0] != "cand":
                continue
            _, name, vals = row
            while (j < len(rec_cand)
                   and difflib.SequenceMatcher(None, norm(name),
                                               norm(rec_cand[j][1])).ratio()
                   < 0.55):
                j += 1
            if j >= len(rec_cand):
                break
            tvals = rec_cand[j][2]
            j += 1
            if len(vals) < len(headers) and len(tvals) > len(vals):
                diffs = sum(1 for x, y in zip(vals, tvals)
                            if x.strip() != y.strip())
                if diffs:
                    warnings.append(f"p{page}: {name}: {diffs} value(s) differ "
                                    f"between main and recovery reads")
                rows[i] = ("cand", name, tvals)
                warnings.append(f"p{page}: {name!r}: recovered "
                                f"{len(tvals) - len(vals)} value(s)")

    # ---- pass 3: emit rows, with TOTAL-aligned insertion for leftovers ----
    carry_office = None
    carry_page = None
    for page, (headers, rows) in sorted(pages.items()):
        for row in rows:
            if row[0] == "office":
                carry_office = row[1]
                carry_page = page
                continue
            _, cand, vals = row
            # ROW_FIXES: reassign OCR rows that landed on the wrong candidate
            # (see ROW_FIXES).  Lookup is by the row's name as OCR'd, before
            # any snapping; the printed office is taken from the roster so
            # the relabel logic assigns the row cleanly.
            office_fix = None
            if cand in ROW_FIXES.get((COUNTY, PARTY, page), {}):
                fix = ROW_FIXES[(COUNTY, PARTY, page)][cand]
                if fix is None:
                    continue          # duplicated row; the real one is fixed
                cand, vals = fix
                vals = list(vals)
                # the printed name may differ from the roster's spelling
                # (Simpson's roster has 'Kelvin NoRobo Schulz'); snap before
                # taking the roster office
                if cand not in roster:
                    close = difflib.get_close_matches(cand, roster, n=1,
                                                      cutoff=0.6)
                    cand = close[0] if close else cand
                office_fix = roster.get(cand)
            if headers is None:
                warnings.append(f"p{page}: candidate row before any header: {cand!r}")
                continue
            vals = list(vals)
            while vals and not vals[-1]:
                vals.pop()              # OCR's trailing blank padding cells
            if len(vals) < len(headers):
                # hand-read override (see OVERRIDES): fill the missing
                # trailing header cell(s) from values read off the render
                need = len(headers) - len(vals)
                ovr = _ovr_for(page, cand)
                match_key = None
                best_ratio = 0.0
                for k in ovr:
                    if norm(k) == norm(cand):
                        match_key, best_ratio = k, 1.0
                        break
                    ratio = difflib.SequenceMatcher(
                        None, norm(cand), norm(k)).ratio()
                    # take the BEST match, not the first that clears the
                    # bar ('Robert Shuler' must snap to 'Robert Shuler
                    # Smith', not dict-earlier 'Robert J. Ray')
                    if ratio >= 0.6 and ratio > best_ratio:
                        match_key, best_ratio = k, ratio
                if match_key is not None:
                    fill = ovr[match_key]
                    fill = [str(v) for v in
                            (fill if isinstance(fill, (list, tuple)) else [fill])]
                    if len(fill) == need:
                        vals = vals + fill
                        warnings.append(f"p{page}: {cand!r}: filled {need} "
                                        f"missing value(s) from hand-read "
                                        f"override {fill}")
                    else:
                        warnings.append(f"p{page}: {cand!r}: override has "
                                        f"{len(fill)} value(s) but {need} "
                                        f"needed; ignoring")
            if len(vals) < len(headers):
                # a dropped (usually zero/X) cell shifts everything left and
                # puts the printed TOTAL on the last precinct instead. Try
                # inserting a blank at each position; accept those that put the
                # row's max value on the TOTAL header (a section total is always
                # the row's largest cell). Ties are numerically identical --
                # the inserted blank is a zero either way -- so take the last.
                tidx = [i for i, h in enumerate(headers)
                        if h.strip().upper() == "TOTAL"]
                mx = max((float(v.replace(",", "")) for v in vals
                          if v.replace(",", "").strip().isdigit()), default=None)
                best = None
                for i in range(len(vals) + 1):
                    cand_vals = vals[:i] + [""] + vals[i:]
                    if len(cand_vals) != len(headers):
                        continue
                    if tidx and mx is not None:
                        cell = cand_vals[tidx[0]].replace(",", "").strip()
                        if not cell.isdigit() or float(cell) != mx:
                            continue
                    best = cand_vals
                if best is None:
                    warnings.append(f"p{page}: {cand!r} has {len(vals)} cells vs "
                                    f"{len(headers)} headers; no TOTAL-aligned "
                                    f"fit, padding blanks")
                    best = vals + [""] * (len(headers) - len(vals))
                else:
                    warnings.append(f"p{page}: {cand!r} short row ({len(vals)} "
                                    f"vs {len(headers)}); inserted blank")
                vals = best
            elif len(vals) > len(headers):
                # a trailing header cell can come back blank while its values
                # survive (Smith R p5's TOTAL column), leaving extra value
                # cells after the last named header. An extra that equals the
                # row's max value is that section's TOTAL.
                extras = vals[len(headers):]
                mx = max((float(v.replace(",", "")) for v in vals
                          if v.replace(",", "").strip().isdigit()), default=None)
                if (mx and all(v.replace(",", "").strip().isdigit()
                               and float(v.replace(",", "")) == mx
                               for v in extras)):
                    warnings.append(f"p{page}: {cand!r}: {len(extras)} extra "
                                    f"value cell(s) equal the row max; reading "
                                    f"as TOTAL (header cell came back blank)")
                    headers = headers + ["TOTAL"] * len(extras)
                else:
                    warnings.append(f"p{page}: {cand!r} has {len(vals)} cells "
                                    f"vs {len(headers)} headers; dropping "
                                    f"extras")
            for i, h in enumerate(headers):
                key = (COUNTY, PARTY, page, cand, norm(h))
                if key in CELL_FIXES:
                    warnings.append(f"p{page}: {cand!r} {h!r}: {vals[i]!r} -> "
                                    f"{CELL_FIXES[key]!r} (cell fix)")
                    vals[i] = CELL_FIXES[key]
            for h, v in zip(headers, vals):
                if not v and not h:
                    continue
                rows_out.append({
                    "page": page,
                    "precinct": h,
                    "office_raw": ((office_fix[0] if office_fix else None)
                                   or carry_office or "UNKNOWN"),
                    # office label carried over from a previous page?  a
                    # same-page header is trustworthy; a cross-page carry is
                    # not (the section the rows continue may not be the
                    # section the previous page ended with)
                    "carried": carry_page is not None and carry_page != page,
                    "office": "", "district": "",
                    "candidate": cand,
                    "votes": v,
                })
    pending_relabel = []
    for r in rows_out:
        cand = r["candidate"]
        match = cand if cand in roster else None
        if match is None:
            close = difflib.get_close_matches(cand, roster, n=1, cutoff=0.6)
            if close:
                match = close[0]
        if match is not None:
            office, district = roster[match]
            # a row whose office_raw isn't the office its roster candidate ran
            # for is either a local-office same-name row (e.g. Constable
            # 'Michael Brown' -- leave unassigned; the builder's gate drops
            # it) or a continuation row that lost its section header and
            # inherited the previous page's carry (Scott R p9 SD31 rows under
            # "Supervisor-Beat 5").  A genuine same-name local row sits under
            # a same-page header; a lost-header row sits under a cross-page
            # carry AND the candidate has proper-office rows elsewhere.
            if base_office(r["office_raw"] or "") == base_office(office):
                if match != cand:
                    warnings.append(f"p{r['page']}: snapped candidate "
                                    f"{cand!r} -> {match!r}")
                r["candidate"] = match
                r["office"], r["district"] = office, district
                continue
            if r.get("carried") and cand in roster:
                pending_relabel.append(r)
            warnings.append(f"p{r['page']}: office_raw {r['office_raw']!r} != "
                            f"roster {office!r} for {match!r}; leaving unassigned")
        else:
            warnings.append(f"p{r['page']}: unmatched candidate {cand!r} "
                            f"(office_raw {r['office_raw']!r})")

    # fallback: a section header can be lost/mangled on a continuation page
    # (e.g. Scott R's SD31 header merged into "Names of Election Precincts"),
    # leaving a candidate's rows under a bogus or local-office carry. If an
    # exactly-named roster candidate has NO rows under its proper office, trust
    # the roster for the unassigned rows.
    has_proper = {r["candidate"] for r in rows_out if r["office"]}
    for r in rows_out:
        cand = r["candidate"]
        if r["office"] or cand not in roster or cand in has_proper:
            continue
        office, district = roster[cand]
        warnings.append(f"p{r['page']}: {cand!r} rows under "
                        f"{r['office_raw']!r} have no proper-office rows; "
                        f"assigning to roster {office!r}")
        r["office"], r["district"] = office, district
        r["office_raw"] = office

    # second chance for cross-page carries: a section whose repeated header
    # was lost on a continuation page lets its rows inherit the previous
    # page's last section (Scott R p9/p10 SD31 rows carried "Supervisor-Beat
    # 5").  Relabel only when the candidate also has proper-office rows
    # (so a same-name local row under a same-page header is untouched) AND
    # the row's precinct is not already covered by a proper row (a genuine
    # same-name local candidate's rows cover the same precincts as the
    # roster candidate's; a lost-header continuation covers new ones).
    proper_precincts = defaultdict(set)
    for r in rows_out:
        if r["office"]:
            proper_precincts[r["candidate"]].add(norm(r["precinct"]))
    for r in pending_relabel:
        cand = r["candidate"]
        if cand not in has_proper:
            continue
        office, district = roster[cand]
        if norm(r["precinct"]) in proper_precincts.get(cand, set()):
            continue
        warnings.append(f"p{r['page']}: {cand!r} under carried "
                        f"{r['office_raw']!r} has no proper row for "
                        f"{r['precinct']!r}; relabeling to roster "
                        f"{office!r}")
        r["office"], r["district"] = office, district
        r["office_raw"] = office

    for r in rows_out:
        r.pop("carried", None)          # internal flag, not a CSV column
    with open(RAW, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page", "precinct", "office_raw",
                                          "office", "district", "candidate",
                                          "votes"])
        w.writeheader()
        w.writerows(rows_out)
    print(f"wrote {len(rows_out)} raw rows to {RAW}")
    for w in warnings:
        print(f"  ! {w}")

    # ---- verification ----
    print("\n=== verification ===")
    cell_sums = defaultdict(int)
    totals = {}
    bad_votes = []
    for r in rows_out:
        v = r["votes"]
        if v.upper() == "X" or not v.strip():
            continue
        if not v.replace(",", "").strip().isdigit():
            bad_votes.append(r)
            continue
        n = int(v.replace(",", ""))
        key = (r["office"], r["district"], r["candidate"])
        if r["precinct"].upper() == "TOTAL":
            if key in totals and totals[key] != n:
                print(f"  ! conflicting TOTALs for {key}: {totals[key]} vs {n}")
            totals[key] = n
        else:
            cell_sums[key] += n
    if bad_votes:
        print(f"  ! {len(bad_votes)} non-numeric vote cells:")
        for r in bad_votes[:20]:
            print(f"      {r}")
    mismatches = 0
    for key in sorted(set(cell_sums) | set(totals)):
        cs, tot = cell_sums.get(key, 0), totals.get(key)
        if tot is not None and cs != tot:
            mismatches += 1
            print(f"  ! TOTAL mismatch {key}: cells sum {cs} vs printed {tot}")
    print(f"  internal TOTAL check: {len(totals)} candidates with printed "
          f"TOTALs, {mismatches} mismatches")

    expected = {}
    with open(COUNTY_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["county"] == COUNTY:
                key = (row["office"], row["district"], row["candidate"])
                expected[key] = int(row["votes"])
    ok = bad = 0
    for key, exp in sorted(expected.items()):
        cs = cell_sums.get(key)
        tot = totals.get(key)
        if cs == exp and (tot is None or tot == exp):
            ok += 1
        else:
            bad += 1
            print(f"  ! crosstab mismatch {key}: crosstab {exp}, "
                  f"OCR cells {cs}, OCR TOTAL {tot}")
    print(f"  crosstab check: {ok} exact, {bad} differ")


if __name__ == "__main__":
    main()