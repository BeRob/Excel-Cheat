# QAInput -- Dokumentation

## Was macht diese Anwendung?

QAInput ist eine Desktop-Anwendung zur Erfassung von Messwerten in der Qualitätssicherung. Mitarbeiter melden sich an, wählen ein Produkt und einen Prozess aus, und geben dann Messwerte ein. Die Anwendung speichert alles in Excel-Dateien, die automatisch erstellt und benannt werden.

Die Grundidee: Statt manuell Excel-Vorlagen zu öffnen und Spalten zuzuordnen, wird alles über JSON-Konfigurationsdateien gesteuert. Ein neues Produkt hinzufügen bedeutet einfach: eine neue JSON-Datei in den `data/products/`-Ordner legen -- oder direkt im integrierten Admin-Editor anlegen. Kein Code ändern.

Seit v0.9.1 erfasst die Anwendung zusätzlich **Maschinenstörungen und Stillstandszeiten** (an Produkt/Prozess gebunden): der Bediener meldet eine Störung per Knopfdruck, die Technik behebt sie und gibt die Maschine wieder frei. Ein Admin-Tab wertet die Störungen aus (Verfügbarkeit, MTTR/MTBF, Zahlen je Station/Kategorie/Zeitraum) — siehe Abschnitt „Admin-Funktionen" und `CLAUDE.md`.

---

## Versionierung

Single Source of Truth für die Anwendungsversion ist `src/version.py` (`APP_VERSION_TUPLE`, `APP_VERSION`, `APP_VERSION_DATE`); `version_info.txt` (Windows-Ressource der exe) wird beim Versions-Bump manuell synchron gehalten. Der Audit-Trail schreibt die Version in jedes Event (Feld `app_version`).

**Versions-Neubasislinie (2026-06-30):** Mit v0.9.0 wurde die Zählung ausdrücklich von 1.9.0 auf **0.9.0** zurückgesetzt — ab dort zählt 0.9.x als aktuelle Pre-1.0-Linie (siehe CHANGELOG). Für Auswertungen des Audit-Trails bedeutet das: `app_version`-Werte 1.x stammen aus Events **vor** dem 2026-06-30 und liegen zeitlich VOR allen 0.9.x+-Events — die Versionsfolge im Log ist über diesen Punkt hinweg nicht numerisch monoton. Maßgeblich für die zeitliche Ordnung ist immer der `ts`-Zeitstempel des Events.

---

## Projektstruktur

```
QAInput/
|-- app.py                          Einstiegspunkt der Anwendung
|-- QUESTALPHA_StaticLogo_pos_rgb.png  Logo für die Kopfleiste
|-- build_exe.spec                  PyInstaller Build-Konfiguration
|-- data/
|   |-- app_config.json             Globale Einstellungen (Schichten, Freigabepflicht)
|   |-- process_templates/          Kanonische Feldstruktur je Operation (8 Dateien)
|   |   |-- Vorschneiden.json, Schaelen.json, ... (eine je Operation)
|   |-- products/
|   |   |-- <REF>.json              Dünne Produkt-Configs (template + active_fields + overrides)
|   |   |-- freigaben.json          Freigabe-Manifest (Vier-Augen, Hash-gebunden)
|   |-- vorlagen/
|   |   |-- freigabedokument.docx   (optional) Word-Vorlage fürs Freigabedokument
|   |-- users.kv                    Benutzerliste (Passwort, QR-Code, Name)
|-- src/
|   |-- audit/
|   |   |-- audit_logger.py         Audit-Trail (wer hat wann was gemacht)
|   |-- auth/
|   |   |-- login.py                Authentifizierung (Passwort + QR)
|   |   |-- users_kv.py             Parser für die Benutzerdatei
|   |-- config/
|   |   |-- settings.py             Feste Anwendungskonstanten (Pfade, Fenstergröße)
|   |   |-- process_config.py       Konfigurationssystem (JSON lesen, Datenklassen, Hilfsfunktionen)
|   |   |-- config_writer.py        Konfiguration schreiben (Datenklassen -> JSON, Validierung)
|   |-- domain/
|   |   |-- state.py                Zentraler Zustand der Anwendung (wer ist eingeloggt, was ist ausgewählt)
|   |   |-- validation.py           Validierung von Eingaben (Zahlenformate, Spec-Limits, Feldtypen)
|   |-- excel/
|   |   |-- creator.py              Excel-Dateien erstellen (Info-Header, Kopfzeile, Dateiname, Resume)
|   |   |-- reader.py               Excel-Dateien lesen (für die Analyse-Ansicht)
|   |   |-- writer.py               Messwert-Zeilen in Excel schreiben
|   |-- ui/
|       |-- base_view.py            Basisklasse für alle Bildschirme
|       |-- theme.py                Farben, Schriften, Styles (Questalpha-Design)
|       |-- login_view.py           Anmeldebildschirm
|       |-- product_process_view.py Produkt- und Prozessauswahl (inkl. Admin-Tabs)
|       |-- context_view.py         Feste Werte setzen (z.B. FA-Nr., LOT Nr.)
|       |-- form_view.py            Messwerterfassung (Hauptbildschirm)
|       |-- review_dialog.py        Prüfung vor dem Speichern
|       |-- analysis_view.py        Datenauswertung (nur für Admins)
|       |-- config_editor_view.py   Produktkonfigurations-Editor (nur für Admins)
|-- tests/
    |-- test_process_config.py      Tests für das Konfigurationssystem
    |-- test_config_writer.py       Tests für Serialisierung und Validierung
    |-- test_creator.py             Tests für die Excel-Erstellung
    |-- test_writer.py              Tests für den Excel-Writer
    |-- test_validation.py          Tests für die Eingabevalidierung
    |-- test_kv_parser.py           Tests für den Benutzer-Parser
```

