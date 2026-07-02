"""Datenmodell und zweistufige Fehler-Code-Liste für die Störungserfassung.

Eine Störung wird im Store als zwei Zeilen abgelegt (``stoerung_start`` bei der
Erfassung, ``stoerung_ende`` bei der Freigabe), gepaart über ``id``. Das
``Stoerung``-Dataclass ist die zusammengeführte Sicht für Auswertung und UI.

Dieses Modul ist bewusst **Tk-frei** und damit ohne GUI unit-testbar.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_logger = logging.getLogger("downtime")

# Eingebaute Default-Taxonomie — greift, wenn stoerungs_codes.json fehlt oder
# fehlerhaft ist, damit die Erfassung immer funktioniert.
DEFAULT_KATEGORIEN: list[dict] = [
    {"name": "Mechanik", "ursachen": ["Lagerschaden", "Werkzeugbruch", "Materialstau", "Verschleiß", "Justage/Einstellung"]},
    {"name": "Elektrik", "ursachen": ["Sensorfehler", "Antrieb/Motor", "Steuerung/SPS", "Verkabelung"]},
    {"name": "Material", "ursachen": ["Fehlmaterial", "Materialfehler", "Materialwechsel"]},
    {"name": "Bediener/Rüstung", "ursachen": ["Rüstung/Umbau", "Bedienfehler", "Reinigung"]},
    {"name": "Sonstiges", "ursachen": ["Warten auf Technik", "Alle übrigen Verluste"]},
]


def parse_iso(value: str | None) -> datetime | None:
    """Robustes Parsen eines ISO-8601-Zeitstempels (mit Offset). None bei Fehler."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


@dataclass
class StoerungsCodes:
    """Zweistufige Klassifizierung: Kategorie → Liste möglicher Ursachen."""

    kategorien: list[dict] = field(default_factory=list)

    def kategorie_namen(self) -> list[str]:
        return [str(k["name"]) for k in self.kategorien if k.get("name")]

    def ursachen(self, kategorie: str) -> list[str]:
        for k in self.kategorien:
            if k.get("name") == kategorie:
                return [str(u) for u in k.get("ursachen", [])]
        return []


def load_stoerungs_codes(path: str | Path) -> StoerungsCodes:
    """Lädt die Fehler-Code-Liste. Fehlt/fehlerhaft → Default-Taxonomie."""
    try:
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            raw = data.get("kategorien") if isinstance(data, dict) else None
            if isinstance(raw, list):
                clean: list[dict] = []
                for k in raw:
                    if isinstance(k, dict) and k.get("name"):
                        urs = k.get("ursachen", [])
                        clean.append({
                            "name": str(k["name"]),
                            "ursachen": [str(u) for u in urs] if isinstance(urs, list) else [],
                        })
                if clean:
                    return StoerungsCodes(kategorien=clean)
            _logger.warning("stoerungs_codes.json ohne gültige 'kategorien' — nutze Default")
    except Exception as e:  # noqa: BLE001
        _logger.warning("stoerungs_codes.json nicht lesbar (%s) — nutze Default", e)
    return StoerungsCodes(kategorien=[dict(k) for k in DEFAULT_KATEGORIEN])


@dataclass
class Stoerung:
    """Zusammengeführte Sicht auf eine Störung (Start + optionales Ende)."""

    id: str
    ts_start: str
    produkt_id: str = ""
    prozess_template_id: str = ""
    prozess_name: str = ""
    schicht: str = ""
    maschine: str = ""
    station: str = ""
    kategorie: str = ""
    ursache: str = ""
    beschreibung: str = ""
    erfasser_user: str = ""
    host: str = ""
    win_user: str = ""
    # Ende-Felder (None/leer solange offen)
    ts_ende: str | None = None
    dauer_sekunden: float | None = None
    techniker_name: str = ""
    behebung: str = ""
    freigabe_user: str = ""

    @property
    def offen(self) -> bool:
        return not self.ts_ende

    @property
    def status(self) -> str:
        return "offen" if self.offen else "behoben"

    @property
    def start_dt(self) -> datetime | None:
        return parse_iso(self.ts_start)

    @property
    def ende_dt(self) -> datetime | None:
        return parse_iso(self.ts_ende)

    def computed_dauer_sekunden(self) -> float | None:
        """Dauer aus den Zeitstempeln (Fallback, falls dauer_sekunden fehlt)."""
        if self.dauer_sekunden is not None:
            return self.dauer_sekunden
        a, b = self.start_dt, self.ende_dt
        if a and b:
            return max(0.0, (b - a).total_seconds())
        return None
