"""Messzeile an eine bestehende Excel-Datei anhängen."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openpyxl

from src.config.settings import HEADER_ROW


@dataclass
class WriteResult:
    success: bool = False
    row_number: int | None = None
    error: str | None = None


def _build_col_map(ws) -> dict[str, int]:
    """Liest die Spaltenüberschriften aus der Datei – verhindert Spaltenshift bei Config-Änderungen."""
    col_map = {}
    for col in range(1, ws.max_column + 1):
        val = ws.cell(HEADER_ROW, col).value
        if val is not None:
            col_map[str(val)] = col
    return col_map


def write_measurement_row(
    filepath: str | Path,
    process,
    context_values: dict[str, str],
    measurements: dict[str, float | str | None],
    auto_values: dict[str, str | float | None],
) -> WriteResult:
    """Hängt eine Messzeile an. Spaltenposition wird aus der Datei gelesen, nicht aus process.fields."""
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
        col_map = _build_col_map(ws)

        all_values: dict[str, str | float | None] = {}
        all_values.update(context_values)
        all_values.update(measurements)
        all_values.update(auto_values)

        for display_name, value in all_values.items():
            col_idx = col_map.get(display_name)
            if col_idx is not None and value is not None:
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


def write_measurement_rows(
    filepath: str | Path,
    rows: list[dict[str, str | float | None]],
) -> WriteResult:
    """Hängt mehrere Messzeilen in einem Schreibvorgang an (für Multi-Nutzen)."""
    result = WriteResult()
    if not rows:
        result.error = "Keine Zeilen zum Schreiben."
        return result

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
        col_map = _build_col_map(ws)
        next_row = ws.max_row + 1

        for row_data in rows:
            for display_name, value in row_data.items():
                col_idx = col_map.get(display_name)
                if col_idx is not None and value is not None:
                    ws.cell(row=next_row, column=col_idx, value=value)
            next_row += 1

        wb.save(filepath)
        result.success = True
        result.row_number = next_row - 1

    except PermissionError:
        result.error = "Datei ist gesperrt. Bitte Excel schliessen und erneut versuchen."
    except Exception as e:
        result.error = f"Unerwarteter Fehler beim Schreiben: {e}"
    finally:
        wb.close()

    return result
