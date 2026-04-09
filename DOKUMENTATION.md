# QAInput -- Dokumentation

## Was macht diese Anwendung?

QAInput ist eine Desktop-Anwendung zur Erfassung von Messwerten in der Qualitaetssicherung. Mitarbeiter melden sich an, waehlen ein Produkt und einen Prozess aus, und geben dann Messwerte ein. Die Anwendung speichert alles in Excel-Dateien, die automatisch erstellt und benannt werden.

Die Grundidee: Statt manuell Excel-Vorlagen zu oeffnen und Spalten zuzuordnen, wird alles ueber JSON-Konfigurationsdateien gesteuert. Ein neues Produkt hinzufuegen bedeutet einfach: eine neue JSON-Datei in den `data/products/`-Ordner legen -- oder direkt im integrierten Admin-Editor anlegen. Kein Code aendern.

---

## Projektstruktur

```
QAInput/
|-- app.py                          Einstiegspunkt der Anwendung
|-- QUESTALPHA_StaticLogo_pos_rgb.png  Logo fuer die Kopfleiste
|-- build_exe.spec                  PyInstaller Build-Konfiguration
|-- data/
|   |-- app_config.json             Globale Einstellungen (Schichten, Ausgabeverzeichnis)
|   |-- products/
|   |   |-- REF31962.json           Produktkonfiguration mit allen Prozessen
|   |   |-- (weitere Produkte...)
|   |-- users.kv                    Benutzerliste (Passwort, QR-Code, Name)
|-- src/
|   |-- audit/
|   |   |-- audit_logger.py         Audit-Trail (wer hat wann was gemacht)
|   |-- auth/
|   |   |-- login.py                Authentifizierung (Passwort + QR)
|   |   |-- users_kv.py             Parser fuer die Benutzerdatei
|   |-- config/
|   |   |-- settings.py             Feste Anwendungskonstanten (Pfade, Fenstergroesse)
|   |   |-- process_config.py       Konfigurationssystem (JSON lesen, Datenklassen, Hilfsfunktionen)
|   |   |-- config_writer.py        Konfiguration schreiben (Datenklassen -> JSON, Validierung)
|   |-- domain/
|   |   |-- state.py                Zentraler Zustand der Anwendung (wer ist eingeloggt, was ist ausgewaehlt)
|   |   |-- validation.py           Validierung von Eingaben (Zahlenformate, Spec-Limits, Feldtypen)
|   |-- excel/
|   |   |-- creator.py              Excel-Dateien erstellen (Info-Header, Kopfzeile, Dateiname, Resume)
|   |   |-- reader.py               Excel-Dateien lesen (fuer die Analyse-Ansicht)
|   |   |-- writer.py               Messwert-Zeilen in Excel schreiben
|   |-- ui/
|       |-- base_view.py            Basisklasse fuer alle Bildschirme
|       |-- theme.py                Farben, Schriften, Styles (Questalpha-Design)
|       |-- login_view.py           Anmeldebildschirm
|       |-- product_process_view.py Produkt- und Prozessauswahl (inkl. Admin-Tabs)
|       |-- context_view.py         Feste Werte setzen (z.B. FA-Nr., LOT Nr.)
|       |-- form_view.py            Messwerterfassung (Hauptbildschirm)
|       |-- review_dialog.py        Pruefung vor dem Speichern
|       |-- analysis_view.py        Datenauswertung (nur fuer Admins)
|       |-- config_editor_view.py   Produktkonfigurations-Editor (nur fuer Admins)
|-- tests/
    |-- test_process_config.py      Tests fuer das Konfigurationssystem
    |-- test_config_writer.py       Tests fuer Serialisierung und Validierung
    |-- test_creator.py             Tests fuer die Excel-Erstellung
    |-- test_writer.py              Tests fuer den Excel-Writer
    |-- test_validation.py          Tests fuer die Eingabevalidierung
    |-- test_kv_parser.py           Tests fuer den Benutzer-Parser
```

---

## Ablauf in der Anwendung

```
Anmeldung --> Produkt/Prozess waehlen --> Feste Werte setzen --> Messwerte erfassen
                                                                      |
                                                                      v
                                                               Pruefen + Senden
                                                                      |
                                                                      v
                                                            In Excel geschrieben
```

