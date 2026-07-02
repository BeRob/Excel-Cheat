"""Tests für Paarung, Filter, Aggregation und KPIs der Störungsauswertung."""

import unittest
from datetime import date

from src.downtime.downtime_query import (
    aggregate_by_kategorie, aggregate_by_station, anzahl_ausfaelle,
    filter_stoerungen, find_open, gesamt_stoerzeit, mtbf, mttr,
    pair_stoerungen, verfuegbarkeit,
)


def _start(sid, ts, **kw):
    return {"kind": "stoerung_start", "id": sid, "ts_start": ts, **kw}


def _ende(sid, ts, dauer, **kw):
    return {"kind": "stoerung_ende", "id": sid, "ts_ende": ts,
            "dauer_sekunden": dauer, **kw}


class TestPairing(unittest.TestCase):
    def test_pair_start_and_ende(self):
        recs = [
            _start("1", "2026-06-01T08:00:00+02:00", kategorie="Mechanik"),
            _ende("1", "2026-06-01T08:10:00+02:00", 600.0, techniker_name="Max"),
        ]
        st = pair_stoerungen(recs)
        self.assertEqual(len(st), 1)
        self.assertFalse(st[0].offen)
        self.assertEqual(st[0].kategorie, "Mechanik")
        self.assertEqual(st[0].techniker_name, "Max")
        self.assertEqual(st[0].dauer_sekunden, 600.0)

    def test_ende_without_start_ignored(self):
        st = pair_stoerungen([_ende("99", "2026-06-01T08:10:00+02:00", 600.0)])
        self.assertEqual(st, [])

    def test_duplicate_start_ignored(self):
        recs = [
            _start("1", "2026-06-01T08:00:00+02:00"),
            _start("1", "2026-06-01T09:00:00+02:00"),
        ]
        st = pair_stoerungen(recs)
        self.assertEqual(len(st), 1)
        self.assertEqual(st[0].ts_start, "2026-06-01T08:00:00+02:00")


class TestFindOpen(unittest.TestCase):
    def _data(self):
        return pair_stoerungen([
            _start("1", "2026-06-01T08:00:00+02:00",
                   produkt_id="A", prozess_template_id="P1", maschine="1"),
            _start("2", "2026-06-01T09:00:00+02:00",
                   produkt_id="A", prozess_template_id="P1", maschine="2"),
        ])

    def test_find_open_by_context(self):
        s = find_open(self._data(), produkt_id="A", prozess_template_id="P1")
        self.assertIsNotNone(s)

    def test_find_open_filters_machine(self):
        s = find_open(self._data(), produkt_id="A", prozess_template_id="P1", maschine="2")
        self.assertEqual(s.id, "2")

    def test_no_open_for_other_product(self):
        s = find_open(self._data(), produkt_id="B", prozess_template_id="P1")
        self.assertIsNone(s)

    def test_closed_not_returned(self):
        data = pair_stoerungen([
            _start("1", "2026-06-01T08:00:00+02:00", produkt_id="A", prozess_template_id="P1"),
            _ende("1", "2026-06-01T08:10:00+02:00", 600.0),
        ])
        self.assertIsNone(find_open(data, produkt_id="A", prozess_template_id="P1"))


class TestFilter(unittest.TestCase):
    def _data(self):
        return pair_stoerungen([
            _start("1", "2026-06-01T08:00:00+02:00", produkt_id="A",
                   station="12", kategorie="Mechanik"),
            _ende("1", "2026-06-01T08:10:00+02:00", 600.0),
            _start("2", "2026-06-15T08:00:00+02:00", produkt_id="B",
                   station="7", kategorie="Elektrik"),
        ])

    def test_filter_by_daterange(self):
        out = filter_stoerungen(self._data(), von=date(2026, 6, 10), bis=date(2026, 6, 20))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, "2")

    def test_filter_by_station(self):
        out = filter_stoerungen(self._data(), station="12")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, "1")

    def test_filter_by_status(self):
        out = filter_stoerungen(self._data(), status="offen")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, "2")

    def test_filter_by_kategorie(self):
        out = filter_stoerungen(self._data(), kategorie="Mechanik")
        self.assertEqual([s.id for s in out], ["1"])


class TestAggregationAndKPIs(unittest.TestCase):
    def _data(self):
        return pair_stoerungen([
            _start("1", "2026-06-01T08:00:00+02:00", station="12", kategorie="Mechanik"),
            _ende("1", "2026-06-01T08:10:00+02:00", 600.0),
            _start("2", "2026-06-02T08:00:00+02:00", station="12", kategorie="Elektrik"),
            _ende("2", "2026-06-02T08:20:00+02:00", 1200.0),
            _start("3", "2026-06-03T08:00:00+02:00", station="7", kategorie="Mechanik"),
        ])

    def test_aggregate_by_station(self):
        agg = aggregate_by_station(self._data())
        self.assertEqual(agg["12"]["anzahl"], 2)
        self.assertEqual(agg["12"]["dauer_sum"], 1800.0)
        self.assertEqual(agg["12"]["dauer_avg"], 900.0)
        self.assertEqual(agg["7"]["anzahl"], 1)
        self.assertEqual(agg["7"]["offen"], 1)

    def test_aggregate_by_kategorie(self):
        agg = aggregate_by_kategorie(self._data())
        self.assertEqual(agg["Mechanik"]["anzahl"], 2)
        self.assertEqual(agg["Mechanik"]["offen"], 1)

    def test_gesamt_stoerzeit_and_ausfaelle(self):
        data = self._data()
        self.assertEqual(gesamt_stoerzeit(data), 1800.0)
        self.assertEqual(anzahl_ausfaelle(data), 2)

    def test_mttr(self):
        self.assertEqual(mttr(self._data()), 900.0)

    def test_mttr_none_without_closed(self):
        data = pair_stoerungen([_start("1", "2026-06-01T08:00:00+02:00")])
        self.assertIsNone(mttr(data))

    def test_mtbf(self):
        # Planzeit 10000 s, Störzeit 1800 s → Betriebszeit 8200 s, 2 Ausfälle → 4100 s
        self.assertEqual(mtbf(self._data(), 10000.0), 4100.0)

    def test_mtbf_none_without_failures(self):
        data = pair_stoerungen([_start("1", "2026-06-01T08:00:00+02:00")])
        self.assertIsNone(mtbf(data, 10000.0))

    def test_verfuegbarkeit(self):
        v = verfuegbarkeit(self._data(), 10000.0)
        self.assertAlmostEqual(v, 0.82, places=4)

    def test_verfuegbarkeit_none_without_planzeit(self):
        self.assertIsNone(verfuegbarkeit(self._data(), 0.0))

    def test_verfuegbarkeit_clamped(self):
        # Störzeit > Planzeit → 0, nie negativ
        self.assertEqual(verfuegbarkeit(self._data(), 1000.0), 0.0)


if __name__ == "__main__":
    unittest.main()
