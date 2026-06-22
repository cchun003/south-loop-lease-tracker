# South Loop Lease Tracker

Automated lease-availability tracker for a pinned South Loop / Southbank Chicago apartment shortlist.

The tracker checks official apartment availability pages plus selected backup listing sources, writes current inventory and change history to Google Sheets, and sends WeCom webhook alerts only when a matching unit is new or meaningfully changed.

## Current Target

- Buildings: Coeval, 1400 Wabash, 1401 S State, AMLI 900, Roosevelt Collection Lofts, Aspire, Arrive LEX, Eleven40, The Reed at Southbank, The Grand Central / Alta Grand Central.
- Layout: 2B2B.
- Good alert: estimated monthly rent at or below `$4,000`.
- Urgent alert: estimated monthly rent at or below `$3,500`.
- Change alerts: new unit, price drop, availability-date change, status change, or alert-level upgrade.

## Safety Policy

This project intentionally avoids high-risk scraping behavior.

- It uses low-volume ordinary HTTP requests with a fixed delay between sources.
- It logs Cloudflare, 403, 429, and similar challenge pages as blocked.
- It does not bypass anti-bot systems.
- It does not automate logged-in social-media sessions.
- Social-media research is represented as building risk tags and notes; production lease availability comes from official and backup listing sources.

## Repository Layout

```text
tracker.py                         CLI entrypoint
lease_tracker/                     tracker package
lease_tracker/config.py            pinned buildings and source map
lease_tracker/parsers.py           source parsers
lease_tracker/runner.py            fetch, compare, write, and alert loop
.github/workflows/lease-tracker.yml GitHub Actions schedule
outputs/lease_tracker_operations.md detailed operations guide
deploy/launchd/                    local macOS scheduler template
```

## Local Setup

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create local secrets from the example:

```bash
cp .env.example .secrets/tracker.env
```

Required local environment values:

```bash
GOOGLE_SHEET_ID=...
GOOGLE_APPLICATION_CREDENTIALS=.secrets/google_service_account.json
WECOM_WEBHOOK_URL=...
```

Optional:

```bash
DEEPSEEK_API_KEY=...
DEEPSEEK_ENABLED=0
```

Keep `.secrets/` out of git.

## Local Commands

Verify Google Sheets access:

```bash
python3 tracker.py test-sheet
```

Verify WeCom delivery:

```bash
python3 tracker.py test-alert
```

Fetch and compare without writing or alerting:

```bash
python3 tracker.py dry-run
```

Write the first baseline without sending alerts:

```bash
python3 tracker.py run-once --no-alerts
```

Production run:

```bash
python3 tracker.py run-once
```

## GitHub Actions

The workflow in `.github/workflows/lease-tracker.yml` runs on a schedule and can also be triggered manually from the Actions tab.

Required repository secrets:

- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON_B64`
- `WECOM_WEBHOOK_URL`
- `DEEPSEEK_API_KEY` if DeepSeek summaries are enabled

Optional repository variable:

- `DEEPSEEK_ENABLED`, default `0`

To create the service-account secret:

```bash
base64 -i .secrets/google_service_account.json | pbcopy
```

Paste the copied value into `GOOGLE_SERVICE_ACCOUNT_JSON_B64`.

## Output Tables

The tracker writes these Google Sheet tabs:

- `Buildings`: pinned building metadata and notes.
- `Units`: latest visible inventory.
- `Unit_History`: observed unit changes.
- `Alerts`: sent or suppressed alert records with dedupe keys.
- `Run_Log`: source status and run summary.
- `Source_Status`: per-source latest status, units found, error reason, and action.
- `Config`: runtime assumptions and thresholds.

## More Detail

See `outputs/lease_tracker_operations.md` for the full operations guide, including GitHub and macOS launchd setup.
