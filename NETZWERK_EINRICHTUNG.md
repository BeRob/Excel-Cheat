# QAInput – Netzlaufwerk einrichten

Diese Anleitung beschreibt die **neue Ordnerstruktur** auf dem Netzlaufwerk und
wie sie einmalig angelegt und befüllt wird. Sie ersetzt die alte Aufteilung
`…\Data\{user,config,products,process_templates}` + `Audit` + `Log`.

Grundidee: **klein geschriebene Ordner mit Nummern-Präfix**, gegliedert nach
GMP-Funktion – getrennt in **read-only Konfiguration**, **schreibbare
Aufzeichnungen (Records)**, **technische Protokolle**, **Freigabedokumente** und
**Dokumentation**.

---

## 1. Zielstruktur

```
<netzlaufwerk>\qainput\
│
├── 01_konfiguration\              ← read-only für Bediener
│   ├── app_config.json                (Schichten, globale Einstellungen)
│   ├── stoerungs_codes.json           (Kategorie/Ursache der Störungen)
│   ├── 01_benutzer\
│   │   └── users.kv                   (Benutzerdatenbank)
│   ├── 02_produkte\
│   │   ├── <REF>.json                 (freigegebene Produkt-Configs)
│   │   └── freigaben.json             (Vier-Augen-Freigabe-Manifest)
│   ├── 03_prozess_templates\
│   │   └── *.json                     (8 Operationen)
│   └── 04_vorlagen\
│       └── freigabedokument.docx      (optionale Word-Vorlage)
│
├── 02_aufzeichnungen\             ← Records, schreibbar
│   ├── 01_messwerte\                  (erzeugte Excel-Dateien)
│   ├── 02_audit_trail\               (audit_log.jsonl + Tagesrotationen)
│   └── 03_stoerungen\                (stoerungen.jsonl)
│
├── 03_protokolle\                 ← technische Logs
│   ├── debug.log
│   └── error.log
│
├── 04_freigabedokumente\          ← generierte Freigabedokumente
│
└── 05_dokumentation\             ← für Menschen (nur Ablage)
    ├── DOKUMENTATION.md
    ├── ADMIN_GUIDE.md
    ├── CONFIG_REFERENZ.md
    ├── CHANGELOG.md
    ├── Bedienungsanleitung.html
    └── Kurzanleitung.html
```

> `<netzlaufwerk>\qainput\` ist der Wurzelordner – z. B. `X:\Produktion\14_QAInput`
> (Laufwerksbuchstabe) **oder** `\\SERVER\Freigabe\Produktion\14_QAInput` (UNC).
> Bei automatischer Softwareverteilung (baramundi, SYSTEM-Konto ohne gemappte
> Laufwerke) **immer den UNC-Pfad** verwenden.

**Was NICHT ins Netz gehört:** `ui_prefs.json` (Spaltenauswahl im Verlauf) wird
seit dieser Version **pro Station lokal** unter `%LOCALAPPDATA%\QAInput\` gespeichert –
dafür ist kein Netzordner nötig.

---

## 2. Ordner anlegen (PowerShell)

Wurzelpfad anpassen und den Block einmal ausführen:

```powershell
$root = "X:\Produktion\14_QAInput"   # oder: "\\SERVER\Freigabe\Produktion\14_QAInput"

