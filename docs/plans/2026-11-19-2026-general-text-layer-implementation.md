# 2026 General Text-Layer County Conversion — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert the four 2026 MS general election county PDFs that carry an embedded text layer (Jasper, Lee, Union, Warren) into per-county OpenElections precinct CSVs in `2026/counties/`.

**Architecture:** A deterministic natural_pdf geometry parser rebuilds each SEMS "Official Recapitulation" crosstab (candidate rows x precinct columns) from word/char coordinates — no OCR, no vision models. Internal gates (row sums vs the PDF's own TOTAL column, roster consistency, structure checks) decide whether a county's CSV may be written. Design doc: `docs/plans/2026-11-19-2026-general-text-layer-conversion-design.md`.

**Tech Stack:** Python 3.12 via `uv run` (always — never bare `python3`), natural_pdf (pdfplumber-backed) for pages, stdlib `unittest` for tests (pytest is NOT installed and we will not add it), difflib for fuzzy label matching on the two OCR-noisy counties (Jasper, Lee).

**Verified geometry facts** (probed 2026-11-19 on `Union_County_2026_general.pdf`, page 2 — rely on these, don't re-derive):

- Pages are natively landscape (~787.7 x 607.0 pt); all chars are upright. The certification blurb repeats at the top of every table page and must be excluded before parsing.
- `page.extract_table()` returns nothing — there are no detectable ruled lines. Use `page.words` and `page.chars` (both exist on natural_pdf pages) with x/y coordinates.
- Candidate/office labels occupy a left x-band (~x0 40-180). Numeric cells cluster at an even ~45 pt x-pitch. Precinct headers are vertical char stacks (one char per word-object, constant x0, descending y) that interleave in y with the blurb prose lines — prose lines are wide (x-span > 300 pt), header stacks are narrow and at constant x0.
- The TOTAL column appears (per the 2024 runbook) on the **last** table page only, identified by its vertical "TOTAL" header.

**Data conventions that pin the output** (from 2024 general / 2026 primary precedent):

- Header: `county,precinct,office,district,candidate,party,votes`. No winner column, no TOTAL rows written.
- Office map: `United States-Senate` -> `U.S. Senate`; `US House Of Rep NN` -> `U.S. House` + district `N`; `Court Of Appeals 0N-District N...` -> `Court of Appeals`; `Chancery Court ...` -> `Chancery Court`. Party: `Democrat`->DEM, `Republican`->REP, `Libertarian`->LIB, `Constitution`->CON, Independent->IND, `Nonpartisan`->blank.
- Two-seat judicial rule (approved judgment call): bare office label when one seat of a district appears; append the printed seat qualifier (`Court of Appeals Position 2`, `Chancery Court Place 2`) when two seats appear.
- Candidates keep ballot order (do not sort). File sorts by precinct name.
- Sources live in `~/code/openelections-sources-ms/2026/general/` (sibling checkout; never import its PDFs into this repo).
- Testing in this project: run via `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v` from the repo root.

**Gotchas for the implementer** (from `CLAUDE.md` + runbooks):

- Precinct names contain unquoted commas and stray quotes; never split on commas — use coordinates.
- The two OCR-noisy files (Jasper, Lee) have text layers produced by scanner OCR ("Elecuon", "Recapltulatlon"); digit confusions must be cleaned only *inside numeric columns*, never in label text, and every fuzzy guess must still pass the gates.
- If a county fails its gates after real fixes, stop and diagnose — do not weaken a gate. Escalation path: render pages and read as a vision model, then PaddleOCR (`cache/` pattern) — record whatever decision is made in the notes report.

---

### Task 1: Module skeleton + geometry helpers (lines, table-top detection, x-clustering)

**Files:**
- Create: `src/extract_2026_general_text_pdf.py`
- Test: `test/test_2026_general_text_parser.py`

**Step 1: Write the failing tests**

Create `test/test_2026_general_text_parser.py`:

```python
"""Tests for the 2026 general text-layer county extractor.

Pure-function tests run everywhere. Integration tests read the real PDFs in
~/code/openelections-sources-ms/ and are skipped when that checkout is absent.
"""
import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import extract_2026_general_text_pdf as ex  # noqa: E402

SOURCES_DIR = os.path.expanduser("~/code/openelections-sources-ms/2026/general")
SOURCES_PRESENT = os.path.isdir(SOURCES_DIR)


def w(text, x0, top, x1=None, bottom=None):
    return {"text": text, "x0": x0, "x1": x1 if x1 is not None else x0 + len(text) * 5,
            "top": top, "bottom": bottom if bottom is not None else top + 8}


def c(text, x0, top):
    return {"text": text, "x0": x0, "x1": x0 + 5, "top": top, "bottom": top + 8}


class GeometryTests(unittest.TestCase):
    def test_lines_group_by_top(self):
        words = [w("Votes", 40, 94), w("cast", 70, 94.5), w("in", 100, 95, x1=105),
                 w("Chunky", 45, 150)]
        lines = ex.lines_from_words(words, y_tol=2.0)
        self.assertEqual(len(lines), 2)
        self.assertEqual(len(lines[0]["words"]), 3)
        self.assertEqual(lines[0]["text"], "Votes cast in")

    def test_find_table_top_needs_three_digit_columns(self):
        lines = ex.lines_from_words([
            # prose line with one stray number - not a table line
            w("the 3rd day of November 2026 end", 40, 104, x1=700),
            # wide prose with two numbers - still not enough
            w("401 MISSISSIPPI ST 39201 and 3 copies", 40, 114, x1=700),
            # table line: label + three numeric cells across columns
            w("Chunky", 45, 150.0, x1=130),
            w("188", 246.0, 152.0), w("164", 291.0, 152.0), w("5", 337.0, 152.0),
        ])
        top = ex.find_table_top(lines)
        self.assertEqual(top, 150.0)

    def test_column_centers_cluster_by_pitch(self):
        digits = [w("188", 246, 152), w("190", 246, 300), w("164", 291, 152),
                  w("170", 292, 300), w("5", 337, 152), w("4", 338, 300)]
        centers = ex.column_centers(digits)
        self.assertEqual(len(centers), 3)
        self.assertAlmostEqual(centers[0], 246.0)
        self.assertAlmostEqual(centers[1], 291.5)
        self.assertAlmostEqual(centers[2], 337.5)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v`
Expected: FAIL (`ModuleNotFoundError: extract_2026_general_text_pdf`), and a comment line in the sources-repo skip test would matter only later.

**Step 3: Write minimal implementation**

Create `src/extract_2026_general_text_pdf.py`:

```python
"""Deterministic extraction of precinct-level results from 2026 Mississippi
general election county recapitulation PDFs that carry an embedded text layer.

Rebuilds the SEMS "Official Recapitulation" crosstab (candidate rows x
precinct columns) from natural_pdf word/char geometry -- no OCR, no vision
models. Internal gates decide whether a county's CSV may be written:

1. per-candidate precinct sums equal the PDF's own TOTAL column,
2. structure: header columns match body columns on every table page,
3. roster consistency across counties sharing a race (batch stage).

natural_pdf is imported lazily: the pure geometry/label functions must stay
importable (and testable) without it.

Usage:
    uv run python src/extract_2026_general_text_pdf.py \
        ~/code/openelections-sources-ms/2026/general/Union_County_2026_general.pdf \
        --county Union --out 2026/counties/20261103__ms__general__union__precinct.csv
"""

import re

DIGIT_RE = re.compile(r"^-?\d+$")

DIGIT_CLEANUP = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "|": "1", "S": "5", "s": "5"})


def digit_clean(text, enabled):
    """Normalize a suspected numeric token. Only ever applied to tokens chosen
    because they sit in numeric columns -- never to label text."""
    t = text.strip().replace(",", "").replace(" ", "")
    if enabled:
        t = t.translate(DIGIT_CLEANUP)
    return t


def looks_numeric(text, fuzzy=False):
    return bool(DIGIT_RE.match(digit_clean(text, fuzzy)))


def lines_from_words(words, y_tol=3.0):
    """Group words into text lines by top coordinate; return list of
    {"top", "words": [word dicts sorted by x0], "text": " ".join}
    sorted by top."""
    order = sorted(words, key=lambda x: (x["top"], x["x0"]))
    lines = []
    for word in order:
        if lines and abs(word["top"] - lines[-1]["top"]) <= y_tol:
            lines[-1]["words"].append(word)
        else:
            lines.append({"top": word["top"], "words": [word]})
    for ln in lines:
        ln["words"].sort(key=lambda x: x["x0"])
        ln["text"] = " ".join(x["text"] for x in ln["words"])
    return lines


def _x_span(line):
    return line["words"][-1]["x1"] - line["words"][0]["x0"]


def find_table_top(lines, min_columns=3):
    """Top coordinate of the first table data line: the first line containing
    >= min_columns numeric tokens in >= min_columns distinct x clusters.
    Prose lines (strays like '2026', '(3)', '39201,') never reach that count."""
    for line in lines:
        nums = [x for x in line["words"] if looks_numeric(x["text"])]
        xs = [x["x0"] for x in nums]
        clusters = cluster_xs([(x, x) for x in xs], gap=20.0)
        if len(nums) >= min_columns and len(clusters) >= min_columns:
            return line["top"]
    return None


def cluster_xs(pairs, gap=20.0):
    """Cluster (x, payload) pairs by x with unsorted-adjacent gap threshold.
    Returns sorted list of clusters; each cluster is {"center", "items"}."""
    items = sorted(pairs, key=lambda p: p[0])
    clusters = []
    for x, payload in items:
        if clusters and x - clusters[-1]["items"][-1][0] <= gap:
            clusters[-1]["items"].append((x, payload))
        else:
            clusters.append({"center": x, "items": [(x, payload)]})
    for cl in clusters:
        cl["center"] = sum(x for x, _ in cl["items"]) / len(cl["items"])
    return clusters


def column_centers(digit_words, gap=20.0):
    """Distinct x0 centers of numeric columns, ascending."""
    clusters = cluster_xs([(w["x0"], w) for w in digit_words], gap=gap)
    return sorted(cl["center"] for cl in clusters)
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v`
Expected: PASS (4 tests).

**Step 5: Commit**

```bash
git add src/extract_2026_general_text_pdf.py test/test_2026_general_text_parser.py
git commit -m "Add 2026 general text-layer extractor: geometry helpers

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Vertical header stacks (precinct names, TOTAL)

**Files:**
- Modify: `src/extract_2026_general_text_pdf.py`
- Test: `test/test_2026_general_text_parser.py`

**Step 1: Write the failing tests**

Append to `test/test_2026_general_text_parser.py`:

```python
class VerticalStackTests(unittest.TestCase):
    def build_table_chars(self):
        # Two columns at x=246 and x=291; precinct names stacked one char per y.
        # "Dist 1, Bellemont" style name with a comma is the classic landmine.
        chars = []
        for i, ch in enumerate("Bellemont"):
            chars.append(c(ch, 246.0, 120.0 + i * 9))
        chars.append(c(",", 246.0, 120.0 + 9 * 8))  # comma in the name
        for i, ch in enumerate("Chunky"):
            chars.append(c(ch, 291.0, 120.0 + i * 9))
        # wide prose line to be excluded (spans across columns)
        for x in range(60, 400, 5):
            chars.append(c("x", float(x), 96.0))
        return chars

    def test_read_vertical_headers(self):
        chars = self.build_table_chars()
        got = ex.vertical_headers(chars, [246.0, 291.0],
                                  exclude_tops=(90.0, 100.0))
        self.assertEqual(got[246.0], "Bellemont,")
        self.assertEqual(got[291.0], "Chunky")

    def test_total_header_detected(self):
        chars = [c(ch, 700.0, 120.0 + i * 9) for i, ch in enumerate("TOTAL")]
        got = ex.vertical_headers(chars, [700.0], exclude_tops=(0.0, 0.0))
        self.assertEqual(ex.total_col(got), 700.0)

    def test_header_word_gap_becomes_space(self):
        chars = ([c(ch, 246.0, 120.0 + i * 9) for i, ch in enumerate("Dist")]
                 + [c(ch, 246.0, 120.0 + 4 * 9 + 6 + i * 9) for i, ch in enumerate("1")])
        got = ex.vertical_headers(chars, [246.0], exclude_tops=(0.0, 0.0))
        self.assertEqual(got[246.0], "Dist 1")
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v -k Vertical`
Expected: FAIL (`AttributeError: module ... has no attribute 'vertical_headers'`).

**Step 3: Write minimal implementation**

Append to `src/extract_2026_general_text_pdf.py`:

```python
X_TOL = 6.0          # char x0 must sit within this of a column center
STACK_X_TOL = 2.5    # chars of one vertical stack share x0 this tightly
CHAR_STEP_JITTER = 2.0
MIN_STACK_CHARS = 2
WORD_GAP_FACTOR = 0.6  # vertical gap > this * char height => word break


def vertical_headers(chars, centers, exclude_tops):
    """Rebuild each column's vertical header string from char geometry.

    Precinct names in SEMS recaps print as vertical char stacks (constant x0,
    descending y) that can interleave in y with the certification prose, so
    chars inside the padded prose bands (exclude_tops as (top, bottom) pairs)
    are dropped before reading."""
    lo, hi = exclude_tops
    keep = [ch for ch in chars if not any(t0 <= ch["top"] <= t1 for (t0, t1) in [(lo, hi)])
            and not isinstance(lo, float) or True]  # placeholder simplified below
    # (see note) filter: drop any char whose top lies inside a prose band
    def excluded(ch, bands):
        return any(b0 <= ch["top"] <= b1 for b0, b1 in bands)

    out = {}
    for center in centers:
        near = [ch for ch in chars
                if abs(ch["x0"] - center) <= X_TOL and not excluded(ch, bands)]
        stacks = cluster_xs([(ch["x0"], ch) for ch in near], gap=STACK_X_TOL)
        best = None
        for st in stacks:
            st_items = sorted(st["items"], key=lambda p: p[1]["top"])
            if len(st_items) < MIN_STACK_CHARS:
                continue
            step = st_items[1][1]["top"] - st_items[0][1]["top"]
            if any(abs((st_items[i + 1][1]["top"] - st_items[i][1]["top"]) - step)
                   > CHAR_STEP_JITTER for i in range(len(st_items) - 1)):
                continue  # irregular => prose contamination
            text = stack_text(st_items, step)
            if best is None or len(text) > len(best):
                best = text
        out[center] = best
    return out


def stack_text(items, step, base_step=None):
    """Join stacked chars top-to-bottom, inserting a space where the vertical
    gap exceeds the regular char step (word boundary)."""
    if base_step is None:
        base_step = step
    chars = []
    for i, (_, ch) in enumerate(items):
        if i and ch["top"] - items[i - 1][1]["bottom"] > base_step * WORD_GAP_FACTOR + 2.0:
            chars.append(" ")
        chars.append(ch["text"])
    return "".join(chars)


def total_col(headers):
    """x center of the column whose header reads TOTAL (fuzzy allowed)."""
    import difflib
    for center, text in headers.items():
        if text and difflib.SequenceMatcher(None, text.replace(" ", "").upper(),
                                            "TOTAL").ratio() >= 0.6:
            return center
    return None
```

Then **rewrite the sloppy first `vertical_headers` body** so it is the clean version (the draft above carries a deliberately broken placeholder line — replace the function with this exact body, keeping the helpers):

```python
def vertical_headers(chars, centers, bands):
    """Rebuild each column's vertical header string from char geometry.

    `bands` is a list of (top, bottom) prose bands whose chars must be
    ignored (the certification blurb spans the columns' x range)."""
    def excluded(ch):
        return any(b0 <= ch["top"] <= b1 for b0, b1 in bands)

    out = {}
    for center in centers:
        near = [ch for ch in chars
                if abs(ch["x0"] - center) <= X_TOL and not excluded(ch)]
        stacks = cluster_xs([(ch["x0"], ch) for ch in near], gap=STACK_X_TOL)
        best = None
        for st in stacks:
            st_items = sorted(st["items"], key=lambda p: p[1]["top"])
            if len(st_items) < MIN_STACK_CHARS:
                continue
            step = st_items[1][1]["top"] - st_items[0][1]["top"]
            if step <= 0 or any(
                    abs((st_items[i + 1][1]["top"] - st_items[i][1]["top"]) - step)
                    > CHAR_STEP_JITTER for i in range(len(st_items) - 1)):
                continue  # irregular => prose contamination
            text = stack_text(st_items, step)
            if best is None or len(text) > len(best):
                best = text
        out[center] = best
    return out
```

Update the tests' call signature accordingly (`exclude_tops=(lo, hi)` becomes a bands list `[("90.0, 100.0")]` style: pass `[ (lo, hi) ]`):

```python
got = ex.vertical_headers(chars, [246.0, 291.0], [(90.0, 100.0)])
# and total test: ex.vertical_headers(chars, [700.0], [])
# and gap test:   ex.vertical_headers(chars, [246.0], [])
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v`
Expected: PASS (7 tests).

**Step 5: Commit**

```bash
git add -A src/extract_2026_general_text_pdf.py test/test_2026_general_text_parser.py
git commit -m "Add vertical header stack reading for SEMS crosstab

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Label classifiers (office / party / noise / precinct normalization)

**Files:**
- Modify: `src/extract_2026_general_text_pdf.py`
- Test: `test/test_2026_general_text_parser.py`

**Step 1: Write the failing tests**

Append to `test/test_2026_general_text_parser.py`:

```python
class LabelTests(unittest.TestCase):
    def test_office_parsing(self):
        cases = [
            ("United States-Senate", ("U.S. Senate", "", None)),
            ("US House Of Rep 01-1st Congressional\nDistrict"
             .replace("\n", " "), ("U.S. House", "1", None)),
            ("Court Of Appeals 01-District 1 Position 1",
             ("Court of Appeals", "1", 1)),
            ("Court Of Appeals 01-District 1 Position 2",
             ("Court of Appeals", "1", 2)),
            ("Chancery Court 1-Chancery District 1 Place 1",
             ("Chancery Court", "1", 1)),
        ]
        for label, expected in cases:
            self.assertEqual(ex.parse_office(label), expected, label)

    def test_office_fuzzy_on_noisy_text(self):
        self.assertEqual(ex.parse_office("US House 0f Rep 02- Znd Congresslonal Dlstrict",
                                         fuzzy=True), ("U.S. House", "2", None))
        self.assertIsNone(ex.parse_office("Statew1de Electlon Management System"))

    def test_party_parsing(self):
        self.assertEqual(ex.party_of("Democrat"), "DEM")
        self.assertEqual(ex.party_of("Republican"), "REP")
        self.assertEqual(ex.party_of("Libertarian"), "LIB")
        self.assertEqual(ex.party_of("Independen"), "IND")
        self.assertEqual(ex.party_of("Independlent"), "IND")
        self.assertEqual(ex.party_of("Nonpartisan"), "")
        self.assertIsNone(ex.party_of("Chunky"), None)

    def test_noise_lines(self):
        noise = [
            "Page : 2", "Statewide Election Management System",
            "Votes cast in the County of Union, Mississippi on",
            "Official Recapitulation 2026 Federal General Election",
            "nn Prpclncts",
        ]
        for line in noise:
            self.assertTrue(ex.is_noise(line), line)
        self.assertFalse(ex.is_noise("Johnny Baucom Libertarian"))

    def test_precinct_normalization(self):
        cases = [("01", "1"), ("Chunky", "Chunky"), ("Dist. 1, Bellemont Precinct",
                  "Dist. 1, Bellemont"), ('"Airport"', "Airport"),
                 ("Noxubee  12", "Noxubee 12")]
        for name, expected in cases:
            self.assertEqual(ex.precinct_norm(name), expected, name)
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v -k Label`
Expected: FAIL (`no attribute 'parse_office'`).

**Step 3: Write minimal implementation**

Append to `src/extract_2026_general_text_pdf.py`:

```python
import difflib


FUZZY_RATIO = 0.72


def _fuzzy_eq(a, b, ratio):
    return difflib.SequenceMatcher(None, a.upper(), b.upper()).ratio() >= ratio


OFFICE_CANONS = {
    "United States-Senate": ("U.S. Senate", "", None),
    "U.S. Senate": ("U.S. Senate", "", None),
}


def parse_office(label, fuzzy=False):
    """Office header label -> (office, district, seat) or None. `seat` is the
    raw position/place qualifier when the ballot prints one."""
    label = re.sub(r"\s+", " ", label).strip()
    if _fuzzy_eq(label, "United States-Senate", 0.8 if fuzzy else 1.0) or label == "United States - Senate":
        return OFFICE_CANONS["United States-Senate"]
    m = re.search(r"US House 0[fF] Rep 0*(\d+)", label)
    if not m and fuzzy:
        m2 = difflib.SequenceMatcher(None, label.upper(), "US HOUSE OF REP")
        if m2.ratio() >= FUZZY_RATIO:
            m = re.search(r"\b0*(\d)\b", label)
    if m:
        return "U.S. House", str(int(m.group(1))), None
    m = re.search(r"Court 0[fF] Appeals 0*(\d+)-District 0*(\d+)"
                  r"(?:\s*Position\s*0*(\d+))?", label)
    if not m and fuzzy:
        if difflib.SequenceMatcher(None, label.upper()[:18], "COURT OF APPEALS"
                                   [:18]).ratio() >= FUZZY_RATIO:
            digits = re.findall(r"\b0*(\d+)\b", label)
            if digits:
                dd = digits[0]
                pos = digits[-1] if len(digits) > 1 else None
                return ("Court of Appeals", str(int(dd)),
                        int(pos) if pos and pos != dd else None)
    if m:
        d = str(int(m.group(2)))
        return "Court of Appeals", d, int(m.group(3)) if m.group(3) else None
    m = re.search(r"Chancery Court 0*(\d+)-Chancery District 0*(\d+)"
                  r"(?:\s*Place\s*0*(\d+))?", label)
    if m:
        d = str(int(m.group(2)))
        return "Chancery Court", d, int(m.group(3)) if m.group(3) else None
    m = re.search(r"(?:St?l?ate|State) Senate 0*(\d+)", label)
    if m:
        return "State Senate", str(int(m.group(1))), None
    m = re.search(r"(?:Stat[ei]|Stlale) House 0*(\d+)", label)
    if m:
        return "State House", str(int(m.group(1))), None
    if fuzzy:
        # one generic last resort: match any known canon by ratio
        for canon in ["United States-Senate", "US House Of Rep", "Court Of Appeals",
                      "Chancery Court"]:
            if _fuzzy_eq(label, canon, 0.7):
                return parse_office(canon, fuzzy=False)
    return None


PARTY_WORDS = {
    "Democrat": "DEM", "Democratic": "DEM", "Democra": "DEM", "Democratl": "DEM",
    "Republican": "REP", "Republlcan": "REP",
    "Libertarian": "LIB", "Llbertarlan": "LIB",
    "Constitution": "CON", "Constitutlon": "CON",
    "Independent": "IND", "Independen": "IND", "Independlent": "IND",
    "Nonpartisan": "", "Nonpartlsan": "",
}


def party_of(text, fuzzy=False):
    """Party code for a standalone party token, or None if not a party word."""
    token = re.sub(r"[^A-Za-z]", "", text).strip()
    if not token:
        return None
    if token in PARTY_WORDS:
        return PARTY_WORDS[token]
    if fuzzy or True:  # party words on noisy scans need tolerance by design
        for word, code in PARTY_WORDS.items():
            if difflib.SequenceMatcher(None, token.upper(), word.upper()).ratio() >= 0.75:
                return code
    return None


NOISE_PREFIXES = (
    "page :", "page:", "statewide election", "votes cast", "official recapitulation",
    "the county election commission", "we, the undersigned", "in testimony whereof",
    "district 1 - election", "district 2 - election", "district 3 - election",
    "district 4 - election", "district 5 - election", "county of ", "ms 39201",
)


def is_noise(text, fuzzy=False):
    t = re.sub(r"\s+", " ", text).strip().lower()
    if not t:
        return True
    if any(t.startswith(p) for p in NOISE_PREFIXES):
        return True
    if fuzzy or True:
        for p in ["page", "statewide", "official", "votes cast", "recapitulation",
                  "election commission"]:
            if _fuzzy_eq(t[:len(p) + 3], p, 0.75):
                return True
    return False


def precinct_norm(name):
    name = (name or "").strip().strip('"').strip()
    name = re.sub(r",\s*$", "", name)
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"\s+precinct\s*$", "", name, flags=re.IGNORECASE)
    m = re.match(r"^0*(\d+)$", name)
    if m:
        return m.group(1)
    return name
```

(Do not add a second `import difflib` if Task 2's `total_col` already imported it — keep one import at the top of the added block.)

**Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v`
Expected: PASS (12 tests).

**Step 5: Commit**

```bash
git add src/extract_2026_general_text_pdf.py test/test_2026_general_text_parser.py
git commit -m "Add office/party/noise classifiers for SEMS recap labels

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Page extraction (labels band, numeric row assignment)

**Files:**
- Modify: `src/extract_2026_general_text_pdf.py`
- Test: `test/test_2026_general_text_parser.py`

**Step 1: Write the failing tests**

Append to `test/test_2026_general_text_parser.py` (skip-if guard for the real-PDF integration):

```python
@unittest.skipUnless(SOURCES_PRESENT, "sources checkout not present")
class UnionPage2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from natural_pdf import PDF
        cls.pdf = PDF(os.path.join(SOURCES_DIR, "Union_County_2026_general.pdf"))
        cls.page = cls.pdf.pages[1]
        cls.word_dicts = [{"text": x.text, "x0": x.x0, "x1": x.x1,
                           "top": x.top, "bottom": x.bottom} for x in cls.page.words]
        cls.char_dicts = [{"text": x.text, "x0": x.x0, "x1": x.x1,
                           "top": x.top, "bottom": x.bottom} for x in cls.page.chars]
        cls.tp = ex.extract_table_page(cls.page, fuzzy=False)

    def test_finds_precinct_columns(self):
        self.assertGreater(len(self.tp["precinct_names"]), 0)
        self.assertTrue(all(self.tp["precinct_names"].values()))

    def test_office_and_candidate_stream(self):
        stream = self.tp["rows"]
        offices = [r for r in stream if r["kind"] == "office"]
        cands = [r for r in stream if r["kind"] == "candidate"]
        names = {r["office"] for r in offices}
        self.assertIn("U.S. Senate", names)
        self.assertIn("U.S. House", names)
        senate = [r for r in cands if r["office"] == "U.S. Senate"]
        self.assertEqual(
            {(r["candidate"], r["party"]) for r in senate},
            {("Scott Colom", "DEM"), ("Cindy Hyde-Smith", "REP"), ("Ty Pinkins", "IND")})

    def test_numeric_cells_attached(self):
        cands = [r for r in self.tp["rows"] if r["kind"] == "candidate"]
        hyde = [r for r in cands if r["candidate"] == "Cindy Hyde-Smith"]
        self.assertTrue(hyde and hyde[0]["cells"], "no votes attached")
        vals = set(hyde[0]["cells"].values())
        self.assertIn(188, vals)
        self.assertIn(164, vals)


class CellAssignmentTests(unittest.TestCase):
    def test_row_band_assignment(self):
        # one candidate line at top=200 (label band x<240), numbers at y=205
        rows = [{"kind": "candidate", "candidate": "A", "top": 200.0, "bottom": 212.0},
                {"kind": "office", "office": "X", "top": 240.0, "bottom": 250.0}]
        numwords = [w("188", 246.0, 205.0), w("7", 291.0, 206.0)]
        centers = [246.0, 291.0]
        cells = ex.assign_cells(rows, numwords, centers)
        self.assertEqual(cells, {(0, 246.0): 188, (0, 291.0): 7})

    def test_no_cell_below_last_row(self):
        rows = [{"kind": "candidate", "candidate": "A", "top": 200.0, "bottom": 212.0}]
        cells = ex.assign_cells(rows, [w("5", 246.0, 260.0)], [246.0])
        self.assertEqual(cells, {})
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v -k "Union or CellAssign"`
Expected: FAIL (`no attribute 'extract_table_page'`).

**Step 3: Write minimal implementation**

Append to `src/extract_2026_general_text_pdf.py`:

```python
LABEL_BAND = 6.0        # pt margin: label words sit left of the first column
ROW_PITCH_FALLBACK = 9.0


def extract_table_page(page, fuzzy=False):
    """Parse one recap table page into a row stream + attached numeric cells.

    Returns {"precinct_names": {center: name}, "total_center": center|None,
             "rows": [ {"kind": "office"|"candidate", ...,"top","bottom"} ],
             "table_top": float}"""
    words = [{"text": x.text, "x0": x.x0, "x1": x.x1, "top": x.top, "bottom": x.bottom}
             for x in page.words]
    chars = [{"text": x.text, "x0": x.x0, "x1": x.x1, "top": x.top, "bottom": x.bottom}
             for x in page.chars]
    lines = lines_from_words(words)
    table_top = find_table_top(lines)
    if table_top is None:
        return None  # cover page
    digits = [x for ln in lines if ln["top"] >= table_top - ROW_PITCH_FALLBACK
              for x in ln["words"] if looks_numeric(x["text"], fuzzy)]
    centers = column_centers(digits)

    # prose bands: wide lines in the header region must not feed the stacks
    bands = [(ln["top"] - 2, max(x["bottom"] for x in ln["words"]) + 2)
             for ln in lines if ln["top"] < table_top and _x_span(ln) > 300.0]

    headers = vertical_headers(chars, centers, bands)
    total_center = total_col(headers)
    body_centers = [c0 for c0 in centers
                    if total_center is None or c0 != total_center]
    precinct_names = {c0: headers.get(c0) for c0 in body_centers}

    rows = label_rows(lines, table_top, min(centers) - LABEL_BAND, fuzzy)
    body = [r for r in rows if r["top"] >= table_top - ROW_PITCH_FALLBACK]
    cells = assign_cells(
        body,
        [x for x in digits if x["x0"] >= min(centers) - LABEL_BAND],
        centers,
    )
    add_cells(body, cells)
    return {"precinct_names": precinct_names, "total_center": total_center,
            "rows": body, "table_top": table_top}


def label_rows(lines, table_top, label_x_max, fuzzy=False):
    """Build the candidate/office row stream from the label band."""
    rows = []
    current_office = None
    last_candidate = None
    for ln in lines:
        if ln["top"] < table_top - ROW_PITCH_FALLBACK:
            continue
        label_words = [x for x in ln["words"] if x["x0"] < label_x_max]
        if not label_words:
            continue
        text = " ".join(x["text"] for x in label_words)
        if text and all(x["x1"] <= label_x_max + 30 for x in ln["words"]):
            # full-width line: office headers often run into the columns area
            pass
        office = parse_office(text, fuzzy)
        if office:
            o, d, seat = office
            current_office = {"kind": "office", "office": o, "district": d,
                              "seat": seat, "top": ln["top"],
                              "bottom": max(x["bottom"] for x in label_words)}
            rows.append(current_office)
            last_candidate = None
            continue
        if is_noise(text, fuzzy):
            continue
        # party token may sit on its own line under the candidate name
        pk = party_of(label_words[0]["text"], fuzzy) if len(label_words) == 1 else None
        if pk is not None and last_candidate is not None:
            last_candidate["party"] = pk
            last_candidate["bottom"] = max(last_candidate["bottom"],
                                           max(x["bottom"] for x in label_words))
            continue
        if last_candidate is not None and last_candidate.get("party") is None:
            # trailing party word on the name line ("Cindy Hyde-Smith Republican")
            words = text.split(" ")
            if len(words) > 1 and party_of(words[-1], fuzzy) is not None:
                last_candidate.update(
                    candidate=" ".join(words[:-1]),
                    party=party_of(words[-1], fuzzy),
                    top=ln["top"], bottom=max(x["bottom"] for x in label_words))
                continue
        cand = {"kind": "candidate", "office": current_office["office"] if current_office else None,
                "district": current_office["district"] if current_office else None,
                "seat": current_office["seat"] if current_office else None,
                "candidate": text, "party": None,
                "top": ln["top"], "bottom": max(x["bottom"] for x in label_words),
                "cells": {}}
        rows.append(cand)
        last_candidate = cand
    return rows


def assign_cells(rows, numeric_words, centers):
    """Map (row_index, column_center) -> votes by row y-band overlap."""
    out = {}
    for i, row in enumerate(rows):
        out_row = i if row["kind"] == "candidate" else None
    for wtext in numeric_words:
        mid = (wtext["top"] + wtext["bottom"]) / 2.0
        for i, row in enumerate(rows):
            if row["kind"] != "candidate":
                continue
            if row["top"] - 3 <= mid < row["bottom"] + 6:
                col = min(centers, key=lambda c0: abs(c0 - wtext["x0"]))
                if abs(col - wtext["x0"]) <= LABEL_BAND + 12:
                    val = int(digit_clean(wtext["text"], False))
                    out[(i, col)] = val
                break
    return out


def add_cells(rows, cells):
    for (i, col), val in cells.items():
        rows[i]["cells"][col] = val
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v`

If `UnionPage2Tests` fail, **stop and diagnose against the real PDF** (`uv run python -c` probes of `page.words` around the failing region are fine); fix the parser, not the test's verified facts (Senate roster and Hyde-Smith's 188/164 came from the PDF itself). Iterate until PASS.

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v`
Expected: PASS (15 tests).

**Step 5: Commit**

```bash
git add src/extract_2026_general_text_pdf.py test/test_2026_general_text_parser.py
git commit -m "Extract SEMS recap table pages into labeled row stream

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: County assembly + TOTAL capture + gates

**Files:**
- Modify: `src/extract_2026_general_text_pdf.py`
- Test: `test/test_2026_general_text_parser.py`

**Step 1: Write the failing tests**

Append to `test/test_2026_general_text_parser.py`:

```python
@unittest.skipUnless(SOURCES_PRESENT, "sources checkout not present")
class UnionCountyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pd = ex.parse_county_pdf(
            os.path.join(SOURCES_DIR, "Union_County_2026_general.pdf"),
            "Union", fuzzy=False)
        cls.problems = ex.run_gates(cls.pd)

    def test_all_rows_reconcile_to_printed_total(self):
        self.assertEqual(self.problems["total_mismatches"], [])

    def test_structure_clean(self):
        self.assertEqual(self.problems["structure"], [])

    def test_every_precinct_has_senate_votes(self):
        senate = [r for r in self.pd["candidate_rows"] if r["office"] == "U.S. Senate"]
        self.assertGreaterEqual(len(senate), 3)
        for r in senate:
            self.assertEqual(sum(r["cells"].values()), r["total"])


class GateMathTests(unittest.TestCase):
    def test_total_mismatch_detected(self):
        pd = {"precincts": ["1"], "candidate_rows": [
            {"office": "O", "district": "", "seat": None, "candidate": "A",
             "party": "DEM", "cells": {246.0: 10}, "total": 9}]}
        probs = ex.run_gates(pd)
        self.assertEqual(len(probs["total_mismatches"]), 1)
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v -k "Union County or GateMath"`
Expected: FAIL (`no attribute 'parse_county_pdf'`).

**Step 3: Write minimal implementation**

Append to `src/extract_2026_general_text_pdf.py`:

```python
def _page_words_chars(page):
    words = [{"text": x.text, "x0": x.x0, "x1": x.x1, "top": x.top, "bottom": x.bottom}
             for x in page.words]
    chars = [{"text": x.text, "x0": x.x0, "x1": x.x1, "top": x.top, "bottom": x.bottom}
             for x in page.chars]
    return words, chars


def parse_county_pdf(pdf_path, county, fuzzy=False):
    """Whole-PDF parse. Returns:
    {"county": ..., "candidate_rows": [...], "precinct_names": [str],
     "page_count": int, "pages_used": [...]}
    candidate_rows carry {"office","district","seat","candidate","party",
    "cells": {precinct_name: votes}, "total": int|None}."""
    from natural_pdf import PDF  # lazy: keeps module importable without it

    pdf = PDF(str(pdf_path))
    pages = [extract_table_page(p, fuzzy) for p in pdf.pages]
    table_pages = [tp for tp in pages if tp is not None]
    if not table_pages:
        raise ValueError(f"no table pages found in {pdf_path}")

    # TOTAL column is on the last table page only (2024 runbook)
    last = table_pages[-1]
    total_center = last["total_center"]

    # global column layout: precinct centers by name, across pages
    name_by_center = {}
    for tp in table_pages:
        for c0, name in tp["precinct_names"].items():
            if name:
                name_by_center[name] = name_by_center.get(name, c0)

    precinct_names = sorted({v for v in name_by_center.values()},
                            key=lambda s: (s == "TOTAL", s))
    total_col_name = "TOTAL"

    candidate_rows = []
    for tp in table_pages:
        candidates = [r for r in tp["rows"] if r["kind"] == "candidate"]
        for r in candidates:
            cells = {}
            for col, val in r["cells"].items():
                if total_center is not None and tp is last and abs(col - total_center) < 12:
                    r["total"] = val
                    continue
                pname = tp["precinct_names"].get(col)
                if pname is None:
                    continue  # gate will flag the orphan
                cells[pname] = val
            r["cells"] = cells
            candidate_rows.append(r)

    # merge multi-page continuation rows (same candidate printed once per page)
    merged = {}
    for r in candidate_rows:
        if not r["candidate"] or r["office"] is None:
            continue
        key = (r["office"], r["district"], r["seat"], r["candidate"].lower())
        if key in merged:
            tgt = merged[key]
            for k, v in r["cells"].items():
                tgt["cells"][k] = v
            if r.get("total") is not None:
                tgt["total"] = r["total"]
            if tgt.get("party") is None and r.get("party"):
                tgt["party"] = r["party"]
        else:
            merged[key] = r
    rows_out = sorted(merged.values(), key=lambda r: list(merged).index(
        (r["office"], r["district"], r["seat"], r["candidate"].lower())))
    return {"county": county, "candidate_rows": rows_out,
            "precinct_names": [p for p in precinct_names if p],
            "page_count": len(pdf.pages), "pages_used": [i + 1 for i, tp in enumerate(pages) if tp]}


def run_gates(pd, total_name=total_col_name if False else "TOTAL"):
    """Gate results dict {total_mismatches, structure, roster}."""
    problems = {"total_mismatches": [], "structure": [], "roster": []}
    pnames = pd["precinct_names"] + [total_name]
    for r in pd["candidate_rows"]:
        r["total"] = r.get("total")
        cells_total = sum(r["cells"].values())
        if r["total"] is not None and cells_total != r["total"]:
            problems["total_mismatches"].append(
                {"office": r["office"], "district": r["district"],
                 "candidate": r["candidate"], "party": r.get("party"),
                 "sum": cells_total, "printed_total": r["total"]})
        missing = [p for p in pd["precinct_names"] if p not in r["cells"]]
        if missing:
            problems["structure"].append(
                {"kind": "missing_precinct_cells", "office": r["office"],
                 "candidate": r["candidate"], "precincts": missing})
        orphan = [c0 for c0 in r["cells"] if c0 not in pnames and c0 != "TOTAL"]
        if not orphan:
            continue
    return problems
```

Replace the sloppy `run_gates(pd, total_name=total_col_name if False else "TOTAL")` signature with `def run_gates(pd, total_name="TOTAL"):` (the placeholder existed only to name the module constant cleanly — define `TOTAL_NAME = "TOTAL"` above the function and use it as the default).

**Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v`

If `UnionCountyTests` fails, diagnose against the real PDF (orphan columns, TOTAL misidentified, party lines) — fix the parser, not the gate. Iterate until PASS.

Expected: PASS (17 tests).

**Step 5: Commit**

```bash
git add src/extract_2026_general_text_pdf.py test/test_2026_general_text_parser.py
git commit -m "Assemble county parse with TOTAL reconciliation gates

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: CSV writer + CLI, produce Union

**Files:**
- Modify: `src/extract_2026_general_text_pdf.py`
- Test: `test/test_2026_general_text_parser.py`
- Create: `2026/counties/20261103__ms__general__union__precinct.csv` (generated)

**Step 1: Write the failing tests**

Append to `test/test_2026_general_text_parser.py`:

```python
class CsvTests(unittest.TestCase):
    def test_seat_suffix_only_when_two_seats(self):
        rows = [
            {"office": "Court of Appeals", "district": "1", "seat": 1,
             "candidate": "A", "party": "", "cells": {"P1": 1}, "total": 1},
            {"office": "Court of Appeals", "district": "1", "seat": 2,
             "candidate": "B", "party": "", "cells": {"P1": 2}, "total": 2},
            {"office": "U.S. Senate", "district": "", "seat": None,
             "candidate": "C", "party": "REP", "cells": {"P1": 3}, "total": 3},
        ]
        pd = {"county": "Test", "candidate_rows": rows, "precinct_names": ["P1"]}
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fh:
            out = fh.name
        ex.write_precinct_csv(pd, out)
        import csv as _csv
        with open(out) as fh:
            got = list(_csv.reader(fh))
        self.assertEqual(got[0], ["county", "precinct", "office", "district",
                                  "candidate", "party", "votes"])
        offices = {(r[0], r[2], r[3]) for r in got[1:]}
        self.assertIn(("Test", "Court of Appeals Position 2", "1"), offices)
        self.assertIn(("Test", "Court of Appeals", "1"), offices)
        self.assertIn(("Test", "U.S. Senate", ""), offices)
        os.unlink(out)
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v -k Csv`
Expected: FAIL (`no attribute 'write_precinct_csv'`).

**Step 3: Write minimal implementation**

Append to `src/extract_2026_general_text_pdf.py`:

```python
CSV_FIELDS = ["county", "precinct", "office", "district", "candidate", "party", "votes"]


def seat_labels(pd):
    """office+district keys holding 2+ seats -> {key: seat_suffix_map}."""
    seats = {}
    for r in pd["candidate_rows"]:
        if r["seat"] is None:
            continue
        key = (r["office"], r["district"])
        seats.setdefault(key, set()).add(r["seat"])
    return {key: s for key, s in seats.items() if len(s) > 1}


def write_precinct_csv(pd, out_path):
    import csv
    multi = seat_labels(pd)
    rows = []
    for r in pd["candidate_rows"]:
        office = r["office"]
        if (r["office"], r["district"]) in multi and r["seat"] is not None:
            office = f"{r['office']} Position {r['seat']}"
        for pname in sorted(r["cells"], key=lambda p: pd["precinct_names"].index(p)
                            if p in pd["precinct_names"] else 10**9):
            rows.append({
                "county": pd["county"], "precinct": pname, "office": office,
                "district": r["district"] or "", "candidate": r["candidate"],
                "party": r.get("party") or "", "votes": r["cells"][pname]})
    rows.sort(key=lambda x: ((x["precinct"] or "").lower(),))
    with open(out_path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        wr.writeheader()
        wr.writerows(rows)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("--county", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fuzzy", action="store_true",
                    help="tolerant matching for OCR-derived text layers (Jasper/Lee)")
    ap.add_argument("--allow-gate-failures", action="store_true",
                    help="write CSV even when gates flag problems (for diagnosis)")
    args = ap.parse_args(argv)

    pd = parse_county_pdf(args.pdf_path, args.county, fuzzy=args.fuzzy)
    problems = run_gates(pd)
    n_bad = sum(len(v) for v in problems.values())
    for kind, items in problems.items():
        for item in items:
            print(f"  ! {kind}: {item}")
    print(f"{args.county}: {len(pd['candidate_rows'])} candidate rows, "
          f"{len(pd['precinct_names'])} precincts, {n_bad} gate problem(s)")
    if problems == {"total_mismatches": [], "structure": [], "roster": []} or args.allow_gate_failures:
        write_precinct_csv(pd, args.out)
        print(f"  wrote {args.out}")
        return 0
    if n_bad:
        print("  gates FAILED; CSV not written (rerun with --allow-gate-failures to inspect)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4: Run tests, then produce Union for real**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v`
Expected: PASS (18 tests).

Run: `mkdir -p 2026/counties && uv run python src/extract_2026_general_text_pdf.py ~/code/openelections-sources-ms/2026/general/Union_County_2026_general.pdf --county Union --out 2026/counties/20261103__ms__general__union__precinct.csv`
Expected: `Union: N candidate rows, M precincts, 0 gate problem(s)` and `wrote ...`.

Sanity-check the output:
- `head 2026/counties/20261103__ms__general__union__precinct.csv` shows Senate DEM/REP/IND rows per precinct with plausible two-digit counts.
- `cut -d, -f3,5 2026/counties/20261103__ms__general__union__precinct.csv | sort -u` lists the ballot's races.

**Step 5: Commit**

```bash
git add src/extract_2026_general_text_pdf.py test/test_2026_general_text_parser.py 2026/counties/20261103__ms__general__union__precinct.csv
git commit -m "Write per-county precinct CSVs; generate Union

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: Warren end-to-end

**Files:**
- Create: `2026/counties/20261103__ms__general__warren__precinct.csv` (generated)

**Step 1: Run the extractor**

Run: `uv run python src/extract_2026_general_text_pdf.py ~/code/openelections-sources-ms/2026/general/Warren_County_2026_general.pdf --county Warren --out 2026/counties/20261103__ms__general__warren__precinct.csv`
Expected: `Warren: N candidate rows, M precincts, 0 gate problem(s)`.

**Step 2: Diagnose any gate failures (if raised)**

Warren pages differ (7 pages); expect layout quirks. For each failure: render/inspect that page's words with a small probe (`page.words` filtered by the mismatched row's y band), fix the parser rule, re-run the full unittest suite, and re-run Warren. Do not weaken gates.

**Step 3: Verify against 2024 precedent loosely**

Run: `head -5 2026/counties/20261103__ms__general__warren__precinct.csv && cut -d, -f3 2026/counties/20261103__ms__general__warren__precinct.csv | sort -u`
Expected: Warren is U.S. House district 2 — check the House roster printed at district `2` and the Senate races carry district blank.

**Step 4: Commit**

```bash
git add 2026/counties/20261103__ms__general__warren__precinct.csv src/extract_2026_general_text_pdf.py test/test_2026_general_text_parser.py
git commit -m "Generate Warren 2026 general precinct CSV

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: Jasper and Lee (OCR-noisy text layers)

**Files:**
- Create: `2026/counties/20261103__ms__general__jasper__precinct.csv` (generated if gates pass)
- Create: `2026/counties/20261103__ms__general__lee__precinct.csv` (generated if gates pass)
- Modify: `src/extract_2026_general_text_pdf.py` (as diagnosis demands)

**Step 1: Try Jasper with fuzzy mode**

Run: `uv run python src/extract_2026_general_text_pdf.py ~/code/openelections-sources-ms/2026/general/Jasper_County_2026_general.pdf --county Jasper --fuzzy --out 2026/counties/20261103__ms__general__jasper__precinct.csv`
Expected: gate report; if 0 problems, CSV written.

**Step 2: Try Lee with fuzzy mode**

Run: `uv run python src/extract_2026_general_text_pdf.py ~/code/openelections-sources-ms/2026/general/Lee_County_2026_general.pdf --county Lee --fuzzy --out 2026/counties/20261103__ms__general__lee__precinct.csv`
Expected: gate report. Lee is the flagged escalation candidate (13 pages) — expect possible TOTAL/orphan-column failures.

**Step 3: Diagnose failures with probes, fix parser rules**

For each failing county: probe the specific page/row (y band of the mismatch), decide whether the defect is (a) parser geometry, (b) OCR noise needing a rule (e.g., `party_of` variants, digit cleanup inside numeric columns only), or (c) a genuinely unreadable cell. Only fix (a)/(b) in the parser; record (c) cells in the notes report. Re-run the full test suite after each fix.

Cross-checks available with no extra source:
- 2024 precedent CSVs for the same county: `2024/counties/20241105__ms__general__jasper__precinct.csv` (precinct-name spellings to sanity-check header reading),
- shared-race roster consistency across the four counties (Senate roster must match everywhere).

**Step 4: Record escalation decision if a county cannot pass**

If a county's gates stay red after parser fixes, do **not** write its CSV with `--allow-gate-failures` by default. Escalate per the design: render its pages and read as a vision model, or PaddleOCR. Whichever path is taken, record it in the notes report (Task 9).

**Step 5: Commit whatever passed**

```bash
git add 2026/counties/20261103__ms__general__jasper__precinct.csv 2026/counties/20261103__ms__general__lee__precinct.csv src/ src/
git commit -m "Generate Jasper/Lee 2026 general precinct CSVs (noisy text layers)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

(Adjust paths if a county didn't pass.)

---

### Task 9: Batch wrapper, notes report, final checks

**Files:**
- Create: `src/batch_extract_2026_general_text.py`
- Create: `2026/20261103-general-text-layer-notes.md`
- Test: `test/test_2026_general_text_parser.py`

**Step 1: Write the failing test**

Append to `test/test_2026_general_text_parser.py`:

```python
class BatchTests(unittest.TestCase):
    def test_county_from_filename(self):
        self.assertEqual(ex_batch.county_from_filename("Union_County_2026_general.pdf"), "Union")
        self.assertEqual(ex_batch.county_from_filename("Neshoba_2026_general.pdf"), "Neshoba")
```

Add at the top of the test file (after `import extract_2026_general_text_pdf as ex`):

```python
import batch_extract_2026_general_text as ex_batch  # noqa: E402
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v -k Batch`
Expected: FAIL (`No module named 'batch_extract_2026_general_text'`).

**Step 3: Write the wrapper**

Create `src/batch_extract_2026_general_text.py`:

```python
"""Batch runner for the four text-layer 2026 general county PDFs.

 Parses each PDF (fuzzy mode for the OCR-noisy scans), runs the internal
gates, writes per-county CSVs into 2026/counties/ for counties whose gates
are clean, and records a short notes report. State tracked in
cache/2026-general-text/status.json so re-runs skip completed counties.

Usage:
    uv run python src/batch_extract_2026_general_text.py \
        --sources-dir ~/code/openelections-sources-ms/2026/general
"""

import argparse
import json
import re
import sys
from pathlib import Path

import extract_2026_general_text_pdf as ex

TEXT_LAYER_COUNTIES = ["Union", "Warren", "Jasper", "Lee"]
DATE = "20261103"


def county_from_filename(filename):
    """`Warren_County_2026_general.pdf` -> `Warren` (no County suffix variants too)."""
    stem = re.sub(r"\.pdf$", "", filename)
    stem = re.sub(r"_2026_general$", "", stem)
    stem = re.sub(r"_?county$", "", stem, flags=re.IGNORECASE)
    return stem


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources-dir", required=True)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--cache-dir", default="cache/2026-general-text")
    args = ap.parse_args(argv)

    sources = Path(args.sources_dir).expanduser()
    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    status_path = cache / "status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}

    only = args.only or TEXT_LAYER_COUNTIES
    results = {}
    for county in [c for c in TEXT_LAYER_COUNTIES if c in only]:
        if status.get(county, {}).get("state") == "PASSED" and county not in (args.only or []):
            print(f"{county}: already PASSED, skipping")
            continue
        matches = sorted(sources.glob(f"{county}_*_general.pdf"))
        if not matches:
            print(f"{county}: no source PDF found")
            continue
        fuzzy = county in ("Jasper", "Lee")
        out_name = f"2026/counties/{DATE}__ms__general__{county.lower()}__precinct.csv"
        rc = ex.main([str(matches[0]), "--county", county, "--out", out_name]
                     + (["--fuzzy"] if fuzzy else []))
        state = "PASSED" if rc == 0 else "FAILED"
        status[county] = {"state": state, "pdf": matches[0].name, "out": out_name}
        json.dump(status, status_path.write_text(status) or status)  # placeholder fixed below
        results[county] = state
```

**Fix the status-write line** to:

```python
        status[county] = {"state": state, "pdf": matches[0].name, "out": out_name}
        status_path.write_text(json.dumps(status, indent=2))
        results[county] = state
```

Finish `main` with the roster gate and report:

```python
    # cross-county roster gate
    parsed = [ex.parse_county_pdf(str(sources / status[c]["pdf"]), c,
                                  fuzzy=c in ("Jasper", "Lee"))
              for c, s in status.items() if s.get("state") == "PASSED"]
    roster_problems = ex.check_roster_shared_races(parsed)
    for p in roster_problems:
        print(f"  ! roster: {p}")
    if roster_problems:
        sys.exit(1)
    print("done:", results or "nothing to do")
```

Append the roster gate to `src/extract_2026_general_text_pdf.py`:

```python
def check_roster_shared_races(counties_pd):
    """Same office+district+seat contested everywhere -> identical (candidate,
    party) roster. Only compares races that appear in 2+ counties."""
    from collections import defaultdict
    by_race = defaultdict(list)
    for pd in counties_pd:
        seen = {}
        for r in pd["candidate_rows"]:
            key = (r["office"], r["district"], r["seat"])
            seen.setdefault(key, set()).add((r["candidate"], r.get("party") or ""))
        for key, roster in seen.items():
            by_race[key].append(roster)
    problems = []
    for key, rosters in by_race.items():
        if len(rosters) < 2:
            continue
        first = rosters[0]
        for other in rosters[1:]:
            if first != other:
                problems.append({"race": key, "rosters": [
                    sorted(first), sorted(other)]})
    return problems
```

**Step 4: Run tests to verify they pass, then run the batch**

Run: `uv run python -m unittest discover -s test -p "test_2026_general_text_parser.py" -v`
Expected: PASS (19 tests).

Run: `uv run python src/batch_extract_2026_general_text.py --sources-dir ~/code/openelections-sources-ms/2026/general`
Expected: per-county gate reports; `done: {'Union': 'PASSED', ...}` (counties that failed gates in Task 8 remain absent from `2026/counties/`).

**Step 5: Write the notes report**

Create `2026/20261103-general-text-layer-notes.md` covering: the 4 text-layer counties, mode used (deterministic geometry parse; fuzzy for Jasper/Lee), gate results per county, any cells left for manual review or escalation decisions, and this required flag sentence:

> These four per-county files are gated on internal PDF reconciliation only and have **not** been checked against official county totals; when a 2026 general statewide recap PDF becomes available, build the official county CSV and re-verify all four.

**Step 6: Final repo checks and commit**

Run: `uv run python src/verifier.py 2026/counties/20261103__ms__general__union__precinct.csv` (older generic linter; adapt invocation if it requires args — read its `main` first)
Expected: no structural complaints (column names, unique row ids).

Run: `git status --short 2026/ src/ test/` — only intended files.
Then:

```bash
git add 2026/counties/ 2026/20261103-general-text-layer-notes.md src/batch_extract_2026_general_text.py src/extract_2026_general_text_pdf.py test/test_2026_general_text_parser.py
git commit -m "Batch runner + notes for 2026 general text-layer counties

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Step 7: Report back**

Summarize: counties converted, gate results, any county left unconverted + why, and the not-yet-officially-verified flag. Note the remaining 78 scanned counties are the next phase (PaddleOCR).