---

## Ablauf in der Anwendung

```
Anmeldung --> Produkt/Prozess wählen --> Feste Werte setzen --> Messwerte erfassen
                                                                      |
                                                                      v
                                                               Prüfen + Senden
                                                                      |
                                                                      v
                                                            In Excel geschrieben
```

1. **Anmeldung** -- Mitarbeiter meldet sich mit Passwort oder QR-Handscanner an.
2. **Produkt/Prozess wählen** -- Produkt aus Dropdown wählen, dann den Prozess. Die App zeigt an, welche Felder erwartet werden und welche Spec-Limits gelten. Die Schicht wird automatisch anhand der Uhrzeit bestimmt.
3. **Feste Werte setzen** -- Werte wie FA-Nr. und LOT-Nr., die sich nicht bei jeder Messung ändern, werden hier einmal eingetragen und für alle folgenden Messungen beibehalten. Diese Werte werden auch in den Info-Header der Excel-Datei geschrieben.
4. **Messwerte erfassen** -- Der Hauptbildschirm. Hier gibt der Mitarbeiter die aktuellen Messwerte ein. Oben stehen die festen Werte in einem eigenen Block (editierbar, falls sich z.B. die LOT-Nr. ändert). Darunter die Messwert-Felder. Zahlenfelder prüfen sofort, ob der Wert innerhalb der Spec-Limits liegt (grün/rot). Optionale Felder wie "Bemerkungen" können leer bleiben.
5. **Prüfen und Senden** -- Vor dem Schreiben öffnet sich ein Dialog, der alle Werte noch einmal zusammenfasst. Fehler (z.B. ungültige Zahlen) blockieren das Senden. Warnungen (z.B. Wert außerhalb Spec) werden angezeigt, aber das Senden ist trotzdem möglich.

### Tastaturnavigation

Im Messwert-Bildschirm kann mit Tastatur navigiert werden:
- **Enter** oder **Pfeil runter** -- Springt zum nächsten Eingabefeld
- **Pfeil hoch** -- Springt zum vorherigen Eingabefeld
- **Tab** -- Standard-Tab-Navigation

---

## Admin-Funktionen

Admin-Benutzer (gekennzeichnet durch `admin=true` in `users.kv`) bekommen in der Produkt/Prozess-Ansicht vier Tabs statt einem:

1. **Produkt/Prozess** -- Die normale Auswahl-Ansicht (für alle Benutzer)
2. **Datenauswertung** -- Excel-Dateien öffnen und als Tabelle anzeigen
3. **Störungen / Auswertung** -- Erfasste Störungen/Stillstandszeiten filtern und auswerten (Verfügbarkeit, MTTR/MTBF, Zahlen je Station/Kategorie/Prozess; Excel-Export)
4. **Produktkonfiguration** -- Produkt-JSON-Dateien direkt in der App erstellen und bearbeiten

### Störungen / Auswertung

Liest den append-only Störungs-Store (`stoerungen.jsonl`) und zeigt eine Detailtabelle plus KPI-Kacheln. Filter: Zeitraum (Schnellwahl „letzte 2 Wochen"/„dieser Monat"), Produkt, Prozess, Station, Kategorie, Status (offen/behoben). Gruppierung nach Station/Kategorie/Prozess; Export der gefilterten Liste + Aggregate als `.xlsx`. **Verfügbarkeit** braucht eine Planzeit (vorgeschlagen aus Schichtlänge × aktiven Tagen, überschreibbar); MTTR/MTBF/Zählungen funktionieren ohne. Die fachliche Rechnung liegt Tk-frei in `src/downtime/downtime_query.py`. Die Bediener-Erfassung selbst läuft über das Störungsfenster aus dem Messwert-Bildschirm (`src/ui/downtime_window.py`).

### Produktkonfigurations-Editor

Der Editor ist **template-basiert**: Feld-IDs kommen immer aus einem gewählten Operation-Template, nicht mehr per Freitext. So verwalten Admins Produkte ohne manuelles JSON-Editieren und ohne Tippfehler:

