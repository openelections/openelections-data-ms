"""Deterministic extraction of precinct-level results from 2026 Mississippi
general election county recapitulation PDFs that carry an embedded text layer.

Rebuilds the SEMS "Official Recapitulation" crosstab (candidate rows x
precinct columns) from natural_pdf word/char geometry -- no OCR, no vision
models. Header labels are never read from geometry (Amendment A): an
operator-vision manifest per county names each page's columns, and a later
assembly stage binds the detected column centers to those names. Internal
gates decide whether a county's CSV may be written:

1. per-candidate precinct cells sum to the manifest-designated TOTAL column,
2. structure/manifest alignment: label counts match detected columns on every
   page, names normalize uniquely and non-empty, every candidate carries a
   total, and blank body cells reconcile to the row's own total before they
   read as 0,
3. roster consistency across counties sharing a race (batch stage).

natural_pdf is imported lazily: the pure geometry/label functions must stay
importable (and testable) without it.

Usage:
    uv run python src/extract_2026_general_text_pdf.py \
        ~/code/openelections-sources-ms/2026/general/Union_County_2026_general.pdf \
        --county Union --out 2026/counties/20261103__ms__general__union__precinct.csv
"""

import json
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
    """Distinct x0 centers of numeric columns, ascending.

    Non-load-bearing utility (superseded in the live path by grid_centers,
    which additionally filters clusters against the first data line's own
    span); its tests still pin the clustering math both paths share."""
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
    m = re.search(r"(Chancery|Circuit) Court 0*(\d+)(?:\s*-\s*0*(\d+))?\s*-\s*"
                  r"\1 District 0*(\d+)(?:\s*-\s*0*(\d+))?(?:\s*Place\s*0*(\d+))?",
                  label)
    if m:
        # Double-dash judicial labels: "Chancery Court 9-2-Chancery District
        # 9-2" (Warren p2/p3), "Circuit Court 9-1-Circuit District 9-1" and
        # the Place-suffixed "Circuit Court 3-Circuit District 03 Place 1"
        # (Union p4/p5). The first number pair is district-place; the second
        # pair / Place slot repeat it.
        place = m.group(6) or m.group(3) or m.group(5)
        return (f"{m.group(1)} Court", str(int(m.group(2))),
                int(place) if place else None)
    if not m and fuzzy and _fuzzy_eq(label[:15], "CIRCUIT COURT", 0.7):
        # District-first family: "Circuit Court <d>-Circuit District <d>
        # Place <p>". The OCR layer hides the leading "1" of "13" inside the
        # 'l3' token (Jasper p2), so the surviving digit runs are 13 / 1 --
        # the district is digits[0] and the place is the next run that is
        # not a repeat of the district number itself.
        digits = re.findall(r"\b(\d+)\b", label)
        if digits:
            district = digits[0]
            place = None
            for run in digits[1:]:
                if int(run) != int(district):
                    place = int(run)
                    break
            return "Circuit Court", str(int(district)), place
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
TABLE_TOP_Y_WINDOW = 9.0
# How far above the first data row's top the numeric scan still reaches: the
# digits floor is table_top - TABLE_TOP_Y_WINDOW, and the anchor window is
# symmetric. 9.0pt clears every line whose top anchors within one row pitch.
COL_TOL = 18.0          # max |x0 - column center| for a cell to attach
MIN_CLUSTER_MEMBERS = 3  # drop 1-2-member x clusters (footer digits, noise)
CELL_BAND_TOP = 3.0     # a cell's mid may sit this far ABOVE its row's top
CELL_BAND_BOTTOM = 6.0  # ... or this far BELOW its row's bottom

# Qualifier words that may make up a wrapped office-header line ("US House Of
# Rep 01-1st Congressional" + "District", or a split before the "Of": "Court"
# + "Of Appeals 01-District 3 Position 2"), with their digit runs ("01-1st").
# The vocabulary gate guards the continuation branch: the office regexes match
# by prefix, so merged text keeps parsing after candidate names are appended
# ("...Position 1 Derek Dewayne Hopson Jr. Nonpartisan" still matches the
# Court pattern). Proper noun tokens never gate-pass, so the first candidate
# row under a self-contained header is never swallowed.
WRAP_WORDS = ("district", "position", "place", "congressional", "court",
              "appeals", "chancery", "circuit", "of", "us", "rep", "house")

# Race-header keywords for the unparseable-header catch-all: a label line the
# office parser does not know but that carries one of these as a word, a
# structural separator (a dash-like run or a trailing numeral) and a role-word
# tail. Conservative on purpose -- keyword alone ("Court") is not enough, the
# match is word-bounded ("Courtney Smith" stays a candidate), and the
# certification blurb's "Election Commission will prepare..." lines end in
# prose, not a role word, so the commission/election keywords cannot reach
# them. The SEMS local-race vocabulary (county/municipal sections: school
# districts, municipal added territory, justice court, consolidated races)
# extends both the keyword and the tail sets -- real Union p4/p5 strings:
# "New Albany Added Territory-Added Territory", "New Albany Municipal
# Separate School District" (+ its garbled wrapped line 'LIstnCT'/'u.strica').
LOCAL_RACE_WORDS = ("school", "municipal", "territory", "justice",
                    "consolidated")