1. **Anmeldung** -- Mitarbeiter meldet sich mit Passwort oder QR-Handscanner an.
2. **Produkt/Prozess waehlen** -- Produkt aus Dropdown waehlen, dann den Prozess. Die App zeigt an, welche Felder erwartet werden und welche Spec-Limits gelten. Die Schicht wird automatisch anhand der Uhrzeit bestimmt.
3. **Feste Werte setzen** -- Werte wie FA-Nr. und LOT-Nr., die sich nicht bei jeder Messung aendern, werden hier einmal eingetragen und fuer alle folgenden Messungen beibehalten. Diese Werte werden auch in den Info-Header der Excel-Datei geschrieben.
4. **Messwerte erfassen** -- Der Hauptbildschirm. Hier gibt der Mitarbeiter die aktuellen Messwerte ein. Oben stehen die festen Werte in einem eigenen Block (editierbar, falls sich z.B. die LOT-Nr. aendert). Darunter die Messwert-Felder. Zahlenfelder pruefen sofort, ob der Wert innerhalb der Spec-Limits liegt (gruen/rot). Optionale Felder wie "Bemerkungen" koennen leer bleiben.
5. **Pruefen und Senden** -- Vor dem Schreiben oeffnet sich ein Dialog, der alle Werte noch einmal zusammenfasst. Fehler (z.B. ungueltige Zahlen) blockieren das Senden. Warnungen (z.B. Wert ausserhalb Spec) werden angezeigt, aber das Senden ist trotzdem moeglich.

### Tastaturnavigation

Im Messwert-Bildschirm kann mit Tastatur navigiert werden:
- **Enter** oder **Pfeil runter** -- Springt zum naechsten Eingabefeld
- **Pfeil hoch** -- Springt zum vorherigen Eingabefeld
- **Tab** -- Standard-Tab-Navigation

---

## Admin-Funktionen

Admin-Benutzer (gekennzeichnet durch `admin=true` in `users.kv`) bekommen in der Produkt/Prozess-Ansicht drei Tabs statt einem:

1. **Produkt/Prozess** -- Die normale Auswahl-Ansicht (fuer alle Benutzer)
2. **Datenauswertung** -- Excel-Dateien oeffnen und als Tabelle anzeigen
3. **Produktkonfiguration** -- Neues Feature: Produkt-JSON-Dateien direkt in der App erstellen und bearbeiten

### Produktkonfigurations-Editor

Der Editor erlaubt Admins, Produkte ohne manuelles JSON-Editieren zu verwalten:

- **Produkt laden/neu/kopieren** -- Bestehende Produkte aus der Dropdown-Liste laden, neue anlegen, oder ein bestehendes als Vorlage kopieren
- **Prozesse verwalten** -- Prozesse hinzufuegen, entfernen und umsortieren. Jeder Prozess hat eine Template-ID, einen Anzeigenamen und eine optionale Zeilengruppe
- **Felder bearbeiten** -- Per Doppelklick oder "Bearbeiten"-Button oeffnet sich ein Dialog mit allen Feldeigenschaften:
  - ID und Anzeigename
  - Typ (Text, Zahl, Auswahl)
  - Rolle (Kontext, Messwert, Auto)
  - Persistent und Optional Flags
  - Spezifikationsgrenzen (Min/Max/Zielwert) fuer Zahlenfelder
  - Optionsliste fuer Auswahl-Felder
- **Ausgabeverzeichnis** -- Pro Produkt ein eigenes Ausgabeverzeichnis setzen
- **Speichern** -- Validiert die Konfiguration (Pflichtfelder, doppelte IDs, Spec-Grenzen) und schreibt die JSON-Datei. Danach ist das Produkt sofort in der Produkt/Prozess-Auswahl verfuegbar

Die gespeicherten JSON-Dateien koennen per USB-Stick auf andere Rechner verteilt werden -- einfach in den `data/products/`-Ordner kopieren.

---

## Excel-Dateien

### Dateinamen

Die generierten Dateien heissen z.B.:

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

Die Zeilen 1-5 bilden den Info-Header-Block. Er wird beim ersten Setzen der festen Werte geschrieben und bei Aenderung (z.B. "Kontext aendern") aktualisiert.

