"""Tests für den Out-of-Spec-Gate des Review-Dialogs (reine Logik, ohne Tk)."""

import unittest

from src.config.process_config import FieldDef
from src.domain.validation import ValidationResult
from src.ui.review_dialog import (
    _remark_display_name,
    collect_oos_details,
    oos_blocked_sections_multi,
    oos_blocked_sections_single,
)


def _fields(remark_name: str = "Bemerkungen") -> list[FieldDef]:
    return [
        FieldDef(id="breite", display_name="Breite", type="number",
                 role="measurement", spec_min=180, spec_max=190),
        FieldDef(id="bemerkungen", display_name=remark_name, type="text",
                 role="measurement", optional=True, default_value="n/a"),
    ]


def _oos_result(value: float = 200.0) -> ValidationResult:
    result = ValidationResult()
    result.normalized_values["Breite"] = value
    result.oos_fields.add("Breite")
    return result


class TestSingleGate(unittest.TestCase):

    def test_oos_without_remark_blocks(self):
        raw = {"Breite": "200", "Bemerkungen": "n/a"}
        self.assertEqual(
            oos_blocked_sections_single(raw, _oos_result(), _fields()),
            ["Messwerte"],
        )

    def test_oos_with_real_remark_passes(self):
        raw = {"Breite": "200", "Bemerkungen": "Werkzeug stumpf"}
        self.assertEqual(
            oos_blocked_sections_single(raw, _oos_result(), _fields()),
            [],
        )

    def test_in_spec_never_blocks(self):
        raw = {"Breite": "185", "Bemerkungen": "n/a"}
        self.assertEqual(
            oos_blocked_sections_single(raw, ValidationResult(), _fields()),
            [],
        )

    def test_remark_field_found_by_id_not_display_name(self):
        # Prozess mit abweichendem Anzeigenamen: Gate muss das Feld über die
        # id "bemerkungen" finden, sonst wäre OoS-Speichern unmöglich.
        fields = _fields(remark_name="Kommentar QS")
        self.assertEqual(_remark_display_name(fields), "Kommentar QS")
        raw = {"Breite": "200", "Kommentar QS": "Materialcharge zäh"}
        self.assertEqual(
            oos_blocked_sections_single(raw, _oos_result(), fields), [],
        )

    def test_remark_display_name_fallback(self):
        self.assertEqual(_remark_display_name([]), "Bemerkungen")
        self.assertEqual(_remark_display_name(None), "Bemerkungen")


class TestMultiGate(unittest.TestCase):

    def test_only_oos_nutzen_without_remark_listed(self):
        nutzen_values = [
            {"Breite": "185", "Bemerkungen": "n/a"},      # in Spec
            {"Breite": "200", "Bemerkungen": "n/a"},      # OoS ohne Bemerkung
            {"Breite": "200", "Bemerkungen": "Randstück"},  # OoS begründet
        ]
        nutzen_validations = [ValidationResult(), _oos_result(), _oos_result()]
        blocked = oos_blocked_sections_multi(
            nutzen_values, nutzen_validations, ValidationResult(), _fields(),
        )
        self.assertEqual(blocked, ["Nutzen 2"])

    def test_shared_oos_without_any_remark_blocks(self):
        nutzen_values = [{"Breite": "185", "Bemerkungen": "n/a"}]
        blocked = oos_blocked_sections_multi(
            nutzen_values, [ValidationResult()], _oos_result(), _fields(),
        )
        self.assertEqual(blocked, ["Gemeinsame Werte"])

    def test_shared_oos_with_one_valid_remark_passes(self):
        nutzen_values = [
            {"Breite": "185", "Bemerkungen": "n/a"},
            {"Breite": "185", "Bemerkungen": "Schälspalt nachjustiert"},
        ]
        blocked = oos_blocked_sections_multi(
            nutzen_values, [ValidationResult(), ValidationResult()],
            _oos_result(), _fields(),
        )
        self.assertEqual(blocked, [])


class TestCollectOosDetails(unittest.TestCase):

    def test_details_contain_value_and_limits(self):
        details = collect_oos_details(_oos_result(200.0), _fields())
        self.assertEqual(details, [{
            "field": "Breite",
            "value": 200.0,
            "spec_min": 180,
            "spec_max": 190,
        }])

    def test_no_oos_empty(self):
        self.assertEqual(collect_oos_details(ValidationResult(), _fields()), [])


if __name__ == "__main__":
    unittest.main()
