from __future__ import annotations

import unittest

from lease_tracker.wecom_doc_sync import (
    FieldSpec,
    TAB_CONFIGS,
    convert_cell_value,
    row_to_webhook_values,
    validate_schema,
)


class WeComDocSyncTest(unittest.TestCase):
    def test_convert_text_and_number_values(self) -> None:
        self.assertEqual(convert_cell_value("Arrive LEX", "text"), "Arrive LEX")
        self.assertEqual(convert_cell_value("$2,500", "number"), 2500)
        self.assertEqual(convert_cell_value("2.5", "number"), 2.5)
        self.assertIsNone(convert_cell_value("not public", "number"))

    def test_row_to_webhook_values_uses_field_ids_and_omits_blanks(self) -> None:
        schema = (
            FieldSpec("building_field", "Building", "text"),
            FieldSpec("rent_field", "Rent", "number"),
            FieldSpec("notes_field", "Notes", "text"),
        )

        values = row_to_webhook_values(
            {"Building": "Arrive LEX", "Rent": "2500", "Notes": ""},
            schema,
        )

        self.assertEqual(values["building_field"], "Arrive LEX")
        self.assertEqual(values["rent_field"], 2500)
        self.assertNotIn("notes_field", values)

    def test_units_schema_matches_expected_google_headers(self) -> None:
        units = TAB_CONFIGS[0]
        headers = [field.title for field in units.schema]
        validate_schema(units, headers)

    def test_validate_schema_rejects_schema_drift(self) -> None:
        units = TAB_CONFIGS[0]
        headers = [field.title for field in units.schema]
        headers[1] = "renamed_building_id"
        with self.assertRaisesRegex(RuntimeError, "schema mismatch"):
            validate_schema(units, headers)


if __name__ == "__main__":
    unittest.main()
