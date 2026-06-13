"""Freigabedokumente für Produkt-Configs erzeugen (CLI).

Nutzt die Word-Vorlage ``data/vorlagen/freigabedokument.docx`` (Platzhalter
siehe ``src/config/freigabedokument.py``); ohne Vorlage entsteht ein HTML mit
festem Layout. Das ausgedruckte, von zwei Personen unterschriebene Dokument
ist die Freigabe; der enthaltene SHA-256-Hash bindet sie an exakt diesen
Dateistand. Danach im Config-Editor „Freigabe erfassen…“ — erst dann ist das
Produkt im Scope.

Aufruf:
    python scripts/make_freigabedokument.py            # alle Produkte
    python scripts/make_freigabedokument.py REF31962   # nur eines

Ausgabe: data/freigabedokumente/Freigabe_<REF>_Rev<N>.(docx|html)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.freigabedokument import erzeuge_freigabedokument  # noqa: E402
from src.config.process_config import (  # noqa: E402
    load_process_templates,
    load_product_config,
)

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "data" / "products"
TEMPLATES_DIR = ROOT / "data" / "process_templates"
OUT_DIR = ROOT / "data" / "freigabedokumente"
VORLAGE = ROOT / "data" / "vorlagen" / "freigabedokument.docx"


def main(argv: list[str]) -> int:
    templates = load_process_templates(TEMPLATES_DIR)
    if argv:
        paths = [PRODUCTS_DIR / f"{ref}.json" for ref in argv]
        missing = [p for p in paths if not p.exists()]
        if missing:
            print("Nicht gefunden: " + ", ".join(p.name for p in missing))
            return 1
    else:
        paths = [
            p for p in sorted(PRODUCTS_DIR.glob("*.json"))
            if p.name != "freigaben.json" and not p.name.startswith("_")
        ]

    if not VORLAGE.exists():
        print(f"Hinweis: keine Word-Vorlage unter {VORLAGE} — erzeuge HTML.")

    for path in paths:
        product = load_product_config(path, templates)
        out, unresolved = erzeuge_freigabedokument(
            product, path, OUT_DIR,
            vorlage=VORLAGE if VORLAGE.exists() else None,
        )
        note = ""
        if unresolved:
            note = "  [unbekannte Platzhalter: " + ", ".join(sorted(unresolved)) + "]"
        print(f"[ OK ] {out.name}{note}")

    print(f"\n{len(paths)} Dokument(e) in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
