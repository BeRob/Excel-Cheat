<#
.SYNOPSIS
    Baut QAInput reproduzierbar und erzeugt Client- + Backend-Setup (Inno Setup).

.DESCRIPTION
    1. PyInstaller-onedir-Build via build.bat (-> dist\QAInput\).
    2. Liest die Version aus src\version.py (Single Source of Truth).
    3. Staged die Seed-Struktur fürs Backend-Setup nach installer\seed\.
    4. Kompiliert client_setup.iss und backend_setup.iss mit ISCC.exe.
    Ergebnis: installer\Output\QAInput-Setup-<ver>.exe und
              installer\Output\QAInput-Backend-Setup-<ver>.exe

.PARAMETER CheckPath
    Optionale UNC-Wurzel, die das Client-Setup auf Erreichbarkeit prüft
    (z.B. \\SERVER\Freigabe\Produktion\14_QAInput). Leer = kein Check.

.PARAMETER SkipBuild
    PyInstaller-Build überspringen (dist\QAInput\ muss schon existieren).

.EXAMPLE
    .\build_installers.ps1
    .\build_installers.ps1 -CheckPath '\\SERVER\Freigabe\Produktion\14_QAInput'
#>
[CmdletBinding()]
param(
    [string]$CheckPath = '',
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$InstallerDir = $PSScriptRoot
$RepoRoot     = Split-Path -Parent $InstallerDir

function Find-ISCC {
    $cmd = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    throw "ISCC.exe (Inno Setup 6) nicht gefunden. Bitte Inno Setup installieren oder in den PATH legen."
}

# --- 1. PyInstaller-Build ---------------------------------------------------
if (-not $SkipBuild) {
    Write-Host '=== PyInstaller-Build (build.bat) ===' -ForegroundColor Cyan
    Push-Location $RepoRoot
    try {
        & cmd.exe /c 'build.bat'
        if ($LASTEXITCODE -ne 0) { throw "build.bat fehlgeschlagen (Exit $LASTEXITCODE)." }
    } finally {
        Pop-Location
    }
}

$DistDir = Join-Path $RepoRoot 'dist\QAInput'
if (-not (Test-Path (Join-Path $DistDir 'QAInput.exe'))) {
    throw "dist\QAInput\QAInput.exe fehlt — Build zuerst ausführen (ohne -SkipBuild)."
}

# --- 2. Version aus src\version.py ------------------------------------------
Push-Location $RepoRoot
try {
    $Version = (& python -c 'from src.version import APP_VERSION; print(APP_VERSION)').Trim()
} finally {
    Pop-Location
}
if (-not $Version) { throw 'Version konnte nicht aus src\version.py gelesen werden.' }
Write-Host "Version: $Version" -ForegroundColor Green

# --- 3. Seed-Struktur fürs Backend-Setup ------------------------------------
# Layout muss zu config.client.json passen:
#   Data\user, Data\config, Data\products, Data\process_templates, Data\vorlagen
Write-Host '=== Seed-Struktur vorbereiten ===' -ForegroundColor Cyan
$Seed = Join-Path $InstallerDir 'seed'
if (Test-Path $Seed) { Remove-Item $Seed -Recurse -Force }
$null = New-Item -ItemType Directory -Force -Path `
    (Join-Path $Seed 'Data\user'), `
    (Join-Path $Seed 'Data\config'), `
    (Join-Path $Seed 'Data\products'), `
    (Join-Path $Seed 'Data\process_templates'), `
    (Join-Path $Seed 'Data\vorlagen')

$DataDir = Join-Path $RepoRoot 'data'
function Copy-IfExists($src, $dst) {
    if (Test-Path $src) { Copy-Item $src $dst -Recurse -Force }
}
Copy-IfExists (Join-Path $DataDir 'app_config.json')        (Join-Path $Seed 'Data\config')
Copy-IfExists (Join-Path $DataDir 'products\*.json')        (Join-Path $Seed 'Data\products')
Copy-IfExists (Join-Path $DataDir 'process_templates\*.json') (Join-Path $Seed 'Data\process_templates')
Copy-IfExists (Join-Path $DataDir 'vorlagen\*')            (Join-Path $Seed 'Data\vorlagen')
# users.kv: nur die Vorlage seeden (echte Datenbank legt die IT an).
Copy-IfExists (Join-Path $InstallerDir 'templates\users.kv.template') (Join-Path $Seed 'Data\user\users.kv')

# --- 4. Inno Setup kompilieren ----------------------------------------------
$ISCC = Find-ISCC
Write-Host "=== Inno Setup ($ISCC) ===" -ForegroundColor Cyan
$Output = Join-Path $InstallerDir 'Output'
$null = New-Item -ItemType Directory -Force -Path $Output

$clientArgs = @(
    "/DAppVersion=$Version",
    "/DDistDir=$DistDir"
)
if ($CheckPath) { $clientArgs += "/DCheckPath=$CheckPath" }
$clientArgs += (Join-Path $InstallerDir 'client_setup.iss')

& $ISCC @clientArgs
if ($LASTEXITCODE -ne 0) { throw "Client-Setup-Kompilierung fehlgeschlagen (Exit $LASTEXITCODE)." }

& $ISCC "/DAppVersion=$Version" (Join-Path $InstallerDir 'backend_setup.iss')
if ($LASTEXITCODE -ne 0) { throw "Backend-Setup-Kompilierung fehlgeschlagen (Exit $LASTEXITCODE)." }

Write-Host ''
Write-Host '=== Fertig ===' -ForegroundColor Green
Get-ChildItem $Output -Filter '*.exe' | ForEach-Object { Write-Host "  $($_.FullName)" }