### Ausgabeverzeichnis

Das Ausgabeverzeichnis kann auf drei Ebenen konfiguriert werden:

1. **Pro Produkt** -- Im Feld `output_dir` der Produkt-JSON-Datei (hoechste Prioritaet)
2. **Global** -- Im Feld `output_dir` in `app_config.json` (Fallback)
3. **Standard** -- `output/` im Anwendungsverzeichnis (wenn nichts konfiguriert)

---

## Dateien im Detail

### `app.py` -- Einstiegspunkt

Erstellt das Tkinter-Hauptfenster, laedt die Konfiguration, und verwaltet die Navigation zwischen den vier Bildschirmen (Login, Produkt/Prozess, Kontext, Formular). Die Navigation funktioniert ueber gestapelte Frames -- alle Views werden beim Start erzeugt und per `tkraise()` in den Vordergrund gebracht.

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

Schicht 3 ist die Nachtschicht und geht ueber Mitternacht. Die App erkennt das: Wer um 3 Uhr nachts arbeitet, ist noch in Schicht 3 vom Vortag.

### `data/products/REF31962.json` -- Produktkonfiguration

Jedes Produkt hat eine eigene JSON-Datei. Diese definiert alle Prozesse (IPC1 bis IPC5) und fuer jeden Prozess die Felder mit ihren Eigenschaften:

- **id** -- Technischer Bezeichner (z.B. `"breite_1"`)
- **display_name** -- Anzeigename (z.B. `"Breite 1"`)
- **type** -- `"text"`, `"number"` oder `"choice"` (Dropdown)
- **role** -- `"context"` (Kontext), `"measurement"` (Messwert) oder `"auto"` (automatisch)
- **persistent** -- `true` wenn der Wert ueber mehrere Messungen gleich bleibt (z.B. FA-Nr., LOT Nr.)
- **spec_min/spec_max/spec_target** -- Spezifikationsgrenzen und Zielwert fuer Zahlenfelder
- **options** -- Auswahlliste fuer Choice-Felder (z.B. `["Ja", "Nein"]`)
- **optional** -- `true` wenn das Feld leer bleiben darf

Optionales Top-Level-Feld:
- **output_dir** -- Ausgabeverzeichnis fuer dieses Produkt (ueberschreibt den globalen Wert)

Besonderheiten einzelner Prozesse:
- **IPC2 Schaelen** hat `row_group_size: 3` -- das bedeutet, es gibt 3 Nutzen pro Rolle. Die App zaehlt automatisch "Nutzen 1 von 3", "Nutzen 2 von 3", etc.
- **IPC4 Stanzen** hat ein Auto-Feld "Pruefmuster", das bei jeder Messung hochzaehlt.

Um ein neues Produkt hinzuzufuegen gibt es zwei Wege:
1. **Admin-Editor** -- Im Tab "Produktkonfiguration" direkt in der App anlegen
2. **Manuell** -- Eine neue JSON-Datei nach dem gleichen Schema in `data/products/` legen

Die App findet neue Produkte beim naechsten Start (oder nach dem Speichern im Editor) automatisch.

### `src/config/process_config.py` -- Konfigurationssystem

Das Herzstueck der Konfiguration. Definiert fuenf Datenklassen:

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
- `get_persistent_context_fields()` -- Kontext-Felder, die ueber Messungen bestehen bleiben
- `get_per_measurement_context_fields()` -- Kontext-Felder, die sich pro Messung aendern
- `get_measurement_fields()` -- Alle Messwert-Felder
- `get_auto_fields()` -- Automatisch befuellte Felder
- `get_all_headers()` -- Anzeigenamen aller Felder in Reihenfolge (fuer die Excel-Kopfzeile)
- `get_field_by_id()` -- Feld anhand der technischen ID suchen
- `determine_shift()` -- Schicht anhand der aktuellen Stunde bestimmen (mit Mitternachts-Logik)

### `src/config/config_writer.py` -- Konfiguration schreiben

Gegenstueck zu `process_config.py`: Konvertiert die Datenklassen zurueck in JSON-Dicts und schreibt sie als Datei. Wird vom Admin-Editor benutzt.

