from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .google_sheets import GoogleSheetsClient
from .query_bot import answer_sheet_question, send_query_answer
from .wecom_callback import WeComCallbackCrypto


DEFAULT_SAMPLE_QUESTION = "Arrive Lex现在有多少available lease"


@dataclass
class GeneratedQuerySecrets:
    query_gateway_token: str
    wecom_callback_token: str
    wecom_callback_encoding_aes_key: str

    def env_lines(self) -> list[str]:
        return [
            f"QUERY_GATEWAY_TOKEN={self.query_gateway_token}",
            f"WECOM_CALLBACK_TOKEN={self.wecom_callback_token}",
            f"WECOM_CALLBACK_ENCODING_AES_KEY={self.wecom_callback_encoding_aes_key}",
        ]


def generate_query_secrets() -> GeneratedQuerySecrets:
    return GeneratedQuerySecrets(
        query_gateway_token=secrets.token_urlsafe(24),
        wecom_callback_token=secrets.token_urlsafe(24),
        wecom_callback_encoding_aes_key=generate_encoding_aes_key(),
    )


def write_generated_secrets_to_env(path: Path, generated: GeneratedQuerySecrets) -> None:
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    updates = {
        "QUERY_GATEWAY_TOKEN": generated.query_gateway_token,
        "WECOM_CALLBACK_TOKEN": generated.wecom_callback_token,
        "WECOM_CALLBACK_ENCODING_AES_KEY": generated.wecom_callback_encoding_aes_key,
    }
    seen: set[str] = set()
    out: list[str] = []
    for line in existing:
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            out.append(line)
            continue
        key, _value = line.split("=", 1)
        key = key.strip()
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def generate_encoding_aes_key() -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(43))


def query_self_check(
    env: dict[str, str],
    *,
    question: str = DEFAULT_SAMPLE_QUESTION,
    send_wecom: bool = False,
) -> dict[str, Any]:
    checks: dict[str, Any] = {
        "env": {
            "google_sheet_id": bool(env.get("GOOGLE_SHEET_ID")),
            "google_application_credentials": bool(env.get("GOOGLE_APPLICATION_CREDENTIALS")),
            "wecom_webhook_url": bool(env.get("WECOM_WEBHOOK_URL")),
            "deepseek_api_key": bool(env.get("DEEPSEEK_API_KEY")),
            "deepseek_enabled": env.get("DEEPSEEK_ENABLED", ""),
            "query_gateway_token": bool(env.get("QUERY_GATEWAY_TOKEN")),
            "wecom_callback_token": bool(env.get("WECOM_CALLBACK_TOKEN")),
            "wecom_callback_encoding_aes_key": valid_encoding_key_shape(
                env.get("WECOM_CALLBACK_ENCODING_AES_KEY", "")
            ),
            "wecom_receive_id": env.get("WECOM_CORP_ID", ""),
        },
        "google_sheet": {"ok": False},
        "query": {"ok": False, "sample_question": question},
        "wecom_outbound": {"tested": send_wecom, "ok": None},
        "wecom_callback_config": {"ok": False},
        "notes": [],
    }
    try:
        sheet = GoogleSheetsClient.from_env(env)
        rows = sheet.values_get("Config!A1:C5")
        checks["google_sheet"] = {"ok": True, "rows_read": len(rows)}
    except Exception as exc:
        checks["google_sheet"] = {"ok": False, "error": str(exc)}
        checks["notes"].append("Google Sheet access failed; query answers cannot work until fixed.")

    try:
        answer = answer_sheet_question(env, question, use_deepseek=bool(env.get("DEEPSEEK_API_KEY")))
        checks["query"] = {
            "ok": True,
            "matched_buildings": answer.matched_buildings,
            "unit_rows_used": answer.unit_rows_used,
            "deepseek_used": answer.deepseek_used,
            "answer_preview": answer.answer[:160],
        }
        if send_wecom:
            delivery = send_query_answer(env, answer)
            checks["wecom_outbound"] = {
                "tested": True,
                "ok": '"errcode":0' in delivery or '"errcode": 0' in delivery,
                "delivery": delivery,
            }
    except Exception as exc:
        checks["query"] = {"ok": False, "sample_question": question, "error": str(exc)}

    token = env.get("WECOM_CALLBACK_TOKEN", "")
    aes_key = env.get("WECOM_CALLBACK_ENCODING_AES_KEY", "")
    receive_id = env.get("WECOM_CORP_ID", "")
    if token and aes_key:
        try:
            WeComCallbackCrypto(token, aes_key, receive_id)
            checks["wecom_callback_config"] = {
                "ok": True,
                "receive_id": "empty_for_internal_intelligent_robot" if not receive_id else "configured",
            }
        except Exception as exc:
            checks["wecom_callback_config"] = {"ok": False, "error": str(exc)}
    else:
        checks["wecom_callback_config"] = {
            "ok": False,
            "missing": [
                key
                for key, value in [
                    ("WECOM_CALLBACK_TOKEN", token),
                    ("WECOM_CALLBACK_ENCODING_AES_KEY", aes_key),
                ]
                if not value
            ],
        }
        checks["notes"].append("Inbound WeCom callback is not configured yet.")

    return checks


def valid_encoding_key_shape(value: str) -> bool:
    return len(value) == 43


def format_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
