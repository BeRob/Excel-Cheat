"""Serialisierung und Validierung von Produktkonfigurationen."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.config.process_config import FieldDef, ProcessConfig, ProductConfig


def field_to_dict(field: FieldDef) -> dict:
    """Konvertiert ein FieldDef in ein JSON-serialisierbares Dict."""
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
    return d


def process_to_dict(process: ProcessConfig) -> dict:
    """Konvertiert ein ProcessConfig in ein JSON-serialisierbares Dict."""
    d: dict = {
        "template_id": process.template_id,
        "display_name": process.display_name,
        "fields": [field_to_dict(f) for f in process.fields],
    }
    if process.row_group_size is not None:
        d["row_group_size"] = process.row_group_size
    return d


def product_to_dict(product: ProductConfig) -> dict:
    """Konvertiert ein ProductConfig in ein JSON-serialisierbares Dict."""
    d: dict = {
        "product_id": product.product_id,
        "display_name": product.display_name,
        "processes": [process_to_dict(p) for p in product.processes],
    }
    if product.output_dir is not None:
        d["output_dir"] = product.output_dir
    return d


def validate_product_config(product: ProductConfig) -> list[str]:
    """Validiert eine ProductConfig. Gibt eine Liste von Fehlerstrings zurueck (leer = OK)."""
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
            if field.type not in ("text", "number", "choice"):
                errors.append(f"{fp}: Ungueltiger Typ '{field.type}'.")
            if field.role not in ("context", "measurement", "auto"):
                errors.append(f"{fp}: Ungueltige Rolle '{field.role}'.")
            if field.type == "choice" and (
                not field.options or len(field.options) == 0
            ):
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
                    errors.append(f"{fp}: spec_target ueber spec_max.")

    return errors


def save_product_config(product: ProductConfig, products_dir: Path) -> Path:
    """Speichert eine ProductConfig als JSON. Gibt den Dateipfad zurueck."""
    products_dir.mkdir(parents=True, exist_ok=True)
    path = products_dir / f"{product.product_id}.json"
    data = product_to_dict(product)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return path