- `field_to_dict()` / `process_to_dict()` / `product_to_dict()` -- Serialisierung
- `validate_product_config()` -- Prueft: Pflichtfelder ausgefuellt, IDs eindeutig, Spec-Grenzen logisch, Choice-Felder mit Optionen. Gibt eine Liste von Fehlertexten zurueck (leer = alles OK)
- `save_product_config()` -- Schreibt die JSON-Datei in den Produkt-Ordner

### `src/config/settings.py` -- Konstanten

Feste Werte, die nicht in der JSON-Konfiguration stehen:

- Fenstertitel und -groesse
- Pfade zu Benutzerdatei, Audit-Log, Konfiguration und Produktordner
- Ausgabeverzeichnis
- Info-Header-Konfiguration (`INFO_HEADER_ROWS = 5`, `HEADER_ROW = 6`)
- Automatisch generierte Spaltennamen (`Datum`, `Bearbeiter`)

### `src/domain/state.py` -- Anwendungszustand

Die zentrale `AppState`-Klasse haelt alles, was die App gerade weiss:

- Wer ist eingeloggt? (`current_user`)
- Welche Konfiguration ist geladen? (`app_config`)
- Was ist ausgewaehlt? (`selected_product`, `selected_process`, `current_shift`)
- In welche Datei wird geschrieben? (`current_file`)
- Welche festen Werte sind gesetzt? (`persistent_values`)
- Wo stehen die Zaehler? (`row_group_counter`, `auto_sequence`)

Die `reset_*`-Methoden sorgen dafuer, dass beim Zuruecknavigieren alles sauber zurueckgesetzt wird -- in der richtigen Reihenfolge (User -> Product -> Process -> Context).

### `src/domain/validation.py` -- Eingabevalidierung

Validiert Benutzereingaben vor dem Schreiben. Drei Stufen:

1. **Dezimal-Normalisierung** -- Erkennt automatisch deutsches (`3,14`) und englisches (`3.14`) Zahlenformat. Auch gemischte Formate wie `1.250,5` (deutsch fuer 1250,5) werden korrekt geparst.

2. **Typbasierte Validierung** (mit FieldDefs):
   - `number` -- Muss eine gueltige Zahl sein. Spec-Limits erzeugen Warnungen (keine Fehler), weil der Bediener bewusst ausserhalb der Spec messen kann.
   - `choice` -- Muss eine der definierten Optionen sein.
   - `text` -- Wird durchgereicht ohne Pruefung.

3. **Fallback** (ohne FieldDefs) -- Alles wird als Zahl behandelt. Das ist die Rueckwaertskompatibilitaet fuer Code, der noch keine Konfiguration verwendet.

Leere Felder erzeugen eine Warnung, ausser sie sind als `optional` markiert. Fehler blockieren das Speichern, Warnungen nicht.

### `src/excel/creator.py` -- Excel-Dateien erstellen

Kuemmert sich um die Erstellung und das Auffinden von Excel-Dateien:

- `generate_file_name()` -- Erzeugt den Dateinamen: `{Prozess}_{Produkt}_Schicht{X}_{Datum}.xlsx`
- `get_shift_date()` -- Bestimmt das Datum fuer den Dateinamen. Wichtig: Wer nach Mitternacht in Schicht 3 arbeitet, bekommt das Datum des Vortages (weil die Schicht vor Mitternacht begann).
- `find_existing_file()` -- Sucht, ob es fuer diese Kombination aus Produkt/Prozess/Schicht/Datum schon eine Datei gibt (fuer Resume nach App-Neustart).
- `create_measurement_file()` -- Erstellt eine neue Excel-Datei mit Kopfzeile in Zeile 6 (nach dem Info-Header).
- `write_info_header()` -- Schreibt den Info-Header (Zeilen 1-5) mit Produkt, Prozess, FA-Nr., Schicht und Datum.
- `count_data_rows()` -- Zaehlt vorhandene Datenzeilen (fuer die Initialisierung der Zaehler beim Resume).

### `src/excel/reader.py` -- Excel lesen

Liest Daten aus bestehenden Excel-Dateien. Wird nur von der Analyse-Ansicht genutzt (Admin-Funktion). Kann Header lesen, Spalten-Maps erstellen, und alle Daten als Liste von Dictionaries zurueckgeben.

### `src/excel/writer.py` -- Messwerte schreiben

