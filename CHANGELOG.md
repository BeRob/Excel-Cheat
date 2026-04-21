# Versionshistorie – QAInput

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
