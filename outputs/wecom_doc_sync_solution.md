# WeCom Smart-Sheet Webhook Sync

## Finding

The WeCom smart-sheet webhook route is a better fit than `WecomTeam/wecom-cli` for this project.

Official docs:

- https://developer.work.weixin.qq.com/document/path/101239
- https://developer.work.weixin.qq.com/document/path/101240
- https://developer.work.weixin.qq.com/document/path/101241

Each smart-sheet worksheet can expose a webhook URL. A normal HTTP POST can add records, and update records when the caller already knows each row's `record_id`. This removes the need for:

- a persistent server
- a long-connection robot worker
- an API-mode bot just for document writes
- `wecom-cli`

## Implemented

The repo now has:

```bash
python tracker.py wecom-doc-sync
```

It reads the Google Sheet tabs and pushes them into the WeCom smart-sheet mirror through the three worksheet webhooks:

- `Units`
- `Source_Status`
- `Run_Log`

The sync stores WeCom `record_id` values in a Google Sheet tab named `WeCom_Record_Map`. After the first successful bootstrap, later runs compare row hashes and send webhook updates only for changed records.

The GitHub Actions workflow runs this after `python tracker.py run-once` when all three webhook secrets are configured.

## Required GitHub Secrets

Add these repository secrets:

```text
WECOM_UNITS_WEBHOOK_URL
WECOM_SOURCE_STATUS_WEBHOOK_URL
WECOM_RUN_LOG_WEBHOOK_URL
```

Existing Google secrets are also required:

```text
GOOGLE_SHEET_ID
GOOGLE_SERVICE_ACCOUNT_JSON_B64
```

## First Run

Webhook update calls require WeCom `record_id`, and an existing mirror created by another tool does not give this project those IDs automatically.

For the first run, use one of these clean bootstrap paths:

1. Clear the existing rows in the three WeCom mirror worksheets, then run once with `WECOM_WEBHOOK_SYNC_ALLOW_BOOTSTRAP=1`.
2. Create a fresh empty WeCom smart-sheet mirror with the same three worksheets and field schemas, generate new webhook URLs, then run once with `WECOM_WEBHOOK_SYNC_ALLOW_BOOTSTRAP=1`.

After the first successful run, set `WECOM_WEBHOOK_SYNC_ALLOW_BOOTSTRAP` back to `0` or remove it. The `WeCom_Record_Map` tab will then let every scheduled GitHub Actions run update existing WeCom records instead of duplicating them.
