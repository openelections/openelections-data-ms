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
        --county Union \
        --manifest 2026/header-reads/20261103__ms__general__union__headers.json \
        --out 2026/counties/20261103__ms__general__union__precinct.csv
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

    Non-load-bearing utility since Amendment A (the operator manifest
    designates the TOTAL column); retained for cross-checks.

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


# Candidate-name merge folds, keyed on the variants the text layers actually
# render (Task 7: Warren p3 prints "Cindy  Hyde·Smith " with a unicode mid dot
# where p2/p4 print the hyphen, and "Bennie G, Thompson" with a comma where
# p2/p4 print the period for an initial's stop). Whitespace collapse and
# lowering always apply; nothing else folds.
NAME_PUNCT_FOLDS = ((("·",), "-"), ((",",), "."))
NAME_WS_RE = re.compile(r"\s+")


def name_key(name):
    """Merge key for a candidate name: punctuation folds tied to observed
    label variants (NAME_PUNCT_FOLDS) + whitespace collapse + lowercase.

    Shared by the assembly's merge key (parse_county_from_pages) and the CSV
    writer's ballot-order index (_merge_key) so both fold identically -- a
    split key would present one candidate as two rows/positions."""
    folded = name or ""
    for chars, replacement in NAME_PUNCT_FOLDS:
        for ch in chars:
            folded = folded.replace(ch, replacement)
    return NAME_WS_RE.sub(" ", folded).strip().lower()


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


# Invisible text-layer misreads of PRINTED label words, keyed on the observed
# mangle -- the same mechanism as PARTY_WORDS's mangled keys. Applied to
# candidate name words AND to office-header label words before parse_office,
# never to numeric handling. New entries join only from a render-verified
# read of the printed page ("Amendment A: operator vision is the truth"):
#
# - Union p2: print says "Scott Colom" / "John Weddle"; layer reads
#   "Coiom" / "weddie" (Task 4, render-verified).
# - Warren p2/p4: print says "United States-Senate" (rendered strip, 400 dpi);
#   the born-digital layer reads "United states-senatel" -- lowercase + a
#   trailing 'l' glyph. parse_office refused it at fuzzy=False, so p2's whole
#   Senate section folded into the page's previous context (and p4's opening
#   rows relied on a cross-page carry).
# - Warren p4: print says "Chancery Court 9-2-..."; the layer lost the label's
#   first two characters at the page's left edge ("ancery Court ..."), and
#   without this, is_unparsed_header would have swallowed the section's two
#   nonpartisan candidates into the local-row drop.
# - Warren p7: an invisible junk glyph merged into the first name word
#   ("iM. James 'Jim' Chaney Jr."); the print reads "M. James ..." -- without
#   the repair the p7 copy never merges with p5/p6 same-candidate rows.
LABEL_REPAIRS = {"Coiom": "Colom", "weddie": "Weddle",
                 "states-senatel": "States-Senate",
                 "ancery": "Chancery", "iM.": "M."}


def _repair_label(text):
    """LABEL_REPAIRS applied word-wise to a label line's text (candidate
    names and office headers alike)."""
    return " ".join(LABEL_REPAIRS.get(tok, tok) for tok in text.split(" "))


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


ANCHOR_DATA_LINES = 3


def multi_line_anchor_digits(lines, table_top, looks_like_cell,
                             is_header_line=None, max_lines=ANCHOR_DATA_LINES):
    """Clean digit tokens of up to the first `max_lines` data lines.

    `lines` are lines_from_words' dicts; a data line is one at or below
    `table_top` (the line find_table_top fired on, or one of the y-jitter
    follow-on lines the window lets in) that carries at least one token the
    caller's predicate accepts (looks_numeric over clean digit tokens -- the
    same shape test the anchor window uses) and is not a race-header line.

    `is_header_line` (called with the line's text) excludes office-label
    lines: their printed qualifier digits ("Place 3", "Position 1") sit just
    right of the label band and would widen the span over the Position/Place
    phantom clusters (Union p4 reprints its Chancery header mid-table:
    'Chancery Court 1-Chancery District 1 Place 3'; the caller classifies
    with parse_office + is_unparsed_header + is_noise). Lines without a
    cell-shaped token are skipped too, so a jitter pair line whose only
    words are label fragments (Jasper p2's 'Scott Colom 71.') neither
    widens the span nor consumes a slot. The list is concatenated:
    grid_centers computes its span as min/max x0 over every token, i.e. the
    union of the lines' spans.

    Why: extract_table_page anchors the grid's x span on the first data
    line's own cells, but an OCR text layer can misread or drop cells on
    that one line -- Jasper p2's carries only 3 clean digits (x 464..745),
    which dropped the table's five left clusters (c285..c423). The next data
    lines carry the same columns' cells (x 281.5..745.5), so the union binds
    the whole grid while staying clear of the x~246 '1'-debris phantom: no
    early data line reaches that far left. The cap keeps the anchor a span
    measurement over the table's opening rows -- never over arbitrary
    body/fragment lines further down.
    """
    out = []
    lines_collected = 0
    for ln in lines:
        if (ln["top"] < table_top
                or (is_header_line is not None and is_header_line(ln["text"]))):
            continue
        tokens = [x for x in ln["words"] if looks_like_cell(x)]
        if not tokens:
            continue
        out.extend(tokens)
        lines_collected += 1
        if lines_collected >= max_lines:
            break
    return out


def grid_centers(digits, anchor_digits, min_members=MIN_CLUSTER_MEMBERS,
                 filler_words=()):
    """x centers of the crosstab columns among `digits`' x clusters.

    Every data line carries one cell in every column, so the numeric tokens
    of the table's first data lines (`anchor_digits`) bound the grid's x
    span. extract_table_page widens that reference to the clean digit tokens
    of up to the first THREE data lines (multi_line_anchor_digits): their
    union span still drops every cluster that no early data line touches,
    while columns whose first-line cell the layer misread keep their span
    evidence (Jasper p2's first data line carries only 3 clean OCR digits,
    x 464..745; lines 2-3 carry the left cells, x 281..745). A cluster is a
    real column when -- after `filler_words` attach -- it has >= min_members
    members AND its x range overlaps that span. Office-header qualifier
    digits (Position/Place values, which print just right of the label band,
    x ~195-250 on Union p2) form two phantom ~45pt-pitch clusters left of the
    first column that overlap nothing on the first data lines, so they drop
    without a special case -- Jasper p2's x~246 '1'-debris phantom drops the
    same way (no early data line reaches x <= 246).

    `filler_words` are the recap's printed X cells: they join the NEAREST
    numeric cluster within COL_TOL without moving its center (an X glyph
    sits ~10pt right of its column's right-aligned digits, so counting X
    glyphs into the cluster's x mean would drag the column center toward the
    label band). They carry column-position evidence only; X never becomes a
    votes value, and columns whose members are mostly X (Warren's local-zone
    tails, p7's "Porters Chapel") stay detectable. A column with NO numeric
    member at all still has no cluster seed and stays undetected -- the
    column-count gate reports the loss loudly.

    The anchor-span rule is a FILTER on the clustered digits, not a lossless
    detector: `digits` only reaches back to table_top - TABLE_TOP_Y_WINDOW,
    so a column whose cells sit above that floor is unseen. Starving a page
    of its real columns fails loud downstream in Task 5's count gate
    (manifest entries == detected columns per page)."""
    if not digits or not anchor_digits:
        return []
    anchor_lo = min(x["x0"] for x in anchor_digits)
    anchor_hi = max(x["x0"] for x in anchor_digits)
    seeds = []
    for cl in cluster_xs([(x["x0"], x) for x in digits], gap=COLUMN_GAP):
        # the center stays the numeric members' mean: the right-aligned
        # digits define the column, and a shifted center would drag the
        # label-band boundary into the cells
        seeds.append({"center": cl["center"], "items": list(cl["items"])})
    for word in filler_words:
        # nearest-seed attachment, same tolerance as assign_cells
        best = min(seeds, key=lambda s: abs(s["center"] - word["x0"]))
        if abs(best["center"] - word["x0"]) <= COL_TOL:
            best["items"].append((word["x0"], word))
    out = []
    for seed in seeds:
        if len(seed["items"]) < min_members:
            continue
        lo = min(x for x, _ in seed["items"])
        hi = max(x for x, _ in seed["items"])
        if hi >= anchor_lo and lo <= anchor_hi:
            out.append(seed["center"])
    return sorted(out)


X_CELL_WORDS = frozenset({"X", "x"})
# A grid word must not be a scrap of an overlay glyph run: below this share
# of the page's anchor-digit height the token is invisible junk (Warren p3's
# Times-Roman 1.7pt "1" against 8.6pt data digits -- a stray that used to
# overwrite Eller's real "76" cell and fire a conflict). Real cells sit at
# the page's own digit height (ratio ~1.0); the floor is anchored on the
# page's FIRST data line so no absolute size is assumed.
CELL_HEIGHT_FLOOR = 0.5


