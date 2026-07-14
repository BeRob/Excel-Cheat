# Config-Referenz QAInput (Cheat-Sheet)

Alle Schlüssel, die in Produkt-Configs, Prozess-Templates und den übrigen
Konfigurationsdateien wirksam sind. **Unbekannte Schlüssel werden beim Laden
ignoriert** (deshalb können Altlasten in Dateien stehen, ohne dass etwas
bricht — und deshalb fallen Tippfehler nicht auf!). Dateien/Schlüssel mit
`_`-Präfix sind Kommentare/Arbeitsdateien und werden nie geladen.

---

## 1. Prozess-Template (`data/process_templates/<Operation>.json`)

Kanonische Feldstruktur **einmal je Operation** (Superset über alle Produkte).
Dateiname = Operationsname (Konvention). 8 Operationen: Vorschneiden, Walzen,
Schaelen, Stanzen, Schneiden, Packliste, Ausschussplatten, Probenfertigung.

| Schlüssel | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `template` | string | ✔ | Operationsname — **Referenzschlüssel**, auf den Produkt-Configs zeigen |
| `template_revision` | int | – (Default 1) | Bei jeder Template-Änderung erhöhen; landet in `write_success`-Audit-Events (GMP: welche Template-Version erzeugte die Datei) |
| `fields` | Liste von Feld-Objekten | ✔ | Feld-Superset der Operation (siehe Abschnitt 3) |
| `_present_in` (je Feld) | string | – | Nur Review-Annotation („ALL" oder Produktliste) — Laufzeit ignoriert sie |
| `_unification_notes` | object | – | Nur Doku uneinheitlicher Felder — Laufzeit ignoriert sie |

---

## 2. Produkt-Config (`data/products/<REF>.json`) — dünne Form

### Top-Level

| Schlüssel | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `product_id` | string | ✔ | Nur `A-Z a-z 0-9 _` — Dateiname, Excel-Dateiname, Freigabe-Manifest-Schlüssel |
| `display_name` | string | ✔ | Anzeige in der Produktauswahl |
| `revision` | int | – (Default 1) | Produkt-Revision; der Config-Editor erhöht sie beim Speichern automatisch |
| `revision_history` | Liste | – | Einträge `{"revision": int, "date": "YYYY-MM-DD", "user": str, "change": str}` — Editor füllt sie automatisch |
| `output_dir` | string | – | Zielordner der Excel-Dateien (absolut oder relativ zu APP_ROOT); fehlt er, fragt die App per Ordner-Dialog |
| `processes` | Liste von Prozess-Objekten | ✔ | siehe unten |

### Prozess (dünn — der Normalfall)

| Schlüssel | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `template_id` | string | ✔ | **Prozess-Identität, wörtlich erhalten!** Excel-Dateiname + Resume-Schlüssel (z.B. `IPC3_Fertigschneiden`) — nie aus Stufe+Operation rekonstruieren |
| `display_name` | string | ✔ | Anzeige in der Prozessauswahl |
| `template` | string | ✔ (dünn) | Operationsname → `data/process_templates/<Name>.json` |
| `active_fields` | Liste von Feld-ids | ✔ (dünn) | **Auswahl UND Reihenfolge** der Felder = Excel-Spaltenreihenfolge. Jede id muss im Template oder in `extra_fields` existieren, sonst Ladefehler |
| `field_overrides` | object | – | Je Feld-id ein Objekt mit abweichenden Attributen (nur die Keys aus Abschnitt 3, typisch `spec_min`/`spec_max`/`spec_target`). Overrides für ids außerhalb `active_fields` sind wirkungslos |
| `extra_fields` | Liste von Feld-Objekten | – | Produktunike Felder mit **voller** Definition (Abschnitt 3) |
| `row_group_size` | int | – | **Standard-/Max-Anzahl Nutzen/Bahnen** je Messung. Der Bediener wählt beim Prozessstart 1..Max; beim Fortsetzen wird die Anzahl aus der Datei gelesen. Multi-Nutzen (Wide-Format) ist aktiv, sobald mind. ein Feld `clone: true` ist — clone-Felder verlangen einen `row_group_size`-Wert. Weglassen = einzeilig |
| `template_revision` | int | – | Rein informativ in der Datei — beim Laden gilt immer die Revision der Template-Datei |

### Prozess (Legacy — nur noch für Alt-/Sonderfälle)

Statt `template`+`active_fields` eine volle `fields`-Liste. Wird unverändert
geladen; `template`/`template_revision` werden, falls vorhanden, als Metadaten
durchgereicht. Neue Configs bitte immer dünn anlegen.

---

## 3. Feld-Definition (in Templates, `extra_fields` und Legacy-`fields`)

| Schlüssel | Typ | Default | Bedeutung |
|---|---|---|---|
| `id` | string | Pflicht | Technischer Schlüssel (klein, snake_case). Einige ids haben **Sonderverhalten** — siehe Abschnitt 4! |
| `display_name` | string | Pflicht | Anzeigename = **Excel-Spaltenkopf** (Zeile 9). Ändern bricht das Spalten-Mapping bestehender Dateien nicht (Header-basiert), aber neue und alte Spalte koexistieren dann |
| `type` | `text` \| `number` \| `choice` \| `date` | `text` | `number` → Dezimal-Validierung + Spec-Prüfung; `choice` → Dropdown (braucht `options`); `date` → Eingabe + 📅-Kalender |
| `role` | `context` \| `identifier` \| `measurement` \| `auto` | `measurement` | `context` = Rahmendaten, `identifier` = Zeilen-Kennung (Rollen-Nr./Bahn/Lfd. Nr. — wie Kontext erfasst, als Spalte geschrieben, nie geklont), `measurement` = Messwert, `auto` = systemgeneriert (Abschnitt 4) |
| `persistent` | bool | false | Nur bei `role: context`: Wert gilt für die ganze Sitzung (ContextView „Feste Werte"); false = je Messung neu („Gemeinsame Werte") |
| `spec_min` / `spec_max` | Zahl | – | Spezifikationsgrenzen (nur `number`). Verletzung ⇒ Out-of-Spec-Gate: Senden nur mit echter Bemerkung |
| `spec_target` | Zahl | – | Sollwert (Anzeige/Doku, keine Prüfung) |
| `options` | Liste von strings | – | Pflicht bei `choice` (z.B. `["Ja", "Nein"]`) |
| `optional` | bool | false | true = darf leer bleiben. **false + leer = Fehler, blockiert das Senden** (seit v1.6.0) |
| `default_value` | string | – | Vorbelegung beim Laden und nach jedem Speichern (z.B. `"n/a"` für Bemerkungen) |
| `clone` | bool | false | `true` = Feld wird je Nutzen/Bahn wiederholt und erzeugt im Wide-Format **je Nutzen eine eigene Spalte** („Breite Bahn 1", „Breite Bahn 2" …). `false` = einmal je Messung (gemeinsam, z. B. Schälspalt). Löst `group_shared` ab (invertiert: altes `group_shared: true` == `clone: false`); Alt-Configs werden beim Laden automatisch umgesetzt |
| `info_header` | bool | false | Feld wandert in den Excel-Info-Block (Zeilen 2–12, Spalten C/D) statt als Spalte; im Formular read-only in der Kopfleiste mit ✎ |
| `machine_scoped` | bool | false | Kontextfeld, dessen Wert je Maschine gemerkt wird — braucht ein `choice`-Feld mit `id: "maschine"` im selben Prozess |

`field_overrides` darf genau diese Schlüssel überschreiben (außer `id`).

---

## 4. Feld-ids und display_names mit Sonderverhalten (im Code verdrahtet)

| id / display_name | Verhalten |
|---|---|
| id `datum` (role auto) | App schreibt Zeitstempel `YYYY-MM-DD HH:MM:SS` beim Speichern |
| id `bearbeiter` (role auto) | App schreibt den Anzeigenamen des angemeldeten Benutzers |
| id `nutzen` (role auto) | Liefert im Wide-Format die **Nutzen-Bezeichnung** für die Spaltennamen (`display_name` z. B. „Bahn" → „Breite Bahn 1"; „Nutzen" bei Schälen). Wird selbst **nicht** als eigene Spalte geschrieben |
| id `pruefmuster`, `beutel_nr` (role auto) | Fortlaufende Nummer **je Datei** (läuft beim Fortsetzen weiter; Rollback bei Schreibfehler) |
| id `karton` (role auto) | `(beutel_nr − 1) // 20 + 1` — das Sequenz-Feld muss in der Feldreihenfolge **vor** `karton` stehen |
| id `messmittel` (context, info_header) | Komma-getrennte Eingabe wird im Excel-Info-Block auf mehrere Zeilen verteilt |
| id `bemerkungen` | Ziel des Out-of-Spec-Gates (Platzhalter `n/a`, `-`, `—` … zählen als leer). Empfehlung: `optional: true`, `default_value: "n/a"` — **jeder Prozess braucht dieses Feld** |
| id `maschine` (choice) | Anker für `machine_scoped`-Felder („Aktive Rolle pro Maschine") |
| id `rollen_nr` (role identifier) | Reine Rollennummer als eigene Kennung; wahlweise neben oder statt `rolle_bahn_nutzen` |
| id `rolle_bahn_nutzen` (role identifier) | Konvention ab Schälen: zusammengesetzte Kennung „Rollen Nr. / Bahn / Nutzen" (display_name) |
| id `lfd_nr` (role identifier) | Manuelles Eingabefeld (kein Auto-Zähler), pro Rolle; nur Produkte, die es in `active_fields` aufnehmen |
| ids `schichtdicke` / `schichtdicke_anfang_links` … / `schichtdicke_trocken_oben` … | Ein Messwert je Nutzen; Produkte mit Positionsmessung nehmen die Anfang/Ende-links/rechts-Varianten, Produkte mit Messung beider Zustände (trocken/nass × oben/unten, z. B. REF31827) die Zustands-Varianten (seit Schaelen-Template Rev. 4) |
| display_name `FA-Nr.`, `LOT Nr.`, `Verwendbarkeitsdatum` | Werden beim Prozesswechsel als „carried values" vorgetragen — exakt diese Schreibweise verwenden |
| `FA-Nr.` + `LOT Nr.` | Bestandteil des Excel-Dateinamens und des Resume-Schlüssels |
| type `choice` (alle) | Behält den Wert über Messungen hinweg (wird beim Felder-Leeren nicht geleert) |

---

## 5. Freigabe-Manifest (`data/products/freigaben.json`)

Wird **nur** über den Config-Editor („Freigabe erfassen…") geschrieben.

```json
{
  "REF31962": {
    "revision": 3,
    "sha256": "<Hash der Config-Datei>",
    "dokument": "FB-31962-003",
    "datum": "2026-06-12",
    "geprueft_von": "…",
    "freigegeben_von": "…",
    "erfasst_von": "…"
  }
}
```

Hash oder Revision passt nicht mehr ⇒ Status „geändert" ⇒ Produkt fällt aus
dem Scope. Kein Eintrag ⇒ „nicht freigegeben".

---

## 6. Globale Einstellungen (`data/app_config.json`)

| Schlüssel | Typ | Default | Bedeutung |
|---|---|---|---|
| `freigabe_pflicht` | bool | **true** | true = nur freigegebene Produkte wählbar; false = Übergangsbetrieb mit ⚠-Markierung |
| `qr_prefix` | string | `""` | Scanner-Präfix, das vor dem QR-Abgleich entfernt wird (z.B. `"WF2 "`) |
| `shifts` | Liste | `[]` | `{"name": "1", "start_hour": 6, "end_hour": 14}`; über Mitternacht erlaubt (22→6) |
| `sheet_protection_password` | string | `"hexhex"` | Excel-Blattschutz (Bedienschutz, kein Sicherheitsmerkmal) |
| `audit_lock_timeout_seconds` | Zahl | 5.0 | Lock-Timeout des Audit-Loggers |
| `logging` | object | – | `debug_max_mb`, `debug_backup_count`, `error_max_mb`, `error_backup_count`, `buffer_capacity` |

Pfade (Datenverzeichnisse) kommen **nicht** hierher, sondern aus Env-Vars /
Bootstrap-`config.json` neben der exe (siehe CLAUDE.md „Data Folder").

---

## 7. Benutzerdatei (`data/users.kv`)

```
user.<id>.password=…   # Klartext (Härtung = offenes P2-Paket)
user.<id>.qr=…         # QR-Code-Inhalt für Scanner-Login
user.<id>.name=…       # Anzeigename (→ Bearbeiter-Spalte)
user.<id>.admin=true   # Admin-Tabs (Auswertung, Config-Editor)
```

---

## 8. Word-Vorlage Freigabedokument (`data/vorlagen/freigabedokument.docx`)

Eine normale Word-Datei mit Platzhaltern `{{NAME}}` — sie definiert den immer
gleichen Aufbau aller Freigabedokumente. Platzhalter am Stück tippen/einfügen.

**Skalare** (überall, auch Kopf-/Fußzeile):
`{{PRODUKT_ID}}` `{{PRODUKT_NAME}}` `{{REVISION}}` `{{CONFIG_DATEI}}`
`{{SHA256}}` `{{DATUM}}` `{{APP_VERSION}}` `{{ANZAHL_PROZESSE}}` `{{PROZESSLISTE}}`

**Felder-Tabelle** — eine Tabellenzeile mit diesen Platzhaltern wird je Feld
(über alle Prozesse) dupliziert:
`{{PROZESS}}` `{{PROZESS_ID}}` `{{TEMPLATE}}` `{{TEMPLATE_REV}}` `{{FELD_ID}}`
`{{FELD_NAME}}` `{{FELD_TYP}}` `{{FELD_ROLLE}}` `{{SPEC_MIN}}` `{{SPEC_SOLL}}`
`{{SPEC_MAX}}` `{{OPTIONEN}}` `{{DEFAULT}}` `{{FLAGS}}`

**Revisionshistorie-Tabelle** — eine Zeile, dupliziert je Eintrag:
`{{REV_NR}}` `{{REV_DATUM}}` `{{REV_USER}}` `{{REV_AENDERUNG}}`

Unbekannte Platzhalter bleiben im Dokument stehen und werden beim Erzeugen
gemeldet (Tippfehler fallen sofort auf). Ohne Vorlage erzeugt die App ein
HTML mit festem Layout.

---

## 9. Minimal-Muster: dünne Produkt-Config

```json
{
  "product_id": "REF99999",
  "display_name": "REF 99999 - Musterprodukt",
  "revision": 1,
  "revision_history": [
    {"revision": 1, "date": "2026-06-12", "user": "qm", "change": "Neuanlage"}
  ],
  "output_dir": "output/REF99999",
  "processes": [
    {
      "template_id": "IPC1_Vorschneiden",
      "display_name": "IPC1 Vorschneiden",
      "template": "Vorschneiden",
      "active_fields": ["fa_nr", "lot_nr", "breite", "bemerkungen", "datum", "bearbeiter"],
      "field_overrides": {
        "breite": {"spec_min": 180.0, "spec_max": 190.0, "spec_target": 185.0}
      }
    }
  ]
}
```

---

## 10. Störungs-Codes (`data/stoerungs_codes.json`)

Zweistufige Fehler-Klassifizierung für die Störungserfassung (Kategorie →
Ursache). Fehlt die Datei oder ist sie fehlerhaft, greift die eingebaute
Default-Taxonomie aus `src/downtime/downtime_models.py` (`DEFAULT_KATEGORIEN`).
Pfad: `config_dir/stoerungs_codes.json` (`STOERUNGS_CODES_PATH`).

```json
{
  "kategorien": [
    {"name": "Mechanik", "ursachen": ["Lagerschaden", "Werkzeugbruch", "Materialstau"]},
    {"name": "Elektrik", "ursachen": ["Sensorfehler", "Antrieb/Motor", "Steuerung/SPS"]},
    {"name": "Sonstiges", "ursachen": ["Warten auf Technik", "Alle übrigen Verluste"]}
  ]
}
```

Der Störungs-Store selbst (`stoerungen.jsonl`, append-only, ein `stoerung_start`-
und ein `stoerung_ende`-Eintrag je Störung, gepaart über `id`) ist **kein**
Config-File, sondern Laufzeit-Record. Ablage: `QAINPUT_DOWNTIME_DIR` /
Bootstrap-Key `downtime_dir` (Default: neben dem Audit-Trail).
