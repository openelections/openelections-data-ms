"""Tests for the 2026 general text-layer county extractor.

Pure-function tests run everywhere. Integration tests read the real PDFs in
~/code/openelections-sources-ms/ and are skipped when that checkout is absent.
"""
import io
import json
import os
import re
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

    def test_widened_anchor_binds_grid_span_over_three_data_lines(self):
        # Jasper p2 shape: the FIRST data line carries only 3 clean OCR digits
        # (x 464..745), so the one-line anchor dropped the five left clusters
        # (x 281..429). Widening the anchor reference to the first THREE data
        # lines' clean digit spans -- their union bounds the grid -- recovers
        # them; the x~246 '1'-debris cluster (3 members around fragment lines,
        # y 353/490/523) still drops because no data line reaches that far
        # left (span lo stays at 281.5).
        line1 = [w("8", 464.0, 200.3), w("101", 601.2, 201.1),
                 w("602", 735.8, 199.1)]
        line2 = [w("152", 510.5, 221.1), w("217", 735.5, 220.8)]
        line3 = [w("156", 281.5, 222.2), w("1281", 464.8, 222.3)]
        body = line1 + line2 + line3 + [
            # five left-column clusters, 3+ members each
            w("3", 291.2, 243.9), w("155", 286.2, 289.6), w("1", 288.0, 331.0),
            w("39", 327.2, 288.8), w("11", 332.6, 243.5), w("251", 331.1, 287.1),
            w("281", 373.0, 288.5), w("1", 378.7, 244.7), w("220", 380.9, 309.6),
            w("22", 418.7, 288.1), w("7", 428.8, 242.8), w("127", 419.4, 309.3),
            w("1", 470.2, 244.8), w("139", 464.8, 309.3), w("1", 474.5, 251.9),
            w("1", 511.0, 244.5), w("1", 508.5, 262.0), w("11", 513.0, 242.4),
            w("233", 737.0, 242.5), w("9", 739.0, 242.1),
            # the junk '1'-debris cluster, x ~246 (three members)
            w("1", 245.9, 353.7), w("1", 246.0, 490.1), w("1", 246.2, 523.4),
        ]
        centers = ex.grid_centers(body, line1 + line2 + line3)
        self.assertEqual(len(centers), 7)
        self.assertGreater(min(centers), 280.0)
        self.assertFalse(any(abs(c - 246.0) < 10.0 for c in centers))
        # contrast: the OLD one-line anchor loses the left five
        self.assertEqual(len(ex.grid_centers(body, line1)), 3)


class MultiLineAnchorTests(unittest.TestCase):
    """Fix 1: multi_line_anchor_digits collects the clean digit tokens of up
    to the first THREE data lines (y >= table_top) -- not just the table's
    first line -- so grid_centers' span check measures the widened union."""

    LINES_WORDS = [
        ("United States-Senate", 150.0, 176.8),
        ("8", 464.0, 200.3), ("101", 601.2, 202.3), ("602", 735.8, 200.4),
        ("Scott Colom", 42.8, 208.4),                    # no clean digits
        ("156", 281.5, 220.3), ("1281", 464.8, 220.4),   # 2nd collecting line
        ("230", 326.9, 240.3), ("152", 510.5, 240.3),    # 3rd collecting line
        ("1", 245.9, 353.7),                             # beyond the cap
        ("1", 246.0, 490.1),
    ]

    def lines(self):
        return ex.lines_from_words([w(*spec) for spec in self.LINES_WORDS])

    def test_collects_first_three_lines_with_clean_digits(self):
        digits = ex.multi_line_anchor_digits(
            self.lines(), 199.14299999999997,
            lambda wd: ex.looks_numeric(wd["text"]))
        self.assertEqual([(d["text"], round(d["x0"], 1)) for d in digits],
                         [("8", 464.0), ("101", 601.2), ("602", 735.8),
                          ("156", 281.5), ("1281", 464.8),
                          ("230", 326.9), ("152", 510.5)])
        # the y-jitter pair line without clean digits and the capped-out
        # later fragment '1's never enter the anchor
        self.assertEqual(len(digits), 7)

    def test_no_data_line_with_digits_yields_nothing(self):
        lines = ex.lines_from_words([w("cover page", 40.0, 30.0)])
        self.assertEqual(ex.multi_line_anchor_digits(
            lines, 200.0, lambda wd: ex.looks_numeric(wd["text"])), [])

    def test_office_header_lines_never_widen_the_anchor(self):
        # Union p4 reprints its Chancery header mid-table; its qualifier
        # digits ('1' at 208.3, '3' at 242.6) are the Position/Place phantom
        # geometry and must not widen the span over them.
        words = [
            w("171", 279.6, 185.8), w("158", 325.7, 185.8),
            w("Chancery Court", 45.6, 206.6), w("1-Chancery", 118.3, 206.6),
            w("District", 172.1, 206.6), w("1", 208.3, 206.6),
            w("Place", 216.2, 206.6), w("3", 242.6, 206.6),
            w("169", 279.6, 231.6), w("156", 325.7, 231.6),
        ]
        lines = ex.lines_from_words(words)
        digits = ex.multi_line_anchor_digits(
            lines, 185.52839999999998,
            lambda wd: ex.looks_numeric(wd["text"]),
            is_header_line=lambda text: (
                ex.parse_office(text) is not None
                or ex.is_unparsed_header(text)
                or ex.is_noise(text)))
        xs = sorted(d["x0"] for d in digits)
        self.assertEqual(xs, [279.6, 279.6, 325.7, 325.7])

    def test_unknown_header_lines_never_widen_the_anchor(self):
        # Warren's unparseable local-office labels route through
        # is_unparsed_header; 'District 1' carries a bare qualifier numeral.
        words = [
            w("5", 292.3, 205.0), w("7", 333.4, 205.0),
            w("Election Commission", 45.0, 240.0),
            w("I-Election Commissioner", 130.0, 240.0),
            w("District 1", 60.0, 260.0),
            w("9", 292.0, 292.0),
        ]
        lines = ex.lines_from_words(words)
        digits = ex.multi_line_anchor_digits(
            lines, 205.0, lambda wd: ex.looks_numeric(wd["text"]),
            is_header_line=lambda text: (
                ex.parse_office(text) is not None
                or ex.is_unparsed_header(text)
                or ex.is_noise(text)))
        self.assertEqual([(d["text"], round(d["x0"], 1)) for d in digits],
                         [("5", 292.3), ("7", 333.4), ("9", 292.0)])

    def test_stops_before_the_cap_when_lines_run_out(self):
        words = [w("Row", 42.0, 210.0), w("5", 292.3, 210.0)]
        digits = ex.multi_line_anchor_digits(ex.lines_from_words(words), 210.0,
                                             lambda wd: ex.looks_numeric(wd["text"]))
        self.assertEqual([d["text"] for d in digits], ["5"])


class PageMinColumnsTests(unittest.TestCase):
    """Fix 2: the manifest key page_min_columns declares, per table page, the
    floor parse_county_pdf's table-top retry may drop to (Jasper p3: min2, so
    the top reaches the first candidate row the min3 default loses) -- bounded
    to declared pages, min value 2, and pages without the key keep the
    previous behavior exactly."""

    BASE = {"county": "Synth", "source": "x.pdf", "total_label": "TOTAL",
            "pages": {"3": ["Rose Hill", "Stringer", "TOTAL"]}}

    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._tmpdir = tmp.name

    def manifest(self, extra):
        """Write a BASE+extra manifest to disk; load_manifest validates a PATH."""
        m = dict(self.BASE)
        m.update(extra)
        path = os.path.join(self._tmpdir, "m.json")
        with open(path, "w") as fh:
            json.dump(m, fh)
        return path

    def mdict(self, extra):
        m = dict(self.BASE)
        m.update(extra)
        return m

    def test_reader_and_default(self):
        self.assertEqual(ex.page_min_columns(self.BASE, 3), None)
        self.assertEqual(ex.page_min_columns(
            self.BASE, None), None)
        self.assertEqual(ex.page_min_columns(
            {"pages": self.BASE["pages"], "page_min_columns": {"3": 2}}, 3), 2)

    def test_load_requires_int_at_least_two(self):
        _, problems = ex.load_manifest(self.manifest(
            {"page_min_columns": {"3": 1}}))
        self.assertTrue(any(p["kind"] == "manifest_shape"
                            and p["key"] == "page_min_columns"
                            and ">= 2" in p["problem"] for p in problems),
                        problems)
        _, problems = ex.load_manifest(self.manifest(
            {"page_min_columns": {"3": "x"}}))
        self.assertTrue(any(p["kind"] == "manifest_shape"
                            and p["key"] == "page_min_columns" for p in problems),
                        problems)

    def test_load_requires_declared_page(self):
        _, problems = ex.load_manifest(self.manifest(
            {"page_min_columns": {"7": 2}}))
        self.assertEqual([p for p in problems if p["kind"] == "manifest_shape"],
                         [{"kind": "manifest_shape",
                           "key": "page_min_columns",
                           "problem": "page 7 not declared under pages"}])
        _, problems = ex.load_manifest(self.manifest(
            {"page_min_columns": {"3": 2}}))
        self.assertEqual([p for p in problems if p["kind"] == "manifest_shape"], [])

    def test_extraction_floors_keeps_default_behavior(self):
        # a declared page without page_min_columns: floor 3, then the
        # existing one narrow retry at 2 (non-authoritative) -- unchanged
        self.assertEqual(ex.extraction_floors(self.BASE, 3),
                         [(3, False), (2, False)])
        # undeclared pages: the default floor only
        undeclared = ex.extraction_floors({"pages": {"3": ["P1"]}}, 9)
        self.assertEqual(undeclared, [(3, False)])

    def test_extraction_floors_declared_low_is_authoritative(self):
        # Jasper p3: the operator declares min2, so the declared pass runs
        # after the default one and its result replaces it when it yields a
        # table
        self.assertEqual(
            ex.extraction_floors(
                self.mdict({"page_min_columns": {"3": 2}}), 3),
            [(3, False), (2, True)])

    def test_declared_high_floor_runs_instead_after_default(self):
        self.assertEqual(
            ex.extraction_floors(
                self.mdict({"page_min_columns": {"3": 4}}), 3),
            [(3, False), (4, True)])

    def test_declared_floor_two_suppresses_duplicate_narrow_retry(self):
        self.assertEqual(
            ex.extraction_floors(
                self.mdict({"page_min_columns": {"3": 2}}), 3),
            [(3, False), (2, True)])


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


