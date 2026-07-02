"""Event-Namens-Konstanten für das Audit-Log.

Alle audit.log_event()-Aufrufe sollten diese Konstanten benutzen, damit
keine Tippfehler in Event-Strings landen und nachträgliche Auswertungen
sauber filterbar bleiben.
"""

from __future__ import annotations


class Event:
    APP_START = "app_start"
    APP_EXIT = "app_exit"

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAIL = "login_fail"
    LOGOUT = "logout"

    NAVIGATE = "navigate"

    PRODUCT_SELECT = "product_select"
    PROCESS_SELECT = "process_select"
    OUTPUT_DIR_CHOSEN = "output_dir_chosen"

    CONTEXT_SET = "context_set"
    FILE_CREATED = "file_created"
    FILE_RESUMED = "file_resumed"
    FILE_CREATE_FAIL = "file_create_fail"
    FILE_RESUME_FAIL = "file_resume_fail"
    INFO_HEADER_FAIL = "info_header_fail"

    REVIEW_OPENED = "review_opened"
    REVIEW_CANCELLED = "review_cancelled"
    OOS_BLOCKED = "oos_blocked"

    WRITE_ATTEMPT = "write_attempt"
    WRITE_SUCCESS = "write_success"
    WRITE_FAIL = "write_fail"
    FIELDS_CLEARED = "fields_cleared"

    NUTZEN_COUNT_CHANGED = "nutzen_count_changed"
    LAYOUT_TOGGLED = "layout_toggled"
    DARK_MODE_TOGGLED = "dark_mode_toggled"
    FONT_SCALED = "font_scaled"
    HISTORY_COLUMNS_CHANGED = "history_columns_changed"
    HISTORY_TOGGLED = "history_toggled"

    CONFIG_EDITED = "config_edited"
    CONFIG_LOADED = "config_loaded"
    CONFIG_RELEASED = "config_released"
    CONTEXT_EDIT_REQUESTED = "context_edit_requested"

    PREFLIGHT_OK = "preflight_ok"
    PREFLIGHT_FAIL = "preflight_fail"

    # Störungs-/Stillstandserfassung — Breadcrumbs ins zentrale Audit-Log.
    # System-of-Record ist der eigene Störungs-Store (data/.../stoerungen.jsonl).
    STOERUNG_START = "stoerung_start"
    STOERUNG_ENDE = "stoerung_ende"
    STOERUNG_FAIL = "stoerung_fail"

    EXCEPTION = "exception"
