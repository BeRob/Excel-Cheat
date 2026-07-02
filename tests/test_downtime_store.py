"""Tests für den append-only Störungs-Store."""

import tempfile
import unittest
from pathlib import Path

from src.downtime.downtime_store import DowntimeStore
from src.downtime.downtime_query import pair_stoerungen


class TestDowntimeStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "stoerungen.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_and_read_roundtrip(self):
        store = DowntimeStore(self.path, lock_timeout=2.0)
        store.append_start({
            "id": "abc", "ts_start": "2026-06-01T08:00:00+02:00",
            "produkt_id": "REF1", "prozess_template_id": "IPC5_Stanzen",
            "kategorie": "Mechanik", "ursache": "Lager",
        })
        store.append_ende({
            "id": "abc", "ts_ende": "2026-06-01T08:30:00+02:00",
            "dauer_sekunden": 1800.0, "techniker_name": "Max", "behebung": "getauscht",
        })
        records = store.read_all()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["kind"], "stoerung_start")
        self.assertEqual(records[1]["kind"], "stoerung_ende")
        self.assertIsNone(store.degraded_reason)

    def test_read_missing_file_is_empty(self):
        store = DowntimeStore(self.path)
        self.assertEqual(store.read_all(), [])

    def test_pairing_after_store(self):
        store = DowntimeStore(self.path, lock_timeout=2.0)
        store.append_start({"id": "1", "ts_start": "2026-06-01T08:00:00+02:00"})
        store.append_ende({
            "id": "1", "ts_ende": "2026-06-01T08:10:00+02:00", "dauer_sekunden": 600.0,
        })
        store.append_start({"id": "2", "ts_start": "2026-06-01T09:00:00+02:00"})
        stoerungen = pair_stoerungen(store.read_all())
        self.assertEqual(len(stoerungen), 2)
        self.assertFalse(stoerungen[0].offen)
        self.assertTrue(stoerungen[1].offen)

    def test_invalid_line_skipped(self):
        store = DowntimeStore(self.path)
        store.append_start({"id": "1", "ts_start": "2026-06-01T08:00:00+02:00"})
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("nicht json\n")
        self.assertEqual(len(store.read_all()), 1)


if __name__ == "__main__":
    unittest.main()
