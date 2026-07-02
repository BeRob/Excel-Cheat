"""Tests für die Tk-freie Config-Editor-Logik (src/config/config_editing.py)."""

import json
import tempfile
import unittest
from pathlib import Path

from src.config.config_editing import (
    apply_template_change,
    default_active_ids,
    is_legacy_product,
    is_legacy_raw,
    removed_template_ids,
    seed_process_from_template,
    validate_editor_product,
)
from src.config.config_writer import _thin_process_to_dict
from src.config.process_config import (
    FieldDef,
    ProcessConfig,
    ProcessTemplate,
    ProductConfig,
    _resolve_process,
)


def _walzen_template() -> ProcessTemplate:
    """Minimal-Nachbau des Walzen-Templates (info_header-Kontext, optionaler
    Kontext, Messwerte, Bemerkungen, Auto-Felder)."""
    return ProcessTemplate(
        template="Walzen",
        template_revision=2,
        fields=[
            FieldDef("fa_nr", "FA-Nr.", "text", "context", persistent=True, info_header=True),
            FieldDef("lot_nr", "LOT Nr.", "text", "context", persistent=True, info_header=True),
            FieldDef("verwendbarkeitsdatum", "Verwendbarkeitsdatum", "date", "context", persistent=True, info_header=True),
            FieldDef("messmittel", "Messmittel", "text", "context", persistent=True, info_header=True),
            FieldDef("rollencharge", "Rollencharge", "text", "context"),
            FieldDef("ask", "ASK", "choice", "context", options=["Ja", "Nein"]),
            FieldDef("schichtdicke", "Schichtdicke", "number", "measurement"),
            FieldDef("laenge", "Länge", "number", "measurement"),
            FieldDef("bemerkungen", "Bemerkungen", "text", "measurement", optional=True, default_value="n/a"),
            FieldDef("datum", "Datum", "text", "auto"),
            FieldDef("bearbeiter", "Bearbeiter", "text", "auto"),
        ],
    )


def _vorschneiden_template() -> ProcessTemplate:
    return ProcessTemplate(
        template="Vorschneiden",
        template_revision=1,
        fields=[
            FieldDef("fa_nr", "FA-Nr.", "text", "context", persistent=True, info_header=True),
            FieldDef("lot_nr", "LOT Nr.", "text", "context", persistent=True, info_header=True),
            FieldDef("verwendbarkeitsdatum", "Verwendbarkeitsdatum", "date", "context", persistent=True, info_header=True),
            FieldDef("messmittel", "Messmittel", "text", "context", persistent=True, info_header=True),
            FieldDef("rollencharge", "Rollencharge", "text", "context"),
            FieldDef("breite", "Breite", "number", "measurement"),
            FieldDef("bemerkungen", "Bemerkungen", "text", "measurement", optional=True, default_value="n/a"),
            FieldDef("nutzen", "Nutzen", "text", "auto"),
            FieldDef("datum", "Datum", "text", "auto"),
            FieldDef("bearbeiter", "Bearbeiter", "text", "auto"),
        ],
    )


class TestDefaultActiveIds(unittest.TestCase):

    def test_includes_header_context_auto_bemerkungen(self):
        ids = default_active_ids(_walzen_template())
        self.assertEqual(
            ids,
            ["fa_nr", "lot_nr", "verwendbarkeitsdatum", "messmittel",
             "bemerkungen", "datum", "bearbeiter"],
        )

    def test_excludes_measurements_and_optional_context(self):
        ids = default_active_ids(_walzen_template())
        self.assertNotIn("schichtdicke", ids)   # Messwert -> abgewählt
        self.assertNotIn("laenge", ids)         # Messwert -> abgewählt
        self.assertNotIn("rollencharge", ids)   # optionaler Kontext -> abgewählt
        self.assertNotIn("ask", ids)            # optionaler Kontext -> abgewählt

    def test_preserves_template_order(self):
        ids = default_active_ids(_vorschneiden_template())
        self.assertEqual(
            ids,
            ["fa_nr", "lot_nr", "verwendbarkeitsdatum", "messmittel",
             "bemerkungen", "nutzen", "datum", "bearbeiter"],
        )


