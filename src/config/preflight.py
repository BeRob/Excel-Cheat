"""Startup-Preflight: prüft, ob alle konfigurierten Pfade erreichbar sind.

In Produktion liegen Daten- und Schreibpfade auf einem Netzlaufwerk (UNC,
konfiguriert über ``config.json``). Ist die Freigabe nicht erreichbar oder
fehlen Rechte, soll die App das **beim Start** klar melden und sauber
beenden — statt später mit unvollständigem Audit-Trail weiterzulaufen (GMP).

Das Modul ist bewusst **Tk-frei**: es liefert nur strukturierte Befunde
(`PreflightResult`). Den Dialog und das Beenden baut der Aufrufer (`app.py`),
und Unit-Tests können die Logik ohne Tkinter prüfen.

Schweregrade:
- ``CRITICAL``: ohne diesen Pfad ist kein regulärer/GMP-konformer Betrieb
  möglich (Anmeldung, Produkte, Templates, Audit-/Log-Schreibziele).
- ``WARNING``: Datei fehlt, App läuft aber mit dokumentiertem Fallback
  weiter (app_config.json → Defaults, freigaben.json → „nicht freigegeben").
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

CRITICAL = "critical"
WARNING = "warning"


@dataclass
class PreflightIssue:
    """Ein einzelner Befund zu genau einem Pfad."""

    severity: str          # CRITICAL | WARNING
    label: str             # menschenlesbare Bezeichnung des Pfads
    path: Path
    reason: str            # Klartext, was nicht stimmt


@dataclass
class PreflightResult:
    issues: list[PreflightIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True, solange kein CRITICAL-Befund vorliegt (Warnings erlaubt)."""
        return not any(i.severity == CRITICAL for i in self.issues)

    @property
    def critical(self) -> list[PreflightIssue]:
        return [i for i in self.issues if i.severity == CRITICAL]

    @property
    def warnings(self) -> list[PreflightIssue]:
        return [i for i in self.issues if i.severity == WARNING]


def _strerror(exc: OSError) -> str:
    return exc.strerror or str(exc)


def _check_readable_file(
    label: str, path: Path, issues: list[PreflightIssue], severity: str = CRITICAL,
) -> None:
    if not path.exists():
        issues.append(PreflightIssue(severity, label, path, "Datei nicht gefunden"))
        return
    try:
        with open(path, "rb"):
            pass
    except OSError as exc:
        issues.append(
            PreflightIssue(severity, label, path, f"nicht lesbar: {_strerror(exc)}")
        )


def _check_dir_has_json(
    label: str, path: Path, issues: list[PreflightIssue], severity: str = CRITICAL,
) -> None:
    if not path.exists():
        issues.append(PreflightIssue(severity, label, path, "Verzeichnis nicht gefunden"))
        return
    if not path.is_dir():
        issues.append(PreflightIssue(severity, label, path, "ist kein Verzeichnis"))
        return
    try:
        has_json = any(path.glob("*.json"))
    except OSError as exc:
        issues.append(
            PreflightIssue(severity, label, path, f"nicht lesbar: {_strerror(exc)}")
        )
        return
    if not has_json:
        issues.append(
            PreflightIssue(severity, label, path, "keine *.json-Dateien gefunden")
        )


def _check_writable_dir(
    label: str, path: Path, issues: list[PreflightIssue], severity: str = CRITICAL,
) -> None:
    """Echter Schreibtest: Verzeichnis anlegen (falls nötig) + Probe-Datei
    schreiben und wieder löschen. Reines ``exists()`` würde Rechteprobleme
    auf Netzwerkfreigaben nicht erkennen."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        issues.append(
            PreflightIssue(severity, label, path, f"nicht anlegbar: {_strerror(exc)}")
        )
        return
    probe = path / f".qainput_write_test_{os.getpid()}"
    try:
        probe.write_text("ok", encoding="utf-8")
    except OSError as exc:
        issues.append(
            PreflightIssue(severity, label, path, f"nicht beschreibbar: {_strerror(exc)}")
        )
        return
    finally:
        try:
            probe.unlink()
        except OSError:
            pass


def check_paths() -> PreflightResult:
    """Prüft alle in ``settings`` aufgelösten Pfade auf Erreichbarkeit.

    Liest die Pfade beim Aufruf aus dem ``settings``-Modul (Tests können die
    Modul-Attribute monkeypatchen)."""
    from src.config import settings as s

    result = PreflightResult()
    iss = result.issues

    # --- READ-required: ohne diese ist kein Betrieb möglich ---
    _check_readable_file("Benutzerdatenbank (users.kv)", s.USERS_KV_PATH, iss)
    _check_dir_has_json("Produkt-Configs", s.PRODUCTS_DIR, iss)
    _check_dir_has_json("Prozess-Templates", s.PROCESS_TEMPLATES_DIR, iss)

    # --- WRITE-required: GMP-Schreibziele müssen erreichbar UND beschreibbar sein ---
    _check_writable_dir("Audit-Verzeichnis", s.AUDIT_DIR, iss)
    _check_writable_dir("Log-Verzeichnis", s.LOG_DIR, iss)

    # --- Optional: App läuft mit dokumentiertem Fallback weiter ---
    _check_readable_file(
        "Globale Konfiguration (app_config.json)", s.APP_CONFIG_PATH, iss, WARNING
    )
    _check_readable_file(
        "Freigabe-Manifest (freigaben.json)", s.PRODUCTS_DIR / "freigaben.json", iss, WARNING
    )

    return result
