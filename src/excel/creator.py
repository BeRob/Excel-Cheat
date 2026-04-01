"""Excel-Dateien aus Prozesskonfiguration erstellen."""

from __future__ import annotations

from datetime import datetime, date, timedelta
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side

from src.config.process_config import ProcessConfig, get_all_headers

HEADER_FONT = Font(bold=True, size=11)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrapText=True)
THIN_BORDER = Border(
    left=Side("thin"), right=Side("thin"),
    top=Side("thin"), bottom=Side("thin"),
)


def generate_file_name(
    process: ProcessConfig,
    product_id: str,
    shift: str,
    dt: date,
) -> str:
    """Erzeugt den standardisierten Dateinamen.

    Format: {template_id}_{product_id}_Schicht{shift}_{YYYY-MM-DD}.xlsx
    """
    date_str = dt.strftime("%Y-%m-%d")
    return f"{process.template_id}_{product_id}_Schicht{shift}_{date_str}.xlsx"


def get_shift_date(now: datetime, shift: str) -> date:
    """Bestimmt das Datum fuer die Datei.

    Fuer Schicht 3 (Nachtschicht nach Mitternacht) wird das Datum
    des Vortages verwendet, da die Schicht vor Mitternacht begann.
    """
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
    """Prüft ob eine Datei fuer diese Kombination bereits existiert."""
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
    """Erstellt eine neue Excel-Datei mit Header-Zeile.

    Args:
        process: Prozesskonfiguration.
        product_id: Produkt-ID fuer Dateinamen.
        output_dir: Ausgabeverzeichnis.
        shift: Schichtnummer ("1", "2", "3").
        dt: Datum fuer Dateinamen.

    Returns:
        Pfad zur erstellten Datei.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    name = generate_file_name(process, product_id, shift, dt)
    path = output_dir / name

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Messdaten"

    headers = get_all_headers(process)
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(1, col_idx, header)
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN
        cell.border = THIN_BORDER

    # Spaltenbreiten anpassen
    for col_idx, header in enumerate(headers, 1):
        width = max(len(header) + 4, 14)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    wb.save(path)
    wb.close()

    return path


def count_data_rows(filepath: Path) -> int:
    """Zaehlt vorhandene Datenzeilen (ohne Header).

    Nuetzlich fuer Resume: Sequenz-Counter (Pruefmuster) und
    Row-Group-Counter (Nutzen) initialisieren.
    """
    try:
        wb = openpyxl.load_workbook(filepath, read_only=True)
        ws = wb.active
        count = max(ws.max_row - 1, 0)  # -1 fuer Header
        wb.close()
        return count
    except Exception:
        return 0
