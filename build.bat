@echo off
setlocal

echo === QAInput Build ===

:: 1. Alte Build-Artefakte aufraeumen (nur falls vorhanden)
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"

:: 2. PyInstaller mit Spec-Datei (einzige Wahrheitsquelle fuer Build-Optionen)
::    --clean:        loescht PyInstaller-Cache, verhindert gemischte Builds
::    --noconfirm:    keine Rueckfragen
::    build_exe.spec: definiert alle AV-relevanten Flags (noupx, onedir,
::                    version_info.txt, uac_admin=False, etc.)
echo Baue mit build_exe.spec...
pyinstaller --clean --noconfirm build_exe.spec
if errorlevel 1 (
    echo.
    echo FEHLER: PyInstaller-Build fehlgeschlagen.
    exit /b 1
)

:: 3. NUR die noetigen Konfigurationsdaten ins Build-Output kopieren.
::    Bewusst NICHT: users.kv, logs\, audit_log*, ui_prefs.json, _thin\,
::    freigabedokumente\ (Laufzeit-/sensible Daten, kommen vom Netzlaufwerk
::    bzw. werden vor Ort erzeugt). Pfade ueber <app>\config.json umbiegbar.
echo Kopiere Konfigurationsdaten...
if not exist "dist\QAInput\data" mkdir "dist\QAInput\data"
copy /Y "data\app_config.json" "dist\QAInput\data\" > nul

:: Prozess-Templates MUESSEN mit - sonst sind die duennen Produkt-Configs
:: zur Laufzeit nicht aufloesbar.
xcopy /E /I /Y "data\process_templates" "dist\QAInput\data\process_templates" > nul
if errorlevel 1 (
    echo FEHLER: Prozess-Templates konnten nicht kopiert werden.
    exit /b 1
)

:: Produkt-Configs + Freigabe-Manifest (freigaben.json liegt im products-Ordner).
:: Das _thin-Arbeitsverzeichnis wird ausgelassen.
if not exist "dist\QAInput\data\products" mkdir "dist\QAInput\data\products"
for %%F in ("data\products\*.json") do copy /Y "%%F" "dist\QAInput\data\products\" > nul

:: Optionale Word-Vorlage fuer Freigabedokumente (falls vorhanden).
if exist "data\vorlagen" xcopy /E /I /Y "data\vorlagen" "dist\QAInput\data\vorlagen" > nul

:: 4. config.json neben die exe (Netzwerkpfade), falls vorhanden.
if exist "config.json" copy /Y "config.json" "dist\QAInput\config.json" > nul

echo.
echo === Build abgeschlossen ===
echo Ausgabe: dist\QAInput\
echo Inhalt nach Zielordner kopieren (QAInput.exe + _internal\ + data\ + config.json).
endlocal