HEADER_KEYWORDS_RE = re.compile(
    r"\b(court|district|place|position|appeals|chancery|circuit|house|senate|"
    r"commission|commissioner|judge|election|trustee|school|municipal|"
    r"territory|justice|consolidated)\b")
EXISTING_ROLE_TAIL_RE = re.compile(
    r"(?:judge|trustee|commissioner|court|district|place|position|rep|house|"
    r"senate|appeals|chancery|circuit|election|board)\W*$")
HEADER_ROLE_TAIL_RE = re.compile(
    r"(?:judge|trustee|commissioner|court|district|place|position|rep|house|"
    r"senate|appeals|chancery|circuit|election|board|school|municipal|"
    r"territory|justice|consolidated)\W*$")


def is_unparsed_header(text):
    """True for a race-header label shape that parse_office does not
    recognize (Warren p5's local-office labels: "Warren County-County Court
    Judge", "Election Commission I-Election Commissioner" + its "District 1"
    wrap, "School Board District 3-School Board Trustee"; Union p4/p5's
    "New Albany Added Territory-Added Territory" and the one-line municipal
    form "New Albany Municipal Separate School District").

    The dash-less municipal/school shape qualifies only with a LOCAL_RACE
    keyword plus a PRE-EXISTING role tail, so a candidate merely named like
    the vocabulary ("John Justice") stays a candidate; a dash-less line
    whose tail is itself only local-race vocabulary ("New Albany Municipal
    Separate School", the wrapped first half of that header) is NOT a
    standalone header here -- it is consumed as a wrapped fragment by the
    label_rows local-header runner."""
    t = text.lower()
    if not HEADER_KEYWORDS_RE.search(t):
        return False
    if not re.search(r"[-–—·]", text) and not re.search(r"\d\s*\W*\s*$", t):
        if not any(re.search(rf"\b{word}\b", t) for word in LOCAL_RACE_WORDS):
            return False
        if not EXISTING_ROLE_TAIL_RE.search(t):
            return False
    # tail: a role word or a bare numeral ("District 1")
    return (bool(HEADER_ROLE_TAIL_RE.search(t))
            or bool(re.search(r"\d\s*$", t)))


# Invisible-Tesseract text-layer misreads of PRINTED candidate names, keyed on
# the observed mangle -- the same mechanism as PARTY_WORDS's mangled keys.
# Union's print says "Scott Colom" / "John Weddle" (verified against the
# rendered page; the OCR layer reads "Coiom" / "weddie"). Applied to label
# words only, never to numeric handling or office patterns.
LABEL_REPAIRS = {"Coiom": "Colom", "weddie": "Weddle"}


def _is_wrap_token(token):
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
    nothing on the first data line, so they drop without a special case.

    The anchor-span rule is a FILTER on the clustered digits, not a lossless
    detector: `digits` only reaches back to table_top - TABLE_TOP_Y_WINDOW,
    so a column whose cells sit above that floor is unseen (Jasper p2's
    first data line starts at x=464 and its left clusters -- 5-8 members --
    drop). Starving a page of its real columns fails loud downstream in
    Task 5's count gate (manifest entries == detected columns per page)."""
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

    Returns {"precinct_centers": [x...], "table_top": float, "rows": [...],
    "conflicts": [...]} with rows = label_rows(...) and each candidate row's
    "cells" filled from the numeric grid; "conflicts" records every
    (row_index, column_center) attach that overwrote an earlier value as
    [row_index, column_center, kept_value, overwritten_value] (assign_cells
    is last-wins; Warren p3 fires this for real). Equal-value repeats are
    logged too -- two words reading the same cell value still overwrite one
    another, and the record is the caller's only trace of it. Does NOT
    resolve header labels (the operator manifest does that in Task 5); does
    NOT call vertical_headers.

    Returns None in two cases: a non-table page (find_table_top finds no
    numeric-grid line -- the cover page), or a table page whose column
    clusters all drop (no cluster with >= MIN_CLUSTER_MEMBERS members
    overlapping the first data line -- see grid_centers)."""
    words = [{"text": x.text, "x0": x.x0, "x1": x.x1, "top": x.top, "bottom": x.bottom}
             for x in page.words]
    lines = lines_from_words(words)
    table_top = find_table_top(lines)
    if table_top is None:
        return None  # not a table page (cover page)

    def band_words(lo, hi):
        return [x for ln in lines if lo <= ln["top"] < hi for x in ln["words"]]

    digits = [x for x in band_words(table_top - TABLE_TOP_Y_WINDOW, float("inf"))
              if looks_numeric(x["text"], fuzzy)]
    # The first data line anchors the grid; a +-TABLE_TOP_Y_WINDOW window
    # keeps cells that y-jitter split onto a follow-on line inside the anchor.
    anchor_digits = [x for x in
                     band_words(table_top - TABLE_TOP_Y_WINDOW,
                                table_top + TABLE_TOP_Y_WINDOW)
                     if looks_numeric(x["text"], fuzzy)]
    centers = grid_centers(digits, anchor_digits)
    if not centers:
        return None  # numeric grid lost; caller treats the page as unused

    # Measured on Union p2-p5 this leaves +1.9..+4.4pt between the band and
    # the leftmost col-1 cell x0; one 4-digit cell would push a cell token
    # into the label band (Task 8 de-risking candidate: derive the boundary
    # from the party-column right edge instead of min(centers)).
    label_x_max = min(centers) - LABEL_BAND
    rows = label_rows(lines, table_top, label_x_max, fuzzy)
    conflicts = []
    cells = assign_cells(rows, [x for x in digits if x["x0"] >= label_x_max],
                         centers, fuzzy, conflicts=conflicts)
    for (r_idx, col), val in cells.items():
        rows[r_idx]["cells"][col] = val
    return {"precinct_centers": centers, "table_top": table_top, "rows": rows,
            "conflicts": conflicts}


def _next_label_band(lines, idx, label_x_max):
    """The first label band AFTER `lines[idx]` (for lookahead), or None."""
    for later in lines[idx + 1:]:
        band = [x for x in later["words"] if x["x0"] < label_x_max]
        if band:
            return band
    return None


FRAGMENT_CAP = 3  # consumed fragments per open local-race header, max

# A lone token that reads like a plausible person name is never a consumable
# fragment: garbage fragments garble the case ('LIstnCT', 'u.strica') or
# carry digits. 'Bulger' after a local header stays a candidate.
PLAUSIBLE_NAME_RE = re.compile(r"^[A-Z][a-z]+$")


def _is_local_fragment(band_text, band_words, fuzzy):
    """True for a wrapped-fragment line that belongs to an open local-race
    header block: a single non-party token that is not a plausible person
    name (Union p4/p5's garbled 'LIstnCT' / 'u.strica' -- the block's third
    printed line), an all-qualifier line (the shared wrap vocabulary), or a
    dash-less line carrying the local-race vocabulary that is not itself a
    standalone header (the wrapped 'New Albany Municipal Separate School'
    half). A standalone party token is never a fragment; it is furniture or
    the candidate above's party."""
    if len(band_words) == 1:
        token = band_words[0]["text"]
        if party_of(token, fuzzy) is not None:
            return False  # standalone party word: furniture, never a fragment
        return not PLAUSIBLE_NAME_RE.match(token)
    tokens = band_text.split(" ")
    if all(_is_wrap_token(tok) for tok in tokens):
        return True
    t = band_text.lower()
    return (any(re.search(rf"\b{word}\b", t) for word in LOCAL_RACE_WORDS)
            and not is_unparsed_header(band_text))


