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
        chars.append(c(",", 246.0, 120.0 + 9 * 8))  # comma in the name
        for i, ch in enumerate("Chunky"):
            chars.append(c(ch, 291.0, 120.0 + i * 9))
        # wide prose line to be excluded (spans across columns)
        for x in range(60, 400, 5):
            chars.append(c("x", float(x), 96.0))
        return chars

    def test_read_vertical_headers(self):
        chars = self.build_table_chars()
        got = ex.vertical_headers(chars, [246.0, 291.0], [(90.0, 100.0)])
        self.assertEqual(got[246.0], "Bellemont,")
        self.assertEqual(got[291.0], "Chunky")

    def test_total_header_detected(self):
        chars = [c(ch, 700.0, 120.0 + i * 9) for i, ch in enumerate("TOTAL")]
        got = ex.vertical_headers(chars, [700.0], [])
        self.assertEqual(ex.total_col(got), 700.0)

    def test_header_word_gap_becomes_space(self):
        chars = ([c(ch, 246.0, 120.0 + i * 9) for i, ch in enumerate("Dist")]
                 + [c(ch, 246.0, 120.0 + 4 * 9 + 6 + i * 9) for i, ch in enumerate("1")])
        got = ex.vertical_headers(chars, [246.0], [])
        self.assertEqual(got[246.0], "Dist 1")


if __name__ == "__main__":
    unittest.main()
