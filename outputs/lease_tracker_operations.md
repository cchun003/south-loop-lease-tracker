# South Loop / Southbank Lease Tracker Operations

## What It Tracks

- Pinned buildings: Coeval, 1400 Wabash, 1401 S State, AMLI 900, Roosevelt Collection Lofts, Aspire, Arrive LEX, Eleven40, The Reed at Southbank, The Grand Central / Alta Grand Central.
- Target: 2B2B units with estimated monthly rent <= $4,000.
- Urgent: target 2B2B units with estimated monthly rent <= $3,500.
- Alerts: new unit, price drop, availability-date change, status change, or alert-level upgrade/new qualifying unit.
- Backup sources are included, but official sources are preferred when both exist.
- Blocked/challenged pages are retried with Scrapling for better visibility.
- `Source_Status` records each configured source as `ok`, `ok_enhanced`, `ok_no_units`, `ok_no_units_enhanced`, `manual_check`, `blocked:*`, or `blocked_after_enhanced:*`.
- `Units.status = visibility_unconfirmed` means a source family was missed in the latest scan and prior units were retained to avoid false unavailable flips.

## Local Commands

Run from:

```bash
cd /path/to/south-loop-lease-tracker
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
scrapling install
```

Verify Google Sheets access:

```bash
python3 tracker.py test-sheet
```

Verify 企业微信 delivery:

```bash
python3 tracker.py test-alert
```

Fetch and compare without writing or alerting:

```bash
python3 tracker.py dry-run
```

Create the first baseline without alert spam:

```bash
python3 tracker.py run-once --no-alerts
```

Normal production run:

```bash
python3 tracker.py run-once
```

Source health is visible in the `Source_Status` tab. Manual-check links are intentionally not fetched by the tracker.

## Environment

Local secrets live in `.secrets/tracker.env` and should not be committed.

Required values:

```bash
GOOGLE_SHEET_ID=18ajK9gur0PSGtkoturUEwgqoaXa9M_MFVC9CYV-x0og
GOOGLE_APPLICATION_CREDENTIALS=.secrets/google_service_account.json
WECOM_WEBHOOK_URL=...
```

Optional:

```bash
DEEPSEEK_API_KEY=...
DEEPSEEK_ENABLED=0
SCRAPLING_ENABLED=1
SCRAPLING_FETCHER=stealthy
SCRAPLING_SOLVE_CLOUDFLARE=1
SCRAPLING_TIMEOUT_MS=60000
SCRAPLING_WAIT_MS=2500
SCRAPLING_NETWORK_IDLE=0
```

Keep `DEEPSEEK_ENABLED=0` unless you want the alert text rewritten by DeepSeek. The default alert text already includes the Chinese decision fields and English building/unit names.

## GitHub Actions Setup

Use this if you want the tracker to run without keeping Codex or your laptop open.

1. Push this folder to a private GitHub repository.
2. In GitHub, go to `Settings > Secrets and variables > Actions > Repository secrets`.
3. Add:
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_SERVICE_ACCOUNT_JSON_B64`
   - `WECOM_WEBHOOK_URL`
   - `DEEPSEEK_API_KEY` if you enable DeepSeek
4. Create the base64 service-account secret locally:

```bash
base64 -i .secrets/google_service_account.json | pbcopy
```

Paste the clipboard value into `GOOGLE_SERVICE_ACCOUNT_JSON_B64`.

5. Optional: in `Settings > Secrets and variables > Actions > Variables`, add:

```text
DEEPSEEK_ENABLED=0
SCRAPLING_ENABLED=1
SCRAPLING_FETCHER=stealthy
SCRAPLING_SOLVE_CLOUDFLARE=1
SCRAPLING_WAIT_MS=2500
SCRAPLING_NETWORK_IDLE=0
```

6. The workflow file is `.github/workflows/lease-tracker.yml`.
7. Run it manually once from the GitHub Actions tab with `workflow_dispatch`.

Notes:

- GitHub Actions cron is UTC. The included schedule approximates frequent Chicago daytime checks in CDT and less frequent overnight checks.
- For exact America/Chicago timezone behavior year-round, run from a small server or macOS launchd instead.

## macOS launchd Setup

Use this if you prefer your Mac to run it every 30 minutes.

```bash
mkdir -p ~/Library/LaunchAgents
cp deploy/launchd/com.chenchun.lease-tracker.plist.template ~/Library/LaunchAgents/com.chenchun.lease-tracker.plist
launchctl load ~/Library/LaunchAgents/com.chenchun.lease-tracker.plist
launchctl start com.chenchun.lease-tracker
```

Logs:

```bash
tail -f logs/lease-tracker.out.log
tail -f logs/lease-tracker.err.log
```

Stop it:

```bash
launchctl unload ~/Library/LaunchAgents/com.chenchun.lease-tracker.plist
```

## Enhanced Fetch Policy

- The tracker first uses low-volume ordinary HTTP requests with a fixed delay between source requests.
- When a public availability source returns Cloudflare/403/429/challenge content, it retries that source with Scrapling.
- Scrapling defaults to `StealthyFetcher` with Cloudflare solving enabled, captured XHR appended for parser visibility, and no credentials.
- Enhanced parsers consume captured SightMap, RentCafe/Yardi, and Knock Doorway availability APIs when those interfaces are exposed by official building pages.
- It does not automate 小红书, Facebook, Reddit login sessions in the production loop.
- Social-media findings are folded into building risk tags and notes; lease availability comes from official/backup apartment listing sources.
- Manual-check backup links remain stored for sources that need human inspection after enhanced fetching.
