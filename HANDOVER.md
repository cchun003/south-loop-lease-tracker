# South Loop Lease Tracker Handover

Last updated: 2026-06-22

## Project Purpose

This repository runs an automated lease tracker for a pinned South Loop / Southbank Chicago apartment shortlist. It checks public apartment availability pages, writes current inventory and change history to Google Sheets, and sends WeCom alerts only when matching units are new or meaningfully changed.

Primary target:

- Layout: 2B2B
- Good alert: estimated monthly rent <= $4,000
- Urgent alert: estimated monthly rent <= $3,500
- Alert-worthy changes: new unit, price drop, availability-date change, status change, or source recovery

Pinned buildings:

- Coeval
- 1400 Wabash
- 1401 S State
- AMLI 900
- Roosevelt Collection Lofts
- Aspire
- Arrive LEX
- Eleven40
- The Reed at Southbank
- The Grand Central / Alta Grand Central

## Current Operating State

The tracker is live through GitHub Actions and can also be run locally.

Current Sheet state at the last verified handoff run:

- `Units`: 59 current parseable unit rows
- `Unit_History`: 59 historical rows
- `Alerts`: 10 baseline alert/dedupe rows
- `Run_Log`: 4 run rows
- `Source_Status`: 24 configured source rows

Current `Source_Status` breakdown:

- `ok`: 5 automated sources return parseable availability
- `ok_no_units`: 6 sources load but do not expose parseable unit rows
- `blocked:http_403`: 8 sources return HTTP 403 / anti-bot or access-control responses
- `manual_check`: 5 manual backup links are recorded but not fetched automatically

The five buildings currently producing parseable unit rows are:

- Coeval
- 1400 Wabash
- AMLI 900
- Eleven40
- The Reed at Southbank

## Repository Layout

```text
tracker.py
  CLI entrypoint.

lease_tracker/
  Core package.

lease_tracker/config.py
  Building list, source URLs, source parser mapping, risk tags, and manual-check links.

lease_tracker/http_client.py
  Low-volume urllib fetcher and block/challenge detector.

lease_tracker/parsers.py
  Parsers for Spaces/RealPage-style embedded JSON, AMLI Next.js data, JSON-LD floorplans, and The Reed HTML tables.

lease_tracker/runner.py
  Main orchestration: fetch sources, parse units, compare against prior Sheet state, write tabs, create alerts, and record source status.

lease_tracker/google_sheets.py
  Minimal Google Sheets REST client using service-account JWT auth.

lease_tracker/notifier.py
  WeCom markdown webhook sender and alert message builders.

.github/workflows/lease-tracker.yml
  Scheduled and manual GitHub Actions runner.

work/setup_google_sheet.py
  One-time / reset script for creating and formatting Google Sheet tabs.

outputs/lease_tracker_operations.md
  Operator guide with commands and scheduler setup.

deploy/launchd/
  Optional macOS local scheduler template.
```

## Google Sheet Tabs

The tracker writes these tabs:

- `Buildings`: seeded building metadata and risk notes
- `Units`: latest visible inventory
- `Unit_History`: observed changes over time
- `Alerts`: sent or suppressed alert records with dedupe keys
- `Run_Log`: one row per run with aggregate status and errors
- `Source_Status`: one row per configured source with latest `ok`, `ok_no_units`, `manual_check`, or `blocked:*` status
- `Config`: tracker assumptions and thresholds

The Google Sheet ID is configured through `GOOGLE_SHEET_ID`.

## Secrets And Credentials

Do not commit any real secrets.

Local secrets live under `.secrets/`, which is gitignored:

```text
.secrets/tracker.env
.secrets/google_service_account.json
```

GitHub Actions uses repository secrets:

- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON_B64`
- `WECOM_WEBHOOK_URL`
- `DEEPSEEK_API_KEY` if DeepSeek summarization is enabled

GitHub Actions uses this optional repository variable:

- `DEEPSEEK_ENABLED`, default `0`

Important: the DeepSeek key was once pasted in chat during setup. Rotate it if this tracker continues to be used.

## Local Commands

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Verify Google Sheet access:

```bash
python3 tracker.py test-sheet
```

Verify WeCom delivery:

```bash
python3 tracker.py test-alert
```

Run without writing or alerting:

```bash
python3 tracker.py dry-run
```

Run and write, but suppress alerts:

```bash
python3 tracker.py run-once --no-alerts
```

Production run:

```bash
python3 tracker.py run-once
```

## GitHub Actions Schedule

The workflow is `.github/workflows/lease-tracker.yml`.

It supports manual dispatch and scheduled runs.

Cron entries are UTC:

```yaml
- cron: "13,43 12-23 * * *"
- cron: "13,43 0-4 * * *"
- cron: "17 5-11/2 * * *"
```

This approximates frequent daytime Chicago checks and less frequent overnight checks. GitHub scheduled jobs can start a few minutes late.

## Alert Semantics

The tracker does not alert on every successful scan.

It sends WeCom only when there is a meaningful event:

- new matching target unit
- price drop
- availability-date change
- status change
- source recovers from non-working to `ok`

Rows with `delivery_result = suppressed:no_alerts` are usually from intentional baseline or rollout runs using `--no-alerts`. They record dedupe keys without sending WeCom messages.

## Source Health Semantics

`Source_Status.status` values:

- `ok`: fetched and parsed usable units
- `ok_no_units`: fetched successfully but no parseable units exposed
- `manual_check`: recorded link; not fetched automatically
- `blocked:http_403`: blocked by HTTP 403 or challenge response
- `fetch_error`: network or non-HTTP failure

`Source_Status.action` values:

- `working`: automated source is healthy
- `monitor_no_units`: source works but currently exposes no units
- `manual_check`: user should open the link manually
- `manual_check_do_not_bypass`: blocked source; do not attempt challenge bypass
- `inspect_source`: parser/fetch behavior needs review

## Known Limitations

Blocked / weak-coverage buildings:

- 1401 S State: official and Apartments.com backup blocked; manual link recorded.
- Arrive LEX: official and Apartments.com backup blocked or no-unit; manual link recorded.
- Aspire: mixed blocked/no-unit; manual link recorded.
- Roosevelt Collection Lofts: some sources load but only expose limited/no unit-level data; manual link recorded.
- Grand Central / Alta Grand Central: official blocked; manual link recorded.

Other limitations:

- Parking availability is marked `unconfirmed` unless a source exposes it clearly.
- Rent threshold uses exposed base/estimated total rent and does not fully model parking, concessions, or all mandatory fees unless a source exposes them.
- Some backup sources expose only floorplan-level availability, not unit-level rows.
- GitHub CLI auth on the local machine has previously been flaky; GitHub Actions itself still runs once the repo secrets are configured.

## Public Repository Note

Before making the repository public, a tracked-file scan found no committed real DeepSeek key, WeCom webhook key, service-account private key marker, or local service-account filename identifier.

Public repository contents still include:

- apartment shortlist logic
- public source URLs
- social-screening markdown notes
- Google Sheet ID in the operations guide

If that is too much disclosure for long-term public hosting, remove or redact `outputs/*.md` and the Sheet ID before keeping the repo public.

## Hand-Off Checklist

For a new operator:

1. Confirm the Google Sheet is accessible to the configured service account.
2. Confirm GitHub repo secrets are set.
3. Run `python3 tracker.py test-sheet`.
4. Run `python3 tracker.py dry-run`.
5. Run `python3 tracker.py run-once --no-alerts` if rebuilding a baseline.
6. Run `python3 tracker.py run-once` for production behavior.
7. Check `Run_Log` and `Source_Status`.
8. Confirm WeCom delivery with `python3 tracker.py test-alert`.
9. Rotate the DeepSeek key if it has not already been rotated.

## Useful Links

- Repository: `https://github.com/cchun003/south-loop-lease-tracker`
- Workflow: `.github/workflows/lease-tracker.yml`
- Operations guide: `outputs/lease_tracker_operations.md`
- Main command: `python3 tracker.py run-once`
