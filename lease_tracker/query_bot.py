from __future__ import annotations

import json
import re
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import BUILDINGS
from .google_sheets import GoogleSheetsClient, rows_to_dicts
from .notifier import send_wecom_markdown
from .settings import HARD_RENT_CAP, PREFERRED_RENT, SHEET_TABS


DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MAX_CONTEXT_UNITS = 30
ALIAS_STOPWORDS = {"the", "at", "and", "or", "of", "lofts", "apartments"}


@dataclass
class QueryAnswer:
    question: str
    answer: str
    matched_buildings: list[str]
    unit_rows_used: int
    deepseek_used: bool


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value)


def is_addressed_to_bot(text: str, bot_name: str = "South Loop Tracker") -> bool:
    normalized = normalize_text(text)
    aliases = {
        normalize_text(bot_name),
        "southlooptracker",
        "trackerbot",
        "sltracker",
        "租房tracker",
        "租房助手",
        "南环tracker",
    }
    return any(alias and alias in normalized for alias in aliases)


def strip_bot_address(text: str, bot_name: str = "South Loop Tracker") -> str:
    patterns = [
        bot_name,
        "@South Loop Tracker",
        "South Loop Tracker:",
        "South Loop Tracker：",
        "@Tracker Bot",
        "Tracker Bot:",
        "Tracker Bot：",
    ]
    out = text
    for pattern in patterns:
        out = re.sub(re.escape(pattern), "", out, flags=re.IGNORECASE)
    return out.strip() or text.strip()


def answer_sheet_question(env: dict[str, str], question: str, *, use_deepseek: bool = True) -> QueryAnswer:
    sheet = GoogleSheetsClient.from_env(env)
    units = rows_to_dicts(sheet.values_get(f"{SHEET_TABS['units']}!A1:X5000"))
    sources = rows_to_dicts(sheet.values_get(f"{SHEET_TABS['source_status']}!A1:N1000"))
    runs = rows_to_dicts(sheet.values_get(f"{SHEET_TABS['run_log']}!A1:Z5000"))
    context = build_query_context(question, units, sources, runs)
    fallback = deterministic_answer(context)
    deepseek_answer = ""
    if use_deepseek and env.get("DEEPSEEK_API_KEY"):
        deepseek_answer = ask_deepseek(env["DEEPSEEK_API_KEY"], question, context)
    answer = deepseek_answer or fallback
    return QueryAnswer(
        question=question,
        answer=answer,
        matched_buildings=context["matched_buildings"],
        unit_rows_used=len(context["units"]),
        deepseek_used=bool(deepseek_answer),
    )


