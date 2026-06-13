"""Tests für die Vier-Augen-Freigabe von Produkt-Configs (Hash-Manifest)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.config.freigabe import (
    FREIGEGEBEN,
    GEAENDERT,
    NICHT_FREIGEGEBEN,
    compute_config_hash,
    determine_status,
    freigaben_path,
    load_freigaben,
    record_freigabe,
    save_freigaben,
)
from src.config.process_config import load_app_config


_PRODUCT_JSON = {
    "product_id": "REFTEST",
    "display_name": "Testprodukt",
    "revision": 2,
    "processes": [{
        "template_id": "IPC1_Test",
        "display_name": "IPC1",
        "fields": [
            {"id": "fa_nr", "display_name": "FA-Nr.", "type": "text",
             "role": "context"},
        ],
    }],
}


class FreigabeTestBase(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.products_dir = self.tmp_dir / "products"
        self.products_dir.mkdir()
        self.config_path = self.products_dir / "REFTEST.json"
        self.config_path.write_text(
            json.dumps(_PRODUCT_JSON, ensure_ascii=False), encoding="utf-8"
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


class TestManifest(FreigabeTestBase):

    def test_missing_manifest_is_empty(self):
        self.assertEqual(load_freigaben(self.products_dir), {})

    def test_roundtrip(self):
        data = {"REFTEST": {"revision": 2, "sha256": "abc"}}
        save_freigaben(self.products_dir, data)
        self.assertEqual(load_freigaben(self.products_dir), data)

    def test_malformed_manifest_is_empty_failsafe(self):
        freigaben_path(self.products_dir).write_text("{kaputt", encoding="utf-8")
        self.assertEqual(load_freigaben(self.products_dir), {})


class TestDetermineStatus(FreigabeTestBase):

    def test_no_entry(self):
        sha = compute_config_hash(self.config_path)
        self.assertEqual(determine_status(None, sha, 2), NICHT_FREIGEGEBEN)

    def test_valid_entry(self):
        sha = compute_config_hash(self.config_path)
        entry = {"revision": 2, "sha256": sha}
        self.assertEqual(determine_status(entry, sha, 2), FREIGEGEBEN)

    def test_changed_file_breaks_freigabe(self):
        sha = compute_config_hash(self.config_path)
        entry = {"revision": 2, "sha256": sha}
        # Datei nachträglich ändern → Hash bricht → Freigabe erlischt
        changed = dict(_PRODUCT_JSON)
        changed["display_name"] = "Manipuliert"
        self.config_path.write_text(
            json.dumps(changed, ensure_ascii=False), encoding="utf-8"
        )
        new_sha = compute_config_hash(self.config_path)
        self.assertEqual(determine_status(entry, new_sha, 2), GEAENDERT)

    def test_revision_mismatch_breaks_freigabe(self):
        sha = compute_config_hash(self.config_path)
        entry = {"revision": 1, "sha256": sha}
        self.assertEqual(determine_status(entry, sha, 2), GEAENDERT)


class TestRecordFreigabe(FreigabeTestBase):

    def test_record_writes_manifest_entry(self):
        entry = record_freigabe(
            self.products_dir, "REFTEST", self.config_path, 2,
            dokument="FB-TEST-002", geprueft_von="Anna Muster",
            freigegeben_von="Bob Beispiel", erfasst_von="admin",
        )
        stored = load_freigaben(self.products_dir)["REFTEST"]
        self.assertEqual(stored, entry)
        self.assertEqual(stored["revision"], 2)
        self.assertEqual(stored["dokument"], "FB-TEST-002")
        self.assertEqual(stored["sha256"], compute_config_hash(self.config_path))
        self.assertEqual(stored["erfasst_von"], "admin")
        self.assertIn("datum", stored)


class TestLoadAppConfigFreigabe(FreigabeTestBase):

    def _load(self):
        return load_app_config(self.tmp_dir / "app_config.json", self.products_dir)

    def test_status_annotated_nicht_freigegeben(self):
        cfg = self._load()
        self.assertEqual(len(cfg.products), 1)
        product = cfg.products[0]
        self.assertEqual(product.freigabe_status, NICHT_FREIGEGEBEN)
        self.assertEqual(
            product.config_sha256, compute_config_hash(self.config_path)
        )
        self.assertTrue(cfg.freigabe_pflicht)  # Default: streng

    def test_status_annotated_freigegeben(self):
        record_freigabe(
            self.products_dir, "REFTEST", self.config_path, 2,
            dokument="FB-TEST-002", geprueft_von="A", freigegeben_von="B",
        )
        product = self._load().products[0]
        self.assertEqual(product.freigabe_status, FREIGEGEBEN)
        self.assertEqual(product.freigabe["dokument"], "FB-TEST-002")

    def test_manifest_not_loaded_as_product(self):
        # freigaben.json liegt im Produktordner und matcht *.json —
        # darf aber nie als Produkt-Config geparst werden.
        record_freigabe(
            self.products_dir, "REFTEST", self.config_path, 2,
            dokument="FB", geprueft_von="A", freigegeben_von="B",
        )
        cfg = self._load()
        self.assertEqual([p.product_id for p in cfg.products], ["REFTEST"])

    def test_freigabe_pflicht_from_app_config(self):
        (self.tmp_dir / "app_config.json").write_text(
            json.dumps({"freigabe_pflicht": False}), encoding="utf-8"
        )
        self.assertFalse(self._load().freigabe_pflicht)


if __name__ == "__main__":
    unittest.main()
