"""Freigabe-Verwaltung für Produkt-Configs (Vier-Augen-Prinzip ohne E-Signatur).

Die eigentliche Freigabe passiert auf Papier: ein Freigabedokument je Produkt
und Revision, geprüft und freigegeben von zwei Personen (Unterschriften).
Technisch verankert wird sie über den SHA-256-Hash der Config-Datei — derselbe
Hash steht auf dem unterschriebenen Dokument und im Manifest
``data/products/freigaben.json``. Beim Laden wird der Datei-Hash gegen das
Manifest geprüft: jede nachträgliche Änderung an der Config bricht den Hash
und nimmt das Produkt automatisch aus dem Scope, bis eine neue Freigabe
erfasst wird. Digitale Signaturen sind bewusst nicht vorgesehen
(Hybrid-Ansatz, 21 CFR Part 11 narrow scope).

Manifest-Format::

    {
      "REF31962": {
        "revision": 3,
        "sha256": "<hex>",
        "dokument": "FB-31962-003",
        "datum": "2026-06-12",
        "geprueft_von": "...",
        "freigegeben_von": "...",
        "erfasst_von": "..."
      }
    }
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import date
from pathlib import Path


_logger = logging.getLogger("config")

# Status-Werte für ProductConfig.freigabe_status
FREIGEGEBEN = "freigegeben"
GEAENDERT = "geändert"            # Eintrag vorhanden, Hash/Revision passt nicht mehr
NICHT_FREIGEGEBEN = "nicht freigegeben"

_MANIFEST_NAME = "freigaben.json"


def freigaben_path(products_dir: str | Path) -> Path:
    """Das Manifest liegt bewusst im Produkt-Ordner: wer die Configs
    deployt, deployt die Freigaben mit."""
    return Path(products_dir) / _MANIFEST_NAME


def compute_config_hash(path: str | Path) -> str:
    """SHA-256 über die rohen Datei-Bytes — bindet die Papier-Freigabe an
    exakt diesen Dateistand."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_freigaben(products_dir: str | Path) -> dict[str, dict]:
    """Liest das Freigabe-Manifest. Defekt/fehlend → leer (fail-safe:
    ohne lesbares Manifest gilt kein Produkt als freigegeben)."""
    path = freigaben_path(products_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as e:
        _logger.error("Freigabe-Manifest %s nicht lesbar: %s", path, e)
        return {}


def save_freigaben(products_dir: str | Path, freigaben: dict[str, dict]) -> Path:
    """Schreibt das Manifest atomar (Temp + Rename)."""
    path = freigaben_path(products_dir)
    payload = json.dumps(freigaben, indent=2, ensure_ascii=False)
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


def determine_status(entry: dict | None, actual_sha256: str, revision: int) -> str:
    """Freigabe-Status einer Config gegen ihren Manifest-Eintrag."""
    if not entry:
        return NICHT_FREIGEGEBEN
    if entry.get("sha256") != actual_sha256:
        return GEAENDERT
    try:
        if int(entry.get("revision", -1)) != int(revision):
            return GEAENDERT
    except (TypeError, ValueError):
        return GEAENDERT
    return FREIGEGEBEN


def record_freigabe(
    products_dir: str | Path,
    product_id: str,
    config_path: str | Path,
    revision: int,
    *,
    dokument: str,
    geprueft_von: str,
    freigegeben_von: str,
    erfasst_von: str | None = None,
    datum: str | None = None,
) -> dict:
    """Erfasst eine erteilte Papier-Freigabe im Manifest und liefert den Eintrag.

    Erfasst wird nur, was auf dem unterschriebenen Dokument steht — die
    Vier-Augen-Prüfung selbst findet auf Papier statt."""
    entry = {
        "revision": int(revision),
        "sha256": compute_config_hash(config_path),
        "dokument": dokument.strip(),
        "datum": datum or date.today().isoformat(),
        "geprueft_von": geprueft_von.strip(),
        "freigegeben_von": freigegeben_von.strip(),
    }
    if erfasst_von:
        entry["erfasst_von"] = erfasst_von
    freigaben = load_freigaben(products_dir)
    freigaben[product_id] = entry
    save_freigaben(products_dir, freigaben)
    return entry
