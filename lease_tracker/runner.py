from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .config import BUILDING_BY_ID, BUILDINGS
from .deepseek import maybe_summarize_alert
from .google_sheets import GoogleSheetsClient, rows_to_dicts
from .http_client import blocked_reason, fetch_url, polite_pause
from .models import SourceResult, Unit
from .notifier import build_alert_message, build_source_recovered_message, send_wecom_markdown
from .parsers import parse_units
from .settings import HARD_RENT_CAP, PREFERRED_RENT, SHEET_TABS


UNIT_HEADERS = [
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

HISTORY_HEADERS = [
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

ALERT_HEADERS = [
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

RUN_LOG_HEADERS = [
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

SOURCE_STATUS_HEADERS = [
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


@dataclass
class TrackerRunResult:
    run_started_at: str
    run_finished_at: str
    status: str
    sources_checked: int
    units_seen: int
    new_units: int
    changed_units: int
    alerts_sent: int
    alert_candidates: int
    errors: list[str]
    source_results: list[SourceResult]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_all_sources() -> list[SourceResult]:
    results: list[SourceResult] = []
    for building in BUILDINGS:
        for source in building["sources"]:
            if source["parser"] == "manual_link":
                results.append(
                    SourceResult(
                        building_id=building["id"],
                        building_name=building["name"],
                        source_name=source["name"],
                        source_type=source["type"],
                        url=source["url"],
                        parser=source["parser"],
                        status="manual_check",
                        error="Manual-check link; not fetched automatically.",
                    )
                )
                continue
            response = fetch_url(source["url"])
            reason = blocked_reason(response.text, response.status_code)
            if response.error and not response.text:
                results.append(
                    SourceResult(
                        building_id=building["id"],
                        building_name=building["name"],
                        source_name=source["name"],
                        source_type=source["type"],
                        url=source["url"],
                        parser=source["parser"],
                        status="fetch_error",
                        error=response.error,
                    )
                )
            elif reason:
                results.append(
                    SourceResult(
                        building_id=building["id"],
                        building_name=building["name"],
                        source_name=source["name"],
                        source_type=source["type"],
                        url=source["url"],
                        parser=source["parser"],
                        status=f"blocked:{reason}",
                        error=f"HTTP {response.status_code}; {reason}",
                    )
                )
            else:
                units = parse_units(
                    source["parser"],
                    building_id=building["id"],
                    building_name=building["name"],
                    source_url=response.final_url or source["url"],
                    source_type=source["type"],
                    text=response.text,
                )
                results.append(
                    SourceResult(
                        building_id=building["id"],
                        building_name=building["name"],
                        source_name=source["name"],
                        source_type=source["type"],
                        url=source["url"],
                        parser=source["parser"],
                        status="ok" if units else "ok_no_units",
                        units=units,
                    )
                )
            polite_pause()
    return results


def choose_units(results: list[SourceResult]) -> list[Unit]:
    units_by_key: dict[str, Unit] = {}
    for result in results:
        for unit in result.units:
            units_by_key[unit.unit_key] = unit
    return sorted(
        units_by_key.values(),
        key=lambda u: (BUILDING_BY_ID.get(u.building_id, {}).get("priority", 99), u.rent_for_threshold() or 999999, u.unit_key),
    )


def get_existing_units(sheet: GoogleSheetsClient) -> dict[str, dict[str, str]]:
    rows = rows_to_dicts(sheet.values_get(f"{SHEET_TABS['units']}!A1:X2000"))
    return {row.get("unit_key", ""): row for row in rows if row.get("unit_key")}


def get_existing_alert_keys(sheet: GoogleSheetsClient) -> set[str]:
    rows = rows_to_dicts(sheet.values_get(f"{SHEET_TABS['alerts']}!A1:K5000"))
    return {row.get("dedupe_key", "") for row in rows if row.get("dedupe_key")}


def get_existing_source_status(sheet: GoogleSheetsClient) -> dict[str, dict[str, str]]:
    try:
        rows = rows_to_dicts(sheet.values_get(f"{SHEET_TABS['source_status']}!A1:N1000"))
    except RuntimeError as exc:
        if "Source_Status" in str(exc) or "Unable to parse range" in str(exc):
            return {}
        raise
    return {row.get("source_key", ""): row for row in rows if row.get("source_key")}


def classify_change(unit: Unit, existing: dict[str, str] | None) -> tuple[str, int | None]:
    if existing is None:
        return "new_unit", None
    previous_rent = parse_sheet_int(existing.get("estimated_total_rent") or existing.get("base_rent"))
    current_rent = unit.rent_for_threshold()
    if previous_rent is not None and current_rent is not None and previous_rent != current_rent:
        return "price_drop" if current_rent < previous_rent else "price_increase", previous_rent
    if (existing.get("available_date") or "") != (unit.available_date or ""):
        return "available_date_change", previous_rent
    if existing.get("status") and existing.get("status") != unit.status:
        return "status_change", previous_rent
    return "unchanged", previous_rent


def parse_sheet_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(float(str(value).replace(",", "").replace("$", "")))
    except Exception:
        return None


def score_unit(unit: Unit) -> int:
    score = 0
    building = BUILDING_BY_ID.get(unit.building_id, {})
    priority = int(building.get("priority", 99))
    score += max(0, 25 - priority * 2)
    if unit.is_target_layout():
        score += 25
    rent = unit.rent_for_threshold()
    if rent is not None:
        if rent <= PREFERRED_RENT:
            score += 30
        elif rent <= HARD_RENT_CAP:
            score += 15
        else:
            score -= 15
    else:
        score -= 8
    if unit.source_type == "official":
        score += 5
    if "caution" in str(building.get("status", "")):
        score -= 10
    return score


def alert_level(unit: Unit) -> str:
    rent = unit.rent_for_threshold()
    if not unit.is_target_layout() or rent is None:
        return "none"
    if rent <= PREFERRED_RENT:
        return "urgent"
    if rent <= HARD_RENT_CAP:
        return "good"
    return "none"


def unit_row(unit: Unit, first_seen: str, last_seen: str) -> list[Any]:
    score = score_unit(unit)
    level = alert_level(unit)
    return [
        unit.unit_key,
        unit.building_id,
        unit.building_name,
        unit.unit,
        unit.floorplan,
        number_or_blank(unit.beds),
        number_or_blank(unit.baths),
        unit.sqft or "",
        unit.base_rent or "",
        unit.estimated_total_rent or "",
        unit.available_date,
        unit.lease_term,
        unit.concessions,
        unit.fees_notes,
        unit.parking_available,
        unit.parking_monthly,
        unit.source_url,
        unit.source_type,
        first_seen,
        last_seen,
        unit.status,
        score,
        level,
        unit.notes,
    ]


def number_or_blank(value: float | None) -> Any:
    if value is None:
        return ""
    return int(value) if value == int(value) else value


def history_row(observed_at: str, unit: Unit, change_type: str, previous_rent: int | None) -> list[Any]:
    current_rent = unit.rent_for_threshold()
    price_delta = ""
    if current_rent is not None and previous_rent is not None:
        price_delta = current_rent - previous_rent
    return [
        observed_at,
        unit.unit_key,
        unit.building_id,
        unit.building_name,
        unit.unit,
        unit.floorplan,
        number_or_blank(unit.beds),
        number_or_blank(unit.baths),
        unit.sqft or "",
        unit.base_rent or "",
        unit.estimated_total_rent or "",
        unit.available_date,
        unit.lease_term,
        unit.concessions,
        unit.source_url,
        change_type,
        previous_rent or "",
        price_delta,
        unit.notes,
    ]


def make_dedupe_key(unit: Unit, change_type: str) -> str:
    rent = unit.rent_for_threshold()
    return "|".join(
        [
            unit.unit_key,
            change_type,
            str(rent or ""),
            unit.available_date or "",
            unit.status or "",
        ]
    )


def source_key(result: SourceResult) -> str:
    return f"{result.building_id}:{result.source_name}"


def source_action(status: str) -> str:
    if status == "ok":
        return "working"
    if status == "ok_no_units":
        return "monitor_no_units"
    if status == "manual_check":
        return "manual_check"
    if status.startswith("blocked:"):
        return "manual_check_do_not_bypass"
    return "inspect_source"


def source_notes(result: SourceResult) -> str:
    if result.status == "ok":
        return "Automated source returned parseable availability data."
    if result.status == "ok_no_units":
        return "Page loaded, but no parseable unit rows were exposed to the tracker."
    if result.status == "manual_check":
        return "Manual-check backup link. The tracker does not fetch this source automatically."
    if result.status.startswith("blocked:"):
        return "Blocked by access control or anti-bot response. Logged without bypassing."
    return "Fetch or parser needs review."


def source_status_row(observed_at: str, result: SourceResult) -> list[Any]:
    target_units = sum(1 for unit in result.units if unit.is_target_layout())
    return [
        source_key(result),
        observed_at,
        result.building_id,
        result.building_name,
        result.source_name,
        result.source_type,
        result.parser,
        result.status,
        len(result.units),
        target_units,
        result.error,
        result.url,
        source_action(result.status),
        source_notes(result),
    ]


def source_recovery_alert_rows(
    *,
    observed_at: str,
    source_results: list[SourceResult],
    existing_source_status: dict[str, dict[str, str]],
    existing_alert_keys: set[str],
    env: dict[str, str],
    dry_run: bool,
    send_alerts: bool,
) -> tuple[list[list[Any]], int]:
    rows: list[list[Any]] = []
    sent_count = 0
    for result in source_results:
        previous = existing_source_status.get(source_key(result), {})
        previous_status = previous.get("status", "")
        recovered_to_units = result.status == "ok" and previous_status and previous_status != "ok"
        if not recovered_to_units:
            continue
        target_units = sum(1 for unit in result.units if unit.is_target_layout())
        dedupe = f"source_recovered|{source_key(result)}|{previous_status}|{result.status}|{observed_at[:10]}"
        if dedupe in existing_alert_keys:
            continue
        message = build_source_recovered_message(
            building_name=result.building_name,
            source_name=result.source_name,
            previous_status=previous_status,
            current_status=result.status,
            units_found=len(result.units),
            target_units_found=target_units,
            source_url=result.url,
        )
        delivery = "dry_run" if dry_run else "suppressed:no_alerts"
        if send_alerts and not dry_run:
            delivery = send_wecom_markdown(env["WECOM_WEBHOOK_URL"], message)
            sent_count += 1
        rows.append(
            [
                observed_at,
                "wecom",
                "source",
                result.building_id,
                result.building_name,
                source_key(result),
                "source_recovered",
                message,
                result.url,
                delivery,
                dedupe,
            ]
        )
    return rows, sent_count


def run_once(env: dict[str, str], *, dry_run: bool = False, send_alerts: bool = True) -> TrackerRunResult:
    started = now_iso()
    source_results = fetch_all_sources()
    units = choose_units(source_results)
    errors = [
        f"{r.building_name}/{r.source_name}: {r.status} {r.error}".strip()
        for r in source_results
        if r.status not in {"ok", "ok_no_units", "manual_check"}
    ]

    sheet = GoogleSheetsClient.from_env(env)
    if not dry_run:
        sheet.ensure_sheet(SHEET_TABS["source_status"])
    existing_units = get_existing_units(sheet)
    existing_alert_keys = get_existing_alert_keys(sheet)
    existing_source_status = get_existing_source_status(sheet)

    current_time = now_iso()
    new_count = 0
    changed_count = 0
    alerts_sent_count = 0
    alert_rows: list[list[Any]] = []
    history_rows: list[list[Any]] = []
    current_rows: list[list[Any]] = [UNIT_HEADERS]

    for unit in units:
        existing = existing_units.get(unit.unit_key)
        change_type, previous_rent = classify_change(unit, existing)
        first_seen = existing.get("first_seen") if existing else current_time
        first_seen = first_seen or current_time
        current_rows.append(unit_row(unit, first_seen, current_time))
        if change_type != "unchanged":
            if change_type == "new_unit":
                new_count += 1
            else:
                changed_count += 1
            history_rows.append(history_row(current_time, unit, change_type, previous_rent))

        level = alert_level(unit)
        if level != "none" and change_type in {"new_unit", "price_drop", "available_date_change", "status_change"}:
            dedupe = make_dedupe_key(unit, change_type)
            if dedupe not in existing_alert_keys:
                building = BUILDING_BY_ID.get(unit.building_id, {})
                risk_tags = list(building.get("risk_tags", []))
                message = build_alert_message(unit, change_type, level, risk_tags)
                if env.get("DEEPSEEK_ENABLED", "0") == "1":
                    message = maybe_summarize_alert(env.get("DEEPSEEK_API_KEY"), message)
                delivery = "dry_run" if dry_run else "suppressed:no_alerts"
                if send_alerts and not dry_run:
                    delivery = send_wecom_markdown(env["WECOM_WEBHOOK_URL"], message)
                    alerts_sent_count += 1
                alert_rows.append(
                    [
                        current_time,
                        "wecom",
                        level,
                        unit.building_id,
                        unit.building_name,
                        unit.unit_key,
                        change_type,
                        message,
                        unit.source_url,
                        delivery,
                        dedupe,
                    ]
                )

    unavailable_rows = unavailable_existing_rows(existing_units, {u.unit_key for u in units}, current_time)
    current_rows.extend(unavailable_rows)
    source_status_rows = [SOURCE_STATUS_HEADERS] + [
        source_status_row(current_time, result) for result in source_results
    ]
    source_alert_rows, source_alerts_sent = source_recovery_alert_rows(
        observed_at=current_time,
        source_results=source_results,
        existing_source_status=existing_source_status,
        existing_alert_keys=existing_alert_keys,
        env=env,
        dry_run=dry_run,
        send_alerts=send_alerts,
    )
    if source_alert_rows:
        alert_rows.extend(source_alert_rows)
        alerts_sent_count += source_alerts_sent

    finished = now_iso()
    status = "ok" if not errors else "ok_with_source_warnings"
    run_log_row = [
        started,
        finished,
        status,
        len(source_results),
        len(units),
        new_count,
        changed_count,
        alerts_sent_count,
        "\n".join(errors[:20]),
        json.dumps(source_status_summary(source_results), ensure_ascii=False),
    ]

    if not dry_run:
        sheet.values_clear([f"{SHEET_TABS['units']}!A1:X5000"])
        sheet.values_clear([f"{SHEET_TABS['source_status']}!A1:N1000"])
        sheet.values_update(
            [
                {"range": f"{SHEET_TABS['units']}!A1", "values": current_rows},
                {"range": f"{SHEET_TABS['source_status']}!A1", "values": source_status_rows},
            ]
        )
        sheet.values_append(f"{SHEET_TABS['history']}!A1", history_rows)
        sheet.values_append(f"{SHEET_TABS['alerts']}!A1", alert_rows)
        sheet.values_append(f"{SHEET_TABS['run_log']}!A1", [run_log_row])

    return TrackerRunResult(
        run_started_at=started,
        run_finished_at=finished,
        status=status,
        sources_checked=len(source_results),
        units_seen=len(units),
        new_units=new_count,
        changed_units=changed_count,
        alerts_sent=alerts_sent_count,
        alert_candidates=len(alert_rows),
        errors=errors,
        source_results=source_results,
    )


def unavailable_existing_rows(existing_units: dict[str, dict[str, str]], seen_keys: set[str], current_time: str) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for key, existing in sorted(existing_units.items()):
        if key in seen_keys:
            continue
        if existing.get("status") == "unavailable":
            rows.append([existing.get(header, "") for header in UNIT_HEADERS])
            continue
        row = []
        for header in UNIT_HEADERS:
            if header == "status":
                row.append("unavailable")
            elif header == "last_seen":
                row.append(existing.get("last_seen", ""))
            elif header == "notes":
                note = existing.get("notes", "")
                row.append((note + " | no longer seen in latest run").strip(" |"))
            else:
                row.append(existing.get(header, ""))
        rows.append(row)
    return rows


def source_status_summary(results: list[SourceResult]) -> dict[str, Any]:
    return {
        "ok": sum(1 for r in results if r.status == "ok"),
        "ok_no_units": sum(1 for r in results if r.status == "ok_no_units"),
        "manual_check": sum(1 for r in results if r.status == "manual_check"),
        "blocked_or_error": [
            {"building": r.building_name, "source": r.source_name, "status": r.status}
            for r in results
            if r.status not in {"ok", "ok_no_units", "manual_check"}
        ],
    }