$dirs = @(
  "01_konfiguration\01_benutzer",
  "01_konfiguration\02_produkte",
  "01_konfiguration\03_prozess_templates",
  "01_konfiguration\04_vorlagen",
  "02_aufzeichnungen\01_messwerte",
  "02_aufzeichnungen\02_audit_trail",
  "02_aufzeichnungen\03_stoerungen",
  "03_protokolle",
  "04_freigabedokumente",
  "05_dokumentation"
)
foreach ($d in $dirs) {
  New-Item -ItemType Directory -Force -Path (Join-Path $root $d) | Out-Null
}
```

---

## 3. Startdateien kopieren – was kommt wohin

Quelle ist der `data\`-Ordner des Projekts (bzw. der ausgelieferte Seed).
Vorhandene Dateien im Netz **nicht überschreiben** (die Configs/Records sind der
laufende Bestand).

| Startdatei (Quelle `data\…`)        | Ziel (unter `<root>\`)                          | Zweck |
|-------------------------------------|-------------------------------------------------|-------|
| `app_config.json`                   | `01_konfiguration\`                             | Schichten, globale Einstellungen |
| `stoerungs_codes.json`              | `01_konfiguration\`                             | Störungs-Klassifizierung |
| `users.kv`                          | `01_konfiguration\01_benutzer\`                 | Benutzer (Passwort/QR/Admin) |
| `products\<REF>.json`               | `01_konfiguration\02_produkte\`                 | Produkt-Configs |
| `products\freigaben.json`           | `01_konfiguration\02_produkte\`                 | Freigabe-Manifest (leer starten ok) |
| `process_templates\*.json`          | `01_konfiguration\03_prozess_templates\`        | Feld-Templates (8 Operationen) |
| `vorlagen\freigabedokument.docx`    | `01_konfiguration\04_vorlagen\`                 | optionale Word-Vorlage |
| *(leer lassen)*                     | `02_aufzeichnungen\…`, `03_protokolle\`, `04_freigabedokumente\` | füllt die App zur Laufzeit |
| Doku (`DOKUMENTATION.md`, HTML …)   | `05_dokumentation\`                             | Nachschlagewerk für Menschen |

> **Messwerte (Excel):** Der Ausgabeordner wird **pro Produkt** über den Schlüssel
> `output_dir` in der jeweiligen `<REF>.json` gesteuert. Auf
> `…\02_aufzeichnungen\01_messwerte` setzen. Ist `output_dir` leer, fragt die App
> beim Start einen Ordner ab.

---

## 4. NTFS-Rechte (durch die IT)

| Ordner | Bediener (Gruppe) | Config-Admins |
|--------|-------------------|---------------|
| `01_konfiguration\` (inkl. Unterordner) | **Lesen** | Lesen; **Schreiben** auf `02_produkte\` (Freigabe-Workflow) |
| `02_aufzeichnungen\` (inkl. Unterordner) | **Ändern/Schreiben** | Ändern/Schreiben |
| `03_protokolle\` | **Ändern/Schreiben** | Ändern/Schreiben |
| `04_freigabedokumente\` | **Ändern/Schreiben** | Ändern/Schreiben |
| `05_dokumentation\` | Lesen | Ändern/Schreiben |

Grundsatz: Bediener dürfen **Aufzeichnungen anlegen/anhängen**, aber die
**Konfiguration nicht verändern**. Der Audit-Trail (`02_audit_trail`) und der
Störungs-Store (`03_stoerungen`) sind append-only – Schreibrecht genügt, Löschrecht
sollte **nicht** vergeben werden.

---

## 5. `config.json` an den Client

Die App findet die Netzordner über eine **Bootstrap-Datei `config.json`**, die
**neben der Programmdatei** (`QAInput.exe`) liegt. Inhalt (Pfade an den eigenen
Wurzelordner anpassen):

```json
{
  "config_dir":             "\\\\SERVER\\Freigabe\\Produktion\\14_QAInput\\01_konfiguration",
  "users_dir":              "\\\\SERVER\\Freigabe\\Produktion\\14_QAInput\\01_konfiguration\\01_benutzer",
  "products_dir":           "\\\\SERVER\\Freigabe\\Produktion\\14_QAInput\\01_konfiguration\\02_produkte",
  "process_templates_dir":  "\\\\SERVER\\Freigabe\\Produktion\\14_QAInput\\01_konfiguration\\03_prozess_templates",
  "vorlagen_dir":           "\\\\SERVER\\Freigabe\\Produktion\\14_QAInput\\01_konfiguration\\04_vorlagen",
  "audit_dir":              "\\\\SERVER\\Freigabe\\Produktion\\14_QAInput\\02_aufzeichnungen\\02_audit_trail",
  "downtime_dir":           "\\\\SERVER\\Freigabe\\Produktion\\14_QAInput\\02_aufzeichnungen\\03_stoerungen",
  "log_dir":                "\\\\SERVER\\Freigabe\\Produktion\\14_QAInput\\03_protokolle",
  "freigabedokumente_dir":  "\\\\SERVER\\Freigabe\\Produktion\\14_QAInput\\04_freigabedokumente"
}
```

Hinweise:
- In JSON wird jeder Backslash **doppelt** geschrieben (`\\`). UNC-Pfade beginnen
  daher mit `\\\\SERVER\\…`.
- Eine Variante mit Laufwerksbuchstaben (`X:\\Produktion\\14_QAInput\\…`) liegt als
  Vorlage in `deployment\config.json`.
- Nicht gesetzte Schlüssel fallen auf den `data`-Ordner **neben der Exe** zurück –
  in Produktion daher **alle** oben genannten Schlüssel setzen.
- `ui_prefs_dir` bewusst **nicht** setzen → landet lokal unter `%LOCALAPPDATA%\QAInput`.

---

## 6. Prüfen

1. App auf einer Station starten und anmelden.
2. Im Info-Dialog (ⓘ in der Kopfzeile) stehen die aufgelösten Pfade – müssen auf
   den Netzordner zeigen.
3. Beim Start schreibt die App `CONFIG_LOADED` in `…\02_aufzeichnungen\02_audit_trail\audit_log.jsonl`
   (Beleg, welche Configs mit welchem Hash/Freigabe-Status geladen wurden).
4. Ein Freigabedokument erzeugen → erscheint in `…\04_freigabedokumente\`.
5. Eine Störung erfassen → Zeile in `…\02_aufzeichnungen\03_stoerungen\stoerungen.jsonl`.
