from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


class GoogleSheetsClient:
    def __init__(self, sheet_id: str, credentials: dict[str, Any]):
        self.sheet_id = sheet_id
        self.credentials = credentials
        self._token = ""
        self._token_expires_at = 0

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "GoogleSheetsClient":
        sheet_id = env.get("GOOGLE_SHEET_ID")
        if not sheet_id:
            raise RuntimeError("GOOGLE_SHEET_ID is not configured.")
        if env.get("GOOGLE_SERVICE_ACCOUNT_JSON_B64"):
            raw = base64.b64decode(env["GOOGLE_SERVICE_ACCOUNT_JSON_B64"]).decode("utf-8")
            credentials = json.loads(raw)
        elif env.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
            credentials = json.loads(env["GOOGLE_SERVICE_ACCOUNT_JSON"])
        elif env.get("GOOGLE_APPLICATION_CREDENTIALS"):
            credentials = json.loads(Path(env["GOOGLE_APPLICATION_CREDENTIALS"]).read_text(encoding="utf-8"))
        else:
            raise RuntimeError(
                "Google credentials missing. Set GOOGLE_SERVICE_ACCOUNT_JSON_B64, "
                "GOOGLE_SERVICE_ACCOUNT_JSON, or GOOGLE_APPLICATION_CREDENTIALS."
            )
        return cls(sheet_id=sheet_id, credentials=credentials)

    def token(self) -> str:
        now = int(time.time())
        if self._token and now < self._token_expires_at - 60:
            return self._token
        header = {"alg": "RS256", "typ": "JWT"}
        claim = {
            "iss": self.credentials["client_email"],
            "scope": SHEETS_SCOPE,
            "aud": TOKEN_URL,
            "iat": now,
            "exp": now + 3600,
        }
        signing_input = (
            b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
            + "."
            + b64url(json.dumps(claim, separators=(",", ":")).encode("utf-8"))
        ).encode("ascii")
        private_key = serialization.load_pem_private_key(
            self.credentials["private_key"].encode("utf-8"),
            password=None,
        )
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        assertion = signing_input.decode("ascii") + "." + b64url(signature)
        payload = urllib.parse.urlencode(
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            token = json.loads(resp.read().decode("utf-8"))
        self._token = token["access_token"]
        self._token_expires_at = now + int(token.get("expires_in", 3600))
        return self._token

    def request_json(self, method: str, path: str, payload: Any | None = None) -> dict[str, Any]:
        url = f"{SHEETS_API}/{self.sheet_id}{path}"
        data = None
        headers = {"Authorization": f"Bearer {self.token()}"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Google Sheets API HTTP {exc.code}: {body}") from exc

    def values_get(self, a1_range: str) -> list[list[str]]:
        encoded = urllib.parse.quote(a1_range, safe="")
        data = self.request_json("GET", f"/values/{encoded}")
        return data.get("values", [])

    def values_clear(self, ranges: list[str]) -> None:
        self.request_json("POST", "/values:batchClear", {"ranges": ranges})

    def values_update(self, updates: list[dict[str, Any]]) -> None:
        self.request_json(
            "POST",
            "/values:batchUpdate",
            {"valueInputOption": "USER_ENTERED", "data": updates},
        )

    def values_append(self, a1_range: str, rows: list[list[Any]]) -> None:
        if not rows:
            return
        encoded = urllib.parse.quote(a1_range, safe="")
        params = urllib.parse.urlencode(
            {"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}
        )
        self.request_json(
            "POST",
            f"/values/{encoded}:append?{params}",
            {"values": rows},
        )


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def rows_to_dicts(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    headers = [str(cell) for cell in rows[0]]
    out: list[dict[str, str]] = []
    for row in rows[1:]:
        item = {}
        for idx, header in enumerate(headers):
            item[header] = str(row[idx]) if idx < len(row) else ""
        out.append(item)
    return out

