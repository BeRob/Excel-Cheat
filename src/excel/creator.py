"""Excel-Dateien aus einer Prozesskonfiguration erstellen."""

from __future__ import annotations

from datetime import datetime, date, timedelta
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side

from src.config.process_config import ProcessConfig, get_all_headers
from src.config.settings import HEADER_ROW


HEADER_FONT = Font(bold=True, size=11)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrapText=True)
THIN_BORDER = Border(
    left=Side("thin"), right=Side("thin"),
    top=Side("thin"), bottom=Side("thin"),
)
INFO_LABEL_FONT = Font(bold=True, size=10)

SHEET_PROTECTION_PASSWORD = "hexhex"


def _apply_sheet_protection(ws) -> None:
    """Sperrt das Blatt in Excel gegen Änderungen (Lesen bleibt möglich)."""
    ws.protection.sheet = True
    ws.protection.password = SHEET_PROTECTION_PASSWORD


def generate_file_name(
    process: ProcessConfig,
    product_id: str,
    shift: str,
    dt: date,
) -> str:
    """Format: {template_id}_{product_id}_Schicht{shift}_{YYYY-MM-DD}.xlsx"""
    date_str = dt.strftime("%Y-%m-%d")
    return f"{process.template_id}_{product_id}_Schicht{shift}_{date_str}.xlsx"


def get_shift_date(now: datetime, shift: str) -> date:
    """Für Schicht 3 nach Mitternacht wird der Vortag verwendet."""
    if shift == "3" and now.hour < 6:
        return (now - timedelta(days=1)).date()
    return now.date()


def find_existing_file(
    process: ProcessConfig,
    product_id: str,
    output_dir: Path,
    shift: str,
    dt: date,
) -> Path | None:
    name = generate_file_name(process, product_id, shift, dt)
    path = output_dir / name
    return path if path.exists() else None


def create_measurement_file(
    process: ProcessConfig,
    product_id: str,
    output_dir: Path,
    shift: str,
    dt: date,
) -> Path:
    """Legt eine neue Excel-Datei mit Kopfzeile an und gibt den Pfad zurück."""
    output_dir.mkdir(parents=True, exist_ok=True)

    name = generate_file_name(process, product_id, shift, dt)
    path = output_dir / name

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Messdaten"

    headers = get_all_headers(process)
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(HEADER_ROW, col_idx, header)
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN
        cell.border = THIN_BORDER

        width = max(len(header) + 4, 14)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    _apply_sheet_protection(ws)

    wb.save(path)
    wb.close()

    return path


def count_data_rows(filepath: Path) -> int:
    """Zählt Datenzeilen (ohne Info-Block und ohne Headerzeile).

    Wird beim Resume gebraucht, um Sequenz- und Nutzen-Zähler korrekt
    weiterzuführen.
    """
    try:
        wb = openpyxl.load_workbook(filepath, read_only=True)
        ws = wb.active
        count = max(ws.max_row - HEADER_ROW, 0)
        wb.close()
        return count
    except Exception:
        return 0


def write_info_header(
    filepath: Path,
    product_name: str,
    process_name: str,
    fa_nr: str,
    shift: str,
    dt: date,
) -> None:
    """Schreibt den Info-Block in die Zeilen 1-5.

    Wird nach dem Setzen der Kontextwerte aufgerufen, da die FA-Nr. erst
    dann bekannt ist.
    """
    try:
        wb = openpyxl.load_workbook(filepath)
    except Exception:
        return

    try:
        ws = wb.active
        info_rows = [
            ("Produkt:", product_name),
            ("Prozess:", process_name),
            ("FA-Nr.:", fa_nr),
            ("Schicht:", shift),
            ("Datum:", dt.strftime("%Y-%m-%d")),
        ]

        for row_idx, (label, value) in enumerate(info_rows, 1):
            cell_label = ws.cell(row_idx, 1, label)
            cell_label.font = INFO_LABEL_FONT
            ws.cell(row_idx, 2, value)

        wb.save(filepath)
    except Exception:
        pass
    finally:
        wb.close()
