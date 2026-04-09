"""Tests fuer die Excel-Dateierstellung."""

import shutil
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import openpyxl

from src.config.process_config import FieldDef, ProcessConfig
from src.config.settings import HEADER_ROW
from src.excel.creator import (
    count_data_rows,
    create_measurement_file,
    find_existing_file,
    generate_file_name,
    get_shift_date,
    write_info_header,
)


def _make_process() -> ProcessConfig:
    return ProcessConfig(
        template_id="IPC1_Test",
        display_name="IPC1 Test",
        fields=[
            FieldDef(id="lot", display_name="LOT Nr.", type="text", role="context"),
            FieldDef(id="breite", display_name="Breite", type="number", role="measurement"),
            FieldDef(id="datum", display_name="Datum", type="text", role="auto"),
        ],
    )


class TestGenerateFileName(unittest.TestCase):

    def test_format(self):
        process = _make_process()
        name = generate_file_name(process, "REF123", "1", date(2026, 4, 1))
        self.assertEqual(name, "IPC1_Test_REF123_Schicht1_2026-04-01.xlsx")

    def test_shift_3(self):
        process = _make_process()
        name = generate_file_name(process, "REF123", "3", date(2026, 3, 31))
        self.assertEqual(name, "IPC1_Test_REF123_Schicht3_2026-03-31.xlsx")


class TestGetShiftDate(unittest.TestCase):

    def test_shift_1_normal(self):
        dt = datetime(2026, 4, 1, 10, 0)
        self.assertEqual(get_shift_date(dt, "1"), date(2026, 4, 1))

    def test_shift_3_before_midnight(self):
        dt = datetime(2026, 4, 1, 23, 0)
        self.assertEqual(get_shift_date(dt, "3"), date(2026, 4, 1))

    def test_shift_3_after_midnight(self):
        dt = datetime(2026, 4, 2, 2, 0)
        self.assertEqual(get_shift_date(dt, "3"), date(2026, 4, 1))

    def test_shift_2_not_affected(self):
        dt = datetime(2026, 4, 1, 2, 0)
        self.assertEqual(get_shift_date(dt, "2"), date(2026, 4, 1))


class TestCreateMeasurementFile(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.process = _make_process()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_creates_file(self):
        path = create_measurement_file(
            self.process, "REF123", self.tmp_dir, "1", date(2026, 4, 1)
        )
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "IPC1_Test_REF123_Schicht1_2026-04-01.xlsx")

    def test_header_row(self):
        path = create_measurement_file(
            self.process, "REF123", self.tmp_dir, "1", date(2026, 4, 1)
        )
        wb = openpyxl.load_workbook(path, read_only=True)
        ws = wb.active
        headers = [ws.cell(HEADER_ROW, c).value for c in range(1, 4)]
        wb.close()
        self.assertEqual(headers, ["LOT Nr.", "Breite", "Datum"])

    def test_creates_output_dir(self):
        sub = self.tmp_dir / "sub" / "dir"
        path = create_measurement_file(
            self.process, "REF123", sub, "1", date(2026, 4, 1)
        )
        self.assertTrue(sub.exists())
        self.assertTrue(path.exists())


class TestFindExistingFile(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.process = _make_process()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_not_found(self):
        result = find_existing_file(
            self.process, "REF123", self.tmp_dir, "1", date(2026, 4, 1)
        )
        self.assertIsNone(result)

    def test_found(self):
        create_measurement_file(
            self.process, "REF123", self.tmp_dir, "1", date(2026, 4, 1)
        )
        result = find_existing_file(
            self.process, "REF123", self.tmp_dir, "1", date(2026, 4, 1)
        )
        self.assertIsNotNone(result)
        self.assertTrue(result.exists())


class TestCountDataRows(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.process = _make_process()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_empty_file(self):
        path = create_measurement_file(
            self.process, "REF123", self.tmp_dir, "1", date(2026, 4, 1)
        )
        self.assertEqual(count_data_rows(path), 0)

    def test_with_data(self):
        path = create_measurement_file(
            self.process, "REF123", self.tmp_dir, "1", date(2026, 4, 1)
        )
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        ws.cell(HEADER_ROW + 1, 1, "LOT-001")
        ws.cell(HEADER_ROW + 2, 1, "LOT-002")
        wb.save(path)
        wb.close()
        self.assertEqual(count_data_rows(path), 2)

    def test_nonexistent_file(self):
        self.assertEqual(count_data_rows(Path("/nonexistent.xlsx")), 0)


class TestWriteInfoHeader(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.process = _make_process()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_writes_info(self):
        path = create_measurement_file(
            self.process, "REF123", self.tmp_dir, "1", date(2026, 4, 1)
        )
        write_info_header(
            path, "Test Product", "IPC1 Test", "FA-12345", "1", date(2026, 4, 1)
        )
        wb = openpyxl.load_workbook(path, read_only=True)
        ws = wb.active
        self.assertEqual(ws.cell(1, 1).value, "Produkt:")
        self.assertEqual(ws.cell(1, 2).value, "Test Product")
        self.assertEqual(ws.cell(2, 1).value, "Prozess:")
        self.assertEqual(ws.cell(2, 2).value, "IPC1 Test")
        self.assertEqual(ws.cell(3, 1).value, "FA-Nr.:")
        self.assertEqual(ws.cell(3, 2).value, "FA-12345")
        self.assertEqual(ws.cell(4, 1).value, "Schicht:")
        self.assertEqual(ws.cell(4, 2).value, "1")
        self.assertEqual(ws.cell(5, 1).value, "Datum:")
        self.assertEqual(ws.cell(5, 2).value, "2026-04-01")
        # Column headers still at HEADER_ROW
        self.assertEqual(ws.cell(HEADER_ROW, 1).value, "LOT Nr.")
        wb.close()


if __name__ == "__main__":
    unittest.main()
