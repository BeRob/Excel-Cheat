"""Tests für die Messwert-Validierung."""

import unittest

from src.config.process_config import FieldDef
from src.domain.validation import normalize_decimal, parse_numeric, validate_measurements


class TestNormalizeDecimal(unittest.TestCase):

    def test_comma_as_decimal(self):
        self.assertEqual(normalize_decimal("3,4"), "3.4")

    def test_dot_as_decimal(self):
        self.assertEqual(normalize_decimal("3.4"), "3.4")

    def test_german_thousands(self):
        self.assertEqual(normalize_decimal("1.250,5"), "1250.5")

    def test_english_thousands(self):
        self.assertEqual(normalize_decimal("1,250.5"), "1250.5")

    def test_integer(self):
        self.assertEqual(normalize_decimal("1250"), "1250")

    def test_empty(self):
        self.assertEqual(normalize_decimal(""), "")

    def test_whitespace(self):
        self.assertEqual(normalize_decimal("  3,4  "), "3.4")


class TestParseNumeric(unittest.TestCase):

    def test_comma(self):
        self.assertAlmostEqual(parse_numeric("3,4"), 3.4)

    def test_dot(self):
        self.assertAlmostEqual(parse_numeric("3.4"), 3.4)

    def test_german_format(self):
        self.assertAlmostEqual(parse_numeric("1.250,5"), 1250.5)

    def test_integer(self):
        self.assertAlmostEqual(parse_numeric("42"), 42.0)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_numeric("abc")

    def test_empty(self):
        with self.assertRaises(ValueError):
            parse_numeric("")


class TestValidateMeasurementsLegacy(unittest.TestCase):
    """Tests ohne field_defs (Rückwärtskompatibilität)."""

    def test_valid_values(self):
        result = validate_measurements({"Laenge": "3,4", "Breite": "5.1"})
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.warnings), 0)
        self.assertAlmostEqual(result.normalized_values["Laenge"], 3.4)
        self.assertAlmostEqual(result.normalized_values["Breite"], 5.1)

    def test_empty_value_warning(self):
        result = validate_measurements({"Laenge": "3,4", "Breite": ""})
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.warnings), 1)
        self.assertIsNone(result.normalized_values["Breite"])

    def test_invalid_value_error(self):
        result = validate_measurements({"Laenge": "abc"})
        self.assertTrue(result.has_errors)
        self.assertEqual(len(result.errors), 1)

    def test_mixed(self):
        result = validate_measurements({"A": "3,4", "B": "", "C": "xyz"})
        self.assertTrue(result.has_errors)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(len(result.errors), 1)
        self.assertAlmostEqual(result.normalized_values["A"], 3.4)


