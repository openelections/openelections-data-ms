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
import difflib  # SequenceMatcher fuzzy matching (TOTAL header, labels); stdlib only

DIGIT_RE = re.compile(r"^-?\d+$")

DIGIT_CLEANUP = str.maketrans(
    {"O": "0", "o": "0", "l": "1", "I": "1", "|": "1", "S": "5", "s": "5"}
)

# Adjacent-x gap threshold separating numeric columns: crosstab columns sit
# ~45pt apart, while right-alignment jitter within one column stays under it.
COLUMN_GAP = 20.0


def digit_clean(text, fuzzy):
    """Normalize a suspected numeric token. Only ever applied to tokens chosen
    because they sit in numeric columns -- never to label text."""
    t = text.strip().replace(",", "").replace(" ", "")
    if fuzzy:
        t = t.translate(DIGIT_CLEANUP)
    return t


def looks_numeric(text, fuzzy=False):
    return bool(DIGIT_RE.match(digit_clean(text, fuzzy)))


def lines_from_words(words, y_tol=3.0):
    """Group words into text lines by top coordinate; return list of
    {"top", "words": [word dicts sorted by x0], "text": " ".join}
    sorted by top.

    line["top"] is the anchor: the top of the first word the line absorbed
    (words are visited in (top, x0) order, so the smallest top in the line).
    Each later word joins only while within y_tol of that anchor, so a visual
    line whose word tops span more than y_tol intentionally splits.
    """
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

    Prose rejection relies on prose carrying fewer than min_columns numeric
    tokens; a numeric-dense prose line would be read as a false table top --
    a known limitation, relevant for the OCR-noisy counties.
    """
    for line in lines:
        nums = [wd for wd in line["words"] if looks_numeric(wd["text"])]
        xs = [wd["x0"] for wd in nums]
        clusters = cluster_xs([(x, None) for x in xs], gap=COLUMN_GAP)
        if len(nums) >= min_columns and len(clusters) >= min_columns:
            return line["top"]
    return None


def cluster_xs(pairs, gap=COLUMN_GAP):
    """Cluster (x, payload) pairs by x with adjacent-gap threshold `gap`.

    Input is sorted by x first, so clusters are returned in ascending x
    order. The threshold is single-linkage against the previous cluster's
    last item: a chain of points each within `gap` of its neighbor merges
    into one cluster, however far apart the chain's ends end up. Each
    cluster is {"center", "items"}, "center" the mean x of its items.
    """
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


def column_centers(digit_words, gap=COLUMN_GAP):
    """Distinct x0 centers of numeric columns, ascending."""
    clusters = cluster_xs([(wd["x0"], wd) for wd in digit_words], gap=gap)
    return sorted(cl["center"] for cl in clusters)


X_TOL = 6.0          # char x0 must sit within this of a column center
STACK_X_TOL = 2.5    # chars of one vertical stack share x0 this tightly
CHAR_STEP_JITTER = 2.0
# Single-glyph vertical headers (e.g. precinct "5") always refuse to None at
# this floor: one char cannot be told apart from stray noise. Deliberate
# precision/recall tradeoff.
MIN_STACK_CHARS = 2
# Accepted vertical gaps, measured against a stack's first inter-row step
# (`step`, so WORD_GAP_FACTOR is step-relative):
#   step - CHAR_STEP_JITTER <= gap <= step + CHAR_STEP_JITTER   (same rhythm)
#   step * (1 + WORD_GAP_FACTOR) < gap < inf                     (word break)
# Everything else-and-below is rejected -- most importantly the in-between
# window (step + jitter, step*(1+factor)] that a stray prose char produces.
WORD_GAP_FACTOR = 0.45


def vertical_headers(chars, centers, bands, max_top):
    """Rebuild each column's vertical header string from char geometry.

    Precinct names in SEMS recaps print as vertical char stacks (constant x0,
    descending y) that can interleave in y with the certification prose, so
    chars inside the (top, bottom) `bands` of wide prose lines are dropped
    before reading. `max_top` is the required header-region top bound (the
    table's top: what find_table_top returns): chars with top >= max_top --
    the body cells -- are dropped before reading, because body-cell digits
    share the column x and stack into rhythmic runs longer than any name,
    which best = longest would read as the header.

    Stack isolation is only ever as complete as the caller's exclusion
    bands: the reader rejects irregular gaps but accepts any gap above
    step * (1 + WORD_GAP_FACTOR) as a word break, so an unbanded prose char
    landing within X_TOL of a column center is silently appended as a
    "word". `bands` must cover every prose y-range that crosses a column.

    Returns {center: header string or None}."""
    def excluded(ch):
        return any(b0 <= ch["top"] <= b1 for b0, b1 in bands)

    out = {}
    for center in centers:
        near = [ch for ch in chars
                if ch["top"] < max_top
                and abs(ch["x0"] - center) <= X_TOL and not excluded(ch)]
        stacks = cluster_xs([(ch["x0"], ch) for ch in near], gap=STACK_X_TOL)
        best = None
        for st in stacks:
            st_items = sorted(st["items"], key=lambda p: p[1]["top"])
            if len(st_items) < MIN_STACK_CHARS:
                continue
            tops = [p[1]["top"] for p in st_items]
            # Chars kerned onto one top are a single row: measure the stack's
            # rhythm across distinct row tops only.
            gaps = [hi - lo for lo, hi in zip(tops, tops[1:]) if hi > lo]
            if not gaps:
                continue
            step = gaps[0]
            # Rows must descend at a uniform step (checked against the first
            # inter-char step); the one tolerated irregularity is a clear word
            # break (inter-word spacing, e.g. "Dist 1"). Anything between --
            # the signature of a stray prose char landing in the stack -- and
            # any smaller-than-step row disqualify the stack.
            word_break = step * (1 + WORD_GAP_FACTOR)
            if any(abs(gap - step) > CHAR_STEP_JITTER and gap <= word_break
                   for gap in gaps):
                continue  # irregular => prose contamination
            text = stack_text(st_items, step)
            if best is None or len(text) > len(best):
                best = text
        out[center] = best
    return out


def stack_text(items, step):
    """Join stacked chars top-to-bottom, inserting a space where the vertical
    gap between consecutive char tops exceeds step * (1 + WORD_GAP_FACTOR)
    (inter-word spacing).

    Precondition: `items` must be sorted by top ascending -- both the space
    decision and the reading order depend on it. The only caller
    (vertical_headers) sorts the stack's items by top before calling."""
    chars = []
    prev_top = None
    for _, ch in items:
        if prev_top is not None and ch["top"] - prev_top > step * (1 + WORD_GAP_FACTOR):
            chars.append(" ")
        chars.append(ch["text"])
        prev_top = ch["top"]
    return "".join(chars)


def total_col(headers):
    """x center of the column whose header reads TOTAL (fuzzy allowed).

    Every column is scored (SequenceMatcher ratio against "TOTAL", case and
    blank insensitive) and the best ratio at or above the 0.6 threshold
    wins; equal ratios tie-break to the smaller center. Scoring all columns
    instead of first-hit keeps the result independent of dict order and of a
    weak short match ("Tot", 0.75) beating a perfect one later in the dict."""
    best = None  # (ratio, center): ratio-maximal, center-minimal on ties
    for center, text in headers.items():
        if not text:
            continue
        ratio = difflib.SequenceMatcher(None, text.replace(" ", "").upper(),
                                        "TOTAL").ratio()
        if ratio < 0.6:
            continue
        if best is None or ratio > best[0] or (ratio == best[0] and center < best[1]):
            best = (ratio, center)
    return None if best is None else best[1]


def _fuzzy_eq(a, b, ratio):
    return difflib.SequenceMatcher(None, a.upper(), b.upper()).ratio() >= ratio


def parse_office(label, fuzzy=False):
    """Office header label -> (office, district, seat) or None.

    `seat` is the printed position/place qualifier when the ballot carries
    one (court-of-appeals positions, chancery places); None otherwise.
    U.S. Senate returns "" for district: the race is not districted, and ""
    (blank) is the repo convention for a race that carries no district --
    parse_2024_general_statewide.parse_office does the same. Fuzzy
    tolerance is for the OCR-derived text layers (Jasper/Lee), whose
    confusions look like "US House 0f Fep 02- Znd Congresslonal Dlstrlct"
    / "Court O Appeals 01-Dlstrlct 3 Posltlon 2".
    """
    label = re.sub(r"\s+", " ", label).strip()
    if (_fuzzy_eq(label, "United States-Senate", 0.8 if fuzzy else 1.0)
            or label == "United States - Senate"):
        return "U.S. Senate", "", None
    # The printed label says "Of" (letter O; Union p2) but the OCR-derived
    # layers render that word both ways: "of"/"Of" or "0f".
    m = re.search(r"US House [O0][fF] Rep 0*([1-9]\d*)", label)
    if not m and fuzzy and _fuzzy_eq(label[:17], "US HOUSE OF REP", 0.7):
        digits = re.findall(r"\b0*(\d)\b", label)
        if digits:
            return "U.S. House", str(int(digits[0])), None
    if m:
        return "U.S. House", str(int(m.group(1))), None
    m = re.search(r"Court [O0][fF] Appeals 0*(\d+)-District 0*(\d+)"
                  r"(?:\s*Position\s*0*(\d+))?", label)
    if not m and fuzzy and _fuzzy_eq(label[:18], "COURT OF APPEALS", 0.7):
        # Leading digit run is the district's place number ("01-"); the
        # District number follows, then an optional Position.
        digits = re.findall(r"\b(\d+)\b", label)
        if digits:
            district = digits[1] if len(digits) >= 2 else digits[0]
            seat = (int(digits[-1])
                    if len(digits) >= 2 and digits[-1] != digits[1] else None)
            return "Court of Appeals", str(int(district)), seat
    if m:
        d = str(int(m.group(2)))
        return "Court of Appeals", d, int(m.group(3)) if m.group(3) else None
    m = re.search(r"Chancery Court 0*(\d+)\s*-\s*Chancery District 0*(\d+)"
                  r"(?:\s*Place\s*0*(\d+))?", label)
    if not m and fuzzy and _fuzzy_eq(label[:15], "CHANCERY COURT", 0.7):
        digits = re.findall(r"\b(\d+)\b", label)
        if digits:
            district = digits[1] if len(digits) >= 2 else digits[0]
            place = (int(digits[-1])
                     if len(digits) >= 2 and digits[-1] != digits[1] else None)
            return "Chancery Court", str(int(district)), place
    if m:
        d = str(int(m.group(2)))
        return "Chancery Court", d, int(m.group(3)) if m.group(3) else None
    return None


# Party -> code map for standalone party tokens. "" is the Nonpartisan
# value (blank party per repo convention, parse_2024_general_statewide
# precedent); OCR-derived layers mangle the spelled words, hence the
# pre-mangled keys.
PARTY_WORDS = {
    "Democrat": "DEM", "Democratic": "DEM", "Democra": "DEM",
    "Republican": "REP", "Republlcan": "REP",
    "Libertarian": "LIB", "Llbertarlan": "LIB",
    "Constitution": "CON", "Constitutlon": "CON",
    "Independent": "IND", "Independen": "IND", "Independlent": "IND",
    "Nonpartisan": "", "Nonpartlsan": "",
}


def party_of(text, fuzzy=False):
    """Party code for a standalone party token, or None if not a party word.

    Returns a code ("DEM"/"REP"/"LIB"/"CON"/"IND"), "" when the token is a
    Nonpartisan one (blank party per repo convention), and None when the
    text is not a party word at all -- call sites must therefore test
    `is not None` and may not treat "" and None alike.

    The tolerant path is ALWAYS active (not gated on `fuzzy`): party tokens
    on the OCR-derived text layers are mangled the same way labels are, and
    a false positive here costs only a wrong party code caught later by the
    roster gate, while a missed party word would silently blank the column.
    """
    token = re.sub(r"[^A-Za-z]", "", text).strip()
    if not token:
        return None
    if token in PARTY_WORDS:
        return PARTY_WORDS[token]
    if len(token) <= 14:  # no party word is longer than 12 characters
        for word, code in PARTY_WORDS.items():
            if difflib.SequenceMatcher(None, token.upper(),
                                       word.upper()).ratio() >= 0.75:
                return code
    return None


NOISE_PREFIXES = (
    "page :", "page:", "statewide election", "votes cast", "official recapitulation",
    "the county election commission", "we, the undersigned", "in testimony whereof",
    "district 1 - election", "district 2 - election", "district 3 - election",
    "district 4 - election", "district 5 - election", "county of ", "ms 39201",
)


def is_noise(text, fuzzy=False):
    """True for certification-blurb lines and page furniture, False for
    candidate/office labels. Tolerant matching is always on (same rationale
    as party_of) but anchors on the line's leading few characters only, so a
    candidate named "Pages ..." does not match."""
    t = re.sub(r"\s+", " ", text).strip().lower()
    if not t:
        return True
    if any(t.startswith(p) for p in NOISE_PREFIXES):
        return True
    leading = t[:10]
    for p in ("page", "statewide", "official", "votes cast", "recapitulation",
              "election commission"):
        if difflib.SequenceMatcher(None, leading, p[:10].ljust(10)).ratio() >= 0.75:
            return True
    return False


def precinct_norm(name):
    """OpenElections precinct-name conventions: no 'Precinct' suffix, no
    leading zeros on pure numbered precincts, no surrounding quotes
    (straight or curly) or stray trailing commas/whitespace; internal
    content (including commas) is preserved."""
    name = (name or "").strip().strip('"“”').strip()
    name = re.sub(r"[,\s]+$", "", name)
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"\s+precinct\s*$", "", name, flags=re.IGNORECASE)
    m = re.match(r"^0*(\d+)$", name)
    if m:
        return m.group(1)
    return name


