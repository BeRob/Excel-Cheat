# projektplan.md – Excel-Messwerterfassung per Python-App (Übergangslösung)

Projektpfad (Vorgabe): `D:\Coding\Projekte\ExcelMesswerteApp\`

Ziel: Mitarbeitende erfassen Messwerte über eine Desktop-Anwendung. Die App liest Excel-Header, baut dynamische Eingabefelder und schreibt Messungen als neue Zeilen in die Excel-Datei. Mitarbeitende sollen nicht direkt in Excel arbeiten.

---

## 1) Rahmenbedingungen (gegeben)

- Pro Fertigungsprozess existiert eine eigene Tabelle/Datei. Mitarbeitende wählen die passende Excel-Datei aus.
- Ein Messschritt enthält mehrere Messwerte (z. B. Länge, Breite). Diese Werte stehen in **einer Zeile** in eigenen Spalten.
- Messungen werden identifiziert über:
  - **Chargen-Nr**
  - **FA-Nr**
  - **Rolle**
- Diese Identifikationswerte bleiben über mehrere Messungen gleich und sollen:
  - zu Beginn gesetzt werden,
  - bei jedem Speichern automatisch mitgeschrieben werden,
  - bis zu einer Änderung persistent bleiben.
- Messwerte sind **Zahlen**, Dezimaltrennzeichen **Komma**.
- Spalten **Zeit** und **Mitarbeiter** sind aktuell in den Tabellen **nicht** vorhanden.
- Benutzerverwaltung:
  - Benutzerliste liegt im Anwendungspfad als `key=value` Datei.
  - Keine Passwort-Policy, keine Hashes.
  - QR-Login: Handscanner liefert Text → App identifiziert Benutzer über Benutzerliste.
- Kein Parallelzugriff (Datei wird nicht gleichzeitig von mehreren Personen beschrieben).
- Auditlog zentral, pragmatisch (nicht “übertrieben”).

---

## 2) Zielbild & Nicht-Ziele

Zielbild:
- App Start → Login (Passwort oder QR) → Datei auswählen → Kontext setzen → Messwerte erfassen → Review → Schreiben in Excel → Auditlog.

Nicht-Ziele:
- Vollwertiges MES/LIMS
- Umfangreiche Rollen-/Rechteverwaltung
- Kryptografisch hochgesicherte Manipulationssicherheit (pragmatisches Logging genügt)

---

## 3) Agent/Team-Arbeitsauftrag (Planungsleitplanken)

Leitplanken:
- Stabil, deterministisch, wenige Abhängigkeiten.
- Mitarbeitende arbeiten nur über die App, nicht direkt in Excel.
- Jede Schreibaktion ist nachvollziehbar (Auditlog).
- Fehler sind sichtbar (UI) und protokolliert (Audit).

Deliverables:
1. Windows-Desktop-App (Python) mit Login, Excel-Auswahl, dynamischem Formular, Review, Excel-Write.
2. Benutzerliste im `key=value` Format im Anwendungspfad.
3. Zentrales Auditlog (JSONL).
4. Doku (Setup, Betrieb, Grenzen).
5. Minimale Tests (Smoke + Kernlogik).

Definition of Done:
- Login ok/fail + Logging.
- Header wird gelesen, Formular korrekt erzeugt.
- Kontext bleibt persistent bis Änderung.
- Speichern zeigt Review und schreibt erst nach Bestätigung.
- Excel-Write hängt genau eine neue Zeile an.
- Zeit/Mitarbeiter werden automatisch geschrieben (und bei Bedarf Spalten erzeugt).
- Auditlog enthält file/user/context/status.

---

## 4) Funktionsübersicht (Was die App kann)

1) **Login**
- Benutzername + Passwort (Klartext aus KV-Datei)
- QR-Login per Handscanner (QR-Text → Benutzer-Mapping)
- Nach Login: `current_user` gesetzt

2) **Dateiauswahl**
- File-Dialog für `.xlsx`
- Workbook laden
- Standard: erster Sheet (optional später: Sheet-Auswahl)

3) **Kontext setzen (persistiert)**
- Felder: Chargen-Nr, FA-Nr, Rolle
- Kontext wird im App-State gehalten und bei jedem Speichern mitgeschrieben
- Button „Kontext ändern“ setzt neue Werte

4) **Dynamische Messwertmaske**
- Headerzeile wird gelesen
- Aus Header-Spalten werden Eingabefelder erzeugt (numerisch)
- Kontext- und Auto-Spalten werden nicht als Messwertfelder gezeigt (Mapping statt Eingabe)

5) **Speichern mit Review**
- Button „Speichern“ öffnet Review:
  - Kontext, Messwerte, Datei/Sheet
  - Validierungswarnungen (leer/ungültig)
- Button „Senden“ schreibt tatsächlich nach Excel

6) **Excel schreiben**
- Append: nächste freie Zeile
- Schreibt Kontext + Messwerte + Zeit + Mitarbeiter
- Speichert Datei

7) **Auditlog zentral**
- JSONL, eine Zeile pro Event
- Ereignisse: app_start, login_success/fail, file_selected, context_set, write_attempt, write_success/fail

---

## 5) Ablaufbeschreibung (User-Flow)

1. App starten  
2. Login (Passwort oder QR-Scan)  
3. Excel-Datei auswählen  
4. Kontext setzen: Chargen-Nr, FA-Nr, Rolle  
5. Messwerte eintragen  
6. „Speichern“ → Review/Prüfen  
7. „Senden“ → Schreiben in Excel + Auditlog  
8. Messwertfelder leeren, Kontext bleibt  
9. Nächste Messung / Kontext ändern / Datei wechseln / Logout

---

## 6) Technischer Entwurf (Programmierung & Architektur)

### 6.1 Technologie-Stack
- Python 3.11+ (Windows)
- GUI: `tkinter`
- Excel IO: `openpyxl`
- KV-Parsing: eigener Parser (simple `split("=", 1)` + Sections via Prefix)
- Auditlog: eigener JSONL-Writer

### 6.2 Projektstruktur (Plan)
`D:\Coding\Projekte\ExcelMesswerteApp\`
- `app.py` (Entry)
- `src/`
  - `ui/`
    - `login_view.py`
    - `file_select_view.py`
    - `context_view.py`
    - `form_view.py`
    - `review_dialog.py`
  - `auth/`
    - `users_kv.py`
    - `login.py`
  - `excel/`
    - `reader.py`
    - `writer.py`
  - `domain/`
    - `state.py` (AppState)
    - `validation.py`
  - `audit/`
    - `audit_logger.py`
  - `config/`
    - `settings.py`
- `data/`
  - `users.kv`
  - `settings.kv` (optional)
- `docs/`
  - `projektplan.md` (dieses Dokument)

### 6.3 App-State (zentral)
- `current_user`: eingeloggter Benutzer (id/name)
- `current_file`: Pfad zur Excel-Datei
- `current_sheet`: Name/Index
- `current_context`: charge/fa/rolle
- `current_headers`: Header-Liste (Spaltennamen)
- `current_values`: aktuelle Eingaben (Dict: header → value)

---

## 7) Benutzerliste (key=value) – Format

Datei: `data/users.kv`

Konvention (einfach, eindeutig):
- `user.<id>.password=...`
- `user.<id>.qr=...`
- `user.<id>.name=...` (optional)

Beispiel:
user.max.password=1234
user.max.qr=QR-MAX-001
user.max.name=Max Mustermann

user.anna.password=pass
user.anna.qr=QR-ANNA-002
user.anna.name=Anna Beispiel



Login-Regeln:
- Passwort: `username` existiert und `password` matcht
- QR: gescannter Text matcht gegen `user.<id>.qr` → Login als `<id>`

---

## 8) Excel-Logik (Header, Mapping, Auto-Spalten)

### 8.1 Header lesen
- Headerzeile: standardmäßig Zeile 1 (konfigurierbar)
- Header = Liste Strings in Reihenfolge

Regeln:
- Leere Headerzellen: entweder blockieren oder automatisch benennen (`Spalte_7`). Plan: **blockieren** (sauberer), mit Fehlermeldung.

### 8.2 Spalten-Konventionen (Festlegung)
Kontext-Spaltennamen (exakt):
- `Charge_#`
- `FA_#`
- `Rolle_#`