- **Neu (Assistent)** -- Geführte Neuanlage: Produkt-ID + Anzeigename + Ausgabeverzeichnis, danach beliebig viele Prozessschritte (je Operation-Template wählen, Felder ankreuzen, Specs setzen). Der Assistent übergibt das fertige Produkt an den normalen Speicherpfad.
- **Laden / Kopieren** -- Bestehende dünne Produkte aus der Dropdown-Liste laden oder kopieren. Alte Voll-Feld-Configs ohne Template werden **blockiert** (per Assistent neu anlegen).
- **Prozesse verwalten** -- Hinzufügen (Operation wählen), entfernen, umsortieren. Pro Prozess: Operation (Template), `template_id` (Excel-/Resume-Schlüssel, mit Warnung gegen spätere Änderung), Anzeigename, **Standard-/Max-Anzahl Nutzen** (`row_group_size` — der Bediener wählt beim Prozessstart 1..Max).
- **Feld-Checkliste** -- Alle Template-Felder als Checkliste; anhaken = aktiv, Reihenfolge = Excel-Spaltenreihenfolge. Felder lassen sich per **Maus-Griff (⠿) ziehen** (↑/↓ als Alternative). Vorausgewählt sind nur die Pflicht-Standardfelder (Kopf-Felder, Kennungen, Auto-Felder, Bemerkungen). Spec-Grenzen (Min/Soll/Max) werden **inline** in der Zeile gesetzt; seltenere Abweichungen (Anzeigename, **`clone`** = je Nutzen/Bahn eigene Spalte, Default, Optional, info_header, Optionen) und die **Rolle** (Kontext/Kennung/Messwert/Auto) über den **Bearbeiten**-Dialog je Feld. Der Typ ist durch das Template fix.
- **Eigenes Feld hinzufügen…** -- Produktunike Felder mit voller Definition (freie ID + alle Attribute) → werden als `extra_fields` gespeichert.
- **Freigabe-Badge** -- Zeigt oben den Freigabe-Status (grün freigegeben / orange geändert / grau nicht freigegeben); die Freigabe-Buttons sind kontextabhängig aktiv.
- **Speichern** -- Validiert (Pflichtfelder, doppelte IDs, Spec-Grenzen, mindestens ein echter Messwert, Bemerkungen-Pflicht, Template vorhanden, eindeutige `template_id`), erhöht die Revision, verlangt eine Änderungsbeschreibung und schreibt die JSON-Datei dünn (atomar).

Die gespeicherten JSON-Dateien gehören mit `data/process_templates/` zusammen (dünne Configs lösen gegen die Templates auf) -- beide zusammen verteilen.

---

## Excel-Dateien

### Dateinamen

Die generierten Dateien heißen z.B.:

```
IPC1_Vorschneiden_REF31962_Schicht1_2026-04-02.xlsx
```

Format: `{Prozess-ID}_{Produkt-ID}_Schicht{1-3}_{Datum}.xlsx`

Wenn dieselbe Kombination am selben Tag in derselben Schicht erneut gestartet wird, findet die App die bestehende Datei und schreibt darin weiter (Resume).

### Aufbau der Excel-Datei

Jede Excel-Datei hat folgenden Aufbau:

| Zeile | Inhalt |
|-------|--------|
| 1 | **Produkt:** Anzeigename des Produkts |
| 2 | **Prozess:** Anzeigename des Prozesses |
| 3 | **FA-Nr.:** Fertigungsauftragsnummer |
| 4 | **Schicht:** 1, 2 oder 3 |
| 5 | **Datum:** Erstellungsdatum |
| 6 | Spalten-Kopfzeile (Feldnamen) |
| 7+ | Messdaten |

Die Zeilen 1-5 bilden den Info-Header-Block. Er wird beim ersten Setzen der festen Werte geschrieben und bei Änderung (z.B. "Kontext ändern") aktualisiert.

### Ausgabeverzeichnis

Das Ausgabeverzeichnis wird in dieser Reihenfolge bestimmt:

1. **Pro Produkt** -- Im Feld `output_dir` der Produkt-JSON-Datei (absoluter Pfad oder relativ zum Anwendungsverzeichnis)
2. **Ordner-Dialog** -- Wenn `output_dir` leer ist, erscheint beim Prozessstart ein Ordner-Auswahl-Dialog

Es gibt kein globales Fallback-Verzeichnis mehr. Produkte ohne `output_dir` fordern den Bediener beim Start aktiv zur Auswahl auf.

---

## Dateien im Detail

### `app.py` -- Einstiegspunkt

Erstellt das Tkinter-Hauptfenster, lädt die Konfiguration, und verwaltet die Navigation zwischen den vier Bildschirmen (Login, Produkt/Prozess, Kontext, Formular). Die Navigation funktioniert über gestapelte Frames -- alle Views werden beim Start erzeugt und per `tkraise()` in den Vordergrund gebracht.

Oben im Fenster ist eine Leiste mit dem Questalpha-Logo (als PNG geladen) und einem Hilfe-Button.

### `data/app_config.json` -- Globale Einstellungen

Definiert das Ausgabeverzeichnis und die Schichten:

```json
{
  "output_dir": "output",
  "shifts": [
    {"name": "1", "start_hour": 6, "end_hour": 14},
    {"name": "2", "start_hour": 14, "end_hour": 22},
    {"name": "3", "start_hour": 22, "end_hour": 6}
  ]
}
```

Schicht 3 ist die Nachtschicht und geht über Mitternacht. Die App erkennt das: Wer um 3 Uhr nachts arbeitet, ist noch in Schicht 3 vom Vortag.

### `data/products/REF31962.json` -- Produktkonfiguration

Jedes Produkt hat eine eigene JSON-Datei. Diese definiert alle Prozesse (IPC1 bis IPC5) und für jeden Prozess die Felder mit ihren Eigenschaften:

- **id** -- Technischer Bezeichner (z.B. `"breite_1"`)
- **display_name** -- Anzeigename (z.B. `"Breite 1"`)
- **type** -- `"text"`, `"number"` oder `"choice"` (Dropdown)
- **role** -- `"context"` (Kontext), `"measurement"` (Messwert) oder `"auto"` (automatisch)
- **persistent** -- `true` wenn der Wert über mehrere Messungen gleich bleibt (z.B. FA-Nr., LOT Nr., Messmittel)
- **spec_min/spec_max/spec_target** -- Spezifikationsgrenzen und Zielwert für Zahlenfelder
- **options** -- Auswahlliste für Choice-Felder (z.B. `["Ja", "Nein"]`)
- **optional** -- `true` wenn das Feld leer bleiben darf
- **default_value** -- Standardwert, mit dem das Feld vorausgefüllt wird (z.B. `"n/a"` für Bemerkungen); wird nach jeder Messung wiederhergestellt

