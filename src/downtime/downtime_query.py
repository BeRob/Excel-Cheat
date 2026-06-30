"""Auswertung der Störungs-Ereignisse: Paarung, Filter, Aggregation, KPIs.

Bewusst **Tk-frei** (wie ``src/config/config_editing.py``), damit die gesamte
Logik ohne GUI unit-testbar ist. Eingabe ist immer die Roh-Ereignisliste aus
``DowntimeStore.read_all()``; ``pair_stoerungen`` macht daraus
``Stoerung``-Objekte (Start + optionales Ende).
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import date
from typing import Callable, Iterable

from src.downtime.downtime_models import Stoerung

_START_FIELDS = (
    "produkt_id", "prozess_template_id", "prozess_name", "schicht", "maschine",
    "station", "kategorie", "ursache", "beschreibung", "erfasser_user",
    "host", "win_user",
)


def pair_stoerungen(records: Iterable[dict]) -> list[Stoerung]:
    """Paart ``stoerung_start``/``stoerung_ende`` über ``id`` zu Stoerung-Objekten.

    Reihenfolge = Reihenfolge des ersten (Start-)Auftretens. Ein Ende ohne Start
    wird ignoriert (defekter Datensatz); ein doppeltes Ende überschreibt nicht.
    """
    by_id: "OrderedDict[str, Stoerung]" = OrderedDict()
    for rec in records:
        kind = rec.get("kind")
        sid = rec.get("id")
        if not sid:
            continue
        if kind == "stoerung_start":
            if sid in by_id:
                continue  # Duplikat-Start ignorieren
            kwargs = {f: rec.get(f, "") for f in _START_FIELDS}
            by_id[sid] = Stoerung(id=sid, ts_start=rec.get("ts_start", ""), **kwargs)
        elif kind == "stoerung_ende":
            s = by_id.get(sid)
            if s is None or not s.offen:
                continue  # Ende ohne Start oder bereits geschlossen
            s.ts_ende = rec.get("ts_ende") or None
            s.dauer_sekunden = rec.get("dauer_sekunden")
            s.techniker_name = rec.get("techniker_name", "")
            s.behebung = rec.get("behebung", "")
            s.freigabe_user = rec.get("freigabe_user", "")
    return list(by_id.values())


def find_open(
    stoerungen: Iterable[Stoerung], *,
    produkt_id: str,
    prozess_template_id: str,
    maschine: str | None = None,
) -> Stoerung | None:
    """Offene Störung für den aktuellen Kontext (Produkt+Prozess[+Maschine])."""
    match: Stoerung | None = None
    for s in stoerungen:
        if not s.offen:
            continue
        if s.produkt_id != produkt_id or s.prozess_template_id != prozess_template_id:
            continue
        if maschine not in (None, "") and s.maschine and s.maschine != maschine:
            continue
        match = s  # jüngste passende offene Störung gewinnt (Liste ist start-sortiert)
    return match


def filter_stoerungen(
    stoerungen: Iterable[Stoerung], *,
    von: date | None = None,
    bis: date | None = None,
    produkt_id: str | None = None,
    prozess_template_id: str | None = None,
    station: str | None = None,
    kategorie: str | None = None,
    maschine: str | None = None,
    status: str | None = None,  # "offen" | "behoben" | None
) -> list[Stoerung]:
    """Filtert nach den üblichen Auswertungs-Dimensionen. Zeitbezug = Startdatum."""
    out: list[Stoerung] = []
    for s in stoerungen:
        d = s.start_dt.date() if s.start_dt else None
        if von and (d is None or d < von):
            continue
        if bis and (d is None or d > bis):
            continue
        if produkt_id and s.produkt_id != produkt_id:
            continue
        if prozess_template_id and s.prozess_template_id != prozess_template_id:
            continue
        if station and s.station.strip().lower() != station.strip().lower():
            continue
        if kategorie and s.kategorie != kategorie:
            continue
        if maschine and s.maschine != maschine:
            continue
        if status and s.status != status:
            continue
        out.append(s)
    return out


# ---- Aggregation & KPIs --------------------------------------------------


def aggregate_by(
    stoerungen: Iterable[Stoerung],
    key_func: Callable[[Stoerung], str],
) -> dict[str, dict]:
    """Gruppiert nach key_func → {key: {anzahl, dauer_sum, dauer_avg, offen}}.

    ``dauer_sum``/``dauer_avg`` beziehen nur geschlossene Störungen mit
    bekannter Dauer ein; ``offen`` zählt noch laufende Störungen der Gruppe.
    """
    agg: dict[str, dict] = {}
    for s in stoerungen:
        key = key_func(s) or "(ohne)"
        bucket = agg.setdefault(
            key, {"anzahl": 0, "dauer_sum": 0.0, "dauer_avg": 0.0, "offen": 0}
        )
        bucket["anzahl"] += 1
        if s.offen:
            bucket["offen"] += 1
        dauer = s.computed_dauer_sekunden()
        if dauer is not None:
            bucket["dauer_sum"] += dauer
    for bucket in agg.values():
        geschlossen = bucket["anzahl"] - bucket["offen"]
        bucket["dauer_avg"] = bucket["dauer_sum"] / geschlossen if geschlossen else 0.0
    return agg


def aggregate_by_station(stoerungen: Iterable[Stoerung]) -> dict[str, dict]:
    return aggregate_by(stoerungen, lambda s: s.station)


def aggregate_by_kategorie(stoerungen: Iterable[Stoerung]) -> dict[str, dict]:
    return aggregate_by(stoerungen, lambda s: s.kategorie)


def aggregate_by_prozess(stoerungen: Iterable[Stoerung]) -> dict[str, dict]:
    return aggregate_by(stoerungen, lambda s: s.prozess_name or s.prozess_template_id)


def gesamt_stoerzeit(stoerungen: Iterable[Stoerung]) -> float:
    """Summe der Störzeit (Sekunden) aller geschlossenen Störungen."""
    total = 0.0
    for s in stoerungen:
        d = s.computed_dauer_sekunden()
        if d is not None and not s.offen:
            total += d
    return total


def anzahl_ausfaelle(stoerungen: Iterable[Stoerung]) -> int:
    """Anzahl geschlossener Störungen (= behobene Ausfälle)."""
    return sum(1 for s in stoerungen if not s.offen)


def mttr(stoerungen: Iterable[Stoerung]) -> float | None:
    """Mean Time To Repair: Ø Behebungsdauer geschlossener Störungen (Sekunden)."""
    durations = [
        s.computed_dauer_sekunden()
        for s in stoerungen
        if not s.offen and s.computed_dauer_sekunden() is not None
    ]
    if not durations:
        return None
    return sum(durations) / len(durations)


def mtbf(stoerungen: Iterable[Stoerung], planzeit_sekunden: float) -> float | None:
    """Mean Time Between Failures: Betriebszeit / Anzahl Ausfälle.

    Betriebszeit = Planzeit − Störzeit. Ohne Ausfälle nicht definiert (None).
    """
    n = anzahl_ausfaelle(stoerungen)
    if n <= 0:
        return None
    betriebszeit = max(0.0, planzeit_sekunden - gesamt_stoerzeit(stoerungen))
    return betriebszeit / n


def verfuegbarkeit(stoerungen: Iterable[Stoerung], planzeit_sekunden: float) -> float | None:
    """Verfügbarkeit (Availability) = (Planzeit − Störzeit) / Planzeit ∈ [0, 1].

    None, wenn keine Planzeit (> 0) angegeben ist.
    """
    if planzeit_sekunden <= 0:
        return None
    stoerzeit = gesamt_stoerzeit(stoerungen)
    return max(0.0, min(1.0, (planzeit_sekunden - stoerzeit) / planzeit_sekunden))