def extract_table_page(page, fuzzy=False, min_columns=3, token_repairs=None):
    """Parse one recap table page (Amendment A contract).

    `min_columns` is find_table_top's threshold; the default 3 holds for
    every standard page, and the manifest-driven retry in parse_county_pdf
    re-extracts a declared page with 2 when its narrow tail (Warren p4/p7:
    only "Porters Chapel" + TOTAL, so a data line carries two numeric
    tokens) leaves find_table_top at None. Under 2, a prose line carrying
    two CLEAN numeric tokens in two x clusters would be read as the table
    top -- the real recap prose does not shape that way (the blurb's tokens
    are "(3)", "39201," or a single "401"), and the column-count gate plus
    the row-sum gate hold the county back if it ever does.

    `token_repairs` are the operator manifest's render-verified replacements
    for mangled cell tokens on this page, applied in assign_cells to tokens
    already bound to a numeric column (Warren p3/p6; see
    CellTokenRepairTests). The grid itself is built from numeric tokens AND
    the recap's printed X cells (X marks a blank/zero-recap position whose
    neighbors never vote): p5-p7's local-zone tails are X-heavy, and a
    column read only from numeric words would lose it (Warren p5 col10,
    p7 col "Porters Chapel"). X words never become values -- a blank is 0
    only when the row's own printed total proves it at assembly.

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
    numeric-grid line at this min_columns -- the cover page), or a table
    page whose column clusters all drop (no cluster with >=
    MIN_CLUSTER_MEMBERS members overlapping the first data line -- see
    grid_centers)."""
    words = [{"text": x.text, "x0": x.x0, "x1": x.x1, "top": x.top, "bottom": x.bottom}
             for x in page.words]
    lines = lines_from_words(words)
    table_top = find_table_top(lines, min_columns=min_columns)
    if table_top is None:
        return None  # not a table page (cover page)

    def band_words(lo, hi):
        return [x for ln in lines if lo <= ln["top"] < hi for x in ln["words"]]

    def prepared_text(word):
        # the manifest's render-verified replacement wins over the token it
        # repairs -- including tokens that already read digit-shaped (p3's
        # phantom '1' rides inside '5821') -- but only when the replacement
        # is itself a clean digit run; a malformed replacement is ignored
        # (the token keeps its own shape, and the printed-TOTAL gate flags
        # whatever it produces).
        if not token_repairs:
            return word["text"]
        replacement = token_repairs.get(word["text"])
        if (replacement is not None and DIGIT_RE.match(replacement)):
            return replacement
        return word["text"]

    def cell_shaped(x):
        # cell-selection sees the repaired token ('AO.' counts as the 484 it
        # prints); label words and prose never reach this test.
        return (looks_numeric(prepared_text(x), fuzzy)
                or x["text"].strip() in X_CELL_WORDS)

    band_lo = table_top - TABLE_TOP_Y_WINDOW
    anchor_words = [x for x in band_words(band_lo, table_top + TABLE_TOP_Y_WINDOW)
                    if cell_shaped(x)]
    # A grid word must clear the page's own digit height (see
    # CELL_HEIGHT_FLOOR): the anchor's data cells set the scale.
    heights = [x["bottom"] - x["top"] for x in anchor_words]
    min_height = (CELL_HEIGHT_FLOOR * sorted(heights)[len(heights) // 2]
                  if heights else 0.0)
    band = band_words(band_lo, float("inf"))
    x_cells = [x for x in band if x["text"].strip() in X_CELL_WORDS
               and x["bottom"] - x["top"] >= min_height]
    digits = [x for x in band if cell_shaped(x)
              and x["text"].strip() not in X_CELL_WORDS
              and x["bottom"] - x["top"] >= min_height]
    # The first data line anchors the grid; a +-TABLE_TOP_Y_WINDOW window
    # keeps cells that y-jitter split onto a follow-on line inside the anchor.
    anchor_digits = [x for x in anchor_words
                     if x["bottom"] - x["top"] >= min_height]
    # Widened to the clean digit tokens of up to the first THREE data lines
    # (see multi_line_anchor_digits / grid_centers): a text layer that reads
    # only part of that one line's cells (Jasper p2: 3 clean digits,
    # x 464..745) must not starve the grid of the columns its neighbors'
    # cells prove (x 281.5..745.5). Race-header lines are excluded up front:
    # their qualifier digits are exactly the Position/Place phantom geometry
    # (Union p4's mid-table Chancery header reprint).
    def is_header_line(text):
        return (parse_office(text, fuzzy) is not None
                or is_unparsed_header(text)
                or is_noise(text, fuzzy))

    anchor_digits.extend(
        d for d in multi_line_anchor_digits(
            lines, table_top,
            looks_like_cell=lambda wd: (looks_numeric(prepared_text(wd), fuzzy)
                                        and wd["text"].strip()
                                        not in X_CELL_WORDS),
            is_header_line=is_header_line)
        if d["bottom"] - d["top"] >= min_height)
    centers = grid_centers(digits, anchor_digits, filler_words=x_cells)
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
                         centers, fuzzy, conflicts=conflicts,
                         token_repairs=token_repairs)
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
    candidate rows). LABEL_REPAIRS applies word-wise to the classification
    text of every label line (candidate names AND office headers: Warren
    p2/p4's "United states-senatel" and p4's left-clipped "ancery Court ..."
    are office-label mangles); a header joined from a held-back fragment
    gets the completing line's top."""
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
        text = _repair_label(" ".join(x["text"] for x in label_words))
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
                "candidate": _repair_label(" ".join(tokens)),
                "party": party,
                "top": ln["top"], "bottom": max(x["bottom"] for x in label_words),
                "cells": {}}
        rows.append(cand)
        last_candidate = cand
        pending_header = None
    return rows


