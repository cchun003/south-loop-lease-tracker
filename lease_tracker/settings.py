from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT / ".secrets" / "tracker.env"

PREFERRED_RENT = 3500
HARD_RENT_CAP = 4000
TARGET_BEDS = 2
TARGET_BATHS = 2

SOURCE_DELAY_SECONDS = 1.25
HTTP_TIMEOUT_SECONDS = 35

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 LeaseTracker/0.1"
)

SHEET_TABS = {
    "units": "Units",
    "history": "Unit_History",
    "alerts": "Alerts",
    "run_log": "Run_Log",
}

