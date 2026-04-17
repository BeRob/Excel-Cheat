# QAInput - Sichere Messwerterfassung
## PowerPoint-Präsentation: Inhalte

---

## Folie 1: Titel

**QAInput - Sichere Messwerterfassung**

*Lösung für GxP-konforme IPC-Datenerfassung*

---

## Folie 2: Ausgangssituation - Das Audit-Finding

**Feststellung bei internem/externem Audit:**

- IPC-Daten (In-Process Control) werden direkt in Excel erfasst
- **Keine Zugriffskontrolle** - jeder kann Werte ändern
- **Kein Audit-Trail** - Änderungen nicht nachvollziehbar
- **Keine Datenintegrität** - Manipulation möglich
- Verstoß gegen ALCOA+-Prinzipien (Attributable, Legible, Contemporaneous, Original, Accurate)

**Risiko:** Abweichung bei GMP-Audits / FDA-Inspektionen

---

## Folie 3: Die Lösung - QAInput

**Einfache Desktop-Anwendung für die Produktion**

- Mitarbeiter erfassen Messwerte über eine **geführte Eingabemaske**
- **Kein direkter Excel-Zugriff** mehr für Bediener
- Automatischer, unveränderlicher **Audit-Trail**
- **Benutzer-Authentifizierung** mit Passwort oder QR-Badge

---

## Folie 4: Vorteile auf einen Blick

| Bereich | Vorteil |
|---------|---------|
| **Compliance** | Vollständiger Audit-Trail (Wer, Was, Wann) |
| **Datenintegrität** | Excel-Dateien bleiben schreibgeschützt |
| **Mitarbeiter** | Kein Mehraufwand - einfachere Eingabe als Excel |
| **Führungskräfte** | Keine Änderung - Excel wie gewohnt lesbar |
| **IT** | Keine Admin-Rechte nötig, keine Installation |

---

## Folie 5: Bestehende Tabellen weiter nutzen

**Keine Migration notwendig!**

- Vorhandene Excel-Dateien werden **unverändert weiterverwendet**
- App erkennt Spaltenstruktur automatisch
- Einmalige Konfiguration: Welche Spalten sind "fest" (z.B. Charge), welche sind Messwerte
- Konfiguration wird als kleine JSON-Datei gespeichert

**Ergebnis:** Bestehende Daten bleiben erhalten, neue Daten sind geschützt

---

## Folie 6: So funktioniert's - Der Ablauf

```
1. Login      → Mitarbeiter meldet sich an (Passwort oder QR-Scan)
2. Datei      → Excel-Datei und Arbeitsblatt auswählen
3. Kontext    → Feste Werte eingeben (Charge, FA, Rolle...)
4. Erfassung  → Messwerte eingeben + Prüfen + Speichern
5. Fertig     → Daten landen in Excel, Audit-Log wird geschrieben
```

**Automatisch erfasst:** Zeitstempel, Mitarbeiter-ID

---

## Folie 7: Audit-Trail - Lückenlose Dokumentation

**Jede Aktion wird protokolliert:**

```json
{
  "ts": "2025-01-15T10:23:45+01:00",
  "event": "row_written",
  "user": "mueller",
  "file": "IPC_Messwerte_2025.xlsx",
  "context": {"Charge": "CH-2025-001", "FA": "12345"}
}
```

- Format: JSONL (JSON Lines) - maschinenlesbar
- Unveränderlich durch Append-Only-Prinzip
- Erfüllt FDA 21 CFR Part 11 Anforderungen

---

## Folie 8: Excel bleibt gesperrt - aber lesbar

**Für Bediener:**

- Kein direkter Schreibzugriff auf Excel-Dateien
- Nur über die App können Werte eingetragen werden

**Für Führungskräfte / QS:**

- Excel-Dateien können **wie gewohnt geöffnet** werden
- Berichte, Pivot-Tabellen, Auswertungen - alles bleibt möglich
- Keine Änderung im täglichen Ablauf beim Lesen der Daten

---

## Folie 9: Einfach für die IT

**Minimaler Aufwand:**

- **Keine Installation** - portable .exe Datei
- **Keine Admin-Rechte** erforderlich
- **Keine Datenbank** - nur Excel + kleine Konfigurationsdateien
- **Keine Serverinfrastruktur** notwendig
- Einzige Abhängigkeit: Excel-Dateien auf Netzlaufwerk

**Deployment:** Kopieren → Fertig

---

## Folie 10: Zusammenfassung

| Anforderung aus Audit | Umsetzung |
|-----------------------|-----------|
| Manipulationsschutz | Bediener haben keinen direkten Excel-Zugriff |
| Audit-Trail | JSONL-Log mit Zeitstempel, User, Aktion |
| Nachvollziehbarkeit | Automatische Erfassung von Zeit + Mitarbeiter |
| Datenintegrität | Validierung bei Eingabe, kontrolliertes Schreiben |

**Ergebnis:** GxP-konforme Messwerterfassung ohne Prozessänderung

---

## Folie 11: Nächste Schritte

1. Pilotphase in ausgewähltem Bereich
2. Schulung der Mitarbeiter (ca. 15 min)
3. Rollout auf weitere Bereiche
4. Abschluss des CAPA zum Audit-Finding
