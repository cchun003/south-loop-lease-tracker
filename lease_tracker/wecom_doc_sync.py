from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from .google_sheets import GoogleSheetsClient, rows_to_dicts
from .settings import SHEET_TABS


CHUNK_SIZE = 200
MAP_TAB = "WeCom_Record_Map"
MAP_HEADERS = ["tab", "row_key", "record_id", "source_hash", "last_synced_at"]
T = TypeVar("T")


@dataclass(frozen=True)
class FieldSpec:
    field_id: str
    title: str
    field_type: str


@dataclass(frozen=True)
class WebhookTabConfig:
    tab: str
    google_tab_key: str
    range_suffix: str
    webhook_env: str
    key_column: str
    schema: tuple[FieldSpec, ...]


@dataclass
class WeComDocSyncResult:
    tab: str
    source_rows: int
    added_records: int
    updated_records: int
    unchanged_records: int
    skipped_records: int


class BootstrapRequiredError(RuntimeError):
    pass


TAB_CONFIGS = [
    WebhookTabConfig(
        tab="Units",
        google_tab_key="units",
        range_suffix="A1:X5000",
        webhook_env="WECOM_UNITS_WEBHOOK_URL",
        key_column="unit_key",
        schema=(
            FieldSpec("f04Gwj", "unit_key", "text"),
            FieldSpec("fwyTOh", "building_id", "text"),
            FieldSpec("fzoIdU", "building_name", "text"),
            FieldSpec("fgQ6rp", "unit", "text"),
            FieldSpec("fhfiEI", "floorplan", "text"),
            FieldSpec("fdTzBj", "beds", "number"),
            FieldSpec("fUbVMu", "baths", "number"),
            FieldSpec("fbAkXe", "sqft", "number"),
            FieldSpec("f16xhO", "base_rent", "number"),
            FieldSpec("fhoajp", "estimated_total_rent", "number"),
            FieldSpec("fx40pK", "available_date", "text"),
            FieldSpec("fML1Jq", "lease_term", "text"),
            FieldSpec("fXpM76", "concessions", "text"),
            FieldSpec("fiub8F", "fees_notes", "text"),
            FieldSpec("fdF1sF", "parking_available", "text"),
            FieldSpec("f95vU1", "parking_monthly", "number"),
            FieldSpec("fghrcl", "source_url", "text"),
            FieldSpec("feihUc", "source_type", "text"),
            FieldSpec("fEuAyP", "first_seen", "text"),
            FieldSpec("f3Rfe7", "last_seen", "text"),
            FieldSpec("fOm7BL", "status", "text"),
            FieldSpec("fVsb8L", "score", "number"),
            FieldSpec("fTICE6", "alert_level", "text"),
            FieldSpec("fINiAl", "notes", "text"),
        ),
    ),
    WebhookTabConfig(
        tab="Source_Status",
        google_tab_key="source_status",
        range_suffix="A1:N1000",
        webhook_env="WECOM_SOURCE_STATUS_WEBHOOK_URL",
        key_column="source_key",
        schema=(
            FieldSpec("fabcde", "source_key", "text"),
            FieldSpec("fTNudO", "observed_at", "text"),
            FieldSpec("fCgoM1", "building_id", "text"),
            FieldSpec("fKR5Re", "building_name", "text"),
            FieldSpec("fBHAi1", "source_name", "text"),
            FieldSpec("fx3wpe", "source_type", "text"),
            FieldSpec("fUzan2", "parser", "text"),
            FieldSpec("fdQf2A", "status", "text"),
            FieldSpec("fzpjwb", "units_found", "number"),
            FieldSpec("fgeaig", "target_units_found", "number"),
            FieldSpec("fAXlAv", "error", "text"),
            FieldSpec("fncto0", "url", "text"),
            FieldSpec("fTcale", "action", "text"),
            FieldSpec("fmVSCf", "notes", "text"),
        ),
    ),
    WebhookTabConfig(
        tab="Run_Log",
        google_tab_key="run_log",
        range_suffix="A1:Z5000",
        webhook_env="WECOM_RUN_LOG_WEBHOOK_URL",
        key_column="run_started_at",
        schema=(
            FieldSpec("fabcde", "run_started_at", "text"),
            FieldSpec("f58l0t", "run_finished_at", "text"),
            FieldSpec("fxrilw", "status", "text"),
            FieldSpec("flDCYE", "sources_checked", "number"),
            FieldSpec("fJVi2s", "units_seen", "number"),
            FieldSpec("fN3Jmm", "new_units", "number"),
            FieldSpec("fofhJW", "changed_units", "number"),
            FieldSpec("fuiBzh", "alerts_sent", "number"),
            FieldSpec("flk9WL", "errors", "text"),
            FieldSpec("fOGTsG", "notes", "text"),
        ),
    ),
]