Haengt eine neue Zeile an eine bestehende Excel-Datei an. Die Spaltenreihenfolge wird aus der Prozesskonfiguration abgeleitet -- Feld 1 in Spalte 1, Feld 2 in Spalte 2, etc.

Nimmt drei getrennte Wert-Dictionaries entgegen (Kontext, Messwerte, Auto-Werte), fuehrt sie zusammen und schreibt sie in die richtige Spalte. Gibt ein `WriteResult` zurueck, das Erfolg/Fehler signalisiert.

Fehlerbehandlung: Wenn die Datei gesperrt ist (z.B. in Excel geoeffnet), gibt es eine klare Fehlermeldung.

### `src/audit/audit_logger.py` -- Audit-Trail

Schreibt strukturierte Events als JSON-Zeilen in eine Logdatei (`data/audit_log.jsonl`). Jeder Eintrag hat einen Zeitstempel, einen Event-Typ und optionale Details. Wird bei jeder relevanten Aktion aufgerufen: Login, Prozessauswahl, Kontext setzen, Schreiben (Versuch, Erfolg, Fehler).

Fehler beim Schreiben des Logs werden abgefangen und auf stderr ausgegeben -- das Audit-Log darf nie die eigentliche Arbeit blockieren.

### `src/auth/login.py` -- Authentifizierung

Bietet zwei Anmeldemethoden:
- **Passwort** -- Benutzername + Passwort pruefen
- **QR-Code** -- Ein Handscanner scannt einen QR-Code, die App sucht den passenden Benutzer

Gibt ein `UserInfo`-Objekt zurueck (mit User-ID, Anzeigename und Admin-Flag) oder `None` bei fehlgeschlagener Anmeldung.

### `src/auth/users_kv.py` -- Benutzerdatei-Parser

Liest die Benutzerliste aus einer einfachen Key-Value-Datei. Format:

```
user.max.password=1234
user.max.qr=QR-MAX
user.max.name=Max Mustermann
user.max.admin=true
```

Kommentare (mit `#`) und Leerzeilen werden ignoriert. Fehlerhafte Zeilen werden uebersprungen.

### `src/ui/base_view.py` -- Basis fuer alle Bildschirme

Abstrakte Basisklasse. Jede View bekommt den `AppState` und eine `on_navigate`-Funktion. Bietet `on_show()` und `on_hide()` zum Ueberschreiben -- damit koennen Views reagieren, wenn sie sichtbar oder unsichtbar werden.

### `src/ui/theme.py` -- Design

Definiert Farben, Schriften und ttk-Styles fuer die gesamte Anwendung. Das Design orientiert sich am Questalpha-Branding:
- Weisser Hintergrund
- Dunkle Schrift (`#1B2023`)
- Blaue Akzentfarbe (`#0070BB`)
- Helle Oberflaechen (`#F0F3F5`)

Alle UI-Elemente (Buttons, Labels, Eingabefelder, Tabs) werden hier zentral gestylt.

### `src/ui/login_view.py` -- Anmeldung

Zwei Tabs: Passwort-Login und QR-Code-Login. Im Passwort-Tab springt Enter vom Benutzernamen zum Passwortfeld und loest dann die Anmeldung aus. Der QR-Tab reagiert auf die Enter-Taste (Handscanner senden Enter nach dem Scan). Nach erfolgreicher Anmeldung geht es weiter zur Produkt/Prozess-Auswahl.

### `src/ui/product_process_view.py` -- Produkt/Prozess-Auswahl

Zwei Dropdown-Felder: Produkt waehlen, dann Prozess waehlen. Bei Auswahl eines Prozesses erscheint eine Uebersicht der Felder (welche Kontext-Felder, welche Messwerte mit Spec-Limits, welche Auto-Felder).

Die Schicht wird automatisch angezeigt. Beim Klick auf "Weiter" passiert einiges:
- Schicht und Datum werden bestimmt
- Das Ausgabeverzeichnis wird aufgeloest (Produkt-spezifisch oder global)
- Die App sucht nach einer bestehenden Datei fuer diese Kombination (Resume)
- Wenn keine existiert, wird eine neue erstellt
- Zaehler werden initialisiert (Nutzen, Pruefmuster)
- Der AppState wird aktualisiert

