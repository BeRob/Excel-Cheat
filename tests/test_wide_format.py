"""Tests für das Wide-Format Clone-Modell und die identifier-Rolle."""

from __future__ import annotations

import datetime
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.config.process_config import (
    FieldDef,
    ProcessConfig,
    ProcessTemplate,
    clone_column_name,
    get_all_headers,
    get_clone_fields,
    get_identifier_fields,
    get_nutzen_label,
    get_shared_input_fields,
    is_multi_nutzen,
    load_process_templates,
    read_nutzen_count_from_file,
    _parse_field,
)
from src.config.config_writer import field_to_dict, process_to_dict
from src.config.settings import HEADER_ROW
from src.excel.creator import create_measurement_file
from src.excel.reader import read_all_data
from src.excel.writer import write_measurement_rows


def _f(fid, dn, typ="number", role="measurement", clone=False, info_header=False):
    return FieldDef(id=fid, display_name=dn, type=typ, role=role,
                    clone=clone, info_header=info_header)


def _schneiden_like():
    fields = [
        _f("fa_nr", "FA-Nr.", "text", "context", info_header=True),
        _f("rollencharge", "Rollencharge", "text", "context"),
        _f("rollen_nr", "Rollen Nr.", "text", "identifier"),
        _f("rollenlaenge", "Rollenlänge", "number", "measurement"),
        _f("nutzen", "Bahn", "number", "auto"),
        _f("breite", "Breite", "number", "measurement", clone=True),
        _f("bemerkungen", "Bemerkungen", "text", "measurement", clone=True),
        _f("datum", "Datum", "text", "auto"),
        _f("bearbeiter", "Bearbeiter", "text", "auto"),
    ]
    return ProcessConfig("IPC1_Schneiden", "Schneiden", fields, row_group_size=3)


class TestCloneModel(unittest.TestCase):
    def test_clone_flag_parsed(self):
        fd = _parse_field({"id": "breite", "display_name": "Breite",
                           "type": "number", "role": "measurement", "clone": True})
        self.assertTrue(fd.clone)

    def test_legacy_group_shared_maps_to_clone(self):
        # group_shared=true bedeutete „über alle Nutzen geteilt" -> clone=false
        shared = _parse_field({"id": "spalt", "display_name": "Spalt",
                               "type": "number", "role": "measurement",
                               "group_shared": True})
        self.assertFalse(shared.clone)
        # group_shared=false (oder fehlend, aber explizit) -> per Nutzen -> clone=true
        per_nutzen = _parse_field({"id": "breite", "display_name": "Breite",
                                   "type": "number", "role": "measurement",
                                   "group_shared": False})
        self.assertTrue(per_nutzen.clone)

    def test_clone_default_false(self):
        fd = _parse_field({"id": "x", "display_name": "X", "type": "number",
                           "role": "measurement"})
        self.assertFalse(fd.clone)

    def test_is_multi_nutzen_from_clone(self):
        self.assertTrue(is_multi_nutzen(_schneiden_like()))

    def test_helpers_split(self):
        p = _schneiden_like()
        self.assertEqual([f.id for f in get_clone_fields(p)], ["breite", "bemerkungen"])
        self.assertEqual([f.id for f in get_identifier_fields(p)], ["rollen_nr"])
        self.assertEqual(
            [f.id for f in get_shared_input_fields(p)],
            ["rollencharge", "rollen_nr", "rollenlaenge"],
        )


class TestWideHeaders(unittest.TestCase):
    def test_clone_columns_expanded(self):
        p = _schneiden_like()
        headers = get_all_headers(p, nutzen_count=2)
        self.assertIn("Breite Bahn 1", headers)
        self.assertIn("Breite Bahn 2", headers)
        self.assertIn("Bemerkungen Bahn 1", headers)
        self.assertIn("Bemerkungen Bahn 2", headers)

    def test_info_header_excluded(self):
        self.assertNotIn("FA-Nr.", get_all_headers(_schneiden_like(), 2))

    def test_nutzen_auto_field_dropped(self):
        # Im Wide-Format steckt die Nutzen-Nr. im Spaltennamen, keine 'Bahn'-Spalte.
        self.assertNotIn("Bahn", get_all_headers(_schneiden_like(), 2))

    def test_nutzen_label(self):
        self.assertEqual(get_nutzen_label(_schneiden_like()), "Bahn")

    def test_clone_column_name(self):
        self.assertEqual(clone_column_name("Breite", "Bahn", 2), "Breite Bahn 2")

    def test_shared_fields_single_column(self):
        headers = get_all_headers(_schneiden_like(), 3)
        self.assertEqual(headers.count("Rollenlänge"), 1)
        self.assertEqual(headers.count("Rollen Nr."), 1)


