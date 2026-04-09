# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for QAInput."""

import os

block_cipher = None

ROOT = os.path.abspath('.')

a = Analysis(
    ['app.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        ('data/app_config.json', 'data'),
        ('data/products', 'data/products'),
        ('QUESTALPHA_StaticLogo_pos_rgb.png', '.'),
    ],
    hiddenimports=['openpyxl'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas', 'PIL', 'pytest'],
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
    upx=True,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='QAInput',
)
