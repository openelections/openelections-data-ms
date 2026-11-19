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
import difflib  # total_col fuzzy header match; stdlib only

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
