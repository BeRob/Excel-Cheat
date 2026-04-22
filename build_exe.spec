# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for QAInput.

Konfiguration fokussiert auf moeglichst niedrige AV-False-Positive-Rate
ohne Code-Signing-Zertifikat:

- Versionsresource (``version_info.txt``) mit Firma, Beschreibung und
  Originalnamen.
- ``--onedir`` statt ``--onefile``: keine entpackende Bootloader-Stage,
  deutlich weniger Heuristik-Treffer.
- ``upx=False``: UPX-gepackte PyInstaller-Binaries werden fast immer
  geflaggt.
- ``uac_admin=False``: kein UAC-Prompt noetig, wirkt weniger aggressiv.
- ``excludes``: grosse Libraries aus dem Bundle draussen halten
  reduziert Angriffsflaeche und Dateigroesse.
- ``noarchive=False``: gepackte Python-Module im Archiv sind
  Standard-Verhalten, nicht im Dateisystem.

Zusaetzliche Empfehlungen (nicht im Spec abbildbar):
- ``build.bat`` verwendet ``--clean`` fuer reproduzierbare Builds.
- Bei anhaltenden FPs den PyInstaller-Bootloader aus dem Source bauen
  (https://pyinstaller.org/en/stable/bootloader-building.html) oder
  ein Code-Signing-Zertifikat einsetzen.
"""

import os

block_cipher = None
ROOT = os.path.abspath('.')


a = Analysis(
    ['app.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        ('QUESTALPHA_StaticLogo_pos_rgb.png', '.'),
        ('Bedienungsanleitung.html', '.'),
        ('Kurzanleitung.html', '.'),
    ],
    hiddenimports=['openpyxl', 'PIL', 'PIL.Image', 'PIL.ImageTk'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'pytest', 'IPython', 'notebook', 'jupyter',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'tests',
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='QAInput',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',
    version='version_info.txt',
    uac_admin=False,
    uac_uiaccess=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='QAInput',
)
