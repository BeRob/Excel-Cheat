"""Tests für die Messwert-Validierung."""

import unittest

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


class TestValidateMeasurements(unittest.TestCase):

    def test_valid_values(self):
        result = validate_measurements({"Länge": "3,4", "Breite": "5.1"})
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.warnings), 0)
        self.assertAlmostEqual(result.normalized_values["Länge"], 3.4)
        self.assertAlmostEqual(result.normalized_values["Breite"], 5.1)

    def test_empty_value_warning(self):
        result = validate_measurements({"Länge": "3,4", "Breite": ""})
        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.warnings), 1)
        self.assertIsNone(result.normalized_values["Breite"])

    def test_invalid_value_error(self):
        result = validate_measurements({"Länge": "abc"})
        self.assertTrue(result.has_errors)
        self.assertEqual(len(result.errors), 1)

    def test_mixed(self):
        result = validate_measurements({"A": "3,4", "B": "", "C": "xyz"})
        self.assertTrue(result.has_errors)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(len(result.errors), 1)
        self.assertAlmostEqual(result.normalized_values["A"], 3.4)


if __name__ == "__main__":
    unittest.main()
