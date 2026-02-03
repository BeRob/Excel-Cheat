"""Tests für den Excel-Reader."""

import unittest
from pathlib import Path

from src.excel.reader import read_excel_headers, _clean_headers


SAMPLE_FILE = Path(__file__).resolve().parent.parent / "Beispiel_Messwerte_Prozess.xlsx"


class TestExcelReader(unittest.TestCase):

    def test_read_sample_headers(self):
        result = read_excel_headers(SAMPLE_FILE)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.headers), 7)
        self.assertIn("Charge_#", result.headers)
        self.assertIn("FA_#", result.headers)
        self.assertIn("Rolle_#", result.headers)

    def test_header_column_map(self):
        result = read_excel_headers(SAMPLE_FILE)
        self.assertEqual(result.header_column_map["Charge_#"], 1)
        self.assertEqual(result.header_column_map["FA_#"], 2)
        self.assertEqual(result.header_column_map["Rolle_#"], 3)

    def test_sheet_names(self):
        result = read_excel_headers(SAMPLE_FILE)
        self.assertIn("Prozess_Beispiel", result.sheet_names)

    def test_specific_sheet(self):
        result = read_excel_headers(SAMPLE_FILE, sheet_name="Prozess_Beispiel")
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.headers), 7)

    def test_file_not_found(self):
        result = read_excel_headers("/nonexistent/file.xlsx")
        self.assertTrue(len(result.errors) > 0)

    def test_invalid_sheet_name(self):
        result = read_excel_headers(SAMPLE_FILE, sheet_name="NonExistent")
        self.assertTrue(len(result.errors) > 0)


class TestCleanHeaders(unittest.TestCase):

    def test_normal_headers(self):
        headers, col_map, errors = _clean_headers(["A", "B", "C"])
        self.assertEqual(headers, ["A", "B", "C"])
        self.assertEqual(len(errors), 0)
        self.assertEqual(col_map["A"], 1)

    def test_empty_header(self):
        headers, col_map, errors = _clean_headers(["A", None, "C"])
        self.assertTrue(len(errors) > 0)

    def test_duplicate_headers(self):
        headers, col_map, errors = _clean_headers(["A", "A", "B"])
        self.assertEqual(headers[0], "A")
        self.assertEqual(headers[1], "A_2")
        self.assertEqual(len(errors), 0)

    def test_whitespace_stripped(self):
        headers, _, _ = _clean_headers(["  A  ", " B "])
        self.assertEqual(headers, ["A", "B"])


if __name__ == "__main__":
    unittest.main()