class TestLegacyDetection(unittest.TestCase):

    def test_is_legacy_raw_true_for_full_fields(self):
        raw = {"template_id": "X", "display_name": "X", "fields": [{"id": "a"}]}
        self.assertTrue(is_legacy_raw(raw))

    def test_is_legacy_raw_false_for_thin(self):
        raw = {"template_id": "X", "template": "Walzen", "active_fields": ["fa_nr"]}
        self.assertFalse(is_legacy_raw(raw))

    def test_is_legacy_raw_true_when_active_fields_missing(self):
        raw = {"template_id": "X", "template": "Walzen"}
        self.assertTrue(is_legacy_raw(raw))

    def _write(self, data: dict) -> Path:
        tmp = Path(tempfile.mkdtemp()) / "p.json"
        tmp.write_text(json.dumps(data), encoding="utf-8")
        return tmp

    def test_is_legacy_product_thin(self):
        path = self._write({
            "product_id": "REF1", "display_name": "Ref 1",
            "processes": [
                {"template_id": "IPC1_Walzen", "template": "Walzen",
                 "active_fields": ["fa_nr", "bemerkungen"]},
            ],
        })
        self.assertFalse(is_legacy_product(path))

    def test_is_legacy_product_full_fields(self):
        path = self._write({
            "product_id": "REF1", "display_name": "Ref 1",
            "processes": [
                {"template_id": "IPC1_Walzen",
                 "fields": [{"id": "fa_nr", "display_name": "FA", "type": "text", "role": "context"}]},
            ],
        })
        self.assertTrue(is_legacy_product(path))

    def test_is_legacy_product_mixed_is_legacy(self):
        path = self._write({
            "product_id": "REF1", "display_name": "Ref 1",
            "processes": [
                {"template_id": "IPC1_Walzen", "template": "Walzen", "active_fields": ["fa_nr"]},
                {"template_id": "IPC2_X", "fields": [{"id": "fa_nr"}]},  # Legacy
            ],
        })
        self.assertTrue(is_legacy_product(path))


class TestSeedProcess(unittest.TestCase):

    def test_seed_resolves_back_identically(self):
        tpl = _walzen_template()
        seed = seed_process_from_template(tpl, "IPC3_Walzen", "IPC3 Walzen")
        # Acid: dünn serialisieren und gegen das Template wieder auflösen -> identisch.
        thin = _thin_process_to_dict(seed, tpl)
        resolved = _resolve_process(thin, {tpl.template: tpl})
        self.assertEqual([f.id for f in resolved.fields], [f.id for f in seed.fields])
        self.assertEqual(resolved.fields, seed.fields)
        self.assertEqual(resolved.template_id, "IPC3_Walzen")

    def test_seed_has_only_standard_fields(self):
        seed = seed_process_from_template(_walzen_template(), "IPC3_Walzen", "IPC3")
        self.assertEqual(
            [f.id for f in seed.fields],
            ["fa_nr", "lot_nr", "verwendbarkeitsdatum", "messmittel",
             "bemerkungen", "datum", "bearbeiter"],
        )

    def test_seed_copies_are_independent_of_template(self):
        tpl = _walzen_template()
        seed = seed_process_from_template(tpl, "IPC3_Walzen", "IPC3")
        # Eine Override-Mutation am Seed-Feld darf das Template nicht verändern.
        from dataclasses import replace
        seed.fields[0] = replace(seed.fields[0], display_name="Geändert")
        self.assertEqual(tpl.fields[0].display_name, "FA-Nr.")


class TestApplyTemplateChange(unittest.TestCase):

    def test_drops_absent_fields_keeps_common_and_extras(self):
        walzen = _walzen_template()
        vorschneiden = _vorschneiden_template()
        proc = seed_process_from_template(walzen, "IPC3_Walzen", "IPC3 Walzen")
        # Messwert + Extra-Feld dazunehmen.
        proc.fields.insert(5, FieldDef("schichtdicke", "Schichtdicke", "number", "measurement", spec_min=0.7, spec_max=0.75))
        proc.fields.append(FieldDef("sonderfeld", "Sonderfeld", "text", "measurement"))

        kept, dropped = apply_template_change(proc, walzen, vorschneiden)

        self.assertIn("schichtdicke", dropped)   # Walzen-Feld, in Vorschneiden weg
        self.assertIn("bemerkungen", kept)        # in beiden
        self.assertIn("fa_nr", kept)              # in beiden
        self.assertIn("sonderfeld", kept)         # Extra -> bleibt immer
        active = [f.id for f in proc.fields]
        self.assertNotIn("schichtdicke", active)
        self.assertIn("sonderfeld", active)
        # Neue Standard-Felder des neuen Templates ergänzt (z.B. nutzen, auto):
        self.assertIn("nutzen", active)
        self.assertEqual(proc.template, "Vorschneiden")
        self.assertEqual(proc.template_revision, 1)


