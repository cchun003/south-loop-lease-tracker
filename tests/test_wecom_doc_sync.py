from __future__ import annotations

import urllib.error
import unittest
from unittest.mock import patch

from lease_tracker.wecom_doc_sync import (
    FieldSpec,
    TAB_CONFIGS,
    convert_cell_value,
    post_webhook,
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

    def test_post_webhook_retries_transient_url_errors(self) -> None:
        class Response:
            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"errcode": 0, "errmsg": "ok"}'

        with (
            patch(
                "lease_tracker.wecom_doc_sync.urllib.request.urlopen",
                side_effect=[urllib.error.URLError(TimeoutError("timed out")), Response()],
            ) as urlopen,
            patch("lease_tracker.wecom_doc_sync.time.sleep") as sleep,
        ):
            result = post_webhook("https://example.test/webhook", {"update_records": []})

        self.assertEqual(result["errcode"], 0)
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
