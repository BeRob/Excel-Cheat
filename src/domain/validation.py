"""Validierung und Normalisierung von Messwert-Eingaben."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Ergebnis der Messwert-Validierung."""

    normalized_values: dict[str, float | None] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


def normalize_decimal(value_str: str) -> str:
    """Normalisiert Dezimaltrennzeichen für die float-Konvertierung.

    Erkennt deutsches Format (1.250,5) und englisches Format (1,250.5).
    Logik: Das letzte Trennzeichen ist der Dezimaltrenner.

    Args:
        value_str: Eingabe-String mit Komma oder Punkt.

    Returns:
        String mit Punkt als Dezimaltrennzeichen.
    """
    s = value_str.strip()
    if not s:
        return s

    last_comma = s.rfind(",")
    last_dot = s.rfind(".")

    if last_comma > last_dot:
        # Komma ist Dezimaltrenner (deutsch: 1.250,5)
        s = s.replace(".", "")
        s = s.replace(",", ".")
    elif last_dot > last_comma:
        # Punkt ist Dezimaltrenner (englisch: 1,250.5)
        s = s.replace(",", "")
    # Kein Trennzeichen oder nur eines -> standard float-Parsing funktioniert

    return s


def parse_numeric(value_str: str) -> float:
    """Parst einen String zu float nach Dezimal-Normalisierung.

    Args:
        value_str: Eingabe-String.

    Returns:
        float-Wert.

    Raises:
        ValueError: Wenn der Wert nicht numerisch ist.
    """
    normalized = normalize_decimal(value_str)
    if not normalized:
        raise ValueError("Leerer Wert")
    return float(normalized)


def validate_measurements(values: dict[str, str]) -> ValidationResult:
    """Validiert alle Messwert-Eingaben.

    Args:
        values: Dict mit Header-Name -> Eingabe-String.

    Returns:
        ValidationResult mit normalisierten Werten, Warnungen und Fehlern.
    """
    result = ValidationResult()

    for header, raw_value in values.items():
        stripped = raw_value.strip()

        if not stripped:
            result.warnings.append(f"{header} ist leer.")
            result.normalized_values[header] = None
            continue

        try:
            parsed = parse_numeric(stripped)
            result.normalized_values[header] = parsed
        except (ValueError, OverflowError):
            result.errors.append(f"{header}: '{stripped}' ist keine gültige Zahl.")
            result.normalized_values[header] = None

    return result
