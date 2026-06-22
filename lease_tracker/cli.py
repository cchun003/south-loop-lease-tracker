from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .env import load_env
from .google_sheets import GoogleSheetsClient
from .notifier import send_wecom_markdown
from .runner import run_once
from .settings import DEFAULT_ENV_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tracker.py")
    parser.add_argument("--env", default=str(DEFAULT_ENV_PATH), help="Path to tracker env file.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run-once", help="Fetch sources, update Google Sheet, send deduped alerts.")
    run_parser.add_argument("--dry-run", action="store_true", help="Fetch and compare but do not write or alert.")
    run_parser.add_argument("--no-alerts", action="store_true", help="Write Sheet but do not send WeCom alerts.")

    sub.add_parser("test-sheet", help="Verify Google Sheet API access.")
    sub.add_parser("test-alert", help="Send a small WeCom test message.")
    sub.add_parser("dry-run", help="Alias for run-once --dry-run.")

    args = parser.parse_args(argv)
    env = load_env(DEFAULT_ENV_PATH if args.env == str(DEFAULT_ENV_PATH) else Path(args.env))

    if args.command == "test-sheet":
        sheet = GoogleSheetsClient.from_env(env)
        rows = sheet.values_get("Config!A1:C5")
        print(json.dumps({"status": "ok", "rows_read": len(rows)}, ensure_ascii=False))
        return 0

    if args.command == "test-alert":
        if not env.get("WECOM_WEBHOOK_URL"):
            print("WECOM_WEBHOOK_URL is not configured.", file=sys.stderr)
            return 1
        result = send_wecom_markdown(
            env["WECOM_WEBHOOK_URL"],
            "**Lease Tracker 测试**\n本机 tracker CLI 可以发送企业微信消息。",
        )
        print(result)
        return 0

    if args.command in {"run-once", "dry-run"}:
        dry_run = args.command == "dry-run" or getattr(args, "dry_run", False)
        no_alerts = getattr(args, "no_alerts", False)
        result = run_once(env, dry_run=dry_run, send_alerts=not no_alerts)
        print(
            json.dumps(
                {
                    "status": result.status,
                    "sources_checked": result.sources_checked,
                    "units_seen": result.units_seen,
                    "new_units": result.new_units,
                    "changed_units": result.changed_units,
                    "alert_candidates": result.alert_candidates,
                    "alerts_sent": result.alerts_sent,
                    "warnings": result.errors[:10],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if result.status.startswith("ok") else 2

    return 1
