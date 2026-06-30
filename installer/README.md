# QAInput — Deployment via Installer (baramundi)

Ersetzt die portable Verteilung durch zwei Inno-Setup-Installer:

| Setup | Zweck | Lauf |
|-------|-------|------|
| **Client-Setup** (`QAInput-Setup-<ver>.exe`) | Thin Client (`QAInput.exe` + `_internal\` + `config.json`) nach `Program Files` | per baramundi auf jeden Client, silent |
| **Backend-Setup** (`QAInput-Backend-Setup-<ver>.exe`) | Datenstruktur + Startdateien auf dem Netzlaufwerk | einmalig durch IT-Admin, interaktiv |

Architektur: Der Client enthält **keine Daten**. Alle Daten- und Schreibpfade
(`users.kv`, Produkte, Templates, `app_config.json`, Audit, Log) liegen zentral
auf dem Netzlaufwerk und werden über die mitgelieferte `config.json` (UNC-Pfade)
aufgelöst. So gibt es genau eine Datenquelle (GMP).

## Voraussetzungen (Build-Rechner)

- Python 3.11+ mit `pyinstaller` (`pip install pyinstaller`)
- **Inno Setup 6** (`ISCC.exe` im PATH oder unter `…\Inno Setup 6\`)

## Bauen

```powershell
# Aus dem Repo-Root:
installer\build_installers.ps1
# optional mit Erreichbarkeits-Check der Netz-Wurzel im Client-Setup:
installer\build_installers.ps1 -CheckPath '\\SERVER\Freigabe\Produktion\14_QAInput'
```

Das Skript: baut PyInstaller (`build.bat`), liest die Version aus `src\version.py`,
staged die Seed-Struktur nach `installer\seed\` und kompiliert beide `.iss`.
Ergebnis liegt in `installer\Output\`.

## Vor dem ersten Rollout

1. **`config.client.json` anpassen:** `\\SERVER\Freigabe\…` durch den realen UNC-Pfad
   ersetzen. **UNC, kein Laufwerksbuchstabe** — baramundi installiert als SYSTEM-Konto,
   das keine benutzergemappten Laufwerke (`X:\`) sieht.
2. **Backend-Setup ausführen** (vor den Clients): legt die Ordnerstruktur an und
   seedet `app_config.json`, Produkte, Templates und eine `users.kv`-Vorlage
   (`onlyifdoesntexist` → überschreibt nichts).
3. **`users.kv` finalisieren:** Admin-Passwort der Vorlage ändern, reale Bediener
   anlegen (Format siehe `templates\users.kv.template`).
4. **Berechtigungen setzen** (siehe unten).

## baramundi: Silent-Install

```cmd
QAInput-Setup-<ver>.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG="C:\Temp\qainput_install.log"
```

- Erfolgsrückgabe: Exit 0.
- `/SKIPPATHCHECK` erzwingt die Installation trotz nicht erreichbarer Netz-Wurzel.
  Im Silent-Modus bricht das Setup ohnehin nicht hart ab (SYSTEM-Kontext sieht die
  Freigabe evtl. nicht); der **Runtime-Preflight** der App prüft die Pfade später
  im Benutzerkontext und meldet Probleme mit klarem Dialog.

## Berechtigungen (durch IT, ohne ACLs im Setup)

| Pfad | Recht für Bediener-Gruppe |
|------|---------------------------|
| `…\Audit`, `…\Log`, Excel-Output | Schreiben/Ändern |
| `…\Data\config`, `…\Data\products`, `…\Data\process_templates`, `…\Data\user` | Lesen |
| `…\Data\products` (nur Config-Editor-Nutzer) | Schreiben (Freigabe-Workflow) |

## Updates

- **Client-Update:** neue `QAInput-Setup-<ver>.exe` über baramundi verteilen.
  `config.json` am Client bleibt erhalten (`onlyifdoesntexist`).
- **Config-/Template-Update:** geänderte Dateien gezielt nach `…\Data\config` bzw.
  `…\Data\process_templates` kopieren. Das Backend-Setup ist idempotent und
  überschreibt **nichts** — für ein bewusstes Update die Dateien manuell ersetzen.