Auto-Spaltennamen (exakt):
- `Zeit`
- `Mitarbeiter`

### 8.3 Auto-Anlegen fehlender Spalten
Beim Öffnen oder spätestens beim ersten Write:
- Prüfen ob Kontext-Spalten vorhanden sind:
  - Falls nicht: am Ende anhängen und Header setzen
- Prüfen ob Auto-Spalten vorhanden sind:
  - Falls nicht: am Ende anhängen und Header setzen

Damit wird das Mapping stabil, ohne dass Vorlagen manuell geändert werden müssen.

### 8.4 Mapping beim Schreiben
Ziel: neue Zeile append (nächste leere Zeile).

Für jede Header-Spalte:
- Wenn `Charge_#` → `current_context.charge`
- Wenn `FA_#` → `current_context.fa`
- Wenn `Rolle_#` → `current_context.rolle`
- Wenn `Zeit` → `datetime.now()` (lokal)
- Wenn `Mitarbeiter` → `current_user.id` oder Anzeigename (Festlegung: `id`)
- Sonst → Messwert aus Eingaben

---

## 9) Validierung (Zahlen, Komma)

- Messwerte sind numerisch.
- Eingabe akzeptiert `,` und `.` als Dezimaltrennzeichen:
  - intern normalisieren: `"," → "."`
  - parse zu `float`