@unittest.skipUnless(SOURCES_PRESENT, "sources checkout not present")
class JasperTextLayerTests(unittest.TestCase):
    """Fix 1 + Fix 2 pins on the real OCR-noisy Jasper pages: the widened
    three-data-line anchor recovers p2's five left columns (11 real centers,
    the x~246 '1'-debris phantom still excluded), and the declared
    page_min_columns floor 2 moves p3's table top from Guest's row (y=308)
    up to the page's true first data line (Colom's row, y=200)."""

    JASPER = os.path.join(SOURCES_DIR, "Jasper_County_2026_general.pdf")

    @classmethod
    def setUpClass(cls):
        from natural_pdf import PDF
        cls.pdf = PDF(cls.JASPER)

    def test_p2_grid_recovers_the_eleven_real_columns(self):
        tp = ex.extract_table_page(self.pdf.pages[1], fuzzy=False)
        self.assertIsNotNone(tp)
        self.assertEqual([round(c, 1) for c in tp["precinct_centers"]],
                         [285.2, 328.3, 376.4, 423.0, 467.9, 511.8, 559.8,
                          608.4, 652.8, 695.4, 738.2])
        # the x~246 '1'-debris cluster (3 members around fragment lines) is
        # not a column: none of the early data lines reaches x <= 246
        self.assertFalse(any(abs(c - 246.0) < 10.0
                             for c in tp["precinct_centers"]))
        # and the office-header qualifier digits stay out: 11 columns, not 13
        self.assertEqual(len(tp["precinct_centers"]), 11)

    def test_p3_min_two_reaches_the_true_first_data_line(self):
        default = ex.extract_table_page(self.pdf.pages[2], fuzzy=False)
        self.assertEqual(round(default["table_top"], 1), 308.2)  # Guest's row
        widened = ex.extract_table_page(self.pdf.pages[2], fuzzy=False,
                                        min_columns=2)
        self.assertIsNotNone(widened)
        self.assertEqual(round(widened["table_top"], 3), 200.296)
        self.assertEqual([round(c, 1) for c in widened["precinct_centers"]],
                         [283.1, 331.6, 369.5])
        # the recovered view reaches the rows the min3 top lost: Colom's
        # row leads the stream
        self.assertEqual(widened["rows"][0]["kind"], "office")
        self.assertEqual(widened["rows"][1].get("candidate"), "Scott colom Demo")

    def test_page_min_columns_floor_assembles_p3_fully(self):
        # through parse_county_pdf: a temp manifest overlaying the committed
        # draft with page_min_columns {"3": 2}; page 3's alignment then binds
        # its three labels to three detected columns (no column_count miss)
        import json as _json
        import tempfile
        with open(os.path.join(REPO, "2026/header-reads/"
                              "20261103__ms__general__jasper__headers.json")
                  ) as fh:
            manifest = _json.load(fh)
        manifest["page_min_columns"] = {"3": 2}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "overlay.json")
        with open(path, "w") as fh:
            _json.dump(manifest, fh)
        pd = ex.parse_county_pdf(self.JASPER, "Jasper", manifest_path=path)
        aligned = pd["alignments"].get("3") or {}
        self.assertEqual(len(aligned.get("names_by_center") or {}), 3)
        self.assertIn("TOTAL", set((aligned.get("names_by_center") or {}).values()))
        p2 = pd["alignments"].get("2") or {}
        self.assertEqual(len(p2.get("names_by_center") or {}), 11)
        # the not-yet-finalized pages: p4's text layer yields no grid at all
        # (page_missing), p5's a single junk cluster (column_count) -- both
        # resolved by the operator-supply finalization, not by these fixes
        count_problems = [p for p in pd["manifest_problems"]
                          if p["kind"] == "column_count"]
        self.assertEqual([p["page"] for p in count_problems], [5])
        self.assertEqual([p["page"] for p in pd["manifest_problems"]
                          if p["kind"] == "page_missing"], [4])


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
                                            "conflicts": [], "manifest": [],
                                            "party": []})
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
        self.assertEqual(self.problems["party"], [])

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


class SeatSuffixTests(unittest.TestCase):
    def make_pd(self, rows):
        return {"county": "Test", "candidate_rows": rows,
                "precinct_names": ["P1"]}

    def out_path(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fh:
            out = fh.name
        self.addCleanup(os.unlink, out)
        return out

    def test_two_seat_ballot_gets_qualifier_suffix(self):
        rows = [
            {"office": "Court of Appeals", "district": "1", "seat": 1,
             "candidate": "A", "party": "", "cells": {"P1": 1}, "total": 1},
            {"office": "Court of Appeals", "district": "1", "seat": 2,
             "candidate": "B", "party": "", "cells": {"P1": 2}, "total": 2},
        ]
        out = self.out_path()
        ex.write_precinct_csv(self.make_pd(rows), out)
        import csv as _csv
        with open(out) as fh:
            got = list(_csv.reader(fh))
        self.assertEqual(got[0], ["county", "precinct", "office", "district",
                                  "candidate", "party", "votes"])
        offices = {(r[0], r[2], r[4], r[5]) for r in got[1:]}
        self.assertIn(("Test", "Court of Appeals Position 1", "A", ""), offices)
        self.assertIn(("Test", "Court of Appeals Position 2", "B", ""), offices)

    def test_single_seat_keeps_bare_office(self):
        rows = [{"office": "Chancery Court", "district": "3", "seat": 2,
                 "candidate": "C", "party": "REP", "cells": {"P1": 3},
                 "total": 3}]
        out = self.out_path()
        ex.write_precinct_csv(self.make_pd(rows), out)
        import csv as _csv
        with open(out) as fh:
            got = list(_csv.reader(fh))
        self.assertEqual([r[2] for r in got[1:]], ["Chancery Court"])

    def test_place_qualifier_for_chancery_and_circuit(self):
        rows = [
            {"office": "Chancery Court", "district": "1", "seat": 1,
             "candidate": "A", "party": "", "cells": {"P1": 1}, "total": 1},
            {"office": "Chancery Court", "district": "1", "seat": 3,
             "candidate": "B", "party": "", "cells": {"P1": 2}, "total": 2},
            {"office": "Circuit Court", "district": "3", "seat": 1,
             "candidate": "C", "party": "", "cells": {"P1": 4}, "total": 4},
            {"office": "Circuit Court", "district": "3", "seat": 2,
             "candidate": "D", "party": "", "cells": {"P1": 5}, "total": 5},
        ]
        out = self.out_path()
        ex.write_precinct_csv(self.make_pd(rows), out)
        import csv as _csv
        with open(out) as fh:
            got = list(_csv.reader(fh))
        labels = {r[2] for r in got[1:]}
        self.assertIn("Chancery Court Place 1", labels)
        self.assertIn("Chancery Court Place 3", labels)
        self.assertIn("Circuit Court Place 1", labels)
        self.assertIn("Circuit Court Place 2", labels)

    def test_partition_sort_and_ballot_order(self):
        rows = [
            {"office": "U.S. Senate", "district": "", "seat": None,
             "candidate": "Zed", "party": "DEM", "cells": {"B": 1, "A": 2},
             "total": 3},
            {"office": "U.S. Senate", "district": "", "seat": None,
             "candidate": "Zed", "party": "REP", "cells": {"A": 2}, "total": 2},
        ]
        pd = self.make_pd(rows)
        pd["precinct_names"] = ["A", "B"]
        out = self.out_path()
        ex.write_precinct_csv(pd, out)
        import csv as _csv
        with open(out) as fh:
            got = list(_csv.reader(fh))
        # sorted by precinct; within a precinct, rows in candidate order
        prec = [r[1] for r in got[1:]]
        self.assertEqual(prec, ["A", "A", "B"])

    def test_unmapped_multi_seat_office_raises(self):
        # a two-seat (office, district) with no printed qualifier mapping
        # must never silently fall back to bare labels that collide.
        rows = [
            {"office": "New Office", "district": "1", "seat": 1,
             "candidate": "A", "party": "", "cells": {"P1": 1}, "total": 1},
            {"office": "New Office", "district": "1", "seat": 2,
             "candidate": "B", "party": "", "cells": {"P1": 2}, "total": 2},
        ]
        out = self.out_path()
        with self.assertRaises(ValueError) as ctx:
            ex.write_precinct_csv(self.make_pd(rows), out)
        msg = str(ctx.exception)
        self.assertIn("New Office", msg)
        self.assertIn("no printed qualifier mapping", msg)

    def test_seat_loss_mix_hits_missing_seat_raise(self):
        # a two-seat key holding {2, None}: the seat-less row reaches the
        # loud missing-seat raise instead of silently writing a colliding
        # bare label (the fuzzy seat-carry loss shape, Task 3/R1).
        rows = [
            {"office": "Chancery Court", "district": "1", "seat": 2,
             "candidate": "A", "party": "", "cells": {"P1": 1}, "total": 1},
            {"office": "Chancery Court", "district": "1", "seat": None,
             "candidate": "B", "party": "", "cells": {"P1": 2}, "total": 2},
        ]
        out = self.out_path()
        with self.assertRaises(ValueError) as ctx:
            ex.write_precinct_csv(self.make_pd(rows), out)
        msg = str(ctx.exception)
        self.assertIn("no seat number", msg)
        self.assertIn("'B'", msg)

    def test_same_final_label_collision_raises(self):
        # two distinct ballot races resolving to ONE final (label, district):
        # an inconsistent parse of the same race (one page emitted the bare
        # family + seat, another folded the qualifier into the office name
        # and lost the seat) must raise naming both sources, never write two
        # races under one label.
        rows = [
            {"office": "Chancery Court", "district": "1", "seat": 1,
             "candidate": "A", "party": "", "cells": {"P1": 1}, "total": 1},
            {"office": "Chancery Court", "district": "1", "seat": 3,
             "candidate": "B", "party": "", "cells": {"P1": 2}, "total": 2},
            {"office": "Chancery Court Place 1", "district": "1",
             "seat": None,
             "candidate": "C", "party": "", "cells": {"P1": 3}, "total": 3},
        ]
        out = self.out_path()
        with self.assertRaises(ValueError) as ctx:
            ex.write_precinct_csv(self.make_pd(rows), out)
        msg = str(ctx.exception)
        self.assertIn("distinct ballot races", msg)
        self.assertIn("('Chancery Court', '1', 1)", msg)
        self.assertIn("('Chancery Court Place 1', '1', None)", msg)

    def test_same_family_mixed_districts(self):
        # one file, same office family: multi-seat district 1 gains Place
        # suffixes while district 2's single ballot seat keeps the bare
        # label -- the multi-seat computation is per (office, district).
        rows = [
            {"office": "Chancery Court", "district": "1", "seat": 1,
             "candidate": "A", "party": "", "cells": {"P1": 1}, "total": 1},
            {"office": "Chancery Court", "district": "1", "seat": 3,
             "candidate": "B", "party": "", "cells": {"P1": 2}, "total": 2},
            {"office": "Chancery Court", "district": "2", "seat": 2,
             "candidate": "C", "party": "", "cells": {"P1": 4}, "total": 4},
        ]
        out = self.out_path()
        ex.write_precinct_csv(self.make_pd(rows), out)
        import csv as _csv
        with open(out) as fh:
            got = list(_csv.reader(fh))
        self.assertEqual({(r[2], r[3]) for r in got[1:]},
                         {("Chancery Court Place 1", "1"),
                          ("Chancery Court Place 3", "1"),
                          ("Chancery Court", "2")})

    def test_single_ballot_seat_with_two_candidates_keeps_bare_office(self):
        # one seat on the ballot (two-party contest): no qualifier, distinct
        # party rows stay distinct and keep ballot order.
        rows = [
            {"office": "Circuit Court", "district": "3", "seat": 1,
             "candidate": "Zed", "party": "DEM",
             "cells": {"P1": 1, "P2": 2}, "total": 3},
            {"office": "Circuit Court", "district": "3", "seat": 1,
             "candidate": "Yan", "party": "REP",
             "cells": {"P1": 4, "P2": 5}, "total": 9},
        ]
        pd = self.make_pd(rows)
        pd["precinct_names"] = ["P1", "P2"]
        out = self.out_path()
        ex.write_precinct_csv(pd, out)
        import csv as _csv
        with open(out) as fh:
            got = list(_csv.reader(fh))
        self.assertEqual([(r[1], r[2], r[4]) for r in got[1:]],
                         [("P1", "Circuit Court", "Zed"),
                          ("P1", "Circuit Court", "Yan"),
                          ("P2", "Circuit Court", "Zed"),
                          ("P2", "Circuit Court", "Yan")])


class PartyCheckTests(unittest.TestCase):
    def test_unknown_party_reported_blank_party_not_reported(self):
        rows = [
            {"office": "U.S. Senate", "district": "", "seat": None,
             "candidate": "A", "party": None, "cells": {"P1": 1},
             "total": 1},
            {"office": "U.S. Senate", "district": "", "seat": None,
             "candidate": "B", "party": "", "cells": {"P1": 2},
             "total": 2},
            {"office": "U.S. Senate", "district": "", "seat": None,
             "candidate": "C", "party": "DEM", "cells": {"P1": 3},
             "total": 3},
        ]
        pd = {"county": "Test", "candidate_rows": rows,
              "precinct_names": ["P1"]}
        problems = ex.run_gates(pd)
        # None is recorded under its own "party" kind -- a party unknown to
        # the parse is not silently blanked; "" (Nonpartisan) and resolved
        # codes are not problems.
        self.assertEqual(problems["party"],
                         [{"kind": "unknown_party", "office": "U.S. Senate",
                           "district": "", "seat": None, "candidate": "A"}])
        self.assertEqual(problems["total_mismatches"], [])
        self.assertEqual(problems["structure"], [])
        self.assertEqual(problems["conflicts"], [])
        self.assertEqual(problems["manifest"], [])




def fake_page(word_specs):
    """Attribute-duck-typed stand-in for a natural_pdf page. word_specs: list
    of (text, x0, top) or (text, x0, top, height); x1 derives from len(text)."""
    class _Word:
        def __init__(self, text, x0, top, height):
            self.text, self.x0, self.top = text, x0, top
            self.x1 = x0 + len(text) * 5
            self.bottom = top + height

    class _Page:
        def __init__(self, words):
            self.words = words

    return _Page([_Word(spec[0], spec[1], spec[2],
                        spec[3] if len(spec) > 3 else 8.0)
                  for spec in word_specs])


class OfficeLabelRepairTests(unittest.TestCase):
    """Task 7 item 1: the text layer mangles OFFICE labels too; render-verified
    LABEL_REPAIRS entries repair them before parse_office (fuzzy stays off --
    Warren's reliable digits must never be fuzzy-cleaned)."""

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
                             table_top=150.0, label_x_max=280.0)

    def test_senate_mangle_repairs_at_fuzzy_off(self):
        # Warren p2/p4's text layer reads the printed "United States-Senate"
        # (operator strip render) as "United states-senatel"; parse_office
        # refused it at fuzzy=False. The repair restores the printed truth.
        self.assertIsNone(ex.parse_office("United states-senatel"))
        rows = self.run_rows([
            ("United states-senatel", 160.0),
            ("Scott Colom", 170.0), ("Democrat", 178.0),
        ])
        self.assertEqual((rows[0]["kind"], rows[0]["office"],
                          rows[0]["district"], rows[0]["seat"]),
                         ("office", "U.S. Senate", "", None))
        self.assertEqual((rows[1]["candidate"], rows[1]["office"]),
                         ("Scott Colom", "U.S. Senate"))

    def test_chancery_clip_repairs(self):
        # Warren p4's label lost its first two characters in the text layer
        # ("ancery Court 9-2-..."); the rendered page prints the full
        # "Chancery Court 9-2-Chancery District 9-2" (p2/p3 carry the same
        # label). Without the repair p4's two Chancery candidates drop.
        rows = self.run_rows([
            ("ancery Court 9-2-Chancery District 9-2", 160.0),
            ("Vicki  Roach  Barnes", 170.0), ("Nonpartisan", 178.0),
        ])
        self.assertEqual((rows[0]["office"], rows[0]["district"],
                          rows[0]["seat"]), ("Chancery Court", "9", 2))
        self.assertEqual(rows[1]["office"], "Chancery Court")

    def test_leading_junk_glyph_repair(self):
        # Warren p7's label band merges an invisible junk glyph into the first
        # name word ("iM. James 'Jim' Chaney Jr."); the rendered strip reads
        # "M. James 'Jim' Chaney Jr.". Without the repair the p7 copy of the
        # candidate cannot merge with p5/p6's rows of the same person.
        rows = self.run_rows([
            ("iM.  James 'Jim' Chaney Jr.", 160.0), ("Nonpartisan", 168.0),
        ])
        # label_rows preserves the line's own word spacing (the assembly
        # collapses it); the repair removes only the rogue leading glyph.
        self.assertEqual(rows[0]["candidate"], "M.  James 'Jim' Chaney Jr.")
        self.assertEqual(rows[0]["candidate"][0], "M")
        self.assertEqual(ex.name_key(rows[0]["candidate"]),
                         ex.name_key("M. James 'Jim' Chaney Jr."))

    def test_repair_map_stays_minimal_and_render_verified(self):
        # Pin the whole map: one entry per render-verified observed mangle
        # (Union Task 4, Warren Task 7). New entries join only with a render
        # read; an unrelated fold would risk silent corruption.
        self.assertEqual(ex.LABEL_REPAIRS,
                         {"Coiom": "Colom", "weddie": "Weddle",
                          "states-senatel": "States-Senate",
                          "ancery": "Chancery", "iM.": "M."})