class TestWideWriteResume(unittest.TestCase):
    def test_write_and_resume_count(self):
        p = _schneiden_like()
        d = Path(tempfile.mkdtemp())
        N = 2
        fp = create_measurement_file(
            p, "REFX", d, "LOT1", "FA1", "1",
            datetime.date(2026, 6, 30), nutzen_count=N,
        )
        label = get_nutzen_label(p)
        row = {"FA-Nr.": "FA1", "Rollencharge": "C1", "Rollen Nr.": "R1",
               "Rollenlänge": 100.0, "Datum": "2026-06-30 10:00:00",
               "Bearbeiter": "Tester"}
        nutzen_vals = [{"Breite": 71.0, "Bemerkungen": "ok"},
                       {"Breite": 72.5, "Bemerkungen": "n/a"}]
        for i, pv in enumerate(nutzen_vals, 1):
            for cf in get_clone_fields(p):
                row[clone_column_name(cf.display_name, label, i)] = pv[cf.display_name]

        res = write_measurement_rows(fp, [row], p, nutzen_count=N)
        self.assertTrue(res.success, res.error)

        # Eine Zeile je Messung (Wide-Format), nicht N Zeilen.
        data = read_all_data(fp, header_row=HEADER_ROW)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["Breite Bahn 1"], 71)
        self.assertEqual(data[0]["Breite Bahn 2"], 72.5)
        self.assertEqual(data[0]["Bemerkungen Bahn 1"], "ok")

        # Resume liest die Nutzen-Anzahl aus den Spaltenköpfen zurück.
        self.assertEqual(read_nutzen_count_from_file(fp, p), N)

    def test_wrong_nutzen_count_aborts_write(self):
        # Datei mit N=2 erzeugt; Schreiben mit N=3 -> Spalte 'Breite Bahn 3' fehlt -> Abbruch.
        p = _schneiden_like()
        d = Path(tempfile.mkdtemp())
        fp = create_measurement_file(
            p, "REFX", d, "LOT1", "FA1", "1",
            datetime.date(2026, 6, 30), nutzen_count=2,
        )
        row = {"Rollencharge": "C1", "Rollen Nr.": "R1", "Rollenlänge": 1.0,
               "Breite Bahn 1": 1, "Breite Bahn 2": 2, "Breite Bahn 3": 3,
               "Bemerkungen Bahn 1": "a", "Bemerkungen Bahn 2": "b",
               "Bemerkungen Bahn 3": "c", "Datum": "x", "Bearbeiter": "y"}
        res = write_measurement_rows(fp, [row], p, nutzen_count=3)
        self.assertFalse(res.success)


class TestCloneRoundtrip(unittest.TestCase):
    def test_field_to_dict_clone(self):
        fd = _f("breite", "Breite", clone=True)
        self.assertTrue(field_to_dict(fd)["clone"])

    def test_field_to_dict_no_clone_omitted(self):
        fd = _f("spalt", "Spalt", clone=False)
        self.assertNotIn("clone", field_to_dict(fd))

    def test_thin_clone_override_roundtrip(self):
        tpl = ProcessTemplate(
            template="Schneiden", template_revision=3,
            fields=[
                _f("breite", "Breite", clone=True),
                _f("bemerkungen", "Bemerkungen", "text", "measurement", clone=True),
            ],
        )
        # Produkt überschreibt clone auf False für 'breite'
        proc = ProcessConfig(
            "IPC1_Schneiden", "Schneiden",
            [replace(tpl.fields[0], clone=False), replace(tpl.fields[1])],
            template="Schneiden", template_revision=3,
        )
        d = process_to_dict(proc, {"Schneiden": tpl})
        self.assertIn("field_overrides", d)
        self.assertEqual(d["field_overrides"]["breite"], {"clone": False})


if __name__ == "__main__":
    unittest.main()