# ---- page extraction (recap table pages) --------------------------------
#
# Amendment A: header sourcing is an operator-vision job (Task 5). Nothing
# here reads precinct names out of geometry -- extract_table_page returns the
# detected column centers plus a labeled row stream with numeric cells keyed
# by column center, and a later stage binds centers to names.

LABEL_BAND = 6.0        # label words sit at least this far left of column 1
ROW_PITCH_FALLBACK = 9.0
COL_TOL = 18.0          # max |x0 - column center| for a cell to attach
MIN_CLUSTER_MEMBERS = 3  # drop 1-2-member x clusters (footer digits, noise)

# Qualifier words that may make up a wrapped office-header line ("US House Of
# Rep 01-1st Congressional" + "District"), with their digit runs ("01-1st").
# The vocabulary gate guards the continuation branch: the office regexes match
# by prefix, so merged text keeps parsing after candidate names are appended
# ("...Position 1 Derek Dewayne Hopson Jr. Nonpartisan" still matches the
# Court pattern). Proper noun tokens never gate-pass, so the first candidate
# row under a self-contained header is never swallowed.
WRAP_WORDS = ("district", "position", "place", "congressional", "court",
              "appeals", "chancery", "circuit")

# Invisible-Tesseract text-layer misreads of PRINTED candidate names, keyed on
# the observed mangle -- the same mechanism as PARTY_WORDS's mangled keys.
# Union's print says "Scott Colom" / "John Weddle" (verified against the
# rendered page; the OCR layer reads "Coiom" / "weddie"). Applied to label
# words only, never to numeric handling or office patterns.
LABEL_REPAIRS = {"Coiom": "Colom", "weddie": "Weddle"}


