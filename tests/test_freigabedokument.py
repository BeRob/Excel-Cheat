"""Tests für die Freigabedokument-Erzeugung (Word-Vorlage + HTML-Fallback)."""

import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.config.freigabedokument import (
    build_kontext,
    erzeuge_freigabedokument,
    render_docx,
)
from src.config.process_config import FieldDef, ProcessConfig, ProductConfig


def _make_product() -> ProductConfig:
    return ProductConfig(
        product_id="REFDOC",
        display_name="Dokument-Testprodukt",
        revision=2,
        revision_history=[
            {"revision": 2, "date": "2026-06-01", "user": "anna",
             "change": "Spec angepasst"},
        ],
        processes=[
            ProcessConfig(
                template_id="IPC1_Test",
                display_name="IPC1 Test",
                template="Vorschneiden",
                template_revision=1,
                fields=[
                    FieldDef(id="fa_nr", display_name="FA-Nr.", type="text",
                             role="context", persistent=True, info_header=True),
                    FieldDef(id="breite", display_name="Breite (mm)",
                             type="number", role="measurement",
                             spec_min=180.0, spec_max=190.0),
                ],
            ),
        ],
    )


_DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:t>Produkt: {{PRODUKT_ID}} Rev. {{REVISION}}</w:t></w:r></w:p>
<w:p><w:r><w:t>Hash: {{SHA</w:t></w:r><w:r><w:t>256}}</w:t></w:r></w:p>
<w:p><w:r><w:t>{{UNBEKANNT}}</w:t></w:r></w:p>
<w:tbl>
<w:tr><w:tc><w:p><w:r><w:t>{{FELD_ID}}</w:t></w:r></w:p></w:tc>
<w:tc><w:p><w:r><w:t>{{SPEC_MIN}}-{{SPEC_MAX}}</w:t></w:r></w:p></w:tc></w:tr>
</w:tbl>
<w:tbl>
<w:tr><w:tc><w:p><w:r><w:t>{{REV_NR}}: {{REV_AENDERUNG}}</w:t></w:r></w:p></w:tc></w:tr>
</w:tbl>
</w:body>
</w:document>"""


class FreigabedokumentTestBase(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.product = _make_product()
        self.config_path = self.tmp_dir / "REFDOC.json"
        self.config_path.write_text('{"dummy": 1}', encoding="utf-8")
        self.vorlage = self.tmp_dir / "vorlage.docx"
        with zipfile.ZipFile(self.vorlage, "w") as z:
            z.writestr("word/document.xml", _DOCUMENT_XML)
            z.writestr("word/styles.xml", "<w:styles/>")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


class TestBuildKontext(FreigabedokumentTestBase):

    def test_skalare_und_zeilen(self):
        kontext = build_kontext(self.product, self.config_path)
        s = kontext["skalare"]
        self.assertEqual(s["PRODUKT_ID"], "REFDOC")
        self.assertEqual(s["REVISION"], "2")
        self.assertEqual(s["CONFIG_DATEI"], "REFDOC.json")
        self.assertEqual(len(s["SHA256"]), 64)
        self.assertEqual(len(kontext["felder"]), 2)
        self.assertEqual(kontext["felder"][1]["SPEC_MIN"], "180.0")
        self.assertEqual(kontext["felder"][0]["FLAGS"], "persistent, info_header")
        self.assertEqual(kontext["historie"][0]["REV_AENDERUNG"], "Spec angepasst")


class TestRenderDocx(FreigabedokumentTestBase):

    def _render(self) -> tuple[str, set[str]]:
        kontext = build_kontext(self.product, self.config_path)
        out = self.tmp_dir / "out.docx"
        unresolved = render_docx(self.vorlage, out, kontext)
        with zipfile.ZipFile(out) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        return xml, unresolved

    def test_scalar_replaced(self):
        xml, _ = self._render()
        self.assertIn("Produkt: REFDOC Rev. 2", xml)

    def test_split_run_placeholder_replaced(self):
        # Word zerlegt Platzhalter gern in mehrere Runs — {{SHA / 256}} über
        # zwei <w:r> hinweg muss trotzdem ersetzt werden.
        xml, _ = self._render()
        self.assertNotIn("{{SHA", xml)
        kontext = build_kontext(self.product, self.config_path)
        self.assertIn(kontext["skalare"]["SHA256"], xml)

    def test_field_rows_cloned_per_field(self):
        xml, _ = self._render()
        self.assertIn("fa_nr", xml)
        self.assertIn("breite", xml)
        self.assertIn("180.0-190.0", xml)
        self.assertNotIn("{{FELD_ID}}", xml)

    def test_history_rows_cloned(self):
        xml, _ = self._render()
        self.assertIn("2: Spec angepasst", xml)
        self.assertNotIn("{{REV_NR}}", xml)

    def test_unknown_placeholder_reported_and_kept(self):
        xml, unresolved = self._render()
        self.assertEqual(unresolved, {"UNBEKANNT"})
        self.assertIn("{{UNBEKANNT}}", xml)

    def test_other_zip_entries_untouched(self):
        kontext = build_kontext(self.product, self.config_path)
        out = self.tmp_dir / "out.docx"
        render_docx(self.vorlage, out, kontext)
        with zipfile.ZipFile(out) as z:
            self.assertEqual(z.read("word/styles.xml"), b"<w:styles/>")


class TestErzeugeFreigabedokument(FreigabedokumentTestBase):

    def test_docx_mit_vorlage(self):
        out, unresolved = erzeuge_freigabedokument(
            self.product, self.config_path, self.tmp_dir / "out",
            vorlage=self.vorlage,
        )
        self.assertEqual(out.name, "Freigabe_REFDOC_Rev2.docx")
        self.assertTrue(out.exists())
        self.assertEqual(unresolved, {"UNBEKANNT"})

    def test_html_fallback_ohne_vorlage(self):
        out, unresolved = erzeuge_freigabedokument(
            self.product, self.config_path, self.tmp_dir / "out", vorlage=None,
        )
        self.assertEqual(out.name, "Freigabe_REFDOC_Rev2.html")
        content = out.read_text(encoding="utf-8")
        self.assertIn("REFDOC", content)
        self.assertIn("Breite (mm)", content)
        self.assertIn("Vier-Augen-Prinzip", content)
        self.assertEqual(unresolved, set())


if __name__ == "__main__":
    unittest.main()
