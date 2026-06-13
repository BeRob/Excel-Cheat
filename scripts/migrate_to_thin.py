"""Migriert die bestehenden (vollen) Produkt-Configs zu dünnen Configs.

Aus jeder data/products/<REF>.json wird eine dünne Variante erzeugt, bei der die
Prozesse nur noch auf ein Operation-Template verweisen (template + active_fields +
field_overrides + ggf. extra_fields). Ausgabe nach data/products/_thin/.

ACID-TEST: Für jedes Produkt wird geprüft, dass
    resolve(dünn + Templates).fields  ==  load(alt).fields   (exakt, inkl. specs)
und template_id unverändert ist. Bei jeder Abweichung Abbruch mit Report — so ist
garantiert, dass Excel-Spalten-Mapping und Resume nicht brechen.

Aufruf:  python scripts/make_templates.py   (zuerst Templates erzeugen)
         python scripts/migrate_to_thin.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config.process_config import (  # noqa: E402
    load_process_templates,
    load_product_config,
)

from make_templates import operation_of  # noqa: E402

PRODUCTS_DIR = ROOT / "data" / "products"
TEMPLATES_DIR = ROOT / "data" / "process_templates"
THIN_DIR = PRODUCTS_DIR / "_thin"

# Attribute, die das Template kanonisch vorgibt; Override nur bei Abweichung.
OVERRIDE_KEYS = [
    "display_name", "type", "role", "persistent", "optional", "options",
    "default_value", "group_shared", "info_header", "machine_scoped",
    "spec_min", "spec_max", "spec_target",
]


def _field_attrs(fld: dict) -> dict:
    """Normalisierte Attribute eines Roh-Feld-Dicts (mit Defaults)."""
    return {
        "display_name": fld.get("display_name"),
        "type": fld.get("type", "text"),
        "role": fld.get("role", "measurement"),
        "persistent": fld.get("persistent", False),
        "optional": fld.get("optional", False),
        "options": fld.get("options"),
        "default_value": fld.get("default_value"),
        "group_shared": fld.get("group_shared", False),
        "info_header": fld.get("info_header", False),
        "machine_scoped": fld.get("machine_scoped", False),
        "spec_min": fld.get("spec_min"),
        "spec_max": fld.get("spec_max"),
        "spec_target": fld.get("spec_target"),
    }


def _thin_process(proc: dict, templates) -> dict:
    """Wandelt einen vollen Prozess in die dünne Repräsentation."""
    operation = operation_of(proc["template_id"])
    tpl = templates.get(operation)
    if tpl is None:
        raise SystemExit(f"Template '{operation}' fehlt — erst make_templates.py laufen lassen.")
    tpl_fields = {f.id: f for f in tpl.fields}

    active_fields: list[str] = []
    field_overrides: dict[str, dict] = {}
    extra_fields: list[dict] = []

    for fld in proc["fields"]:
        fid = fld["id"]
        active_fields.append(fid)
        attrs = _field_attrs(fld)

        if fid in tpl_fields:
            base = tpl_fields[fid]
            ov: dict = {}
            for key in OVERRIDE_KEYS:
                want = attrs[key]
                have = getattr(base, key)
                # options: leere Liste/None gleich behandeln
                if key == "options":
                    if (want or None) != (have or None):
                        ov[key] = want
                elif want != have:
                    ov[key] = want
            if ov:
                field_overrides[fid] = ov
        else:
            # Produktunikes Feld → extra_fields (volle Definition, default-frei)
            extra = {"id": fid, "display_name": attrs["display_name"],
                     "type": attrs["type"], "role": attrs["role"]}
            for key in ("persistent", "optional", "group_shared", "info_header",
                        "machine_scoped"):
                if attrs[key]:
                    extra[key] = True
            if attrs["options"]:
                extra["options"] = attrs["options"]
            if attrs["default_value"] is not None:
                extra["default_value"] = attrs["default_value"]
            for key in ("spec_min", "spec_max", "spec_target"):
                if attrs[key] is not None:
                    extra[key] = attrs[key]
            extra_fields.append(extra)

    thin: dict = {
        "template_id": proc["template_id"],
        "template": operation,
        "display_name": proc["display_name"],
    }
    if proc.get("row_group_size") is not None:
        thin["row_group_size"] = proc["row_group_size"]
    thin["active_fields"] = active_fields
    if field_overrides:
        thin["field_overrides"] = field_overrides
    if extra_fields:
        thin["extra_fields"] = extra_fields
    return thin


def _thin_product(data: dict, templates) -> dict:
    out: dict = {
        "product_id": data["product_id"],
        "display_name": data["display_name"],
        "revision": data.get("revision", 1),
    }
    if data.get("output_dir") is not None:
        out["output_dir"] = data["output_dir"]
    if data.get("revision_history"):
        out["revision_history"] = data["revision_history"]
    out["processes"] = [_thin_process(p, templates) for p in data["processes"]]
    return out


def _fields_equal(a, b) -> list[str]:
    """Vergleicht zwei FieldDef-Listen; liefert Liste der Abweichungs-Beschreibungen."""
    diffs: list[str] = []
    if len(a) != len(b):
        diffs.append(f"Feldanzahl {len(a)} != {len(b)}")
        return diffs
    for fa, fb in zip(a, b):
        da, db = asdict(fa), asdict(fb)
        for key in da:
            if da[key] != db[key]:
                diffs.append(f"{fa.id}.{key}: {db[key]!r} -> {da[key]!r}")
    return diffs


def main() -> int:
    templates = load_process_templates(TEMPLATES_DIR)
    if not templates:
        raise SystemExit("Keine Templates gefunden — erst make_templates.py laufen lassen.")

    THIN_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    failures = 0
    for path in sorted(PRODUCTS_DIR.glob("*.json")):
        total += 1
        original = load_product_config(path)  # alte volle Datei
        raw = json.loads(path.read_text(encoding="utf-8"))
        thin = _thin_product(raw, templates)

        thin_path = THIN_DIR / path.name
        thin_path.write_text(
            json.dumps(thin, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # ACID-TEST: dünn auflösen und gegen Original vergleichen
        resolved = load_product_config(thin_path, templates)
        product_diffs: list[str] = []
        if len(resolved.processes) != len(original.processes):
            product_diffs.append("Prozessanzahl unterschiedlich")
        for rp, op in zip(resolved.processes, original.processes):
            if rp.template_id != op.template_id:
                product_diffs.append(
                    f"template_id {op.template_id} -> {rp.template_id}"
                )
            for d in _fields_equal(rp.fields, op.fields):
                product_diffs.append(f"{op.template_id}: {d}")

        if product_diffs:
            failures += 1
            print(f"[FAIL] {path.name}")
            for d in product_diffs:
                print(f"        {d}")
        else:
            print(f"[ OK ] {path.name}")

    print(f"\n{total} Produkte, {failures} Abweichungen.")
    print(f"Dünne Configs in {THIN_DIR}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
