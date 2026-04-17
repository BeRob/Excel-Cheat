@echo off
setlocal

echo === QAInput Build ===

:: 1. Alte Build-Artefakte aufraeumen (nur falls vorhanden)
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"

:: 2. PyInstaller mit Spec-Datei (einzige Wahrheitsquelle fuer Build-Optionen)
::    --clean:           loescht PyInstaller-Cache, verhindert gemischte Builds
::    --noconfirm:       keine Rueckfragen
::    build_exe.spec:    definiert alle AV-relevanten Flags (noupx, onedir,
::                       version_info.txt, uac_admin=False, etc.)
echo Baue mit build_exe.spec...
pyinstaller --clean --noconfirm build_exe.spec
if errorlevel 1 (
    echo.
    echo FEHLER: PyInstaller-Build fehlgeschlagen.
    exit /b 1
)

:: 3. Datenordner ins Build-Output kopieren
::    Die exe erwartet data\ neben sich (siehe src\config\settings.py).
::    Bei Multi-Instance-Setup kann dieser Ordner auf dem Zielrechner durch
::    <app>\config.json mit "data_dir": ... auf ein Netzlaufwerk umgebogen
::    werden; der lokale data-Ordner ist dann nur Fallback.
echo Kopiere data-Ordner...
xcopy /E /I /Y "data" "dist\QAInput\data" > nul
if errorlevel 1 (
    echo FEHLER: data-Ordner konnte nicht kopiert werden.
    exit /b 1
)

echo.
echo === Build abgeschlossen ===
echo Ausgabe: dist\QAInput\
endlocal
