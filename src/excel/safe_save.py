"""Atomares Speichern von openpyxl-Workbooks."""

from __future__ import annotations

import os
from pathlib import Path


def save_workbook_atomic(wb, filepath: str | Path) -> None:
    """Speichert erst in eine Temp-Datei im Zielordner und ersetzt dann per Rename.

    Ein Absturz oder Netzabriss mitten im Save kann so nie eine bestehende
    Chargendatei zerstören — es liegt immer entweder die alte oder die neue
    vollständige Version vor. Die Temp-Datei liegt im selben Ordner, damit
    os.replace auf demselben Volume (auch SMB) atomar bleibt.
    """
    filepath = Path(filepath)
    tmp = filepath.with_name(filepath.name + ".tmp~")
    try:
        wb.save(tmp)
        with open(tmp, "rb+") as f:
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, filepath)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
