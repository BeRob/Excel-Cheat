"""Acid-Roundtrip-Tests über das Editor-Editiermodell.

Stellt sicher, dass eine im Editor (über die volle ``fields``-Liste) gebaute
oder geänderte Config wieder DÜNN auf Platte landet und beim Laden identisch
auflöst — die GMP-kritische Garantie, dass Resume/Spaltenmapping/Excel
unverändert bleiben. Läuft gegen die echten Templates in data/process_templates.
"""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.config.config_editing import seed_process_from_template
from src.config.config_writer import save_product_config
from src.config.process_config import (
    FieldDef,
    ProductConfig,
    load_process_templates,
    load_product_config,
)
from src.config.settings import PROCESS_TEMPLATES_DIR


class TestEditorRoundtrip(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.templates = load_process_templates(PROCESS_TEMPLATES_DIR)
        if "Walzen" not in cls.templates:
            raise unittest.SkipTest("Walzen-Template nicht gefunden")

    def _save_reload(self, product: ProductConfig) -> tuple[Path, ProductConfig]:
        tmpdir = Path(tempfile.mkdtemp())
        path = save_product_config(product, tmpdir, self.templates)
        reloaded = load_product_config(path, self.templates)
        return path, reloaded

    def test_seed_plus_measurement_plus_extra_stays_thin_and_resolves(self):
        walzen = self.templates["Walzen"]
        proc = seed_process_from_template(walzen, "IPC3_Walzen", "IPC3 Walzen")

        # Messwert aus dem Template mit Inline-Spec-Override anhaken.
        sd = replace(
            walzen.field_map()["schichtdicke"],
            spec_min=0.7, spec_max=0.75, spec_target=0.725,
        )
        proc.fields.insert(len(proc.fields) - 3, sd)  # vor bemerkungen/datum/bearbeiter

        # Produktunikes Extra-Feld (nicht im Template) hinzufügen.
        proc.fields.insert(
            len(proc.fields) - 3,
            FieldDef("sondermass", "Sondermaß", "number", "measurement",
                     spec_min=1.0, spec_max=2.0),
        )

        product = ProductConfig("REF_TEST_RT", "Roundtrip", [proc])
        path, reloaded = self._save_reload(product)

        # 1) Auf Platte DÜNN: keine volle fields-Liste, aber active_fields +
        #    field_overrides (für schichtdicke) + extra_fields (für sondermass).
        raw = json.loads(path.read_text(encoding="utf-8"))
        praw = raw["processes"][0]
        self.assertNotIn("fields", praw)
        self.assertIn("active_fields", praw)
        self.assertIn("schichtdicke", praw.get("field_overrides", {}))
        self.assertTrue(
            any(f["id"] == "sondermass" for f in praw.get("extra_fields", []))
        )

        # 2) Reload löst identisch auf (ids, Reihenfolge, Attribute, Specs).
        self.assertEqual(reloaded.processes[0].fields, product.processes[0].fields)
        self.assertEqual(reloaded.processes[0].template_id, "IPC3_Walzen")

    def test_override_survives_toggle_off_then_on(self):
        """Decision 4: abgewähltes Feld wird gemerkt (Stash) und beim erneuten
        Anhaken samt Override wiederhergestellt. Auf Datenebene heißt das:
        dieselbe FieldDef wieder einsetzen erhält den Override über save/reload."""
        walzen = self.templates["Walzen"]
        proc = seed_process_from_template(walzen, "IPC3_Walzen", "IPC3 Walzen")
        sd = replace(walzen.field_map()["schichtdicke"], spec_min=0.7, spec_max=0.75)
        proc.fields.insert(len(proc.fields) - 3, sd)

        # Abwählen = entfernen + in Stash legen.
        stash = {}
        stash["schichtdicke"] = proc.fields.pop(len(proc.fields) - 4)
        self.assertNotIn("schichtdicke", [f.id for f in proc.fields])

        # Wieder anhaken = aus Stash zurück.
        proc.fields.insert(len(proc.fields) - 3, stash["schichtdicke"])

        product = ProductConfig("REF_TEST_RT2", "Roundtrip2", [proc])
        _, reloaded = self._save_reload(product)
        restored = next(
            f for f in reloaded.processes[0].fields if f.id == "schichtdicke"
        )
        self.assertEqual(restored.spec_min, 0.7)
        self.assertEqual(restored.spec_max, 0.75)


if __name__ == "__main__":
    unittest.main()