Optionales Top-Level-Feld:
- **output_dir** -- Ausgabeverzeichnis für dieses Produkt (überschreibt den globalen Wert)

Besonderheiten einzelner Prozesse:
- **IPC2 Schaelen** hat `clone`-Felder (je Nutzen/Bahn) und `row_group_size: 3` (Standard-/Max-Anzahl). Der Bediener wählt beim Prozessstart die Anzahl Nutzen (1..3); im **Wide-Format** bekommt jedes Clone-Feld je Nutzen eine eigene Spalte ("Schichtdicke Nutzen 1", "Schichtdicke Nutzen 2", …) — eine Zeile je Messung. Beim Fortsetzen wird die Anzahl aus der Datei gelesen.
- **IPC4 Stanzen** hat ein Auto-Feld "Prüfmuster", das bei jeder Messung hochzählt.

Standard-Kontextfelder in allen Prozessen beider Produkte (persistent):
- **FA-Nr.** -- Fertigungsauftragsnummer
- **LOT Nr.** -- Losnummer
- **Messmittel** -- Verwendetes Messinstrument
- **Verwendbarkeitsdatum** -- Verfallsdatum des Messmittels

Um ein neues Produkt hinzuzufügen gibt es zwei Wege:
1. **Admin-Editor** -- Im Tab "Produktkonfiguration" direkt in der App anlegen
2. **Manuell** -- Eine neue JSON-Datei nach dem gleichen Schema in `data/products/` legen

Die App findet neue Produkte beim nächsten Start (oder nach dem Speichern im Editor) automatisch.

### `src/config/process_config.py` -- Konfigurationssystem

Das Herzstück der Konfiguration. Definiert fünf Datenklassen:

- **FieldDef** -- Ein einzelnes Feld (Name, Typ, Rolle, Spec-Limits, etc.)
- **ProcessConfig** -- Ein Prozess mit seinen Feldern und optionaler Zeilengruppierung
- **ProductConfig** -- Ein Produkt mit seinen Prozessen und optionalem Ausgabeverzeichnis
- **ShiftDef** -- Eine Schichtdefinition (Name, Start, Ende)
- **AppConfig** -- Alles zusammen: Produkte, Schichten, Ausgabeverzeichnis

Ladefunktionen:
- `load_app_config()` -- Liest `app_config.json` und scannt den `products/`-Ordner
- `load_product_config()` -- Liest eine einzelne Produkt-JSON-Datei

Hilfsfunktionen zum Filtern von Feldern nach Rolle:
- `get_context_fields()` -- Alle Kontext-Felder
- `get_persistent_context_fields()` -- Kontext-Felder, die über Messungen bestehen bleiben
- `get_per_measurement_context_fields()` -- Kontext-Felder, die sich pro Messung ändern
- `get_measurement_fields()` -- Alle Messwert-Felder
- `get_auto_fields()` -- Automatisch befüllte Felder
- `get_all_headers()` -- Anzeigenamen aller Felder in Reihenfolge (für die Excel-Kopfzeile)
- `get_field_by_id()` -- Feld anhand der technischen ID suchen
- `determine_shift()` -- Schicht anhand der aktuellen Stunde bestimmen (mit Mitternachts-Logik)

### `src/config/config_writer.py` -- Konfiguration schreiben

Gegenstück zu `process_config.py`: Konvertiert die Datenklassen zurück in JSON-Dicts und schreibt sie als Datei. Wird vom Admin-Editor benutzt.

- `field_to_dict()` / `process_to_dict()` / `product_to_dict()` -- Serialisierung
- `validate_product_config()` -- Prüft: Pflichtfelder ausgefüllt, IDs eindeutig, Spec-Grenzen logisch, Choice-Felder mit Optionen. Gibt eine Liste von Fehlertexten zurück (leer = alles OK)
- `save_product_config()` -- Schreibt die JSON-Datei in den Produkt-Ordner

### `src/config/settings.py` -- Pfade und Konstanten

Löst alle Dateisystempfade zur Laufzeit auf. Priorität je Verzeichnis:

1. Umgebungsvariable (`QAINPUT_USERS_DIR`, `QAINPUT_CONFIG_DIR`, `QAINPUT_PRODUCTS_DIR`, `QAINPUT_AUDIT_DIR`)
2. Bootstrap-Datei `config.json` neben der exe mit Schlüsseln `users_dir`, `config_dir`, `products_dir`, `audit_dir`
3. Standard: Unterordner von `<APP_ROOT>/data`

Exportierte Konstanten: `USERS_DIR`, `CONFIG_DIR`, `PRODUCTS_DIR`, `AUDIT_DIR`, `USERS_KV_PATH`, `APP_CONFIG_PATH`, `AUDIT_LOG_PATH`, `HEADER_ROW`, Fenstertitel und -größe.

### `src/domain/state.py` -- Anwendungszustand

Die zentrale `AppState`-Klasse hält alles, was die App gerade weiß:

- Wer ist eingeloggt? (`current_user`)
- Welche Konfiguration ist geladen? (`app_config`)
- Was ist ausgewählt? (`selected_product`, `selected_process`, `current_shift`)
- In welche Datei wird geschrieben? (`current_file`)
- Welche festen Werte sind gesetzt? (`persistent_values`)
- Wo stehen die Zähler? (`row_group_counter`, `auto_sequence`)

Die `reset_*`-Methoden sorgen dafür, dass beim Zurücknavigieren alles sauber zurückgesetzt wird -- in der richtigen Reihenfolge (User -> Product -> Process -> Context).

### `src/domain/validation.py` -- Eingabevalidierung

Validiert Benutzereingaben vor dem Schreiben. Drei Stufen:

1. **Dezimal-Normalisierung** -- Erkennt automatisch deutsches (`3,14`) und englisches (`3.14`) Zahlenformat. Auch gemischte Formate wie `1.250,5` (deutsch für 1250,5) werden korrekt geparst.

2. **Typbasierte Validierung** (mit FieldDefs):
   - `number` -- Muss eine gültige Zahl sein. Spec-Limits erzeugen Warnungen (keine Fehler), weil der Bediener bewusst außerhalb der Spec messen kann.
   - `choice` -- Muss eine der definierten Optionen sein.
   - `text` -- Wird durchgereicht ohne Prüfung.

3. **Fallback** (ohne FieldDefs) -- Alles wird als Zahl behandelt. Das ist die Rückwärtskompatibilität für Code, der noch keine Konfiguration verwendet.

Leere Felder erzeugen eine Warnung, außer sie sind als `optional` markiert. Fehler blockieren das Speichern, Warnungen nicht.

### `src/excel/creator.py` -- Excel-Dateien erstellen

Kümmert sich um die Erstellung und das Auffinden von Excel-Dateien:

- `generate_file_name()` -- Erzeugt den Dateinamen: `{Prozess}_{Produkt}_Schicht{X}_{Datum}.xlsx`
- `get_shift_date()` -- Bestimmt das Datum für den Dateinamen. Wichtig: Wer nach Mitternacht in Schicht 3 arbeitet, bekommt das Datum des Vortages (weil die Schicht vor Mitternacht begann).
- `find_existing_file()` -- Sucht, ob es für diese Kombination aus Produkt/Prozess/Schicht/Datum schon eine Datei gibt (für Resume nach App-Neustart).
- `create_measurement_file()` -- Erstellt eine neue Excel-Datei mit Kopfzeile in Zeile 6 (nach dem Info-Header).
- `write_info_header()` -- Schreibt den Info-Header (Zeilen 1-5) mit Produkt, Prozess, FA-Nr., Schicht und Datum.
- `count_data_rows()` -- Zählt vorhandene Datenzeilen (für die Initialisierung der Zähler beim Resume).

### `src/excel/reader.py` -- Excel lesen

Liest Daten aus bestehenden Excel-Dateien. Wird nur von der Analyse-Ansicht genutzt (Admin-Funktion). Kann Header lesen, Spalten-Maps erstellen, und alle Daten als Liste von Dictionaries zurückgeben.

### `src/excel/writer.py` -- Messwerte schreiben

Hängt eine neue Zeile an eine bestehende Excel-Datei an. Die Spaltenreihenfolge wird aus der Prozesskonfiguration abgeleitet -- Feld 1 in Spalte 1, Feld 2 in Spalte 2, etc.

Nimmt drei getrennte Wert-Dictionaries entgegen (Kontext, Messwerte, Auto-Werte), führt sie zusammen und schreibt sie in die richtige Spalte. Gibt ein `WriteResult` zurück, das Erfolg/Fehler signalisiert.

Fehlerbehandlung: Wenn die Datei gesperrt ist (z.B. in Excel geöffnet), gibt es eine klare Fehlermeldung.

### `src/audit/audit_logger.py` -- Audit-Trail

Schreibt strukturierte Events als JSON-Zeilen in eine Logdatei (`data/audit_log.jsonl`). Jeder Eintrag hat einen Zeitstempel, einen Event-Typ und optionale Details. Wird bei jeder relevanten Aktion aufgerufen: Login, Prozessauswahl, Kontext setzen, Schreiben (Versuch, Erfolg, Fehler).

Fehler beim Schreiben des Logs werden abgefangen und auf stderr ausgegeben -- das Audit-Log darf nie die eigentliche Arbeit blockieren.

### `src/auth/login.py` -- Authentifizierung

Bietet zwei Anmeldemethoden:
- **Passwort** -- Benutzername + Passwort prüfen
- **QR-Code** -- Ein Handscanner scannt einen QR-Code, die App sucht den passenden Benutzer

Gibt ein `UserInfo`-Objekt zurück (mit User-ID, Anzeigename und Admin-Flag) oder `None` bei fehlgeschlagener Anmeldung.

### `src/auth/users_kv.py` -- Benutzerdatei-Parser

Liest die Benutzerliste aus einer einfachen Key-Value-Datei. Format:

```
user.max.password=1234
user.max.qr=QR-MAX
user.max.name=Max Mustermann
user.max.admin=true
```

Kommentare (mit `#`) und Leerzeilen werden ignoriert. Fehlerhafte Zeilen werden übersprungen.

### `src/ui/base_view.py` -- Basis für alle Bildschirme

Abstrakte Basisklasse. Jede View bekommt den `AppState` und eine `on_navigate`-Funktion. Bietet `on_show()` und `on_hide()` zum Überschreiben -- damit können Views reagieren, wenn sie sichtbar oder unsichtbar werden.