class NameKeyTests(unittest.TestCase):
    """Task 7 item 2: one merge key for candidate names across the label
    variants the Warren text layer renders. Each fold is tied to an observed
    variant; whitespace collapse + lowering stay."""

    def test_mid_dot_folds_to_hyphen(self):
        # p3 prints "Cindy  Hyde·Smith " (mid dot, doubled spaces); p2/p4
        # print "Cindy Hyde-Smith" -- one candidate, one key.
        self.assertEqual(ex.name_key("Cindy  Hyde\u00b7Smith "),
                         ex.name_key("Cindy Hyde-Smith"))
        self.assertEqual(ex.name_key("Cindy  Hyde\u00b7Smith "),
                         "cindy hyde-smith")

    def test_initial_comma_folds_to_period(self):
        # p3 prints "Bennie G, Thompson" vs p2/p4 "Bennie G. Thompson".
        self.assertEqual(ex.name_key("Bennie G, Thompson"),
                         ex.name_key("Bennie G. Thompson"))

    def test_no_arbitrary_folds(self):
        # Only the observed variants fold: a missing stop stays a distinct
        # key, as does any other punctuation.
        self.assertNotEqual(ex.name_key("Bennie G Thompson"),
                            ex.name_key("Bennie G. Thompson"))
        self.assertNotEqual(ex.name_key("Bennie G/ Thompson"),
                            ex.name_key("Bennie G. Thompson"))
        self.assertEqual(ex.name_key("M. James 'Jim' Chaney Jr."),
                         "m. james 'jim' chaney jr.")

    def test_shared_between_merge_and_writer(self):
        # The assembly's merge key and the CSV writer's ballot-order index
        # must fold identically, or the writer splits one candidate into two
        # positions exactly as the Task 6 review flagged.
        mk = {"office": "U.S. Senate", "district": "", "seat": None,
              "candidate": "Cindy  Hyde\u00b7Smith "}
        norm = {"office": "U.S. Senate", "district": "", "seat": None,
                "candidate": "Cindy Hyde-Smith"}
        self.assertEqual(ex._merge_key(mk), ex._merge_key(norm))

    def test_assembly_merges_variant_spellings(self):
        # The p2/p3 shape: the same candidate renders with doubled spaces and
        # the mid-dot variant on the second page; both pages' cells land on
        # one merged row and the first (ballot-order) spelling wins.
        def page(name, cells):
            return {"precinct_centers": [246.0, 291.0], "table_top": 200.0,
                    "rows": [{"kind": "office", "office": "U.S. Senate",
                              "district": "", "seat": None},
                             {"kind": "candidate", "candidate": name,
                              "party": "REP", "office": "U.S. Senate",
                              "district": "", "seat": None,
                              "top": 210.0, "bottom": 218.0, "cells": cells}],
                    "conflicts": []}

        pd = ex.parse_county_from_pages(
            {"2": page("Cindy Hyde-Smith", {246.0: 1, 291.0: 2}),
             "3": page("Cindy  Hyde\u00b7Smith ", {246.0: 3, 291.0: 4})},
            "Warren", {"pages": {"2": ["Ridgeway", "Bovina"],
                                 "3": ["Ridgeway", "Bovina"]}})
        self.assertEqual(len(pd["candidate_rows"]), 1)
        row = pd["candidate_rows"][0]
        self.assertEqual(row["candidate"], "Cindy Hyde-Smith")
        self.assertEqual(row["cells"], {"Ridgeway": 1, "Bovina": 2})
        self.assertEqual(row["pages"], [2, 3])

    def test_assembly_normalizes_whitespace(self):
        # The word layer keeps doubled internal spaces and a trailing space
        # ("Ron  Eller "); the CSV name is single-spaced, per the repo's data
        # (no doubled spaces in any committed county file).
        p = {"precinct_centers": [246.0], "table_top": 200.0,
             "rows": [{"kind": "office", "office": "U.S. House",
                       "district": "2", "seat": None},
                      {"kind": "candidate", "candidate": "Ron  Eller ",
                       "party": "REP", "office": "U.S. House",
                       "district": "2", "seat": None,
                       "top": 210.0, "bottom": 218.0, "cells": {246.0: 1}}],
             "conflicts": []}
        pd = ex.parse_county_from_pages(
            {"2": p}, "Warren", {"pages": {"2": ["P1"]}})
        self.assertEqual([r["candidate"] for r in pd["candidate_rows"]],
                         ["Ron Eller"])
        self.assertEqual(ex._merge_key({"office": "U.S. House",
                                        "district": "2", "seat": None,
                                        "candidate": "Ron Eller"}),
                         ex._merge_key({"office": "U.S. House",
                                        "district": "2", "seat": None,
                                        "candidate": "Ron  Eller "}))


