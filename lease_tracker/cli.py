from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .env import load_env
from .google_sheets import GoogleSheetsClient
from .notifier import send_wecom_markdown
from .query_bot import answer_sheet_question, send_query_answer
from .query_setup import (
    format_json,
    generate_query_secrets,
    query_self_check,
    write_generated_secrets_to_env,
)
from .runner import run_once
from .settings import DEFAULT_ENV_PATH
from .wecom_doc_sync import sync_google_sheet_to_wecom_doc


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
    ask_parser = sub.add_parser("ask", help="Answer a natural-language question from the Google Sheet.")
    ask_parser.add_argument("question", help="Question to answer from the tracker Sheet.")
    ask_parser.add_argument("--reply-to-wecom", action="store_true", help="Send the answer to WeCom.")
    secrets_parser = sub.add_parser(
        "query-generate-secrets",
        help="Generate query gateway and WeCom callback secret values.",
    )
    secrets_parser.add_argument(
        "--write-env",
        action="store_true",
        help="Write generated values into the selected tracker env file.",
    )
    secrets_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print generated values. Useful with --write-env.",
    )
    check_parser = sub.add_parser("query-self-check", help="Check Sheet, DeepSeek, WeCom, and callback readiness.")
    check_parser.add_argument(
        "--question",
        default="Arrive Lex现在有多少available lease",
        help="Sample question for the live query check.",
    )
    check_parser.add_argument("--send-wecom", action="store_true", help="Send the sample answer to WeCom.")
    sub.add_parser("wecom-doc-sync", help="Sync Google Sheet tabs into the WeCom smart-sheet mirror.")

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

    if args.command == "ask":
        answer = answer_sheet_question(env, args.question)
        if args.reply_to_wecom:
            delivery = send_query_answer(env, answer)
            print(json.dumps({"status": "sent", "delivery": delivery}, ensure_ascii=False))
        else:
            print(answer.answer)
        return 0

    if args.command == "query-generate-secrets":
        generated = generate_query_secrets()
        if args.write_env:
            env_path = DEFAULT_ENV_PATH if args.env == str(DEFAULT_ENV_PATH) else Path(args.env)
            write_generated_secrets_to_env(env_path, generated)
        if not args.quiet:
            print("\n".join(generated.env_lines()))
        elif not args.write_env:
            print("Generated values suppressed; use --write-env to save them.")
        return 0

    if args.command == "query-self-check":
        report = query_self_check(env, question=args.question, send_wecom=args.send_wecom)
        print(format_json(report))
        critical_ok = bool(report["google_sheet"]["ok"]) and bool(report["query"]["ok"])
        return 0 if critical_ok else 2

    if args.command == "wecom-doc-sync":
        results = sync_google_sheet_to_wecom_doc(env)
        print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))
        return 0

    return 1
