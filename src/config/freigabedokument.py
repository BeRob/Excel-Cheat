"""Freigabedokumente aus einer Word-Vorlage (oder als HTML-Fallback) erzeugen.

Die Vorlage ist eine normale .docx-Datei unter ``data/vorlagen/freigabedokument.docx``
mit Platzhaltern im Text. Sie wird einmal vom QM gestaltet und dann für jedes
Freigabedokument verwendet — das Dokument ist damit immer gleich aufgebaut.
Befüllt wird ohne Zusatzabhängigkeit (docx = ZIP mit XML; Platzhalter werden
direkt im XML ersetzt, auch wenn Word sie intern in mehrere Runs zerlegt hat).

Platzhalter (doppelte geschweifte Klammern, z.B. ``{{PRODUKT_ID}}``):

Skalare (überall im Dokument, auch Kopf-/Fußzeile):
    {{PRODUKT_ID}}      Produkt-ID (z.B. REF31962)
    {{PRODUKT_NAME}}    Anzeigename des Produkts
    {{REVISION}}        Produkt-Revision
    {{CONFIG_DATEI}}    Dateiname der Config (REF31962.json)
    {{SHA256}}          SHA-256-Hash der Config-Datei (bindet die Freigabe)
    {{DATUM}}           Erzeugungsdatum (YYYY-MM-DD)
    {{APP_VERSION}}     QAInput-Version, mit der das Dokument erzeugt wurde
    {{ANZAHL_PROZESSE}} Anzahl Prozesse
    {{PROZESSLISTE}}    Prozess-Anzeigenamen, kommagetrennt

Felder-Tabelle: EINE Tabellenzeile in der Vorlage enthält diese Platzhalter —
sie wird je Feld (über alle Prozesse) dupliziert:
    {{PROZESS}} {{PROZESS_ID}} {{TEMPLATE}} {{TEMPLATE_REV}}
    {{FELD_ID}} {{FELD_NAME}} {{FELD_TYP}} {{FELD_ROLLE}}
    {{SPEC_MIN}} {{SPEC_SOLL}} {{SPEC_MAX}} {{OPTIONEN}} {{DEFAULT}} {{FLAGS}}

Revisionshistorie-Tabelle: EINE Zeile mit diesen Platzhaltern, dupliziert je
Historieneintrag:
    {{REV_NR}} {{REV_DATUM}} {{REV_USER}} {{REV_AENDERUNG}}

Hinweis für die Vorlage: Platzhalter am Stück tippen oder einfügen (keine
Tabellen in Tabellen in den Wiederhol-Zeilen). Unbekannte Platzhalter bleiben
sichtbar stehen und werden gemeldet — Tippfehler fallen so sofort auf.
"""

from __future__ import annotations

import html
import re
import zipfile
from datetime import date
from pathlib import Path

from src.config.freigabe import compute_config_hash
from src.config.process_config import ProductConfig
from src.version import APP_VERSION


_PLACEHOLDER_RE = re.compile(r"\{\{(?:<[^>]+>|[^{}<])*?\}\}", re.S)
_ROW_RE = re.compile(r"<w:tr(?: [^>]*)?>.*?</w:tr>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")

# Marker, an denen die Wiederhol-Zeilen erkannt werden
_FELD_MARKER = "{{FELD_ID}}"
_HISTORIE_MARKER = "{{REV_NR}}"


def _spec(value) -> str:
    return "" if value is None else str(value)


def _flags(fd) -> str:
    flags = []
    if fd.persistent:
        flags.append("persistent")
    if fd.optional:
        flags.append("optional")
    if fd.info_header:
        flags.append("info_header")
    if fd.clone:
        flags.append("clone")
    if fd.machine_scoped:
        flags.append("machine_scoped")
    return ", ".join(flags)