Fuer Admin-Benutzer gibt es zwei zusaetzliche Tabs: "Datenauswertung" und "Produktkonfiguration".

### `src/ui/context_view.py` -- Feste Werte

Zeigt Eingabefelder fuer die persistenten Kontext-Felder (z.B. FA-Nr., LOT Nr.). Wenn ein Prozess keine persistenten Felder hat, zeigt die View einen Hinweis und laesst direkt weiter navigieren.

Die Felder werden dynamisch generiert, basierend auf der Prozesskonfiguration. Choice-Felder bekommen ein Dropdown, Text-Felder ein normales Eingabefeld. Vorherige Werte werden vorausgefuellt.

Nach dem Setzen der Werte wird der Info-Header der Excel-Datei geschrieben (Produkt, Prozess, FA-Nr., Schicht, Datum).

### `src/ui/form_view.py` -- Messwerterfassung

Der Hauptbildschirm. Zeigt zwei getrennte Bloecke:

1. **Feste Werte** (LabelFrame "Feste Werte") -- Die persistenten Kontext-Felder (z.B. FA-Nr., LOT Nr.) werden hier editierbar angezeigt. Aenderungen werden beim Speichern uebernommen.
2. **Messwerte** (LabelFrame "Messwerte") -- Eingabefelder fuer alle pro-Messung-Kontext-Felder und Messwert-Felder.

Zwei Layouts: vertikal (untereinander) und horizontal (Gitter mit 4 Spalten), umschaltbar per Button.

Besonderheiten:
- **Tastaturnavigation**: Enter/Pfeil-runter springt zum naechsten Feld, Pfeil-hoch zum vorherigen.
- **Spec-Feedback**: Zahlenfelder pruefen beim Verlassen, ob der Wert innerhalb der Spec-Limits liegt. Gruene Schrift = OK, rote Schrift = ausserhalb.
- **Scroll-Begrenzung**: Die Felder koennen nicht ueber den sichtbaren Bereich hinaus gescrollt werden. Die Scrollbar wird ausgeblendet, wenn der gesamte Inhalt sichtbar ist.
- **Row-Group-Anzeige**: Bei Prozessen mit Zeilengruppen (z.B. IPC2 mit 3 Nutzen) zeigt ein Label "Nutzen: 2 von 3" an.
- **History**: Die letzten 10 Messungen werden in einer Tabelle am unteren Rand angezeigt.
- **Auto-Werte**: Datum, Bearbeiter, Nutzen und Pruefmuster werden automatisch berechnet.
- **Rollback**: Wenn das Schreiben fehlschlaegt, wird der Pruefmuster-Zaehler zurueckgesetzt.

### `src/ui/review_dialog.py` -- Pruefung vor dem Speichern

Ein modaler Dialog, der alle Werte zusammenfasst bevor sie geschrieben werden. Zeigt:
- Produkt, Prozess, Schicht und Datei
- Feste Werte (Kontext)
- Automatische Felder (Datum, Bearbeiter, Nutzen)
- Alle Messwerte mit Farbmarkierung (gruen = OK, gelb = Warnung, rot = Fehler)
- Spec-Bereiche neben den Werten

Fehler blockieren den Senden-Button. Warnungen erlauben das Senden, werden aber deutlich angezeigt.

### `src/ui/analysis_view.py` -- Datenauswertung

Nur fuer Admins zugaenglich (als Tab in der Produkt/Prozess-Ansicht). Laesst eine Excel-Datei oeffnen und zeigt deren Daten in einer scrollbaren Tabelle an.

### `src/ui/config_editor_view.py` -- Produktkonfigurations-Editor

Nur fuer Admins zugaenglich (als Tab in der Produkt/Prozess-Ansicht). Enthaelt zwei Klassen:

- **ConfigEditorView** -- Der Haupteditor mit Produkt-Auswahl, Prozessliste und Felder-Tabelle
- **FieldEditorDialog** -- Modaler Dialog zum Bearbeiten eines einzelnen Feldes (Typ, Rolle, Spec-Limits, Optionen, Flags)

Der Editor validiert die Konfiguration vor dem Speichern und aktualisiert die App-Konfiguration sofort nach dem Schreiben.

---