class NarrowPageRetryTests(unittest.TestCase):
    """Task 7 item 3: manifest-declared narrow pages (Warren p4/p7 carry only
    Porters Chapel + TOTAL; their data lines hold two numeric tokens) get a
    min_columns=2 retry for table-top detection -- but only on pages the
    manifest declares as table pages."""

    def page(self):
        words = [
            ("The County Election Commission will", 252.0, 40.0),
            ("prepare three (3) Official", 252.0, 44.0),
            ("Recapitulation Sheets containing the", 252.0, 48.0),
            ("vote of the entire", 252.0, 52.0),
            ("401 MISSISSIPPI ST. JACKSON", 250.0, 54.0),
            ("General MS 39201, file one copy", 125.0, 58.0),
            ("Votes cast in the County of Warren,", 40.0, 90.0),
            ("on the 3rd day of November 2026", 40.0, 94.0),
            ("United States-Senate", 150.0, 181.0),
        ]
        for name, party, top in (("Scott Colom", "Democrat", 205.0),
                                 ("Cindy Hyde-Smith", "Republican", 226.0),
                                 ("Ty Pinkins", "Independent", 247.0)):
            words += [(name, 40.0, top), (party, 150.0, top)]
        words += [("324", 282.6, 205.1), ("8576", 323.4, 205.1),
                  ("445", 282.2, 226.1), ("6272", 322.3, 226.1),
                  ("21", 287.9, 247.1), ("393", 326.9, 247.1)]
        return fake_page(words)

    def words_as_dicts(self, page):
        return [{"text": wd.text, "x0": wd.x0, "x1": wd.x1,
                 "top": wd.top, "bottom": wd.bottom} for wd in page.words]

    def test_default_refuses_narrow_page(self):
        page = self.page()
        self.assertIsNone(ex.find_table_top(
            ex.lines_from_words(self.words_as_dicts(page)), min_columns=3))
        self.assertIsNone(ex.extract_table_page(page, False))

    def test_real_prose_shapes_do_not_table_top_at_two(self):
        # The false-top risk under min_columns=2 is guarded by the real page's
        # prose shapes: the certification blurb's stop-adjacent tokens
        # ("(3)", "39201,") and each line's single clean number never reach
        # two clean numeric tokens in two x clusters.
        lines = ex.lines_from_words(self.words_as_dicts(self.page()))
        self.assertEqual(ex.find_table_top(lines, min_columns=2), 205.0)
        tp = ex.extract_table_page(self.page(), False, min_columns=2)
        self.assertIsNotNone(tp)
        # each center is its column's mean cell x0 (324/445/21 -> 284.2)
        self.assertEqual([round(c, 1) for c in tp["precinct_centers"]],
                         [284.2, 324.2])
        self.assertEqual(
            [(r["kind"], r.get("office"), r.get("candidate"), r.get("party"))
             for r in tp["rows"]],
            [("office", "U.S. Senate", None, None),
             ("candidate", "U.S. Senate", "Scott Colom", "DEM"),
             ("candidate", "U.S. Senate", "Cindy Hyde-Smith", "REP"),
             ("candidate", "U.S. Senate", "Ty Pinkins", "IND")])
        cands = [r for r in tp["rows"] if r["kind"] == "candidate"]
        self.assertEqual(len(cands[0]["cells"]), 2)

    def test_prose_two_clean_numbers_would_table_top(self):
        # Documented limitation (min_columns=3 has the same prose note): a
        # prose line carrying two genuine clean numbers in two x clusters is
        # read as the table top. The pinned guarantee is limited to the real
        # recap prose shapes (test above); the count gate + roster checks
        # catch a false top downstream.
        words = []
        for text, top in (("Statewide Election", 40.0),
                          ("Management System 5 and 7 copies", 44.0)):
            x = 40.0
            for tok in text.split(" "):
                words.append(w(tok, x, top))
                x += len(tok) * 5 + 4
        self.assertEqual(
            ex.find_table_top(ex.lines_from_words(words), min_columns=2), 44.0)

    def test_retry_policy_from_manifest(self):
        # Retry ONLY manifest-declared table pages, never local-only pages or
        # undeclared pages (Warren p5/p6 carry no TOTAL; p1 is the cover).
        manifest = {"pages": {"2": ["P1", "TOTAL"], "3": ["P1", "TOTAL"],
                              "4": ["Porters Chapel", "TOTAL"],
                              "5": ["P1"], "6": ["P1"]},
                    "local_only_pages": ["5", "6"]}
        self.assertEqual(ex.narrow_retry_numbers(manifest), {2, 3, 4})
        self.assertNotIn(7, ex.narrow_retry_numbers(manifest))  # undeclared
        self.assertEqual(ex.narrow_retry_numbers({"pages": {"2": ["P1"]}}),
                         {2})
        self.assertEqual(ex.narrow_retry_numbers({"pages": {}}), set())
        # a shape-bad local_only_pages does not crash the reader (the load
        # records the shape problem and holds the county at the gates)
        self.assertEqual(ex.narrow_retry_numbers(
            {"pages": {"2": ["P1"]}, "local_only_pages": "2"}), {2})


class LocalOnlyPageTests(unittest.TestCase):
    """Task 7 item 4: manifest-declared local-only pages are skipped entirely
    (out of scope per the no-local-offices convention), recorded, never
    gated, and never read as missing."""

    def tmp_manifest(self, pages, extra=None):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        manifest = {"county": "Synth", "source": "x.pdf",
                    "election_date": "2026-11-03", "read_by": "operator-vision",
                    "date": "2026-11-19", "total_label": "TOTAL",
                    "pages": pages}
        if extra:
            manifest.update(extra)
        path = os.path.join(tmp.name, "m.json")
        with open(path, "w") as fh:
            json.dump(manifest, fh)
        return path

    @staticmethod
    def page(p1, total):
        return {"precinct_centers": [246.0, 291.0], "table_top": 200.0,
                "rows": [{"kind": "candidate", "candidate": "A",
                          "party": "DEM", "office": "U.S. Senate",
                          "district": "", "seat": None,
                          "top": 200.0, "bottom": 208.0,
                          "cells": {246.0: p1, 291.0: total}}],
                "conflicts": []}

    def test_declared_local_page_not_assembled(self):
        pd = ex.parse_county_from_pages(
            {"2": self.page(5, 5), "5": self.page(9, 9)},
            "Synth", self.tmp_manifest({"2": ["P1", "TOTAL"],
                                        "5": ["P1", "TOTAL"]},
                                       {"local_only_pages": ["5"]}))
        self.assertEqual(
            pd["skipped_local_pages"],
            [{"page": 5, "labels": ["P1", "TOTAL"], "reason": "local_only"}])
        self.assertEqual([(r["candidate"], r["total"])
                          for r in pd["candidate_rows"]], [("A", 5)])
        self.assertEqual(pd["precinct_names"], ["P1"])
        self.assertEqual(ex.run_gates(pd)["manifest"], [])

    def test_declared_local_page_absent_not_missing(self):
        # A local-only page absent from the extraction is the declared state;
        # "page_missing" stays reserved for a declared TABLE page that failed
        # extraction (next test).
        probs = ex.run_gates(ex.parse_county_from_pages(
            {"2": self.page(5, 5)}, "Synth",
            self.tmp_manifest({"2": ["P1", "TOTAL"], "5": ["P1", "TOTAL"]},
                              {"local_only_pages": ["5"]})))
        self.assertEqual(probs["manifest"], [])

    def test_declared_table_page_absent_is_missing(self):
        probs = ex.run_gates(ex.parse_county_from_pages(
            {"2": self.page(5, 5)}, "Synth",
            self.tmp_manifest({"2": ["P1", "TOTAL"], "3": ["P1", "TOTAL"]})))
        self.assertEqual([p["kind"] for p in probs["manifest"]],
                         ["page_missing"])
        self.assertEqual(probs["manifest"][0]["page"], 3)

    def test_bad_shapes_degrade(self):
        path = self.tmp_manifest(
            {"2": ["P1", "TOTAL"]},
            {"local_only_pages": "5", "carry_pages": 5})
        manifest, problems = ex.load_manifest(path)
        kinds = {(p["kind"], p.get("key")) for p in problems}
        self.assertIn(("manifest_shape", "local_only_pages"), kinds)
        self.assertIn(("manifest_shape", "carry_pages"), kinds)
        # and the assembly degrades to nothing skipped, never a crash
        pd = ex.parse_county_from_pages(
            {"2": self.page(5, 5)}, "Synth", path)
        self.assertEqual(pd["skipped_local_pages"], [])

    def test_county_manifest_without_key_is_clean(self):
        pd = ex.parse_county_from_pages(
            {"2": self.page(5, 5)}, "Synth",
            {"total_label": "TOTAL", "pages": {"2": ["P1", "TOTAL"]}})
        self.assertEqual(pd["skipped_local_pages"], [])
        self.assertEqual(pd["candidate_rows"][0]["candidate"], "A")


class CellHeightFloorTests(unittest.TestCase):
    """Task 7 evidence: Warren carries an invisible overlay glyph layer; its
    digit-looking runs are ~1.7pt tall against ~8.6pt data digits. p3's Eller
    row fired a recorded conflict because the stray "1" overwrote the real
    "76" cell. The floor is relative to each page's own anchor digits."""

    def ghost_page(self, ghost_height):
        # three rows x three columns; row 2's col-2 area carries the ghost
        words = [
            ("Scott Colom", 45.0, 205.0), ("Democrat", 150.0, 205.0),
            ("449", 282.6, 205.1), ("582", 329.6, 205.1), ("778", 375.4, 205.1),
            ("Ron Eller", 45.0, 226.0), ("Republican", 150.0, 226.0),
            ("273", 283.1, 226.5), ("76", 334.7, 226.5), ("143", 376.3, 226.5),
            ("1", 345.6, 227.0, ghost_height),
            ("Ty Pinkins", 45.0, 247.0), ("Independent", 150.0, 247.0),
            ("18", 288.7, 247.1), ("14", 335.2, 247.1), ("17", 381.3, 247.1),
        ]
        return fake_page(words)

    def test_ghost_word_never_attaches(self):
        # 1.7pt ghost in Eller's band: dropped before the grid, so no
        # conflict fires and the row keeps its printed cells.
        tp = ex.extract_table_page(self.ghost_page(1.7), False)
        self.assertIsNotNone(tp)
        eller = [r for r in tp["rows"] if r.get("candidate") == "Ron Eller"][0]
        self.assertEqual(len(eller["cells"]), 3)
        self.assertEqual(tp["conflicts"], [])
        col2 = tp["precinct_centers"][1]
        self.assertEqual(eller["cells"].get(col2), 76)

    def test_full_height_single_digit_is_a_real_cell(self):
        # the floor is relative, not absolute: on a page whose anchor digits
        # are small, same-height single-digit cells all keep attaching.
        words = [
            ("Scott Colom", 45.0, 205.0), ("Democrat", 150.0, 205.0),
            ("4", 282.6, 205.1, 2.0), ("7", 329.6, 205.1, 2.0),
            ("5", 375.4, 205.1, 2.0),
            ("Ron Eller", 45.0, 226.0), ("Republican", 150.0, 226.0),
            ("2", 283.1, 226.5, 2.0), ("1", 329.6, 226.5, 2.0),
            ("9", 375.4, 226.5, 2.0),
            ("Ty Pinkins", 45.0, 247.0), ("Independent", 150.0, 247.0),
            ("3", 282.6, 247.1, 2.0), ("9", 329.6, 247.1, 2.0),
            ("2", 375.4, 247.1, 2.0),
        ]
        tp = ex.extract_table_page(fake_page(words), False)
        self.assertIsNotNone(tp)
        eller = [r for r in tp["rows"] if r.get("candidate") == "Ron Eller"][0]
        self.assertEqual(eller["cells"][tp["precinct_centers"][1]], 1)

    def test_x_cells_belong_to_grid_columns(self):
        # Recap X cells are column positions: a column whose members are
        # mostly X (Warren p5-p7's local-zone tails) stays detectable -- one
        # numeric cell plus X glyphs is enough -- and X never becomes a
        # votes value; the row's own printed total proves blanks 0 at
        # assembly instead.
        words = [
            ("Scott Colom", 45.0, 205.0), ("Democrat", 150.0, 205.0),
            ("X", 293.0, 205.1, 9.5), ("582", 329.6, 205.1), ("778", 375.4, 205.1),
            ("19", 417.8, 205.1),
            ("Ron Eller", 45.0, 226.0), ("Republican", 150.0, 226.0),
            ("X", 293.0, 226.5, 9.5), ("273", 329.9, 226.5), ("76", 375.3, 226.5),
            ("143", 417.8, 226.5), ("11", 451.0, 226.5),
            ("Ty Pinkins", 45.0, 247.0), ("Independent", 150.0, 247.0),
            ("18", 288.7, 247.1), ("16", 331.2, 247.1), ("17", 381.3, 247.1),
            ("9", 418.1, 247.1), ("7", 450.6, 247.1),
        ]
        tp = ex.extract_table_page(fake_page(words), False)
        self.assertIsNotNone(tp)
        # col 1's only numeric cell is row 3's "18"; X glyphs keep the
        # column alive for rows 1-2 without becoming values
        self.assertEqual(len(tp["precinct_centers"]), 4)
        colom = [r for r in tp["rows"] if r.get("candidate") == "Scott Colom"][0]
        eller = [r for r in tp["rows"] if r.get("candidate") == "Ron Eller"][0]
        self.assertNotIn(tp["precinct_centers"][0], colom["cells"])
        self.assertNotIn(tp["precinct_centers"][0], eller["cells"])
        self.assertEqual(eller["cells"][tp["precinct_centers"][1]], 273)
        pinkins = [r for r in tp["rows"]
                   if r.get("candidate") == "Ty Pinkins"][0]
        self.assertEqual(pinkins["cells"][tp["precinct_centers"][0]], 18)