def assign_cells(rows, numeric_words, centers, fuzzy=False, conflicts=None,
                 token_repairs=None):
    """Map (row_index, column_center) -> votes by row y-band overlap.

    `fuzzy` repairs digit-shaped OCR confusions; `token_repairs` (an
    operator-manifest map of mangled token -> printed value, render-verified
    per page) applies first and only here, to tokens already chosen because
    they sit in a numeric column -- label text and prose never see it, and
    a replacement that fails the digit shape is ignored (the cell drops and
    the row's printed-TOTAL gate flags the loss).

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
        raw = word["text"]
        cleaned = digit_clean(raw, fuzzy)
        # the manifest's render-verified replacement wins over the token it
        # repairs -- INCLUDING tokens that already read digit-shaped (p3's
        # phantom '1' rides inside '5821'); a replacement that is not
        # itself a clean digit run is ignored, and the original token's
        # own fate decides.
        replacement = (token_repairs or {}).get(raw)
        if replacement is not None and DIGIT_RE.match(replacement):
            cleaned = replacement
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

# Optional manifest keys mapping page lists to behavior:
#   local_only_pages: pages the operator declares out of scope (local-race
#     recap pages; the no-local-offices convention keeps them unextracted
#     and unassembled, recorded under pd["skipped_local_pages"]).
#   carry_pages: pages whose FIRST rows continue the section the previous
#     page ended on instead of opening a new one -- the manifest-declared
#     answer to an ambiguity no in-page heuristic can settle (Warren p5/p6/p7:
#     the Circuit Court 9-2 row prints at the top of the next page group,
#     ahead of the local zone's first header box).
MANIFEST_OPTIONAL_LIST_KEYS = ("local_only_pages", "carry_pages")

# Optional manifest key for cell-token repairs, keyed per page:
#   "cell_token_repairs": {"<page>": {"<mangled token>": "<printed value>"}}
# Only tokens already bound to a numeric column pass through it (Task 7's
# evidence: Warren p3's phantom '1' glyph rides inside '5821'/'2731' and the
# page's Times-Italic glyphs print "484" while decoding "AO."), and every
# applied replacement faces the row's printed-TOTAL gate like any other cell.
MANIFEST_REPAIRS_KEY = "cell_token_repairs"

# Optional keys for operator-supplied cells (cells an OCR-corrupted text
# layer cannot deliver; values read from the page renders and arithmetic-
# checked against the printed county TOTAL). Both apply AFTER manifest
# alignment: they key cells by that page's 0-based column-order index in the
# manifest's left-to-right label order (a TOTAL column is referenced by its
# position index like any other), so they bind to the same normalized
# positions the labels do.
#
#   "operator_cells": {"<page>": {"<candidate name>": {"<index>": value}}}
#     Page-scoped repairs into rows ALREADY PARSED from that page: the named
#     row's parsed cell at that column position is replaced, a missed cell is
#     added. A candidate key matching no merged row from that page is a LOUD
#     manifest problem -- never silent.
#
#   "operator_rows": [<row>]
#     Identity-supplied rows for pages whose layer parses no usable candidate
#     row at all (row label garbage). Each entry carries the ballot identity
#     (key/office/district/seat/candidate/party) and cells per page. A parsed
#     row with the same identity receives the cells (mode 2: merge/override);
#     when no parsed row matches, the entry's own metadata defines a
#     synthetic candidate row whose cells come from the entry across pages
#     (mode 3, Lee's case) -- a parsed row under the same
#     (office, district, seat) that did NOT match is a LOUD collision,
#     because silently adding a synthetic twin would double-count the seat.
#     Operator rows face the printed-TOTAL gate like parsed rows.
#
#   "operator_provenance" (on an operator_rows row)
#     Free-text operator provenance/annotation on operator_rows rows, unread
#     by the parser (Jasper's Sullivan row carries the Holders-cell
#     adjudication pointer).
#
#   "operator_supply_pages": [<page>]
#     Pages whose text-layer parse is not used at all (Jasper p2-p5, then all
#     of Lee's p2-p9: no usable grid survives) -- never extracted, never a
#     page_missing/column_count gate problem, the scope decision is the
#     operator's. Their declared labels remain the position index the
#     operator read against, and they join the county's precinct universe
#     UNCONDITIONALLY by that same positional reading (an all-supply county
#     has no layer alignment to name its precincts; a partially-supplied
#     county's manifest may repeat the layer column groups -- the observed
#     instance -- but the labels join by position, not by repetition). Every
#     such page must be referenced by at least one operator cells/rows
#     entry: a supplied page with no operator content would silently
#     produce nothing. A county whose in-scope pages are all supplied is a
#     legitimate parse shape (see no_table_pages_reason).
MANIFEST_OPERATOR_CELLS_KEY = "operator_cells"
MANIFEST_OPERATOR_ROWS_KEY = "operator_rows"
MANIFEST_SUPPLY_KEY = "operator_supply_pages"


def page_number(value):
    """int(value) for a page-number-shaped manifest key, else None.

    str.isdigit() alone is not a page-number test ('²'.isdigit() is True
    while int('²') raises) and int() is not a guard, so every page-key
    block's guard AND parse share this one helper."""
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def manifest_numbers(manifest, key):
    """Int page numbers declared under manifest[key] (list of page strings or
    ints). A missing or shape-bad value degrades to an empty set -- the shape
    problem is load_manifest's record, this is only the tolerant reader."""
    entries = manifest.get(key) if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or isinstance(entries, (str, bytes)):
        return set()
    out = set()
    for entry in entries:
        if isinstance(entry, int) and not isinstance(entry, bool):
            out.add(entry)
            continue
        try:
            out.add(int(str(entry)))
        except (TypeError, ValueError):
            continue
    return out


