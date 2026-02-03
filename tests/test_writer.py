"""Tests für den Excel-Writer."""

import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import openpyxl

from src.domain.state import ContextInfo, UserInfo
from src.excel.writer import write_measurement_row


SAMPLE_FILE = Path(__file__).resolve().parent.parent / "Beispiel_Messwerte_Prozess.xlsx"


class TestExcelWriter(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.tmp_dir) / "test.xlsx"
        shutil.copy(SAMPLE_FILE, self.test_file)
        self.context = ContextInfo(charge="C-TEST", fa="FA-001", rolle="R1")
        self.user = UserInfo(user_id="testuser", display_name="Test User")
        self.col_map = {
            "Charge_#": 1, "FA_#": 2, "Rolle_#": 3,
            "Länge (mm)": 4, "Breite (mm)": 5, "Dicke (mm)": 6, "Gewicht (g)": 7,
        }

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_write_appends_row(self):
        measurements = {"Länge (mm)": 100.0, "Breite (mm)": 50.0, "Dicke (mm)": 2.0, "Gewicht (g)": 10.0}
        result = write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.context, self.user, measurements
        )
        self.assertTrue(result.success)
        self.assertEqual(result.row_number, 5)

    def test_auto_columns_created(self):
        measurements = {"Länge (mm)": 100.0}
        result = write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.context, self.user, measurements
        )
        self.assertIn("Zeit", result.columns_created)
        self.assertIn("Mitarbeiter", result.columns_created)

    def test_context_values_written(self):
        measurements = {"Länge (mm)": 100.0}
        write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.context, self.user, measurements
        )
        wb = openpyxl.load_workbook(self.test_file, read_only=True)
        ws = wb["Prozess_Beispiel"]
        row = list(ws.iter_rows(min_row=5, max_row=5, values_only=True))[0]
        self.assertEqual(row[0], "C-TEST")
        self.assertEqual(row[1], "FA-001")
        self.assertEqual(row[2], "R1")
        wb.close()

    def test_zeit_is_datetime(self):
        measurements = {"Länge (mm)": 100.0}
        write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.context, self.user, measurements
        )
        wb = openpyxl.load_workbook(self.test_file, read_only=True)
        ws = wb["Prozess_Beispiel"]
        row = list(ws.iter_rows(min_row=5, max_row=5, values_only=True))[0]
        # Zeit should be at index 7 (column 8)
        self.assertIsInstance(row[7], datetime)
        wb.close()

    def test_mitarbeiter_written(self):
        measurements = {"Länge (mm)": 100.0}
        write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.context, self.user, measurements
        )
        wb = openpyxl.load_workbook(self.test_file, read_only=True)
        ws = wb["Prozess_Beispiel"]
        row = list(ws.iter_rows(min_row=5, max_row=5, values_only=True))[0]
        # Mitarbeiter should be at index 8 (column 9)
        self.assertEqual(row[8], "testuser")
        wb.close()

    def test_two_sequential_writes(self):
        measurements = {"Länge (mm)": 100.0}
        r1 = write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.context, self.user, measurements
        )
        # Update col_map with auto columns for second write
        col_map2 = dict(self.col_map)
        col_map2["Zeit"] = 8
        col_map2["Mitarbeiter"] = 9
        r2 = write_measurement_row(
            self.test_file, "Prozess_Beispiel", col_map2,
            self.context, self.user, measurements
        )
        self.assertEqual(r1.row_number, 5)
        self.assertEqual(r2.row_number, 6)

    def test_file_not_found(self):
        result = write_measurement_row(
            "/nonexistent/file.xlsx", "Sheet1", self.col_map,
            self.context, self.user, {}
        )
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)

    def test_invalid_sheet(self):
        result = write_measurement_row(
            self.test_file, "NonExistent", self.col_map,
            self.context, self.user, {}
        )
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