class CellTokenRepairTests(unittest.TestCase):
    """Task 7 evidence: Warren's text layer also mangles cell tokens -- a
    phantom glyph inside a right-aligned cell, and a broken ToUnicode decode
    (Times-Italic glyphs print "484", decode "AO."). Per page, the operator
    manifest carries EXACT render-verified repairs applied only to tokens
    already bound to a numeric column, and only for that county's declared
    pages; each repair then faces the row's printed-TOTAL gate."""

    def page(self):
        # p3's shape in miniature: a phantom-digit token ("5821" for the
        # printed 582), a decode-broken small-glyph token ("AO." for 484),
        # and a trailing-junk token ("617!" for 617).
        return fake_page([
            ("Scott Colom", 45.0, 205.0), ("Democrat", 150.0, 205.0),
            ("449", 282.6, 205.1), ("5821", 329.6, 205.1),
            ("AO.", 375.4, 205.1, 4.7), ("17", 417.8, 205.1),
            ("Ron Eller", 45.0, 226.0), ("Republican", 150.0, 226.0),
            ("273", 283.1, 226.5), ("76", 329.9, 226.5),
            ("617!", 376.3, 226.5), ("143", 417.8, 226.5),
            ("Ty Pinkins", 45.0, 247.0), ("Independent", 150.0, 247.0),
            ("18", 282.6, 247.1), ("77", 330.1, 247.1), ("16", 376.5, 247.1),
            ("33", 418.1, 247.1),
            ("Deborah A.", 45.0, 268.0), ("Nonpartisan", 150.0, 268.0),
            ("21", 292.0, 268.1), ("14", 336.2, 268.1), ("55", 377.0, 268.1),
            ("9", 418.3, 268.1),
            ("Bennie Foster", 45.0, 289.0), ("Independent", 150.0, 289.0),
            ("2", 292.6, 289.1), ("10", 335.6, 289.1), ("12", 376.9, 289.1),
            ("4", 418.5, 289.1),
        ])

    def test_repairs_apply_in_numeric_columns_only(self):
        tp = ex.extract_table_page(
            self.page(), False,
            token_repairs={"5821": "582", "AO.": "484", "617!": "617"})
        self.assertIsNotNone(tp)
        colom = [r for r in tp["rows"] if r.get("candidate") == "Scott Colom"][0]
        eller = [r for r in tp["rows"] if r.get("candidate") == "Ron Eller"][0]
        self.assertEqual(colom["cells"][tp["precinct_centers"][1]], 582)
        self.assertEqual(colom["cells"][tp["precinct_centers"][2]], 484)
        self.assertEqual(eller["cells"][tp["precinct_centers"][2]], 617)
        # every token with no repair entry keeps its own value
        self.assertEqual(colom["cells"][tp["precinct_centers"][3]], 17)

    def test_without_repairs_the_mangles_are_lost_or_wrong(self):
        # what the repair saves the county from: the phantom digit rides in
        # as the printed value (5821), and the decode-broken tokens are
        # missing cells that the total gate then flags.
        tp = ex.extract_table_page(self.page(), False)
        colom = [r for r in tp["rows"] if r.get("candidate") == "Scott Colom"][0]
        eller = [r for r in tp["rows"] if r.get("candidate") == "Ron Eller"][0]
        self.assertEqual(colom["cells"].get(tp["precinct_centers"][1]), 5821)
        self.assertNotIn(tp["precinct_centers"][2], colom["cells"])
        self.assertNotIn(tp["precinct_centers"][2], eller["cells"])

    def test_non_digit_repair_value_is_ignored(self):
        # a replacement that is not a clean digit run is ignored and the
        # mangled token keeps its own (wrong) shape -- caught by the row's
        # printed-TOTAL gate, never silently "fixed"
        tp = ex.extract_table_page(
            self.page(), False, token_repairs={"5821": "58,2"})
        colom = [r for r in tp["rows"] if r.get("candidate") == "Scott Colom"][0]
        self.assertEqual(colom["cells"].get(tp["precinct_centers"][1]), 5821)

    def test_manifest_plumbing(self):
        manifest = {"cell_token_repairs": {"3": {"5821": "582"},
                                           "6": {"7491": "749"}}}
        self.assertEqual(ex.page_token_repairs(manifest, 3), {"5821": "582"})
        self.assertEqual(ex.page_token_repairs(manifest, 6), {"7491": "749"})
        self.assertEqual(ex.page_token_repairs(manifest, 4), {})
        self.assertEqual(ex.page_token_repairs({}, 3), {})

    def test_manifest_shape_validation(self):
        for bad in ("x", {"2": "not-a-dict"}, {"2": {"A": 5}}):
            manifest = {"county": "X", "source": "s", "total_label": "TOTAL",
                        "pages": {"2": ["P1", "TOTAL"]},
                        "cell_token_repairs": bad}
            import tempfile
            import json
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            path = os.path.join(tmp.name, "m.json")
            with open(path, "w") as fh:
                json.dump(manifest, fh)
            self.assertIn(
                ("manifest_shape", "cell_token_repairs"),
                {(p["kind"], p.get("key")) for p in ex.load_manifest(path)[1]})


class CarriedOpenPageTests(unittest.TestCase):
    """Task 7 evidence: the Circuit Court 9-2 header prints at the end of
    p2/p3/p4 and its row (M. James 'Jim' Chaney Jr.) prints at the TOP of the
    next page group (p5 cols 1-11, p6 cols 12-22, p7 Porters Chapel + TOTAL),
    ahead of the local zone's first header box. No in-page heuristic can
    distinguish "opening rows continue the previous section" from "opening
    rows are local-zone furniture"; the manifest declares the carried pages."""

    @staticmethod
    def row(name, cells, top, total=None, office=None):
        return {"kind": "candidate", "candidate": name, "party": "",
                "office": office and office[0], "district": office and office[1],
                "seat": office and office[2],
                "top": top, "bottom": top + 8.0, "total": total,
                "cells": cells or {}}

    @staticmethod
    def table(rows):
        return {"precinct_centers": [246.0, 291.0], "table_top": 200.0,
                "rows": list(rows), "conflicts": []}

    def pages(self):
        local_header = {"kind": "unknown_header", "text": "Local Judge"}
        opener = {"kind": "office", "office": "Circuit Court", "district": "9",
                  "seat": 2}
        return {
            "4": self.table([opener,
                             self.row("Toni Walker Terrett",
                                      {246.0: 1, 291.0: 1}, 210.0, 2,
                                      office=("Circuit Court", "9", 2))]),
            "5": self.table([self.row("M. James Chaney", {246.0: 4}, 182.0),
                             local_header,
                             self.row("Local A", {246.0: 9}, 229.0, 9)]),
            "6": self.table([self.row("M.  James Chaney ",
                                      {246.0: 0, 291.0: 3}, 182.0),
                             local_header,
                             self.row("Local B", {246.0: 9}, 229.0, 9)]),
            "7": self.table([self.row("M. James Chaney", {246.0: 0}, 182.0,
                                      total=7),
                             local_header,
                             self.row("Local C", {246.0: 9}, 229.0, 9)]),
        }

    def manifest(self, extra=None):
        m = {"pages": {"4": ["P1", "TOTAL"],
                       "5": ["P3", "P4"], "6": ["P5", "P6"],
                       "7": ["P7", "TOTAL"]}}
        if extra:
            m.update(extra)
        return m

    def test_declared_carry_pages_keep_the_group_row_stream(self):
        pd = ex.parse_county_from_pages(
            self.pages(), "Warren",
            self.manifest({"carry_pages": ["5", "6", "7"]}))
        chaney = [r for r in pd["candidate_rows"]
                  if r["candidate"] == "M. James Chaney"]
        self.assertEqual(len(chaney), 1)
        row = chaney[0]
        # carried context: the section p4 ended on, refreshed through the
        # group's pages (p6/p7 keep it although p5 ended under the local
        # zone's header box)
        self.assertEqual((row["office"], row["district"], row["seat"]),
                         ("Circuit Court", "9", 2))
        self.assertEqual(row["pages"], [5, 6, 7])
        self.assertEqual(row["total"], 7)
        # P1/P2/P4 are the printed 0s the row's own total proves
        self.assertEqual(row["cells"], {"P1": 0, "P3": 4, "P4": 0,
                                        "P5": 0, "P6": 3, "P7": 0})
        # the local rows still drop by design, recorded whole
        self.assertEqual([(d["candidate"], d["page"])
                          for d in pd["dropped_local_rows"]],
                         [("Local A", 5), ("Local B", 6), ("Local C", 7)])
        self.assertEqual(ex.run_gates(pd)["manifest"], [])

    def test_without_declaration_the_local_zone_rule_applies(self):
        # For pages NOT declared carried, the Task 5 boundary rule stands:
        # opening rows ahead of an in-stream local header never inherit the
        # prior page's end context (they drop to dropped_local_rows instead)
        # -- which is exactly why the declaration had to exist.
        pd = ex.parse_county_from_pages(self.pages(), "Warren",
                                        self.manifest())
        self.assertEqual([r["candidate"] for r in pd["candidate_rows"]],
                         ["Toni Walker Terrett"])
        self.assertEqual([(d["candidate"], d["page"])
                          for d in pd["dropped_local_rows"]],
                         [("M. James Chaney", 5), ("Local A", 5),
                          ("M.  James Chaney ", 6), ("Local B", 6),
                          ("M. James Chaney", 7), ("Local C", 7)])


