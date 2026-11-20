"""Tests for the 2026 general text-layer county extractor.

Pure-function tests run everywhere. Integration tests read the real PDFs in
~/code/openelections-sources-ms/ and are skipped when that checkout is absent.
"""
import json
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

    def test_column_centers_mixed_digit_lengths_stay_one_column(self):
        # Real cells are right-aligned (x1 is the column's right edge), so x0
        # varies with digit length within one column; clustering must not
        # split a column just because its cells differ in digit count.
        digits = [w("168", 282.2, 150.0, x1=297.2), w("5", 292.1, 300.0, x1=297.1)]
        centers = ex.column_centers(digits)
        self.assertEqual(len(centers), 1)
        self.assertAlmostEqual(centers[0], 287.15)

    def test_column_centers_single_column_two_rows(self):
        digits = [w("188", 246, 150), w("190", 246, 300)]
        self.assertEqual(ex.column_centers(digits), [246.0])

    def test_column_centers_empty_input(self):
        self.assertEqual(ex.column_centers([]), [])

    def test_lines_from_words_sorts_shuffled_input(self):
        # Words arrive in arbitrary (top, x0) order: output must be sorted by
        # top, and within-line words re-sorted by x0 ("5" precedes "188" in
        # the input but not in the line).
        words = [w("190", 246, 300), w("5", 337, 152),
                 w("Chunky", 45, 100, x1=130), w("164", 291, 152),
                 w("188", 246, 152)]
        lines = ex.lines_from_words(words, y_tol=2.0)
        self.assertEqual([ln["top"] for ln in lines], [100, 152, 300])
        self.assertEqual([ln["text"] for ln in lines],
                         ["Chunky", "188 164 5", "190"])


class DigitTests(unittest.TestCase):
    def test_looks_numeric_accepts_plain_comma_and_signed(self):
        for text in ("188", "1,234", "-5"):
            self.assertTrue(ex.looks_numeric(text), repr(text))

    def test_looks_numeric_rejects_prose_fragments(self):
        for text in ("3rd", "(3)", "", "-"):
            self.assertFalse(ex.looks_numeric(text), repr(text))

    def test_fuzzy_rescue_only_when_enabled(self):
        self.assertFalse(ex.looks_numeric("5O"))
        self.assertTrue(ex.looks_numeric("5O", fuzzy=True))

    def test_digit_clean_fuzzy_mangles_label_text(self):
        # Exactly why fuzzy cleanup must only ever be applied to tokens chosen
        # because they sit in numeric columns: on label text it manufactures
        # digit soup.
        self.assertEqual(ex.digit_clean("MISSISSIPPI", True), "M1551551PP1")


class VerticalStackTests(unittest.TestCase):
    def build_table_chars(self):
        # Two columns at x=246 and x=291; precinct names stacked one char per y.
        # "Dist 1, Bellemont" style name with a comma is the classic landmine.
        chars = []
        for i, ch in enumerate("Bellemont"):
            chars.append(c(ch, 246.0, 120.0 + i * 9))
        chars.append(c(",", 246.0, 120.0 + 9 * 8))  # comma kerned onto the final char
        for i, ch in enumerate("Chunky"):
            chars.append(c(ch, 291.0, 120.0 + i * 9))
        # wide prose line to be excluded (spans across columns)
        for x in range(60, 400, 5):
            chars.append(c("x", float(x), 96.0))
        return chars

    def test_read_vertical_headers(self):
        # Header stacks end at top 192, so the header-region bound passes
        # them through at 200.0 while any body char (top >= 200) is dropped.
        chars = self.build_table_chars()
        got = ex.vertical_headers(chars, [246.0, 291.0], [(90.0, 100.0)], 200.0)
        self.assertEqual(got[246.0], "Bellemont,")
        self.assertEqual(got[291.0], "Chunky")

    def test_body_digit_runs_cannot_displace_header_stack(self):
        # Regression: the consumer passes ALL page chars. Below the table
        # top, body-cell digits share the column x and form rhythmic
        # vertical runs longer than any name, so best = longest used to
        # return that digit soup; max_top must drop body chars outright,
        # never merely let them be outranked.
        chars = []
        for i, ch in enumerate("Bellemont"):
            chars.append(c(ch, 246.0, 37.0 + i * 9))
        chars.append(c(",", 246.0, 37.0 + 9 * 8))  # comma kerned onto "t"
        for i, ch in enumerate("Chunky"):
            chars.append(c(ch, 291.0, 37.0 + i * 9))
        # 30 rows of single-digit body cells right under the column center,
        # starting below the table top: one rhythmic run per column.
        for i in range(30):
            chars.append(c("0123456789"[i % 10], 246.0, 130.0 + i * 9))
            chars.append(c("0123456789"[i % 10], 291.0, 130.0 + i * 9))
        got = ex.vertical_headers(chars, [246.0, 291.0], [], 118.0)
        self.assertEqual(got[246.0], "Bellemont,")
        self.assertEqual(got[291.0], "Chunky")

    def test_total_header_detected(self):
        chars = [c(ch, 700.0, 120.0 + i * 9) for i, ch in enumerate("TOTAL")]
        got = ex.vertical_headers(chars, [700.0], [], 200.0)
        self.assertEqual(ex.total_col(got), 700.0)

    def test_header_word_gap_becomes_space(self):
        chars = ([c(ch, 246.0, 120.0 + i * 9) for i, ch in enumerate("Dist")]
                 + [c(ch, 246.0, 120.0 + 4 * 9 + 6 + i * 9) for i, ch in enumerate("1")])
        got = ex.vertical_headers(chars, [246.0], [], 200.0)
        self.assertEqual(got[246.0], "Dist 1")

    def test_comma_kerned_mid_name_is_preserved(self):
        # The real "Lake, 1" landmine: the comma kerns onto a mid-name char
        # (same top), not only onto the final one; reading order must keep
        # it in place: "Bea" then comma-on-'a' then "lert".
        chars = ([c(ch, 246.0, 120.0 + i * 9) for i, ch in enumerate("Bea")]
                 + [c(",", 246.0, 120.0 + 2 * 9)]
                 + [c(ch, 246.0, 120.0 + (3 + i) * 9) for i, ch in enumerate("lert")])
        got = ex.vertical_headers(chars, [246.0], [], 300.0)
        self.assertEqual(got[246.0], "Bea,lert")

    def test_stray_char_in_rejected_gap_window_refuses_column(self):
        # A stray prose char landing on the column x whose gap falls in the
        # rejected in-between window (step + jitter < 12 <= word break)
        # contaminates the stack: the whole column refuses to None.
        chars = [c(ch, 246.0, 120.0 + i * 9) for i, ch in enumerate("Bellemont")]
        chars.append(c("x", 246.0, 192.0 + 12.0))
        got = ex.vertical_headers(chars, [246.0], [], 300.0)
        self.assertIsNone(got[246.0])

    def test_total_col_scores_every_column_not_first_hit(self):
        # A weak 3-char match ("Tot", ratio 0.75) must not win just because
        # it comes first in dict order; the best ratio at or above the
        # threshold decides.
        self.assertEqual(ex.total_col({246.0: "Tot", 700.0: "TOTAL"}), 700.0)

    def test_total_col_returns_none_without_total(self):
        self.assertIsNone(ex.total_col({246.0: "Chunky"}))

    def test_total_col_fuzzy_variant_detected(self):
        self.assertEqual(ex.total_col({246.0: "T0TAL"}), 246.0)

    def test_total_col_tie_breaks_to_smaller_center(self):
        # Equal ratios are order-dependent without a stated tie-break; the
        # smaller center must win regardless of dict insertion order.
        self.assertEqual(ex.total_col({700.0: "TOTAL", 246.0: "TOTAL"}), 246.0)


