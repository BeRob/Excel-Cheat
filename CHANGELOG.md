# Versionshistorie – QAInput

## v1.3.1 – 2026-04-27

### Neu
- **Produkt REF32102** – Sugi Eyedrain, 155 x 4 x 1 mm, non-sterile, 100 Stk. mit 4 IPC-Prozessen:
  - **IPC1 Schneiden**: ASK > 1200 % (Ja/Nein), Kanten sauber & fusselfrei (Ja/Nein), Bahn 1 + Bahn 2 (Spec 155 mm, 153–157)
  - **IPC2 Schälen** (Multi-Nutzen, 3 Nutzen): Schalspalt oben/unten als gemeinsame Werte, Flächengewicht pro Nutzen (Spec 135 g/m², 125–150)
  - **IPC3 Stanzen**: Auto-Prüfmuster, Kanten-Choice, Breite (Spec 4 mm, 3,2–4,8) + Länge (Spec 155 mm, 153–157)
  - **IPC4 Packliste**: Beutel-Nr. als Auto-Sequenz, Rollen/Schicht-Nr. pro Eintrag

### Geändert
- **Auto-Sequenz-Felder** – Auto-Felder mit der ID `beutel_nr` werden jetzt analog zu `pruefmuster` automatisch hochgezählt (inkl. Rollback bei Schreibfehler); ermöglicht durchnummerierte Packlisten

---

## v1.3.0 – 2026-04-27

### Neu
- **Datumsauswahl für Verwendbarkeitsdatum** – Kalender-Popup mit Monats-/Jahresnavigation und Heute-Button; öffnet sich über das 📅-Symbol neben dem Eingabefeld in der Kontext-Eingabe (kein Tippen mehr nötig)
- **Read-only Header-Zeile im Messformular** – FA-Nr., LOT Nr., Verwendbarkeitsdatum und Messmittel werden oben im Messformular dauerhaft angezeigt; ein ✎-Symbol pro Wert führt zurück zur Kontext-Eingabe für Korrekturen, ohne dass die Werte versehentlich überschrieben werden können
- **Excel-Info-Header zweispaltig** – Produkt/Prozess/Schicht/Datum links, FA-Nr./LOT/Verwendbarkeitsdatum/Messmittel rechts (Spalten C–D) im Block über der Datentabelle; diese vier Felder erscheinen damit nur einmal pro Datei und nicht mehr in jeder Messzeile

### Geändert
- **Rollencharge** ist nicht mehr „fester Wert" über den ganzen Prozess, sondern wird zu den gemeinsamen Werten gezählt (kann zwischen Messungen leer/anders sein); im Multi-Nutzen-Modus erscheint Rollencharge im Block „Gemeinsame Werte" über den Nutzen-Sektionen, im Single-Modus in einem eigenen Block oberhalb der Messwerte
- **FA-Nr., LOT Nr., Verwendbarkeitsdatum, Messmittel** wandern aus der Datenzeile in den Excel-Info-Block; in jeder Excel-Datei steht damit nur noch im Header, was sich pro Datei nicht ändert. Die Spalten in Zeile 6 enthalten nur noch echte Mess- und Per-Messung-Werte
- **Reihenfolge in der Kontext-Eingabe**: FA-Nr → LOT Nr. → Verwendbarkeitsdatum → Messmittel
- **Review-Dialog hochformatig** – Breite 680 px (vorher 1000 px), maximale Höhe 1100 px (vorher 900 px); Nutzen-Anzeige im Auto-Block entfernt
- **„Nutzen X von Y"-Label entfernt** – im Single-Nutzen-Pfad redundant, weil das automatische Feld `Nutzen` ohnehin in jede Zeile geschrieben wird

### Behoben
- **Multi-Nutzen + Layout-Toggle** – Im horizontalen Layout-Modus werden die Nutzen-Sektionen jetzt nebeneinander statt untereinander dargestellt; vorher hatte der Toggle bei Multi-Nutzen-Prozessen keine sichtbare Wirkung
- **Spec-Validierungsrahmen pro Nutzen** – Im Multi-Nutzen-Modus war der grüne/rote Rahmen für Felder mit Spec-Grenzen (z. B. Flächengewicht) nur für die letzte Nutzen-Sektion korrekt, weil alle Nutzen denselben Border-Schlüssel teilten. Jetzt validiert jede Sektion unabhängig (Schlüssel `{name}_n{i}`)
- **Bemerkungen-Default „n/a"** in allen Render-Pfaden konsistent – wird sowohl beim Initial-Aufbau als auch nach „Felder leeren" sicher gesetzt

### Konfiguration
- Neuer Feldtyp `"date"` (Datumsauswahl-Render im UI, im Excel als Text gespeichert)
- Neues Feld-Flag `"info_header": true` – Feld erscheint im Excel-Info-Block statt als Spalte
- Neuer Helfer `get_info_header_fields(process)` und `get_form_persistent_fields(process)`; `get_all_headers(process)` schließt Info-Header-Felder vom Spaltenkopf aus

---

## v1.2.1 – 2026-04-27

### Behoben
- **Multi-Nutzen-Eingabe in REF31962 IPC2 Schälen** – `group_shared`-Flag fehlte bei `Schalspalt oben`/`Schalspalt unten`, dadurch wurde das Multi-Nutzen-Formular gar nicht angezeigt; jetzt analog zu REF31963 konfiguriert
- **Multi-Nutzen-Default** – Beim Öffnen des Formulars werden jetzt sofort alle Nutzen-Sektionen (= `row_group_size`, typisch 3) angezeigt statt nur einer; vorher musste der Bediener erst manuell den Radio-Button auf "3" klicken

