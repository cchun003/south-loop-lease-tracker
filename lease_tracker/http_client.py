from __future__ import annotations

import gzip
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .settings import HTTP_TIMEOUT_SECONDS, SOURCE_DELAY_SECONDS, USER_AGENT


@dataclass
class FetchResponse:
    url: str
    status_code: int
    text: str
    final_url: str
    error: str = ""
    fetcher: str = "urllib"
    primary_blocked_reason: str = ""


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


def fetch_url_with_enhancement(
    url: str,
    *,
    env: dict[str, str] | None = None,
    timeout: int = HTTP_TIMEOUT_SECONDS,
) -> FetchResponse:
    primary = fetch_url(url, timeout=timeout)
    reason = blocked_reason(primary.text, primary.status_code)
    if not reason or not env_flag(env, "SCRAPLING_ENABLED", default=True):
        return primary

    enhanced = fetch_url_scrapling(url, env=env or {}, primary_blocked_reason=reason)
    if enhanced.error and not enhanced.text:
        enhanced.error = f"Primary blocked: {reason}; enhanced fetch failed: {enhanced.error}"
    elif enhanced.error:
        enhanced.error = f"Primary blocked: {reason}; enhanced fetch warning: {enhanced.error}"
    else:
        enhanced.error = f"Primary blocked: {reason}; enhanced fetcher used."
    return enhanced


def fetch_url_scrapling(
    url: str,
    *,
    env: dict[str, str],
    primary_blocked_reason: str,
) -> FetchResponse:
    fetcher_name = env.get("SCRAPLING_FETCHER", "stealthy").strip().lower() or "stealthy"
    try:
        page = run_scrapling_fetch(url, fetcher_name=fetcher_name, env=env)
        text = scrapling_response_text(page, env=env)
        return FetchResponse(
            url=url,
            status_code=int(getattr(page, "status", 0) or 0),
            text=text,
            final_url=str(getattr(page, "url", "") or url),
            fetcher=f"scrapling:{fetcher_name}",
            primary_blocked_reason=primary_blocked_reason,
        )
    except Exception as exc:
        return FetchResponse(
            url=url,
            status_code=0,
            text="",
            final_url=url,
            error=str(exc),
            fetcher=f"scrapling:{fetcher_name}",
            primary_blocked_reason=primary_blocked_reason,
        )


def run_scrapling_fetch(url: str, *, fetcher_name: str, env: dict[str, str]) -> Any:
    if fetcher_name == "http":
        from scrapling.fetchers import Fetcher

        return Fetcher.get(
            url,
            timeout=env_int(env, "SCRAPLING_HTTP_TIMEOUT_SECONDS", default=45),
            retries=env_int(env, "SCRAPLING_RETRIES", default=2),
            retry_delay=env_float(env, "SCRAPLING_RETRY_DELAY_SECONDS", default=1.5),
            impersonate=env.get("SCRAPLING_IMPERSONATE", "chrome"),
            stealthy_headers=env_flag(env, "SCRAPLING_STEALTHY_HEADERS", default=True),
        )

    browser_kwargs = {
        "headless": env_flag(env, "SCRAPLING_HEADLESS", default=True),
        "network_idle": env_flag(env, "SCRAPLING_NETWORK_IDLE", default=False),
        "load_dom": env_flag(env, "SCRAPLING_LOAD_DOM", default=True),
        "disable_resources": env_flag(env, "SCRAPLING_DISABLE_RESOURCES", default=False),
        "block_ads": env_flag(env, "SCRAPLING_BLOCK_ADS", default=True),
        "timeout": env_int(env, "SCRAPLING_TIMEOUT_MS", default=60000),
        "wait": env_int(env, "SCRAPLING_WAIT_MS", default=2500),
        "retries": env_int(env, "SCRAPLING_RETRIES", default=1),
        "retry_delay": env_float(env, "SCRAPLING_RETRY_DELAY_SECONDS", default=1.5),
        "google_search": env_flag(env, "SCRAPLING_GOOGLE_SEARCH", default=True),
        "extra_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "capture_xhr": env.get(
            "SCRAPLING_CAPTURE_XHR",
            r"(?i)(sightmap|doorway-api|knockrentals|rentcafe|ysi|floorplan|availability|available|unit|units|inventory|pricing|property)",
        ),
    }
    if env_flag(env, "SCRAPLING_REAL_CHROME", default=False):
        browser_kwargs["real_chrome"] = True
    if env.get("SCRAPLING_CDP_URL"):
        browser_kwargs["cdp_url"] = env["SCRAPLING_CDP_URL"]

    if fetcher_name == "dynamic":
        from scrapling.fetchers import DynamicFetcher

        return DynamicFetcher.fetch(url, **browser_kwargs)

    if fetcher_name != "stealthy":
        raise ValueError("SCRAPLING_FETCHER must be one of: stealthy, dynamic, http.")

    from scrapling.fetchers import StealthyFetcher

    browser_kwargs.update(
        {
            "solve_cloudflare": env_flag(env, "SCRAPLING_SOLVE_CLOUDFLARE", default=True),
            "block_webrtc": env_flag(env, "SCRAPLING_BLOCK_WEBRTC", default=True),
            "hide_canvas": env_flag(env, "SCRAPLING_HIDE_CANVAS", default=True),
        }
    )
    return StealthyFetcher.fetch(url, **browser_kwargs)


def scrapling_response_text(page: Any, *, env: dict[str, str]) -> str:
    encoding = getattr(page, "encoding", None) or "utf-8"
    body = getattr(page, "body", b"") or b""
    text = body.decode(encoding, errors="replace") if isinstance(body, bytes) else str(body)
    if not env_flag(env, "SCRAPLING_APPEND_CAPTURED_XHR", default=True):
        return text

    max_chars = env_int(env, "SCRAPLING_CAPTURED_XHR_MAX_CHARS", default=250000)
    appended = 0
    chunks: list[str] = []
    for item in getattr(page, "captured_xhr", []) or []:
        xhr_body = getattr(item, "body", b"") or b""
        if isinstance(xhr_body, bytes):
            xhr_text = xhr_body.decode(getattr(item, "encoding", None) or "utf-8", errors="replace")
        else:
            xhr_text = str(xhr_body)
        if not xhr_text.strip():
            continue
        remaining = max_chars - appended
        if remaining <= 0:
            break
        xhr_text = xhr_text[:remaining]
        appended += len(xhr_text)
        chunks.append(
            "\n<!-- scrapling captured_xhr: "
            + str(getattr(item, "url", ""))
            + " -->\n"
            + xhr_text
        )
    return text + "".join(chunks)


def env_flag(env: dict[str, str] | None, key: str, *, default: bool) -> bool:
    if not env or key not in env or env[key] == "":
        return default
    value = str(env[key]).strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return default


def env_int(env: dict[str, str], key: str, *, default: int) -> int:
    try:
        return int(str(env.get(key, "")).strip() or default)
    except ValueError:
        return default


def env_float(env: dict[str, str], key: str, *, default: float) -> float:
    try:
        return float(str(env.get(key, "")).strip() or default)
    except ValueError:
        return default


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