### `src/ui/theme.py` -- Design

Definiert Farben, Schriften und ttk-Styles für die gesamte Anwendung. Das Design orientiert sich am Questalpha-Branding:
- Weißer Hintergrund
- Dunkle Schrift (`#1B2023`)
- Blaue Akzentfarbe (`#0070BB`)
- Helle Oberflächen (`#F0F3F5`)

Alle UI-Elemente (Buttons, Labels, Eingabefelder, Tabs) werden hier zentral gestylt.

### `src/ui/login_view.py` -- Anmeldung

Zwei Tabs: Passwort-Login und QR-Code-Login. Im Passwort-Tab springt Enter vom Benutzernamen zum Passwortfeld und löst dann die Anmeldung aus. Der QR-Tab reagiert auf die Enter-Taste (Handscanner senden Enter nach dem Scan). Nach erfolgreicher Anmeldung geht es weiter zur Produkt/Prozess-Auswahl.

### `src/ui/product_process_view.py` -- Produkt/Prozess-Auswahl

Zwei Dropdown-Felder: Produkt wählen, dann Prozess wählen. Bei Auswahl eines Prozesses erscheint eine Übersicht der Felder (welche Kontext-Felder, welche Messwerte mit Spec-Limits, welche Auto-Felder).

Die Schicht wird automatisch angezeigt. Beim Klick auf "Weiter" passiert einiges:
- Schicht und Datum werden bestimmt
- Das Ausgabeverzeichnis wird aufgelöst (Produkt-spezifisch oder global)
- Die App sucht nach einer bestehenden Datei für diese Kombination (Resume)
- Wenn keine existiert, wird eine neue erstellt
- Zähler werden initialisiert (Nutzen, Prüfmuster)
- Der AppState wird aktualisiert

Für Admin-Benutzer gibt es zwei zusätzliche Tabs: "Datenauswertung" und "Produktkonfiguration".

### `src/ui/context_view.py` -- Feste Werte

Zeigt Eingabefelder für die persistenten Kontext-Felder (z.B. FA-Nr., LOT Nr.). Wenn ein Prozess keine persistenten Felder hat, zeigt die View einen Hinweis und lässt direkt weiter navigieren.

Die Felder werden dynamisch generiert, basierend auf der Prozesskonfiguration. Choice-Felder bekommen ein Dropdown, Text-Felder ein normales Eingabefeld. Vorherige Werte werden vorausgefüllt.

Nach dem Setzen der Werte wird der Info-Header der Excel-Datei geschrieben (Produkt, Prozess, FA-Nr., Schicht, Datum).

### `src/ui/form_view.py` -- Messwerterfassung

Der Hauptbildschirm. Zeigt zwei getrennte Blöcke:

1. **Feste Werte** (LabelFrame "Feste Werte") -- Die persistenten Kontext-Felder (z.B. FA-Nr., LOT Nr.) werden hier editierbar angezeigt. Änderungen werden beim Speichern übernommen.
2. **Messwerte** (LabelFrame "Messwerte") -- Eingabefelder für alle pro-Messung-Kontext-Felder und Messwert-Felder.

Zwei Layouts: vertikal (untereinander) und horizontal (Gitter mit 4 Spalten), umschaltbar per Button.

Besonderheiten:
- **Tastaturnavigation**: Enter/Pfeil-runter springt zum nächsten Feld, Pfeil-hoch zum vorherigen.
- **Spec-Feedback**: Zahlenfelder prüfen beim Verlassen, ob der Wert innerhalb der Spec-Limits liegt. Grüne Schrift = OK, rote Schrift = außerhalb.
- **Scroll-Begrenzung**: Die Felder können nicht über den sichtbaren Bereich hinaus gescrollt werden. Die Scrollbar wird ausgeblendet, wenn der gesamte Inhalt sichtbar ist.
- **Row-Group-Anzeige**: Bei Prozessen mit Zeilengruppen (z.B. IPC2 mit 3 Nutzen) zeigt ein Label "Nutzen: 2 von 3" an.
- **History**: Die letzten 10 Messungen werden in einer Tabelle am unteren Rand angezeigt.
- **Auto-Werte**: Datum, Bearbeiter, Nutzen und Prüfmuster werden automatisch berechnet.
- **Rollback**: Wenn das Schreiben fehlschlägt, wird der Prüfmuster-Zähler zurückgesetzt.

### `src/ui/review_dialog.py` -- Prüfung vor dem Speichern

Ein modaler Dialog, der alle Werte zusammenfasst bevor sie geschrieben werden. Zeigt:
- Produkt, Prozess, Schicht und Datei
- Feste Werte (Kontext)
- Automatische Felder (Datum, Bearbeiter, Nutzen)
- Alle Messwerte mit Farbmarkierung (grün = OK, gelb = Warnung, rot = Fehler)
- Spec-Bereiche neben den Werten

Fehler blockieren den Senden-Button. Warnungen erlauben das Senden, werden aber deutlich angezeigt.

### `src/ui/analysis_view.py` -- Datenauswertung

Nur für Admins zugänglich (als Tab in der Produkt/Prozess-Ansicht). Lässt eine Excel-Datei öffnen und zeigt deren Daten in einer scrollbaren Tabelle an.

### `src/downtime/` -- Störungs-/Stillstandserfassung