class TestValidateEditorProduct(unittest.TestCase):

    def _templates(self):
        t = _walzen_template()
        return {t.template: t}

    def _product(self, fields):
        return ProductConfig(
            product_id="REF1", display_name="Ref 1",
            processes=[ProcessConfig(
                template_id="IPC3_Walzen", display_name="IPC3 Walzen",
                fields=fields, template="Walzen", template_revision=2,
            )],
        )

    def test_ok(self):
        p = self._product([
            FieldDef("schichtdicke", "Schichtdicke", "number", "measurement"),
            FieldDef("bemerkungen", "Bemerkungen", "text", "measurement"),
        ])
        self.assertEqual(validate_editor_product(p, self._templates()), [])

    def test_requires_real_measurement(self):
        # nur bemerkungen (role=measurement) reicht NICHT.
        p = self._product([FieldDef("bemerkungen", "Bemerkungen", "text", "measurement")])
        errs = validate_editor_product(p, self._templates())
        self.assertTrue(any("Messwert" in e for e in errs))

    def test_requires_bemerkungen(self):
        p = self._product([FieldDef("schichtdicke", "Schichtdicke", "number", "measurement")])
        errs = validate_editor_product(p, self._templates())
        self.assertTrue(any("Bemerkungen" in e for e in errs))

    def test_missing_template_errors(self):
        p = self._product([
            FieldDef("schichtdicke", "Schichtdicke", "number", "measurement"),
            FieldDef("bemerkungen", "Bemerkungen", "text", "measurement"),
        ])
        p.processes[0].template = "GibtsNicht"
        errs = validate_editor_product(p, self._templates())
        self.assertTrue(any("nicht gefunden" in e for e in errs))

    def test_no_template_errors(self):
        p = self._product([
            FieldDef("schichtdicke", "Schichtdicke", "number", "measurement"),
            FieldDef("bemerkungen", "Bemerkungen", "text", "measurement"),
        ])
        p.processes[0].template = None
        errs = validate_editor_product(p, self._templates())
        self.assertTrue(any("Template" in e for e in errs))

    def test_duplicate_template_id(self):
        proc1 = ProcessConfig(
            template_id="IPC3_Walzen", display_name="A",
            fields=[
                FieldDef("schichtdicke", "Schichtdicke", "number", "measurement"),
                FieldDef("bemerkungen", "Bemerkungen", "text", "measurement"),
            ],
            template="Walzen", template_revision=2,
        )
        proc2 = ProcessConfig(
            template_id="IPC3_Walzen", display_name="B",  # gleiche template_id!
            fields=[
                FieldDef("schichtdicke", "Schichtdicke", "number", "measurement"),
                FieldDef("bemerkungen", "Bemerkungen", "text", "measurement"),
            ],
            template="Walzen", template_revision=2,
        )
        p = ProductConfig(product_id="REF1", display_name="Ref 1", processes=[proc1, proc2])
        errs = validate_editor_product(p, self._templates())
        self.assertTrue(any("doppelt" in e for e in errs))


class TestRemovedTemplateIds(unittest.TestCase):
    """Wächter für template_id-Änderungen an bereits gespeicherten Produkten
    (template_id = Excel-Dateiname + Resume-Schlüssel)."""

    def _product(self, *tids: str) -> ProductConfig:
        tpl = _walzen_template()
        return ProductConfig(
            product_id="REF1", display_name="Ref 1",
            processes=[
                seed_process_from_template(tpl, tid, f"Prozess {i}")
                for i, tid in enumerate(tids, 1)
            ],
        )

    def test_unchanged_ids_report_nothing(self):
        product = self._product("IPC1_Walzen", "IPC2_Walzen")
        self.assertEqual(
            removed_template_ids({"IPC1_Walzen", "IPC2_Walzen"}, product), []
        )

    def test_renamed_id_is_reported(self):
        product = self._product("IPC1_NEU", "IPC2_Walzen")
        self.assertEqual(
            removed_template_ids({"IPC1_Walzen", "IPC2_Walzen"}, product),
            ["IPC1_Walzen"],
        )

    def test_removed_process_is_reported(self):
        product = self._product("IPC1_Walzen")
        self.assertEqual(
            removed_template_ids({"IPC1_Walzen", "IPC2_Walzen"}, product),
            ["IPC2_Walzen"],
        )

    def test_empty_snapshot_for_new_file(self):
        # Assistent/Kopie: kein gespeicherter Stand -> Wächter feuert nie.
        product = self._product("IPC1_Walzen")
        self.assertEqual(removed_template_ids(set(), product), [])

    def test_added_processes_are_not_reported(self):
        product = self._product("IPC1_Walzen", "IPC2_Walzen")
        self.assertEqual(removed_template_ids({"IPC1_Walzen"}, product), [])

    def test_whitespace_only_differences_are_not_reported(self):
        product = self._product("IPC1_Walzen")
        self.assertEqual(removed_template_ids({" IPC1_Walzen "}, product), [])


if __name__ == "__main__":
    unittest.main()