def load_manifest(path):
    """Load + validate an operator header manifest. Returns (manifest, problems).

    `pages` maps 1-based page-number strings to that page's header labels
    left-to-right (exactly one entry equals `total_label` where the page
    carries a TOTAL column) and must be a dict of label-lists of strings;
    `total_label` must be a non-empty string; each of local_only_pages /
    carry_pages, when present, must be a list of page numbers, and every
    entry -- in those two lists and in every cell_token_repairs and
    operator_cells/operator_rows page key -- must reference a page the
    manifest declares under `pages`, and a page key that is not an integer
    (repairs, operator_cells, operator_rows) is recorded too (neither can
    bind to anything, so each is a {"kind": "manifest_shape"} problem; the
    tolerant readers ignore it, the gates hold the county at write time).
    Label truncations are the
    operator's to resolve; problems here are only missing required keys and
    {"kind": "manifest_shape", "key": ...} shape errors -- alignment
    problems are the assembly's (see normalize_page_labels / run_gates)."""
    with open(path) as fh:
        manifest = json.load(fh)
    problems = [{"kind": "manifest_missing_key", "key": key}
                for key in MANIFEST_REQUIRED_KEYS if key not in manifest]
    page_map = manifest.get("pages")
    pages_shape_bad = not isinstance(page_map, dict)
    if pages_shape_bad:
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
    for key in MANIFEST_OPTIONAL_LIST_KEYS:
        if key in manifest and (not isinstance(manifest[key], list)
                                or isinstance(manifest[key], (str, bytes))):
            problems.append({"kind": "manifest_shape", "key": key,
                             "problem": f"{key} must be a list of page "
                                        "numbers, got "
                                        f"{type(manifest[key]).__name__}"})
        elif (key in manifest
              and any(not isinstance(n, (str, int)) for n in manifest[key])):
            problems.append({"kind": "manifest_shape", "key": key,
                             "problem": f"{key} entries must be page "
                                        "numbers (string or int)"})
    repairs = manifest.get(MANIFEST_REPAIRS_KEY)
    declared = set()
    if not pages_shape_bad:
        for key in page_map:
            page = page_number(key)
            if page is not None:
                declared.add(page)

    def undeclared_pages(numbers):
        return [n for n in numbers if int(n) not in declared]

    for key in MANIFEST_OPTIONAL_LIST_KEYS:
        if pages_shape_bad or key not in manifest:
            continue
        missing = undeclared_pages(manifest_numbers(manifest, key))
        if missing:
            problems.append({"kind": "manifest_shape", "key": key,
                             "problem": "page "
                                        + ", ".join(str(m) for m in missing)
                                        + " not declared under pages"})
    if MANIFEST_REPAIRS_KEY in manifest:
        bad = None
        if not isinstance(repairs, dict) or isinstance(repairs, list):
            bad = ("must be a dict of page -> {mangled token: printed value},"
                   f" got {type(repairs).__name__}")
        elif any(not isinstance(m, dict) for m in repairs.values()):
            bad = "every page's repairs must be a dict of token -> value"
        elif any(not isinstance(tok, str) or not isinstance(val, str)
                 for page_repairs in repairs.values()
                 for tok, val in page_repairs.items()):
            bad = "every repair must map a mangled token string to a value string"
        if bad:
            problems.append({"kind": "manifest_shape",
                             "key": MANIFEST_REPAIRS_KEY, "problem": bad})
        else:
            # a page key that is not a page number cannot bind to a page
            # either: every such key is recorded, never crashed on and never
            # silently dropped
            numbers = {k: page_number(k) for k in repairs}
            for k, number in numbers.items():
                if number is None:
                    problems.append({
                        "kind": "manifest_shape", "key": MANIFEST_REPAIRS_KEY,
                        "problem": f"page key {k!r} is not a page number"})
            if not pages_shape_bad:
                missing = undeclared_pages(
                    n for n in numbers.values() if n is not None)
                if missing:
                    problems.append({
                        "kind": "manifest_shape", "key": MANIFEST_REPAIRS_KEY,
                        "problem": "page "
                                   + ", ".join(str(m) for m in missing)
                                   + " not declared under pages"})
    total_label = manifest.get("total_label")
    if not isinstance(total_label, str) or not total_label.strip():
        problems.append({"kind": "manifest_shape", "key": "total_label",
                         "problem": "total_label must be a non-empty string"})
    if MANIFEST_MIN_COLUMNS_KEY in manifest:
        bad = None
        overrides = manifest[MANIFEST_MIN_COLUMNS_KEY]
        if not isinstance(overrides, dict) or isinstance(overrides, list):
            bad = ("must be a dict of page -> floor (int >= "
                   f"{MIN_TABLE_TOP_FLOOR}), got {type(overrides).__name__}")
        else:
            # every bad key and every bad floor is recorded, uniformly with
            # the page-keyed operator blocks
            for key, value in overrides.items():
                page = page_number(key)
                if page is None:
                    problems.append({
                        "kind": "manifest_shape",
                        "key": MANIFEST_MIN_COLUMNS_KEY,
                        "problem": f"page key {key!r} is not a page "
                                   "number"})
                    continue
                if isinstance(value, bool) or not isinstance(value, int) \
                        or value < MIN_TABLE_TOP_FLOOR:
                    problems.append({
                        "kind": "manifest_shape",
                        "key": MANIFEST_MIN_COLUMNS_KEY,
                        "problem": f"page {page}'s floor must be an int "
                                   f">= {MIN_TABLE_TOP_FLOOR}, got "
                                   f"{value!r}"})
        if bad:
            problems.append({"kind": "manifest_shape",
                             "key": MANIFEST_MIN_COLUMNS_KEY, "problem": bad})
        elif not pages_shape_bad:
            missing = undeclared_pages(
                n for n in (page_number(k) for k in overrides)
                if n is not None)
            if missing:
                problems.append({
                    "kind": "manifest_shape",
                    "key": MANIFEST_MIN_COLUMNS_KEY,
                    "problem": "page "
                               + ", ".join(str(m) for m in missing)
                               + " not declared under pages"})
    if MANIFEST_OPERATOR_CELLS_KEY in manifest:
        bad = None
        cells = manifest[MANIFEST_OPERATOR_CELLS_KEY]
        if not isinstance(cells, dict) or isinstance(cells, list):
            bad = ("must be a dict of page -> {candidate: {column index: "
                   f"value}}, got {type(cells).__name__}")
        else:
            for page_key, candidates in cells.items():
                if not isinstance(candidates, dict) \
                        or isinstance(candidates, list):
                    bad = f"page {page_key!r}'s entries must be a dict of " \
                          "candidate name -> {column index: value}"
                    break
                for name, page_cells in candidates.items():
                    if not isinstance(page_cells, dict) \
                            or isinstance(page_cells, list):
                        bad = (f"page {page_key!r}'s {name!r} must be a "
                               "dict of column index -> value")
                        break
                    if not operator_cell_values(page_cells):
                        bad = (f"page {page_key!r}'s {name!r} carries no "
                               "int (or digit-string) cell values")
                        break
                if bad:
                    break
        if bad:
            problems.append({"kind": "manifest_shape",
                             "key": MANIFEST_OPERATOR_CELLS_KEY,
                             "problem": bad})
        else:
            # a page key that is not a page number cannot bind to a page
            # either: every such key is recorded, never dropped silently
            numbers = {k: page_number(k) for k in cells}
            for k, number in numbers.items():
                if number is None:
                    problems.append({
                        "kind": "manifest_shape",
                        "key": MANIFEST_OPERATOR_CELLS_KEY,
                        "problem": f"page key {k!r} is not a page number"})
            if not pages_shape_bad:
                missing = undeclared_pages(
                    n for n in numbers.values() if n is not None)
                if missing:
                    problems.append({
                        "kind": "manifest_shape",
                        "key": MANIFEST_OPERATOR_CELLS_KEY,
                        "problem": "page "
                                   + ", ".join(str(m) for m in missing)
                                   + " not declared under pages"})
    if MANIFEST_OPERATOR_ROWS_KEY in manifest:
        bad = None
        rows = manifest[MANIFEST_OPERATOR_ROWS_KEY]
        if not isinstance(rows, list) or isinstance(rows, (str, bytes)):
            bad = f"must be a list of row objects, got {type(rows).__name__}"
        else:
            for i, entry in enumerate(rows):
                if not isinstance(entry, dict):
                    bad = f"row {i} must be an object"
                    break
                if not isinstance(entry.get("key"), str) \
                        or not entry.get("key", "").strip():
                    bad = f"row {i} needs a non-empty 'key'"
                    break
                if not isinstance(entry.get("candidate"), str) \
                        or not entry.get("candidate", "").strip():
                    bad = f"row {i} ({entry.get('key')!r}) needs a " \
                          "non-empty 'candidate'"
                    break
                page_cells = entry.get("cells")
                if not isinstance(page_cells, dict) \
                        or isinstance(page_cells, list):
                    bad = f"row {i} ({entry.get('key')!r}) needs a dict of " \
                          "page -> {column index: value} under 'cells'"
                    break
                if not any(operator_cell_values(pc)
                           for pc in page_cells.values()
                           if isinstance(pc, dict) and not isinstance(pc, list)):
                    bad = f"row {i} ({entry.get('key')!r}) carries no int " \
                          "(or digit-string) cell values"
                    break
        if bad:
            problems.append({"kind": "manifest_shape",
                             "key": MANIFEST_OPERATOR_ROWS_KEY, "problem": bad})
        else:
            # a cells page key that is not a page number cannot bind to a
            # page either: every such key is recorded, never dropped silently
            numbers = []  # (key, page or None) per cells key, encounter order
            for entry in rows:
                for k in (entry.get("cells") or {}):
                    numbers.append((k, page_number(k)))
            for k, number in numbers:
                if number is None:
                    problems.append({
                        "kind": "manifest_shape",
                        "key": MANIFEST_OPERATOR_ROWS_KEY,
                        "problem": f"page key {k!r} is not a page number"})
            if not pages_shape_bad:
                missing = undeclared_pages(
                    {n for _, n in numbers if n is not None})
                if missing:
                    problems.append({
                        "kind": "manifest_shape",
                        "key": MANIFEST_OPERATOR_ROWS_KEY,
                        "problem": "page "
                                   + ", ".join(str(m) for m in missing)
                                   + " not declared under pages"})
    if MANIFEST_SUPPLY_KEY in manifest:
        bad = None
        if not isinstance(manifest[MANIFEST_SUPPLY_KEY], list) \
                or isinstance(manifest[MANIFEST_SUPPLY_KEY], (str, bytes)):
            bad = ("must be a list of page numbers, got "
                   f"{type(manifest[MANIFEST_SUPPLY_KEY]).__name__}")
        elif any(not isinstance(n, (str, int)) or isinstance(n, bool)
                 for n in manifest[MANIFEST_SUPPLY_KEY]):
            bad = "entries must be page numbers (string or int)"
        if bad:
            problems.append({"kind": "manifest_shape",
                             "key": MANIFEST_SUPPLY_KEY, "problem": bad})
        elif not pages_shape_bad:
            supply = manifest_numbers(manifest, MANIFEST_SUPPLY_KEY)
            missing = undeclared_pages(supply)
            if missing:
                problems.append({
                    "kind": "manifest_shape",
                    "key": MANIFEST_SUPPLY_KEY,
                    "problem": "page "
                               + ", ".join(str(m) for m in missing)
                               + " not declared under pages"})
            elif any(key in manifest
                     for key in (MANIFEST_OPERATOR_CELLS_KEY,
                                 MANIFEST_OPERATOR_ROWS_KEY)):
                # a supplied page no operator entry references would
                # silently produce nothing
                referenced = set()
                for page_key in operator_cell_entries(manifest):
                    try:
                        referenced.add(int(str(page_key)))
                    except ValueError:
                        continue
                for entry in operator_row_entries(manifest):
                    cells = entry.get("cells")
                    if not isinstance(cells, dict):
                        continue
                    for page_key in cells:
                        try:
                            referenced.add(int(str(page_key)))
                        except ValueError:
                            continue
                for num in sorted(supply - referenced):
                    problems.append({
                        "kind": "manifest_shape",
                        "key": MANIFEST_SUPPLY_KEY,
                        "problem": f"page {num} is declared "
                                   "operator-supplied but no "
                                   "operator_cells/operator_rows entry "
                                   "supplies it; its declared labels "
                                   "would silently produce nothing"})
    return manifest, problems


def page_token_repairs(manifest, number):
    """The manifest's render-verified cell-token repairs for one page
    (manifest["cell_token_repairs"]["<number>"]), or {} -- a shape-bad or
    absent declaration degrades to no repairs; load_manifest records the
    shape problem and the gates hold the county at write time."""
    repairs = manifest.get(MANIFEST_REPAIRS_KEY) \
        if isinstance(manifest, dict) else None
    if not isinstance(repairs, dict):
        return {}
    page_repairs = repairs.get(str(number))
    if not isinstance(page_repairs, dict):
        return {}
    return page_repairs


def operator_cell_entries(manifest):
    """The manifest's cell_token_repairs-analog map of per-page, per-candidate
    operator-read cells, or {} (tolerant reader: load_manifest records the
    shape problem and the gates hold the county)."""
    entries = manifest.get(MANIFEST_OPERATOR_CELLS_KEY) \
        if isinstance(manifest, dict) else None
    return entries if isinstance(entries, dict) else {}


def operator_row_entries(manifest):
    """The manifest's identity-supplied operator rows (list), or [] (tolerant
    reader; see operator_cell_entries)."""
    entries = manifest.get(MANIFEST_OPERATOR_ROWS_KEY) \
        if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or isinstance(entries, (str, bytes)):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def operator_cell_values(cells):
    """(position index, int value) pairs for one operator entry's cell map,
    skipping shape-bad entries (load_manifest records them)."""
    if not isinstance(cells, dict):
        return []
    out = []
    for key, value in cells.items():
        try:
            idx = int(str(key))
        except (TypeError, ValueError):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            continue
        try:
            val = int(value)
        except (TypeError, ValueError):
            continue
        out.append((idx, val))
    return out


