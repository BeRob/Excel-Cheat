"""Excel-Lesefunktionen: Header lesen, Sheet-Erkennung, Validierung."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import openpyxl


@dataclass
class ExcelReadResult:
    """Ergebnis des Header-Lesens aus einer Excel-Datei."""

    sheet_names: list[str] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    header_column_map: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def read_excel_headers(
    filepath: str | Path,
    sheet_name: str | None = None,
    header_row: int = 1,
) -> ExcelReadResult:
    """Liest Header aus einer Excel-Datei.

    Args:
        filepath: Pfad zur .xlsx Datei.
        sheet_name: Name des Arbeitsblatts. None = erstes Blatt.
        header_row: Zeile mit den Spaltenüberschriften (1-basiert).

    Returns:
        ExcelReadResult mit Headers, Spalten-Map und ggf. Fehlern.
    """
    result = ExcelReadResult()

    try:
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    except FileNotFoundError:
        result.errors.append(f"Datei nicht gefunden: {filepath}")
        return result
    except PermissionError:
        result.errors.append("Datei ist gesperrt. Bitte Excel schließen.")
        return result
    except Exception as e:
        result.errors.append(f"Datei konnte nicht geöffnet werden: {e}")
        return result

    try:
        result.sheet_names = wb.sheetnames

        target_sheet = sheet_name if sheet_name else wb.sheetnames[0]
        if target_sheet not in wb.sheetnames:
            result.errors.append(f"Arbeitsblatt '{target_sheet}' nicht gefunden.")
            return result

        ws = wb[target_sheet]

        raw_headers: list = []
        for row in ws.iter_rows(
            min_row=header_row, max_row=header_row, values_only=True
        ):
            raw_headers = list(row)
            break

        if not raw_headers:
            result.errors.append("Keine Header-Zeile gefunden.")
            return result

        headers, col_map, errors = _clean_headers(raw_headers)
        result.headers = headers
        result.header_column_map = col_map
        result.errors = errors

    finally:
        wb.close()

    return result


def read_all_data(
    filepath: str | Path,
    sheet_name: str | None = None,
    header_row: int = 1,
) -> list[dict[str, any]]:
    """Liest alle Daten aus einer Excel-Datei.

    Args:
        filepath: Pfad zur .xlsx Datei.
        sheet_name: Name des Arbeitsblatts. None = erstes Blatt.
        header_row: Zeile mit den Spaltenüberschriften (1-basiert).

    Returns:
        Liste von Dictionaries (Spaltenname -> Wert).
    """
    try:
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    except Exception:
        return []

    try:
        target_sheet = sheet_name if sheet_name else wb.sheetnames[0]
        if target_sheet not in wb.sheetnames:
            return []

        ws = wb[target_sheet]
        
        # Get headers first
        raw_headers: list = []
        for row in ws.iter_rows(min_row=header_row, max_row=header_row, values_only=True):
            raw_headers = list(row)
            break
            
        if not raw_headers:
            return []
            
        headers, _, _ = _clean_headers(raw_headers)
        
        data = []
        # Iterate through all data rows after header
        for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
            if any(cell is not None for cell in row):
                row_dict = {}
                for idx, value in enumerate(row):
                    if idx < len(headers):
                        row_dict[headers[idx]] = value
                data.append(row_dict)
        
        return data
    finally:
        wb.close()


def _clean_headers(
    raw_headers: list,
) -> tuple[list[str], dict[str, int], list[str]]:
    """Bereinigt und validiert Header-Werte.

    - Leere Zellen erzeugen einen Fehler.
    - Duplikate erhalten Suffix _2, _3 usw.

    Returns:
        Tuple aus (bereinigte Header, Spalten-Map, Fehlerliste).
    """
    headers: list[str] = []
    col_map: dict[str, int] = {}
    errors: list[str] = []
    seen: dict[str, int] = {}

    for idx, value in enumerate(raw_headers):
        col_num = idx + 1  # 1-basiert

        if value is None or str(value).strip() == "":
            errors.append(f"Spalte {col_num} hat keinen Header.")
            continue

        name = str(value).strip()

        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1

        headers.append(name)
        col_map[name] = col_num

    return headers, col_map, errors
