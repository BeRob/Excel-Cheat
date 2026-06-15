"""Tests für die Prozesskonfiguration."""

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


class TestTemplateResolution(unittest.TestCase):
    """Dünne Produkt-Configs werden gegen Operation-Templates aufgelöst."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.tpl_dir = self.tmp / "process_templates"
        self.prod_dir = self.tmp / "products"
        self.tpl_dir.mkdir()
        self.prod_dir.mkdir()

        template = {
            "template": "Schneiden",
            "template_revision": 3,
            "fields": [
                {"id": "fa_nr", "display_name": "FA-Nr.", "type": "text",
                 "role": "context", "persistent": True, "info_header": True},
                {"id": "breite", "display_name": "Breite [mm]", "type": "number",
                 "role": "measurement"},
                {"id": "schnittkante", "display_name": "Schnittkante", "type": "choice",
                 "role": "measurement", "options": ["Ja", "Nein"], "optional": True},
                {"id": "bemerkungen", "display_name": "Bemerkungen", "type": "text",
                 "role": "measurement", "optional": True, "default_value": "n/a",
                 "_present_in": "ALL"},
                {"id": "datum", "display_name": "Datum", "type": "text", "role": "auto"},
            ],
            "_unification_notes": {"breite": "..."},
        }
        (self.tpl_dir / "Schneiden.json").write_text(
            json.dumps(template), encoding="utf-8"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_product(self, data: dict) -> Path:
        path = self.prod_dir / f"{data['product_id']}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_resolve_active_fields_order_and_specs(self):
        from src.config.process_config import load_process_templates
        templates = load_process_templates(self.tpl_dir)
        path = self._write_product({
            "product_id": "REFTEST",
            "display_name": "Test",
            "revision": 1,
            "processes": [{
                "template_id": "IPC3_Fertigschneiden",
                "template": "Schneiden",
                "display_name": "IPC3 Fertigschneiden",
                "active_fields": ["fa_nr", "breite", "bemerkungen", "datum"],
                "field_overrides": {
                    "breite": {"spec_min": 18.0, "spec_max": 22.0, "spec_target": 20.0},
                },
            }],
        })
        product = load_product_config(path, templates)
        proc = product.processes[0]
        # Prozess-Identität bleibt erhalten (Excel-Dateiname/Resume!)
        self.assertEqual(proc.template_id, "IPC3_Fertigschneiden")
        self.assertEqual(proc.template, "Schneiden")
        self.assertEqual(proc.template_revision, 3)
        # active_fields bestimmt Reihenfolge + Auswahl (schnittkante ausgelassen)
        self.assertEqual([f.id for f in proc.fields],
                         ["fa_nr", "breite", "bemerkungen", "datum"])
        breite = next(f for f in proc.fields if f.id == "breite")
        self.assertEqual((breite.spec_min, breite.spec_target, breite.spec_max),
                         (18.0, 20.0, 22.0))
        # default_value/options stammen aus dem Template
        bem = next(f for f in proc.fields if f.id == "bemerkungen")
        self.assertEqual(bem.default_value, "n/a")

    def test_field_override_changes_display_name(self):
        from src.config.process_config import load_process_templates
        templates = load_process_templates(self.tpl_dir)
        path = self._write_product({
            "product_id": "REFTEST2",
            "display_name": "Test2",
            "revision": 1,
            "processes": [{
                "template_id": "IPC2_Fertigschneiden",
                "template": "Schneiden",
                "display_name": "IPC2",
                "active_fields": ["fa_nr", "schnittkante"],
                "field_overrides": {
                    "schnittkante": {"display_name": "Schnittkante sauber?",
                                     "group_shared": True},
                },
            }],
        })
        proc = load_product_config(path, templates).processes[0]
        sk = next(f for f in proc.fields if f.id == "schnittkante")
        self.assertEqual(sk.display_name, "Schnittkante sauber?")
        self.assertTrue(sk.group_shared)
        self.assertEqual(sk.options, ["Ja", "Nein"])  # aus Template übernommen

    def test_extra_field_product_unique(self):
        from src.config.process_config import load_process_templates
        templates = load_process_templates(self.tpl_dir)
        path = self._write_product({
            "product_id": "REFTEST3",
            "display_name": "Test3",
            "revision": 1,
            "processes": [{
                "template_id": "IPC3_Fertigschneiden",
                "template": "Schneiden",
                "display_name": "IPC3",
                "active_fields": ["fa_nr", "sonderfeld"],
                "extra_fields": [
                    {"id": "sonderfeld", "display_name": "Sonderfeld",
                     "type": "number", "role": "measurement"},
                ],
            }],
        })
        proc = load_product_config(path, templates).processes[0]
        self.assertEqual([f.id for f in proc.fields], ["fa_nr", "sonderfeld"])

    def test_unknown_template_raises(self):
        from src.config.process_config import load_process_templates
        templates = load_process_templates(self.tpl_dir)
        path = self._write_product({
            "product_id": "REFBAD",
            "display_name": "Bad",
            "revision": 1,
            "processes": [{
                "template_id": "IPC1_X",
                "template": "GibtsNicht",
                "display_name": "X",
                "active_fields": ["fa_nr"],
            }],
        })
        with self.assertRaises(ValueError):
            load_product_config(path, templates)

    def test_legacy_full_fields_still_load(self):
        # Ohne template/active_fields → klassische volle fields-Liste
        path = self._write_product({
            "product_id": "REFLEGACY",
            "display_name": "Legacy",
            "revision": 1,
            "processes": [{
                "template_id": "IPC1_Alt",
                "display_name": "Alt",
                "fields": [
                    {"id": "fa_nr", "display_name": "FA-Nr.", "type": "text",
                     "role": "context"},
                    {"id": "breite", "display_name": "Breite", "type": "number",
                     "role": "measurement"},
                ],
            }],
        })
        proc = load_product_config(path, {}).processes[0]
        self.assertIsNone(proc.template)
        self.assertEqual([f.id for f in proc.fields], ["fa_nr", "breite"])

    def test_templates_dir_skips_underscore_files(self):
        from src.config.process_config import load_process_templates
        (self.tpl_dir / "_draft.json").write_text(
            json.dumps({"template": "Draft", "fields": []}), encoding="utf-8"
        )
        templates = load_process_templates(self.tpl_dir)
        self.assertIn("Schneiden", templates)
        self.assertNotIn("Draft", templates)


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

    def test_output_dir(self):
        data = {
            "product_id": "T",
            "display_name": "T",
            "output_dir": "output/custom",
            "processes": [],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        product = load_product_config(path)
        self.assertEqual(product.output_dir, "output/custom")

        path.unlink()

    def test_output_dir_default_none(self):
        data = {
            "product_id": "T",
            "display_name": "T",
            "processes": [],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = Path(f.name)

        product = load_product_config(path)
        self.assertIsNone(product.output_dir)

        path.unlink()


class TestLoadAppConfig(unittest.TestCase):

    def test_load_with_products(self):
        tmp = Path(tempfile.mkdtemp())
        config_path = tmp / "app_config.json"
        products_dir = tmp / "products"
        products_dir.mkdir()

        config_path.write_text(json.dumps({
            "sheet_protection_password": "geheim",
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
        self.assertEqual(app_config.sheet_protection_password, "geheim")
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
        self.assertEqual(app_config.sheet_protection_password, "hexhex")
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

    def test_live_templates_parse_and_empty_product_set_loads(self):
        # Ausgeliefert wird mit kanonischen Templates und (noch) ohne Produkte —
        # der Admin baut die Produkt-Configs später. Der Loader muss das ohne
        # Fehler verkraften und alle Live-Templates müssen parsen.
        from src.config.process_config import load_process_templates
        data_dir = Path(__file__).resolve().parent.parent / "data"
        config_path = data_dir / "app_config.json"
        products_dir = data_dir / "products"
        templates_dir = data_dir / "process_templates"

        templates = load_process_templates(templates_dir)
        self.assertIn("Vorschneiden", templates)
        for tpl in templates.values():
            self.assertTrue(tpl.fields, f"Template {tpl.template} hat keine Felder")

        app_config = load_app_config(config_path, products_dir, templates_dir)
        # Kein Crash; Produktanzahl ist datenstandsabhängig (>= 0).
        self.assertGreaterEqual(len(app_config.products), 0)


class TestIsMultiNutzen(unittest.TestCase):
    """Multi-Nutzen aktiviert, sobald row_group_size + etwas Wiederholbares."""

    def _proc(self, row_group_size, fields):
        from src.config.process_config import ProcessConfig
        return ProcessConfig(
            template_id="P", display_name="P",
            fields=fields, row_group_size=row_group_size,
        )

    def _f(self, fid, role="measurement", group_shared=False):
        return FieldDef(id=fid, display_name=fid, type="number",
                        role=role, group_shared=group_shared)

    def test_no_row_group_size_never_multi(self):
        from src.config.process_config import is_multi_nutzen
        p = self._proc(None, [self._f("breite")])
        self.assertFalse(is_multi_nutzen(p))

    def test_per_nutzen_measurement_activates(self):
        # Vorschneiden-Fall: einziges Messfeld 'breite' je Bahn, kein group_shared
        from src.config.process_config import is_multi_nutzen
        p = self._proc(3, [self._f("breite"), self._f("bemerkungen", "measurement")])
        self.assertTrue(is_multi_nutzen(p))

    def test_group_shared_still_activates(self):
        from src.config.process_config import is_multi_nutzen
        p = self._proc(3, [self._f("spalt", group_shared=True)])
        self.assertTrue(is_multi_nutzen(p))

    def test_row_group_size_without_measurement_not_multi(self):
        # row_group_size, aber nur Kontext/Auto -> nichts zu wiederholen
        from src.config.process_config import is_multi_nutzen
        p = self._proc(3, [self._f("fa_nr", "context"), self._f("datum", "auto")])
        self.assertFalse(is_multi_nutzen(p))


class TestJsonErrorContext(unittest.TestCase):
    """Kaputte Config-Dateien müssen beim Laden die Datei beim Namen nennen —
    sonst ist ein Tippfehler in einer von vielen Produkt-JSONs unauffindbar."""

    def setUp(self):
        import tempfile
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_malformed_product_json_names_file(self):
        bad = self.tmp_dir / "REFKAPUTT.json"
        bad.write_text('{"product_id": "X", kaputt', encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            load_product_config(bad)
        self.assertIn("REFKAPUTT.json", str(ctx.exception))

    def test_missing_required_key_names_file(self):
        bad = self.tmp_dir / "REFOHNEID.json"
        bad.write_text(json.dumps({"display_name": "X", "processes": []}),
                       encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            load_product_config(bad)
        self.assertIn("REFOHNEID.json", str(ctx.exception))

    def test_malformed_template_json_names_file(self):
        from src.config.process_config import load_process_templates
        tpl_dir = self.tmp_dir / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "Kaputt.json").write_text("{nicht json", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            load_process_templates(tpl_dir)
        self.assertIn("Kaputt.json", str(ctx.exception))

    def test_template_without_name_key_names_file(self):
        from src.config.process_config import load_process_templates
        tpl_dir = self.tmp_dir / "templates"
        tpl_dir.mkdir()
        (tpl_dir / "OhneName.json").write_text(
            json.dumps({"fields": []}), encoding="utf-8"
        )
        with self.assertRaises(ValueError) as ctx:
            load_process_templates(tpl_dir)
        self.assertIn("OhneName.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