def narrow_retry_numbers(manifest):
    """Manifest-declared TABLE page numbers a min_columns=2 retry may target:
    keys present in manifest["pages"], minus the local-only and the
    operator-supply pages. A narrow page's data lines carry too few numeric
    tokens for find_table_top's default (Warren p4/p7: Porters Chapel +
    TOTAL); the retry is bounded to declared pages so an undeclared page's
    prose can never table-top."""
    pages = manifest.get("pages")
    if not isinstance(pages, dict):
        return set()
    local_only = manifest_numbers(manifest, "local_only_pages")
    operator_supply = manifest_numbers(manifest, MANIFEST_SUPPLY_KEY)
    out = set()
    for key in pages:
        try:
            n = int(str(key))
        except ValueError:
            continue
        if n in local_only or n in operator_supply:
            continue
        out.add(n)
    return out


def no_table_pages_reason(manifest, table_pages, path):
    """The ValueError message for a parse that extracted no table pages at
    all, or None when an empty layer table-page set is legitimate and the
    assembly can still produce the county.

    Empty is legitimate exactly when every page the manifest DECLARES that
    is not local-only is an operator_supply page AND the manifest carries
    operator entries to supply them (operator_rows or operator_cells): the
    operator's grid is the county (pd["pages_used"] is simply empty; the
    precinct universe comes from the supply pages' declared labels). Two
    shapes still raise, because the assembly would be empty and every gate
    on it would look vacuously clean:

    * the manifest declares an in-scope, non-skipped table page that extraction
      attempted and yielded nothing (a scanned PDF, a mis-scoped page), and
    * every in-scope page is skipped but no operator entries exist to supply
      it.
    """
    if table_pages:
        return None
    entries = bool(operator_cell_entries(manifest)
                   or operator_row_entries(manifest))
    declared = manifest.get("pages") if isinstance(manifest, dict) else None
    extractable = set()
    local_only = manifest_numbers(manifest, "local_only_pages")
    operator_supply = manifest_numbers(manifest, MANIFEST_SUPPLY_KEY)
    for key in (declared or {}):
        try:
            num = int(str(key))
        except ValueError:
            continue
        if num in local_only or num in operator_supply:
            continue
        extractable.add(num)
    if extractable or not entries:
        return f"no table pages found in {path}"
    return None


MANIFEST_MIN_COLUMNS_KEY = "page_min_columns"
# find_table_top's floors below this would read prose as the table top; the
# one-retry-at-2 floor is the limit for pages whose narrow tail (Warren p4/p7)
# needs it.
MIN_TABLE_TOP_FLOOR = 2


def page_min_columns(manifest, number):
    """The manifest's declared find_table_top floor for one page
    (manifest["page_min_columns"]["<number>"] as an int >= 2), or None.

    A absent/shape-bad declaration degrades to None -- the shape problem is
    load_manifest's record, and the page keeps the default extraction
    behavior (gates hold the county at write time)."""
    overrides = manifest.get(MANIFEST_MIN_COLUMNS_KEY) \
        if isinstance(manifest, dict) else None
    if not isinstance(overrides, dict):
        return None
    value = overrides.get(str(number))
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def extraction_floors(manifest, number):
    """The min_columns attempts parse_county_pdf walks for one page, in try
    order: [(min_columns, authoritative), ...].

    [(3, False)] is the default: extract at find_table_top's usual floor,
    and -- for a manifest-declared TABLE page -- fall back to one
    non-authoritative retry at 2 on failure (narrow_retry_numbers), the
    pre-page_min_columns behavior kept verbatim for pages without the key.

    A page whose manifest declares page_min_columns (an int >= 2, bounded to
    declared pages) gets a SECOND attempt at that floor after the default
    one, and the declared attempt is authoritative: its result REPLACES the
    default pass's whenever it yields a table. The declared floor is the
    operator's render-checked statement about where this page's table top
    sits (Jasper p3 motivated the key: its min3 top landed on Guest's row,
    losing the four rows above it, while min2 reached the page's true first
    data line), so the wider view wins. A declared floor of 3 equals the
    default pass and adds
    nothing -- it is an explicit floor pin, so such pages give up the
    fallback retry-at-2 too; a floor below 2 is a load-time shape problem
    that degrades to the default behavior."""
    floors = [(3, False)]
    declared = page_min_columns(manifest, number)
    if declared is not None and declared != 3:
        floors.append((declared, True))
    elif declared is None and number in narrow_retry_numbers(manifest):
        floors.append((MIN_TABLE_TOP_FLOOR, False))
    return floors


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


def _name_border_relation(a, b):
    """True when two name keys relate the way a layer row relates to the
    print name an operator read:

    * equality;
    * word-boundary prefix -- the layer glued trailing tokens onto the name
      ('stanley sorey nonpartlsan' for 'Stanley Sorey');
    * word-boundary suffix ('lee jr.' for the tail of 'Roy Noble Lee Jr.');
    * leading truncation: the shorter 2+-token name is the tail of the
      longer one, cut inside a token each time ('ley sorey' for 'Stanley
      Sorey' -- the layer lost 'Stan'). One-token short names never relate
      this way (the 'ann' inside 'Joanne' coincidence), and no bare
      substring ('orey') ever does."""
    if a == b:
        return True
    if b.startswith(a + " ") or b.endswith(" " + a):
        return True
    if a.startswith(b + " ") or a.endswith(" " + b):
        return True
    return (_tail_truncation(a, b) or _tail_truncation(b, a))


def _tail_truncation(longer, shorter):
    """True when `shorter` (2+ tokens) is `longer` cut short at the head:
    aligned at the tail, the first shorter token is a PROPER suffix of the
    matching longer token and the remaining tokens are equal."""
    lt, st = longer.split(" "), shorter.split(" ")
    if len(st) < 2 or len(st) > len(lt):
        return False
    k = len(lt) - len(st)
    if not (len(lt[k]) > len(st[0]) and lt[k].endswith(st[0])):
        return False
    return st[1:] == lt[k + 1:]


def operator_match_rows(name, rows):
    """The candidate rows matching one operator row identity, by name.

    Exact name_key equality first; when nothing matches exactly, the
    word-boundary relation (_name_border_relation) against name_key -- an
    operator row met with partial layer names or a glued-on party token.
    Only rows are passed in that the caller already scoped (a page's merged
    rows, or all of them for the mode-3 race check)."""
    wanted = name_key(name)
    if not wanted:
        return []
    exact = [row for row in rows
             if name_key(row.get("candidate") or "") == wanted]
    if exact:
        return exact
    return [row for row in rows
            if _name_border_relation(wanted, name_key(row.get("candidate")
                                                      or ""))]