- **downtime_store.py** (`DowntimeStore`) -- Append-only JSONL-Store `stoerungen.jsonl` (eigener GMP-Record, getrennt vom Audit-Log) mit Inter-Prozess-Lock, lokalem Fallback und Replay nach dem `AuditLogger`-Muster. Je Störung zwei Zeilen (`stoerung_start`/`stoerung_ende`), gepaart über `id`.
- **downtime_models.py** -- `Stoerung`-Dataclass (Start+Ende, `computed_dauer_sekunden`), `StoerungsCodes` + `load_stoerungs_codes` (zweistufige Fehler-Code-Liste mit eingebauter Default-Taxonomie).
- **downtime_query.py** -- Tk-frei und unit-getestet: `pair_stoerungen`, `find_open`, `filter_stoerungen`, `aggregate_by_station/kategorie/prozess`, `mttr`, `mtbf`, `verfuegbarkeit`.

### `src/ui/downtime_window.py` -- Störungsfenster

Ein modaler Dialog (`StoerungFenster`), geöffnet über den Button „⚠ Störung / Stillstand" in der FormView-Action-Bar. Zeigt je nach offener Störung den **Erfassungs**- (Kategorie → Ursache, Station, Beschreibung) oder den **Freigabe**-Abschnitt (Technikername + Behebung, beide Pflicht; ohne Re-Authentifizierung). Schreibt in den `DowntimeStore` und loggt ein Audit-Breadcrumb. `FormView` rekonstruiert eine offene Störung beim Anzeigen aus dem Store (überlebt Logout/Neustart).

### `src/ui/downtime_report_view.py` -- Störungs-Auswertung

