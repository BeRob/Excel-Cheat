"""Messzeile an eine bestehende Excel-Datei anhängen."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openpyxl

from src.config.process_config import ProcessConfig


@dataclass
class WriteResult:
    success: bool = False
    row_number: int | None = None
    error: str | None = None


def write_measurement_row(
    filepath: str | Path,
    process: ProcessConfig,
    context_values: dict[str, str],
    measurements: dict[str, float | str | None],
    auto_values: dict[str, str | float | None],
) -> WriteResult:
    """Hängt eine Messzeile an. Die Spaltenreihenfolge folgt `process.fields`."""
    result = WriteResult()

    try:
        wb = openpyxl.load_workbook(filepath)
    except PermissionError:
        result.error = "Datei ist gesperrt. Bitte Excel schliessen und erneut versuchen."
        return result
    except FileNotFoundError:
        result.error = f"Datei nicht gefunden: {filepath}"
        return result
    except Exception as e:
        result.error = f"Datei konnte nicht geöffnet werden: {e}"
        return result

    try:
        ws = wb.active
        next_row = ws.max_row + 1

        col_map = {fd.display_name: idx for idx, fd in enumerate(process.fields, 1)}

        all_values: dict[str, str | float | None] = {}
        all_values.update(context_values)
        all_values.update(measurements)
        all_values.update(auto_values)

        for display_name, col_idx in col_map.items():
            value = all_values.get(display_name)
            if value is not None:
                ws.cell(row=next_row, column=col_idx, value=value)

        wb.save(filepath)
        result.success = True
        result.row_number = next_row

    except PermissionError:
        result.error = "Datei ist gesperrt. Bitte Excel schliessen und erneut versuchen."
    except Exception as e:
        result.error = f"Unerwarteter Fehler beim Schreiben: {e}"
    finally:
        wb.close()

    return result