def _operator_positional_labels(manifest_pages, pno):
    """A declared page's manifest labels (list), or None."""
    labels = manifest_pages.get(str(pno)) \
        if isinstance(manifest_pages, dict) else None
    return labels if isinstance(labels, list) else None


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

    Local-only pages: manifest["local_only_pages"] pages the operator
    declares out of scope (local-race recaps under the no-local-offices
    convention) are SKIPPED -- never extracted by parse_county_pdf, and not
    assembled if a caller hands them in; each is recorded under
    pd["skipped_local_pages"] ({page, labels, reason}) and, unlike a
    declared TABLE page that fails extraction, is never reported as
    "page_missing". Their absence is therefore never a gate problem: the
    declaration itself is the scope decision. Operator-supply pages
    (manifest["operator_supply_pages"]) skip the same way -- their scope
    decision is that the text layer is not used, with the in-scope data
    arriving through the operator cells/rows entries; each is recorded under
    pd["operator_supply_pages"], and their declared labels join the county's
    precinct universe positionally (an all-supply county has no layer
    alignment to name its precincts -- Lee is such a county).

    Operator cells/rows (manifest["operator_cells"]/"operator_rows") apply
    AFTER the alignment and merge: each referenced (page, position index)
    maps through that page's manifest labels to a normalized precinct name
    (or the TOTAL marker), then overrides/adds that cell in the matched or
    operator-defined row. Pages the assembly aligned -- a layer page or an
    operator-supply one -- key through their recorded alignment; a page the
    layer failed to extract keeps the positional fallback (its manifest
    labels), but a LOCAL-ONLY page binds nothing (loud
    operator_cell_no_labels). Every application is recorded in
    pd["operator_cells_applied"] ({page, mechanism, key, candidate, column,
    precinct, old, new}); rows keep facing the printed-TOTAL gate.
    """
    if isinstance(manifest, str):
        manifest, mproblems = load_manifest(manifest)
    else:
        mproblems = []
    local_only = manifest_numbers(manifest, "local_only_pages")
    operator_supply = manifest_numbers(manifest, MANIFEST_SUPPLY_KEY)
    manifest_problems = list(mproblems)
    structure_problems = []
    conflicts = []
    dropped_local_rows = []
    skipped_local_pages = []
    operator_supply_records = []
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
        if pno in local_only or pno in operator_supply:
            continue  # declared out of scope: recorded below, never assembled
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
        alignments[pno] = {"names_by_center": by_center, "names": names,
                           "total_pos": total_pos, "labels": labels}
    supply_alignments = {}
    for key in sorted(manifest_pages, key=sort_key):
        pno = page_no(key)
        if pno in local_only:
            skipped_local_pages.append({"page": page_no(key),
                                        "labels": manifest_pages[key] or [],
                                        "reason": "local_only"})
        elif pno in operator_supply:
            labels = manifest_pages[key] or []
            operator_supply_records.append({"page": page_no(key),
                                            "labels": labels})
            # an operator-supply page's labels are position-indexed the same
            # way: they name the precinct universe the operator's cells key
            # into (an all-supply county has no layer alignment for them),
            # and their label problems are recorded like an alignment's
            names, total_pos, label_problems = normalize_page_labels(
                labels, total_label)
            for pr in label_problems:
                pr.setdefault("page", pno)
                (structure_problems if pr["kind"] == "empty_name"
                 else manifest_problems).append(pr)
            supply_alignments[pno] = {"names": names, "total_pos": total_pos,
                                      "labels": labels}
        elif key not in pages:
            manifest_problems.append({"kind": "page_missing", "page": page_no(key)})

    # The precinct universe: the aligned layer pages' labels PLUS every
    # operator-supply page's declared labels -- an UNCONDITIONAL union, since
    # a supply page's labels are a legitimate positional reading of the
    # county whatever the layer pages aligned to (an all-supply county has no
    # layer alignment at all and is named here). The observed partially-
    # supplied county happens to repeat the layer column groups, so that
    # union adds nothing in practice -- but the labels join by position, not
    # by repetition.
    all_names = sorted({name for al in alignments.values()
                        for name in al["names_by_center"].values()
                        if name and name != TOTAL_NAME}
                       | {name for supply in supply_alignments.values()
                          for name in supply["names"] if name})

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
    carry_numbers = manifest_numbers(manifest, "carry_pages")
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
        elif pno in carry_numbers:
            # manifest-declared carried opening: this page's FIRST rows
            # continue the section the previous page ended on, and the carry
            # refreshes exactly as a repeating group's does -- even though a
            # local-race header sits inside the page's stream after them
            # (Warren p5/p6/p7: Circuit Court 9-2's row prints at the top of
            # the next page group, ahead of the local zone's first header
            # box). No in-page signal distinguishes "opening rows continue a
            # section" from "opening rows are local-zone furniture", so the
            # operator declares the pages; undeclared pages keep the rule
            # below.
            pending = last_carry_used if last_carry_used is not None \
                else end_context
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
            if (office is None and not own_context and pending is not None
                    and row.get("cells")):
                # cross-page carry. The carry attributes DATA (a repeating
                # group's continuation rows, Union p5's Malski, Warren p5-p7's
                # Circuit 9-2 row): a row that captured no cell has nothing
                # to attribute and is not roster data -- invisible-layer
                # remnants of exactly this shape (Warren p7 prints a lone
                # 'i' word whose neighbors rows carry the data) drop to
                # dropped_local_rows instead of entering the carried race.
                office, district, seat = pending
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
            # the merged row's candidate spelling: the word layer keeps the
            # print's jitter ("Ron  Eller " -- doubled internal spaces, a
            # trailing space from the party-token split) so the candidate
            # name is normalized once here; name_key (shared with the writer)
            # additionally folds the punctuation variants the text layers
            # render.
            cand_name = NAME_WS_RE.sub(" ", row.get("candidate") or "").strip()
            entries.append((idx, (office, district, seat, name_key(cand_name)),
                            {"kind": "candidate", "office": office,
                             "district": district, "seat": seat,
                             "candidate": cand_name,
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

    # ---- operator cells / operator rows (applied after the alignment) ----
    #
    # Every entry's cells key on that page's 0-based column-order index in
    # the manifest's label order (a TOTAL column by its position like any
    # other), which resolves through the page's manifest labels to the same
    # normalized precinct names the parsed cells carry. Every application is
    # recorded; rows keep facing the printed-TOTAL gate.
    operator_applied = []

    def operator_labels_for(pno):
        # the labels an operator entry's cells key into come from an assembly
        # alignment when one exists -- an aligned layer page's, or an
        # operator-supply page's (both read positionally into the precinct
        # universe above). A LOCAL-ONLY page is out of scope and binds
        # nothing even though its declaration still carries labels (which can
        # repeat another page's real names): (None, None, None) makes
        # apply_operator_cells record operator_cell_no_labels instead. Any
        # other declared page keeps the positional fallback in order of
        # declaration (a page the layer failed to extract may still carry
        # operator cells -- the mode-3 ballot-order case).
        al = alignments.get(pno) or supply_alignments.get(pno)
        if al is not None:
            return al["labels"], al["names"], al["total_pos"]
        if pno in local_only:
            return None, None, None
        labels = _operator_positional_labels(manifest_pages, pno)
        if labels is None:
            return None, None, None
        names, total_pos, _ = normalize_page_labels(labels, total_label)
        return labels, names, total_pos

    def apply_operator_cells(mechanism, identity, target, pno, page_cells):
        """One entry's (position index -> value) map into one row."""
        labels, names, total_pos = operator_labels_for(pno)
        if names is None:
            manifest_problems.append(
                {"kind": "operator_cell_no_labels", "mechanism": mechanism,
                 "page": pno, **identity})
            return
        for idx, value in operator_cell_values(page_cells):
            if idx < 0 or idx >= len(names):
                manifest_problems.append(
                    {"kind": "operator_cell_position_out_of_range",
                     "mechanism": mechanism, "page": pno, "position": idx,
                     "labels": len(names), **identity})
                continue
            label = labels[idx] if labels and idx < len(labels) else str(idx)
            name = None if idx == total_pos else names[idx]
            if name is None and idx != total_pos:
                manifest_problems.append(
                    {"kind": "operator_cell_unlabeled_position",
                     "mechanism": mechanism, "page": pno, "position": idx,
                     "label": label, **identity})
                continue
            if name == TOTAL_NAME or (idx == total_pos and name is None):
                # a TOTAL-column cell: the operator read of the printed
                # county total becomes the row's total (recorded either way)
                old = target.get("total")
                if old is not None and old != value:
                    conflicts.append(
                        {"kind": "duplicate_total", "pages": target["pages"],
                         "candidate": target.get("candidate"),
                         "values": [old, value]})
                target["total"] = value
                precinct = TOTAL_NAME
            else:
                old = target["cells"].get(name)
                if name not in all_names:
                    structure_problems.append(
                        {"kind": "operator_cell_unknown_precinct",
                         "page": pno, "precinct": name,
                         "candidate": target.get("candidate"),
                         "value": value})
                elif old is not None and old != value:
                    conflicts.append(
                        {"kind": "conflicting_cells", "page": pno,
                         "candidate": target.get("candidate"),
                         "precinct": name, "values": [old, value]})
                target["cells"][name] = value
                precinct = name
            operator_applied.append(
                dict(identity, page=pno, mechanism=mechanism, column=label,
                     precinct=precinct, old=old, new=value))

    op_cells = operator_cell_entries(manifest)
    for pno_key in sorted(op_cells, key=sort_key):
        pno = page_no(pno_key)
        if pno is None:
            continue  # non-numeric page key: recorded as a shape problem
        # page-scoped and name-matched ONLY: the named row must be among the
        # merged rows this page produced -- repairs never create rows
        page_rows = [merged[k] for k in order
                     if pno in (merged[k].get("pages") or [])]
        for name in sorted(op_cells[pno_key]):
            matches = operator_match_rows(name, page_rows)
            entry_identity = {"key": name, "candidate": name}
            if len(matches) == 1 \
                    and name_key(matches[0]["candidate"] or "") \
                    != name_key(name):
                entry_identity["matched_layer"] = matches[0]["candidate"]
            if len(matches) > 1:
                manifest_problems.append(
                    {"kind": "operator_cell_ambiguous_match",
                     "page": pno, "candidate": name,
                     "matched": sorted(m["candidate"] for m in matches)})
                continue
            if not matches:
                manifest_problems.append(
                    {"kind": "operator_cell_no_row", "page": pno,
                     "candidate": name})
                continue
            apply_operator_cells("operator_cells", entry_identity,
                                 matches[0], pno, op_cells[pno_key][name])
    synthetic_keys = set()
    for entry in operator_row_entries(manifest):
        key = entry.get("key")
        candidate = (entry.get("candidate") or "").strip()
        office = entry.get("office")
        district = entry.get("district")
        seat = entry.get("seat")
        cells_by_page = (entry.get("cells")
                         if isinstance(entry.get("cells"), dict) else {})
        identity = {"key": key, "candidate": candidate or entry.get("candidate")}
        mkey = (office, district, seat, name_key(candidate))
        target = merged.get(mkey)
        matched_layer = None
        if target is None:
            # mode 2 with a partial layer name: the same race's parsed rows
            race_rows = [merged[k] for k in order
                         if k not in synthetic_keys
                         and (merged[k].get("office"), merged[k].get("district"),
                              merged[k].get("seat")) == (office, district, seat)]
            matches = operator_match_rows(candidate, race_rows)
            if len(matches) > 1:
                manifest_problems.append(
                    {"kind": "operator_cell_ambiguous_match", "key": key,
                     "candidate": candidate,
                     "matched": sorted(m["candidate"] for m in matches)})
                continue
            if matches:
                target = matches[0]
                matched_layer = target["candidate"]
        if target is None:
            referenced = [p for p in (page_no(k) for k in cells_by_page)
                          if p is not None]
            missing_meta = [f for f in ("candidate", "office")
                            if not str(entry.get(f) or "").strip()]
            if missing_meta:
                manifest_problems.append(
                    {"kind": "operator_row_missing_metadata", "key": key,
                     "missing": missing_meta, "pages": sorted(referenced)})
                continue
            races = sorted(merged[k]["candidate"] for k in order
                           if k not in synthetic_keys
                           and (merged[k].get("office"), merged[k].get("district"),
                                merged[k].get("seat")) == (office, district, seat))
            if races:
                manifest_problems.append(
                    {"kind": "operator_row_race_collision", "key": key,
                     "candidate": candidate,
                     "race": [office, district, seat], "parsed": races})
                continue
            row = {"kind": "candidate", "office": office, "district": district,
                   "seat": seat,
                   "candidate": NAME_WS_RE.sub(" ", candidate).strip(),
                   "party": (entry.get("party")
                             if isinstance(entry.get("party"), str) else None),
                   "total": None, "cells": {}, "orphan_cells": {},
                   "pages": sorted(set(referenced)),
                   "page": min(referenced) if referenced else None}
            # ballot order: the operator row belongs after the rows the
            # document printed at or before its own first referenced page
            insert_at = 0
            if row["page"] is not None:
                for pos, mkey_seen in enumerate(order):
                    if (merged[mkey_seen].get("page") or 0) <= row["page"]:
                        insert_at = pos + 1
            merged[mkey] = row
            synthetic_keys.add(mkey)
            order.insert(insert_at, mkey)
            target = row
        for pno_key in sorted(cells_by_page, key=sort_key):
            pno = page_no(pno_key)
            if pno is None:
                continue
            entry_identity = dict(identity)
            if matched_layer is not None:
                entry_identity["matched_layer"] = matched_layer
            apply_operator_cells("operator_rows", entry_identity, target, pno,
                                 cells_by_page[pno_key])
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
            "skipped_local_pages": skipped_local_pages,
            "operator_supply_pages": operator_supply_records,
            "operator_cells_applied": operator_applied,
            "conflicts": conflicts,
            "manifest_problems": manifest_problems,
            "structure_problems": structure_problems,
            "alignments": {str(pno): al for pno, al in sorted(alignments.items())},
            "pages_used": [page_no(key) for key in sorted(pages, key=sort_key)
                           if page_no(key) in alignments]}


