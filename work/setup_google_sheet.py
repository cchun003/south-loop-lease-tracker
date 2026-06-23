#!/usr/bin/env python3
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".secrets" / "tracker.env"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


def load_env(path: Path) -> dict:
    env = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        env[key.strip()] = value
    return env


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def service_account_token(credentials_path: Path) -> str:
    info = json.loads(credentials_path.read_text(encoding="utf-8"))
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {
        "iss": info["client_email"],
        "scope": SHEETS_SCOPE,
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + b64url(json.dumps(claim, separators=(",", ":")).encode("utf-8"))
    ).encode("ascii")
    private_key = serialization.load_pem_private_key(
        info["private_key"].encode("utf-8"),
        password=None,
    )
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    assertion = signing_input.decode("ascii") + "." + b64url(signature)
    payload = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        token = json.loads(resp.read().decode("utf-8"))
    return token["access_token"]


def request_json(method: str, url: str, token: str, payload=None):
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {body}") from exc


def get_metadata(sheet_id: str, token: str) -> dict:
    params = urllib.parse.urlencode(
        {"fields": "spreadsheetId,properties.title,sheets.properties"}
    )
    return request_json("GET", f"{SHEETS_API}/{sheet_id}?{params}", token)


def get_values(sheet_id: str, token: str, a1_range: str) -> list:
    encoded_range = urllib.parse.quote(a1_range, safe="")
    params = urllib.parse.urlencode({"majorDimension": "ROWS"})
    url = f"{SHEETS_API}/{sheet_id}/values/{encoded_range}?{params}"
    return request_json("GET", url, token).get("values", [])


def batch_update(sheet_id: str, token: str, requests: list) -> dict:
    return request_json(
        "POST",
        f"{SHEETS_API}/{sheet_id}:batchUpdate",
        token,
        {"requests": requests},
    )


def values_batch_update(sheet_id: str, token: str, updates: list) -> dict:
    return request_json(
        "POST",
        f"{SHEETS_API}/{sheet_id}/values:batchUpdate",
        token,
        {"valueInputOption": "USER_ENTERED", "data": updates},
    )


def values_clear(sheet_id: str, token: str, ranges: list) -> dict:
    return request_json(
        "POST",
        f"{SHEETS_API}/{sheet_id}/values:batchClear",
        token,
        {"ranges": ranges},
    )


