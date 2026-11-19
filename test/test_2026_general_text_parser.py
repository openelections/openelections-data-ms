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