## v1.2.0 – 2026-04-24

### Neu
- **Multi-Nutzen-Eingabe für IPC2 Schälen** – Anzahl der Nutzen (1–3) vor der Messung wählbar; gemeinsame Felder (Rollennummer, Rollencharge, Schälspalt oben/unten) werden einmal erfasst, Nutzen-spezifische Felder (Schichtdicke Nass, Flächengewicht, Bemerkungen) pro Nutzen; alle Zeilen werden in einem Schritt gespeichert
- **Rollencharge** als persistentes Kontextfeld in IPC1 Vorschneiden und IPC2 Schälen (REF31963) – wird vor Rollen Nr. abgefragt und bleibt über Messungen hinweg erhalten
- **Resume bei LOT + FA-Nr.** – eine bestehende Datei wird fortgesetzt, sobald LOT Nr. und FA-Nr. übereinstimmen, unabhängig von Datum und Schicht; die letzten 10 Messungen werden beim Fortsetzen direkt in die History vorgeladen
- **Kontextanzeige in der Context-View** – zeigt dynamisch „Neue Datei wird erstellt" oder „Fortsetzen – N Messungen vorhanden", sobald FA-Nr. und LOT eingegeben werden
- **Schriftgröße skalierbar** – + / – Schaltflächen im Header vergrößern/verkleinern alle Schriften global (Bereich −2 bis +5 Stufen)
- **Dark Mode** – Umschalter im Header wechselt zwischen Hell- und Dunkeldesign
- **Farbiger Validierungsrahmen** – Messfelder mit Spec-Grenzen zeigen bei Eingabe einen grünen (OK) oder roten (außerhalb Spec) Rahmen statt Schriftfarbänderung; Rahmen wird beim Leeren zurückgesetzt
- **History-Spalten automatisch angepasst** – Spaltenbreiten in „Letzte 10 Messungen" passen sich nach jeder Messung dem längsten Inhalt an

### Geändert
- **Dateinamenschema** – neues Format: `{LOT}_{FANR}_{ProduktID}_{ProzessID}_{YYYY-MM-DD}_Schicht{N}.xlsx`
- **Spalten-Mapping im Writer** – Spalten werden anhand der tatsächlichen Spaltenüberschriften in der Datei zugeordnet (statt positionsbasiert); verhindert Spaltenverschiebungen bei Änderungen an der Feldkonfiguration
- **FA-Nr., LOT Nr., Verwendbarkeitsdatum** bleiben beim Wechsel von Produkt oder Prozess erhalten und werden im neuen Prozess vorausgefüllt
- **Review-Dialog** – Breite auf 1000 px erhöht, Höhe skaliert dynamisch mit Feldanzahl (max. 900 px)

---

## v1.1.0 – 2026-04-22

### Neu
- **Produkt REF31963** – Sugi Instrument Wipe Xtra, 80×80 mm, non-sterile, 250 Stk. mit allen 5 IPC-Prozessen (Vorschneiden, Schälen, Walzen, Stanzen, Packliste)
- **`default_value`-Unterstützung für Felder** – Eingabefelder können mit einem Standardwert vorausgefüllt werden; der Wert wird auch nach jeder Messung wiederhergestellt (z.B. Bemerkungen = „n/a")
- **Neue persistente Kontextfelder in allen Prozessen beider Produkte**: Messmittel, Verwendbarkeitsdatum
- **Bemerkungen** in allen Prozessen beider Produkte – optional, Standardwert „n/a"
- **Granulare Pfad-Konfiguration** – `config.json` unterstützt jetzt separate Schlüssel `users_dir`, `config_dir`, `products_dir` und `audit_dir` statt einem einzelnen `data_dir`; ermöglicht getrennte Netzwerkpfade für Benutzerdaten, Konfiguration, Produkte und Audit-Trail
- **Output-Verzeichnis per Ordner-Dialog** – kein fester globaler Output-Ordner mehr; das Verzeichnis wird aus der Produkt-Config gelesen oder beim Prozessstart per Ordner-Auswahl-Dialog abgefragt

### Geändert
- REF31963 IPC2 Schälen: `row_group_size` 2 → 3 (identisch zu REF31962); Flächengewicht-Spec angepasst (270–330 g/m², Ziel 300)
- Schälspalt-Felder in REF31963 auf konsistente Schreibweise vereinheitlicht (ohne Umlaut, wie REF31962)
- `settings.py`: `OUTPUT_DIR` entfernt; neue Konstanten `USERS_DIR`, `CONFIG_DIR`, `AUDIT_DIR`
- Deployment-Konfiguration auf Produktionspfade `X:\Produktion\14_QAInput\` angepasst
- Projektbereinigung: Planungs- und Präsentationsdateien aus dem Repository entfernt

---

## v1.0.0 – 2026-03-01

Erstveröffentlichung.

- Login mit Passwort oder QR-Code-Handscanner
- JSON-basierte Produkt- und Prozesskonfiguration (kein Code-Änderung nötig für neue Produkte)
- Dynamische Messwert-Formulare mit Spec-Feedback (grün/rot)
- Excel-Ausgabe mit automatischer Benennung, Info-Header und Passwortschutz
- Resume: bestehende Datei wird beim Neustart erkannt und weitergeführt
- Zeilengruppen (z.B. 3 Nutzen pro Rolle) mit automatischer Zählung
- Admin-Funktionen: Datenauswertung, Produktkonfigurations-Editor
- Audit-Log (JSONL) mit Inter-Prozess-Dateisperrung für Multi-Instanz-Betrieb
- Schicht-Logik mit Mitternachts-Übergang für Schicht 3