def sheet_rows():
    buildings_headers = [
        "building_id",
        "building_name",
        "neighborhood",
        "manager_or_owner",
        "official_url",
        "availability_url",
        "target_priority",
        "target_status",
        "preferred_base_rent",
        "hard_total_rent_cap",
        "bed_bath_target",
        "parking_need",
        "washer_dryer",
        "gym_required",
        "application_notes",
        "social_notes",
        "risk_flags",
        "last_checked",
        "source_notes",
    ]
    buildings = [
        [
            "coeval",
            "Coeval",
            "South Loop",
            "Greystar-linked",
            "https://coevalchicago.com/",
            "https://coevalchicago.com/floor-plans/",
            1,
            "top_candidate",
            3500,
            4000,
            "2B2B",
            "2 garage/covered spaces preferred",
            "required",
            "required",
            "Confirm F-1/no-SSN path and two parking spaces before application fees.",
            "Inquiry-only Reddit signal; check noise/wall soundproofing.",
            "noise_wall_check; no_ssn_unverified",
            "",
            "Seeded from local tracker and social addendum.",
        ],
        [
            "1400_wabash",
            "1400 Wabash",
            "South Loop",
            "Greystar",
            "https://1400wabash.com/",
            "https://1400wabash.com/floorplans/",
            2,
            "top_candidate",
            3500,
            4000,
            "2B2B",
            "2 garage/covered spaces preferred",
            "required",
            "required",
            "Prequalify Greystar no-SSN documents.",
            "Relatively favorable social signal; no direct F-1/no-SSN approval proof.",
            "two_parking_unverified; no_ssn_unverified",
            "",
            "Seeded from local tracker and social addendum.",
        ],
        [
            "1401_s_state",
            "1401 S State",
            "South Loop",
            "Greystar-linked",
            "https://www.1401southstate.com/",
            "https://www.1401southstate.com/chicago/1401-s-state/2-bedroom-apartments/",
            3,
            "top_candidate",
            3500,
            4000,
            "2B2B",
            "2 garage/covered spaces preferred",
            "required",
            "required",
            "Confirm total monthly cost, fees, F-1/no-SSN path.",
            "Tour signal positive on vibe/windows; utility and train/noise cautions.",
            "utility_cost_risk; holding_fee_check; transit_noise_check",
            "",
            "Seeded from local tracker and social addendum.",
        ],
        [
            "amli_900",
            "AMLI 900",
            "South Loop",
            "AMLI",
            "https://www.amli.com/apartments/chicago/south-loop-apartments/amli-900",
            "https://www.amli.com/apartments/chicago/south-loop-apartments/amli-900/floorplans",
            4,
            "policy_fallback",
            3700,
            4000,
            "2B2B",
            "2 garage/covered spaces preferred",
            "required",
            "required",
            "Strongest policy-clarity candidate; confirm exact no-SSN document package.",
            "Policy-positive, social mixed due noise/thin-wall concerns.",
            "price_risk; noise_wall_check",
            "",
            "Seeded from local tracker and social addendum.",
        ],
        [
            "roosevelt_collection",
            "Roosevelt Collection Lofts",
            "South Loop",
            "Bozzuto / Roosevelt Collection",
            "https://www.rooseveltcollection.com/lofts",
            "https://www.rooseveltcollection.com/lofts/floor-plans",
            5,
            "lifestyle_value_watch",
            3500,
            4000,
            "2B2B",
            "2 garage/covered spaces preferred",
            "required",
            "required",
            "Confirm new-lease vs takeover/sublet approval requirements.",
            "Strongest public Facebook/sublet lifestyle signal.",
            "sublet_price_not_official; f1_path_unverified",
            "",
            "Seeded from local tracker and social addendum.",
        ],
        [
            "aspire",
            "Aspire",
            "South Loop",
            "",
            "https://www.aspiresouthloop.com/",
            "https://www.aspiresouthloop.com/floorplans/",
            6,
            "conditional_high_value",
            3500,
            4000,
            "2B2B",
            "2 garage/covered spaces preferred",
            "required",
            "required",
            "Do not mark application-ready until guarantor/no-SSN rules are known.",
            "Good building fit, weak direct social/application evidence.",
            "guarantor_requirement_unknown; no_ssn_unverified",
            "",
            "Seeded from local tracker and social addendum.",
        ],
        [
            "arrive_lex",
            "Arrive LEX",
            "South Loop",
            "",
            "https://www.arrivelex.com/",
            "https://arrivelex.prospectportal.com/chicago-il-apartments/arrive-lex/conventional/",
            7,
            "conditional_value",
            3400,
            4000,
            "2B2B",
            "2 garage/covered spaces preferred",
            "required",
            "required",
            "Require building-specific F-1/no-SSN and parking confirmation.",
            "Limited mixed social evidence; avoid confusing with other Arrive properties.",
            "arrive_brand_confusion; application_path_unknown",
            "",
            "Seeded from local tracker and social addendum.",
        ],
        [
            "eleven40",
            "Eleven40",
            "South Loop",
            "",
            "https://live1140.com/",
            "https://live1140.com/floorplans/",
            10,
            "caution_watchlist",
            3500,
            4000,
            "2B2B",
            "2 garage/covered spaces preferred",
            "required",
            "required",
            "Only alert for exceptional unit or very strong price.",
            "Reddit area-awareness caution plus Xiaohongshu move-in/management complaint.",
            "move_in_condition_risk; management_response_risk",
            "",
            "Seeded from local tracker and social addendum.",
        ],
        [
            "the_reed",
            "The Reed at Southbank",
            "Southbank",
            "",
            "https://www.thereedsouthbank.com/",
            "https://www.thereedsouthbank.com/floorplans/",
            8,
            "southbank_lifestyle_stretch",
            3800,
            4000,
            "2B2B",
            "2 garage/covered spaces preferred",
            "required",
            "required",
            "Confirm official price, parking, and F-1/no-SSN path.",
            "Student-rental platform visibility, no approval proof.",
            "price_stretch; no_ssn_unverified",
            "",
            "Seeded from local tracker and social addendum.",
        ],
        [
            "grand_central",
            "The Grand Central / Alta Grand Central",
            "Southbank / Loop edge",
            "",
            "https://www.thegrandcentralapartments.com/",
            "https://www.thegrandcentralapartments.com/floorplans/",
            9,
            "watchlist",
            3500,
            4000,
            "2B2B",
            "2 garage/covered spaces preferred",
            "required",
            "required",
            "Require unit orientation/noise and application path check.",
            "Reddit area safety generally positive; highway/interchange noise caution.",
            "highway_interchange_noise; no_ssn_unverified",
            "",
            "Seeded from local tracker and social addendum.",
        ],
    ]

    units_headers = [
        "unit_key",
        "building_id",
        "building_name",
        "unit",
        "floorplan",
        "beds",
        "baths",
        "sqft",
        "base_rent",
        "estimated_total_rent",
        "available_date",
        "lease_term",
        "concessions",
        "fees_notes",
        "parking_available",
        "parking_monthly",
        "source_url",
        "source_type",
        "first_seen",
        "last_seen",
        "status",
        "score",
        "alert_level",
        "notes",
    ]
    history_headers = [
        "observed_at",
        "unit_key",
        "building_id",
        "building_name",
        "unit",
        "floorplan",
        "beds",
        "baths",
        "sqft",
        "base_rent",
        "estimated_total_rent",
        "available_date",
        "lease_term",
        "concessions",
        "source_url",
        "change_type",
        "previous_base_rent",
        "price_delta",
        "notes",
    ]
    alerts_headers = [
        "sent_at",
        "channel",
        "alert_level",
        "building_id",
        "building_name",
        "unit_key",
        "reason",
        "message",
        "source_url",
        "delivery_result",
        "dedupe_key",
    ]
    config_headers = ["key", "value", "notes"]
    config_rows = [
        ["tracker_name", "South Loop / Southbank 2B2B Lease Tracker", ""],
        ["timezone", "Asia/Hong_Kong", "User-local notification timezone."],
        ["market", "Chicago South Loop / Southbank", ""],
        ["bed_bath_target", "2B2B", ""],
        ["preferred_base_rent", "3500", "Aggressive alert threshold."],
        ["hard_total_rent_cap", "4000", "Excludes parking unless tracker later adds total-cost logic."],
        ["parking_spaces_required", "2", "Confirm garage/covered parking directly."],
        ["washer_dryer_required", "true", "In-unit preferred/required."],
        ["gym_required", "true", ""],
        ["application_profile", "Two UChicago F-1 students; one may lack SSN", ""],
        ["alert_channel", "企业微信", "Webhook stored locally in .secrets/tracker.env."],
        ["scrapling_enabled", "1", "Retry blocked public availability sources with Scrapling."],
        ["scrapling_fetcher", "stealthy", "Default enhanced fetcher for blocked/challenged sources."],
        ["scrapling_solve_cloudflare", "1", "Enable Scrapling Cloudflare handling on enhanced fetches."],
        ["scrapling_wait_ms", "2500", "Extra browser wait for captured vendor availability APIs."],
        ["scrapling_network_idle", "0", "Avoid waiting indefinitely on pages with tracking pings."],
        ["enhanced_vendor_parsers", "SightMap, RentCafe/Yardi, Knock Doorway", "Captured APIs parsed from official building pages."],
        [
            "urgent_alert_rule",
            "top candidate 2B2B under hard cap; price drop; new availability; rare under preferred threshold",
            "",
        ],
    ]
    run_log_headers = [
        "run_started_at",
        "run_finished_at",
        "status",
        "sources_checked",
        "units_seen",
        "new_units",
        "changed_units",
        "alerts_sent",
        "errors",
        "notes",
    ]
    source_status_headers = [
        "source_key",
        "observed_at",
        "building_id",
        "building_name",
        "source_name",
        "source_type",
        "parser",
        "status",
        "units_found",
        "target_units_found",
        "error",
        "url",
        "action",
        "notes",
    ]

    return {
        "Buildings": [buildings_headers] + buildings,
        "Units": [units_headers],
        "Unit_History": [history_headers],
        "Alerts": [alerts_headers],
        "Config": [config_headers] + config_rows,
        "Run_Log": [run_log_headers],
        "Source_Status": [source_status_headers],
    }


