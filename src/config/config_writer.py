"""Serialisierung und Validierung von Produkt-JSONs."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from src.config.process_config import (
    FIELD_OVERRIDE_KEYS,
    FieldDef,
    ProcessConfig,
    ProcessTemplate,
    ProductConfig,
)


def field_to_dict(field: FieldDef) -> dict:
    d: dict = {
        "id": field.id,
        "display_name": field.display_name,
        "type": field.type,
        "role": field.role,
    }
    if field.persistent:
        d["persistent"] = True
    if field.optional:
        d["optional"] = True
    if field.spec_target is not None:
        d["spec_target"] = field.spec_target
    if field.spec_min is not None:
        d["spec_min"] = field.spec_min
    if field.spec_max is not None:
        d["spec_max"] = field.spec_max
    if field.options is not None:
        d["options"] = field.options
    if field.default_value is not None:
        d["default_value"] = field.default_value
    if field.group_shared:
        d["group_shared"] = True
    if field.info_header:
        d["info_header"] = True
    if field.machine_scoped:
        d["machine_scoped"] = True
    return d


def _field_override_diff(base: FieldDef, actual: FieldDef) -> dict:
    """Attribut-Abweichungen der aufgelösten FieldDef gegenüber dem Template-Feld.

    Liefert genau die Werte, die als ``field_overrides``-Eintrag nötig sind,
    damit die Auflösung wieder ``actual`` ergibt."""
    diff: dict = {}
    for key in sorted(FIELD_OVERRIDE_KEYS):
        if getattr(actual, key) != getattr(base, key):
            diff[key] = getattr(actual, key)
    return diff


def _thin_process_to_dict(process: ProcessConfig, tpl: ProcessTemplate) -> dict:
    """Serialisiert einen aufgelösten Prozess zurück in die dünne Form
    (template + active_fields + field_overrides + extra_fields).

    Die Overrides werden gegen das Template zurückgerechnet — Editor-Änderungen
    an einzelnen Feldern bleiben so als Override erhalten, statt die Config zur
    vollen Legacy-fields-Liste aufzublasen."""
    tpl_fields = tpl.field_map()
    active: list[str] = []
    overrides: dict[str, dict] = {}
    extras: list[dict] = []

    for f in process.fields:
        active.append(f.id)
        base = tpl_fields.get(f.id)
        if base is None:
            extras.append(field_to_dict(f))
        else:
            diff = _field_override_diff(base, f)
            if diff:
                overrides[f.id] = diff

    d: dict = {
        "template_id": process.template_id,
        "display_name": process.display_name,
        "template": tpl.template,
        "template_revision": tpl.template_revision,
        "active_fields": active,
    }
    if overrides:
        d["field_overrides"] = overrides
    if extras:
        d["extra_fields"] = extras
    if process.row_group_size is not None:
        d["row_group_size"] = process.row_group_size
    return d


def process_to_dict(
    process: ProcessConfig,
    templates: dict[str, ProcessTemplate] | None = None,
) -> dict:
    tpl = (templates or {}).get(process.template) if process.template else None
    if tpl is not None:
        return _thin_process_to_dict(process, tpl)

    d: dict = {
        "template_id": process.template_id,
        "display_name": process.display_name,
        "fields": [field_to_dict(f) for f in process.fields],
    }
    if process.row_group_size is not None:
        d["row_group_size"] = process.row_group_size
    # Herkunft erhalten, auch wenn die Template-Datei gerade nicht auflösbar ist —
    # der Loader reicht beide Schlüssel im Legacy-Fall durch.
    if process.template:
        d["template"] = process.template
        if process.template_revision is not None:
            d["template_revision"] = process.template_revision
    return d


def product_to_dict(
    product: ProductConfig,
    templates: dict[str, ProcessTemplate] | None = None,
) -> dict:
    d: dict = {
        "product_id": product.product_id,
        "display_name": product.display_name,
        "revision": product.revision,
        "processes": [process_to_dict(p, templates) for p in product.processes],
    }
    if product.output_dir is not None:
        d["output_dir"] = product.output_dir
    if product.revision_history:
        d["revision_history"] = product.revision_history
    return d


def validate_product_config(product: ProductConfig) -> list[str]:
    """Prüft eine ProductConfig und liefert eine Liste der Fehler (leer = OK)."""
    errors: list[str] = []

    if not product.product_id.strip():
        errors.append("Produkt-ID darf nicht leer sein.")
    elif not re.match(r"^[A-Za-z0-9_]+$", product.product_id):
        errors.append(
            "Produkt-ID darf nur Buchstaben, Ziffern und Unterstriche enthalten."
        )

    if not product.display_name.strip():
        errors.append("Produkt-Anzeigename darf nicht leer sein.")

    if not product.processes:
        errors.append("Mindestens ein Prozess muss definiert sein.")

    for pi, proc in enumerate(product.processes):
        prefix = f"Prozess {pi + 1} ({proc.display_name or '?'})"

        if not proc.template_id.strip():
            errors.append(f"{prefix}: Template-ID darf nicht leer sein.")
        if not proc.display_name.strip():
            errors.append(f"{prefix}: Anzeigename darf nicht leer sein.")
        if not proc.fields:
            errors.append(f"{prefix}: Mindestens ein Feld muss definiert sein.")

        field_ids: set[str] = set()
        for fi, field in enumerate(proc.fields):
            fp = f"{prefix}, Feld {fi + 1} ({field.display_name or '?'})"

            if not field.id.strip():
                errors.append(f"{fp}: ID darf nicht leer sein.")
            if field.id in field_ids:
                errors.append(f"{fp}: ID '{field.id}' ist doppelt.")
            field_ids.add(field.id)

            if not field.display_name.strip():
                errors.append(f"{fp}: Anzeigename darf nicht leer sein.")
            if field.type not in ("text", "number", "choice", "date"):
                errors.append(f"{fp}: Ungültiger Typ '{field.type}'.")
            if field.role not in ("context", "measurement", "auto"):
                errors.append(f"{fp}: Ungültige Rolle '{field.role}'.")
            if field.type == "choice" and not field.options:
                errors.append(f"{fp}: Choice-Feld braucht mindestens eine Option.")
            if field.spec_min is not None and field.spec_max is not None:
                if field.spec_min > field.spec_max:
                    errors.append(
                        f"{fp}: spec_min ({field.spec_min}) > spec_max ({field.spec_max})."
                    )
            if field.spec_target is not None:
                if field.spec_min is not None and field.spec_target < field.spec_min:
                    errors.append(f"{fp}: spec_target unter spec_min.")
                if field.spec_max is not None and field.spec_target > field.spec_max:
                    errors.append(f"{fp}: spec_target über spec_max.")

    return errors


def save_product_config(
    product: ProductConfig,
    products_dir: Path,
    templates: dict[str, ProcessTemplate] | None = None,
) -> Path:
    """Speichert eine ProductConfig als JSON und liefert den Dateipfad.

    Mit ``templates`` bleiben dünne Configs dünn (Overrides werden gegen das
    Template zurückgerechnet). Geschrieben wird atomar (Temp-Datei + Rename),
    damit ein Abbruch mitten im Schreiben keine halbe Config hinterlässt."""
    products_dir.mkdir(parents=True, exist_ok=True)
    path = products_dir / f"{product.product_id}.json"
    data = product_to_dict(product, templates)
    payload = json.dumps(data, indent=2, ensure_ascii=False)

    tmp = path.with_name(path.name + ".tmp~")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return path
