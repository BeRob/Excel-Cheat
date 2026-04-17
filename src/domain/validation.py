"""Validierung und Normalisierung von Messwert-Eingaben."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.process_config import FieldDef


@dataclass
class ValidationResult:
    normalized_values: dict[str, float | str | None] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


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
            else:
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
        try:
            parsed = parse_numeric(value)
            result.normalized_values[header] = parsed
            if fd.spec_min is not None and parsed < fd.spec_min:
                result.warnings.append(
                    f"{header}: {parsed} liegt unter Minimum {fd.spec_min}"
                )
            if fd.spec_max is not None and parsed > fd.spec_max:
                result.warnings.append(
                    f"{header}: {parsed} liegt über Maximum {fd.spec_max}"
                )
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
    try:
        parsed = parse_numeric(value)
        result.normalized_values[header] = parsed
    except (ValueError, OverflowError):
        result.errors.append(f"{header}: '{value}' ist keine gültige Zahl.")
        result.normalized_values[header] = None