Nur für Admins (Tab „Störungen / Auswertung"). Siehe Abschnitt „Admin-Funktionen".

### `src/ui/config_editor_view.py` -- Produktkonfigurations-Editor

Nur für Admins zugänglich (als Tab in der Produkt/Prozess-Ansicht). Enthält zwei Klassen:

- **ConfigEditorView** -- Der Haupteditor mit Produkt-Auswahl, Prozessliste und Freigabe-Badge
- **ProcessEditorPanel** -- Geteilte Per-Prozess-Komponente (Editor + Assistent): Operation-Dropdown, `template_id`, Feld-Checkliste mit Inline-Specs
- **FieldOverrideDialog** -- Override-Editor für ein Template-Feld (Rolle, Anzeigename, `clone`, Default, Optional, machine_scoped, info_header, Optionen; Typ fix)
- **FieldEditorDialog** -- Voll-Editor für produktunike Felder (`extra_fields`): freie ID + alle Attribute inkl. Datum-Typ
- **NewProductWizard** -- Geführte Neuanlage neuer Produkte

Die nicht-triviale Logik liegt Tk-frei in `src/config/config_editing.py` (unit-getestet). Der Editor validiert vor dem Speichern, schreibt dünn zurück und aktualisiert die App-Konfiguration sofort nach dem Schreiben.

---

## Schichtlogik

| Schicht | Zeitraum | Besonderheit |
|---------|----------|--------------|
| 1       | 06:00 - 14:00 | -- |
| 2       | 14:00 - 22:00 | -- |
| 3       | 22:00 - 06:00 | Geht über Mitternacht. Wer um 3 Uhr nachts arbeitet, bekommt das Datum des Vortages im Dateinamen. |

---

## Tests

Die Tests nutzen `unittest` und können so ausgeführt werden:

```bash
python -m unittest discover -s tests -v
```

### test_process_config.py (22 Tests)

Testet das komplette Konfigurationssystem:
- Feld-Filterfunktionen (context/persistent/measurement/auto)
- Schichtbestimmung zu verschiedenen Uhrzeiten (auch Mitternachts-Übergang)
- JSON-Laden mit Defaults und Sonderoptionen (row_group_size, output_dir)
- Template-Auflösung dünner Configs + Multi-Nutzen-Erkennung (`is_multi_nutzen`)
- `test_wide_format.py` -- Wide-Format: Clone-Spalten-Expansion, group_shared→clone-Kompat, identifier-Rolle, Schreib-/Resume-Roundtrip
- Stand: 275 Tests gesamt (alle Suiten zusammen), alle grün

### test_config_writer.py (26 Tests)

Testet Serialisierung und Validierung:
- Konvertierung von Feldern, Prozessen und Produkten in JSON-Dicts
- Roundtrip-Test: Serialisieren -> JSON schreiben -> wieder parsen -> vergleichen
- Validierungsregeln: leere IDs, doppelte IDs, ungültige Typen/Rollen, Spec-Grenzen, Choice-Optionen
- Datei erstellen, überschreiben, Verzeichnis anlegen

### test_creator.py (14 Tests)

Testet die Excel-Erstellung:
- Dateinamengenerierung
- Datumszuordnung für Nachtschicht
- Datei erstellen mit korrekter Kopfzeile in Zeile 9
- Info-Header schreiben (Zeilen 1-12)
- Bestehende Dateien finden
- Datenzeilen zählen (für Resume; wirft bei Lesefehlern)
- Atomares Schreiben + Header-Validierung (`test_writer.py`)

### test_writer.py (6 Tests)

Testet das Schreiben von Messwerten:
- Zeile wird angehängt (ab Zeile 10)
- Werte landen in der richtigen Spalte
- Zwei aufeinanderfolgende Schreibvorgänge
- Fehlerbehandlung bei fehlender Datei
- None-Werte werden übersprungen

### test_validation.py (28 Tests)

Testet die Eingabevalidierung:
- Dezimal-Normalisierung (deutsches/englisches Format)
- Numerisches Parsing
- Validierung ohne Felddefinitionen (Legacy-Modus)
- Typbasierte Validierung (number mit Spec-Limits, choice mit Optionsprüfung, text)
- Optionale vs. Pflichtfelder

### test_kv_parser.py (7 Tests)

Testet den Benutzerdatei-Parser:
- Einzelne und mehrere Benutzer
- Kommentare und Leerzeilen
- Sonderzeichen in Werten
- Fehlerhafte Zeilen

### test_downtime_models.py / test_downtime_store.py / test_downtime_query.py (34 Tests)

Testet die Störungserfassung (Tk-frei):
- Fehler-Code-Liste laden (gültig / fehlend / fehlerhaft → Default-Taxonomie)
- `Stoerung`-Modell: offen/behoben, Dauer-Berechnung aus Zeitstempeln
- Store: Append/Read-Roundtrip, ungültige Zeilen überspringen, Start/Ende-Paarung
- Query: `find_open` (Kontext + Maschine), Filter (Zeitraum/Station/Kategorie/Status), Aggregation je Station/Kategorie, MTTR/MTBF/Verfügbarkeit gegen handgerechnete Fälle

---

## Ein neues Produkt hinzufügen (mit Vier-Augen-Freigabe)

Die Produkt-Configs sind **dünn**: Sie referenzieren die Feldstruktur einer Operation aus `data/process_templates/<Operation>.json` (`template` + `active_fields`) und tragen nur Abweichungen (`field_overrides`, z.B. produktspezifische Spec-Grenzen, und `extra_fields`). Nur **freigegebene** Configs sind in der App wählbar.

### Schritt 1: Config anlegen oder ändern (Admin-Editor)

1. Als Admin anmelden, Tab "Produktkonfiguration" öffnen
2. "Neu" klicken — oder besser: ein bestehendes Produkt mit "Kopieren" als Vorlage nehmen (Kopien behalten die Template-Verknüpfung)
3. Produkt-ID, Anzeigename, Prozesse und Felder definieren
4. "Speichern" — die App erhöht die Revision automatisch und fragt eine Änderungsbeschreibung für die Revisionshistorie ab

### Schritt 2: Freigabedokument erzeugen und unterschreiben

Im Admin-Editor **"Freigabedokument erzeugen…"** klicken (alternativ: `python scripts\make_freigabedokument.py REF12345`). Das Dokument landet in `data/freigabedokumente/` und enthält alle aufgelösten Felder und Spec-Grenzen, die Revisionshistorie und den **SHA-256-Hash** der Config-Datei.

Liegt eine **Word-Vorlage** unter `data/vorlagen/freigabedokument.docx`, wird sie befüllt — damit sieht jedes Freigabedokument exakt gleich aus (Corporate Design, feste Abschnitte). Die Vorlage ist eine normale Word-Datei mit Platzhaltern wie `{{PRODUKT_ID}}`, `{{SHA256}}` oder `{{FELD_ID}}` (vollständige Liste: `CONFIG_REFERENZ.md`, Abschnitt 8). Ohne Vorlage entsteht ein HTML mit festem Standard-Layout.

Ausdrucken, fachlich prüfen lassen und von **zwei verschiedenen Personen** unterschreiben (Geprüft / Freigegeben — Vier-Augen-Prinzip). Das unterschriebene Papier ist der Freigabe-Nachweis.

### Schritt 3: Freigabe in der App erfassen

Im Admin-Editor "Freigabe erfassen…" klicken, Dokument-Nr. und die Namen vom unterschriebenen Dokument eintragen. Die App berechnet den Datei-Hash selbst und trägt die Freigabe in `data/products/freigaben.json` ein (Audit-Event `config_released`). Erst danach erscheint das Produkt in der Produktauswahl.

**Wichtig:** Jede spätere Änderung an der Config-Datei (auch außerhalb der App) ändert den Hash — das Produkt fällt automatisch aus dem Scope, bis eine neue Freigabe erteilt und erfasst ist. Der Schalter `"freigabe_pflicht"` in `data/app_config.json` steuert die Härte: `true` (Default) blendet nicht freigegebene Produkte aus, `false` (Übergangsbetrieb) zeigt sie mit ⚠-Warnung an.

### Verteilung auf andere Rechner

Den kompletten Ordner `data/products/` (Configs **und** `freigaben.json`) sowie `data/process_templates/` auf den Zielrechner kopieren. Beim nächsten Start der App wird das Produkt automatisch erkannt — inklusive Freigabe-Status.

---

## Abhängigkeiten

- **Python 3.11+** (nutzt `X | Y`-Union-Syntax via `from __future__ import annotations`)
- **openpyxl** -- Excel-Dateien lesen und schreiben
- **tkinter** -- GUI (in Python enthalten)

---

## Build (Windows EXE)

Der Build läuft aus dem `deployment/`-Ordner:

```bat
cd deployment
build.bat
```

`build.bat` bereinigt alte Artefakte, ruft PyInstaller mit `build_exe.spec` auf, kopiert `data/app_config.json` und `data/products/` in das Output-Verzeichnis und legt `config.json` neben die exe.

Ausgabe: `deployment/dist/QAInput/` -- dieser Ordner wird auf den Produktionsserver kopiert.

Für Entwicklung (direkter Start):

```bash
python app.py
```