def sync_google_sheet_to_wecom_doc(env: dict[str, str]) -> list[WeComDocSyncResult]:
    allow_bootstrap = env.get("WECOM_WEBHOOK_SYNC_ALLOW_BOOTSTRAP", "0") == "1"
    google = GoogleSheetsClient.from_env(env)
    google.ensure_sheet(MAP_TAB)
    record_map = load_record_map(google)
    if not record_map and not allow_bootstrap:
        raise BootstrapRequiredError(
            f"{MAP_TAB} is empty. To avoid duplicating the existing WeCom mirror, "
            "clear the WeCom mirror rows or create a fresh empty mirror, then run once "
            "with WECOM_WEBHOOK_SYNC_ALLOW_BOOTSTRAP=1."
        )

    now_marker = latest_run_finished_at(google)
    results: list[WeComDocSyncResult] = []
    updated_map = dict(record_map)

    for config in TAB_CONFIGS:
        webhook_url = require_env(env, config.webhook_env)
        rows = google.values_get(f"{SHEET_TABS[config.google_tab_key]}!{config.range_suffix}")
        headers = [str(cell) for cell in rows[0]] if rows else []
        validate_schema(config, headers)
        data_rows = rows_to_dicts(rows)
        result = sync_tab(
            config,
            webhook_url,
            data_rows,
            record_map,
            updated_map,
            now_marker,
            persist_map=lambda: save_record_map(google, updated_map),
        )
        results.append(result)

    save_record_map(google, updated_map)
    return results


def sync_tab(
    config: WebhookTabConfig,
    webhook_url: str,
    rows: list[dict[str, str]],
    record_map: dict[tuple[str, str], dict[str, str]],
    updated_map: dict[tuple[str, str], dict[str, str]],
    now_marker: str,
    persist_map: Callable[[], None] | None = None,
) -> WeComDocSyncResult:
    to_add: list[tuple[str, str, dict[str, Any]]] = []
    to_update: list[tuple[str, str, str, dict[str, Any]]] = []
    unchanged = 0
    skipped = 0

    for row in rows:
        row_key = row.get(config.key_column, "").strip()
        if not row_key:
            skipped += 1
            continue
        source_hash = hash_row(row, config)
        values = row_to_webhook_values(row, config.schema)
        if not values:
            skipped += 1
            continue
        map_entry = record_map.get((config.tab, row_key))
        record_id = map_entry.get("record_id", "") if map_entry else ""
        if record_id:
            if map_entry and map_entry.get("source_hash") == source_hash:
                unchanged += 1
                continue
            to_update.append((row_key, record_id, source_hash, values))
        else:
            to_add.append((row_key, source_hash, values))

    added = add_records(config, webhook_url, to_add, updated_map, now_marker, persist_map)
    updated = update_records(config, webhook_url, to_update, updated_map, now_marker, persist_map)

    return WeComDocSyncResult(
        tab=config.tab,
        source_rows=len(rows),
        added_records=added,
        updated_records=updated,
        unchanged_records=unchanged,
        skipped_records=skipped,
    )


def add_records(
    config: WebhookTabConfig,
    webhook_url: str,
    records: list[tuple[str, str, dict[str, Any]]],
    updated_map: dict[tuple[str, str], dict[str, str]],
    now_marker: str,
    persist_map: Callable[[], None] | None = None,
) -> int:
    added = 0
    for chunk in chunked(records, CHUNK_SIZE):
        payload = {"add_records": [{"values": values} for _row_key, _source_hash, values in chunk]}
        response = post_webhook(webhook_url, payload)
        response_records = response.get("add_records", [])
        if len(response_records) != len(chunk):
            raise RuntimeError(
                f"WeCom add_records for {config.tab} returned {len(response_records)} records "
                f"for {len(chunk)} requested records."
            )
        for (row_key, source_hash, _values), response_record in zip(chunk, response_records):
            record_id = str(response_record.get("record_id", ""))
            if not record_id:
                raise RuntimeError(f"WeCom add_records for {config.tab} did not return record_id.")
            updated_map[(config.tab, row_key)] = {
                "tab": config.tab,
                "row_key": row_key,
                "record_id": record_id,
                "source_hash": source_hash,
                "last_synced_at": now_marker,
            }
            added += 1
        if persist_map:
            persist_map()
    return added