def build_kontext(product: ProductConfig, config_path: Path) -> dict:
    """Stellt alle Platzhalter-Werte für ein Produkt zusammen.

    Liefert {"skalare": {...}, "felder": [zeilen-dicts], "historie": [...]}."""
    sha = compute_config_hash(config_path)

    skalare = {
        "PRODUKT_ID": product.product_id,
        "PRODUKT_NAME": product.display_name,
        "REVISION": str(product.revision),
        "CONFIG_DATEI": Path(config_path).name,
        "SHA256": sha,
        "DATUM": date.today().isoformat(),
        "APP_VERSION": APP_VERSION,
        "ANZAHL_PROZESSE": str(len(product.processes)),
        "PROZESSLISTE": ", ".join(p.display_name for p in product.processes),
    }

    felder: list[dict] = []
    for proc in product.processes:
        for fd in proc.fields:
            felder.append({
                "PROZESS": proc.display_name,
                "PROZESS_ID": proc.template_id,
                "TEMPLATE": proc.template or "",
                "TEMPLATE_REV": _spec(proc.template_revision),
                "FELD_ID": fd.id,
                "FELD_NAME": fd.display_name,
                "FELD_TYP": fd.type,
                "FELD_ROLLE": fd.role,
                "SPEC_MIN": _spec(fd.spec_min),
                "SPEC_SOLL": _spec(fd.spec_target),
                "SPEC_MAX": _spec(fd.spec_max),
                "OPTIONEN": ", ".join(fd.options) if fd.options else "",
                "DEFAULT": fd.default_value or "",
                "FLAGS": _flags(fd),
            })

    historie: list[dict] = []
    for h in product.revision_history:
        historie.append({
            "REV_NR": str(h.get("revision", "")),
            "REV_DATUM": str(h.get("date", "")),
            "REV_USER": str(h.get("user", "") or ""),
            "REV_AENDERUNG": str(h.get("change", "")),
        })

    return {"skalare": skalare, "felder": felder, "historie": historie}


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _replace_placeholders(xml: str, values: dict[str, str]) -> tuple[str, set[str]]:
    """Ersetzt {{KEY}}-Platzhalter, auch wenn Word sie über mehrere Runs
    verteilt hat (XML-Tags zwischen den Klammern werden mit entfernt).
    Liefert (neues XML, Menge unbekannter Platzhalter)."""
    unresolved: set[str] = set()

    def sub(match: re.Match) -> str:
        key = _TAG_RE.sub("", match.group(0)).strip("{}  ")
        if key in values:
            return _xml_escape(values[key])
        unresolved.add(key)
        return match.group(0)

    return _PLACEHOLDER_RE.sub(sub, xml), unresolved


def _expand_rows(xml: str, marker: str, rows: list[dict]) -> str:
    """Dupliziert die Tabellenzeile, die den Marker-Platzhalter enthält,
    einmal je Datenzeile (Platzhalter pro Kopie ersetzt)."""

    def expand(match: re.Match) -> str:
        row_xml = match.group(0)
        if marker not in _TAG_RE.sub("", row_xml):
            return row_xml
        copies = []
        for row in rows:
            copy, _ = _replace_placeholders(row_xml, row)
            copies.append(copy)
        return "".join(copies)

    return _ROW_RE.sub(expand, xml)


def render_docx(
    template_path: Path, out_path: Path, kontext: dict,
) -> set[str]:
    """Befüllt die Word-Vorlage und schreibt das Freigabedokument.

    Liefert die Menge nicht aufgelöster Platzhalter (leer = alles ersetzt).
    Bearbeitet werden Hauptdokument sowie Kopf-/Fußzeilen."""
    unresolved: set[str] = set()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(template_path, "r") as zin:
        items = [(info, zin.read(info.filename)) for info in zin.infolist()]

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, payload in items:
            name = info.filename
            if name == "word/document.xml" or re.fullmatch(
                r"word/(header|footer)\d*\.xml", name
            ):
                xml = payload.decode("utf-8")
                xml = _expand_rows(xml, _FELD_MARKER, kontext["felder"])
                xml = _expand_rows(xml, _HISTORIE_MARKER, kontext["historie"])
                xml, missing = _replace_placeholders(xml, kontext["skalare"])
                unresolved |= missing
                payload = xml.encode("utf-8")
            zout.writestr(name, payload)

    return unresolved


_HTML_CSS = """
body { font-family: Segoe UI, Arial, sans-serif; font-size: 11pt; margin: 2em; }
h1 { font-size: 16pt; border-bottom: 2px solid #333; padding-bottom: 4px; }
h2 { font-size: 13pt; margin-top: 1.4em; }
table { border-collapse: collapse; width: 100%; margin: 0.5em 0 1em 0; }
th, td { border: 1px solid #999; padding: 3px 7px; text-align: left; font-size: 9.5pt; }
th { background: #eee; }
.meta td { border: none; padding: 1px 8px 1px 0; font-size: 10.5pt; }
.hash { font-family: Consolas, monospace; font-size: 9pt; word-break: break-all; }
.sig { margin-top: 2.5em; width: 100%; }
.sig td { border: none; padding-top: 2.5em; width: 33%; font-size: 10pt; }
.sigline { border-top: 1px solid #333; padding-top: 3px; }
.hinweis { font-size: 9pt; color: #444; margin-top: 1.5em; }
@media print { .noprint { display: none; } }
"""


