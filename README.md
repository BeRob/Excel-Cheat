# QAInput – Messwerterfassung

Tkinter-Desktop-App zur Erfassung von QA-Messwerten in Excel-Dateien.
Bediener wählen Produkt und Prozess (JSON-Configs), tragen Kontext- und
Messwerte ein, die App schreibt die Zeilen in automatisch erzeugte
Excel-Dateien. Komplett deutschsprachige Oberfläche, GMP-Audit-Trail.

Aktuelle Version: siehe `src/version.py` (`APP_VERSION`).

## Voraussetzungen

| | Version / Paket |
|---|---|
| Python | **3.11 – 3.13** empfohlen (`X \| Y`-Union-Syntax) |
| Pflicht-Abhängigkeit | `openpyxl` |
| Optional | `xlrd` (nur für alte `.xls`-Vorlagen), `Pillow` (Logo-Skalierung) |
| Nur für Build | `pyinstaller` |

### Hinweis zu Python 3.14

Python 3.14 funktioniert, ist aber sehr neu. PyInstaller erfasst dort unter
Umständen nicht alle `openpyxl`-Submodule automatisch — die `.spec`-Datei
verwendet deshalb `collect_all('openpyxl')`. Wer auf Nummer sicher gehen
will, baut mit Python 3.11–3.13.

## Installation

```bash
git clone <repo-url>
cd QAInput
pip install openpyxl
# optional:
pip install xlrd Pillow
# nur für den Build:
pip install pyinstaller
```

Es gibt bewusst keine `requirements.txt` — die Abhängigkeitsliste ist klein
und absichtlich minimal gehalten.

## Aus dem Quellcode starten

```bash
python app.py
```

## Tests

```bash
# alle Tests
python -m unittest discover -s tests -p "test_*.py" -v

# einzelne Datei
python -m unittest tests.test_validation -v
```

Kein pytest — nur die Standardbibliothek `unittest`.

## Produktions-Build (Windows-EXE)

Der Build läuft über PyInstaller (`build_exe.spec`, `--onedir`-Modus).
**Wichtig:** PyInstaller bündelt `openpyxl` aus genau dem Python, das in der
aktiven Shell als `python`/`pyinstaller` aufgelöst wird. Vor dem Build prüfen:

```bash
python -c "import openpyxl, sys; print(openpyxl.__version__, sys.executable)"
where pyinstaller
```

Beide müssen auf dieselbe Python-Installation zeigen.

Build ausführen (PowerShell oder cmd, kein Admin nötig):

```bash
cd deployment
.\build.bat
```

Ergebnis: `deployment/dist/QAInput/`. Den **kompletten Ordnerinhalt**
(`QAInput.exe` + `_internal/` + `data/` + `config.json`) auf das
Zielverzeichnis kopieren.

### deployment/-Ordner

`deployment/` ist eine lokale, gitignorierte Kopie aller Build-Artefakte
(`app.py`, `src/`, Configs, Logo, HTML-Anleitungen, `.spec`, `build.bat`,
`version_info.txt`, `config.json` mit Produktions-Netzwerkpfaden).
Entwicklung immer aus dem Repo-Root, **nicht** aus `deployment/`.

## Konfiguration der Datenpfade

Datenverzeichnisse sind zur Laufzeit überschreibbar (siehe `CLAUDE.md` /
`src/config/settings.py`). Auflösungsreihenfolge:

1. Umgebungsvariablen (`QAINPUT_AUDIT_DIR`, `QAINPUT_PRODUCTS_DIR`, …,
   bzw. `QAINPUT_DATA_DIR` als Sammel-Fallback)
2. Bootstrap-Datei `config.json` neben der EXE
3. Default: Unterordner von `<APP_ROOT>/data`

So zeigen in der Produktion z.B. Audit-Trail und Produkt-Configs auf ein
Netzlaufwerk, ohne den Code anzufassen.

## Versionierung

Single Source of Truth: `src/version.py`. Bei einem Versions-Bump zusätzlich
`version_info.txt` (PyInstaller-Windows-Resource) manuell synchron halten
und einen `vX.Y.Z – YYYY-MM-DD`-Eintrag in `CHANGELOG.md` ergänzen.

## Weitere Dokumentation

- `DOKUMENTATION.md` – ausführliche Architektur- und Bedienungs-Doku
- `CHANGELOG.md` – Versionshistorie
- `Bedienungsanleitung.html` / `Kurzanleitung.html` – Endbenutzer-Hilfen