class CarriedGroupJunkRowTests(unittest.TestCase):
    """Task 7 evidence: Warren p7 prints an invisible-layer remnant -- a lone
    \'i\' word (Helvetica 5.0, 2.5pt wide) after the carried Circuit 9-2 row
    and before the local section header; the rendered page prints nothing
    there. The carry exists to attribute data, so a carried page's zero-cell
    row is never roster data: it drops to dropped_local_rows (recorded whole)."""

    @staticmethod
    def table(rows):
        return {"precinct_centers": [246.0, 291.0], "table_top": 200.0,
                "rows": list(rows), "conflicts": []}

    def carried_pages(self, extra_row=None):
        opener = {"kind": "office", "office": "Circuit Court", "district": "9",
                  "seat": 2}
        local_header = {"kind": "unknown_header", "text": "Local Judge"}
        # p4/p5 carry the section's own office at capture (their pages have
        # the header row); p6 is the carried continuation: no header, its
        # opener row(s) print with office=None
        chaney_p = {"kind": "candidate", "candidate": "M. James Chaney",
                    "party": "", "office": "Circuit Court", "district": "9",
                    "seat": 2, "top": 182.0, "bottom": 190.0, "total": 6,
                    "cells": {246.0: 6}}
        junk = {"kind": "candidate", "candidate": "i", "party": None,
                "office": None, "district": None, "seat": None,
                "top": 194.5, "bottom": 199.5, "total": None, "cells": {}}
        local = {"kind": "candidate", "candidate": "Local A", "party": "",
                 "office": None, "district": None, "seat": None,
                 "top": 229.0, "bottom": 237.0, "total": 9,
                 "cells": {246.0: 9}}
        chaney_c = dict(chaney_p, office=None, district=None, seat=None,
                        total=6)
        rows = [chaney_c] + ([junk] if extra_row else []) + [local_header,
                                                             local]
        return {"4": self.table([opener, chaney_p]),
                "5": self.table([opener, chaney_p]),
                "6": self.table(rows if extra_row else
                                [chaney_c, local_header, local])}

    def test_zero_cell_row_is_not_carried_data(self):
        # the junk word sits between the carried row and the local header on
        # p6: it must not enter the carried race, which keeps Chaney's
        # carried group intact (1 carried row, not 2)
        pd = ex.parse_county_from_pages(
            self.carried_pages(extra_row=True), "Warren",
            {"pages": {"4": ["P1"], "5": ["P2"],
                       "6": ["P3", "TOTAL"]},
             "carry_pages": ["4", "5", "6"]})
        self.assertEqual([(r["candidate"], r["office"])
                          for r in pd["candidate_rows"]],
                         [("M. James Chaney", "Circuit Court")])
        self.assertEqual([(d["candidate"], d["page"])
                          for d in pd["dropped_local_rows"]],
                         [("i", 6), ("Local A", 6)])
        self.assertEqual(pd["candidate_rows"][0]["cells"],
                         {"P1": 6, "P2": 6, "P3": 6})


@unittest.skipUnless(SOURCES_PRESENT, "sources checkout not present")
class WarrenCountyTests(unittest.TestCase):
    """Task 7 end-to-end on the real Warren PDF under the corrected manifest:
    structure, per-candidate printed totals, roster, and the cross-county
    Senate roster against Union's committed CSV."""

    @classmethod
    def setUpClass(cls):
        cls.pd = ex.parse_county_pdf(
            os.path.join(SOURCES_DIR, "Warren_County_2026_general.pdf"),
            "Warren",
            manifest_path=os.path.join(REPO, "2026/header-reads/"
                                       "20261103__ms__general__warren__headers.json"))
        cls.totals = {"Scott Colom": 8576, "Cindy Hyde-Smith": 6272,
                      "Ty Pinkins": 393, "Ron Eller": 6519,
                      "Bennie G. Thompson": 8309, "Bennie Foster": 412,
                      "Deborah A. McDonald": 12927, "Vicki Roach Barnes": 6482,
                      "Penny B. Lawson": 7918, "Toni Walker Terrett": 2985,
                      "M. James 'Jim' Chaney Jr.": 10545}

    def test_gates_clean(self):
        problems = ex.run_gates(self.pd)
        self.assertEqual(problems["total_mismatches"], [])
        self.assertEqual(problems["structure"], [])
        self.assertEqual(problems["conflicts"], [])
        self.assertEqual(problems["manifest"], [])
        self.assertEqual(problems["party"], [])

    def test_no_in_scope_row_silently_lost(self):
        names = {r["candidate"] for r in self.pd["candidate_rows"]}
        self.assertEqual(names, {
            "Scott Colom", "Cindy Hyde-Smith", "Ty Pinkins", "Ron Eller",
            "Bennie G. Thompson", "Bennie Foster", "Deborah A. McDonald",
            "Vicki Roach Barnes", "Penny B. Lawson", "Toni Walker Terrett",
            "M. James 'Jim' Chaney Jr."})
        self.assertEqual(len(self.pd["candidate_rows"]), 11)
        # the second table group's other rows are local-zone candidates,
        # recorded whole (raw text, no office) rather than merged or gated --
        # Union precedent; NO variant of the carried Circuit 9-2 row drops.
        dropped = self.pd["dropped_local_rows"]
        # 19 rows: 18 of the 27 possible (local-name x page) rows reach
        # dropped_local_rows (the three JCJ-zone names are absorbed by the
        # bounded fragment run behind their header on each page, out-of-scope
        # data either way) + Warren p7's invisible 'i' remnant, which the
        # carry correctly refuses to treat as carried data
        self.assertEqual(len(dropped), 19)
        self.assertEqual([d["candidate"] for d in dropped
                          if d["page"] == 7 and d["cells"] == {}], ["i"])
        self.assertTrue(all(d["office"] is None for d in dropped))
        self.assertFalse(any("Chaney" in d["candidate"] for d in dropped))

    def test_full_cells_and_printed_totals(self):
        for row in self.pd["candidate_rows"]:
            self.assertEqual(len(row["cells"]), 23, row["candidate"])
            self.assertEqual(sum(row["cells"].values()), row["total"],
                             row["candidate"])
            self.assertEqual(row["total"], self.totals[row["candidate"]])
        self.assertEqual(sorted(self.pd["precinct_names"]), sorted([
            "Ridgeway", "Bovina", "Gibson", "Oakland", "Medgar Foundation",
            "Elizabeth Circle", "Kings", "Spring Hill", "Auditorium",
            "Eagle Lake Methodist", "International Paper", "Calvary Indiana",
            "American Legion", "Travelers Rest", "Plumbers & Pipefitters",
            "Immanuel", "Goodrum", "Yokena", "Elks Lodge", "Calvary Old 27",
            "Life", "Lee Rd Fire", "Porters Chapel"]))

    def test_roster_offices_districts_parties(self):
        roster = {(r["office"], r["district"], r.get("seat"), r["party"])
                  for r in self.pd["candidate_rows"]}
        self.assertEqual(roster, {
            ("U.S. Senate", "", None, "DEM"), ("U.S. Senate", "", None, "REP"),
            ("U.S. Senate", "", None, "IND"),
            ("U.S. House", "2", None, "REP"), ("U.S. House", "2", None, "DEM"),
            ("U.S. House", "2", None, "IND"),
            ("Court of Appeals", "2", 1, ""), ("Chancery Court", "9", 2, ""),
            ("Circuit Court", "9", 1, ""), ("Circuit Court", "9", 2, "")})
        # two seats of Circuit Court district 9 on one ballot -> Place labels
        self.assertEqual(ex.multi_seat_keys(self.pd), {("Circuit Court", "9")})

    def test_senate_roster_matches_union_csv(self):
        import csv
        union = os.path.join(REPO, "2026/counties/"
                             "20261103__ms__general__union__precinct.csv")
        with open(union) as fh:
            rows = list(csv.DictReader(fh))
        union_roster = {(r["candidate"], r["party"])
                        for r in rows if r["office"] == "U.S. Senate"}
        warren = {(r["candidate"], r["party"])
                  for r in self.pd["candidate_rows"]
                  if r["office"] == "U.S. Senate"}
        self.assertEqual(warren, union_roster)


