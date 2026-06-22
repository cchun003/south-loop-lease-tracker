from __future__ import annotations


BUILDINGS = [
    {
        "id": "coeval",
        "name": "Coeval",
        "priority": 1,
        "status": "top_candidate",
        "application_note": "Greystar-linked; F-1/no-SSN path must be prequalified.",
        "risk_tags": ["F-1 path unverified", "noise/wall check", "parking unconfirmed"],
        "sources": [
            {
                "name": "official",
                "type": "official",
                "url": "https://coevalchicago.com/floor-plans/",
                "parser": "spaces",
            },
            {
                "name": "apartments_backup",
                "type": "backup",
                "url": "https://www.apartments.com/coeval-chicago-il/n9160mq/",
                "parser": "jsonld_floorplans",
            },
        ],
    },
    {
        "id": "1400_wabash",
        "name": "1400 Wabash",
        "priority": 2,
        "status": "top_candidate",
        "application_note": "Greystar-managed; prequalify no-SSN documents.",
        "risk_tags": ["F-1 path unverified", "parking unconfirmed"],
        "sources": [
            {
                "name": "official",
                "type": "official",
                "url": "https://1400wabash.com/floorplans/",
                "parser": "spaces",
            },
            {
                "name": "zillow_backup",
                "type": "backup",
                "url": "https://www.zillow.com/apartments/chicago-il/1400-wabash/Ck5m5W/",
                "parser": "jsonld_floorplans",
            },
        ],
    },
    {
        "id": "1401_s_state",
        "name": "1401 S State",
        "priority": 3,
        "status": "top_candidate",
        "application_note": "Greystar-linked; verify total monthly cost and F-1/no-SSN path.",
        "risk_tags": ["utility cost risk", "transit noise check", "parking unconfirmed"],
        "sources": [
            {
                "name": "official",
                "type": "official",
                "url": "https://www.1401southstate.com/chicago/1401-s-state/2-bedroom-apartments/",
                "parser": "jsonld_floorplans",
            },
            {
                "name": "apartments_backup",
                "type": "backup",
                "url": "https://www.apartments.com/1401-s-state-chicago-il/4nfye8j/",
                "parser": "jsonld_floorplans",
            },
        ],
    },
    {
        "id": "amli_900",
        "name": "AMLI 900",
        "priority": 4,
        "status": "policy_fallback",
        "application_note": "Best policy clarity; confirm exact no-SSN document package.",
        "risk_tags": ["AMLI policy clearer", "noise/wall check", "parking unconfirmed"],
        "sources": [
            {
                "name": "official",
                "type": "official",
                "url": "https://www.amli.com/apartments/chicago/south-loop-apartments/amli-900/floorplans",
                "parser": "amli_next",
            },
        ],
    },
    {
        "id": "roosevelt_collection",
        "name": "Roosevelt Collection Lofts",
        "priority": 5,
        "status": "lifestyle_value_watch",
        "application_note": "Confirm new lease vs takeover/sublet requirements.",
        "risk_tags": ["F-1 path unverified", "sublet price not official", "parking unconfirmed"],
        "sources": [
            {
                "name": "official",
                "type": "official",
                "url": "https://www.rooseveltcollection.com/lofts/floor-plans",
                "parser": "jsonld_floorplans",
            },
            {
                "name": "bozzuto_backup",
                "type": "backup",
                "url": "https://www.bozzuto.com/apartments-for-rent/il/chicago/roosevelt-collection-lofts/floor-plans",
                "parser": "jsonld_floorplans",
            },
            {
                "name": "apartments_backup",
                "type": "backup",
                "url": "https://www.apartments.com/roosevelt-collection-lofts-chicago-il/3w2802d/",
                "parser": "jsonld_floorplans",
            },
        ],
    },
    {
        "id": "aspire",
        "name": "Aspire",
        "priority": 6,
        "status": "conditional_high_value",
        "application_note": "Do not mark application-ready until guarantor/no-SSN rules are known.",
        "risk_tags": ["guarantor unknown", "F-1 path unverified", "parking unconfirmed"],
        "sources": [
            {
                "name": "official",
                "type": "official",
                "url": "https://www.aspiresouthloop.com/floorplans/",
                "parser": "jsonld_floorplans",
            },
            {
                "name": "apartments_backup",
                "type": "backup",
                "url": "https://www.apartments.com/aspire-chicago-il/dtdhkwk/",
                "parser": "jsonld_floorplans",
            },
            {
                "name": "redfin_backup",
                "type": "backup",
                "url": "https://www.redfin.com/IL/Chicago/Aspire/apartment/178606257",
                "parser": "jsonld_floorplans",
            },
        ],
    },
    {
        "id": "arrive_lex",
        "name": "Arrive LEX",
        "priority": 7,
        "status": "conditional_value",
        "application_note": "Require building-specific F-1/no-SSN and two-parking confirmation.",
        "risk_tags": ["Arrive brand confusion", "application path unknown", "parking unconfirmed"],
        "sources": [
            {
                "name": "official",
                "type": "official",
                "url": "https://arrivelex.prospectportal.com/chicago-il-apartments/arrive-lex/conventional/",
                "parser": "jsonld_floorplans",
            },
            {
                "name": "apartments_backup",
                "type": "backup",
                "url": "https://www.apartments.com/arrive-lex-chicago-il/qv2k7sy/",
                "parser": "jsonld_floorplans",
            },
        ],
    },
    {
        "id": "eleven40",
        "name": "Eleven40",
        "priority": 10,
        "status": "caution_watchlist",
        "application_note": "Only alert for exceptional unit or very strong price.",
        "risk_tags": ["move-in condition risk", "management response risk", "area awareness"],
        "sources": [
            {
                "name": "official",
                "type": "official",
                "url": "https://live1140.com/floorplans/",
                "parser": "jsonld_floorplans",
            },
        ],
    },
    {
        "id": "the_reed",
        "name": "The Reed at Southbank",
        "priority": 8,
        "status": "southbank_lifestyle_stretch",
        "application_note": "Confirm official price, parking, and F-1/no-SSN path.",
        "risk_tags": ["price stretch", "F-1 path unverified", "parking unconfirmed"],
        "sources": [
            {
                "name": "official_apts",
                "type": "official",
                "url": "https://thereedapts.com/floor-plans/",
                "parser": "reed_html",
            },
            {
                "name": "uhouzz_backup",
                "type": "backup",
                "url": "https://www.uhouzz.com/us/chicago/detail-apartments-1567688",
                "parser": "jsonld_floorplans",
            },
        ],
    },
    {
        "id": "grand_central",
        "name": "The Grand Central / Alta Grand Central",
        "priority": 9,
        "status": "watchlist",
        "application_note": "Require unit orientation/noise and application path check.",
        "risk_tags": ["highway/interchange noise", "F-1 path unverified", "parking unconfirmed"],
        "sources": [
            {
                "name": "official",
                "type": "official",
                "url": "https://www.thegrandcentralapartments.com/floorplans/",
                "parser": "jsonld_floorplans",
            },
        ],
    },
]


BUILDING_BY_ID = {building["id"]: building for building in BUILDINGS}