def label_rows(lines, table_top, label_x_max, fuzzy=False):
    """Build the candidate/office row stream from the label band.

    Lines strictly above `table_top` carry nothing but the section's office
    header: the certification blurb and vertical-name-stack fragments sit
    there too and parse as nothing, so any line above the first data row that
    is not an office label is skipped outright. Below it the classification
    order is: office header (parse_office, alone or joined from a split first
    fragment held back from header territory), wrapped continuation of the
    just-opened header (only when every token is qualifier vocabulary), the
    local-race header block (an unparseable race header -> kind
    "unknown_header", never a candidate, no office attribution: Warren's
    double-dash judicial and local-office labels and Union's municipal/school
    section; checked ahead of is_noise because Warren's "Election Commission
    I-Election Commissioner" carries a noise anchor yet is a header -- and,
    while such a header is open, directly-following wrapped-fragment lines
    (_is_local_fragment) extend the header's text instead of becoming
    candidate rows; the block closes at the first definite candidate line: a
    name with an inline trailing party token, or a lone token whose next
    label line is a standalone party token), page furniture (is_noise), a
    standalone party word attached to the candidate above it, a trailing
    party token attached to THIS line's own candidate (real recap pages
    print the party right of the name, in its own column, on the same line),
    else a candidate row.

    Row dicts carry top/bottom so assign_cells can band them; office rows
    carry "raw" (the exact label text consumed so a continuation joins
    faithfully) and an empty "cells" map (dict-shape symmetry with
    candidate rows). Candidate "candidate" text gets LABEL_REPAIRS applied
    to its words (the party token is identified on the raw text before
    repair); a header joined from a held-back fragment gets the completing
    line's top."""
    rows = []
    current_office = None
    last_candidate = None
    pending_header = None
    local_header = None  # open local-race unknown_header consuming fragments
    local_fragments = 0  # fragments consumed into that header (cap FRAGMENT_CAP)
    for idx, ln in enumerate(lines):
        label_words = [x for x in ln["words"] if x["x0"] < label_x_max]
        if not label_words:
            continue
        above_table = ln["top"] < table_top
        text = " ".join(x["text"] for x in label_words)
        # 1) office header, alone or joined from a split first fragment
        office = parse_office(text, fuzzy)
        if office is None and pending_header is not None:
            joined_text = pending_header + " " + text
            office = parse_office(joined_text, fuzzy)
            if office is not None:
                o, d, seat = office
                current_office = {"kind": "office", "office": o, "district": d,
                                  "seat": seat, "raw": joined_text,
                                  "top": ln["top"],
                                  "bottom": max(x["bottom"] for x in label_words),
                                  "cells": {}}
                rows.append(current_office)
                local_header = None  # a new office section closes the block
                last_candidate = None
                pending_header = None
                continue
        if office is None and current_office is not None and last_candidate is None:
            # 2) wrapped continuation of the just-opened office header
            tokens = text.split(" ")
            if all(_is_wrap_token(tok) for tok in tokens):
                merged = current_office["raw"] + " " + text
                office = parse_office(merged, fuzzy)
                if office is not None:
                    o, d, seat = office
                    current_office.update(office=o, district=d, seat=seat,
                                          raw=merged,
                                          bottom=max(x["bottom"] for x in label_words))
                    pending_header = None
                    continue
        if office is not None:
            o, d, seat = office
            current_office = {"kind": "office", "office": o, "district": d,
                              "seat": seat, "raw": text,
                              "top": ln["top"],
                              "bottom": max(x["bottom"] for x in label_words),
                              "cells": {}}
            rows.append(current_office)
            local_header = None  # a new office section closes the block
            last_candidate = None
            pending_header = None
            continue
        if above_table:
            # only the office header lives above the first data row; hold the
            # line back as a possible split-header fragment
            pending_header = text
            continue
        # 3) wrapped local-race header block. While an unknown_header row is
        #    open, directly-following fragment lines (_is_local_fragment)
        #    extend that header's text and are never candidate rows, up to
        #    FRAGMENT_CAP consecutive fragments; another header-shaped line
        #    opens its own row (Warren's "District 1" stays its own header),
        #    a newly-opened OFFICE row closes the block, and anything else --
        #    above all the first definite candidate line (name + inline
        #    trailing party token, or a lone token whose next label line is a
        #    standalone party token) -- closes the block and is classified
        #    normally below.
        if local_header is not None:
            tokens = text.split(" ")
            next_band = _next_label_band(lines, idx, label_x_max) \
                if len(label_words) == 1 else None
            definite = ((len(tokens) > 1
                         and party_of(tokens[-1], fuzzy) is not None)
                        or (next_band is not None and len(next_band) == 1
                            and party_of(next_band[0]["text"], fuzzy)
                            is not None))
            if definite:
                local_header = None  # fall through; classify normally
            elif is_unparsed_header(text):
                pass  # another header line: its own unknown_header row below
            elif local_fragments >= FRAGMENT_CAP:
                local_header = None  # capped: classify normally below
            elif _is_local_fragment(text, label_words, fuzzy):
                local_header["text"] += " " + text
                local_header["bottom"] = max(
                    local_header["bottom"],
                    max(x["bottom"] for x in label_words))
                local_fragments += 1
                last_candidate = None
                pending_header = None
                continue
            else:
                local_header = None  # unrecognised line closes the block
        if is_unparsed_header(text):
            row = {"kind": "unknown_header", "text": text,
                   "top": ln["top"],
                   "bottom": max(x["bottom"] for x in label_words)}
            rows.append(row)
            local_header = row
            local_fragments = 0  # a fresh header gets its own fragment budget
            # A local-office header closes the office context: candidates
            # under it carry NO office (N2), and the wrap-continuation gate
            # above must not reach back into the previous header and rewrite
            # its district/seat.
            current_office = None
            last_candidate = None
            pending_header = None
            continue
        if is_noise(text, fuzzy):
            pending_header = None
            continue
        # 4) standalone party word -> attach to the candidate above (if any);
        #    with no candidate above it the word is furniture, not a name
        if len(label_words) == 1:
            pk = party_of(label_words[0]["text"], fuzzy)
            if pk is not None:
                if last_candidate is not None:
                    last_candidate["party"] = pk
                    last_candidate["bottom"] = max(last_candidate["bottom"],
                                                   max(x["bottom"] for x in label_words))
                pending_header = None
                continue
        # 5) trailing party token on the candidate's own line: it belongs to
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
        pending_header = None
    return rows