def _is_wrap_token(token, fuzzy=False):
    """True for a token that may appear on a wrapped office-label line:
    a qualifier word (exact or, for the mangled OCR layers, near-exact),
    a digit run, or a punctuation-only filler."""
    letters = re.sub(r"[^A-Za-z]", "", token).lower()
    if not letters:
        return True  # "-", ":" -- carries no name identity
    if re.search(r"\d", token):
        return True  # "01-1st", "3", "District 2"
    if letters in WRAP_WORDS:
        return True
    if len(letters) <= 14:
        return any(_fuzzy_eq(letters, word, 0.75) for word in WRAP_WORDS)
    return False


def grid_centers(digits, anchor_digits, min_members=MIN_CLUSTER_MEMBERS):
    """x centers of the crosstab columns among `digits`' x clusters.

    The table's first data line carries one cell in every column, so its own
    numeric tokens (`anchor_digits`) bound the grid's x span. A cluster is a
    real column when it has >= min_members members AND its x range overlaps
    that span. Office-header qualifier digits (Position/Place values, which
    print just right of the label band, x ~195-250 on Union p2) form two
    phantom ~45pt-pitch clusters left of the first column that overlap
    nothing on the first data line, so they drop without a special case."""
    if not digits or not anchor_digits:
        return []
    anchor_lo = min(x["x0"] for x in anchor_digits)
    anchor_hi = max(x["x0"] for x in anchor_digits)
    centers = []
    for cl in cluster_xs([(x["x0"], x) for x in digits], gap=COLUMN_GAP):
        if len(cl["items"]) < min_members:
            continue
        lo = min(x for x, _ in cl["items"])
        hi = max(x for x, _ in cl["items"])
        if hi >= anchor_lo and lo <= anchor_hi:
            centers.append(cl["center"])
    return sorted(centers)


