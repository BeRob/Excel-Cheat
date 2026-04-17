"""Tests für den Excel-Writer (neue config-basierte API)."""

import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import openpyxl

from src.config.process_config import FieldDef, ProcessConfig
from src.config.settings import HEADER_ROW
from src.excel.creator import create_measurement_file
from src.excel.writer import write_measurement_row


def _make_process() -> ProcessConfig:
    return ProcessConfig(
        template_id="IPC1_Test",
        display_name="IPC1 Test",
        fields=[
            FieldDef(id="lot", display_name="LOT Nr.", type="text", role="context", persistent=True),
            FieldDef(id="rollen", display_name="Rollen Nr.", type="text", role="context"),
            FieldDef(id="breite", display_name="Breite 1", type="number", role="measurement",
                     spec_min=180, spec_max=190),
            FieldDef(id="breite2", display_name="Breite 2", type="number", role="measurement",
                     spec_min=180, spec_max=190),
            FieldDef(id="datum", display_name="Datum", type="text", role="auto"),
            FieldDef(id="bearbeiter", display_name="Bearbeiter", type="text", role="auto"),
        ],
    )


class TestWriteMeasurementRow(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.process = _make_process()
        self.filepath = create_measurement_file(
            self.process, "TEST", self.tmp_dir, "1", date(2026, 4, 2)
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_write_appends_row(self):
        result = write_measurement_row(
            self.filepath,
            self.process,
            context_values={"LOT Nr.": "LOT-001", "Rollen Nr.": "R1"},
            measurements={"Breite 1": 185.0, "Breite 2": 186.0},
            auto_values={"Datum": "2026-04-02", "Bearbeiter": "testuser"},
        )
        self.assertTrue(result.success)
        self.assertEqual(result.row_number, HEADER_ROW + 1)

    def test_values_in_correct_columns(self):
        write_measurement_row(
            self.filepath,
            self.process,
            context_values={"LOT Nr.": "LOT-001", "Rollen Nr.": "R1"},
            measurements={"Breite 1": 185.0, "Breite 2": 186.0},
            auto_values={"Datum": "2026-04-02", "Bearbeiter": "testuser"},
        )
        wb = openpyxl.load_workbook(self.filepath, read_only=True)
        ws = wb.active
        data_row = HEADER_ROW + 1
        row = [ws.cell(data_row, c).value for c in range(1, 7)]
        self.assertEqual(row[0], "LOT-001")     # col 1: LOT Nr.
        self.assertEqual(row[1], "R1")           # col 2: Rollen Nr.
        self.assertAlmostEqual(row[2], 185.0)    # col 3: Breite 1
        self.assertAlmostEqual(row[3], 186.0)    # col 4: Breite 2
        self.assertEqual(row[4], "2026-04-02")   # col 5: Datum
        self.assertEqual(row[5], "testuser")     # col 6: Bearbeiter
        wb.close()

    def test_two_sequential_writes(self):
        ctx = {"LOT Nr.": "LOT-001", "Rollen Nr.": "R1"}
        meas = {"Breite 1": 185.0, "Breite 2": 186.0}
        auto = {"Datum": "2026-04-02", "Bearbeiter": "user"}

        r1 = write_measurement_row(self.filepath, self.process, ctx, meas, auto)
        r2 = write_measurement_row(self.filepath, self.process, ctx, meas, auto)
        self.assertEqual(r1.row_number, HEADER_ROW + 1)
        self.assertEqual(r2.row_number, HEADER_ROW + 2)

    def test_file_not_found(self):
        result = write_measurement_row(
            Path("/nonexistent/file.xlsx"),
            self.process,
            {}, {}, {},
        )
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)

    def test_none_values_skipped(self):
        result = write_measurement_row(
            self.filepath,
            self.process,
            context_values={"LOT Nr.": "LOT-001"},
            measurements={"Breite 1": None},
            auto_values={"Datum": "2026-04-02"},
        )
        self.assertTrue(result.success)
        wb = openpyxl.load_workbook(self.filepath, read_only=True)
        ws = wb.active
        data_row = HEADER_ROW + 1
        # Breite 1 (col 3) should be None since we passed None
        self.assertIsNone(ws.cell(data_row, 3).value)
        # Rollen Nr. (col 2) should be None since not provided
        self.assertIsNone(ws.cell(data_row, 2).value)
        wb.close()

    def test_partial_measurements(self):
        result = write_measurement_row(
            self.filepath,
            self.process,
            context_values={"LOT Nr.": "LOT-001"},
            measurements={"Breite 1": 185.0},
            auto_values={},
        )
        self.assertTrue(result.success)
        wb = openpyxl.load_workbook(self.filepath, read_only=True)
        ws = wb.active
        data_row = HEADER_ROW + 1
        self.assertAlmostEqual(ws.cell(data_row, 3).value, 185.0)
        self.assertIsNone(ws.cell(data_row, 4).value)  # Breite 2 not provided
        wb.close()


if __name__ == "__main__":
    unittest.main()