class TestValidateWithFieldDefs(unittest.TestCase):
    """Tests mit typbasierter Validierung."""

    def _make_fields(self) -> list[FieldDef]:
        return [
            FieldDef(id="b1", display_name="Breite 1", type="number", role="measurement",
                     spec_min=180, spec_max=190),
            FieldDef(id="ask", display_name="ASK", type="choice", role="measurement",
                     options=["Ja", "Nein"]),
            FieldDef(id="bem", display_name="Bemerkungen", type="text", role="measurement",
                     optional=True),
            FieldDef(id="lot", display_name="LOT Nr.", type="text", role="context"),
        ]

    def test_number_valid(self):
        fields = self._make_fields()
        result = validate_measurements({"Breite 1": "185"}, field_defs=fields)
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.warnings), 0)
        self.assertAlmostEqual(result.normalized_values["Breite 1"], 185.0)

    def test_number_below_spec(self):
        fields = self._make_fields()
        result = validate_measurements({"Breite 1": "170"}, field_defs=fields)
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("unter Minimum", result.warnings[0])

    def test_number_above_spec(self):
        fields = self._make_fields()
        result = validate_measurements({"Breite 1": "200"}, field_defs=fields)
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("über Maximum", result.warnings[0])

    def test_number_invalid(self):
        fields = self._make_fields()
        result = validate_measurements({"Breite 1": "abc"}, field_defs=fields)
        self.assertTrue(result.has_errors)
        self.assertEqual(len(result.errors), 1)

    def test_choice_valid(self):
        fields = self._make_fields()
        result = validate_measurements({"ASK": "Ja"}, field_defs=fields)
        self.assertFalse(result.has_errors)
        self.assertEqual(result.normalized_values["ASK"], "Ja")

    def test_choice_invalid(self):
        fields = self._make_fields()
        result = validate_measurements({"ASK": "Vielleicht"}, field_defs=fields)
        self.assertTrue(result.has_errors)
        self.assertIn("keine gültige Auswahl", result.errors[0])

    def test_text_passthrough(self):
        fields = self._make_fields()
        result = validate_measurements({"LOT Nr.": "LOT-123"}, field_defs=fields)
        self.assertFalse(result.has_errors)
        self.assertEqual(result.normalized_values["LOT Nr."], "LOT-123")

    def test_optional_empty_no_warning(self):
        fields = self._make_fields()
        result = validate_measurements({"Bemerkungen": ""}, field_defs=fields)
        self.assertFalse(result.has_errors)
        # Optional fields that are empty get None but no warning
        self.assertIsNone(result.normalized_values["Bemerkungen"])
        self.assertEqual(len(result.warnings), 0)

    def test_required_empty_warning(self):
        fields = self._make_fields()
        result = validate_measurements({"Breite 1": ""}, field_defs=fields)
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.warnings), 1)

    def test_number_with_german_format(self):
        fields = self._make_fields()
        result = validate_measurements({"Breite 1": "185,5"}, field_defs=fields)
        self.assertFalse(result.has_errors)
        self.assertAlmostEqual(result.normalized_values["Breite 1"], 185.5)


class TestOosDetection(unittest.TestCase):
    """Out-of-Spec-Erkennung über die neue oos_fields-Menge."""

    def _fields(self) -> list[FieldDef]:
        return [
            FieldDef(id="b", display_name="Breite", type="number",
                     role="measurement", spec_min=180, spec_max=190),
            FieldDef(id="h", display_name="Höhe", type="number",
                     role="measurement", spec_min=10, spec_max=12),
        ]

    def test_no_oos_when_in_spec(self):
        result = validate_measurements(
            {"Breite": "185", "Höhe": "11"}, field_defs=self._fields(),
        )
        self.assertEqual(result.oos_fields, set())
        self.assertFalse(result.has_oos)

    def test_oos_below_minimum(self):
        result = validate_measurements(
            {"Breite": "170"}, field_defs=self._fields(),
        )
        self.assertIn("Breite", result.oos_fields)
        self.assertTrue(result.has_oos)

    def test_oos_above_maximum(self):
        result = validate_measurements(
            {"Breite": "200"}, field_defs=self._fields(),
        )
        self.assertIn("Breite", result.oos_fields)

    def test_oos_multiple_fields(self):
        result = validate_measurements(
            {"Breite": "170", "Höhe": "15"}, field_defs=self._fields(),
        )
        self.assertEqual(result.oos_fields, {"Breite", "Höhe"})

    def test_invalid_number_is_error_not_oos(self):
        result = validate_measurements(
            {"Breite": "abc"}, field_defs=self._fields(),
        )
        self.assertTrue(result.has_errors)
        self.assertEqual(result.oos_fields, set())


class TestRemarkPlaceholder(unittest.TestCase):
    """Bemerkungen-Gate: 'n/a' und Varianten zählen als nicht ausgefüllt."""

    def test_placeholders_invalid(self):
        from src.ui.review_dialog import _remark_is_valid
        for placeholder in ["", "  ", "n/a", "N/A", "n.a.", "NA",
                            "-", "—", "–", "  n/a  "]:
            self.assertFalse(
                _remark_is_valid(placeholder),
                f"{placeholder!r} sollte als ungültig gelten",
            )

    def test_real_remark_valid(self):
        from src.ui.review_dialog import _remark_is_valid
        for valid in ["Werkzeug stumpf", "Material zäh", "n/a ist okay"]:
            self.assertTrue(
                _remark_is_valid(valid),
                f"{valid!r} sollte als gültig gelten",
            )


if __name__ == "__main__":
    unittest.main()