def assign_cells(rows, numeric_words, centers, fuzzy=False, conflicts=None):
    """Map (row_index, column_center) -> votes by row y-band overlap.

    A numeric word attaches to the candidate row whose y band contains its
    vertical center -- band = [row top - CELL_BAND_TOP, row bottom +
    CELL_BAND_BOTTOM) -- and to the nearest column center within COL_TOL.
    Rows are tested in list order and the first candidate whose band
    contains the mid wins (bands deliberately overlap: the single-row pitch
    is ~20pt but cells can print in two y positions ~3-9pt apart within one
    row -- "second printings" observed on Warren p2/p3 -- and a split
    y-jitter line keeps a row's own cells on consecutive lines). The value
    is an integer shape recheck on the cleaned text: digit_clean applies
    its fuzzy substitutions ONLY to tokens already chosen because they sit
    in a numeric column, so `fuzzy` repairs digit-shaped OCR confusions
    ("5O" -> "50") without touching label text.

    When two words claim the same (row_index, column_center) the LAST word
    wins. That is silent unless the caller passes `conflicts` (a list), which
    collects each overwrite as [row_index, column_center, kept_value,
    overwritten_value] -- equal-value repeats are logged as well (two words
    agreeing on a cell still overwrite one another) -- the record surfaces
    both true duplicates and
    clusters that chained two real columns together (Warren p3 reports
    row 5 / '76' vs '1' at column 333.12).

    The result is keyed on `rows`' list indices, so the mapping only holds
    while that list order does: callers merging or reordering rows must do
    it before attaching cells."""
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
            if row["top"] - CELL_BAND_TOP <= mid < row["bottom"] + CELL_BAND_BOTTOM:
                val = int(cleaned)
                if (i, col) in out and conflicts is not None:
                    conflicts.append([i, col, out[(i, col)], val])
                out[(i, col)] = val
                break
    return out


