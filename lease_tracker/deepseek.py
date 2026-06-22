from __future__ import annotations

import json
import urllib.request


DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def maybe_summarize_alert(api_key: str | None, template_message: str) -> str:
    if not api_key:
        return template_message
    prompt = (
        "请把下面的租房提醒压缩成适合企业微信群机器人推送的中文消息。"
        "保留楼名、户型、价格、可入住日期、风险标签和链接，不要夸大，不要新增事实。\n\n"
        + template_message
    )
    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": "You write concise Chinese apartment tracker alerts."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip() or template_message
    except Exception:
        return template_message

