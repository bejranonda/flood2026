"""Polite HTTP: honest User-Agent, gzip, retries with backoff, optional Thai egress proxy (D-004, D-014)."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

from floodwatch.config import settings

log = logging.getLogger(__name__)
_session = requests.Session()


@dataclass
class Fetched:
    url: str
    status: int
    body: bytes
    content_type: str


def fetch(url: str, *, via_thai_egress: bool = False, retries: int = 3, method: str = "GET",
          data: dict | None = None) -> Fetched:
    """Fetch a URL. Raises the last error if every attempt fails."""
    headers = {"User-Agent": settings.user_agent, "Accept": "application/json, text/html;q=0.8, */*;q=0.5",
               "Accept-Encoding": "gzip, deflate"}
    proxies = None
    if via_thai_egress:
        if not settings.thai_egress_proxy:
            raise RuntimeError("THAI_EGRESS_PROXY not configured")
        proxies = {"http": settings.thai_egress_proxy, "https": settings.thai_egress_proxy}
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = _session.request(method, url, headers=headers, timeout=settings.timeout_s,
                                    proxies=proxies, data=data)
            if resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            return Fetched(url, resp.status_code, resp.content, resp.headers.get("content-type", ""))
        except Exception as e:  # network error or 5xx: back off and retry
            last = e
            wait = min(8, 2 ** attempt)
            log.warning("fetch failed (%s) attempt %d/%d, retry in %ss: %s", url, attempt + 1, retries, wait, e)
            time.sleep(wait)
    assert last is not None
    raise last