class SuiteHygieneTests(unittest.TestCase):
    """Task 7 re-review carries: structural pins for the test file itself.

    The integration classes must skip (not error) on machines without the
    sources checkout, and direct execution must collect every test class.
    """

    INTEGRATION_CLASSES = ("UnionPage2Tests", "UnionCountyTests",
                           "WarrenCountyTests")

    def test_integration_classes_skip_without_sources(self):
        with open(__file__, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for name in self.INTEGRATION_CLASSES:
            idx = next(i for i, l in enumerate(lines)
                       if l.startswith(f"class {name}("))
            self.assertTrue(
                lines[idx - 1].strip().startswith(
                    "@unittest.skipUnless(SOURCES_PRESENT"),
                f"{name} must be decorated @unittest.skipUnless so a machine "
                f"without the sources checkout skips it instead of erroring "
                f"(line {idx})")

    def test_single_trailing_main_block(self):
        with open(__file__, encoding="utf-8") as fh:
            source = fh.read()
        block = 'if __name__ == "__main__":\n    unittest.main()'
        self.assertEqual(1, source.count(block),
                         "the stale mid-file __main__ block makes direct "
                         "execution run only the tests defined above it")
        self.assertLess(source.rindex("\nclass "),
                        source.index(block),
                        "the __main__ block must come after every test class")


class ManifestDeclarationTests(unittest.TestCase):
    """Task 8 mechanics: carry_pages / local_only_pages / cell_token_repairs
    declarations must reference pages the manifest declares under "pages" --
    a declaration naming an undeclared page cannot bind to anything and is
    recorded as a manifest_shape problem (it degrades harmlessly: the
    tolerant readers ignore it, the gates hold the county at write time)."""

    BASE = {"county": "Synth", "source": "x.pdf",
            "election_date": "2026-11-03", "read_by": "operator-vision",
            "date": "2026-11-19", "total_label": "TOTAL",
            "pages": {"2": ["P1", "TOTAL"]}}

    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._tmpdir = tmp.name

    def path(self, extra):
        manifest = dict(self.BASE)
        manifest.update(extra)
        path = os.path.join(self._tmpdir, "m.json")
        with open(path, "w") as fh:
            json.dump(manifest, fh)
        return path

    def page(self, p1, total):
        return {"precinct_centers": [246.0, 291.0], "table_top": 200.0,
                "rows": [{"kind": "candidate", "candidate": "A",
                          "party": "DEM", "office": "U.S. Senate",
                          "district": "", "seat": None,
                          "top": 200.0, "bottom": 208.0,
                          "cells": {246.0: p1, 291.0: total}}],
                "conflicts": []}

    def test_undeclared_carry_page_recorded(self):
        manifest, problems = ex.load_manifest(self.path({"carry_pages": ["9"]}))
        self.assertEqual([p for p in problems
                          if p["kind"] == "manifest_shape"
                          and p["key"] == "carry_pages"],
                         [{"kind": "manifest_shape", "key": "carry_pages",
                           "problem": "page 9 not declared under pages"}])

    def test_undeclared_local_only_page_recorded(self):
        manifest, problems = ex.load_manifest(
            self.path({"local_only_pages": ["5"]}))
        self.assertEqual([p for p in problems
                          if p["kind"] == "manifest_shape"
                          and p["key"] == "local_only_pages"],
                         [{"kind": "manifest_shape", "key": "local_only_pages",
                           "problem": "page 5 not declared under pages"}])

    def test_undeclared_repair_page_recorded(self):
        manifest, problems = ex.load_manifest(
            self.path({"cell_token_repairs": {"4": {"AO.": "484"}}}))
        self.assertEqual([p for p in problems
                          if p["kind"] == "manifest_shape"
                          and p["key"] == "cell_token_repairs"],
                         [{"kind": "manifest_shape", "key": "cell_token_repairs",
                           "problem": "page 4 not declared under pages"}])

    def test_declared_pages_stay_clean(self):
        manifest, problems = ex.load_manifest(
            self.path({"local_only_pages": ["2"],
                       "carry_pages": [2],
                       "cell_token_repairs": {"2": {"AO.": "484"}}}))
        self.assertEqual([p for p in problems
                          if p.get("kind") == "manifest_shape"], [])

    def test_degrades_harmlessly_through_the_assembly(self):
        pd = ex.parse_county_from_pages(
            {"2": self.page(5, 5)}, "Synth",
            self.path({"local_only_pages": ["5"], "carry_pages": ["5"],
                       "cell_token_repairs": {"5": {"AO.": "484"}}}))
        self.assertEqual(pd["manifest_problems"][0]["kind"], "manifest_shape")
        self.assertEqual(pd["candidate_rows"][0]["candidate"], "A")
        self.assertEqual(ex.run_gates(pd)["total_mismatches"], [])


class OperatorManifestTests(unittest.TestCase):
    """Fix 3 + the operator_rows amendment: operator_cells (page-scoped
    repairs into parsed rows), operator_rows (identity-supplied rows for
    layers that parse no usable candidate name), and operator_supply_pages
    (pages whose text-layer parse the operator declares unused). All apply
    AFTER manifest alignment and key cells on the manifest's 0-based column-
    order index (a TOTAL column by its position index like any other); every
    application is recorded in pd["operator_cells_applied"], and every row
    faces the printed-TOTAL gate exactly like a parsed row."""

    MANIFEST = {"county": "Synth", "source": "x.pdf",
                "election_date": "2026-11-03", "read_by": "operator-vision",
                "date": "2026-11-19", "total_label": "TOTAL",
                "pages": {"2": ["P1", "P2", "TOTAL"],
                          "3": ["P3", "TOTAL"]}}

    @staticmethod
    def parsed_page(centers, candidates, office="U.S. Senate", district="",
                    seat=None):
        """A table page dict with candidates:
        candidates = [(name, {center: value}, total)] in row order, each
        carrying office/district/seat. office=None makes the rows
        unattributable garbage (the assembly drops them)."""
        rows = []
        if office is not None:
            rows.append({"kind": "office", "office": office,
                         "district": district, "seat": seat})
        for name, cells, total in candidates:
            rows.append({"kind": "candidate", "candidate": name,
                         "party": "DEM" if office == "U.S. Senate" else "",
                         "office": office, "district": district, "seat": seat,
                         "top": 200.0, "bottom": 208.0,
                         "cells": dict(cells), "total": total})
        return {"precinct_centers": centers, "table_top": 200.0,
                "rows": rows, "conflicts": []}

    def county(self, manifest, pages):
        return ex.parse_county_from_pages(pages, "Synth", manifest)

    def problems_of(self, pd, kind):
        return [p for p in pd["manifest_problems"] if p["kind"] == kind]

    def test_operator_cells_override_parsed_cells(self):
        manifest = dict(self.MANIFEST, operator_cells={
            "2": {"A": {"0": 9, "2": 15}}})
        pd = self.county(manifest, {
            "2": self.parsed_page([246.0, 291.0, 333.0],
                                  [("A", {246.0: 5, 291.0: 6}, 15)])})
        (row,) = pd["candidate_rows"]
        self.assertEqual(row["cells"], {"P1": 9, "P2": 6})
        self.assertEqual(row["total"], 15)
        self.assertEqual(self.problems_of(pd, "operator_cell_no_row"), [])
        self.assertEqual(
            sorted((r["precinct"], r["old"], r["new"])
                   for r in pd["operator_cells_applied"]),
            [("P1", 5, 9), ("TOTAL", 15, 15)])
        (rec,) = [r for r in pd["operator_cells_applied"]
                  if r["precinct"] == "P1"]
        self.assertEqual(rec["mechanism"], "operator_cells")
        self.assertEqual(rec["column"], "P1")
        self.assertEqual(rec["page"], 2)
        self.assertEqual(ex.run_gates(pd)["total_mismatches"], [])

    def test_operator_cells_add_missing_cells(self):
        manifest = dict(self.MANIFEST, operator_cells={
            "2": {"A": {"0": 9, "1": 6}}})
        pd = self.county(manifest, {
            "2": self.parsed_page([246.0, 291.0, 333.0],
                                  [("A", {333.0: 15}, 15)])})
        (row,) = pd["candidate_rows"]
        self.assertEqual(row["cells"], {"P1": 9, "P2": 6})
        self.assertEqual(row["total"], 15)
        self.assertEqual([(r["precinct"], r["old"], r["new"])
                          for r in pd["operator_cells_applied"]],
                         [("P1", None, 9), ("P2", None, 6)])
        self.assertEqual(ex.run_gates(pd)["total_mismatches"], [])

    def test_operator_cells_unmatched_name_is_loud(self):
        manifest = dict(self.MANIFEST, operator_cells={
            "2": {"Nope": {"0": 9}}})
        pd = self.county(manifest, {
            "2": self.parsed_page([246.0, 291.0],
                                  [("A", {246.0: 5}, 5)])})
        self.assertEqual(self.problems_of(pd, "operator_cell_no_row"),
                         [{"kind": "operator_cell_no_row", "page": 2,
                           "candidate": "Nope"}])
        self.assertEqual(pd["operator_cells_applied"], [])
        manifest_kinds = [p.get("kind")
                          for p in ex.run_gates(pd)["manifest"]]
        self.assertIn("operator_cell_no_row", manifest_kinds)

    def test_operator_cells_ambiguous_match_is_loud(self):
        # a junk fragment row whose name is a tail of BOTH 'Stanley Sorey'
        # reads cannot bind silently
        manifest = dict(self.MANIFEST, operator_cells={
            "2": {"ley Sorey": {"0": 9}}})
        pd = self.county(manifest, {
            "2": self.parsed_page([246.0, 291.0],
                                  [("Stanley Sorey", {246.0: 5}, 5),
                                   ("Shirley Sorey", {291.0: 6}, 6)])})
        self.assertEqual(self.problems_of(pd, "operator_cell_ambiguous_match"),
                         [{"kind": "operator_cell_ambiguous_match",
                           "page": 2, "candidate": "ley Sorey",
                           "matched": ["Shirley Sorey", "Stanley Sorey"]}])

    def test_operator_rows_synth_row_with_multipage_merge(self):
        # mode 3, Lee's case: the pages' candidate rows are garbage
        # (office=None, so they are dropped local rows), the operator row
        # carries its own ballot identity and cells keyed by position across
        # two pages; the printed-TOTAL gate measures it like a parsed row.
        manifest = dict(self.MANIFEST, operator_rows=[{
            "key": "hydesmith", "office": "U.S. Senate", "district": "",
            "seat": None, "candidate": "Cindy Hyde-Smith", "party": "REP",
            "cells": {"2": {"0": 300, "1": 400, "2": 900},
                      "3": {"0": 200, "1": 900}}}])
        pd = self.county(manifest, {
            "2": self.parsed_page([246.0, 291.0, 333.0],
                                  [("junk fragment", {246.0: 1}, None)],
                                  office=None),
            "3": self.parsed_page([246.0, 291.0], [])})
        senate = [r for r in pd["candidate_rows"]
                  if r["candidate"] == "Cindy Hyde-Smith"]
        self.assertEqual(len(senate), 1)
        (row,) = senate
        self.assertEqual(row["office"], "U.S. Senate")
        self.assertEqual(row["party"], "REP")
        self.assertEqual(row["cells"], {"P1": 300, "P2": 400, "P3": 200})
        self.assertEqual(row["total"], 900)
        self.assertEqual(row["pages"], [2, 3])
        self.assertEqual(len(pd["candidate_rows"]), 1)
        # the layer junk row stayed exactly where the normal rules put it
        self.assertEqual([d["candidate"] for d in pd["dropped_local_rows"]],
                         ["junk fragment"])
        self.assertEqual(len(pd["operator_cells_applied"]), 5)
        (rec,) = [r for r in pd["operator_cells_applied"]
                  if r["page"] == 3 and r["precinct"] == "TOTAL"]
        self.assertEqual(rec["new"], 900)
        problems = ex.run_gates(pd)
        self.assertEqual(problems["total_mismatches"], [])
        self.assertEqual(problems["structure"], [])
        self.assertEqual(problems["manifest"], [])
        self.assertEqual(problems["party"], [])

    def test_operator_rows_mode_three_ballot_order_after_previous_race(self):
        # a synthetic Circuit row first-referenced on page 4 sorts after the
        # rows the document printed at or before page 4 (page 2's stream)
        # and its multi-page merge keeps one row
        page2 = self.parsed_page([246.0, 291.0, 333.0],
                                 [("Scott Colom", {246.0: 400, 291.0: 500},
                                   900)])
        pd = self.county(
            dict(self.MANIFEST, pages={"2": ["P1", "P2", "TOTAL"],
                                       "4": ["P1", "P2", "TOTAL"]},
                 operator_rows=[{
                     "key": "sorey", "office": "Circuit Court",
                     "district": "13", "seat": 2,
                     "candidate": "Stanley Sorey", "party": "",
                     "cells": {"4": {"0": 100, "1": 200, "2": 300}}}]),
            {"2": page2})
        self.assertEqual([r["candidate"] for r in pd["candidate_rows"]],
                         ["Scott Colom", "Stanley Sorey"])
        (sorey,) = [r for r in pd["candidate_rows"]
                    if r["candidate"] == "Stanley Sorey"]
        self.assertEqual(sorey["cells"], {"P1": 100, "P2": 200})
        self.assertEqual(sorey["total"], 300)
        self.assertEqual(ex.run_gates(pd)["total_mismatches"], [])

    def test_operator_rows_name_partial_match_merges_into_parsed_row(self):
        # mode 2 with a partial layer name: 'ley Sorey' is 'Stanley Sorey'
        # cut at the head; the cell lands in the parsed row
        page2 = self.parsed_page([246.0, 291.0, 333.0],
                                 [("ley Sorey", {246.0: 37}, None)],
                                 office="Circuit Court", district="13",
                                 seat=2)
        pd = self.county(
            dict(self.MANIFEST,
                 pages={"2": ["Rose Hill", "Stringer", "TOTAL"]},
                 operator_rows=[{
                     "key": "sorey", "office": "Circuit Court",
                     "district": "13", "seat": 2,
                     "candidate": "Stanley Sorey", "party": "",
                     "cells": {"2": {"0": 414, "1": 523, "2": 937}}}]),
            {"2": page2},)
        (row,) = pd["candidate_rows"]
        self.assertEqual(row["candidate"], "ley Sorey")
        self.assertEqual(row["cells"], {"Rose Hill": 414, "Stringer": 523})
        self.assertEqual(row["total"], 937)
        self.assertEqual(pd["operator_cells_applied"][0]["matched_layer"],
                         "ley Sorey")
        self.assertEqual(ex.run_gates(pd)["total_mismatches"], [])

    def test_operator_rows_missing_metadata_is_loud(self):
        manifest = dict(self.MANIFEST, operator_rows=[{
            "key": "x", "candidate": "Cindy Hyde-Smith",
            "cells": {"2": {"0": 300, "2": 900}}}])
        pd = self.county(manifest, {
            "2": self.parsed_page([246.0, 291.0], [])})
        self.assertEqual(self.problems_of(pd, "operator_row_missing_metadata"),
                         [{"kind": "operator_row_missing_metadata",
                           "key": "x",
                           "missing": ["office"], "pages": [2]}])
        self.assertEqual(pd["candidate_rows"], [])
        self.assertNotEqual(ex.run_gates(pd)["manifest"], [])

    def test_operator_rows_race_collision_is_loud(self):
        # a parsed row holds the Circuit 13 Place 2 race under a distinct
        # identity: a synthetic twin would double-count the seat
        pd = self.county(
            dict(self.MANIFEST, operator_rows=[{
                "key": "sorey", "office": "Circuit Court", "district": "13",
                "seat": 2, "candidate": "Stanley Sorey",
                "cells": {"2": {"0": 414}}}]),
            {"2": self.parsed_page([246.0],
                                   [("Someone Else", {246.0: 5}, 5)],
                                   office="Circuit Court", district="13",
                                   seat=2)})
        (problem,) = self.problems_of(pd, "operator_row_race_collision")
        self.assertEqual(problem["race"], ["Circuit Court", "13", 2])
        self.assertEqual(problem["parsed"], ["Someone Else"])
        self.assertEqual([r["candidate"] for r in pd["candidate_rows"]],
                         ["Someone Else"])
        self.assertEqual(pd["operator_cells_applied"], [])

    def test_operator_rows_position_out_of_range_is_loud(self):
        manifest = dict(self.MANIFEST, operator_rows=[{
            "key": "x", "office": "U.S. Senate", "district": "",
            "candidate": "Cindy Hyde-Smith", "party": "REP",
            "cells": {"2": {"7": 300, "2": 900}}}])
        pd = self.county(manifest, {
            "2": self.parsed_page([246.0, 291.0, 333.0], []),
            "3": self.parsed_page([246.0, 291.0], [])})
        self.assertEqual(
            self.problems_of(pd, "operator_cell_position_out_of_range"),
            [{"kind": "operator_cell_position_out_of_range",
              "mechanism": "operator_rows", "page": 2, "position": 7,
              "labels": 3, "key": "x", "candidate": "Cindy Hyde-Smith"}])
        (row,) = pd["candidate_rows"]
        self.assertEqual(row["total"], 900)
        self.assertEqual([p["kind"] for p in ex.run_gates(pd)["manifest"]],
                         ["operator_cell_position_out_of_range"])

    def test_operator_rows_unknown_precinct_is_loud(self):
        pd = self.county(
            dict(self.MANIFEST, operator_rows=[{
                "key": "x", "office": "U.S. Senate", "district": "",
                "candidate": "Cindy Hyde-Smith", "party": "REP",
                "cells": {"2": {"0": 300}}}]),
            {"3": self.parsed_page([246.0], [])})
        self.assertEqual([p["kind"] for p in pd["structure_problems"]],
                         ["operator_cell_unknown_precinct"])
        self.assertNotEqual(ex.run_gates(pd)["structure"], [])

    def test_end_to_end_garbage_layer_with_operator_rows_gates_clean(self):
        # the real workflow shape: a county whose only parseable page yields
        # junk rows; the operator supplies two full rows from renders with
        # printed totals; gates clean, CSV writes the operator values.
        import csv as _csv
        import tempfile
        manifest = dict(self.MANIFEST, pages={"2": ["P1", "P2", "TOTAL"]},
                        operator_rows=[
            {"key": "colom", "office": "U.S. Senate", "district": "",
             "candidate": "Scott Colom", "party": "DEM",
             "cells": {"2": {"0": 29, "1": 300, "2": 329}}},
            {"key": "hydesmith", "office": "U.S. Senate", "district": "",
             "candidate": "Cindy Hyde-Smith", "party": "REP",
             "cells": {"2": {"0": 5, "1": 7, "2": 12}}}])
        junk = self.parsed_page([246.0, 291.0, 333.0],
                                [("garbage name 9", {246.0: 9}, None)],
                                office=None)
        pd = self.county(manifest, {"2": junk})
        problems = ex.run_gates(pd)
        self.assertEqual(problems["total_mismatches"], [])
        self.assertEqual(problems["manifest"], [])
        self.assertEqual(problems["structure"], [])
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmpdir))
        out = os.path.join(tmpdir, "synth__precinct.csv")
        ex.write_precinct_csv(pd, out)
        with open(out) as fh:
            rows = list(_csv.DictReader(fh))
        by = {(r["candidate"], r["precinct"]): int(r["votes"]) for r in rows}
        self.assertEqual(by[("Scott Colom", "P1")], 29)
        self.assertEqual(by[("Cindy Hyde-Smith", "P2")], 7)
        # the junk layer row never became data
        self.assertEqual({r["candidate"] for r in rows},
                         {"Scott Colom", "Cindy Hyde-Smith"})

    def test_operator_supply_pages_skip_extraction_of_missing_pages(self):
        manifest = dict(self.MANIFEST, pages={"2": ["P1", "P2", "TOTAL"],
                                              "3": ["P3", "TOTAL"]},
                        operator_supply_pages=["3"],
                        operator_rows=[{
                            "key": "sorey", "office": "Circuit Court",
                            "district": "13", "seat": 2,
                            "candidate": "Stanley Sorey", "party": "",
                            "cells": {"2": {"0": 414, "1": 523, "2": 937},
                                      "3": {"1": 937}}}])
        pd = self.county(manifest, {"2": self.parsed_page([246.0], [])})
        # page 3's absence is a scope decision, not a page_missing gate
        self.assertEqual(
            [p for p in pd["manifest_problems"] if p["kind"] == "page_missing"],
            [])
        self.assertEqual(pd["operator_supply_pages"],
                         [{"page": 3, "labels": ["P3", "TOTAL"]}])
        # its cells re-key through the page's own declared labels
        self.assertEqual(
            sorted((r["page"], r["precinct"])
                   for r in pd["operator_cells_applied"]),
            [(2, "P1"), (2, "P2"), (2, "TOTAL"), (3, "TOTAL")])
        (row,) = pd["candidate_rows"]
        self.assertEqual(row["cells"], {"P1": 414, "P2": 523})
        self.assertEqual(row["total"], 937)
        self.assertEqual(ex.run_gates(pd)["total_mismatches"], [])

    def test_unreferenced_operator_supply_page_is_loud(self):
        import tempfile
        manifest = dict(self.MANIFEST, operator_supply_pages=["3"],
                        operator_rows=[{
                            "key": "x", "office": "U.S. Senate",
                            "district": "", "candidate": "Cindy Hyde-Smith",
                            "party": "REP", "cells": {"2": {"0": 1, "2": 100}}}],
                        pages={"2": ["P1", "P2", "TOTAL"],
                               "3": ["P3", "TOTAL"]})
        path = os.path.join(self._tmpdir(), "m.json")
        with open(path, "w") as fh:
            json.dump(manifest, fh)
        _, problems = ex.load_manifest(path)
        self.assertEqual(
            [p for p in problems if p["kind"] == "manifest_shape"],
            [{"kind": "manifest_shape", "key": "operator_supply_pages",
              "problem": "page 3 is declared operator-supplied but no "
                         "operator_cells/operator_rows entry supplies it; "
                         "its declared labels would silently produce "
                         "nothing"}])

    def _tmpdir(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, True))
        return tmp

    def test_load_shape_validation(self):
        import tempfile
        path = os.path.join(self._tmpdir(), "m.json")
        for extra, expected in (
                ({"operator_cells": ["2"]},
                 "must be a dict of page -> {candidate: {column index: "
                 "value}, got list"),
                ({"operator_cells": {"2": {"A": "nope"}}},
                 "must be a dict of column index -> value"),
                ({"operator_rows": {"2": {}}},
                 "must be a list of row objects, got dict"),
                ({"operator_rows": [{"key": "", "cells": {}}]},
                 "needs a non-empty 'key'"),
                ({"operator_rows": [{"key": "x", "candidate": "A",
                                     "cells": {}}]},
                 "carries no int (or digit-string) cell values"),
                ({"operator_cells": {"9": {"A": {"0": 1}}}},
                 "page 9 not declared under pages"),
                ({"operator_rows": [{"key": "x", "candidate": "A",
                                     "cells": {"9": {"0": 1}}}]},
                 "page 9 not declared under pages")):
            manifest = dict(self.MANIFEST)
            manifest.update(extra)
            with open(path, "w") as fh:
                json.dump(manifest, fh)
            _, problems = ex.load_manifest(path)
            shapes = [p for p in problems if p["kind"] == "manifest_shape"]
            self.assertEqual(len(shapes), 1, (extra, problems))
            self.assertIn(expected, shapes[0]["problem"],
                          (extra, shapes[0]))

    def test_digit_string_values_accepted(self):
        manifest = dict(self.MANIFEST, operator_cells={
            "2": {"A": {"0": "9", "1": 6}}})
        pd = self.county(manifest, {
            "2": self.parsed_page([246.0, 291.0],
                                  [("A", {246.0: 5}, 5)])})
        (row,) = pd["candidate_rows"]
        self.assertEqual(row["cells"], {"P1": 9, "P2": 6})


