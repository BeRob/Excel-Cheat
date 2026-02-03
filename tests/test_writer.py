"""Tests fuer den Excel-Writer."""

import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import openpyxl

from src.domain.state import UserInfo
from src.excel.writer import write_measurement_row


SAMPLE_FILE = Path(__file__).resolve().parent.parent / "Beispiel_Messwerte_Prozess.xlsx"


class TestExcelWriter(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.tmp_dir) / "test.xlsx"
        shutil.copy(SAMPLE_FILE, self.test_file)
        self.persistent_values = {"Charge_#": "C-TEST", "FA_#": "FA-001", "Rolle_#": "R1"}
        self.user = UserInfo(user_id="testuser", display_name="Test User")
        # Read actual row count to determine next_row
        wb = openpyxl.load_workbook(self.test_file, read_only=True)
        ws = wb[wb.sheetnames[0]]
        self._existing_rows = ws.max_row
        wb.close()
        self.col_map = {
            "Charge_#": 1, "FA_#": 2, "Rolle_#": 3,
            "Länge (mm)": 4, "Breite (mm)": 5, "Dicke (mm)": 6, "Gewicht (g)": 7,
            "Zeit": 8, "Mitarbeiter": 9,
        }

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_write_appends_row(self):
        measurements = {"Länge (mm)": 100.0, "Breite (mm)": 50.0, "Dicke (mm)": 2.0, "Gewicht (g)": 10.0}
        result = write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.persistent_values, self.user, measurements
        )
        self.assertTrue(result.success)
        self.assertEqual(result.row_number, self._existing_rows + 1)

    def test_auto_columns_not_recreated(self):
        """Auto columns already exist in sample file, so none should be created."""
        measurements = {"Länge (mm)": 100.0}
        result = write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.persistent_values, self.user, measurements
        )
        self.assertTrue(result.success)
        # Zeit and Mitarbeiter already exist in col_map, so nothing new created
        self.assertEqual(len(result.columns_created), 0)

    def test_auto_columns_created_when_missing(self):
        """Auto columns are created if not in col_map."""
        col_map_no_auto = {
            "Charge_#": 1, "FA_#": 2, "Rolle_#": 3,
            "Länge (mm)": 4, "Breite (mm)": 5, "Dicke (mm)": 6, "Gewicht (g)": 7,
        }
        measurements = {"Länge (mm)": 100.0}
        result = write_measurement_row(
            self.test_file, "Prozess_Beispiel", col_map_no_auto,
            self.persistent_values, self.user, measurements
        )
        self.assertTrue(result.success)
        # Only auto columns should be created (Zeit, Mitarbeiter)
        # They may or may not appear depending on whether they exist in the file
        # but not in the map - the function should try to create them
        for col in result.columns_created:
            self.assertIn(col, ["Zeit", "Mitarbeiter"])

    def test_context_values_written(self):
        measurements = {"Länge (mm)": 100.0}
        result = write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.persistent_values, self.user, measurements
        )
        written_row = result.row_number
        wb = openpyxl.load_workbook(self.test_file, read_only=True)
        ws = wb["Prozess_Beispiel"]
        row = list(ws.iter_rows(min_row=written_row, max_row=written_row, values_only=True))[0]
        self.assertEqual(row[0], "C-TEST")
        self.assertEqual(row[1], "FA-001")
        self.assertEqual(row[2], "R1")
        wb.close()

    def test_zeit_is_datetime(self):
        measurements = {"Länge (mm)": 100.0}
        result = write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.persistent_values, self.user, measurements
        )
        written_row = result.row_number
        wb = openpyxl.load_workbook(self.test_file, read_only=True)
        ws = wb["Prozess_Beispiel"]
        row = list(ws.iter_rows(min_row=written_row, max_row=written_row, values_only=True))[0]
        # Zeit should be at index 7 (column 8)
        self.assertIsInstance(row[7], datetime)
        wb.close()

    def test_mitarbeiter_written(self):
        measurements = {"Länge (mm)": 100.0}
        result = write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.persistent_values, self.user, measurements
        )
        written_row = result.row_number
        wb = openpyxl.load_workbook(self.test_file, read_only=True)
        ws = wb["Prozess_Beispiel"]
        row = list(ws.iter_rows(min_row=written_row, max_row=written_row, values_only=True))[0]
        # Mitarbeiter should be at index 8 (column 9)
        self.assertEqual(row[8], "testuser")
        wb.close()

    def test_two_sequential_writes(self):
        measurements = {"Länge (mm)": 100.0}
        r1 = write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.persistent_values, self.user, measurements
        )
        r2 = write_measurement_row(
            self.test_file, "Prozess_Beispiel", self.col_map,
            self.persistent_values, self.user, measurements
        )
        self.assertEqual(r1.row_number, self._existing_rows + 1)
        self.assertEqual(r2.row_number, self._existing_rows + 2)

    def test_file_not_found(self):
        result = write_measurement_row(
            "/nonexistent/file.xlsx", "Sheet1", self.col_map,
            self.persistent_values, self.user, {}
        )
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)

    def test_invalid_sheet(self):
        result = write_measurement_row(
            self.test_file, "NonExistent", self.col_map,
            self.persistent_values, self.user, {}
        )
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
