; QAInput — Backend-Setup (Inno Setup 6)
; ---------------------------------------------------------------------------
; Richtet EINMALIG die Datenstruktur auf dem Netzlaufwerk ein (vom IT-Admin
; gegen die UNC-Freigabe ausgeführt). Legt die Ordnerstruktur passend zu
; config.client.json an und seedet die Startdateien aus installer\seed\.
;
; IDEMPOTENT: alle Seed-Dateien tragen das Flag onlyifdoesntexist — ein
; erneuter Lauf (z.B. nach Template-Update) überschreibt KEINE Produktivdaten,
; Audit-Logs oder Freigaben. Wie man Configs/Templates bewusst aktualisiert,
; steht in installer\README.md.
;
; KEINE NTFS-ACLs (bewusste Entscheidung) — Rechte setzt die IT separat
; (siehe README, Abschnitt „Berechtigungen").
;
; Aufruf (interaktiv):  QAInput-Backend-Setup-<ver>.exe
; Ziel-Root vorgeben:   ... /DIR="\\SERVER\Freigabe\Produktion\14_QAInput"
; ---------------------------------------------------------------------------

#define AppName "QAInput Backend"
#define AppPublisher "Questalpha"

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

; Verzeichnis mit der vorbereiteten Seed-Struktur (von build_installers.ps1 erzeugt).
#ifndef SeedDir
  #define SeedDir "seed"
#endif

[Setup]
AppId={{C9D2E3F4-1A2B-4C3D-8E4F-5A6B7C8D9E0F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName=\\SERVER\Freigabe\Produktion\14_QAInput
DisableProgramGroupPage=yes
DisableDirPage=no
Uninstallable=no
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=QAInput-Backend-Setup-{#AppVersion}
SetupLogging=yes

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Dirs]
; Schreibziele (zur Laufzeit von der App befüllt) — leer anlegen.
Name: "{app}\Audit"
Name: "{app}\Log"
Name: "{app}\Data\freigabedokumente"

[Files]
; Gesamte vorbereitete Seed-Struktur (Data\user, Data\config, Data\products,
; Data\process_templates, Data\vorlagen) — jede Datei nur, falls noch nicht da.
Source: "{#SeedDir}\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs onlyifdoesntexist

[Messages]
WelcomeLabel2=Dieses Setup richtet die QAInput-Datenstruktur auf dem Netzlaufwerk ein.%n%nWählen Sie als Ziel die UNC-Wurzel der Freigabe (z.B. \\SERVER\Freigabe\Produktion\14_QAInput). Vorhandene Dateien werden NICHT überschrieben.