class CliSummaryTests(unittest.TestCase):
    """The CLI summary line reports the skipped-local-page count alongside
    the dropped-local-row count (Task 8 mechanics)."""

    @unittest.skipUnless(SOURCES_PRESENT, "sources checkout not present")
    def test_summary_line_includes_skipped_local_pages(self):
        import contextlib
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = os.path.join(tmp.name, "union.csv")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = ex.main([os.path.join(SOURCES_DIR,
                                       "Union_County_2026_general.pdf"),
                          "--county", "Union",
                          "--manifest", os.path.join(
                              REPO, "2026/header-reads/"
                              "20261103__ms__general__union__headers.json"),
                          "--out", out])
        self.assertEqual(rc, 0)
        lines = stdout.getvalue().splitlines()
        summary = [l for l in lines if l.startswith("Union: ")][0]
        self.assertIn("2 local rows dropped", summary, summary)
        self.assertIn("0 skipped local pages", summary, summary)
        self.assertIn("0 operator-supplied pages", summary, summary)
        self.assertIn("0 operator cells applied", summary, summary)
        self.assertIn("0 gate problem(s)", summary, summary)
        m = re.match(
            r"^Union: (\d+) candidate rows, (\d+) precincts, "
            r"(\d+) local rows dropped, (\d+) skipped local pages, "
            r"(\d+) operator-supplied pages, (\d+) operator cells applied, "
            r"(\d+) gate problem\(s\)$", summary)
        self.assertIsNotNone(m, summary)


if __name__ == "__main__":
    unittest.main()