# ---- county assembly (Amendment A: manifest-driven) -----------------------
#
# Header labels are the operator vision manifest's: each page's labels zip
# positionally against the page's ascending column centers, the total-label
# column becomes the candidate's total, and merged rows, cross-page office
# carry and the gates below decide whether a county parse is trustworthy.

TOTAL_NAME = "TOTAL"

MANIFEST_REQUIRED_KEYS = ("county", "source", "total_label", "pages")


def load_manifest(path):
    """Load + validate an operator header manifest. Returns (manifest, problems).

    `pages` maps 1-based page-number strings to that page's header labels
    left-to-right (exactly one entry equals `total_label` where the page
    carries a TOTAL column) and must be a dict of label-lists of strings;
    `total_label` must be a non-empty string. Label truncations are the
    operator's to resolve; problems here are only missing required keys and
    {"kind": "manifest_shape", "key": ...} shape errors -- alignment
    problems are the assembly's (see normalize_page_labels / run_gates)."""
    with open(path) as fh:
        manifest = json.load(fh)
    problems = [{"kind": "manifest_missing_key", "key": key}
                for key in MANIFEST_REQUIRED_KEYS if key not in manifest]
    page_map = manifest.get("pages")
    if not isinstance(page_map, dict):
        problems.append({"kind": "manifest_shape", "key": "pages",
                         "problem": "pages must be a dict of "
                                    "page-number -> label-list, got "
                                    f"{type(page_map).__name__}"})
    elif any(not isinstance(labels, list)
             for labels in page_map.values()):
        problems.append({"kind": "manifest_shape", "key": "pages",
                         "problem": "every page's labels must be a list"})
    elif any(not isinstance(label, str)
             for labels in page_map.values()
             for label in (labels or [])):
        problems.append({"kind": "manifest_shape", "key": "pages",
                         "problem": "every manifest label must be a string"})
    total_label = manifest.get("total_label")
    if not isinstance(total_label, str) or not total_label.strip():
        problems.append({"kind": "manifest_shape", "key": "total_label",
                         "problem": "total_label must be a non-empty string"})
    return manifest, problems


def normalize_page_labels(labels, total_label):
    """One page's left-to-right manifest labels -> (names, total_pos, problems).

    names is POSITIONAL (one entry per label): precinct_norm(label) for body
    columns, None where the label is the TOTAL marker or normalizes empty.
    total_pos is the first label equal to `total_label` (compared
    case-insensitively after stripping), or None when the page has no TOTAL
    column. problems flags {"kind": "empty_name"} (a body label that
    normalizes to nothing: the column's cells will be orphans), a second
    {"kind": "total_label_repeated"} marker, and {"kind": "name_collision"}
    -- any two of THIS page's labels whose normalized forms are equal
    ('P1' vs 'P1 ', or a repeated spelling). The same name repeated across
    PAGES is normal; collisions are checked per page only. Callers add the
    page number to every record they forward.
    """
    names = []
    total_pos = None
    problems = []
    wanted = (total_label or "").strip().upper()
    for pos, label in enumerate(labels):
        if (label or "").strip().upper() == wanted:
            if total_pos is None:
                total_pos = pos
            else:
                problems.append({"kind": "total_label_repeated", "pos": pos,
                                 "label": label})
            names.append(None)
            continue
        name = precinct_norm(label or "")
        names.append(name or None)
        if not name:
            problems.append({"kind": "empty_name", "pos": pos, "label": label})
    by_norm = {}
    for pos, label in enumerate(labels):
        if names[pos] is not None:
            by_norm.setdefault(names[pos], []).append(label)
    for name, spellings in by_norm.items():
        if len(spellings) > 1:
            problems.append({"kind": "name_collision", "name": name,
                             "labels": sorted(spellings)})
    return names, total_pos, problems


