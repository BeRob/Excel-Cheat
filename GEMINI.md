# Messanwendung (Easy Mode)

## Project Overview

This is a Python-based desktop application designed to streamline the collection of measurement data and append it to Excel files. It replaces direct Excel editing to ensure data integrity, consistent formatting, and auditability.

The application allows users to:
- **Login** via password or QR code scanner.
- **Select** a target Excel file (`.xlsx`) representing a specific manufacturing process.
- **Set Context** (Batch #, FA #, Role) which persists across measurements.
- **Enter Data** into a dynamically generated form based on the Excel file's header row.
- **Review & Save** data, which appends a new row to the Excel file with timestamps and user info.
- **Audit Logging** tracks all key actions (login, writes, errors) in a central JSONL file.

**Architecture:**
- **Entry Point:** `app.py`
- **UI:** `tkinter` (Windows standard GUI)
- **Excel I/O:** `openpyxl`
- **Data Persistence:** Direct Excel manipulation (Append-only logic).
- **Authentication:** Simple Key-Value file (`data/users.kv`).
- **Audit:** JSONL logging to `data/audit_log.jsonl`.

## Building and Running

The project is a standard Python application.

### Prerequisites
- Python 3.11+
- `openpyxl` (Install via `pip install openpyxl`)
- Standard libraries: `tkinter`, `unittest`, `json`, `pathlib`.

### Running the Application
To start the application:

```bash
python app.py
```

### Running Tests
The project uses the standard `unittest` framework.

```bash
# Run all tests
python -m unittest discover tests
```

## Development Conventions

- **Project Structure:**
  - `src/`: Contains all source code divided by domain (ui, auth, excel, domain, audit).
  - `data/`: Stores runtime data like `users.kv` and `audit_log.jsonl`.
  - `tests/`: Contains unit tests mirroring the src structure.
  
- **Coding Style:**
  - Type hinting is used throughout (`from __future__ import annotations`).
  - Path handling uses `pathlib`.
  - UI logic is separated from business logic where possible.

- **Key Files:**
  - `planung.md`: Contains the detailed specification and "Definition of Done".
  - `src/config/settings.py`: Central configuration (paths, column names).
  - `data/users.kv`: User database (Plain text key-value).

## Usage Notes

- The application expects Excel files to have a header row (default row 1).
- Columns named `Charge_#`, `FA_#`, `Rolle_#` are treated as **Context Columns**.
- Columns named `Zeit`, `Mitarbeiter` are **Auto-Columns** (filled automatically).
- Decimal separator handling: The app accepts both `,` and `.` but normalizes to `.` internally for float storage (or writes them as numbers to Excel).
