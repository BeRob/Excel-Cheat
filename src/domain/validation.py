"""Validierung und Normalisierung von Messwert-Eingaben."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.process_config import FieldDef


# Einzelner Trenner mit genau drei Folgeziffern: "1.250" kann deutsche
# Tausenderschreibweise (1250) oder englischer Dezimalwert (1,25) sein.
# Solche Eingaben werden abgelehnt statt geraten — ein 1000-fach
# fehlinterpretierter Messwert wäre ein Datenintegritätsfehler (ALCOA+).
# Führende 0 ("0,500") bleibt erlaubt, da als Tausenderschreibweise sinnlos.
_AMBIGUOUS_DECIMAL_RE = re.compile(r"^[1-9]\d{0,2}[.,]\d{3}$")


def is_ambiguous_decimal(value_str: str) -> bool:
    """True, wenn die Eingabe nicht eindeutig als Dezimalwert lesbar ist."""
    return _AMBIGUOUS_DECIMAL_RE.match(value_str.strip()) is not None


@dataclass
class ValidationResult:
    normalized_values: dict[str, float | str | None] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    oos_fields: set[str] = field(default_factory=set)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_oos(self) -> bool:
        return len(self.oos_fields) > 0


def normalize_decimal(value_str: str) -> str:
    """Bringt Dezimaltrenner in ein Format, das float() frisst.

    Sowohl das deutsche Format (1.250,5) als auch das englische (1,250.5)
    werden akzeptiert. Entscheidend ist: das letzte Trennzeichen ist der
    Dezimaltrenner.
    """
    s = value_str.strip()
    if not s:
        return s

    last_comma = s.rfind(",")
    last_dot = s.rfind(".")

    if last_comma > last_dot:
        s = s.replace(".", "").replace(",", ".")
    elif last_dot > last_comma:
        s = s.replace(",", "")

    return s


def parse_numeric(value_str: str) -> float:
    normalized = normalize_decimal(value_str)
    if not normalized:
        raise ValueError("Leerer Wert")
    return float(normalized)


def validate_measurements(
    values: dict[str, str],
    field_defs: list[FieldDef] | None = None,
) -> ValidationResult:
    """Validiert alle Messwerte.

    `values` bildet Feld-Anzeigename -> Rohstring ab. Ohne `field_defs`
    wird zur Rückwärtskompatibilität jeder Wert numerisch geparst.
    """
    result = ValidationResult()

    field_map: dict[str, FieldDef] = {}
    if field_defs:
        for fd in field_defs:
            field_map[fd.display_name] = fd

    for header, raw_value in values.items():
        stripped = raw_value.strip()
        fd = field_map.get(header)

        if not stripped:
            if fd and fd.optional:
                result.normalized_values[header] = None
            elif fd:
                # Pflichtfeld leer = Fehler, nicht nur Warnung: eine leere
                # Zelle ohne Begründung im Chargen-Record verletzt ALCOA+
                # („complete"). Entwerten läuft über default_value "n/a".
                result.errors.append(f"{header}: Pflichtfeld ist leer.")
                result.normalized_values[header] = None
            else:
                # Legacy-Pfad ohne FieldDefs: Verhalten unverändert (Warnung).
                result.warnings.append(f"{header} ist leer.")
                result.normalized_values[header] = None
            continue

        if fd:
            _validate_typed(header, stripped, fd, result)
        else:
            _validate_numeric(header, stripped, result)

    return result


def _validate_typed(
    header: str, value: str, fd: FieldDef, result: ValidationResult
) -> None:
    if fd.type == "number":
        if is_ambiguous_decimal(value):
            result.errors.append(
                f"{header}: '{value}' ist mehrdeutig (Tausender- oder "
                f"Dezimaltrenner?). Bitte ohne Tausendertrenner eingeben "
                f"(z. B. 1250) oder den Dezimalwert eindeutig schreiben "
                f"(z. B. 1,25)."
            )
            result.normalized_values[header] = None
            return
        try:
            parsed = parse_numeric(value)
            result.normalized_values[header] = parsed
            if fd.spec_min is not None and parsed < fd.spec_min:
                result.warnings.append(
                    f"{header}: {parsed} liegt unter Minimum {fd.spec_min}"
                )
                result.oos_fields.add(header)
            if fd.spec_max is not None and parsed > fd.spec_max:
                result.warnings.append(
                    f"{header}: {parsed} liegt über Maximum {fd.spec_max}"
                )
                result.oos_fields.add(header)
        except (ValueError, OverflowError):
            result.errors.append(f"{header}: '{value}' ist keine gültige Zahl.")
            result.normalized_values[header] = None

    elif fd.type == "choice":
        if fd.options and value not in fd.options:
            result.errors.append(
                f"{header}: '{value}' ist keine gültige Auswahl. "
                f"Erlaubt: {', '.join(fd.options)}"
            )
            result.normalized_values[header] = None
        else:
            result.normalized_values[header] = value

    else:
        result.normalized_values[header] = value


def _validate_numeric(header: str, value: str, result: ValidationResult) -> None:
    if is_ambiguous_decimal(value):
        result.errors.append(
            f"{header}: '{value}' ist mehrdeutig (Tausender- oder "
            f"Dezimaltrenner?). Bitte ohne Tausendertrenner eingeben "
            f"(z. B. 1250) oder den Dezimalwert eindeutig schreiben "
            f"(z. B. 1,25)."
        )
        result.normalized_values[header] = None
        return
    try:
        parsed = parse_numeric(value)
        result.normalized_values[header] = parsed
    except (ValueError, OverflowError):
        result.errors.append(f"{header}: '{value}' ist keine gültige Zahl.")
        result.normalized_values[header] = None
