"""Tests fuer config_writer (Serialisierung, Validierung, Speichern)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.config.config_writer import (
    field_to_dict,
    process_to_dict,
    product_to_dict,
    save_product_config,
    validate_product_config,
)
from src.config.process_config import (
    FieldDef,
    ProcessConfig,
    ProductConfig,
    load_product_config,
)


def _make_valid_product() -> ProductConfig:
    """Erzeugt ein gueltiges Beispiel-Produkt."""
    return ProductConfig(
        product_id="TEST001",
        display_name="Test Produkt",
        processes=[
            ProcessConfig(
                template_id="PROC1",
                display_name="Prozess 1",
                fields=[
                    FieldDef(
                        id="f1",
                        display_name="Feld 1",
                        type="text",
                        role="context",
                        persistent=True,
                    ),
                    FieldDef(
                        id="f2",
                        display_name="Feld 2",
                        type="number",
                        role="measurement",
                        spec_min=10.0,
                        spec_max=20.0,
                        spec_target=15.0,
                    ),
                    FieldDef(
                        id="f3",
                        display_name="Feld 3",
                        type="choice",
                        role="measurement",
                        options=["Ja", "Nein"],
                    ),
                ],
            ),
        ],
    )


class TestFieldToDict(unittest.TestCase):

    def test_minimal(self):
        field = FieldDef(id="x", display_name="X", type="text", role="measurement")
        d = field_to_dict(field)
        self.assertEqual(d["id"], "x")
        self.assertEqual(d["display_name"], "X")
        self.assertEqual(d["type"], "text")
        self.assertEqual(d["role"], "measurement")
        self.assertNotIn("persistent", d)
        self.assertNotIn("optional", d)
        self.assertNotIn("spec_min", d)
        self.assertNotIn("spec_max", d)
        self.assertNotIn("spec_target", d)
        self.assertNotIn("options", d)

    def test_number_with_specs(self):
        field = FieldDef(
            id="b", display_name="Breite", type="number", role="measurement",
            spec_min=180, spec_max=190, spec_target=185,
        )
        d = field_to_dict(field)
        self.assertEqual(d["spec_min"], 180)
        self.assertEqual(d["spec_max"], 190)
        self.assertEqual(d["spec_target"], 185)

    def test_choice_with_options(self):
        field = FieldDef(
            id="ask", display_name="ASK", type="choice", role="measurement",
            options=["Ja", "Nein"],
        )
        d = field_to_dict(field)
        self.assertEqual(d["options"], ["Ja", "Nein"])

    def test_persistent_and_optional(self):
        field = FieldDef(
            id="lot", display_name="LOT", type="text", role="context",
            persistent=True, optional=True,
        )
        d = field_to_dict(field)
        self.assertTrue(d["persistent"])
        self.assertTrue(d["optional"])


class TestProcessToDict(unittest.TestCase):

    def test_with_row_group(self):
        proc = ProcessConfig(
            template_id="P1", display_name="P1",
            fields=[FieldDef(id="f", display_name="F", type="text", role="measurement")],
            row_group_size=3,
        )
        d = process_to_dict(proc)
        self.assertEqual(d["row_group_size"], 3)

    def test_without_row_group(self):
        proc = ProcessConfig(
            template_id="P1", display_name="P1",
            fields=[FieldDef(id="f", display_name="F", type="text", role="measurement")],
        )
        d = process_to_dict(proc)
        self.assertNotIn("row_group_size", d)


class TestProductToDict(unittest.TestCase):

    def test_with_output_dir(self):
        product = _make_valid_product()
        product.output_dir = "output/custom"
        d = product_to_dict(product)
        self.assertEqual(d["output_dir"], "output/custom")

    def test_without_output_dir(self):
        product = _make_valid_product()
        d = product_to_dict(product)
        self.assertNotIn("output_dir", d)


class TestRoundtrip(unittest.TestCase):

    def test_roundtrip(self):
        """Serialize -> write JSON -> parse back -> verify."""
        product = _make_valid_product()
        product.output_dir = "output/test"
        product.processes[0].row_group_size = 3

        tmp = Path(tempfile.mkdtemp())
        try:
            path = save_product_config(product, tmp)
            loaded = load_product_config(path)

            self.assertEqual(loaded.product_id, product.product_id)
            self.assertEqual(loaded.display_name, product.display_name)
            self.assertEqual(loaded.output_dir, product.output_dir)
            self.assertEqual(len(loaded.processes), 1)

            proc = loaded.processes[0]
            self.assertEqual(proc.template_id, "PROC1")
            self.assertEqual(proc.row_group_size, 3)
            self.assertEqual(len(proc.fields), 3)

            f1 = proc.fields[0]
            self.assertEqual(f1.id, "f1")
            self.assertTrue(f1.persistent)

            f2 = proc.fields[1]
            self.assertEqual(f2.spec_min, 10.0)
            self.assertEqual(f2.spec_max, 20.0)
            self.assertEqual(f2.spec_target, 15.0)

            f3 = proc.fields[2]
            self.assertEqual(f3.options, ["Ja", "Nein"])
        finally:
            shutil.rmtree(tmp)


class TestValidation(unittest.TestCase):

    def test_valid_config(self):
        errors = validate_product_config(_make_valid_product())
        self.assertEqual(errors, [])

    def test_empty_product_id(self):
        p = _make_valid_product()
        p.product_id = ""
        errors = validate_product_config(p)
        self.assertTrue(any("Produkt-ID" in e for e in errors))

    def test_invalid_product_id_chars(self):
        p = _make_valid_product()
        p.product_id = "REF 31962!"
        errors = validate_product_config(p)
        self.assertTrue(any("Buchstaben" in e for e in errors))

    def test_empty_display_name(self):
        p = _make_valid_product()
        p.display_name = "  "
        errors = validate_product_config(p)
        self.assertTrue(any("Anzeigename" in e for e in errors))

    def test_no_processes(self):
        p = _make_valid_product()
        p.processes = []
        errors = validate_product_config(p)
        self.assertTrue(any("Prozess" in e for e in errors))

    def test_empty_template_id(self):
        p = _make_valid_product()
        p.processes[0].template_id = ""
        errors = validate_product_config(p)
        self.assertTrue(any("Template-ID" in e for e in errors))

    def test_no_fields(self):
        p = _make_valid_product()
        p.processes[0].fields = []
        errors = validate_product_config(p)
        self.assertTrue(any("Feld" in e for e in errors))

    def test_duplicate_field_id(self):
        p = _make_valid_product()
        p.processes[0].fields[1].id = "f1"
        errors = validate_product_config(p)
        self.assertTrue(any("doppelt" in e for e in errors))

    def test_spec_min_gt_max(self):
        p = _make_valid_product()
        p.processes[0].fields[1].spec_min = 200
        p.processes[0].fields[1].spec_max = 100
        errors = validate_product_config(p)
        self.assertTrue(any("spec_min" in e for e in errors))

    def test_spec_target_below_min(self):
        p = _make_valid_product()
        p.processes[0].fields[1].spec_target = 5.0
        errors = validate_product_config(p)
        self.assertTrue(any("spec_target" in e for e in errors))

    def test_spec_target_above_max(self):
        p = _make_valid_product()
        p.processes[0].fields[1].spec_target = 25.0
        errors = validate_product_config(p)
        self.assertTrue(any("spec_target" in e for e in errors))

    def test_choice_no_options(self):
        p = _make_valid_product()
        p.processes[0].fields[2].options = []
        errors = validate_product_config(p)
        self.assertTrue(any("Option" in e for e in errors))

    def test_invalid_type(self):
        p = _make_valid_product()
        p.processes[0].fields[0].type = "invalid"
        errors = validate_product_config(p)
        self.assertTrue(any("Typ" in e for e in errors))

    def test_invalid_role(self):
        p = _make_valid_product()
        p.processes[0].fields[0].role = "invalid"
        errors = validate_product_config(p)
        self.assertTrue(any("Rolle" in e for e in errors))


class TestSaveProductConfig(unittest.TestCase):

    def test_creates_file(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            product = _make_valid_product()
            path = save_product_config(product, tmp)
            self.assertTrue(path.exists())
            self.assertEqual(path.name, "TEST001.json")

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["product_id"], "TEST001")
        finally:
            shutil.rmtree(tmp)

    def test_overwrites_existing(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            product = _make_valid_product()
            save_product_config(product, tmp)

            product.display_name = "Updated Name"
            path = save_product_config(product, tmp)

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["display_name"], "Updated Name")
        finally:
            shutil.rmtree(tmp)

    def test_creates_directory(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            sub = tmp / "sub" / "dir"
            product = _make_valid_product()
            path = save_product_config(product, sub)
            self.assertTrue(sub.exists())
            self.assertTrue(path.exists())
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
