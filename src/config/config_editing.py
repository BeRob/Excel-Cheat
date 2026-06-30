"""Reine (Tk-freie) Logik für den Config-Editor.

Hier liegt alles, was der Admin-Editor an Entscheidungen trifft, ohne dass
Tkinter beteiligt ist — dadurch unit-testbar (tests/test_config_editing.py).
Das UI (src/ui/config_editor_view.py) ist nur eine dünne Hülle darüber und baut
nie selbst die dünne Form (active_fields/field_overrides); es reicht immer die
volle ``fields``-Liste an config_writer, der gegen das Template zurückrechnet.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from src.config.process_config import (
    FieldDef,
    ProcessConfig,
    ProcessTemplate,
    ProductConfig,
)


def _copy_field(f: FieldDef) -> FieldDef:
    """Tiefe genug Kopie einer FieldDef (eigene options-Liste), damit Editor-
    Mutationen nie auf das frisch geladene Template-Objekt zurückschlagen."""
    return replace(f, options=list(f.options) if f.options is not None else None)


def default_active_ids(tpl: ProcessTemplate) -> list[str]:
    """Standardmäßig angehakte Feld-ids für ein frisch gewähltes Template.

    Entscheidung 2 (Interview): nur Pflicht-Standard — die vier Kopf-Felder
    (info_header-Kontext: FA-Nr., LOT, Verwendbarkeitsdatum, Messmittel), alle
    Auto-Felder (Datum/Bearbeiter/Nutzen) und Bemerkungen. Messwerte und
    optionale Kontextfelder (ASK, Flächengewicht, Rollencharge, Lfd. Nr., ...)
    startet der Admin bewusst selbst. Reihenfolge = Template-Reihenfolge."""
    result: list[str] = []
    for f in tpl.fields:
        if (
            (f.role == "context" and f.info_header)
            or f.role == "identifier"
            or f.role == "auto"
            or f.id == "bemerkungen"
        ):
            result.append(f.id)
    return result


def is_legacy_raw(raw_process: dict) -> bool:
    """True, wenn ein roher Prozess-Dict NICHT dünn ist (kein ``template`` +
    ``active_fields``) — also eine alte Voll-Feld-Config. Dasselbe Signal, das
    auch ``_resolve_process`` benutzt, um dünn von Legacy zu unterscheiden."""
    return not (raw_process.get("template") and "active_fields" in raw_process)


def is_legacy_product(path: str | Path) -> bool:
    """True, wenn irgendein Prozess in der Produkt-JSON Legacy (Voll-Feld) ist.

    Liest die rohe Datei (kein Template-Auflösen) — JSON-Fehler propagieren an
    den Aufrufer, der den Load ohnehin in try/except kapselt."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    processes = data.get("processes", [])
    return any(is_legacy_raw(p) for p in processes)


def seed_process_from_template(
    tpl: ProcessTemplate,
    template_id: str,
    display_name: str,
    row_group_size: int | None = None,
) -> ProcessConfig:
    """Erzeugt einen neuen Prozess mit den Default-aktiven Feldern des Templates
    (frische Kopien, in Template-Reihenfolge). Ergebnis ist eine volle
    ProcessConfig, die der Writer wieder dünn zurückrechnet."""
    active = set(default_active_ids(tpl))
    fields = [_copy_field(f) for f in tpl.fields if f.id in active]
    return ProcessConfig(
        template_id=template_id,
        display_name=display_name,
        fields=fields,
        row_group_size=row_group_size,
        template=tpl.template,
        template_revision=tpl.template_revision,
    )