## Schichtlogik

| Schicht | Zeitraum | Besonderheit |
|---------|----------|--------------|
| 1       | 06:00 - 14:00 | -- |
| 2       | 14:00 - 22:00 | -- |
| 3       | 22:00 - 06:00 | Geht ueber Mitternacht. Wer um 3 Uhr nachts arbeitet, bekommt das Datum des Vortages im Dateinamen. |

---

## Tests

Die Tests nutzen `unittest` und koennen so ausgefuehrt werden:

```bash
python -m unittest discover -s tests -v
```

### test_process_config.py (22 Tests)

Testet das komplette Konfigurationssystem:
- Feld-Filterfunktionen (context/persistent/measurement/auto)
- Schichtbestimmung zu verschiedenen Uhrzeiten (auch Mitternachts-Uebergang)
- JSON-Laden mit Defaults und Sonderoptionen (row_group_size, output_dir)
- Laden der echten REF31962-Konfiguration als Integrationstest

### test_config_writer.py (26 Tests)

Testet Serialisierung und Validierung:
- Konvertierung von Feldern, Prozessen und Produkten in JSON-Dicts
- Roundtrip-Test: Serialisieren -> JSON schreiben -> wieder parsen -> vergleichen
- Validierungsregeln: leere IDs, doppelte IDs, ungueltige Typen/Rollen, Spec-Grenzen, Choice-Optionen
- Datei erstellen, ueberschreiben, Verzeichnis anlegen

### test_creator.py (14 Tests)

Testet die Excel-Erstellung:
- Dateinamengenerierung
- Datumszuordnung fuer Nachtschicht
- Datei erstellen mit korrekter Kopfzeile in Zeile 6
- Info-Header schreiben (Zeilen 1-5)
- Bestehende Dateien finden
- Datenzeilen zaehlen (fuer Resume)

### test_writer.py (6 Tests)

Testet das Schreiben von Messwerten:
- Zeile wird angehaengt (ab Zeile 7)
- Werte landen in der richtigen Spalte
- Zwei aufeinanderfolgende Schreibvorgaenge
- Fehlerbehandlung bei fehlender Datei
- None-Werte werden uebersprungen

### test_validation.py (28 Tests)

Testet die Eingabevalidierung:
- Dezimal-Normalisierung (deutsches/englisches Format)
- Numerisches Parsing
- Validierung ohne Felddefinitionen (Legacy-Modus)
- Typbasierte Validierung (number mit Spec-Limits, choice mit Optionspruefung, text)
- Optionale vs. Pflichtfelder

### test_kv_parser.py (7 Tests)

Testet den Benutzerdatei-Parser:
- Einzelne und mehrere Benutzer
- Kommentare und Leerzeilen
- Sonderzeichen in Werten
- Fehlerhafte Zeilen

---

## Ein neues Produkt hinzufuegen

### Variante 1: Im Admin-Editor (empfohlen)

1. Als Admin anmelden
2. Tab "Produktkonfiguration" oeffnen
3. "Neu" klicken (oder ein bestehendes Produkt mit "Kopieren" als Vorlage nehmen)
4. Produkt-ID und Anzeigename eingeben
5. Prozesse und Felder definieren
6. "Speichern" klicken -- fertig

### Variante 2: Manuell per JSON

1. Eine neue JSON-Datei in `data/products/` erstellen (z.B. `NEUES_PRODUKT.json`)
2. Die Struktur von `REF31962.json` als Vorlage nehmen
3. Prozesse und Felder anpassen
4. App neu starten -- fertig

### Verteilung auf andere Rechner

Die JSON-Datei aus `data/products/` auf einen USB-Stick kopieren und auf dem Zielrechner in den gleichen Ordner legen. Beim naechsten Start der App wird das Produkt automatisch erkannt.

---

## Abhaengigkeiten

- **Python 3.12+** (nutzt `X | None`-Syntax)
- **openpyxl** -- Excel-Dateien lesen und schreiben
- **tkinter** -- GUI (in Python enthalten)

---

## Build (Windows EXE)

```bash
pyinstaller build_exe.spec
```

Erzeugt im `dist/`-Ordner eine ausfuehrbare Datei. Der `data/`-Ordner und das Logo werden automatisch mit eingepackt.