def parse_county_pdf(pdf_path, county, manifest_path, fuzzy=False):
    """Whole-county parse under an operator header manifest (Amendment A).

    Extracts the manifest's table pages (natural_pdf stays lazily imported
    so the module imports without it), assembles them through
    parse_county_from_pages (the manifest is used ONLY there), and prepends
    the manifest load problems. Returns parse_county_from_pages' dict plus
    pd["page_count"]. Raises ValueError only for the empty-extraction shapes
    no_table_pages_reason distinguishes -- a PDF whose declared in-scope
    table pages all yielded nothing, or an all-skipped manifest with no
    operator entries (gate results on an empty parse would look vacuously
    clean). A county whose in-scope pages are ALL operator_supply_pages and
    whose manifest carries operator entries parses with an empty layer
    table-page set (Lee: the operator grid is the county,
    pd["pages_used"] == []).

    Two manifest-driven behaviors scope what is extracted, both bound to
    pages the manifest declares so undeclared pages can never shape the
    parse:

    * local-only pages (manifest["local_only_pages"]) are never extracted:
      the operator declares them out of scope, and their absence is not a
      gate problem (see parse_county_from_pages' skipped_local_pages);
    * a declared table page that find_table_top's default 3-column floor
      drops gets ONE retry at min_columns=2 (narrow_retry_numbers): Warren
      p4/p7 print only "Porters Chapel" + TOTAL, so a data line carries two
      numeric tokens; the retry never touches undeclared or local-only
      pages.

    A third binding, page_min_columns (extraction_floors), lets the operator
    declare per page which extraction floors run for it: after the default
    pass, an attempt at the declared floor runs and is authoritative -- its
    result replaces the default's whenever that floor yields a table (the
    declared floor is the operator's render-checked statement about where
    the page's table top actually sits; a declared 2 is the narrow-retry
    floor, so no duplicate attempt is appended)."""
    from natural_pdf import PDF  # lazy
    manifest, mproblems = load_manifest(manifest_path)
    local_only = manifest_numbers(manifest, "local_only_pages")
    operator_supply = manifest_numbers(manifest, MANIFEST_SUPPLY_KEY)
    pdf = PDF(str(pdf_path))
    pages = {}
    for i, page in enumerate(pdf.pages, start=1):
        if i in local_only or i in operator_supply:
            # manifest-declared out of scope; recorded at assembly. Operator-
            # supply pages' in-scope data arrives through the operator
            # entries, keyed on their declared labels.
            continue
        page_repairs = page_token_repairs(manifest, i)
        tp = None
        for min_columns, authoritative in extraction_floors(manifest, i):
            if tp is not None and not authoritative:
                break  # narrower non-authoritative floors only fill failure
            attempt = extract_table_page(page, fuzzy, min_columns=min_columns,
                                         token_repairs=page_repairs)
            if attempt is None:
                continue
            if authoritative:
                tp = attempt  # the operator-declared floor view wins
                break
            if tp is None:
                tp = attempt
        if tp is not None:
            pages[str(i)] = tp
    reason = no_table_pages_reason(manifest, pages, pdf_path)
    if reason:
        # a fully operator-supplied county (every in-scope page skipped, the
        # manifest carrying operator entries) parses with an empty layer
        # table-page set; see no_table_pages_reason for the shapes that stay
        # a hard error
        raise ValueError(reason)
    pd = parse_county_from_pages(pages, county, manifest)
    pd["manifest_problems"] = mproblems + pd["manifest_problems"]
    pd["page_count"] = len(pdf.pages)
    return pd


def run_gates(pd):
    """Gate results -> {"total_mismatches", "structure", "conflicts",
    "manifest", "party"}.

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

    party: {"kind": "unknown_party"} -- a candidate row whose party never
    resolved (None), so it would blank in the CSV. run_gates deliberately
    reads None and the deliberate "" value apart: "" there means the
    PRINTED ballot party was blank (Nonpartisan), never unknown. A None
    party is counted as a gate problem and holds the CSV back (main() only
    writes past it under --allow-gate-failures, knowingly). Union (every
    candidate on a verified roster) produces none.

    Roster consistency across counties stays with the batch stage (Task 9)
    and is deliberately not re-derived here."""
    problems = {"total_mismatches": [], "structure": [], "conflicts": [],
                "manifest": [], "party": []}
    names = pd.get("precinct_names") or []
    for row in pd.get("candidate_rows") or []:
        cells = row.get("cells") or {}
        total = row.get("total")
        office, district = row.get("office"), row.get("district")
        seat, cand_name = row.get("seat"), row.get("candidate")
        party = row.get("party")
        if party is None:
            problems["party"].append(
                {"kind": "unknown_party", "office": office,
                 "district": district, "seat": seat, "candidate": cand_name})
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


