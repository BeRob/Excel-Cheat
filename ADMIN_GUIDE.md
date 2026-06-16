# QAInput – Admin-Guide (kurz)

Stand: v1.9.0. Für Details siehe `DOKUMENTATION.md`, `CLAUDE.md`, `CONFIG_REFERENZ.md`.

## 1. Verzeichnisstruktur (Netzlaufwerk)

Die Exe liegt lokal je Arbeitsstation; **Daten zentral** auf einem Share. Pfade werden über `config.json` neben der Exe gesetzt (siehe `deployment/config.json`).

```
X:\Produktion\14_QAInput\
├─ QAInput\                     ← Exe-Ordner je Station (oder zentral, read-only gestartet)
│  ├─ QAInput.exe
│  ├─ _internal\               (PyInstaller-Laufzeit)
│  ├─ config.json              ← zeigt auf die Data-/Audit-/Log-Pfade unten
│  └─ data\                    (nur Fallback; im Betrieb kommt alles vom Share)
├─ Data\
│  ├─ user\                    users.kv (Benutzer, QR, Admin-Flag)
│  ├─ config\                  app_config.json (Schichten, freigabe_pflicht)
│  ├─ process_templates\       kanonische Feldstruktur je Operation
│  ├─ products\                <REF>.json (dünne Configs) + freigaben.json
│  └─ vorlagen\                freigabedokument.docx (optional)
├─ Audit\                      audit_log.jsonl (+ Tagesrotation .YYYY-MM-DD)
├─ Log\                        debug.log, error.log
├─ Freigabedokumente\          erzeugte Freigabe-PDFs/DOCX (das Papier ist der Record)
└─ Output\                     erzeugte Excel-Chargendateien (oder je Produkt anders)
```

**Wichtig:** `products` und `process_templates` gehören **zusammen** (dünne Configs lösen gegen die Templates auf) — beide zentral pflegen, nie nur eines.

## 2. NTFS-Berechtigungen (Minimum, GMP)

| Ordner | Werker | QA/Freigeber | Admin |
|---|---|---|---|
| `Data\process_templates`, `Data\products`, `Data\config` | Lesen | Lesen | Ändern |
| `Data\user` (users.kv) | Lesen* | – | Ändern |
| `Audit\` | **Schreiben/Anfügen, KEIN Löschen** | Lesen | Lesen (kein Löschen) |
| `Log\` | Schreiben | Lesen | Ändern |
| `Output\` | Ändern (Anfügen), **KEIN Löschen** | Lesen | Ändern |
| `Freigabedokumente\` | – | Lesen | Ändern |

\* users.kv enthält Passwörter im Klartext (gehärtetes Hashing ist offenes Backlog) — Leserechte so eng wie möglich; idealerweise QR-Login statt Passwort. Audit/Output bewusst **ohne Löschrecht** für Werker (ALCOA+: keine stille Löschung). „Kein Löschen" via NTFS: `Ändern` gewähren, `Löschen`/`Unterordner und Dateien löschen` explizit verweigern.

## 3. Deployment

1. Build erzeugen: im Build-Ordner `build.bat` ausführen → `dist\QAInput\`.
2. Inhalt von `dist\QAInput\` in den Exe-Ordner der Station kopieren (`QAInput.exe` + `_internal\` + `config.json` + lokaler `data\`-Fallback).
3. `config.json` auf die Share-Pfade zeigen lassen (Vorlage: `deployment/config.json`).
4. Zentral auf dem Share anlegen: `Data\process_templates\` (mitgeliefert), `Data\products\` (anfangs leer + `freigaben.json={}`), `Data\config\app_config.json`, `Data\user\users.kv`.
5. Erststart prüfen: Login, Produktauswahl (anfangs leer ist normal), Audit-Eintrag `app_start`/`config_loaded` im `Audit\`.

## 4. Produkt anlegen / ändern (Config-Editor, v1.9.0)

Der Editor ist template-basiert: Feld-IDs kommen immer aus dem gewählten **Operation-Template** (Dropdown), es gibt **keinen Freitext** für IDs mehr.

**Neues Produkt (Assistent):**
1. Tab „Produktkonfiguration" → **„Neu (Assistent)"**.
2. Produkt-ID (REF) + Anzeigename + optional Ausgabeverzeichnis eintragen.
3. **„+ Prozess"** → Operation wählen (z. B. Walzen). Vorausgewählt sind nur die Pflicht-Standardfelder (FA-Nr., LOT, Verwendbarkeitsdatum, Messmittel, Auto-Felder, Bemerkungen).
4. In der **Checkliste** die gemessenen Felder ankreuzen; Spec-Grenzen (min/soll/max) direkt in der Zeile eintragen. Seltenere Abweichungen über **„Bearbeiten"** je Feld. Produktunike Felder über **„Eigenes Feld hinzufügen…"**.
5. Weitere Prozesse anlegen, dann **„Übernehmen & schließen"** → im Haupteditor **„Speichern"** (Änderungsbeschreibung eingeben).

**Bestehendes Produkt ändern:** „Laden" → Prozess links wählen → Felder/Specs anpassen → „Speichern". Speichern erhöht die Revision und verlangt eine Änderungsbeschreibung. Der **`template_id`** (Excel-Dateiname + Resume-Schlüssel) darf nach den ersten Excel-Dateien **nie** mehr geändert werden — der Editor warnt. Alte Voll-Feld-Configs (ohne Template) werden beim Laden **blockiert**; solche Produkte über den Assistenten neu anlegen.

## 4a. Produkt-Freigabe (Vier-Augen, ohne E-Signatur)

Das **Status-Badge** oben im Editor zeigt: grün „freigegeben" / orange „geändert seit Freigabe" / grau „nicht freigegeben".

1. **Speichern** (s. o.).
2. **„Freigabedokument erzeugen…"** → DOCX (falls `vorlagen\freigabedokument.docx` vorhanden) bzw. HTML. Enthält SHA-256-Hash der Config. (Button ist nur bei gespeichertem Stand aktiv.)
3. **Unterschreiben** lassen: Prüfer ≠ Freigeber.
4. **„Freigabe erfassen…"** im Editor: Dokument-Nr. + Namen eintragen → Eintrag in `freigaben.json`, Badge wird grün.

Jede spätere Änderung der Config bricht den Hash → Badge wird orange, Produkt fällt automatisch aus dem Scope, bis neu freigegeben wird.

**Schalter `freigabe_pflicht`** in `app_config.json`: `true` = nur freigegebene Produkte wählbar (Zielzustand). `false` = Übergangsbetrieb (nicht freigegebene erscheinen mit ⚠). Nach Abschluss der Erst-Freigaben auf `true` setzen.

## 5. Betrieb

- **Templates ändern** wirkt auf alle Produkte, die sie nutzen → Freigaben brechen, neu freigeben. Erst testen (Übergangsbetrieb), dann scharf schalten.
- **Zeitzone:** alle Stationen auf dieselbe lokale Zeit/NTP synchronisieren (Audit-Rotation und Zeitstempel).
- **Backup:** `Audit\`, `Data\products\` (inkl. `freigaben.json`) und `Output\` regelmäßig sichern.
- **Stanzen / Ausschussplatten / Packliste:** Templates sind noch Auto-Generat-Entwürfe — vor Produktivnutzung dieser Operationen harmonisieren.
