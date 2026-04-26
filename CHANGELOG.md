# Versionshistorie – QAInput

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
