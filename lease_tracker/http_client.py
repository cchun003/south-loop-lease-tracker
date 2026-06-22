from __future__ import annotations

import gzip
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .settings import HTTP_TIMEOUT_SECONDS, SOURCE_DELAY_SECONDS, USER_AGENT


@dataclass
class FetchResponse:
    url: str
    status_code: int
    text: str
    final_url: str
    error: str = ""


def fetch_url(url: str, *, timeout: int = HTTP_TIMEOUT_SECONDS) -> FetchResponse:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                data = gzip.decompress(data)
            charset = resp.headers.get_content_charset() or "utf-8"
            return FetchResponse(
                url=url,
                status_code=resp.status,
                text=data.decode(charset, errors="replace"),
                final_url=resp.geturl(),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return FetchResponse(url=url, status_code=exc.code, text=body, final_url=url, error=str(exc))
    except Exception as exc:
        return FetchResponse(url=url, status_code=0, text="", final_url=url, error=str(exc))


def polite_pause() -> None:
    time.sleep(SOURCE_DELAY_SECONDS)


def blocked_reason(text: str, status_code: int) -> str:
    lower = text.lower()
    if status_code in {401, 403, 429}:
        return f"http_{status_code}"
    if "just a moment" in lower and "cloudflare" in lower:
        return "cloudflare_challenge"
    if "enable javascript and cookies to continue" in lower:
        return "javascript_or_cookie_challenge"
    if "you don't have permission to access" in lower:
        return "permission_denied"
    if "access denied" in lower:
        return "access_denied"
    return ""