def send_query_answer(env: dict[str, str], answer: QueryAnswer) -> str:
    webhook_url = env.get("WECOM_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("WECOM_WEBHOOK_URL is not configured.")
    content = "\n".join(["**South Loop Tracker**", answer.answer])
    return send_wecom_markdown(webhook_url, content)


def build_query_context(
    question: str,
    units: list[dict[str, str]],
    sources: list[dict[str, str]],
    runs: list[dict[str, str]],
) -> dict[str, Any]:
    matched_ids = detect_buildings(question)
    wants_target = wants_target_layout(question)
    rent_cap = detect_rent_cap(question)
    wanted_statuses = detect_statuses(question)
    filtered = [
        row
        for row in units
        if row_matches(row, matched_ids, wants_target, rent_cap, wanted_statuses)
    ]
    filtered.sort(key=unit_sort_key)
    compact_units = [compact_unit(row) for row in filtered[:MAX_CONTEXT_UNITS]]
    counts = summarize_counts(units, matched_ids, wants_target, rent_cap)
    matched_names = [building["name"] for building in BUILDINGS if building["id"] in matched_ids]
    if not matched_names:
        matched_names = ["all tracked buildings"]
    source_rows = [
        compact_source(row)
        for row in sources
        if not matched_ids or row.get("building_id") in matched_ids
    ][:25]
    latest_run = compact_run(runs[-1]) if runs else {}
    return {
        "question": question,
        "matched_building_ids": matched_ids,
        "matched_buildings": matched_names,
        "filters": {
            "statuses": sorted(wanted_statuses),
            "target_2b2b_only": wants_target,
            "rent_cap": rent_cap,
        },
        "counts": counts,
        "units": compact_units,
        "unit_rows_omitted": max(0, len(filtered) - len(compact_units)),
        "source_status": source_rows,
        "latest_run": latest_run,
        "rules": {
            "preferred_rent": PREFERRED_RENT,
            "hard_rent_cap": HARD_RENT_CAP,
            "do_not_call_application_ready": True,
        },
    }


def detect_buildings(question: str) -> list[str]:
    normalized = normalize_text(question)
    matched: list[str] = []
    for building in BUILDINGS:
        aliases = building_aliases(building)
        if any(alias and alias in normalized for alias in aliases):
            matched.append(building["id"])
    return matched


def building_aliases(building: dict[str, Any]) -> set[str]:
    aliases = {normalize_text(building["id"]), normalize_text(building["name"])}
    aliases.update(normalize_text(part) for part in building["name"].replace("/", " ").split())
    special = {
        "arrive_lex": ["arrivelex", "lex"],
        "1401_s_state": ["1401", "southstate", "sstate"],
        "1400_wabash": ["1400", "wabash"],
        "roosevelt_collection": ["roosevelt", "rcl", "collectionlofts"],
        "grand_central": ["grandcentral", "altagrandcentral", "alta"],
        "the_reed": ["reed", "southbank"],
        "amli_900": ["amli900", "amli"],
        "eleven40": ["eleven40", "1140"],
    }
    aliases.update(special.get(building["id"], []))
    return {alias for alias in aliases if len(alias) >= 3 and alias not in ALIAS_STOPWORDS}


def wants_target_layout(question: str) -> bool:
    normalized = normalize_text(question)
    markers = ["2b2b", "2bd2ba", "2bed2bath", "2br2ba", "2室2卫", "两室两卫"]
    return any(marker in normalized for marker in markers)


def detect_rent_cap(question: str) -> int | None:
    normalized = unicodedata.normalize("NFKC", question.lower())
    numbers = [int(num) for num in re.findall(r"(?<!\d)([2-5]\d{3})(?!\d)", normalized)]
    if not numbers:
        return None
    cap_words = ["under", "below", "<", "低于", "小于", "以内", "以下", "不超过", "最多", "cap"]
    return min(numbers) if any(word in normalized for word in cap_words) else None


def detect_statuses(question: str) -> set[str]:
    normalized = normalize_text(question)
    if "unavailable" in normalized or "下架" in normalized:
        return {"unavailable"}
    if "visibilityunconfirmed" in normalized or "unconfirmed" in normalized or "不确定" in normalized:
        return {"visibility_unconfirmed"}
    return {"available"}


def row_matches(
    row: dict[str, str],
    building_ids: list[str],
    wants_target: bool,
    rent_cap: int | None,
    wanted_statuses: set[str],
) -> bool:
    if building_ids and row.get("building_id") not in building_ids:
        return False
    if row.get("status", "").strip() not in wanted_statuses:
        return False
    if wants_target and not is_target_2b2b(row):
        return False
    if rent_cap is not None:
        rent = int_or_none(row.get("estimated_total_rent")) or int_or_none(row.get("base_rent"))
        if rent is None or rent > rent_cap:
            return False
    return True


def summarize_counts(
    units: list[dict[str, str]],
    building_ids: list[str],
    wants_target: bool,
    rent_cap: int | None,
) -> dict[str, Any]:
    scoped = [row for row in units if not building_ids or row.get("building_id") in building_ids]
    if wants_target:
        scoped = [row for row in scoped if is_target_2b2b(row)]
    if rent_cap is not None:
        scoped = [
            row
            for row in scoped
            if (int_or_none(row.get("estimated_total_rent")) or int_or_none(row.get("base_rent")) or 10**9)
            <= rent_cap
        ]
    by_status: dict[str, int] = {}
    by_building: dict[str, dict[str, int]] = {}
    for row in scoped:
        status = row.get("status") or "unknown"
        by_status[status] = by_status.get(status, 0) + 1
        building = row.get("building_name") or row.get("building_id") or "unknown"
        by_building.setdefault(building, {})
        by_building[building][status] = by_building[building].get(status, 0) + 1
    available = [row for row in scoped if row.get("status") == "available"]
    target_under_3500 = [
        row
        for row in available
        if is_target_2b2b(row)
        and ((int_or_none(row.get("estimated_total_rent")) or int_or_none(row.get("base_rent")) or 10**9) <= PREFERRED_RENT)
    ]
    target_under_4000 = [
        row
        for row in available
        if is_target_2b2b(row)
        and ((int_or_none(row.get("estimated_total_rent")) or int_or_none(row.get("base_rent")) or 10**9) <= HARD_RENT_CAP)
    ]
    return {
        "by_status": by_status,
        "by_building": by_building,
        "available_total": len(available),
        "available_2b2b_under_3500": len(target_under_3500),
        "available_2b2b_under_4000": len(target_under_4000),
    }


def compact_unit(row: dict[str, str]) -> dict[str, str]:
    return {
        "building": row.get("building_name", ""),
        "unit": row.get("unit", ""),
        "floorplan": row.get("floorplan", ""),
        "beds": row.get("beds", ""),
        "baths": row.get("baths", ""),
        "sqft": row.get("sqft", ""),
        "rent": row.get("estimated_total_rent") or row.get("base_rent", ""),
        "available_date": row.get("available_date", ""),
        "status": row.get("status", ""),
        "source_type": row.get("source_type", ""),
        "notes": truncate(row.get("notes", ""), 120),
    }


def compact_source(row: dict[str, str]) -> dict[str, str]:
    return {
        "building": row.get("building_name", ""),
        "source": row.get("source_name", ""),
        "status": row.get("status", ""),
        "units_found": row.get("units_found", ""),
        "target_units_found": row.get("target_units_found", ""),
        "action": row.get("action", ""),
    }


def compact_run(row: dict[str, str]) -> dict[str, str]:
    return {
        "started": row.get("run_started_at", ""),
        "finished": row.get("run_finished_at", ""),
        "status": row.get("status", ""),
        "sources_checked": row.get("sources_checked", ""),
        "units_seen": row.get("units_seen", ""),
        "alerts_sent": row.get("alerts_sent", ""),
    }


def deterministic_answer(context: dict[str, Any]) -> str:
    buildings = "、".join(context["matched_buildings"])
    counts = context["counts"]
    available = counts.get("available_total", 0)
    target_3500 = counts.get("available_2b2b_under_3500", 0)
    target_4000 = counts.get("available_2b2b_under_4000", 0)
    units = context["units"][:5]
    parts = [
        f"{buildings}：当前 Sheet 里有 {available} 个 available lease。",
        f"其中 2B2B <=$3,500 有 {target_3500} 个，<=$4,000 有 {target_4000} 个。",
    ]
    if units:
        sample = []
        for unit in units:
            label = unit["unit"] or unit["floorplan"] or "unit"
            rent = f"${unit['rent']}" if unit.get("rent") else "租金未公开"
            date = unit.get("available_date") or "日期未公开"
            sample.append(f"{label} {rent} {date}")
        parts.append("前几项：" + "；".join(sample) + "。")
    if context.get("unit_rows_omitted"):
        parts.append(f"另有 {context['unit_rows_omitted']} 条未展开。")
    return "\n".join(parts)


def ask_deepseek(api_key: str, question: str, context: dict[str, Any]) -> str:
    prompt = {
        "task": "Answer the user's WeCom apartment tracker question using only this Google Sheet context.",
        "style": "Chinese if the user used Chinese; otherwise concise English. Be direct. Do not invent.",
        "hard_rules": [
            "Use only counts and rows in context.",
            "Mention that application readiness still needs leasing confirmation when relevant.",
            "If rows are missing or status is not available, say so.",
            "Keep the answer concise enough for 企业微信.",
        ],
        "question": question,
        "context": context,
    }
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": "You answer as South Loop Tracker using provided sheet facts only."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, separators=(",", ":"))},
        ],
        "stream": False,
        "temperature": 0.2,
        "max_tokens": 900,
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data.get("choices", [{}])[0].get("message", {}).get("content") or ""
        return content.strip()
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, json.JSONDecodeError):
        return ""


def is_target_2b2b(row: dict[str, str]) -> bool:
    beds = float_or_none(row.get("beds"))
    baths = float_or_none(row.get("baths"))
    return beds == 2 and baths is not None and baths >= 2


def unit_sort_key(row: dict[str, str]) -> tuple[str, int, str]:
    rent = int_or_none(row.get("estimated_total_rent")) or int_or_none(row.get("base_rent")) or 10**9
    return (row.get("building_name", ""), rent, row.get("available_date", ""))


def int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"-?\d+", str(value).replace(",", ""))
    return int(match.group(0)) if match else None


def float_or_none(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"
