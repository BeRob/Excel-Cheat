"""Tests fuer die Prozesskonfiguration."""

import json
import tempfile
import unittest
from pathlib import Path

from src.config.process_config import (
    AppConfig,
    FieldDef,
    ProcessConfig,
    ProductConfig,
    ShiftDef,
    determine_shift,
    get_all_headers,
    get_auto_fields,
    get_context_fields,
    get_field_by_id,
    get_measurement_fields,
    get_per_measurement_context_fields,
    get_persistent_context_fields,
    load_app_config,
    load_product_config,
)


def _make_process() -> ProcessConfig:
    """Erzeugt eine Beispiel-Prozesskonfiguration."""
    return ProcessConfig(
        template_id="IPC1_Test",
        display_name="IPC1 Test",
        fields=[
            FieldDef(id="lot", display_name="LOT Nr.", type="text", role="context", persistent=True),
            FieldDef(id="rollen", display_name="Rollen Nr.", type="text", role="context", persistent=False),
            FieldDef(id="breite", display_name="Breite", type="number", role="measurement",
                     spec_min=180, spec_max=190, spec_target=185),
            FieldDef(id="ask", display_name="ASK", type="choice", role="measurement",
                     options=["Ja", "Nein"]),
            FieldDef(id="datum", display_name="Datum", type="text", role="auto"),
            FieldDef(id="bearbeiter", display_name="Bearbeiter", type="text", role="auto"),
        ],
    )


class TestFieldFilters(unittest.TestCase):

    def setUp(self):
        self.process = _make_process()

    def test_get_context_fields(self):
        fields = get_context_fields(self.process)
        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0].id, "lot")
        self.assertEqual(fields[1].id, "rollen")

    def test_get_persistent_context_fields(self):
        fields = get_persistent_context_fields(self.process)
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].id, "lot")

    def test_get_per_measurement_context_fields(self):
        fields = get_per_measurement_context_fields(self.process)
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].id, "rollen")

    def test_get_measurement_fields(self):
        fields = get_measurement_fields(self.process)
        self.assertEqual(len(fields), 2)
        ids = [f.id for f in fields]
        self.assertIn("breite", ids)
        self.assertIn("ask", ids)

    def test_get_auto_fields(self):
        fields = get_auto_fields(self.process)
        self.assertEqual(len(fields), 2)
        ids = [f.id for f in fields]
        self.assertIn("datum", ids)
        self.assertIn("bearbeiter", ids)

    def test_get_all_headers(self):
        headers = get_all_headers(self.process)
        self.assertEqual(len(headers), 6)
        self.assertEqual(headers[0], "LOT Nr.")
        self.assertEqual(headers[-1], "Bearbeiter")

    def test_get_field_by_id(self):
        field = get_field_by_id(self.process, "breite")
        self.assertIsNotNone(field)
        self.assertEqual(field.display_name, "Breite")

    def test_get_field_by_id_not_found(self):
        field = get_field_by_id(self.process, "nonexistent")
        self.assertIsNone(field)


class TestDetermineShift(unittest.TestCase):

    def setUp(self):
        self.shifts = [
            ShiftDef(name="1", start_hour=6, end_hour=14),
            ShiftDef(name="2", start_hour=14, end_hour=22),
            ShiftDef(name="3", start_hour=22, end_hour=6),
        ]

    def test_shift_1_morning(self):
        self.assertEqual(determine_shift(8, self.shifts), "1")

    def test_shift_1_start(self):
        self.assertEqual(determine_shift(6, self.shifts), "1")

    def test_shift_2_afternoon(self):
        self.assertEqual(determine_shift(16, self.shifts), "2")

    def test_shift_2_start(self):
        self.assertEqual(determine_shift(14, self.shifts), "2")

    def test_shift_3_night(self):
        self.assertEqual(determine_shift(23, self.shifts), "3")

    def test_shift_3_after_midnight(self):
        self.assertEqual(determine_shift(3, self.shifts), "3")

    def test_shift_3_start(self):
        self.assertEqual(determine_shift(22, self.shifts), "3")

    def test_fallback(self):
        self.assertEqual(determine_shift(10, []), "1")