class LabelTests(unittest.TestCase):
    def test_office_parsing(self):
        cases = [
            ("United States-Senate", ("U.S. Senate", "", None)),
            ("US House Of Rep 01-1st Congressional District", ("U.S. House", "1", None)),
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
        self.assertEqual(ex.parse_office("US House 0f Rep 02- Znd Congresslonal Dlstrlct",
                                         fuzzy=True), ("U.S. House", "2", None))
        self.assertIsNone(ex.parse_office("Statew1de Electlon Management System"))

    def test_party_parsing(self):
        self.assertEqual(ex.party_of("Democrat"), "DEM")
        self.assertEqual(ex.party_of("Republican"), "REP")
        self.assertEqual(ex.party_of("Libertarian"), "LIB")
        self.assertEqual(ex.party_of("Independen"), "IND")
        self.assertEqual(ex.party_of("Independlent"), "IND")
        self.assertEqual(ex.party_of("Nonpartisan"), "")
        self.assertIsNone(ex.party_of("Chunky"))

    def test_noise_lines(self):
        noise = [
            "Page : 2", "Statewide Election Management System",
            "Votes cast in the County of Union, Mississippi on",
            "Official Recapitulation 2026 Federal General Election",
            "District 3 - Election Commissioner",
        ]
        for line in noise:
            self.assertTrue(ex.is_noise(line), line)
        self.assertFalse(ex.is_noise("Johnny Baucom Libertarian"))
        self.assertFalse(ex.is_noise("Pages Worrell"))

    def test_precinct_normalization(self):
        cases = [("01", "1"), ("Chunky", "Chunky"),
                 ("Dist. 1, Bellemont Precinct", "Dist. 1, Bellemont"),
                 ('"Airport"', "Airport"), ("Noxubee  12", "Noxubee 12"),
                 ("Bellemont,", "Bellemont")]
        for name, expected in cases:
            self.assertEqual(ex.precinct_norm(name), expected, name)

    def test_office_fuzzy_prefix_fallback(self):
        # A full-label ratio vs "US HOUSE OF REP"/"COURT OF APPEALS" never
        # reaches 0.7 on real-length labels; the fallback must compare the
        # label's leading characters instead, and the Court fallback must
        # take the DISTRICT digit run (leading number is the place number).
        # Fixtures use the OCR-layer mangles observed on these scans: letter
        # O where the district's leading zero prints, "Fep" for "Rep",
        # "Posltlon" for "Position".
        self.assertEqual(ex.parse_office("Court O Appeals 01-Dlstrlct 3 Posltlon 2",
                                         fuzzy=True), ("Court of Appeals", "3", 2))
        self.assertEqual(ex.parse_office("US House 0f Fep 02- Znd Congresslonal Dlstrlct",
                                         fuzzy=True), ("U.S. House", "2", None))

    def test_chancery_recovery(self):
        # Space after the hyphen defeats the strict pattern's old "-" anchor,
        # and "Destrict" needs a fuzzy branch symmetric to the Court one.
        self.assertEqual(ex.parse_office("Chancery Court 3- Chancery District 3 Place 2"),
                         ("Chancery Court", "3", 2))
        self.assertEqual(ex.parse_office("Chancery Court 3- Chancery Destrict 3", fuzzy=True),
                         ("Chancery Court", "3", None))

    def test_judicial_family_parsing(self):
        # Real label spellings (Warren p2/p3; Union p4/p5). The double-dash
        # family pairs district-place twice ("Court 9-2-... District 9-2");
        # the place is the second number of the first pair, or the Place
        # slot when one prints.
        self.assertEqual(ex.parse_office("Chancery Court 9-2-Chancery District 9-2"),
                         ("Chancery Court", "9", 2))
        self.assertEqual(ex.parse_office("Circuit Court 9-1-Circuit District 9-1"),
                         ("Circuit Court", "9", 1))
        self.assertEqual(ex.parse_office("Circuit Court 9-2-Circuit District 9-2"),
                         ("Circuit Court", "9", 2))
        self.assertEqual(ex.parse_office("Circuit Court 3-Circuit District 03 Place 1"),
                         ("Circuit Court", "3", 1))
        self.assertEqual(ex.parse_office("Circuit Court 3-Circuit District 03 Place 3"),
                         ("Circuit Court", "3", 3))
        self.assertEqual(ex.parse_office("Circuit Court 3-Circuit District 03"),  # no place
                         ("Circuit Court", "3", None))

    def test_judicial_family_fuzzy_rescue(self):
        # OCR-layer mangles, same digit-fallback logic as the Chancery branch.
        self.assertEqual(ex.parse_office("Circult Court 3-Circult Destrict 03 Place 1",
                                         fuzzy=True), ("Circuit Court", "3", 1))

    def test_office_empty_label_is_none(self):
        self.assertIsNone(ex.parse_office(""))

    def test_party_none_guards(self):
        # A Nonpartisan mangle returns "" (blank party), not-a-party text
        # returns None; call sites must test `is not None`.
        self.assertEqual(ex.party_of("Nonpartlsan"), "")
        self.assertIsNone(ex.party_of(""))
        self.assertIsNone(ex.party_of(" "))
        self.assertIsNone(ex.party_of("Ty Pinkins"))

    def test_precinct_norm_edges(self):
        cases = [('"“Airport”"', "Airport"), ("Bellemont,,", "Bellemont"),
                 ("Chunky Precinct 3", "Chunky Precinct 3"), ("5 Precinct", "5")]
        for name, expected in cases:
            self.assertEqual(ex.precinct_norm(name), expected, name)


class CellAssignmentTests(unittest.TestCase):
    def test_row_band_assignment(self):
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

    def test_digit_words_left_of_columns_ignored(self):
        rows = [{"kind": "candidate", "candidate": "A", "top": 200.0, "bottom": 212.0}]
        cells = ex.assign_cells(rows, [w("3", 100.0, 205.0)], [246.0])
        self.assertEqual(cells, {})

    def test_conflict_last_wins_recorded(self):
        # Two numeric words claim the same (row, column) within one band:
        # the LAST word wins, and the overwrite is reported. Real Warren p3
        # fires this (row 5 / Ron Eller: '76' and '1' both band onto the same
        # column at 333.12) -- before the conflicts list it was silent.
        rows = [{"kind": "candidate", "candidate": "A", "top": 200.0, "bottom": 212.0}]
        conflicts = []
        cells = ex.assign_cells(rows, [w("76", 328.0, 205.0), w("1", 338.0, 205.5)],
                                [333.12], conflicts=conflicts)
        self.assertEqual(cells, {(0, 333.12): 1})
        self.assertEqual(conflicts, [[0, 333.12, 76, 1]])


class LabelRowTests(unittest.TestCase):
    def make_lines(self, line_specs):
        """line_specs: list of (text, top) pairs rendered as label-band words."""
        words = []
        for text, top in line_specs:
            x = 45.0
            for tok in text.split(" "):
                words.append(w(tok, x, top))
                x += len(tok) * 5 + 4
        return words

    def run_rows(self, line_specs, label_x_max=240.0, fuzzy=False):
        return ex.label_rows(ex.lines_from_words(self.make_lines(line_specs)),
                             table_top=150.0, label_x_max=label_x_max, fuzzy=fuzzy)

    def run_rows_at(self, line_specs, table_top, label_x_max=240.0, fuzzy=False):
        return ex.label_rows(ex.lines_from_words(self.make_lines(line_specs)),
                             table_top=table_top, label_x_max=label_x_max, fuzzy=fuzzy)

    def test_office_then_candidates_with_party_lines(self):
        rows = self.run_rows([
            ("United States-Senate", 160.0),
            ("Scott Colom", 170.0), ("Democrat", 178.0),
            ("Cindy Hyde-Smith", 188.0), ("Republican", 196.0),
        ])
        self.assertEqual([r["kind"] for r in rows][:2], ["office", "candidate"])
        office = rows[0]
        self.assertEqual(office["office"], "U.S. Senate")
        cand = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual(cand[0]["candidate"], "Scott Colom")
        self.assertEqual(cand[0]["party"], "DEM")
        self.assertEqual(cand[1]["party"], "REP")
        self.assertEqual(cand[1]["district"], "")  # Senate district not applicable

    def test_noise_and_furniture_skipped(self):
        rows = self.run_rows([
            ("Page : 2", 160.0),
            ("United States-Senate", 170.0),
            ("Johnny Baucom", 180.0), ("Libertarian", 188.0),
        ])
        kinds = [r["kind"] for r in rows]
        self.assertEqual(kinds.count("office"), 1)
        cand = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual(len(cand), 1)
        self.assertEqual(cand[0]["party"], "LIB")

    def test_wrapped_office_label_continues(self):
        rows = self.run_rows([
            ("US House Of Rep 01-1st Congressional", 160.0),
            ("District", 168.0),
            ("Trent Kelly", 178.0), ("Republican", 186.0),
        ])
        offices = [r for r in rows if r["kind"] == "office"]
        self.assertEqual(len(offices), 1)
        self.assertEqual((offices[0]["office"], offices[0]["district"]), ("U.S. House", "1"))
        cand = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual([c["candidate"] for c in cand], ["Trent Kelly"])
        # "District" must not survive as a candidate row
        self.assertNotIn("District", [c["candidate"] for c in cand])

    def test_candidate_row_is_anchored_after_party(self):
        rows = self.run_rows([
            ("United States-Senate", 160.0),
            ("Cindy Hyde-Smith", 170.0),
            ("Scott Colom", 190.0), ("Democrat", 198.0),
        ])
        cand = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual(cand[0]["candidate"], "Cindy Hyde-Smith")
        self.assertIsNone(cand[0]["party"])  # trailing candidate without party word

    def test_trailing_party_token_belongs_to_this_line(self):
        # Real Union p2 geometry: the party word prints right of the name, in
        # its own column, on the candidate's OWN line. It must be stripped and
        # attached to the row built from this line -- not forwarded to the
        # candidate above it, and not left polluting the name.
        rows = self.run_rows([
            ("United States-Senate", 160.0),
            ("Amy Jones Republican", 170.0),
            ("Bob Smith", 180.0),
        ])
        cands = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual([(c["candidate"], c["party"]) for c in cands],
                         [("Amy Jones", "REP"), ("Bob Smith", None)])

    def test_label_repairs_fix_printed_names(self):
        # Union's invisible-Tesseract layer misreads printed tokens ("Scott
        # Colom" -> "Coiom", "Democrat" -> "Democra"); the mangled party token
        # still strips via PARTY_WORDS and the name comes back repaired.
        rows = self.run_rows([("Scott Coiom Democra", 160.0)])
        cand = rows[0]
        self.assertEqual((cand["candidate"], cand["party"]), ("Scott Colom", "DEM"))

    def test_continuation_refuses_candidate_name_lines(self):
        # The office regexes match by prefix, so without the wrap-vocabulary
        # gate the first candidate under a self-contained Court header would
        # be swallowed: the merged text "Court Of Appeals 01-District 1
        # Position 1 <name>" still parses as the same office.
        rows = self.run_rows([
            ("Court Of Appeals 01-District 1 Position 1", 160.0),
            ("Derek Dewayne Hopson Jr. Nonpartisan", 170.0),
            ("John Weddle", 180.0),
        ])
        offices = [r for r in rows if r["kind"] == "office"]
        self.assertEqual((offices[0]["office"], offices[0]["district"], offices[0]["seat"]),
                         ("Court of Appeals", "1", 1))
        cands = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual([c["candidate"] for c in cands],
                         ["Derek Dewayne Hopson Jr.", "John Weddle"])
        self.assertEqual(cands[0]["party"], "")  # Nonpartisan -> blank party

    def test_office_header_above_table_top_kept_fragments_skipped(self):
        # Real Union p2: the Senate header prints 23pt above the first data
        # row, below the certification blurb and the vertical-name-stack
        # fragments. Above the table top only office labels classify; blurb
        # text and stack bleed ("he County", "o") must never become candidates.
        band_words = []

        def band_line(text, top):
            x = 45.0
            for tok in text.split(" "):
                band_words.append(w(tok, x, top))
                x += len(tok) * 5 + 4

        band_line("he County", 40.0)
        band_line("o", 60.0)
        band_line("United States-Senate", 140.0)
        band_line("Scott Colom", 151.0)
        band_line("Democrat", 158.0)
        rows = ex.label_rows(ex.lines_from_words(band_words),
                             table_top=150.0, label_x_max=240.0)
        offices = [r for r in rows if r["kind"] == "office"]
        self.assertEqual(len(offices), 1)
        self.assertEqual(offices[0]["office"], "U.S. Senate")
        cands = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual([(c["candidate"], c["party"]) for c in cands],
                         [("Scott Colom", "DEM")])


    def test_judicial_headers_become_offices(self):
        # A double-dash judicial label flows exactly like the other families:
        # header row, then its candidates carry THAT office (Warren p2:
        # Vicki Roach Barnes / Penny B. Lawson ran under Chancery 9-2 before
        # the fix wrongly attributed them to Court of Appeals).
        rows = self.run_rows([
            ("Chancery Court 9-2-Chancery District 9-2", 160.0),
            ("Vicki  Roach  Barnes  Nonpartisan", 170.0),   # Warren p2 word spacing
            ("Toni Walker Terrett Nonpartisan", 180.0),
        ])
        offices = [r for r in rows if r["kind"] == "office"]
        self.assertEqual((offices[0]["office"], offices[0]["district"], offices[0]["seat"]),
                         ("Chancery Court", "9", 2))
        cands = [r for r in rows if r["kind"] == "candidate"]
        # "Vicki  Roach  Barnes " keeps Warren p2's raw word spacing (doubled
        # internal spaces, trailing space from the party-token split);
        # normalization is Task 5/6's job.
        self.assertEqual([(c["candidate"], c["office"], c["party"]) for c in cands],
                         [("Vicki  Roach  Barnes ", "Chancery Court", ""),
                          ("Toni Walker Terrett", "Chancery Court", "")])

    def test_local_race_headers_not_candidates(self):
        # Warren p5/p6 local-race section: labels the office parser does not
        # know must surface as unknown_header rows -- never as candidates
        # inheriting the previous (or no) office.
        rows = self.run_rows([
            ("Warren County-County Court Judge", 160.0),
            ("Election Commission I-Election Commissioner", 168.0),
            ("District 1", 176.0),
            ("JCJ District Central-Justice Court Judge", 184.0),
            ("Vicki Roach Barnes", 192.0), ("Democrat", 198.0),
        ])
        unknown = [r for r in rows if r["kind"] == "unknown_header"]
        self.assertEqual([r["text"] for r in unknown],
                         ["Warren County-County Court Judge",
                          "Election Commission I-Election Commissioner",
                          "District 1",
                          "JCJ District Central-Justice Court Judge"])
        cands = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual([(c["candidate"], c["party"]) for c in cands],
                         [("Vicki Roach Barnes", "DEM")])
        self.assertNotIn("office", unknown[0])  # no office attribution

    def test_candidate_lines_never_unknown_header(self):
        # The catch-all must not reach into name territory: a candidate with a
        # dash but no header keyword, and one whose name merely CONTAINS a
        # keyword inside a word ("Courtney"), stay candidates.
        rows = self.run_rows([
            ("Cindy Hyde-Smith Republican", 160.0),
            ("Courtney Smith Nonpartisan", 170.0),
        ])
        kinds = {r["kind"] for r in rows}
        self.assertEqual(kinds, {"candidate"})
        cands = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual([(c["candidate"], c["party"]) for c in cands],
                         [("Cindy Hyde-Smith", "REP"), ("Courtney Smith", "")])

    def test_wrapped_office_label_split_before_of(self):
        # A header may print before its "Of" (I6: "Court" / "Of Appeals
        # 01-District 3 Position 2"). Split headers print in header territory
        # above the first data row, so the fragment that alone parses as
        # nothing is held back and joins the next label line.
        rows = self.run_rows_at([
            ("Court", 180.0),
            ("Of Appeals 01-District 3 Position 2", 188.0),
            ("Johnny Baucom", 198.0), ("Libertarian", 205.0),
        ], table_top=194.0)
        offices = [r for r in rows if r["kind"] == "office"]
        self.assertEqual(len(offices), 1)
        self.assertEqual((offices[0]["office"], offices[0]["district"], offices[0]["seat"]),
                         ("Court of Appeals", "3", 2))
        cands = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual([(c["candidate"], c["party"]) for c in cands],
                         [("Johnny Baucom", "LIB")])


class GridCentersTests(unittest.TestCase):
    def test_qualifier_clusters_drop_outside_anchor_span(self):
        # Union p2: Position/Place qualifier digits form two phantom
        # ~45pt-pitch clusters LEFT of the grid. The first data line's own
        # cells bound the real columns, so the phantoms drop even though they
        # have 4 members -- the span overlap, not cluster size, is what
        # removes them.
        anchor = [w("18", 287.5, 208.0), w("15", 333.8, 208.0), w("7", 380.0, 208.0)]
        digits = anchor + [
            w("188", 282.2, 231.0), w("5", 292.3, 252.0),    # column 1
            w("164", 328.5, 231.0), w("170", 331.0, 252.0),  # column 2
            w("8", 378.0, 231.0), w("9", 382.0, 252.0),      # column 3
            w("1", 195.8, 364.0), w("1", 211.0, 477.6),      # qualifier cluster A (4 members)
            w("1", 246.0, 364.0), w("2", 245.9, 431.8),      # qualifier cluster B (4 members)
        ]
        centers = ex.grid_centers(digits, anchor)
        self.assertEqual(len(centers), 3)
        self.assertLess(min(centers), 290.0)

    def test_grid_centers_empty_inputs(self):
        self.assertEqual(ex.grid_centers([], [w("5", 246.0, 200.0)]), [])
        self.assertEqual(ex.grid_centers([w("5", 246.0, 200.0)], []), [])


@unittest.skipUnless(SOURCES_PRESENT, "sources checkout not present")
class UnionPage2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from natural_pdf import PDF
        cls.pdf = PDF(os.path.join(SOURCES_DIR, "Union_County_2026_general.pdf"))
        cls.tp = ex.extract_table_page(cls.pdf.pages[1], fuzzy=False)

    def test_page_detected_with_columns(self):
        self.assertIsNotNone(self.tp)
        self.assertGreaterEqual(len(self.tp["precinct_centers"]), 10)

    def test_office_stream_includes_all_sections(self):
        offices = {r["office"] for r in self.tp["rows"] if r["kind"] == "office"}
        self.assertIn("U.S. Senate", offices)
        self.assertIn("U.S. House", offices)
        self.assertIn("Court of Appeals", offices)

    def test_senate_roster_with_parties(self):
        senate = [r for r in self.tp["rows"] if r["kind"] == "candidate"
                  and r["office"] == "U.S. Senate"]
        self.assertEqual(
            {(r["candidate"], r["party"]) for r in senate},
            {("Scott Colom", "DEM"), ("Cindy Hyde-Smith", "REP"), ("Ty Pinkins", "IND")})

    def test_cells_attached_to_rows(self):
        cands = [r for r in self.tp["rows"] if r["kind"] == "candidate"]
        hyde = [r for r in cands if r["candidate"] == "Cindy Hyde-Smith"]
        self.assertTrue(hyde and hyde[0]["cells"], "no votes attached")
        vals = set(hyde[0]["cells"].values())
        self.assertIn(188, vals)
        self.assertIn(164, vals)
        for cand in cands:
            for col in cand["cells"]:
                self.assertIn(col, self.tp["precinct_centers"])

    def test_court_roster_names_repaired(self):
        # Union p2's Court of Appeals Position 1 roster, with the printed
        # name spelled out of the mangled text layer ("John weddie" ->
        # "John Weddle", verified against the rendered page).
        court1 = [r for r in self.tp["rows"] if r["kind"] == "candidate"
                  and r["office"] == "Court of Appeals" and r["seat"] == 1]
        self.assertEqual([(r["candidate"], r["party"]) for r in court1],
                         [("Derek Dewayne Hopson Jr.", ""), ("John Weddle", "")])


class AssemblyTests(unittest.TestCase):
    """Task 5: manifest-driven county assembly, TOTAL capture, gates."""

    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._tmpdir = tmp.name

    def tmpdir(self):
        return self._tmpdir

    def write_manifest(self, tmpdir, pages=None):
        m = {"county": "Synth", "source": "x.pdf", "election_date": "2026-11-03",
             "read_by": "operator-vision", "date": "2026-11-19", "total_label": "TOTAL",
             "pages": pages or {"2": ["P1", "P2", "TOTAL"], "3": ["P1", "P2", "TOTAL"]}}
        path = os.path.join(tmpdir, "m.json")
        with open(path, "w") as fh:
            json.dump(m, fh)
        return path

    def test_manifest_validation_and_alignment(self):
        # Two table pages whose ascending centers zip positionally with the
        # manifest's left-to-right labels; body cells re-key to precinct NAMES.
        def tp(center_xs, n_rows):
            rows = [{"kind": "candidate", "candidate": f"cand{i}", "party": "DEM",
                     "office": "U.S. Senate", "district": "", "seat": None,
                     "top": 200.0 + i, "bottom": 210.0 + i,
                     "cells": {c: 1 for c in center_xs}} for i in range(n_rows)]
            return {"precinct_centers": center_xs, "table_top": 200.0,
                    "rows": [{"kind": "office", "office": "U.S. Senate",
                              "district": "", "seat": None}] + rows,
                    "conflicts": []}

        pd = ex.parse_county_from_pages({"2": tp([246.0, 291.0], 2),
                                         "3": tp([246.0, 291.0], 2)},
                                        "Synth",
                                        self.write_manifest(self.tmpdir()))
        names = pd["precinct_names"]
        self.assertIn("P1", names)
        self.assertIn("P2", names)
        self.assertNotIn("TOTAL", names)
        for r in pd["candidate_rows"]:
            self.assertEqual(sorted(r["cells"]), ["P1", "P2"])
            self.assertIn("total", r)

    def test_count_mismatch_and_collision_flagged(self):
        def tp(center_xs, rows):
            return {"precinct_centers": center_xs, "table_top": 200.0,
                    "rows": rows, "conflicts": []}
        # 3 centers vs 2 labels -> manifest gate flags the page
        probs = ex.run_gates(
            ex.parse_county_from_pages(
                {"2": tp([246.0, 291.0, 337.0], [])},
                "Synth",
                self.write_manifest(self.tmpdir(), {"2": ["P1", "P2"]})))
        self.assertTrue(any(p["kind"] == "column_count" for p in probs["manifest"]))
        # two labels normalizing equal -> collision flagged
        probs2 = ex.run_gates(
            ex.parse_county_from_pages(
                {"2": tp([246.0, 291.0], [])},
                "Synth",
                self.write_manifest(self.tmpdir(), {"2": ["P1", "P1 "]})))
        self.assertTrue(any(p["kind"] == "name_collision" for p in probs2["manifest"]))

    def test_office_carry_across_pages(self):
        # page 3 opens with an office=None candidate under the p2 office row:
        # pending (office, district, seat) from the previous page must fill it.
        p2_rows = [{"kind": "office", "office": "Chancery Court", "district": "1",
                    "seat": 2, "raw": "Chancery Court 1-Chancery District 1 Place 2"}]
        p3_rows = [{"kind": "candidate", "candidate": "Malski", "party": "",
                    "office": None, "district": None, "seat": None,
                    "top": 200.0, "bottom": 208.0, "cells": {246.0: 5, 291.0: 6},
                    "total": 11},
                   {"kind": "unknown_header", "raw": "Justice Court x"}]
        pd = ex.parse_county_from_pages({"2": {"precinct_centers": [246.0, 291.0],
                                               "table_top": 200.0, "rows": p2_rows,
                                               "conflicts": []},
                                         "3": {"precinct_centers": [246.0, 291.0],
                                               "table_top": 200.0, "rows": p3_rows,
                                               "conflicts": []}},
                                        "Synth",
                                        self.write_manifest(self.tmpdir(),
                                                            {"2": ["P1", "P2", "TOTAL"],
                                                             "3": ["P1", "P2", "TOTAL"]}))
        malski = [r for r in pd["candidate_rows"] if r["candidate"] == "Malski"]
        self.assertEqual((malski[0]["office"], malski[0]["district"], malski[0]["seat"]),
                         ("Chancery Court", "1", 2))
        self.assertEqual(malski[0]["total"], 11)

    def test_cross_page_cell_conflict_flagged_and_missing_total(self):
        # same candidate + same precinct on two pages with DIFFERENT values
        def cand_row(value, name="A"):
            return {"kind": "candidate", "candidate": name, "party": "DEM",
                    "office": "U.S. Senate", "district": "", "seat": None,
                    "top": 200.0, "bottom": 208.0, "cells": {246.0: value}}
        probs = ex.run_gates(
            ex.parse_county_from_pages(
                {"2": {"precinct_centers": [246.0], "table_top": 200.0,
                       "rows": [cand_row(5)], "conflicts": []},
                 "3": {"precinct_centers": [246.0], "table_top": 200.0,
                       "rows": [cand_row(7)], "conflicts": []}},
                "Synth",
                self.write_manifest(self.tmpdir(), {"2": ["P1", "TOTAL"],
                                                    "3": ["P1", "TOTAL"]})))
        self.assertTrue(probs["conflicts"], probs)
        self.assertTrue(any(p["kind"] == "missing_total"
                            for p in probs["structure"]), probs)

    def test_blank_cells_zero_only_when_total_reconciles(self):
        # A missing body cell is a 0 only when the row's own printed total
        # equals the sum of its present cells; with no total at all the row
        # is flagged (missing_total), never silently zero-filled.
        def tp(cell_map, centers):
            return {"precinct_centers": centers, "table_top": 200.0,
                    "rows": [{"kind": "candidate", "candidate": "A", "party": "DEM",
                              "office": "U.S. Senate", "district": "", "seat": None,
                              "top": 200.0, "bottom": 208.0, "cells": cell_map}],
                    "conflicts": []}
        labels = {"2": ["P1", "P2", "TOTAL"]}
        pd = ex.parse_county_from_pages(
            {"2": tp({246.0: 5, 337.0: 5}, [246.0, 291.0, 337.0])},
            "Synth", self.write_manifest(self.tmpdir(), labels))
        self.assertEqual(pd["candidate_rows"][0]["cells"], {"P1": 5, "P2": 0})
        self.assertEqual(ex.run_gates(pd), {"total_mismatches": [], "structure": [],
                                            "conflicts": [], "manifest": []})
        probs = ex.run_gates(ex.parse_county_from_pages(
            {"2": tp({246.0: 5}, [246.0, 291.0, 337.0])},
            "Synth", self.write_manifest(self.tmpdir(), labels)))
        self.assertTrue(any(p["kind"] == "missing_total" for p in probs["structure"]),
                        probs)
        self.assertTrue(any(p["kind"] == "missing_precinct_cells"
                            for p in probs["structure"]), probs)


class CarryBoundaryTests(unittest.TestCase):
    """Review round: the office carry must refresh at EVERY page boundary
    (not only after a total-marker page), while a page that opens into a
    local section never inherits the previous page's federal context."""

    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._tmpdir = tmp.name

    def write_manifest(self, labels):
        m = {"county": "Synth", "source": "x.pdf", "election_date": "2026-11-03",
             "read_by": "operator-vision", "date": "2026-11-19", "total_label": "TOTAL",
             "pages": labels}
        path = os.path.join(self._tmpdir, "m.json")
        with open(path, "w") as fh:
            json.dump(m, fh)
        return path

    def test_carry_refreshes_on_every_page_boundary(self):
        # A repeat-columns group whose pages carry NO total marker at all
        # (the group's TOTAL column appears only on a later page): the carry
        # must refresh at every boundary, so an office=None opening row on
        # ANY page of the group carries the context its group began with --
        # never dropped into dropped_local_rows while the gates stay quiet.
        # Pages carry disjoint column groups, as the real recaps do.
        def page(centers, cells_for_x, cells_for_y):
            rows = [{"kind": "candidate", "candidate": "X", "party": "",
                     "office": None, "district": None, "seat": None,
                     "top": 210.0, "bottom": 218.0, "cells": cells_for_x}]
            if cells_for_y is not None:
                rows += [{"kind": "office", "office": "Office B", "district": "",
                          "seat": None},
                         {"kind": "candidate", "candidate": "Y", "party": "",
                          "office": "Office B", "district": "", "seat": None,
                          "top": 230.0, "bottom": 238.0, "cells": cells_for_y}]
            return {"precinct_centers": centers, "table_top": 200.0,
                    "rows": rows, "conflicts": []}
        labels = {"2": ["P1", "P2"], "3": ["P3"], "4": ["P4"]}
        pd = ex.parse_county_from_pages(
            {"2": {"precinct_centers": [246.0, 291.0], "table_top": 200.0,
                   "rows": [{"kind": "office", "office": "Office A",
                             "district": "", "seat": None},
                            {"kind": "candidate", "candidate": "X",
                             "party": "", "office": "Office A",
                             "district": "", "seat": None,
                             "top": 210.0, "bottom": 218.0,
                             "cells": {246.0: 1, 291.0: 2}}],
                   "conflicts": []},
             "3": page([246.0], {246.0: 3}, {246.0: 4}),
             "4": page([246.0], {246.0: 5}, {246.0: 6})},
            "Synth", self.write_manifest(labels))
        self.assertEqual(pd["dropped_local_rows"], [])
        by_name = {r["candidate"]: r for r in pd["candidate_rows"]}
        self.assertEqual(by_name["X"]["office"], "Office A")
        self.assertEqual(by_name["X"]["cells"],
                         {"P1": 1, "P2": 2, "P3": 3, "P4": 5})
        self.assertEqual(by_name["Y"]["office"], "Office B")
        self.assertEqual(by_name["Y"]["cells"], {"P3": 4, "P4": 6})

    def test_local_section_opener_never_carries_federal_context(self):
        # Warren p5/p6's shape: a repeat group whose pages open with a
        # local-race row and whose first header is an unknown_header -- the
        # previous page's federal end context must not leak onto them.
        def page(rows):
            return {"precinct_centers": [246.0], "table_top": 200.0,
                    "rows": rows, "conflicts": []}
        pd = ex.parse_county_from_pages(
            {"2": page([{"kind": "office", "office": "State Office",
                         "district": "", "seat": None},
                        {"kind": "candidate", "candidate": "W", "party": "",
                         "office": "State Office", "district": "", "seat": None,
                         "top": 210.0, "bottom": 218.0, "cells": {246.0: 1}}]),
             "3": page([{"kind": "candidate", "candidate": "C", "party": "",
                         "office": None, "district": None, "seat": None,
                         "top": 210.0, "bottom": 218.0, "cells": {246.0: 2}},
                        {"kind": "unknown_header", "text": "Local Judge"},
                        {"kind": "candidate", "candidate": "S", "party": "",
                         "office": None, "district": None, "seat": None,
                         "top": 230.0, "bottom": 238.0, "cells": {246.0: 3}}])},
            "Synth", self.write_manifest({"2": ["P1"], "3": ["P1"]}))
        self.assertEqual([(r["candidate"], r["office"])
                          for r in pd["candidate_rows"]],
                         [("W", "State Office")])
        self.assertEqual([(d["candidate"], d["page"], d["office"])
                          for d in pd["dropped_local_rows"]],
                         [("C", 3, None), ("S", 3, None)])


class CarryPinTests(unittest.TestCase):
    """Task 4 re-review carries (N1, N2) and the minor ordering pin."""

    def make_lines(self, line_specs):
        words = []
        for text, top in line_specs:
            x = 45.0
            for tok in text.split(" "):
                words.append(w(tok, x, top))
                x += len(tok) * 5 + 4
        return words

    def run_rows(self, line_specs):
        return ex.label_rows(ex.lines_from_words(self.make_lines(line_specs)),
                             table_top=150.0, label_x_max=240.0)

    def test_circuit_fuzzy_branch_is_district_first(self):
        # N1: Jasper p2's real mangled label is the district-first family
        # ("Circuit Court <d>-Circuit District <d> Place <p>"); the OCR mangle
        # hides the leading "1" of "13" inside the 'l3' token, so the digit
        # runs arrive as 13 / 1 and the old digits[1] reading keyed "1".
        self.assertEqual(ex.parse_office("Circuit  Court  l3-Circuit Distrlct 13 Placo 1",
                                         fuzzy=True), ("Circuit Court", "13", 1))
        # the place-less sibling keeps the district, no place (Jasper p3)
        self.assertEqual(ex.parse_office("circuit l3-circuit Distrlct 13 place Court",
                                         fuzzy=True), ("Circuit Court", "13", None))
        # district-first must not break the district-repeat-with-place family
        self.assertEqual(ex.parse_office("Circult Court 3-Circult Destrict 03 Place 1",
                                         fuzzy=True), ("Circuit Court", "3", 1))

    def test_unknown_header_clears_office_context(self):
        # N2: candidates after an unparseable local header carry NO office
        # (never the stale one); the wrap-shaped line after it stays a header.
        rows = self.run_rows([
            ("Court Of Appeals 01-District 1 Position 1", 160.0),
            ("Derek Dewayne Hopson Jr.", 170.0),
            ("Warren County-County Court Judge", 178.0),
            ("District 2", 186.0),
            ("Vicki Roach Barnes", 194.0),
        ])
        self.assertEqual([(o["office"], o["district"], o["seat"])
                          for o in rows if o["kind"] == "office"],
                         [("Court of Appeals", "1", 1)])
        self.assertEqual([r["text"] for r in rows if r["kind"] == "unknown_header"],
                         ["Warren County-County Court Judge", "District 2"])
        self.assertEqual([(c["candidate"], c["office"], c["district"], c["seat"])
                          for c in rows if c["kind"] == "candidate"],
                         [("Derek Dewayne Hopson Jr.", "Court of Appeals", "1", 1),
                          ("Vicki Roach Barnes", None, None, None)])

    def test_unknown_header_closes_stale_continuation(self):
        # A wrap-shaped line directly after the local header must not join the
        # still-open previous office and rewrite its district/seat.
        rows = self.run_rows([
            ("Court Of Appeals 01-District 1 Position 1", 160.0),
            ("Warren County-County Court Judge", 168.0),
            ("Position 2", 176.0),
        ])
        self.assertEqual([(o["office"], o["district"], o["seat"])
                          for o in rows if o["kind"] == "office"],
                         [("Court of Appeals", "1", 1)])
        self.assertEqual([r["kind"] for r in rows],
                         ["office", "unknown_header", "unknown_header"])

    def test_standalone_party_after_unknown_header_not_attached(self):
        # A standalone party word after a dual-classified (unknown_header)
        # line must not attach to the earlier candidate.
        rows = self.run_rows([
            ("United States-Senate", 160.0),
            ("Cindy Hyde-Smith Republican", 170.0),
            ("Warren County-County Court Judge", 178.0),
            ("Democrat", 186.0),
        ])
        self.assertEqual([(c["candidate"], c["party"], c["office"])
                          for c in rows if c["kind"] == "candidate"],
                         [("Cindy Hyde-Smith", "REP", "U.S. Senate")])


class LocalHeaderTests(unittest.TestCase):
    """SEMS local-race headers (school/municipal/territory/justice/
    consolidated vocabulary) and their wrapped fragments."""

    def make_lines(self, line_specs):
        words = []
        for text, top in line_specs:
            x = 45.0
            for tok in text.split(" "):
                words.append(w(tok, x, top))
                x += len(tok) * 5 + 4
        return words

    def run_rows(self, line_specs):
        return ex.label_rows(ex.lines_from_words(self.make_lines(line_specs)),
                             table_top=150.0, label_x_max=240.0)

    def test_local_race_vocabulary_classifies_header(self):
        # Real Union p4/p5 dashes-shape, and the one-line municipal form:
        # both are headers, never candidates. A candidate named like the
        # vocabulary ('John Justice') stays a candidate.
        self.assertTrue(ex.is_unparsed_header(
            "New Albany Added Territory-Added Territory"))
        self.assertTrue(ex.is_unparsed_header(
            "New Albany Municipal Separate School District"))
        self.assertTrue(ex.is_unparsed_header("Consolidated School District 2"))
        self.assertFalse(ex.is_unparsed_header("John Justice"))
        self.assertFalse(ex.is_unparsed_header("John Justice Republican"))
        self.assertFalse(ex.is_unparsed_header("Courtney Smith Nonpartisan"))
        self.assertFalse(ex.is_unparsed_header(
            "New Albany Municipal Separate School"))  # dash-less, no role tail

    def test_wrapped_local_header_consumes_fragments(self):
        # Real Union p4 bottom, in printed y-order: the header's first line,
        # its wrapped "New Albany Municipal Separate School" line, the garbled
        # third line ("District" read as 'LIstnCT'), then the definite
        # candidate line with its inline party token. The fragments extend
        # the header's text and never become candidate rows.
        rows = self.run_rows([
            ("Circuit Court 3-Circuit District 03 Place 3", 160.0),
            ("Kent E. Smith", 170.0),
            ("New Albany Added Territory-Added Territory", 178.0),
            ("New Albany Municipal Separate School", 186.0),
            ("LIstnCT", 194.0),
            ("I David Rainey Nonpartisan1", 202.0),
        ])
        unknowns = [r for r in rows if r["kind"] == "unknown_header"]
        self.assertEqual(len(unknowns), 1)
        self.assertEqual(unknowns[0]["text"],
                         "New Albany Added Territory-Added Territory"
                         " New Albany Municipal Separate School LIstnCT")
        cands = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual([(c["candidate"], c["office"], c["party"]) for c in cands],
                         [("Kent E. Smith", "Circuit Court", None),
                          ("I David Rainey", None, "")])

    def test_fragment_run_stops_at_party_token_lines(self):
        # A lone token followed by a standalone party token is a candidate
        # name, not a garbage fragment; the consumption must stop for it.
        rows = self.run_rows([
            ("Warren County-County Court Judge", 160.0),
            ("Bulger", 168.0),
            ("Democrat", 176.0),
            ("Next Person Republican", 184.0),
        ])
        unknowns = [r for r in rows if r["kind"] == "unknown_header"]
        self.assertEqual([u["text"] for u in unknowns],
                         ["Warren County-County Court Judge"])
        cands = [r for r in rows if r["kind"] == "candidate"]
        self.assertEqual([(c["candidate"], c["party"], c["office"]) for c in cands],
                         [("Bulger", "DEM", None),
                          ("Next Person", "REP", None)])

    def test_fragment_consumption_capped_at_three(self):
        # The run of consumed fragments per open header is bounded at 3:
        # a 4th fragment-shaped line classifies normally (a candidate row)
        # instead of extending the header forever.
        rows = self.run_rows([
            ("Warren County-County Court Judge", 160.0),
            ("LIstnCT", 168.0), ("u.strica", 176.0), ("garb1", 184.0),
            ("garb2", 192.0),
        ])
        self.assertEqual([r["text"] for r in rows if r["kind"] == "unknown_header"],
                         ["Warren County-County Court Judge LIstnCT u.strica garb1"])
        self.assertEqual([(c["candidate"], c["office"])
                          for c in rows if c["kind"] == "candidate"],
                         [("garb2", None)])

    def test_new_office_row_closes_fragment_run(self):
        # A newly-opened office section must close the local block: the
        # armed header never swallows lines that follow a later office row.
        rows = self.run_rows([
            ("Warren County-County Court Judge", 160.0),
            ("Chancery Court 9-2-Chancery District 9-2", 168.0),
            ("LIstnCT", 176.0),
        ])
        self.assertEqual([r["text"] for r in rows if r["kind"] == "unknown_header"],
                         ["Warren County-County Court Judge"])
        self.assertEqual([(o["office"], o["district"])
                          for o in rows if o["kind"] == "office"],
                         [("Chancery Court", "9")])
        self.assertEqual([(c["candidate"], c["office"])
                          for c in rows if c["kind"] == "candidate"],
                         [("LIstnCT", "Chancery Court")])

    def test_lone_name_token_survives_after_local_header(self):
        # The reviewer probe: a plausible single-token NAME after a local
        # header is a candidate, never a garbage fragment -- only
        # name-implausible tokens ('LIstnCT', 'u.strica') are consumable.
        rows = self.run_rows([
            ("Warren County-County Court Judge", 160.0),
            ("Justice Court District 1", 168.0),
            ("Bulger", 176.0),
            ("Two Word", 184.0),
        ])
        self.assertEqual([u["text"] for u in rows if u["kind"] == "unknown_header"],
                         ["Warren County-County Court Judge",
                          "Justice Court District 1"])
        self.assertEqual([(c["candidate"], c["office"])
                          for c in rows if c["kind"] == "candidate"],
                         [("Bulger", None), ("Two Word", None)])


class ManifestShapeTests(unittest.TestCase):
    """load_manifest shape validation: wrong shapes are recorded problems,
    never deep TypeErrors."""

    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._tmpdir = tmp.name

    def write_manifest(self, manifest):
        path = os.path.join(self._tmpdir, "m.json")
        with open(path, "w") as fh:
            json.dump(manifest, fh)
        return path

    def test_shape_failures_recorded(self):
        for bad, key in (({"county": "X", "source": "s", "total_label": "TOTAL",
                           "pages": ["P1", "TOTAL"]}, "pages"),
                         ({"county": "X", "source": "s", "total_label": "  ",
                           "pages": {"2": ["P1"]}}, "total_label"),
                         ({"county": "X", "source": "s", "total_label": "TOTAL",
                           "pages": {"2": ["P1", 5]}}, "pages"),
                         ({"county": "X", "source": "s", "total_label": "TOTAL",
                           "pages": {"2": "P1"}}, "pages")):
            manifest, problems = ex.load_manifest(self.write_manifest(bad))
            self.assertTrue(any(p.get("kind") == "manifest_shape"
                                and p.get("key") == key for p in problems), problems)

    def test_bad_pages_shape_degrades_without_crash(self):
        # A recorded-bad pages shape must degrade to page_unlabeled records
        # plus the manifest_shape record -- loud but never an exception
        # (the page-missing loop used to raise TypeError on list items).
        tp = {"precinct_centers": [246.0], "table_top": 200.0,
              "rows": [{"kind": "candidate", "candidate": "A", "party": "",
                        "office": "U.S. Senate", "district": "", "seat": None,
                        "top": 210.0, "bottom": 218.0, "cells": {246.0: 5}}],
              "conflicts": []}
        bad_pages = (["P1", "TOTAL"], [["2", ["P1"]], ["3", ["P1"]]],
                     {"2": "P1"})
        for pages_value in bad_pages:
            manifest = {"county": "X", "source": "s", "total_label": "TOTAL",
                        "pages": pages_value}
            path = self.write_manifest(manifest)
            pd = ex.parse_county_from_pages({"2": tp, "3": tp}, "X", path)
            probs = ex.run_gates(pd)
            self.assertTrue(any(p["kind"] == "manifest_shape"
                                for p in probs["manifest"]), probs)

    def test_good_manifest_clean(self):
        good = {"county": "X", "source": "s", "total_label": "TOTAL",
                "pages": {"2": ["P1", "TOTAL"]}}
        manifest, problems = ex.load_manifest(self.write_manifest(good))
        self.assertEqual(problems, [])
        self.assertEqual(manifest["pages"]["2"], ["P1", "TOTAL"])


@unittest.skipUnless(SOURCES_PRESENT, "sources checkout not present")
class UnionCountyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pd = ex.parse_county_pdf(
            os.path.join(SOURCES_DIR, "Union_County_2026_general.pdf"),
            "Union",
            manifest_path=os.path.join(REPO, "2026/header-reads/"
                                       "20261103__ms__general__union__headers.json"))
        cls.problems = ex.run_gates(cls.pd)

    def test_gates_clean(self):
        self.assertEqual(self.problems["total_mismatches"], [])
        self.assertEqual(self.problems["manifest"], [])
        self.assertEqual(self.problems["structure"], [])
        self.assertEqual(self.problems["conflicts"], [])

    def test_all_candidates_have_full_cells_and_total(self):
        for r in self.pd["candidate_rows"]:
            self.assertEqual(len(r["cells"]), 20, r["candidate"])
            self.assertEqual(sum(r["cells"].values()), r["total"])

    def test_school_rows_in_dropped_local_rows(self):
        # The New Albany local-race block routes through unknown_header; its
        # only candidate rows are recorded whole (raw text + captured cells,
        # best-effort re-keyed where the manifest alignment resolves them,
        # the TOTAL-column capture kept verbatim), never merged into any
        # reconciled figure, and absent from candidate_rows.
        dropped = self.pd["dropped_local_rows"]
        self.assertEqual([d["candidate"] for d in dropped],
                         ["I David Rainey", "(David Rainey"])
        self.assertEqual([d["page"] for d in dropped], [4, 5])
        self.assertEqual([d["office"] for d in dropped], [None, None])
        self.assertEqual([d["cells"] for d in dropped],
                         [{"Glenfield": 1, "Sportsplex": 1,
                           "Central Maintenance": 3261},
                          {"Beacon Hill": 261, "Hillcrest Church": 1,
                           "Center": 76, "Watson Grove Church": 1301,
                           "Keownville": 2691, "Pleasant Ridge": 891,
                           "TOTAL": 9161}])
        names = {r["candidate"] for r in self.pd["candidate_rows"]}
        self.assertFalse(names & {"I David Rainey", "(David Rainey",
                                  "New Albany Added Territory-Added Territory",
                                  "New Albany Municipal Separate School",
                                  "LIstnCT", "u.strica"})
        self.assertEqual(len(self.pd["candidate_rows"]), 18)

    def test_row_block_merging(self):
        by_name = {r["candidate"]: r for r in self.pd["candidate_rows"]}
        self.assertEqual(by_name["Scott Colom"]["total"], 2055)
        self.assertEqual(by_name["Cindy Hyde-Smith"]["total"], 6761)
        self.assertEqual(by_name["Michael Malski"]["total"], 7629)
        self.assertEqual(by_name["Michael Malski"]["office"], "Chancery Court")
        malski = by_name["Michael Malski"]
        self.assertEqual(sum(malski["cells"].values()), 7629)

    def test_races_office_stream(self):
        offices = {(r["office"], r["district"]) for r in self.pd["candidate_rows"]
                   if r["office"] is not None}
        self.assertIn("U.S. Senate", {o for o, _ in offices})
        self.assertIn("Chancery Court", {o for o, _ in offices})
        self.assertIn("Circuit Court", {o for o, _ in offices})
        house = [r for r in self.pd["candidate_rows"] if r["office"] == "U.S. House"]
        self.assertEqual({(r["candidate"], r["party"])
                          for r in house if r["district"] == "1"},
                         {("Johnny Baucom", "LIB"), ("Cliff Johnson", "DEM"),
                          ("Trent Kelly", "REP")})


if __name__ == "__main__":
    unittest.main()