def parse_county_from_pages(pages, county, manifest):
    """Assemble a county from pre-extracted table pages (Amendment A).

    pages: {"<1-based page number>": extract_table_page result dict}; pages
    the extractor dropped (cover page, lost grid) are simply absent.
    manifest: the loaded manifest dict, or a path to one (loaded here so
    callers can hand over a written file).

    Alignment is positional: each page's ascending precinct_centers zip
    against the manifest's left-to-right labels; a count mismatch is a
    {"kind": "column_count"} manifest problem (the pair still zips over the
    longer side so nothing is thrown away silently). Body cells re-key from
    column center to the normalized precinct NAME at the same position, and
    the cell in the manifest's total-label column becomes the row's total.
    A (candidate, precinct) cell that arrives twice with different values is
    a real data conflict: recorded ({"kind": "conflicting_cells"}) and kept
    as the first value in ballot order.

    Merging: a candidate row printed on several pages (row blocks repeat the
    label stream over disjoint column halves) merges by
    (office, district, seat, collapsed-name), preserving ballot order (the
    first page where the candidate appears); the first non-None party wins,
    and "" (Nonpartisan) counts as a real party value. Equal-value repeats
    (the same value arriving twice for one (candidate, precinct)) are silent
    corroboration at this stage -- a deliberate contrast with the geometry
    layer, where every overwrite is logged as a conflict.

    Cross-page office carry: the pending (office, district, seat) of the
    previous page fills office=None candidate rows at the START of a page,
    until that page's first office row or unknown_header row appears (from
    then on the page's own context rules). The carry refreshes at EVERY page
    boundary: its value is None on the first table page, None when the page's
    first context row is a local-race unknown_header THAT SITS INSIDE the
    page's row stream (the page opens into a local-race zone and must never
    inherit the previous page's federal end context), the carry the previous
    page itself CONSUMED at its start when that page opened with carried
    rows (a repeating group's members share one row stream), else the
    previous page's end context -- which a trailing unknown_header leaves as
    None, so a local section that continues onto the next page does not hand
    its candidates a stale state office.
    office=None rows are never dropped before the carry is applied; rows
    still office-less afterwards (they sat under an unparseable
    local-office header) are excluded BY DESIGN -- recorded in
    pd["dropped_local_rows"], never silently and never as a gate.

    TOTAL: a blank body cell is a 0 only when the row's recorded total equals
    the sum of its present cells (the source's own arithmetic proves the
    blanks); otherwise the cells stay missing and run_gates flags them.
    """
    if isinstance(manifest, str):
        manifest, mproblems = load_manifest(manifest)
    else:
        mproblems = []
    manifest_problems = list(mproblems)
    structure_problems = []
    conflicts = []
    dropped_local_rows = []
    total_label = manifest.get("total_label") or TOTAL_NAME
    # A recorded-bad pages shape degrades to page_unlabeled for every
    # extracted page plus the manifest_shape record -- loud but never an
    # exception (a list value here used to reach the page-missing loop and
    # raise TypeError on its list items).
    manifest_pages = manifest.get("pages") \
        if isinstance(manifest.get("pages"), dict) else {}

    def page_no(key):
        try:
            return int(str(key))
        except ValueError:
            return None

    def sort_key(key):
        n = page_no(key)
        return (n is None, n or 0, str(key))

    alignments = {}
    for key in sorted(pages, key=sort_key):
        pno = page_no(key)
        if pno is None or key not in manifest_pages:
            manifest_problems.append({"kind": "page_unlabeled", "page": str(key)})
            continue
        tp = pages[key]
        labels = manifest_pages[key] or []
        centers = list(tp.get("precinct_centers") or [])
        if len(centers) != len(labels):
            manifest_problems.append({"kind": "column_count", "page": pno,
                                      "labels": len(labels), "centers": len(centers)})
        names, total_pos, label_problems = normalize_page_labels(labels, total_label)
        for pr in label_problems:
            pr.setdefault("page", pno)
            (structure_problems if pr["kind"] == "empty_name"
             else manifest_problems).append(pr)
        by_center = {}
        for pos in range(max(len(labels), len(centers))):
            center = centers[pos] if pos < len(centers) else None
            if pos == total_pos:
                if center is not None:
                    by_center[center] = TOTAL_NAME
            elif center is not None:
                by_center[center] = names[pos] if pos < len(names) else None
        alignments[pno] = {"names_by_center": by_center}
    for key in sorted(manifest_pages, key=sort_key):
        if key not in pages:
            manifest_problems.append({"kind": "page_missing", "page": page_no(key)})

    all_names = sorted({name for al in alignments.values()
                        for name in al["names_by_center"].values()
                        if name and name != TOTAL_NAME})

    merged = {}
    order = []
    # Cross-page office carry. The carry refreshes at EVERY page boundary
    # (Union's row-block halves and Warren's repeat-columns group both open
    # pages whose section was printed on an earlier page): its value is the
    # context the page's opening rows continue --
    #   None on the first table page;
    #   None when the page's first context row is a local-race unknown_header
    #     that sits INSIDE the page's row stream (Warren p5/p6: the page's
    #     opening rows precede the local zone's header box), so the page
    #     must never inherit the previous page's federal end context;
    #   the carry the PREVIOUS page itself consumed at its start, when that
    #     page opened with carried rows -- a repeating group's members share
    #     one row stream, so their office=None openings belong to the same
    #     section (Union p5's Michael Malski keeps Chancery Court d1 place 2
    #     even though p4 ended elsewhere);
    #   else the previous page's end context (the section it was reading
    #     when it ran out), which a trailing unknown_header leaves as None so
    #     a local section continuing onto the next page is not handed a stale
    #     state office.
    pending = None        # carry value decided at this page's boundary
    end_context = None    # office context in force at the end of the last page
    last_carry_used = None  # carry the previous page actually applied
    first_page = True
    for key in sorted(pages, key=sort_key):
        pno = page_no(key)
        if pno not in alignments:
            continue  # unlabeled page: flagged above, not assembled
        tp = pages[key]
        rows = tp.get("rows") or []
        by_center = alignments[pno]["names_by_center"]
        first_context_pos = None
        for pos, r in enumerate(rows):
            if r.get("kind") in ("office", "unknown_header"):
                first_context_pos = pos
                break
        if first_page:
            pending = None
        elif (first_context_pos is not None
              and rows[first_context_pos].get("kind") == "unknown_header"
              and first_context_pos < len(rows) - 1):
            # a local-race header sits INSIDE this page's row stream (Warren
            # p5/p6: the page's opening rows precede the local zone's header
            # box): the page belongs to the local zone and its opening rows
            # must never inherit the previous page's end context. A local
            # header that is instead the page's LAST row closes the page, and
            # the opening rows still carry normally (they precede the box,
            # whose own candidates print on the next page).
            pending = None
        elif last_carry_used is not None:
            pending = last_carry_used  # the group's row stream repeats
        else:
            pending = end_context
        first_page = False
        own_context = False
        last_context_kind = None  # "office" (with its triple) / "unknown"
        last_office = None
        first_carry_used = None  # carry this page applied at its start
        entries = []  # (row index, merge key, assembled row) in row order
        for idx, row in enumerate(rows):
            kind = row.get("kind")
            if kind == "office":
                own_context = True
                last_context_kind = "office"
                last_office = (row.get("office"), row.get("district"),
                               row.get("seat"))
                continue
            if kind == "unknown_header":
                own_context = True
                last_context_kind = "unknown"
                continue
            if kind != "candidate":
                continue
            office, district, seat = (row.get("office"), row.get("district"),
                                      row.get("seat"))
            if office is None and not own_context and pending is not None:
                office, district, seat = pending  # cross-page carry
                if first_carry_used is None:
                    first_carry_used = pending
            if office is None:
                # under an unknown_header (or a page with no office at all):
                # a local-office row, excluded by design and recorded whole:
                # raw label text, party and whatever cells the page captured,
                # BEST-EFFORT re-keyed where the manifest alignment resolves
                # a name (unmapped centers stay raw keys; the total-column
                # capture keeps its TOTAL key) -- never merged into any
                # reconciled figure.
                dropped_local_rows.append(
                    dict(row, text=row.get("candidate"),
                         cells={by_center.get(center) or center: value
                                for center, value
                                in (row.get("cells") or {}).items()},
                         page=pno))
                continue
            cells = {}
            orphans = {}
            total = row.get("total")
            for center, val in (row.get("cells") or {}).items():
                target = by_center.get(center)
                if target == TOTAL_NAME:
                    if total is None:
                        total = val
                    elif total != val:
                        conflicts.append({"kind": "duplicate_total", "page": pno,
                                          "candidate": row.get("candidate"),
                                          "values": [total, val]})
                    continue
                if target is None:
                    # an unattachable cell: best-effort re-keyed where the
                    # alignment resolves a name, else kept under its center
                    orphans[by_center.get(center) or center] = val
                    continue
                first = cells.setdefault(target, val)
                if first != val:
                    conflicts.append({"kind": "conflicting_cells", "page": pno,
                                      "candidate": row.get("candidate"),
                                      "precinct": target, "values": [first, val]})
            name_key = re.sub(r"\s+", " ", row.get("candidate") or "").strip().lower()
            entries.append((idx, (office, district, seat, name_key),
                            {"kind": "candidate", "office": office,
                             "district": district, "seat": seat,
                             "candidate": row.get("candidate"),
                             "party": row.get("party"), "cells": cells,
                             "total": total, "orphan_cells": orphans,
                             "page": pno}))
        # thread this page's duplicate-cell overwrites into the county record
        by_index = {idx: entry for idx, _, entry in entries}
        for idx, col, kept, over in tp.get("conflicts") or []:
            entry = by_index.get(idx)
            if entry is None:
                continue  # cells only ever attach to candidate rows
            conflicts.append({"kind": "duplicate_cell", "page": pno,
                              "candidate": entry["candidate"],
                              "precinct": by_center.get(col, col),
                              "kept": kept, "overwritten": over})
        for _, mkey, cand in entries:
            if mkey not in merged:
                cand["pages"] = [pno]
                merged[mkey] = cand
                order.append(mkey)
                continue
            tgt = merged[mkey]
            pages_seen = sorted(set(tgt["pages"]) | {pno})
            tgt["pages"] = pages_seen
            for pname, val in cand["cells"].items():
                if pname in tgt["cells"]:
                    if tgt["cells"][pname] != val:
                        conflicts.append({"kind": "conflicting_cells",
                                          "candidate": tgt["candidate"],
                                          "precinct": pname, "pages": pages_seen,
                                          "values": [tgt["cells"][pname], val]})
                    # agreement keeps the first-seen value
                else:
                    tgt["cells"][pname] = val
            for o_center, o_val in cand["orphan_cells"].items():
                tgt["orphan_cells"][o_center] = o_val
            if tgt["total"] is None and cand["total"] is not None:
                tgt["total"] = cand["total"]
            elif (tgt["total"] is not None and cand["total"] is not None
                  and tgt["total"] != cand["total"]):
                conflicts.append({"kind": "duplicate_total", "pages": pages_seen,
                                  "candidate": tgt["candidate"],
                                  "values": [tgt["total"], cand["total"]]})
            if tgt["party"] is None and cand["party"] is not None:
                tgt["party"] = cand["party"]
        # the page's end context: the section it was reading when it ran out
        # -- consumed by the NEXT page's boundary decision -- or, if the page
        # ended under an unknown_header, None, so a local section continuing
        # onto the next page is not handed a stale state office.
        if last_context_kind == "office":
            end_context = last_office
        elif last_context_kind == "unknown":
            end_context = None
        last_carry_used = first_carry_used
    candidate_rows = [merged[k] for k in order]
    for row in candidate_rows:
        missing = [n for n in all_names if n not in row["cells"]]
        if (row["total"] is not None and missing
                and sum(row["cells"].values()) == row["total"]):
            for name in missing:
                row["cells"][name] = 0  # blanks proven zero by the row's total
    return {"county": county,
            "precinct_names": all_names,
            "candidate_rows": candidate_rows,
            "dropped_local_rows": dropped_local_rows,
            "conflicts": conflicts,
            "manifest_problems": manifest_problems,
            "structure_problems": structure_problems,
            "alignments": {str(pno): al for pno, al in sorted(alignments.items())},
            "pages_used": [page_no(key) for key in sorted(pages, key=sort_key)
                           if page_no(key) in alignments]}