def render_html(kontext: dict) -> str:
    """HTML-Fallback mit festem Layout — falls (noch) keine Word-Vorlage da ist."""
    s = kontext["skalare"]
    e = html.escape
    parts: list[str] = [
        "<!DOCTYPE html><html lang='de'><head><meta charset='utf-8'>",
        f"<title>Freigabe {e(s['PRODUKT_ID'])} Rev. {e(s['REVISION'])}</title>",
        f"<style>{_HTML_CSS}</style></head><body>",
        f"<h1>Freigabedokument Produkt-Konfiguration — {e(s['PRODUKT_ID'])}</h1>",
        "<table class='meta'>",
        f"<tr><td>Produkt:</td><td><b>{e(s['PRODUKT_NAME'])}</b></td></tr>",
        f"<tr><td>Config-Datei:</td><td>{e(s['CONFIG_DATEI'])}</td></tr>",
        f"<tr><td>Revision:</td><td><b>{e(s['REVISION'])}</b></td></tr>",
        f"<tr><td>Erstellt am:</td><td>{e(s['DATUM'])}</td></tr>",
        f"<tr><td>SHA-256:</td><td class='hash'>{e(s['SHA256'])}</td></tr>",
        "</table>",
    ]

    if kontext["historie"]:
        parts.append("<h2>Revisionshistorie</h2><table>")
        parts.append(
            "<tr><th>Rev.</th><th>Datum</th><th>Benutzer</th><th>Änderung</th></tr>"
        )
        for h in kontext["historie"]:
            parts.append(
                f"<tr><td>{e(h['REV_NR'])}</td><td>{e(h['REV_DATUM'])}</td>"
                f"<td>{e(h['REV_USER'])}</td><td>{e(h['REV_AENDERUNG'])}</td></tr>"
            )
        parts.append("</table>")

    parts.append("<h2>Prozesse und Felder</h2><table>")
    parts.append(
        "<tr><th>Prozess</th><th>Feld-ID</th><th>Anzeigename</th><th>Typ</th>"
        "<th>Rolle</th><th>Spec min</th><th>Soll</th><th>Spec max</th>"
        "<th>Optionen</th><th>Default</th><th>Flags</th></tr>"
    )
    for f in kontext["felder"]:
        parts.append(
            f"<tr><td>{e(f['PROZESS'])}</td><td>{e(f['FELD_ID'])}</td>"
            f"<td>{e(f['FELD_NAME'])}</td><td>{e(f['FELD_TYP'])}</td>"
            f"<td>{e(f['FELD_ROLLE'])}</td><td>{e(f['SPEC_MIN'])}</td>"
            f"<td>{e(f['SPEC_SOLL'])}</td><td>{e(f['SPEC_MAX'])}</td>"
            f"<td>{e(f['OPTIONEN'])}</td><td>{e(f['DEFAULT'])}</td>"
            f"<td>{e(f['FLAGS'])}</td></tr>"
        )
    parts.append("</table>")

    parts.append(
        "<table class='sig'><tr>"
        "<td><div class='sigline'>Erstellt (Datum, Unterschrift)</div></td>"
        "<td><div class='sigline'>Geprüft (Datum, Unterschrift)</div></td>"
        "<td><div class='sigline'>Freigegeben (Datum, Unterschrift)</div></td>"
        "</tr></table>"
    )
    parts.append(
        "<p class='hinweis'>Vier-Augen-Prinzip: Prüfer und Freigeber müssen "
        "verschiedene Personen sein. Die Freigabe gilt ausschließlich für den "
        "Dateistand mit dem oben genannten SHA-256-Hash; jede Änderung der "
        "Config-Datei erfordert ein neues Freigabedokument. Nach Unterschrift "
        "die Freigabe im Config-Editor („Freigabe erfassen…“) eintragen — "
        "erst dann ist das Produkt in QAInput wählbar.</p>"
    )
    parts.append("</body></html>")
    return "".join(parts)


def erzeuge_freigabedokument(
    product: ProductConfig,
    config_path: Path,
    out_dir: Path,
    vorlage: Path | None = None,
) -> tuple[Path, set[str]]:
    """Erzeugt das Freigabedokument für ein Produkt.

    Mit Word-Vorlage → .docx (immer gleicher Aufbau laut Vorlage);
    ohne Vorlage → .html mit festem Layout. Liefert (Pfad, unaufgelöste
    Platzhalter — nur bei docx relevant)."""
    kontext = build_kontext(product, config_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"Freigabe_{product.product_id}_Rev{product.revision}"

    if vorlage is not None and Path(vorlage).exists():
        out_path = out_dir / f"{base}.docx"
        unresolved = render_docx(Path(vorlage), out_path, kontext)
        return out_path, unresolved

    out_path = out_dir / f"{base}.html"
    out_path.write_text(render_html(kontext), encoding="utf-8")
    return out_path, set()
