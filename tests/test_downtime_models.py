"""Tests für Fehler-Code-Liste und Stoerung-Datenmodell."""

import json
import tempfile
import unittest
from pathlib import Path

from src.downtime.downtime_models import (
    DEFAULT_KATEGORIEN, Stoerung, load_stoerungs_codes, parse_iso,
)


class TestLoadCodes(unittest.TestCase):
    def test_valid_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "codes.json"
            p.write_text(json.dumps({
                "kategorien": [
                    {"name": "Mechanik", "ursachen": ["Lager", "Bruch"]},
                    {"name": "Elektrik", "ursachen": ["Sensor"]},
                ]
            }), encoding="utf-8")
            codes = load_stoerungs_codes(p)
            self.assertEqual(codes.kategorie_namen(), ["Mechanik", "Elektrik"])
            self.assertEqual(codes.ursachen("Mechanik"), ["Lager", "Bruch"])
            self.assertEqual(codes.ursachen("Unbekannt"), [])

    def test_missing_file_falls_back_to_default(self):
        codes = load_stoerungs_codes(Path("does_not_exist_xyz.json"))
        self.assertEqual(
            codes.kategorie_namen(),
            [k["name"] for k in DEFAULT_KATEGORIEN],
        )

    def test_malformed_file_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "codes.json"
            p.write_text("{ this is not json", encoding="utf-8")
            codes = load_stoerungs_codes(p)
            self.assertTrue(codes.kategorie_namen())  # Default greift

    def test_empty_kategorien_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "codes.json"
            p.write_text(json.dumps({"kategorien": []}), encoding="utf-8")
            codes = load_stoerungs_codes(p)
            self.assertTrue(codes.kategorie_namen())


class TestStoerungModel(unittest.TestCase):
    def test_parse_iso(self):
        self.assertIsNone(parse_iso(""))
        self.assertIsNone(parse_iso("kaputt"))
        self.assertIsNotNone(parse_iso("2026-06-01T08:00:00+02:00"))

    def test_offen_und_status(self):
        s = Stoerung(id="x", ts_start="2026-06-01T08:00:00+02:00")
        self.assertTrue(s.offen)
        self.assertEqual(s.status, "offen")
        s.ts_ende = "2026-06-01T09:00:00+02:00"
        self.assertFalse(s.offen)
        self.assertEqual(s.status, "behoben")

    def test_computed_dauer_from_timestamps(self):
        s = Stoerung(
            id="x",
            ts_start="2026-06-01T08:00:00+02:00",
            ts_ende="2026-06-01T08:30:00+02:00",
        )
        self.assertEqual(s.computed_dauer_sekunden(), 1800.0)

    def test_computed_dauer_prefers_stored(self):
        s = Stoerung(
            id="x", ts_start="2026-06-01T08:00:00+02:00",
            ts_ende="2026-06-01T09:00:00+02:00", dauer_sekunden=42.0,
        )
        self.assertEqual(s.computed_dauer_sekunden(), 42.0)

    def test_computed_dauer_open_is_none(self):
        s = Stoerung(id="x", ts_start="2026-06-01T08:00:00+02:00")
        self.assertIsNone(s.computed_dauer_sekunden())


if __name__ == "__main__":
    unittest.main()