class TestLoadProductConfig(unittest.TestCase):

    def test_load_from_file(self):
        data = {
            "product_id": "TEST001",
            "display_name": "Test Product",
            "processes": [
                {
                    "template_id": "PROC1",
                    "display_name": "Process 1",
                    "fields": [
                        {"id": "f1", "display_name": "Field 1", "type": "text", "role": "measurement"},
                    ],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        product = load_product_config(path)
        self.assertEqual(product.product_id, "TEST001")
        self.assertEqual(product.display_name, "Test Product")
        self.assertEqual(len(product.processes), 1)
        self.assertEqual(product.processes[0].template_id, "PROC1")
        self.assertEqual(len(product.processes[0].fields), 1)

        path.unlink()

    def test_field_defaults(self):
        """Felder ohne optionale Angaben bekommen Defaults."""
        data = {
            "product_id": "T",
            "display_name": "T",
            "processes": [
                {
                    "template_id": "P",
                    "display_name": "P",
                    "fields": [
                        {"id": "x", "display_name": "X"},
                    ],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        product = load_product_config(path)
        field = product.processes[0].fields[0]
        self.assertEqual(field.type, "text")
        self.assertEqual(field.role, "measurement")
        self.assertFalse(field.persistent)
        self.assertFalse(field.optional)
        self.assertIsNone(field.spec_min)
        self.assertIsNone(field.options)

        path.unlink()

    def test_row_group_size(self):
        data = {
            "product_id": "T",
            "display_name": "T",
            "processes": [
                {
                    "template_id": "P",
                    "display_name": "P",
                    "row_group_size": 3,
                    "fields": [],
                },
            ],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        product = load_product_config(path)
        self.assertEqual(product.processes[0].row_group_size, 3)

        path.unlink()


class TestLoadAppConfig(unittest.TestCase):

    def test_load_with_products(self):
        tmp = Path(tempfile.mkdtemp())
        config_path = tmp / "app_config.json"
        products_dir = tmp / "products"
        products_dir.mkdir()

        config_path.write_text(json.dumps({
            "output_dir": "out",
            "shifts": [
                {"name": "1", "start_hour": 6, "end_hour": 14},
            ],
        }), encoding="utf-8")

        (products_dir / "prod1.json").write_text(json.dumps({
            "product_id": "P1",
            "display_name": "Product 1",
            "processes": [],
        }), encoding="utf-8")

        app_config = load_app_config(config_path, products_dir)
        self.assertEqual(app_config.output_dir, "out")
        self.assertEqual(len(app_config.shifts), 1)
        self.assertEqual(len(app_config.products), 1)
        self.assertEqual(app_config.products[0].product_id, "P1")

        import shutil
        shutil.rmtree(tmp)

    def test_missing_config_file(self):
        tmp = Path(tempfile.mkdtemp())
        products_dir = tmp / "products"
        products_dir.mkdir()

        app_config = load_app_config(tmp / "nonexistent.json", products_dir)
        self.assertEqual(app_config.output_dir, "output")
        self.assertEqual(len(app_config.shifts), 0)
        self.assertEqual(len(app_config.products), 0)

        import shutil
        shutil.rmtree(tmp)

    def test_missing_products_dir(self):
        tmp = Path(tempfile.mkdtemp())
        config_path = tmp / "app_config.json"
        config_path.write_text("{}", encoding="utf-8")

        app_config = load_app_config(config_path, tmp / "nonexistent")
        self.assertEqual(len(app_config.products), 0)

        import shutil
        shutil.rmtree(tmp)


class TestLoadRealConfig(unittest.TestCase):
    """Test mit der echten REF31962-Konfiguration."""

    def test_load_ref31962(self):
        data_dir = Path(__file__).resolve().parent.parent / "data"
        config_path = data_dir / "app_config.json"
        products_dir = data_dir / "products"

        app_config = load_app_config(config_path, products_dir)
        self.assertGreaterEqual(len(app_config.products), 1)

        ref = app_config.products[0]
        self.assertEqual(ref.product_id, "REF31962")
        self.assertEqual(len(ref.processes), 5)

        # IPC1
        ipc1 = ref.processes[0]
        self.assertEqual(ipc1.template_id, "IPC1_Vorschneiden")
        self.assertIsNone(ipc1.row_group_size)

        # IPC2 hat row_group_size
        ipc2 = ref.processes[1]
        self.assertEqual(ipc2.row_group_size, 3)

        # Feld-Rollen pruefen
        lot = get_field_by_id(ipc1, "lot_nr")
        self.assertIsNotNone(lot)
        self.assertTrue(lot.persistent)
        self.assertEqual(lot.role, "context")

        breite = get_field_by_id(ipc1, "breite_1")
        self.assertIsNotNone(breite)
        self.assertEqual(breite.spec_min, 180)
        self.assertEqual(breite.spec_max, 190)


if __name__ == "__main__":
    unittest.main()
