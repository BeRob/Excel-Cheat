"""Zentrale Versionsinformationen.

Single source of truth für die Anwendungsversion. Alle anderen Stellen
(settings.py, Info-Dialog, deployment/version_info.txt) leiten ihre Werte
hieraus ab. Beim Versions-Bump nur `APP_VERSION_TUPLE` und das Datum
unten anpassen — der String wird automatisch generiert.

Produkt-Revisionen liegen pro Produkt-JSON unter dem Top-Level-Schlüssel
`revision`; `collect_product_revisions()` aggregiert sie für den
Info-Dialog und sonstige Auswertungen.
"""

from __future__ import annotations

from pathlib import Path


# (Major, Minor, Patch, Build) — Build bleibt typischerweise 0.
APP_VERSION_TUPLE: tuple[int, int, int, int] = (0, 9, 0, 0)
APP_VERSION: str = ".".join(str(n) for n in APP_VERSION_TUPLE[:3])
APP_VERSION_FULL: str = ".".join(str(n) for n in APP_VERSION_TUPLE)

APP_VERSION_DATE: str = "2026-06-30"

APP_NAME: str = "QAInput"
APP_COMPANY: str = "Questalpha"
APP_DESCRIPTION: str = "QA-Messwerterfassung"


def collect_product_revisions(products_dir: Path) -> dict[str, int]:
    """Liest aus allen Produkt-JSONs im Verzeichnis das Top-Level-Feld
    `revision` und gibt eine Map `product_id -> revision` zurück.

    Fehlt das Feld in einer Datei, wird Revision 1 angenommen
    (rückwärtskompatibel für ältere Configs)."""
    import json

    result: dict[str, int] = {}
    if not products_dir.exists():
        return result
    for path in sorted(products_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        pid = data.get("product_id")
        if not isinstance(pid, str):
            continue
        rev = data.get("revision", 1)
        try:
            result[pid] = int(rev)
        except (TypeError, ValueError):
            result[pid] = 1
    return result