def check_roster_shared_races(county_parses):
    """Cross-county roster gate (the batch stage; the run_gates docstring
    deliberately leaves this here): every (office, district) race that 2+
    counties' parse dicts carry must carry the IDENTICAL (candidate, party)
    roster in each of them.

    county_parses: {county: parse_county_pdf/parse_county_from_pages dict}.

    A mismatched shared race is a whole-seat loss on one side (one county's
    two-candidate Court of Appeals pair, the other's single read), a party
    misread, or a candidate-name reading that diverged -- shapes no
    per-county gate can see, because every row's own arithmetic can be exact
    while a seat's row is missing everywhere in one county. Records are
    {"kind": "roster_mismatch", "race": [office, district],
    "rosters": [{"county", "candidates": [[candidate, party], ...]}]} with
    counties in name order and candidates sorted for a stable diff. Races a
    single county prints are beyond this gate's reach; empty/absent parses
    are tolerated (an empty parse is not a clean roster -- whether a county
    may parse at all stays the per-county gates' problem).

    Known blind spots, accepted for a gate that judges families: the
    (office, district) key is SEAT-BLIND, so a seat swap carrying an
    identical (candidate, party) set reads clean, and a None party is
    normalized to "" (the nonpartisan marker) rather than flagged -- unknown
    parties stay the per-county party gate's problem."""
    rosters = {}
    for county, pd in (county_parses or {}).items():
        for row in (pd.get("candidate_rows") or []):
            office, district = row.get("office"), row.get("district")
            candidate, party = row.get("candidate"), row.get("party")
            if not str(candidate or "").strip():
                continue  # a name-less row is no roster member
            rosters.setdefault(
                (office, district), {}).setdefault(
                county, set()).add((str(candidate), "" if party is None
                                    else str(party)))
    problems = []
    for race in sorted(rosters, key=str):
        by_county = rosters[race]
        if len(by_county) < 2:
            continue
        if len({frozenset(r) for r in by_county.values()}) <= 1:
            continue
        problems.append({
            "kind": "roster_mismatch",
            "race": [race[0], race[1]],
            "rosters": [{"county": county,
                         "candidates": sorted(
                             ([c, p] for c, p in by_county[county]),
                             key=lambda cp: (cp[0], cp[1]))}
                        for county in sorted(by_county)]})
    return problems


# The repo's row-per-result layout (2024/2026 precedent: no winner column --
# winners live in the county/statewide stage, and TOTAL rows are
# verification-only, never written).
CSV_FIELDS = ["county", "precinct", "office", "district", "candidate",
              "party", "votes"]

# Printed multi-seat qualifiers, keyed by office family. Consulted only
# when an (office, district) key carries two or more DISTINCT seats; a
# single ballot seat keeps the bare office label (2024 precedent).
SEAT_QUALIFIER = {
    "Court of Appeals": "Position",
    "Chancery Court": "Place",
    "Circuit Court": "Place",
}


def multi_seat_keys(pd):
    """(office, district) keys holding 2+ distinct seat values -> suffix.

    Per the approved two-seat rule: when two or more seats of the same
    office+district appear on the ballot, EVERY seat's office label gains
    the printed qualifier ("Court of Appeals Position 2", "Chancery Court
    Place 3"); with one seat the bare office label is kept (2024 precedent).

    None COUNTS as a seat value: a key mixing {2, None} is multi, and its
    seat-less rows reach write_precinct_csv's loud missing-seat raise
    instead of silently joining the seat-carrying race under a colliding
    bare label (the Task 3/R1 fuzzy seat-equality carry can lose exactly
    one row's seat on Jasper/Lee)."""
    seats = {}
    for r in pd["candidate_rows"]:
        key = (r["office"], r["district"])
        seats.setdefault(key, set()).add(r.get("seat"))
    return {key for key, s in seats.items() if len(s) > 1}


def _merge_key(row):
    """Ballot-order identity: same tuple parse_county_from_pages merges on
    (name_key -- the shared fold map, punctuation variants included) -- so
    the index built from it is each merged candidate row's first-seen
    position."""
    return (row["office"], row["district"], row.get("seat"),
            name_key(row.get("candidate")))


def write_precinct_csv(pd, out_path):
    """County parse dict -> OpenElections per-county precinct CSV.

    Header exactly county,precinct,office,district,candidate,party,votes
    (CRLF, csv-module default, matching the existing repo files). NO winner
    column, NO TOTAL rows. Rows sort by precinct name (case-insensitive);
    within a precinct, candidate rows keep ballot order -- their first-seen
    position in pd["candidate_rows"], since pd["precinct_names"] is a sorted
    name set and cannot carry it. district is "" when the race is not
    districted; party is "" when the printed ballot party was blank
    (Nonpartisan). A party value of None (unknown) is NOT silently blanked:
    run_gates records it under the "party" kind, so main() refuses to write
    the county unless --allow-gate-failures is passed (diagnosis only).

    Raises ValueError when the labels it would write are not one-to-one
    with the ballot races, because in all three cases bare labels would
    collide with the suffixed ones -- exactly what the qualifier exists to
    prevent:

    * a multi-seat (office, district) whose office family has no printed
      qualifier mapping,
    * a row inside such a key without a seat number (a lost seat-carry
      fragment -- Task 3/R1's fuzzy seat-equality carry on Jasper/Lee),
    * two distinct (office, district, seat) races resolving to ONE final
      (label, district), which additionally catches a qualifier folded into
      the office name (or a seat/district drift) on one page of an otherwise
      seat-carrying race. It does NOT catch total seat loss -- both races of
      a two-place race could each lose their qualifier and still write one
      bare label each; that residual is Task 9's cross-county roster gate
      comparing at the (office, district) family level."""
    import csv
    multi = multi_seat_keys(pd)
    order_index = {}
    for i, r in enumerate(pd["candidate_rows"]):
        order_index.setdefault(_merge_key(r), i)
    # final (label, district) -> the source (office, district, seat) races
    # behind it; the uniqueness gate consumes it below.
    identities = {}
    rows = []
    for r in pd["candidate_rows"]:
        office = r["office"]
        district = r["district"]
        if (office, district) in multi:
            qualifier = SEAT_QUALIFIER.get(office)
            seat = r.get("seat")
            if qualifier is None:
                seats = sorted(
                    {r2.get("seat") for r2 in pd["candidate_rows"]
                     if (r2["office"], r2["district"]) == (office, district)},
                    key=str)
                raise ValueError(
                    f"office {office!r} in district {district!r} carries two"
                    f" or more seats on the ballot ({seats}) but has no"
                    f" printed qualifier mapping in SEAT_QUALIFIER: writing"
                    f" bare labels would collide with the suffixed ones; add"
                    f" a mapping or investigate the parse")
            if seat is None:
                raise ValueError(
                    f"candidate {(r.get('candidate') or '')!r} under "
                    f"{office!r} district {district!r} carries no seat number"
                    f" while other rows of the same office+district are"
                    f" {qualifier}-qualified: a seat-carry fragment was lost"
                    f" (fuzzy header/carry bug); refusing to write a bare"
                    f" label that collides with the suffixed ones")
            office = f"{office} {qualifier} {seat}"
        identities.setdefault((office, district or ""), set()).add(
            (r["office"], district, r.get("seat")))
        key = _merge_key(r)
        for pname in pd["precinct_names"]:
            if pname in r["cells"]:
                # (precinct, ballot order) sort key kept OUT of the row dict
                # itself -- DictWriter would raise on the unknown field.
                rows.append((
                    (pname.lower(), order_index[key]),
                    {"county": pd["county"], "precinct": pname,
                     "office": office, "district": district or "",
                     "candidate": (r["candidate"] or "").strip(),
                     "party": r.get("party") or "",
                     "votes": r["cells"][pname]},
                ))
    colliding = {key: sources for key, sources in identities.items()
                 if len(sources) > 1}
    if colliding:
        (label, district), sources = next(iter(sorted(colliding.items())))
        raise ValueError(
            f"final office label {label!r} in district {district!r} would be"
            f" written for distinct ballot races {sorted(sources, key=str)}:"
            f" a seat qualifier was lost or two races resolved to one label")
    rows.sort(key=lambda pair: pair[0])
    with open(out_path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        wr.writeheader()
        wr.writerows(d for _, d in rows)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("--county", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fuzzy", action="store_true")
    ap.add_argument("--allow-gate-failures", action="store_true",
                    help="write the CSV even when gates flag problems (diagnosis only)")
    args = ap.parse_args(argv)
    pd = parse_county_pdf(args.pdf_path, args.county, args.manifest,
                          fuzzy=args.fuzzy)
    problems = run_gates(pd)
    n_bad = sum(len(v) for v in problems.values())
    for kind, items in problems.items():
        for item in items:
            print(f"  ! {kind}: {item}")
    print(f"{args.county}: {len(pd['candidate_rows'])} candidate rows, "
          f"{len(pd['precinct_names'])} precincts, "
          f"{len(pd.get('dropped_local_rows', []))} local rows dropped, "
          f"{len(pd.get('skipped_local_pages', []))} skipped local pages, "
          f"{len(pd.get('operator_supply_pages', []))} operator-supplied "
          f"pages, "
          f"{len(pd.get('operator_cells_applied', []))} operator cells "
          f"applied, "
          f"{n_bad} gate problem(s)")
    if n_bad == 0:
        write_precinct_csv(pd, args.out)
        print(f"  wrote {args.out}")
        return 0
    if args.allow_gate_failures:
        write_precinct_csv(pd, args.out)
        print(f"  wrote {args.out} ({n_bad} gate problem(s), diagnosis only)")
        return 0
    print("  gates FAILED; CSV not written")
    print("  rerun with --allow-gate-failures to write the CSV anyway"
          " (diagnosis only)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