def extract_table_page(page, fuzzy=False):
    """Parse one recap table page (Amendment A contract).

    Returns {"precinct_centers": [x...], "table_top": float, "rows": [...]}
    with rows = label_rows(...), each candidate row's "cells" filled from the
    numeric grid. Does NOT resolve header labels (the operator manifest does
    that in Task 5); does NOT call vertical_headers."""
    words = [{"text": x.text, "x0": x.x0, "x1": x.x1, "top": x.top, "bottom": x.bottom}
             for x in page.words]
    lines = lines_from_words(words)
    table_top = find_table_top(lines)
    if table_top is None:
        return None  # cover page

    def band_words(lo, hi):
        return [x for ln in lines if lo <= ln["top"] < hi for x in ln["words"]]

    digits = [x for x in band_words(table_top - ROW_PITCH_FALLBACK, float("inf"))
              if looks_numeric(x["text"], fuzzy)]
    # The first data line anchors the grid; a +-ROW_PITCH_FALLBACK window
    # keeps cells that y-jitter split onto a follow-on line inside the anchor.
    anchor_digits = [x for x in
                     band_words(table_top - ROW_PITCH_FALLBACK,
                                table_top + ROW_PITCH_FALLBACK)
                     if looks_numeric(x["text"], fuzzy)]
    centers = grid_centers(digits, anchor_digits)
    if not centers:
        return None  # numeric grid lost; caller treats the page as unused

    label_x_max = min(centers) - LABEL_BAND
    rows = label_rows(lines, table_top, label_x_max, fuzzy)
    cells = assign_cells(rows, [x for x in digits if x["x0"] >= label_x_max],
                         centers, fuzzy)
    for (r_idx, col), val in cells.items():
        rows[r_idx]["cells"][col] = val
    return {"precinct_centers": centers, "table_top": table_top, "rows": rows}


