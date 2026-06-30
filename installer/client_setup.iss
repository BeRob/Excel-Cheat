; QAInput — Client-Setup (Inno Setup 6)
; ---------------------------------------------------------------------------
; Installiert den Thin Client (QAInput.exe + _internal\ + config.json) nach
; Program Files. Alle Daten- und Schreibpfade liegen laut config.json auf dem
; Netzlaufwerk (UNC) und werden NICHT vom Client mitgeliefert.
;
; Gebaut über installer\build_installers.ps1 (setzt AppVersion/DistDir/CheckPath).
; baramundi-Silent-Aufruf:
;   QAInput-Setup-<ver>.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG="C:\Temp\qainput_install.log"
; ---------------------------------------------------------------------------

#define AppName "QAInput"
#define AppPublisher "Questalpha"
#define AppExeName "QAInput.exe"

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

; Pfad zum PyInstaller-Output (relativ zu dieser .iss); per /DDistDir überschreibbar.
#ifndef DistDir
  #define DistDir "..\dist\QAInput"
#endif

; Optionaler Erreichbarkeits-Check: UNC-Wurzel des Netzlaufwerks. Leer = kein Check.
#ifndef CheckPath
  #define CheckPath ""
#endif

[Setup]
AppId={{A3F1C2D4-5E6B-4F8A-9C0D-1E2F3A4B5C6D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=QAInput-Setup-{#AppVersion}
SetupLogging=yes

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; Flags: unchecked

[Files]
Source: "{#DistDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#DistDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; config.json mit UNC-Pfaden — eine vor Ort angepasste Variante beim Upgrade NICHT überschreiben.
Source: "config.client.json"; DestDir: "{app}"; DestName: "config.json"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Code]
function CmdLineParamExists(const Value: string): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), Value) = 0 then
    begin
      Result := True;
      Exit;
    end;
end;

function InitializeSetup(): Boolean;
var
  CheckPath: string;
begin
  Result := True;
  CheckPath := '{#CheckPath}';
  if CheckPath = '' then
    Exit;
  if CmdLineParamExists('/SKIPPATHCHECK') then
    Exit;
  if DirExists(CheckPath) then
    Exit;

  if WizardSilent() then
  begin
    // Silent (baramundi): evtl. SYSTEM-Kontext ohne Share-Zugriff → nur
    // protokollieren, nicht hart abbrechen. Der Runtime-Preflight der App
    // fängt fehlende Pfade später im Benutzerkontext ab.
    Log('WARN: Netzwerkpfad nicht erreichbar (Installation wird fortgesetzt): ' + CheckPath);
    Exit;
  end;

  if MsgBox('Der konfigurierte Netzwerkpfad ist nicht erreichbar:' + #13#10 +
            CheckPath + #13#10#13#10 +
            'Ohne erreichbares Netzlaufwerk startet die Anwendung später nicht.' + #13#10 +
            'Trotzdem mit der Installation fortfahren?',
            mbConfirmation, MB_YESNO) = IDYES then
    Result := True
  else
    Result := False;
end;
