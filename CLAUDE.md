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
```

No pytest installed. Only `openpyxl` is required as external dependency.

## Architecture

**Tkinter desktop app** for recording measurement values into Excel files. Operators never touch Excel directly.

### State & Navigation

All views share a single `AppState` instance (`src/domain/state.py`) passed via constructor. It holds the logged-in user, selected file/sheet, context (Charge/FA/Rolle), parsed headers, and a reference to the `AuditLogger`.

Views are stacked frames in `app.py` using `tkraise()`. Navigation is a callback `on_navigate(target: str)` where target is one of: `"login"`, `"file_select"`, `"context"`, `"form"`. Each view inherits `BaseView` (`src/ui/base_view.py`) with `on_show()`/`on_hide()` lifecycle hooks.

Flow: Login -> FileSelect -> Context -> Form (-> ReviewDialog modal -> write -> back to Form).

### Key Conventions

- **UI language is German** — all labels, messages, buttons.
- **Decimal input**: German format (`1.250,5`) and English (`1,250.5`) are both accepted. `src/domain/validation.py` normalizes by treating the last separator as the decimal point.
- **Excel column mapping**: `header_column_map` is `dict[str, int]` with 1-based column indices (matching openpyxl).
- **Context columns** (`Charge_#`, `FA_#`, `Rolle_#`) and **auto columns** (`Zeit`, `Mitarbeiter`) are defined in `src/config/settings.py` and excluded from the measurement form. Missing auto/context columns are created automatically on first write.
- **Audit**: Every significant action logs a JSONL line to `data/audit_log.jsonl`. The logger silently swallows write errors (prints to stderr) so it never crashes the app.
- **User database**: `data/users.kv` with format `user.<id>.<property>=<value>`. Properties: `password`, `qr`, `name`.

### Module Responsibilities

| Layer | Module | Role |
|-------|--------|------|
| Entry | `app.py` | Window, view instantiation, navigation |
| Config | `src/config/settings.py` | Paths, column names, window size |
| Domain | `src/domain/state.py` | `AppState`, `UserInfo`, `ContextInfo` |
| Domain | `src/domain/validation.py` | Decimal normalization, measurement validation |
| Auth | `src/auth/users_kv.py` | KV file parser |
| Auth | `src/auth/login.py` | `AuthService` (password + QR) |
| Excel | `src/excel/reader.py` | Read headers, validate, build column map |
| Excel | `src/excel/writer.py` | Append row, auto-create missing columns |
| Audit | `src/audit/audit_logger.py` | JSONL event logger |
| UI | `src/ui/*.py` | Tkinter views (login, file_select, context, form, review_dialog) |