def parse_county_pdf(pdf_path, county, manifest_path, fuzzy=False):
    """Whole-county parse under an operator header manifest (Amendment A).

    Extracts every table page (natural_pdf stays lazily imported so the
    module imports without it), assembles them through
    parse_county_from_pages (the manifest is used ONLY there), and prepends
    the manifest load problems. Returns parse_county_from_pages' dict plus
    pd["page_count"]. Raises ValueError when the PDF yields no table pages
    at all (gate results on an empty parse would look vacuously clean)."""
    from natural_pdf import PDF  # lazy
    manifest, mproblems = load_manifest(manifest_path)
    pdf = PDF(str(pdf_path))
    pages = {}
    for i, page in enumerate(pdf.pages, start=1):
        tp = extract_table_page(page, fuzzy)
        if tp is not None:
            pages[str(i)] = tp
    if not pages:
        raise ValueError(f"no table pages found in {pdf_path}")
    pd = parse_county_from_pages(pages, county, manifest)
    pd["manifest_problems"] = mproblems + pd["manifest_problems"]
    pd["page_count"] = len(pdf.pages)
    return pd


def run_gates(pd):
    """Gate results -> {"total_mismatches", "structure", "conflicts",
    "manifest"}.

    total_mismatches: a candidate whose precinct cells do not sum to its own
    printed total (a present total is authoritative; no total here is a
    structure miss, not a mismatch).

    structure: {"kind": "missing_precinct_cells"} -- a candidate lacks cells
    for real precincts. A BLANK body cell is legitimate only when the row's
    printed total equals the sum of its present cells, in which case the
    assembly filled the blanks with 0 and this gate stays silent; anything
    else is flagged. {"kind": "missing_total"} -- a candidate with no total
    anywhere. {"kind": "orphan_cell"} -- a cell that could not be attached
    to a labeled precinct column (reported under the assembly's best-effort
    re-key: the aligned name when one resolved, else the raw column center).
    {"kind": "empty_name"} -- a manifest label that normalized to nothing.
    Local-office rows live OUTSIDE these lists: pd["dropped_local_rows"]
    reports them directly, and the gates see only what remains.

    conflicts: every recorded disagreement, kept visible rather than fixed:
    within-page duplicate-cell overwrites threaded from extract_table_page
    (last-wins there; equal-value repeats included), assembly-time
    (candidate, precinct) value disagreements across pages/entries, and
    duplicate totals.

    manifest: load/alignment problems -- missing manifest keys, per-page
    column-count mismatches, name collisions, repeated total markers, and
    manifest/extracted pages that failed to pair up.

    Roster consistency across counties stays with the batch stage (Task 9)
    and is deliberately not re-derived here."""
    problems = {"total_mismatches": [], "structure": [], "conflicts": [],
                "manifest": []}
    names = pd.get("precinct_names") or []
    for row in pd.get("candidate_rows") or []:
        cells = row.get("cells") or {}
        total = row.get("total")
        office, district = row.get("office"), row.get("district")
        seat, cand_name = row.get("seat"), row.get("candidate")
        party = row.get("party")
        if total is not None and sum(cells.values()) != total:
            problems["total_mismatches"].append(
                {"office": office, "district": district, "candidate": cand_name,
                 "party": party, "sum": sum(cells.values()),
                 "printed_total": total})
        missing = [n for n in names if n not in cells]
        if missing:
            problems["structure"].append(
                {"kind": "missing_precinct_cells", "office": office,
                 "district": district, "seat": seat, "candidate": cand_name,
                 "party": party, "precincts": missing})
        if total is None:
            problems["structure"].append(
                {"kind": "missing_total", "office": office, "district": district,
                 "seat": seat, "candidate": cand_name, "party": party})
        for or_key in sorted(row.get("orphan_cells") or {}, key=str):
            problems["structure"].append(
                {"kind": "orphan_cell", "candidate": cand_name, "party": party,
                 "precinct_or_center": or_key,
                 "value": row["orphan_cells"][or_key]})
    problems["conflicts"].extend(pd.get("conflicts") or [])
    problems["manifest"].extend(pd.get("manifest_problems") or [])
    problems["structure"].extend(pd.get("structure_problems") or [])
    return problems