def apply_template_change(
    process: ProcessConfig,
    old_tpl: ProcessTemplate | None,
    new_tpl: ProcessTemplate,
) -> tuple[list[str], list[str]]:
    """Wechselt das Operation-Template eines bestehenden Prozesses (in-place).

    - Aktive Felder, die es im neuen Template gibt, bleiben (inkl. ihrer
      bisherigen Override-Werte).
    - Extra-Felder (produktunik, nicht im alten Template) bleiben immer.
    - Aktive Felder des ALTEN Templates ohne Entsprechung im neuen Template
      werden entfernt.
    - Neue Standard-Felder des neuen Templates werden ergänzt (vorgehakt).

    Liefert ``(behalten_ids, entfernt_ids)`` — entfernt_ids für den
    Bestätigungsdialog im UI. Ohne ``old_tpl`` werden nicht-passende Felder
    vorsichtshalber als Extra behandelt (kein Datenverlust)."""
    new_map = new_tpl.field_map()
    new_ids = set(new_map)
    old_ids = set(old_tpl.field_map()) if old_tpl else set()

    kept: list[FieldDef] = []
    kept_ids: list[str] = []
    dropped_ids: list[str] = []
    for f in process.fields:
        if f.id in new_ids:
            kept.append(f)  # Template-Feld bleibt, inkl. Overrides
            kept_ids.append(f.id)
        elif f.id not in old_ids:
            kept.append(f)  # Extra-Feld (produktunik) bleibt immer
            kept_ids.append(f.id)
        else:
            dropped_ids.append(f.id)  # war Feld des alten Templates -> weg

    present = set(kept_ids)
    for fid in default_active_ids(new_tpl):
        if fid not in present:
            kept.append(_copy_field(new_map[fid]))
            kept_ids.append(fid)
            present.add(fid)

    process.fields = kept
    process.template = new_tpl.template
    process.template_revision = new_tpl.template_revision
    return kept_ids, dropped_ids


def validate_editor_product(
    product: ProductConfig, templates: dict[str, ProcessTemplate]
) -> list[str]:
    """Editor-spezifische Prüfungen zusätzlich zu ``validate_product_config``.

    Stellt sicher, dass eine im Editor gebaute Config sauber dünn speichert und
    auflösbar bleibt: Template gewählt + vorhanden, je Prozess mindestens ein
    echter Messwert (Bemerkungen zählt nicht) und ein Bemerkungen-Feld,
    template_id über alle Prozesse eindeutig (Excel-Dateiname + Resume-Schlüssel)."""
    errors: list[str] = []

    seen_template_ids: dict[str, int] = {}
    for pi, proc in enumerate(product.processes):
        prefix = f"Prozess {pi + 1} ({proc.display_name or '?'})"

        tid = proc.template_id.strip()
        if tid:
            if tid in seen_template_ids:
                errors.append(
                    f"{prefix}: Template-ID '{tid}' ist doppelt "
                    f"(auch Prozess {seen_template_ids[tid] + 1}). Sie ist "
                    "Excel-Dateiname und Resume-Schlüssel und muss je Produkt "
                    "eindeutig sein."
                )
            else:
                seen_template_ids[tid] = pi

        if not proc.template:
            errors.append(f"{prefix}: Kein Operation-Template gewählt.")
        elif proc.template not in templates:
            errors.append(
                f"{prefix}: Template '{proc.template}' nicht gefunden — "
                "Templates-Verzeichnis prüfen."
            )

        if not any(
            f.role == "measurement" and f.id != "bemerkungen" for f in proc.fields
        ):
            errors.append(f"{prefix}: Mindestens ein Messwert-Feld nötig.")

        if not any(f.id == "bemerkungen" for f in proc.fields):
            errors.append(f"{prefix}: Feld 'Bemerkungen' fehlt (Pflicht).")

        # Clone-Felder (je Nutzen/Bahn wiederholt) brauchen eine Max-/Default-
        # Nutzenzahl, aus der der Bediener beim Start 1..Max wählt.
        if any(f.clone for f in proc.fields) and not proc.row_group_size:
            errors.append(
                f"{prefix}: Es gibt Felder mit 'clone' (je Nutzen/Bahn), aber "
                "keine Standard-/Max-Anzahl Nutzen gesetzt."
            )

    return errors
