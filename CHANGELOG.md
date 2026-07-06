# Versionshistorie – QAInput

## v0.12.0 – 2026-07-07

> Fenster-Anordnung vereinheitlicht + neue, klar gegliederte Netzlaufwerk-Struktur.

### Behoben
- **Störungsfenster nicht mehr unten abgeschnitten** – Das Fenster „Störung / Stillstand" begrenzte seine Höhe zwar auf den Bildschirm, hatte aber keinen Scrollbereich; bei offener Störung (Freigabe-Abschnitt + Liste „Letzte Störungen") wanderten „Maschine freigeben" und „Schließen" aus dem sichtbaren Bereich. Inhalt liegt jetzt in einem scrollbaren Bereich, der **„Schließen"-Button ist fest in der Fußzeile** und immer erreichbar

### Geändert
- **Einheitliche Dialog-Anordnung** – Neuer gemeinsamer Helfer `src/ui/dialog_util.py` (`place_dialog` = an Inhalt anpassen, auf Bildschirm begrenzen, auf dem Elternfenster zentrieren, Mindestgröße setzen; `make_scrollable` = Scrollbereich). Angewandt auf alle Toplevel-Dialoge (Störungsfenster, Prüfen-Dialog, Datumsauswahl, Info-Dialog, Feld-Override/-Editor, Operation-/Freigabe-Dialoge, Verlauf-Spaltenauswahl); wo der Inhalt wachsen kann, sind die Aktions-Buttons gepinnt und die Liste scrollt. Der Neues-Produkt-Assistent wird symmetrisch mit Rand zentriert (Taskleiste bleibt frei)
- **Neue Netzlaufwerk-Struktur** – Empfohlene Ablage nach GMP-Funktion gegliedert, kleingeschrieben mit Nummern-Präfix: `01_konfiguration` (read-only), `02_aufzeichnungen` (Messwerte/Audit-Trail/Störungen), `03_protokolle`, `04_freigabedokumente`, `05_dokumentation`. Einrichtungsanleitung inkl. Ordner-Anlage, „welche Datei wohin", NTFS-Rechten und `config.json`-Vorlage in **`NETZWERK_EINRICHTUNG.md`**; `deployment/config.json` auf die neue Struktur umgestellt

