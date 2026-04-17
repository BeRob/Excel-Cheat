# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run app
python app.py

# Run all tests
python -m unittest discover -s tests -p "test_*.py" -v

# Run a single test file
python -m unittest tests.test_validation -v

# Run a specific test
python -m unittest tests.test_validation.TestNormalizeDecimal.test_german_thousands -v

# Build exe (Windows, requires pyinstaller)
build.bat
# Or directly:
pyinstaller build_exe.spec
```

No pytest. Only `openpyxl` is required as external dependency. Python 3.11+ (uses `X | Y` union syntax via `from __future__ import annotations`).

## Architecture

**Tkinter desktop app** for recording QA measurement values into Excel files. Operators select a product and process (defined in JSON config files), fill in context and measurement values, and the app writes rows to auto-generated Excel files. All UI is in German.

### State & Navigation

All views share a single `AppState` instance (`src/domain/state.py`) passed via constructor. Views are stacked frames using `tkraise()`. Navigation is a callback `on_navigate(target: str)` where target is one of: `"login"`, `"product_process"`, `"context"`, `"form"`. Each view inherits `BaseView` (`src/ui/base_view.py`) with `on_show()`/`on_hide()` lifecycle hooks. Every view constructor takes `(parent, app_state, on_navigate)`.

Flow: **Login -> ProductProcess -> Context -> Form** (-> ReviewDialog modal -> write -> back to Form).

### JSON-Based Configuration

Products and processes are defined in JSON files under `data/products/`. Each product file (e.g. `REF31962.json`) contains processes with typed field definitions (`FieldDef` dataclass in `src/config/process_config.py`). Fields have:
- **type**: `"text"`, `"number"`, or `"choice"`
- **role**: `"context"` (fixed per session or per measurement), `"measurement"` (numeric input), or `"auto"` (system-generated)
- **persistent**: `true` = value carries across measurements (e.g. FA-Nr.)
- **spec_min/spec_max/spec_target**: specification limits for number fields
- **optional**: `true` = may be left empty

Global settings (shifts, output directory) are in `data/app_config.json`. New products can be added by dropping a JSON file into `data/products/` or via the in-app Admin editor.

### Excel File Generation

Excel files are auto-created by `src/excel/creator.py` with a standardized name: `{ProcessID}_{ProductID}_Schicht{N}_{Date}.xlsx`. Rows 1-5 are an info header block (product, process, FA-Nr., shift, date). Row 6 is the column header. Data starts at row 7. The app supports resume: if a file for the same product/process/shift/date exists, it appends to it.

Each sheet is password-protected (`SHEET_PROTECTION_PASSWORD = "hexhex"` in `creator.py`) so operators can't edit values in Excel after the fact. openpyxl ignores sheet protection on load/save, so the app's own writer keeps working; the protection survives load/save cycles and is re-applied by nothing -- it's preserved automatically.

### Data Folder

The `data/` folder lives next to `app.py` (or next to the exe when bundled):
- `data/app_config.json` -- global settings (shifts, output directory)
- `data/products/*.json` -- product/process configuration files
- `data/users.kv` -- user database (gitignored)
- `data/audit_log.jsonl` -- audit log (gitignored)
- `data/configs/` -- legacy per-file classification JSONs (unused in current flow)

Both the data directory and the Excel output directory are overridable at deploy time. `src/config/settings.py` resolves them in this priority order:

1. **Env var** — `QAINPUT_DATA_DIR` / `QAINPUT_OUTPUT_DIR`.
2. **Bootstrap config** — `<APP_ROOT>/config.json` with optional keys `data_dir` and `output_dir` (absolute paths, `~` allowed). Malformed JSON → silently falls through to defaults.
3. **Default** — `<APP_ROOT>/data` / `<APP_ROOT>/output`.

The bootstrap `config.json` is intentionally separate from `app_config.json`: `app_config.json` lives inside the resolved `data_dir`, so using it to configure the data directory would be circular. `app_config.json`'s own `output_dir` and per-product `output_dir` keys continue to win over `OUTPUT_DIR` at the call site in `product_process_view.py`.

### Deployment Folder

`deployment/` is a local, gitignored copy of the minimum files needed to run the app (app entry, `src/`, `data/app_config.json`, `data/products/`, `data/users.kv`, `QUESTALPHA_StaticLogo_pos_rgb.png`, `Bedienungsanleitung.html`, `app.ico`, `build_exe.spec`, `build.bat`). It exists for packaging/handoff -- do not rely on anything there for development.

### Key Conventions

- **Decimal input**: German format (`1.250,5`) and English (`1,250.5`) both accepted. `src/domain/validation.py` normalizes by treating the last separator as the decimal point.
- **Auto columns** (`Datum`, `Bearbeiter`): not constants -- defined per process in the product JSON via `FieldDef` entries with `role: "auto"`. The info-header writer in `src/excel/creator.py` fills them when the file is created.
- **Info header / header row**: `HEADER_ROW = 6` in `settings.py`. Rows 1-5 are an info block (product, process, FA-Nr., shift, date), row 6 is the column header, data starts at row 7.
- **Theming**: `src/ui/theme.py` defines `COLORS`, `FONTS`, and `apply_theme(root)`. Use ttk styles (`Accent.TButton`, `Title.TLabel`, `Subtitle.TLabel`, `Success.TLabel`, `Error.TLabel`, `Warning.TLabel`) instead of inline color strings.
- **Audit**: Every significant action logs a JSONL line. `AuditLogger` uses inter-process file locking (Windows `msvcrt.locking`, Unix `fcntl.flock`) against a sibling `audit_log.jsonl.lock` file, so multiple app instances can append concurrently without corruption. Errors are printed to stderr, never raised -- the logger must not crash the app.
- **Multi-instance data access**: `data/app_config.json` and `data/users.kv` are read-only at runtime. `data/products/*.json` is written only by the admin config editor (rare, non-atomic `write_text`). `data/audit_log.jsonl` is designed for concurrent writes (see Audit above). Excel output files are assumed single-writer per (product, process, shift, date) -- no locking there.
- **User database**: `data/users.kv` with format `user.<id>.<property>=<value>`. Properties: `password`, `qr`, `name`. Users with `user.<id>.admin=true` get access to analysis and config editor tabs.
- **PyInstaller path handling**: `src/config/settings.py` uses `sys.frozen` / `sys.executable` to resolve `APP_ROOT`. Any code resolving resource paths at module level must follow this pattern.
- **Shift logic**: Shift 3 (22:00-06:00) crosses midnight. Workers after midnight get the previous day's date in the filename.
- **Row groups**: Some processes have `row_group_size` (e.g. 3 uses per roll). The app auto-counts "Nutzen 1 von 3" etc.
- **Output directory priority**: product-level `output_dir` > global `app_config.json` `output_dir` > default `output/`.
- **Validation fallback**: `validate_measurements()` accepts an optional `field_defs` list. Without it, it falls back to parsing every value as numeric -- legacy path kept for older callers; new code should always pass `field_defs`.
- **German umlauts in strings**: Tests assert on exact umlaut substrings (e.g. `"über Maximum"`, `"keine gültige Auswahl"`). Don't ASCII-ify error messages or docstrings.
- **Form display order vs. Excel column order**: `FormView` reorders the measurement-block display so choice (dropdown) fields come first; the Excel column order is unaffected because `write_measurement_row` builds its column map from `process.fields` (JSON order). Don't try to "unify" the two orders.
- **Choice field persistence**: In `FormView._clear_fields`, any field with `type == "choice"` keeps its value across measurements in addition to all `role == "context"` fields. The first choice widget (or the first measurement widget if none) is also the initial focus target on show/clear -- tracked via `_first_focus_widget`.

### Module Responsibilities

| Layer | Module | Role |
|-------|--------|------|
| Entry | `app.py` | Window, view instantiation, navigation, branded header bar |
| Config | `src/config/settings.py` | Paths, column names, window size, header row constants |
| Config | `src/config/process_config.py` | Dataclasses (`FieldDef`, `ProcessConfig`, `ProductConfig`, `ShiftDef`, `AppConfig`), JSON loading, field filter helpers, shift determination |
| Config | `src/config/config_writer.py` | Serialize dataclasses back to JSON, validation, save product config |
| Domain | `src/domain/state.py` | `AppState` (central mutable state), `UserInfo` |
| Domain | `src/domain/validation.py` | Decimal normalization, measurement validation (type-aware and legacy) |
| Auth | `src/auth/users_kv.py` | KV file parser |
| Auth | `src/auth/login.py` | `AuthService` (password + QR) |
| Excel | `src/excel/creator.py` | Create Excel files, generate filenames, write info header, find existing files, count data rows |
| Excel | `src/excel/reader.py` | Read headers and data from Excel (used by analysis view) |
| Excel | `src/excel/writer.py` | Append measurement row, `WriteResult` dataclass |
| Audit | `src/audit/audit_logger.py` | JSONL event logger |
| UI | `src/ui/theme.py` | Colors, fonts, ttk style configuration (Questalpha branding) |
| UI | `src/ui/login_view.py` | Password + QR login tabs |
| UI | `src/ui/product_process_view.py` | Product/process dropdowns, field overview, admin tabs (analysis + config editor) |
| UI | `src/ui/context_view.py` | Persistent context field entry (FA-Nr., LOT Nr., etc.) |
| UI | `src/ui/form_view.py` | Main measurement entry, spec feedback, keyboard nav, history table |
| UI | `src/ui/review_dialog.py` | Pre-save review modal with error/warning display |
| UI | `src/ui/analysis_view.py` | Admin-only data analysis table |
| UI | `src/ui/config_editor_view.py` | Admin-only product JSON editor with field editor dialog |
