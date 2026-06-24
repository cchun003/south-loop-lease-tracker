from __future__ import annotations

import unittest

from lease_tracker.query_bot import (
    build_query_context,
    detect_buildings,
    detect_rent_cap,
    is_addressed_to_bot,
    wants_target_layout,
)


UNITS = [
    {
        "building_id": "arrive_lex",
        "building_name": "Arrive LEX",
        "unit": "A",
        "beds": "2",
        "baths": "2",
        "estimated_total_rent": "3299",
        "available_date": "2026-07-01",
        "status": "available",
    },
    {
        "building_id": "arrive_lex",
        "building_name": "Arrive LEX",
        "unit": "B",
        "beds": "2",
        "baths": "2",
        "estimated_total_rent": "3600",
        "available_date": "2026-07-15",
        "status": "available",
    },
    {
        "building_id": "the_reed",
        "building_name": "The Reed at Southbank",
        "unit": "R",
        "beds": "2",
        "baths": "2",
        "estimated_total_rent": "4100",
        "available_date": "2026-08-01",
        "status": "available",
    },
]


class QueryBotTest(unittest.TestCase):
    def test_address_detection(self) -> None:
        self.assertTrue(is_addressed_to_bot("South Loop Tracker Arrive Lex现在有多少available lease"))
        self.assertTrue(is_addressed_to_bot("@South Loop Tracker 查一下Aspire"))
        self.assertTrue(is_addressed_to_bot("@Tracker Bot 查一下Aspire", "Tracker Bot"))
        self.assertFalse(is_addressed_to_bot("Arrive Lex现在有多少available lease"))

    def test_building_aliases_do_not_match_the_stopword(self) -> None:
        self.assertEqual(detect_buildings("what are the available leases"), [])
        self.assertEqual(detect_buildings("Arrive Lex现在有多少available lease"), ["arrive_lex"])
        self.assertIn("the_reed", detect_buildings("The Reed has what available?"))

    def test_layout_and_rent_cap_detection(self) -> None:
        self.assertTrue(wants_target_layout("Arrive Lex 2B2B 3500以下"))
        self.assertEqual(detect_rent_cap("Arrive Lex 2B2B 3500以下"), 3500)
        self.assertEqual(detect_rent_cap("under 4000"), 4000)

    def test_context_prefilters_units_before_prompting(self) -> None:
        context = build_query_context(
            "Arrive Lex 2B2B 3500以下现在有多少available lease",
            UNITS,
            [],
            [],
        )
        self.assertEqual(context["matched_buildings"], ["Arrive LEX"])
        self.assertEqual(context["counts"]["available_total"], 1)
        self.assertEqual(context["counts"]["available_2b2b_under_3500"], 1)
        self.assertEqual(len(context["units"]), 1)
        self.assertEqual(context["units"][0]["unit"], "A")


if __name__ == "__main__":
    unittest.main()
