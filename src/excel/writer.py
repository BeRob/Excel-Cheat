"""Excel-Schreibfunktionen: Zeile anhaengen basierend auf Prozesskonfiguration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

from src.config.process_config import ProcessConfig


@dataclass
class WriteResult:
    """Ergebnis eines Schreibvorgangs."""

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
    """Haengt eine neue Messzeile an die Excel-Datei an.

    Die Spaltenreihenfolge ergibt sich aus process.fields.

    Args:
        filepath: Pfad zur .xlsx Datei.
        process: Prozesskonfiguration (definiert Spaltenreihenfolge).
        context_values: Kontext-Werte (display_name -> Wert).
        measurements: Messwerte (display_name -> Wert).
        auto_values: Auto-Werte (display_name -> Wert).

    Returns:
        WriteResult mit Erfolg/Fehler-Status.
    """
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
        result.error = f"Datei konnte nicht geoeffnet werden: {e}"
        return result

    try:
        ws = wb.active
        next_row = ws.max_row + 1

        # Spalten-Map aus Prozesskonfiguration aufbauen
        col_map: dict[str, int] = {}
        for idx, fd in enumerate(process.fields, 1):
            col_map[fd.display_name] = idx

        # Alle Wert-Quellen zusammenfuehren
        all_values: dict[str, str | float | None] = {}
        all_values.update(context_values)
        all_values.update(measurements)
        all_values.update(auto_values)

        # Werte in die richtige Spalte schreiben
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