def update_records(
    config: WebhookTabConfig,
    webhook_url: str,
    records: list[tuple[str, str, str, dict[str, Any]]],
    updated_map: dict[tuple[str, str], dict[str, str]],
    now_marker: str,
    persist_map: Callable[[], None] | None = None,
) -> int:
    updated = 0
    for chunk in chunked(records, CHUNK_SIZE):
        payload = {
            "update_records": [
                {"record_id": record_id, "values": values}
                for _row_key, record_id, _source_hash, values in chunk
            ]
        }
        post_webhook(webhook_url, payload)
        for row_key, record_id, source_hash, _values in chunk:
            updated_map[(config.tab, row_key)] = {
                "tab": config.tab,
                "row_key": row_key,
                "record_id": record_id,
                "source_hash": source_hash,
                "last_synced_at": now_marker,
            }
            updated += 1
        if persist_map:
            persist_map()
    return updated


def post_webhook(webhook_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"WeCom webhook HTTP {exc.code}: {body}") from exc
    if data.get("errcode") != 0:
        raise RuntimeError(f"WeCom webhook returned error: {data}")
    return data


def row_to_webhook_values(row: dict[str, str], schema: tuple[FieldSpec, ...]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field in schema:
        raw = row.get(field.title, "")
        if raw is None or str(raw).strip() == "":
            continue
        converted = convert_cell_value(str(raw), field.field_type)
        if converted is not None:
            values[field.field_id] = converted
    return values


def convert_cell_value(raw: str, field_type: str) -> Any:
    if field_type == "number":
        return parse_number(raw)
    return truncate_cell(raw)


def parse_number(raw: str) -> int | float | None:
    cleaned = raw.replace("$", "").replace(",", "").strip()
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
        return None
    return float(cleaned) if "." in cleaned else int(cleaned)


def validate_schema(config: WebhookTabConfig, headers: list[str]) -> None:
    expected = [field.title for field in config.schema]
    if headers != expected:
        raise RuntimeError(
            f"WeCom webhook schema mismatch for {config.tab}. Expected {expected}, got {headers}."
        )


def load_record_map(google: GoogleSheetsClient) -> dict[tuple[str, str], dict[str, str]]:
    rows = rows_to_dicts(google.values_get(f"{MAP_TAB}!A1:E50000"))
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        tab = row.get("tab", "").strip()
        row_key = row.get("row_key", "").strip()
        record_id = row.get("record_id", "").strip()
        if tab and row_key and record_id:
            out[(tab, row_key)] = row
    return out


def save_record_map(
    google: GoogleSheetsClient,
    record_map: dict[tuple[str, str], dict[str, str]],
) -> None:
    rows = [MAP_HEADERS]
    for _key, entry in sorted(record_map.items()):
        rows.append([entry.get(header, "") for header in MAP_HEADERS])
    google.values_clear([f"{MAP_TAB}!A1:E50000"])
    google.values_update([{"range": f"{MAP_TAB}!A1", "values": rows}])


def latest_run_finished_at(google: GoogleSheetsClient) -> str:
    rows = rows_to_dicts(google.values_get(f"{SHEET_TABS['run_log']}!A1:Z5000"))
    if rows:
        return rows[-1].get("run_finished_at") or rows[-1].get("run_started_at") or ""
    return ""


def hash_row(row: dict[str, str], config: WebhookTabConfig) -> str:
    stable = {field.title: row.get(field.title, "") for field in config.schema}
    raw = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def truncate_cell(value: str, limit: int = 2000) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


def chunked(items: list[T], size: int) -> list[list[T]]:
    return [items[idx : idx + size] for idx in range(0, len(items), size)]


def require_env(env: dict[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise RuntimeError(f"{key} is not configured.")
    return value
