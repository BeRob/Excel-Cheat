"""Excel-Schreibfunktionen: Zeile anhaengen, Auto-Spalten erstellen."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import openpyxl

from src.config.settings import AUTO_COLUMNS
from src.domain.state import UserInfo


@dataclass
class WriteResult:
    """Ergebnis eines Schreibvorgangs."""

    success: bool = False
    row_number: int | None = None
    error: str | None = None
    columns_created: list[str] = field(default_factory=list)


def write_measurement_row(
    filepath: str | Path,
    sheet_name: str,
    header_column_map: dict[str, int],
    persistent_values: dict[str, str],
    user: UserInfo,
    measurements: dict[str, float | None],
    timestamp: datetime | None = None,
) -> WriteResult:
    """Haengt eine neue Messzeile an die Excel-Datei an.

    Args:
        filepath: Pfad zur .xlsx Datei.
        sheet_name: Name des Arbeitsblatts.
        header_column_map: Mapping Header-Name -> Spaltennummer (1-basiert).
        persistent_values: Feste Werte (Header -> Wert).
        user: Benutzer-Informationen.
        measurements: Normalisierte Messwerte (Header -> float oder None).
        timestamp: Zeitstempel (optional, Standard: jetzt).

    Returns:
        WriteResult mit Erfolg/Fehler-Status.
    """
    result = WriteResult()
    ts = timestamp or datetime.now()

    try:
        wb = openpyxl.load_workbook(filepath)
    except PermissionError:
        result.error = "Datei ist gesperrt. Bitte Excel schließen und erneut versuchen."
        return result
    except FileNotFoundError:
        result.error = f"Datei nicht gefunden: {filepath}"
        return result
    except Exception as e:
        result.error = f"Datei konnte nicht geöffnet werden: {e}"
        return result

    try:
        if sheet_name not in wb.sheetnames:
            result.error = f"Arbeitsblatt '{sheet_name}' nicht gefunden."
            return result

        ws = wb[sheet_name]

        # Auto-Spalten erstellen falls noetig
        col_map = dict(header_column_map)
        created = _ensure_auto_columns(ws, col_map)
        result.columns_created = created

        # Naechste freie Zeile
        next_row = ws.max_row + 1

        # Feste Werte schreiben
        for col_name, value in persistent_values.items():
            if col_name in col_map:
                ws.cell(row=next_row, column=col_map[col_name], value=value)

        # Auto-Spalten schreiben
        if "Zeit" in col_map:
            ws.cell(row=next_row, column=col_map["Zeit"], value=ts)
        if "Mitarbeiter" in col_map:
            ws.cell(row=next_row, column=col_map["Mitarbeiter"], value=user.user_id)

        # Messwerte schreiben
        for header, value in measurements.items():
            if header in col_map and value is not None:
                ws.cell(row=next_row, column=col_map[header], value=value)

        wb.save(filepath)
        result.success = True
        result.row_number = next_row

    except PermissionError:
        result.error = "Datei ist gesperrt. Bitte Excel schließen und erneut versuchen."
    except Exception as e:
        result.error = f"Unerwarteter Fehler beim Schreiben: {e}"
    finally:
        wb.close()

    return result


def _ensure_auto_columns(
    ws, col_map: dict[str, int]
) -> list[str]:
    """Stellt sicher, dass Auto-Spalten (Zeit, Mitarbeiter) existieren.

    Fehlende Spalten werden am Ende angefuegt. col_map wird in-place aktualisiert.

    Returns:
        Liste der neu erstellten Spaltennamen.
    """
    created: list[str] = []

    next_col = max(col_map.values(), default=0) + 1

    for col_name in AUTO_COLUMNS:
        if col_name not in col_map:
            ws.cell(row=1, column=next_col, value=col_name)
            col_map[col_name] = next_col
            created.append(col_name)
            next_col += 1

    return created