def ensure_sheets(sheet_id: str, token: str, desired_names: list) -> dict:
    metadata = get_metadata(sheet_id, token)
    props = {s["properties"]["title"]: s["properties"] for s in metadata["sheets"]}

    requests = []
    if "Buildings" not in props and "Sheet1" in props:
        sheet1_values = get_values(sheet_id, token, "Sheet1!A1:Z200")
        has_content = any(any(str(cell).strip() for cell in row) for row in sheet1_values)
        if not has_content:
            requests.append(
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": props["Sheet1"]["sheetId"],
                            "title": "Buildings",
                        },
                        "fields": "title",
                    }
                }
            )
            props["Buildings"] = {**props["Sheet1"], "title": "Buildings"}
            del props["Sheet1"]

    for name in desired_names:
        if name not in props:
            requests.append({"addSheet": {"properties": {"title": name}}})

    if requests:
        batch_update(sheet_id, token, requests)
    return get_metadata(sheet_id, token)


def format_sheets(sheet_id: str, token: str, metadata: dict, rows_by_sheet: dict):
    by_name = {s["properties"]["title"]: s["properties"] for s in metadata["sheets"]}
    requests = [
        {
            "updateSpreadsheetProperties": {
                "properties": {"title": "South Loop 2B2B Lease Tracker"},
                "fields": "title",
            }
        }
    ]
    for name, rows in rows_by_sheet.items():
        sheet_id_num = by_name[name]["sheetId"]
        col_count = max(len(rows[0]), 1)
        requests.extend(
            [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id_num,
                            "gridProperties": {
                                "frozenRowCount": 1,
                                "rowCount": max(200, len(rows) + 20),
                                "columnCount": max(col_count + 2, 12),
                            },
                        },
                        "fields": "gridProperties.frozenRowCount,gridProperties.rowCount,gridProperties.columnCount",
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id_num,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": col_count,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.08, "green": 0.18, "blue": 0.30},
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                },
                                "horizontalAlignment": "CENTER",
                                "wrapStrategy": "WRAP",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,wrapStrategy)",
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id_num,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": col_count,
                        },
                        "properties": {"pixelSize": 150},
                        "fields": "pixelSize",
                    }
                },
                {
                    "setBasicFilter": {
                        "filter": {
                            "range": {
                                "sheetId": sheet_id_num,
                                "startRowIndex": 0,
                                "endColumnIndex": col_count,
                            }
                        }
                    }
                },
            ]
        )
    batch_update(sheet_id, token, requests)


def main() -> int:
    env = load_env(ENV_PATH)
    credentials_path = Path(env["GOOGLE_APPLICATION_CREDENTIALS"])
    sheet_id = env["GOOGLE_SHEET_ID"]
    token = service_account_token(credentials_path)
    rows_by_sheet = sheet_rows()
    desired = list(rows_by_sheet)
    metadata = ensure_sheets(sheet_id, token, desired)

    ranges_to_clear = [f"{name}!A1:AZ250" for name in desired]
    values_clear(sheet_id, token, ranges_to_clear)
    updates = [
        {"range": f"{name}!A1", "values": rows}
        for name, rows in rows_by_sheet.items()
    ]
    values_batch_update(sheet_id, token, updates)
    metadata = get_metadata(sheet_id, token)
    format_sheets(sheet_id, token, metadata, rows_by_sheet)

    verify = {
        "spreadsheet_title": get_metadata(sheet_id, token)["properties"]["title"],
        "tabs": desired,
        "buildings_seeded": len(rows_by_sheet["Buildings"]) - 1,
        "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
    }
    print(json.dumps(verify, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
