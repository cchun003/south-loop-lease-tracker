from __future__ import annotations

import json
import urllib.error
import urllib.request

from .models import Unit


def send_wecom_markdown(webhook_url: str, content: str) -> str:
    payload = json.dumps({"msgtype": "markdown", "markdown": {"content": content}}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return f"ERROR: {exc}"


def build_alert_message(unit: Unit, reason: str, alert_level: str, risk_tags: list[str]) -> str:
    rent = unit.rent_for_threshold()
    rent_text = f"${rent:,}" if rent is not None else "价格未公开"
    sqft = f"{unit.sqft:,} sqft" if unit.sqft else "面积未公开"
    date = unit.available_date or "日期未公开"
    tags = " / ".join(risk_tags + ["parking unconfirmed"])
    prefix = "🔥" if alert_level == "urgent" else "✅"
    return "\n".join(
        [
            f"{prefix} **South Loop 2B2B Lease Alert**",
            f"> {unit.building_name} | {unit.floorplan or unit.unit or 'unit'}",
            f"> Rent: **{rent_text}** | Layout: {fmt_layout(unit)} | {sqft}",
            f"> Available: {date} | Reason: {reason}",
            f"> Risk: {tags}",
            f"[Open source]({unit.source_url})",
        ]
    )


def fmt_layout(unit: Unit) -> str:
    beds = int(unit.beds) if unit.beds is not None and unit.beds == int(unit.beds) else unit.beds
    baths = int(unit.baths) if unit.baths is not None and unit.baths == int(unit.baths) else unit.baths
    return f"{beds}B{baths}B"

