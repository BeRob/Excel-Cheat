"""Erzeugt kanonische Operation-Templates aus den bestehenden Produkt-Configs.

Gruppiert alle Prozesse nach Operation (Verb hinter ``IPCn_``; Fertigschneiden→
Schneiden, Menge_Ausschussplatten→Ausschussplatten) und bildet je Operation ein
Feld-**Superset**: jede je vorkommende Feld-id genau einmal, mit den kanonischen
Attributen (häufigster Wert). Spec-Grenzen (spec_min/max/target) werden NICHT ins
Template geschrieben — sie sind produktspezifisch und kommen später aus den dünnen
Produkt-Configs (field_overrides).

Zusatz-Annotation ``_present_in`` je Feld (nicht Runtime) dokumentiert, in welchen
Produkten das Feld vorkommt — Review-Hilfe, um produktspezifische Felder zu erkennen.

Aufruf:  python scripts/make_templates.py
Ausgabe: data/process_templates/<Operation>.json  (8 Dateien)

Dies ist ein EINMAL-Tool zur Erstgenerierung der Review-Vorlage. Danach werden die
Templates per Hand/Review gepflegt.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PRODUCTS_DIR = ROOT / "data" / "products"
TEMPLATES_DIR = ROOT / "data" / "process_templates"

# Operationen, die fachlich zusammengefasst werden (User-Entscheidung).
OPERATION_ALIASES = {
    "Fertigschneiden": "Schneiden",
    "Menge_Ausschussplatten": "Ausschussplatten",
}

# Attribute, die NICHT ins Template gehören (produktspezifisch → field_overrides).
SPEC_KEYS = ("spec_min", "spec_max", "spec_target")

# Reihenfolge der FieldDef-Keys in der Ausgabe (für lesbare, stabile Templates).
FIELD_KEY_ORDER = [
    "id", "display_name", "type", "role", "persistent", "optional",
    "options", "default_value", "group_shared", "info_header", "machine_scoped",
]


def operation_of(template_id: str) -> str:
    """Leitet die Operation aus der template_id ab (Teil hinter IPCn_)."""
    verb = template_id.split("_", 1)[1] if "_" in template_id else template_id
    return OPERATION_ALIASES.get(verb, verb)


def load_all_processes():
    """Liefert (product_id, process_dict) für alle Prozesse aller Produkte."""
    for path in sorted(PRODUCTS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        pid = data["product_id"]
        for proc in data.get("processes", []):
            yield pid, proc


def _attr_tuple(fld: dict) -> tuple:
    """Nicht-Spec-Attribute eines Feldes als hashbares Tuple (für Mode-Bildung)."""
    return (
        fld.get("display_name"),
        fld.get("type", "text"),
        fld.get("role", "measurement"),
        fld.get("persistent", False),
        fld.get("optional", False),
        tuple(fld.get("options") or []),
        fld.get("default_value"),
        fld.get("group_shared", False),
        fld.get("info_header", False),
        fld.get("machine_scoped", False),
    )


def _tuple_to_field(fid: str, attrs: tuple) -> dict:
    (display_name, ftype, role, persistent, optional, options,
     default_value, group_shared, info_header, machine_scoped) = attrs
    out: dict = {
        "id": fid,
        "display_name": display_name,
        "type": ftype,
        "role": role,
    }
    if persistent:
        out["persistent"] = True
    if optional:
        out["optional"] = True
    if options:
        out["options"] = list(options)
    if default_value is not None:
        out["default_value"] = default_value
    if group_shared:
        out["group_shared"] = True
    if info_header:
        out["info_header"] = True
    if machine_scoped:
        out["machine_scoped"] = True
    return out


def build_template(operation: str, entries: list[tuple[str, dict]]) -> dict:
    """Baut das Superset-Template für eine Operation.

    entries: Liste von (product_id, process_dict).
    """
    # Pro Feld-id: Positionen, Attribut-Häufigkeiten, Produkte, Spec-Vielfalt.
    positions: dict[str, list[int]] = defaultdict(list)
    attr_counter: dict[str, Counter] = defaultdict(Counter)
    present_in: dict[str, set[str]] = defaultdict(set)
    spec_variants: dict[str, set] = defaultdict(set)

    for pid, proc in entries:
        for idx, fld in enumerate(proc.get("fields", [])):
            fid = fld["id"]
            positions[fid].append(idx)
            attr_counter[fid][_attr_tuple(fld)] += 1
            present_in[fid].add(pid)
            spec_variants[fid].add(tuple(fld.get(k) for k in SPEC_KEYS))

    all_products = {p for p, _ in entries}
    # Felder nach mittlerer Position sortieren (lesbare, plausible Reihenfolge).
    field_ids = sorted(
        positions, key=lambda f: sum(positions[f]) / len(positions[f])
    )

    fields_out: list[dict] = []
    notes: dict[str, str] = {}
    for fid in field_ids:
        common_attrs, _ = attr_counter[fid].most_common(1)[0]
        field = _ordered_field(_tuple_to_field(fid, common_attrs))

        prods = sorted(present_in[fid])
        field["_present_in"] = "ALL" if len(prods) == len(all_products) else prods
        fields_out.append(field)

        # Hinweis: uneinheitliche Nicht-Spec-Attribute (z.B. display_name).
        note_parts: list[str] = []
        if len(attr_counter[fid]) > 1:
            variants = sorted({a[0] for a in attr_counter[fid]})  # display_names
            note_parts.append(
                f"display_name/Attribute uneinheitlich: {variants} — Kanonik gewählt, "
                f"Abweichungen via field_overrides."
            )
        real_specs = {s for s in spec_variants[fid] if any(v is not None for v in s)}
        if len(real_specs) > 1:
            note_parts.append("Specs produktspezifisch (kommen aus field_overrides).")
        if note_parts:
            notes[fid] = " ".join(note_parts)

    template: dict = {
        "template": operation,
        "template_revision": 1,
        "fields": fields_out,
    }
    if notes:
        template["_unification_notes"] = notes
    return template


def _ordered_field(field: dict) -> dict:
    """Sortiert die Keys eines Feld-Dicts in stabile, lesbare Reihenfolge."""
    return {k: field[k] for k in FIELD_KEY_ORDER if k in field}


def main() -> int:
    groups: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for pid, proc in load_all_processes():
        groups[operation_of(proc["template_id"])].append((pid, proc))

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{len(groups)} Operationen gefunden:\n")
    for operation in sorted(groups):
        template = build_template(operation, groups[operation])
        path = TEMPLATES_DIR / f"{operation}.json"
        path.write_text(
            json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        n_fields = len(template["fields"])
        n_prods = len({p for p, _ in groups[operation]})
        print(f"  {operation:<22} {n_fields:>2} Felder  "
              f"({len(groups[operation])} Prozesse, {n_prods} Produkte)  -> {path.name}")
    print(f"\nGeschrieben nach {TEMPLATES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
