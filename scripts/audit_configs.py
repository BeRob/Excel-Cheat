"""Konsistenz-Audit der Produkt-Configs.

Listet auf, wo gleiche Konzepte uneinheitlich definiert sind:
- gleiche Feld-id mit mehreren display_names / Rollen / Typen
- Mess-Sets je Prozesstyp (verb-gruppiert)

Aufruf:  python scripts/audit_configs.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

PRODUCTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "products")


def load_processes() -> list[tuple[str, str, list[dict]]]:
    procs: list[tuple[str, str, list[dict]]] = []
    for path in sorted(glob.glob(os.path.join(PRODUCTS_DIR, "*.json"))):
        data = json.load(open(path, encoding="utf-8"))
        name = os.path.basename(path).replace(".json", "")
        for proc in data.get("processes", []):
            procs.append((name, proc.get("display_name", "?"), proc.get("fields", [])))
    return procs


def verb(display_name: str) -> str:
    tokens = display_name.split()
    return tokens[1] if len(tokens) > 1 else display_name


def audit_field_consistency(procs) -> int:
    """Pro Feld-id: zeigt abweichende display_name/role/type. Returns Anzahl Treffer."""
    variants: dict[str, set] = defaultdict(set)
    for _, _, fields in procs:
        for fld in fields:
            variants[fld["id"]].add(
                (fld.get("display_name"), fld.get("role"), fld.get("type"))
            )
    hits = 0
    print("=== FELD-KONSISTENZ (id mit mehreren Definitionen) ===")
    for fid, defs in sorted(variants.items()):
        if len(defs) > 1:
            hits += 1
            print(f"  [MEHRDEUTIG] {fid}")
            for dn, role, typ in sorted(defs, key=lambda x: str(x)):
                print(f"      display={dn!r}  role={role}  type={typ}")
    if not hits:
        print("  keine Abweichungen")
    print()
    return hits


def audit_measurement_sets(procs) -> None:
    groups: dict[str, list] = defaultdict(list)
    for name, dn, fields in procs:
        groups[verb(dn)].append((name, dn, fields))
    print("=== MESS-SETS JE PROZESSTYP ===")
    for v in sorted(groups):
        print(f"--- {v} ({len(groups[v])} Prozesse) ---")
        for name, dn, fields in groups[v]:
            ms = [x["id"] for x in fields if x.get("role") == "measurement"]
            print(f"  {name:<14}{dn:<32}{ms}")
        print()


def main() -> int:
    procs = load_processes()
    print(f"{len(procs)} Prozesse in {len(set(p[0] for p in procs))} Produkten\n")
    hits = audit_field_consistency(procs)
    audit_measurement_sets(procs)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