def label_rows(lines, table_top, label_x_max, fuzzy=False):
    """Build the candidate/office row stream from the label band.

    Lines strictly above `table_top` carry nothing but the section's office
    header: the certification blurb and vertical-name-stack fragments sit
    there too and parse as nothing, so any line above the first data row that
    is not an office label is skipped outright. Below it the classification
    order is: office header (parse_office), wrapped continuation of the
    just-opened header (only when every token is qualifier vocabulary),
    page furniture (is_noise), a standalone party word attached to the
    candidate above it, a trailing party token attached to THIS line's own
    candidate (real recap pages print the party right of the name, in its own
    column, on the same line), else a candidate row.

    Row dicts carry top/bottom so assign_cells can band them; office rows
    also carry "raw", the exact label text consumed so a continuation joins
    faithfully. Candidate "candidate" text gets LABEL_REPAIRS applied to its
    words (the party token is identified on the raw text before repair)."""
    rows = []
    current_office = None
    last_candidate = None
    for ln in lines:
        label_words = [x for x in ln["words"] if x["x0"] < label_x_max]
        if not label_words:
            continue
        above_table = ln["top"] < table_top
        text = " ".join(x["text"] for x in label_words)
        # 1) office header?
        office = parse_office(text, fuzzy)
        if office is None and current_office is not None and last_candidate is None:
            # 2) wrapped continuation of the just-opened office header
            tokens = text.split(" ")
            if all(_is_wrap_token(tok, fuzzy) for tok in tokens):
                merged = current_office["raw"] + " " + text
                office = parse_office(merged, fuzzy)
                if office is not None:
                    o, d, seat = office
                    current_office.update(office=o, district=d, seat=seat,
                                          raw=merged,
                                          bottom=max(x["bottom"] for x in label_words))
                    continue
        if office is not None:
            o, d, seat = office
            current_office = {"kind": "office", "office": o, "district": d,
                              "seat": seat, "raw": text,
                              "top": ln["top"],
                              "bottom": max(x["bottom"] for x in label_words)}
            rows.append(current_office)
            last_candidate = None
            continue
        if above_table:
            continue  # only the office header lives above the first data row
        if is_noise(text, fuzzy):
            continue
        # 3) standalone party word -> attach to the candidate above (if any);
        #    with no candidate above it the word is furniture, not a name
        if len(label_words) == 1:
            pk = party_of(label_words[0]["text"], fuzzy)
            if pk is not None:
                if last_candidate is not None:
                    last_candidate["party"] = pk
                    last_candidate["bottom"] = max(last_candidate["bottom"],
                                                   max(x["bottom"] for x in label_words))
                continue
        # 4) trailing party token on the candidate's own line: it belongs to
        #    the candidate being built from this line, so strip it from the
        #    name instead of forwarding the line's text to the last candidate
        tokens = text.split(" ")
        party = None
        if len(tokens) > 1:
            pk = party_of(tokens[-1], fuzzy)
            if pk is not None:
                party = pk
                tokens = tokens[:-1]
        cand = {"kind": "candidate",
                "office": current_office["office"] if current_office else None,
                "district": current_office["district"] if current_office else None,
                "seat": current_office["seat"] if current_office else None,
                "candidate": " ".join(LABEL_REPAIRS.get(tok, tok) for tok in tokens),
                "party": party,
                "top": ln["top"], "bottom": max(x["bottom"] for x in label_words),
                "cells": {}}
        rows.append(cand)
        last_candidate = cand
    return rows


def assign_cells(rows, numeric_words, centers, fuzzy=False):
    """Map (row_index, column_center) -> votes by row y-band overlap.

    A numeric word attaches to the candidate row whose y band contains its
    vertical center, and to the nearest column center within COL_TOL."""
    out = {}
    for word in numeric_words:
        col = min(centers, key=lambda c: abs(c - word["x0"]))
        if abs(col - word["x0"]) > COL_TOL:
            continue
        cleaned = digit_clean(word["text"], fuzzy)
        if not DIGIT_RE.match(cleaned):
            continue
        mid = (word["top"] + word["bottom"]) / 2.0
        for i, row in enumerate(rows):
            if row["kind"] != "candidate":
                continue
            if row["top"] - 3 <= mid < row["bottom"] + 6:
                out[(i, col)] = int(cleaned)
                break
    return out