- Leere Messwertfelder:
  - Warnung im Review (nicht zwingend blockieren)
- Ungültige Zahlen:
  - im Review markieren und „Senden“ blockieren, bis korrigiert

---

## 10) Review/Prüfen (UI-Logik)

Beim Klick auf „Speichern“:
- Erzeuge Zusammenfassung:
  - Datei/Sheet
  - Kontext
  - Liste aller Messwerte (Spalte → Wert)
- Validierungsstatus:
  - Warnungen (leer)
  - Fehler (nicht numerisch)
- Buttons:
  - „Bearbeiten“ (zurück)
  - „Senden“ (nur wenn keine Fehler)

---

## 11) Auditlog zentral (pragmatisch)

### 11.1 Pfad
Konfigurierbar (Netzpfad/Share):
- z. B. `\\server\qa-audit\messwerte_app\audit_log.jsonl`

### 11.2 Format JSONL
Eine JSON pro Zeile:
- `ts` (ISO)
- `event`
- `user`
- `file`
- `context` (charge/fa/rolle)
- `details` (row, error, etc.)

Beispiel:
```json
{"ts":"2026-02-03T10:14:11+01:00","event":"write_success","user":"max","file":"X:\\prozess\\tabelle.xlsx","context":{"charge":"C123","fa":"FA77","rolle":"R1"},"details":{"row":128}}

11.3 Events (Minimum)

app_start

login_success

login_fail

file_selected

context_set

write_attempt

write_success

write_fail


12) Fehlerfälle & Edge-Cases (geplant)

Datei nicht vorhanden / falsches Format → Meldung + Audit write_fail/file_select_fail

Datei gesperrt (z. B. Excel offen) → Meldung „Datei schließen“ + Audit

Sehr viele Spalten → Formular scrollfähig (Canvas + Scrollbar)

Header enthält Duplikate → blockieren oder automatisch suffixen (_2). Plan: suffixen (deterministisch).


13) Implementationsreihenfolge (Plan, kein Code)

App-Skeleton (tkinter Fenster, Screen-Navigation, AppState)

KV-Parser + Auth (Passwort + QR)

Datei-Dialog + Excel-Reader (Header, Sheet)

Kontextscreen + Persistenz

Dynamisches Formular (Fields aus Headern, Scroll)

Validation + Review Dialog

Excel-Writer (Auto-Spalten, Append, Save)

Audit-Logger (zentrales JSONL)

Smoke-Tests mit 2–3 echten Prozessdateien


14) Minimale Tests (Plan)

Smoke:

Login ok/fail

Datei wählen

Kontext setzen

Messwerte schreiben → neue Zeile vorhanden

Auto-Spalten wurden angelegt (Zeit/Mitarbeiter) + Werte gesetzt

Unit (Kernlogik):

KV-Parser

Numeric Normalization (Komma/Punkt)

Header-Mapping + Auto-Spalten-Insert

Next empty row finder

15) Betriebsannahmen (für Dokumentation)

Mitarbeitende haben keinen direkten Schreibzugriff außerhalb der App (organisatorisch/Dateirechte).

Kein Parallelbetrieb auf derselben Datei vorgesehen.

Auditlog ist zentral erreichbar und schreibbar.