### Neu
- **Eigene Pfad-Schlüssel** in `settings.py`/`config.json`: `vorlagen_dir` (`QAINPUT_VORLAGEN_DIR`), `freigabedokumente_dir` (`QAINPUT_FREIGABEDOKUMENTE_DIR`) und `ui_prefs_dir` (`QAINPUT_UI_PREFS_DIR`). Bisher hingen Vorlagen und **generierte Freigabedokumente** am `DATA_DIR` und landeten in Produktion neben der Exe (nicht beschreibbar) — jetzt gezielt platzierbar. `ui_prefs.json` (Verlauf-Spaltenauswahl, kein GMP-Record) liegt standardmäßig **pro Station lokal** unter `%LOCALAPPDATA%\QAInput\`. Bestehende Defaults bleiben abwärtskompatibel

## v0.11.0 – 2026-07-03

> Hinweis: **v0.10.0 (baramundi-Installer-Deployment + Startup-Preflight) ist ein paralleler Entwicklungszweig** (`feature/deployment-baramundi`, noch in Arbeit) und in diesem Stand **nicht enthalten**. Die Nummer 0.10.0 bleibt für diesen Zweig reserviert; die Zusammenführung erfolgt nach Abschluss der Feature-Entwicklung als eigenes Release.

### Neu
- **Wächter für Template-ID-Änderungen** – Wird bei einem bereits gespeicherten Produkt eine `template_id` umbenannt oder ein Prozess entfernt, verlangt der Config-Editor beim Speichern eine ausdrückliche Bestätigung: Die Template-ID ist Excel-Dateiname + Fortsetzungs-Schlüssel — bestehende Excel-Dateien würden nicht fortgesetzt. Logik Tk-frei in `config_editing.removed_template_ids` (6 neue Tests); ersetzt die frühere Dauerwarnung robuster als der Hover-Hinweis
- **Hover-Tooltips** (`src/ui/tooltip.py`) – Erklärtexte im Config-Editor sind zu ⓘ-Symbolen mit Tooltip geworden (platzsparend, folgt dem Dark-Mode). Ein Klick/Touch auf ⓘ togglet den Tooltip zusätzlich — funktioniert auch ohne Hover

### Geändert
- **UI-Politur** – Einheitliche ttk-Styles statt verstreuter Inline-Fonts/`width=`-Hacks: `Icon.TButton` (✎/⚙/📅/◀▶/+/−/↑↓), `Small.TButton` (Zeilen-Buttons), `Info.TButton` (ⓘ), `Hint.TLabel` (Hinweistexte), `FieldId.TLabel` (Monospace-Chips); neue Font-Keys `tiny`/`tiny_bold`/`mono`; kompaktere Buttons und Feld-Border (3→2 px)
- **Config-Editor-Feldliste** – Spaltenkopf (✓/ID/Typ/Rolle/Anzeigename/Min/Soll/Max), Feld-ID als Monospace-Chip, Trennlinien zwischen den Zeilen. Kopfzeile und Datenzeilen nutzen ein gemeinsames **Pixel-Spaltenraster** (`_configure_list_columns`) — bündige Spalten unabhängig von den Schriftgrößen; Bearbeiten/✕ liegen in einer Aktionszelle, damit Extra-Feld-Zeilen die Spalten nicht verschieben
- **OoS-Banner präzisiert** – Der Hinweis im Prüfen-Dialog nennt wieder explizit, dass ‚n/a' als Bemerkung nicht genügt (Bemerkungen ist mit „n/a" vorbelegt — ohne den Zusatz wirkte die Meldung widersprüchlich)
- **Neues-Produkt-Assistent** – startet mit expliziter Fenstergeometrie statt `state("zoomed")` (das überdeckte die Taskleiste und verdeckte die Fußzeilen-Buttons)

### Entfernt
- **↑/↓-Buttons in der Feldliste** – Umsortieren jetzt ausschließlich per Maus-Drag am Griff ⠿

## v0.9.1 – 2026-06-30

> **Störungs- und Stillstandserfassung.** Bediener melden Maschinenstörungen aus der Messwertmaske; die Stillstandszeit wird geloggt, klassifiziert und bei der Freigabe abgeschlossen. Auswertung inkl. Verfügbarkeit/MTTR/MTBF als OEE-Vorstufe.

### Neu
- **Störungsfenster aus der Messwertmaske** – Neuer Button „⚠ Störung / Stillstand" in der Action-Bar öffnet ein Fenster, in dem **erfasst und freigegeben** wird. Erfassen: zweistufige Klassifizierung (Kategorie → Ursache), Station (Lokalisierung), Beschreibung; die Startzeit wird gesetzt. Freigeben: Technikername (Pflicht) + Behebungsbeschreibung (Pflicht), Endzeit und Dauer werden berechnet. Jede Störung ist an die laufende Produkt-/Prozess-(/Maschine-)Auswahl gebunden
- **Offene Störung überlebt Logout/Neustart** – Beim Betreten der Messwertmaske wird eine offene Störung des aktuellen Kontexts aus dem Store rekonstruiert; der Button zeigt dann „⚠ Störung aktiv – freigeben"
- **Eigener Störungs-Store** (`stoerungen.jsonl`) – Append-only JSONL nach dem gehärteten Audit-Muster (Inter-Prozess-Lock, lokaler Fallback mit Replay). System-of-Record getrennt vom Audit-Log; je Aktion zusätzlich ein Audit-Breadcrumb (`stoerung_start`/`stoerung_ende`)
- **Zweistufige Fehler-Code-Liste** `data/stoerungs_codes.json` (Kategorie → Ursachen, konfigurierbar; fehlt/fehlerhaft → eingebaute Default-Taxonomie)
- **Admin-Tab „Störungen / Auswertung"** – Filter (Zeitraum mit Schnellwahl „letzte 2 Wochen"/„dieser Monat", Produkt, Prozess, Station, Kategorie, Status), Detailtabelle, KPI-Kacheln (**Anzahl, Σ Störzeit, MTTR, MTBF, Verfügbarkeit**), wählbare Gruppierung (Station/Kategorie/Prozess) und **Excel-Export**
- **Pfade konfigurierbar** – `QAINPUT_DOWNTIME_DIR`/Bootstrap-Key `downtime_dir` (Default: neben dem Audit-Trail); Code-Liste unter `stoerungs_codes.json` im `config_dir`

### Hinweise
- Verfügbarkeit braucht eine Planzeit; der Auswertungs-Tab schlägt sie aus Schichtlänge × aktiven Tagen vor und lässt sie überschreiben. MTTR/MTBF/Zählungen sind ohne Planzeit verfügbar
- Volle OEE (Leistung × Qualität) ist eine spätere Erweiterung (benötigt Stückzahlen + Soll-Taktzeit, die heute nicht erfasst werden)

## v0.9.0 – 2026-06-30

> Versions-Neubasislinie: Die App wird ausdrücklich auf **0.9.0** gesetzt (Vorgänger-Stand war 1.9.0). Ab hier zählt 0.9.x als aktuelle Pre-1.0-Linie.

### Neu
- **Nutzen/Bahnen als nummerierte Spalten (Wide-Format)** – Wird ein Messfeld je Nutzen/Bahn erfasst, erzeugt es jetzt **je Nutzen eine eigene Excel-Spalte** statt mehrerer Zeilen: aus „Breite" werden „Breite Bahn 1", „Breite Bahn 2" … (keine verbundenen Zellen, je Wert eine Zelle). Eine Zeile je Messung
- **Feld-Flag `clone`** – Löst `group_shared` ab (invertiert: `group_shared=true` == `clone=false`). `clone=true` = je Nutzen/Bahn wiederholen. Alt-Configs mit `group_shared` werden beim Laden automatisch umgesetzt
- **Anzahl Nutzen/Bahnen wählt der Bediener beim Prozessstart** – Einmal je Datei (1..Max, Max = `row_group_size` der Config). Beim Fortsetzen wird die Anzahl aus den Spaltenköpfen der bestehenden Datei zurückgelesen und gesperrt — so bleibt die Datei in sich konsistent. Kleine Rolle = 1 Nutzen, große = 2, ohne Config-Änderung
- **Neue Feld-Rolle `identifier` („Kennung")** – Zeilen-Kennungen wie Rollen-Nr., Rolle/Bahn/Nutzen, Lfd. Nr. sind weder Kontext noch Messwert. Sie werden im „Gemeinsame Werte"-Block erfasst, als Spalte geschrieben und nie geklont
- **Eigenes Rollennummer-Feld `rollen_nr`** in den kanonischen Templates (Vorschneiden, Schälen, Schneiden, Walzen, Probenfertigung) — wahlweise neben dem zusammengesetzten `rolle_bahn_nutzen`
- **Drag-&-Drop der Feldreihenfolge** im Config-Editor – Felder per Maus-Griff (⠿) umsortieren; ↑/↓-Buttons bleiben als Alternative

### Geändert
- **Templates neu klassifiziert (Revision 3)** – Kennungen (`rolle_bahn_nutzen`, `rollen_nr`, `lfd_nr`) sind jetzt `role=identifier`; die Ja/Nein-Prüfungen `ask`/`flaechengewicht`/`schnittkante` sind `role=measurement` statt Kontext; per-Nutzen-Messwerte sind `clone=true`. Walzen/Probenfertigung bleiben einzeilig (keine clone-Felder)
- **Config-Editor** – Override-/Voll-Editor zeigen statt `group_shared` den **`clone`**-Haken; die Feld-**Rolle ist im Editor frei wählbar** (auch für Template-Felder, inkl. `identifier`); das Feld „Zeilengruppe" heißt jetzt „Standard-/Max-Anzahl Nutzen"
- **Editor-Validierung** – clone-Felder verlangen eine Standard-/Max-Nutzenzahl; Kennungen sind beim Template-Wählen vorausgewählt
- **Excel-Writer/Creator Wide-fähig** – Header-Erzeugung und -Validierung expandieren clone-Felder anhand der gewählten Nutzenzahl; das `nutzen`-Auto-Feld entfällt als Spalte (die Nutzen-Nr. steckt im Spaltennamen)

### Hinweise
- Bestehende Long-Format-Dateien (eine Zeile je Nutzen) werden vom neuen Writer **nicht** weiter beschrieben — die Templates werden ohnehin neu entworfen
- Die noch nicht redesignten Auto-Generat-Templates (Stanzen, Ausschussplatten, Packliste) laden unverändert (kein clone-Feld → einzeilig)

## v1.9.0 – 2026-06-16

### Neu
- **Config-Editor komplett template-basiert neu** – Der Admin-Editor ist um das dünne Template-Modell herum neu gebaut. Pro Prozess wird eine **Operation (Template) per Dropdown** gewählt; die Felder erscheinen als **Checkliste** mit den IDs aus dem Template — **kein Freitext mehr für Feld-IDs** (Tippfehler-Quelle beseitigt). Spec-Grenzen (min/soll/max) werden **inline in der Zeile** gesetzt, seltenere Overrides (Anzeigename, group_shared, default, optional, machine_scoped, info_header, Optionen) über einen kleinen Bearbeiten-Dialog; Typ/Rolle bleiben fix aus dem Template. Reihenfolge der angehakten Felder = Excel-Spaltenreihenfolge
- **Assistent für neue Produkte** – „Neu (Assistent)" führt durch Produktkopf + beliebig viele Prozessschritte (je Template wählen, Felder ankreuzen, Specs setzen). Speichert nicht selbst, sondern übergibt an den normalen Speicherpfad (eine GMP-Code-Bahn: Änderungsbeschreibung, Revision, Audit)
- **Vorauswahl = nur Pflicht-Standard** – Beim Wählen eines Templates sind nur die vier Kopf-Felder (FA-Nr., LOT, Verwendbarkeitsdatum, Messmittel), die Auto-Felder und Bemerkungen vorausgewählt. Messwerte und optionale Kontextfelder hakt der Admin bewusst dazu
- **Eigene (produktunike) Felder** – „Eigenes Feld hinzufügen…" öffnet einen Voll-Editor (freie ID, alle Attribute) → wird als `extra_fields` gespeichert. Kollision mit Template-IDs wird verhindert
- **Freigabe-Status sichtbar + geführt** – Prominentes Status-Badge (grün „freigegeben" / orange „geändert seit Freigabe" / grau „nicht freigegeben") für das geladene Produkt; die Buttons „Freigabedokument erzeugen…"/„Freigabe erfassen…" sind nur bei gespeichertem Stand aktiv, mit Nächster-Schritt-Hinweis
- **Neues Tk-freies Logikmodul `src/config/config_editing.py`** – `default_active_ids`, `is_legacy_product`, `seed_process_from_template`, `apply_template_change`, `validate_editor_product` — unit-testbar ohne Tkinter. 21 neue Tests (`test_config_editing.py`, `test_editor_roundtrip.py`)

### Geändert
- **Operation-Wechsel eines Prozesses** meldet wegfallende Felder vor dem Entfernen (Bestätigung); Extra-Felder und in beiden Templates vorhandene Felder bleiben samt Overrides erhalten; `template_id` wird nur neu vorgeschlagen, wenn er nicht manuell gesetzt wurde
- **`template_id`-Vergabe** schlägt `IPC<n>_<Operation>` vor (editierbar) mit deutlicher Warnung, dass eine spätere Änderung Resume/Spaltenmapping bricht
- **Zusätzliche Editor-Validierung vor dem Speichern** – je Prozess mindestens ein echter Messwert (Bemerkungen zählt nicht), Bemerkungen-Pflichtfeld, gewähltes/vorhandenes Template, eindeutige `template_id` über alle Prozesse; nicht-numerische Inline-Specs blockieren das Speichern
- **Template-Revisions-Drift sichtbar** – Beim Laden weist der Editor darauf hin, wenn ein Template seit dem letzten Speichern aktualisiert wurde (beim nächsten Speichern wird gegen die neue Revision aufgelöst)

### Entfernt / blockiert
- **Legacy-Voll-Configs (ohne Template) werden beim Laden hart geblockt** – klare Meldung mit Verweis auf den Assistenten; Kopieren von Legacy ebenfalls gesperrt. Die dünne Form ist damit der einzige Bearbeitungspfad
- Das Datenmodell, der dünne Write-Back (`config_writer`) und die Freigabe-Logik bleiben **unverändert** — Acid-Roundtrip (resolve(save(load)) == load) weiterhin 0 Abweichungen

## v1.8.0 – 2026-06-15

### Neu
- **Kanonische Prozess-Templates (5 von 8 neu entworfen)** – Vorschneiden, Probenfertigung, Schälen, Schneiden, Walzen sind harmonisiert: **eine id je Messkonzept** (z. B. `breite` statt `breite_1`/`breite_2`/`bahn_1`/`bahn_2`). Mehrere gleichzeitige Messungen (Bahnen/Nutzen) werden als **Zeilen** geführt, Anzahl je Produkt über `row_group_size`. Identifier-Konvention ab Schälen: aus „Rollen Nr." wird **„Rollen Nr. / Bahn / Nutzen"** (`rolle_bahn_nutzen`). Schichtdicke ist ein Messwert je Nutzen mit optionalen Positionsvarianten (Anfang/Ende × links/rechts); optionales manuelles Feld „Lfd. Nr.". Stanzen, Ausschussplatten und Packliste bleiben vorerst Auto-Generat-Entwürfe (Redesign folgt)
- **Multi-Nutzen aktiviert an `row_group_size`** – neue Hilfsfunktion `is_multi_nutzen()`: der Mehrzeilen-Modus startet jetzt, sobald `row_group_size` gesetzt ist UND es ein wiederholbares Messfeld gibt (auch ein einzelnes pro-Nutzen-Feld wie `breite` je Bahn). Vorher war zwingend ein `group_shared`-Messfeld nötig. 4 neue Unit-Tests
- **Admin-Guide** – `ADMIN_GUIDE.md`: Verzeichnisstruktur-Empfehlung (Netzlaufwerk), NTFS-Berechtigungen, Deploy- und Freigabe-Workflow, kurz und knapp

### Geändert
- **`build.bat` kopiert jetzt `data/process_templates/`** (und optional `data/vorlagen/`) ins Build — vorher fehlten die Templates im Deployment, sodass dünne Produkt-Configs zur Laufzeit nicht auflösbar gewesen wären. Außerdem kopiert der Build nur noch gezielt `app_config.json`, `process_templates/`, `products/*.json` (inkl. `freigaben.json`) — Laufzeit-/Sensibeldaten (`users.kv`, Logs, Audit, `_thin/`) bleiben draußen
- **Auslieferung mit leerem Produktset** – die 17 Alt-Configs (alte, uneinheitliche Feldstruktur) liegen gesichert unter `data/products_legacy_v1.7/`; ausgeliefert wird mit kanonischen Templates und ohne Produkte. Die Produkt-Configs werden gegen die neuen Templates neu angelegt und im Vier-Augen-Prinzip freigegeben (`freigaben.json` zurückgesetzt). Die zugehörigen v1.7-Configs bleiben über die git-Historie nachvollziehbar (Stand `e20b4f2`)
- **`template_revision` der 5 neu entworfenen Templates auf 2 erhöht** – die Feldstruktur hat sich gegenüber v1.7 geändert (andere ids, andere Feldzahl), darum bekommt sie eine neue Revision. Der Audit-Trail (`WRITE_SUCCESS` trägt `template`+`template_revision`) kann so Records der alten von Records der neuen Struktur unterscheiden. Stanzen, Ausschussplatten und Packliste bleiben unverändert bei Revision 1

## v1.7.0 – 2026-06-12

### Neu
- **Vier-Augen-Freigabe für Produkt-Configs (ohne E-Signatur)** – Nur freigegebene Configs sind im Scope. Die Freigabe passiert auf Papier (Freigabedokument mit zwei Unterschriften, Prüfer ≠ Freigeber) und ist technisch über den SHA-256-Hash der Config-Datei verankert: `data/products/freigaben.json` hält je Produkt Revision, Hash und die Dokumentangaben (`src/config/freigabe.py`). Jede nachträgliche Änderung der Datei bricht den Hash — das Produkt fällt automatisch aus dem Scope, bis eine neue Freigabe erfasst ist
- **Freigabe erfassen im Config-Editor** – Dialog mit Dokument-Nr., Geprüft-von und Freigegeben-von (verschiedene Personen erzwungen); die App berechnet den Hash selbst und schreibt ein `config_released`-Audit-Event. Nach dem Speichern einer Änderung weist der Editor darauf hin, dass die Freigabe erloschen ist
- **Freigabedokument-Generator mit Word-Vorlage** – Editor-Button „Freigabedokument erzeugen…" (und `scripts/make_freigabedokument.py <REF>`) erzeugt je Produkt+Revision ein Freigabedokument mit allen aufgelösten Feldern und Spec-Grenzen, Revisionshistorie, SHA-256 und Unterschriftsblock (`data/freigabedokumente/`, gitignored — das unterschriebene Papier ist der Nachweis). Liegt eine Word-Vorlage unter `data/vorlagen/freigabedokument.docx`, wird sie befüllt (immer gleicher Aufbau; `{{…}}`-Platzhalter inkl. wiederholbarer Tabellenzeilen, ohne Zusatzabhängigkeit — docx wird als ZIP/XML direkt befüllt, auch von Word zerteilte Platzhalter werden erkannt, unbekannte gemeldet); ohne Vorlage HTML-Fallback mit festem Layout
- **CONFIG_REFERENZ.md** – Cheat-Sheet aller wirksamen Schlüssel: Produkt-Config (dünn + Legacy), Prozess-Templates, Feld-Attribute, Feld-ids mit Sonderverhalten (datum/bearbeiter/nutzen/pruefmuster/beutel_nr/karton/messmittel/bemerkungen/maschine), `freigaben.json`, `app_config.json`, `users.kv`, Word-Platzhalter — als Grundlage für den Bau von Muster-Configs (unbekannte JSON-Schlüssel werden beim Laden ignoriert)
- **Freigabepflicht-Schalter** – `app_config.json` `"freigabe_pflicht"`: true (Default, streng) blendet nicht freigegebene Produkte aus und blockt den Prozessstart hart; false (Übergangsbetrieb bis zur Erst-Freigabe) zeigt sie mit ⚠-Markierung
- **`config_loaded`-Audit-Event beim App-Start** – protokolliert alle geladenen Produkt-Configs mit Revision, SHA-256 und Freigabe-Status: beweisbar, welcher exakte Config-Stand welche Chargen-Records erzeugt hat
- **12 neue Tests** für Hash-Manifest, Status-Logik (freigegeben/geändert/nicht freigegeben), Freigabe-Erfassung und Loader-Annotation (190 gesamt)

### Geändert
- **Alle 17 Produkt-Configs auf dünne Form migriert** – `data/products/*.json` referenziert jetzt die Prozess-Templates (`template` + `active_fields` + `field_overrides`/`extra_fields`) statt voller Feldlisten. Vor der Umstellung verifiziert: Auflösung jeder dünnen Config ist feldgenau identisch zur bisherigen vollen Config (ids, Reihenfolge, Anzeigenamen, Specs, Flags) — Resume und Spaltenmapping bleiben unberührt
- **`/excel2config` entfernt** – der Excel-Vorlagen-Import ist seit dem Template-Design überflüssig; neue Produkte entstehen im Admin-Editor (Template-basiert oder als Kopie). Das `_pending`-Staging entfällt

## v1.6.0 – 2026-06-12

### Neu
- **Prozess-Templates (dünne Produkt-Configs)** – Die Feldstruktur eines Prozesses ist einmal je Operation in `data/process_templates/<Operation>.json` definiert (8 Operationen). Produkt-Configs referenzieren `template` + `active_fields` und tragen nur noch Abweichungen (`field_overrides`, `extra_fields`). Der Loader löst beides zur vollen Feldliste auf – Formular, Excel, Resume und Spec-Prüfung bleiben unverändert; alte volle Configs laden abwärtskompatibel. `template_id` bleibt wörtlich erhalten (Excel-Dateiname + Resume-Schlüssel). Audit-Events (`write_success`, `oos_blocked`, `review_cancelled`) tragen `template` + `template_revision` (GMP: welche Template-Version erzeugte die Datei). Einmal-Skripte: `scripts/make_templates.py`, `scripts/migrate_to_thin.py` (Acid-Test: 17 Produkte, 0 Abweichungen)
- **GxP-Review-Skill** – `.claude/skills/gxp-review/SKILL.md`: Checklisten-basierte Compliance-Prüfung (21 CFR Part 11, QMSR/ISO 13485, FDA CSA 2025, GAMP 5, ALCOA+) mit Code-Ankern für Änderungen an Schreibpfad, Audit, Auth, Validierung und Configs
- **Audit-Ausfall sichtbar** – Weicht der Audit-Logger auf den lokalen Puffer aus, zeigt die Statuszeile nach dem Speichern eine Warnung; bei Totalausfall (Event verloren) zusätzlich einmalige Warnbox („IT informieren"). Neuer Status `AuditLogger.degraded_reason`
- **Neue Audit-Events** – `file_create_fail`, `file_resume_fail`, `info_header_fail` (Fehler beim Anlegen/Fortsetzen/Kopfdaten-Schreiben); `oos_blocked` enthält jetzt die betroffenen Felder mit Wert und Spec-Grenzen; `config_edited` wird beim Speichern im Config-Editor geschrieben (Benutzer, Produkt, Revision, Änderungsbeschreibung)
- **43 neue Tests** – Audit-Logger (Lock-Timeout, Fallback-Replay, Rotation), OoS-Gate (Single/Multi-Nutzen), AuthService (Passwort/QR/Admin), Excel-Resume mit umgeordneten Headern, Header-Validierung, Thin-Config-Roundtrip, Dezimal-Mehrdeutigkeit, JSON-Fehlerkontext (178 gesamt)

### Geändert – Verhaltensänderungen für Bediener
- **Leere Pflicht-Messfelder blockieren das Senden** – bisher nur Warnung; eine leere Zelle ohne Begründung im Chargen-Record verletzt ALCOA+ („complete"). Bewusst leer lassen weiterhin über `n/a` (z. B. Bemerkungen-Default) bzw. `optional: true` in der Config
- **Mehrdeutige Dezimaleingaben werden abgelehnt** – „1.250" kann 1250 (deutsche Tausender) oder 1,25 (englisches Dezimal) bedeuten und wurde bisher still als 1,25 gelesen. Jetzt Fehlermeldung mit Hinweis: ohne Tausendertrenner (1250) oder eindeutig (1,25) eingeben. Eindeutige Formate („0,500", „1.250,5", „1,2500") bleiben unverändert akzeptiert
- **Config-Editor verlangt eine Änderungsbeschreibung** – beim Speichern mit Änderungen wird die Produkt-`revision` automatisch erhöht und ein `revision_history`-Eintrag (Datum, Benutzer, Beschreibung) angelegt

### Geändert – Robustheit (GMP-Datenintegrität)
- **Atomares Excel-Schreiben** – alle Workbook-Saves laufen über Temp-Datei + Rename (`src/excel/safe_save.py`); ein Absturz oder Netzabriss mitten im Speichern kann die Chargendatei nicht mehr korrumpieren. Gilt für Messzeilen, Dateierstellung und Info-Block
- **Inter-Prozess-Lock um Excel-Schreiben** – Lock-Datei neben der Excel-Datei serialisiert load→save über Workstations (gleiches Muster wie beim Audit-Log, gemeinsame Helfer in `src/audit/file_lock.py`); bei belegtem Lock klare Fehlermeldung statt verlorener Zeile
- **Header-Validierung beim Schreiben** – fehlt eine erwartete Spalte in Zeile 9 oder hat ein Wert keinen Spaltentreffer, bricht das Schreiben mit Fehlermeldung ab statt Werte still zu verwerfen (info_header-Felder sind weiterhin bewusst ausgenommen)
- **`count_data_rows` wirft bei Lesefehlern** – der Resume bricht mit Meldung ab, statt die Prüfmuster-/Beutel-Nummerierung still bei 0 neu zu starten (doppelte Nummern in der Chargendokumentation)
- **`write_info_header` meldet Fehler** – Rückgabewert + Logging + Audit-Event; der Prozessstart bricht ab, wenn die Kopfdaten (FA-Nr., LOT, Messmittel) nicht geschrieben werden konnten
- **Audit-Fallback-Replay crash-sicher** – der lokale Puffer wird vor dem Nachholen per Rename beiseitegelegt; ein Fehlschlag mitten im Replay kann keine Events mehr verlieren (schlimmstenfalls erkennbare Duplikate)
- **Kaputte Config-/Template-JSONs nennen die Datei beim Namen** – `Ungültiges JSON in …REF31963.json: …` statt nackter Traceback beim App-Start
- **Config-Speichern atomar + dünn** – `save_product_config` schreibt über Temp-Datei + Rename; dünne Configs bleiben beim Editor-Speichern dünn (Overrides werden gegen das Template zurückgerechnet) statt zur vollen Feldliste aufgeblasen zu werden
- **Stille Fehlerpfade geloggt** – übersprungene `users.kv`-Zeilen, `ui_prefs.json`-Fehler und der Schicht-Fallback auf „1" landen jetzt im Tech-Log

### Behoben
- **Config-Editor: Produktliste leer beim Start** – `_load_product_list()` war beim Einbau der Template-Unterstützung aus `__init__` herausgerutscht (toter Code hinter einem `return`)
- **Config-Editor: Speichern setzte `revision` auf 1 zurück** – `_build_product_from_ui()` übergab `revision`/`revision_history` nicht; jedes Admin-Save löschte damit die GMP-Änderungshistorie
- **Logout aus der Kontext-Ansicht ohne Audit-Event** – `context_view._logout` loggt jetzt `logout` wie die übrigen Views
- **Auto-Sequenz-Rollback** – bei Schreibfehlern wird `auto_sequence` exakt um die Zahl der Inkremente zurückgenommen (vorher pauschal −1)

## v1.5.2 – 2026-05-19

### Neu
- **Konfigurierbare Betriebsparameter in `app_config.json`** – Audit-Lock-Timeout, Log-Rotationsgrößen und -Anzahl, MemoryHandler-Puffergröße sowie das Excel-Blattschutz-Passwort lassen sich jetzt über `app_config.json` einstellen, statt im Code hartkodiert zu sein. Damit am Standort ohne Neu-Build der EXE anpassbar – sinnvoll für das Netzlaufwerk-Deployment. Fehlende Schlüssel fallen auf die bisherigen Werte zurück, das Verhalten bleibt ohne Änderung der Datei identisch

### Geändert
- **Produkt-Configs vereinheitlicht** – Konsistenz-Durchgang über alle 17 Produkt-JSONs: Rollen-IDs kanonisiert, Einheiten in die Anzeigenamen aufgenommen, Feld-Definitionen vereinheitlicht; Revision-Bumps mit Revisionshistorie
- **Toter Schlüssel `output_dir` aus `app_config.json` entfernt** – wurde nirgends gelesen; der Ausgabepfad kommt weiterhin aus der Produkt-Config bzw. dem Ordner-Dialog

## v1.5.1 – 2026-05-17

### Behoben
- **openpyxl-Bündelung im Build** – Die `.spec`-Datei verwendet jetzt `collect_all('openpyxl')` statt nur `hiddenimports=['openpyxl']`. Damit werden alle Submodule, Data-Files und Binaries zuverlässig eingebunden. Unter neueren PyInstaller-/Python-Versionen fehlten sonst Submodule, sodass die EXE beim Start mit „openpyxl nicht gefunden" abbrach

### Geändert
- **Echte Umlaute in Produkt-Feldnamen** – Angezeigte Feldnamen in REF31962/31963/32102 nutzten ASCII-Umschreibung; korrigiert zu Flächengewicht, IPC2 Schälen, Länge, Prüfmuster. Diese drei Produkte sind auf Revision 2
- **Revisionshistorie in Produkt-Configs** – Produkt-JSONs können eine `revision_history`-Liste tragen (Revision, Datum, Änderung). `ProductConfig` führt das Feld, Laden und Speichern (auch über den Config-Editor) erhalten es

## v1.5.0 – 2026-05-13

### Neu
- **UI-Optimierung Messeingabe** – Kompakte 1-Zeilen-Metaleiste, Info-Header-Chips mit ✎-Bearbeiten-Button, einklappbarer Verlauf (default eingeklappt) mit Toggle-Button und 1-Zeilen-Last-Message, frei wählbare Verlaufsspalten via ⚙-Button (persistent pro Prozess in `data/ui_prefs.json`), zusammengefasste Action-Bar unten (Navigation links, Felder leeren/Speichern rechts). Mitarbeiter sehen alle Messfelder ohne Scrollen
- **Out-of-Spec mit Bemerkungspflicht (GMP)** – Eingaben außerhalb der Spezifikation sind möglich, das Senden wird aber blockiert, solange `Bemerkungen` leer oder `n/a`/`-`/`—` enthält. Bei Multi-Nutzen pro Nutzen separat geprüft. Roter Banner im Review-Dialog nennt die betroffene(n) Sektion(en)
- **Messmittel mit Komma trennen** – Messmittel-Eingabe wie „Bügelmessschraube, Messschieber" landet im Excel-Info-Block als separate Zeilen untereinander
- **Info-Dialog (ⓘ-Button im App-Header)** – Zeigt App-Version, Datum, Python/OS, Host, Windows-Benutzer, App-Benutzer, Session-ID, alle Daten-/Log-Pfade und eine Tabelle aller Produkt-Revisionen
- **Lückenloses Audit + Debug/Error-Logs** – Zusätzlich zu `audit_log.jsonl` werden `debug.log` (5 MB × 5 Rotation, gepuffert für Netzlauffwerk-Effizienz) und `error.log` (2 MB × 5) angelegt. `sys.excepthook` und `tk.Tk.report_callback_exception` fangen alle Exceptions ab und schreiben Traceback in `error.log` plus `exception`-Event ins Audit. Neue Event-Kategorien: `navigate`, `product_select`, `process_select`, `file_created`/`file_resumed`, `review_opened`/`review_cancelled`, `oos_blocked`, `fields_cleared`, `layout_toggled`, `dark_mode_toggled`, `font_scaled`, `history_toggled`/`history_columns_changed`, `app_exit`, `exception`
- **Audit-Trail um Workstation-Identität erweitert** – Jeder Event-Eintrag enthält jetzt zusätzlich `app_version`, `host` (Rechnername), `win_user` (Windows-Account) und `session` (UUID je App-Start). Damit eindeutig nachvollziehbar, von welcher Workstation und welchem Windows-Account eine Aktion stammt (unabhängig vom angemeldeten App-Benutzer)
- **Tagesrotation des Audit-Logs** – `audit_log.jsonl` wird täglich automatisch in `audit_log.jsonl.YYYY-MM-DD` umbenannt. Alte Tagesdateien bleiben dauerhaft erhalten (GMP). Rename geschieht innerhalb des Inter-Prozess-Locks → race-frei auch mit mehreren parallelen Workstations
- **Netzlaufwerk-Robustheit** – Lock-Acquire mit 5-Sekunden-Timeout statt Endlos-Schleife; bei Timeout/Fehler wird das Event in `%LOCALAPPDATA%\QAInput\audit_local_fallback.jsonl` zwischengespeichert und beim nächsten erfolgreichen Audit-Schreibvorgang automatisch ins zentrale Log nachgereicht. Kein verlorener Event-Eintrag bei kurzem Netzaussetzer
- **Produkt-Revisionen** – Jedes Produkt-JSON trägt jetzt ein Top-Level-Feld `revision` (Start bei 1). Wird beim Bearbeiten/Speichern erhalten und im Info-Dialog gelistet
- **Zentrale Versionsdatei `src/version.py`** – Single Source of Truth für `APP_VERSION`, `APP_VERSION_TUPLE`, `APP_VERSION_DATE`. Settings, Info-Dialog und Audit-Logger lesen hier. `version_info.txt` für PyInstaller wird daraus abgeleitet

### Geändert
- **Horizontales Layout als Default** – Neue Sessions starten im horizontalen Layout-Modus; manuelles Umschalten via Button bleibt
- **`ValidationResult` um `oos_fields: set[str]`** – Spec-Verletzungen werden zusätzlich als strukturierte Menge geliefert (vorher nur als Warning-String). Macht den Out-of-Spec-Gate sauber implementierbar
- **`AuditLogger.log_event(event, level, ...)`** als Hauptmethode mit Level-Differenzierung (`info`/`warn`/`error`); altes `log(...)` als Shim für Rückwärtskompatibilität. Pro Event wird gleichzeitig in den passenden `logging`-Logger geschrieben (debug.log/error.log)
- **Excel-Info-Block-Kapazität auf 12 Zeilen** (vorher 8) – nötig für Messmittel mit mehreren komma-getrennten Einträgen

### Behoben
- **Umlaute in Fehlermeldungen** – "schliessen" → "schließen" in den Excel-Writer-Fehlertexten; ASCII-Variante kam bei deutschen Anwendern als unsauber rüber
- **`test_load_ref31962` robust gegen weitere Produkte** – Test sucht REF31962 jetzt per Filter statt `products[0]`; vorher brach er bei jedem neu hinzugefügten Produkt mit alphabetisch früherem Namen

## v1.4.1 – 2026-05-07

### Neu
- **Maschine→Rolle-Bindung pro Messung (`machine_scoped`)** – Neues Feld-Flag in der Produkt-Config: ein als `machine_scoped: true` markiertes Kontextfeld (typisch `rollen_nr`) wird im Formular nicht mehr direkt eingegeben, sondern aus einem oben angezeigten Block „Aktive Rolle pro Maschine" gelesen. Pro Maschinen-Option (z. B. M1/M2) ein eigener Slot. Bei jeder Messung wählt der MA nur die Maschine; der für sie hinterlegte Rolle-Wert wird automatisch in die Datenzeile übernommen. Beim physischen Rollenwechsel auf einer Maschine wird nur der zugehörige Slot angepasst – alle weiteren Messungen mit dieser Maschine bekommen automatisch die neue Rolle. Anwendungsfall: zwei parallele Stanzmaschinen mit unabhängigen Rollenwechseln (kein Tippfehler-Risiko mehr durch manuelles Nachpflegen)
- **Karton-Auto-Berechnung aus Bag-Nr.** – Felder mit `id: "karton"` und `role: "auto"` werden automatisch aus der laufenden Bag-Nr. (`pruefmuster`) abgeleitet: 20 Beutel pro Karton (`((bag-1)//20)+1`). Setzt voraus, dass `pruefmuster` in der JSON vor `karton` deklariert ist
- **Simulations-Skript `scripts/simulate_inputs.py`** – Entwicklungstool, das die App-Schreib-Pfade direkt aufruft (ohne UI) und für ein Produkt eine Excel-Datei pro IPC-Prozess erzeugt. Ermöglicht Format-/Strukturvergleich mit Bestandsdaten ohne manuelles Eintippen

### Geändert
- **`AppState` um `machine_scoped_values` erweitert** – persistente Map `field_id → maschine_wert → wert` für die Aktive-Rolle-Slots; wird in `reset_process()` geleert
- **`FieldDef.machine_scoped: bool`** – neues serialisierbares Flag, abwärtskompatibel (Default `False`); im Config-Editor als zusätzliches Property speicherbar

---

## v1.4.0 – 2026-04-30

### Neu
- **Direkte Jahresauswahl im Datums-Picker** – Monat als Combobox, Jahr als Spinbox (±20 Jahre vom aktuellen Jahr); ◀/▶-Buttons für Schnell-Navigation bleiben erhalten
- **Toleranz-/Optional-Hinweise konsistent angezeigt** – einheitliche Anzeige der Spec-Grenzen (z. B. `153 – 157`, `≥1000`, `≤50`) und `optional`-Markierung in allen Render-Pfaden: Vertikales Layout, Horizontales Layout, Multi-Nutzen-Sektionen und Feste Werte. Vorher fehlten Toleranzen z. B. in den Festen Werten und bei Feldern mit nur einer Grenze
- **Multi-Nutzen-Übersichtsdialog mit Spec-Validierung** – Statt einer einfachen Bestätigungs-Box gibt es jetzt einen vollwertigen Review-Dialog mit eigenem Block pro Nutzen, farblicher Status-Anzeige (Fehler/Warnung/OK) und Senden-Sperre bei Fehlern – analog zum Single-Nutzen-Modus
- **Excel-Header auf 8 Zeilen vergrößert** – Zeile 1 enthält nur den Produktnamen (fett, Größe 14). Prozess/Schicht/Datum stehen ab Zeile 2 in Spalten A/B; FA-Nr./LOT/Verwendbarkeitsdatum/Messmittel ab Zeile 2 in Spalten C/D mit Reserve bis Zeile 8. Spaltenüberschriften in Zeile 9, Daten ab Zeile 10

### Geändert
- **Navigations-Buttons am unteren Fensterrand** – „Abmelden", „Prozess wechseln" und „Layout: …" sind jetzt am unteren Rand jedes Bildschirms (Login, Produkt/Prozess, Kontext, Messwert) angeordnet, ergonomischer für Bedienpulte
- **„Kontext ändern"-Button entfernt** – sowohl der Button im Top-Bar als auch das ✎-Symbol pro Header-Feld; die Info-Header-Zeile ist jetzt rein zur Anzeige
- **Bemerkungen-Feld leer mit Optional-Hinweis** – statt der Vorbelegung „n/a" ist das Feld leer; rechts vom Eingabefeld erscheint die Markierung `optional`, damit Mitarbeiter erkennen, dass sie das Feld leer lassen oder eine Bemerkung eintragen können
- **Eingabefelder einheitliche Maße** – Felder mit und ohne Toleranz-Rahmen sind jetzt gleich groß und linksbündig ausgerichtet; vorher waren Border-Felder durch ihren 3px-Wrapper minimal größer und wirkten verschoben

### Behoben
- **Schriftgröße bleibt beim Theme-Wechsel erhalten** – `+`/`–` skalierte Schriften wurden beim Klick auf „◑ Dark" / „◑ Hell" auf die Standardgröße zurückgesetzt; jetzt bleibt der Zoom-Faktor erhalten
- **Lesbarkeit im Dark Mode** – mehrere tk-Widgets (Canvas, Validation-Borders, Listbox, Text) und ttk-Styles (Radiobutton, Checkbutton, Spinbox) sowie die Combobox-Popup-Listbox waren im Dark Mode nicht oder schlecht lesbar; jetzt einheitliches Mapping beim Theme-Wechsel

### Hinweis zur Datenmigration
- Excel-Dateien aus v1.3.x (Header-Zeile 6, Daten ab Zeile 7) sind mit v1.4.0 **nicht kompatibel** für Resume. Neue Messungen schreiben in das neue 8-Zeilen-Layout. Bestandsdateien bitte abschließen oder archivieren

---

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
