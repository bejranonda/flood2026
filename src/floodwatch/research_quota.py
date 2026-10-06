"""Research calls to Open-Meteo, counted and paced by one shared ledger (owner 2026-10-06, D-108).

The free tier (10,000 calls a day, 5,000 an hour, 600 a minute; open-meteo.com/en/pricing, read 2026-10-06) is shared by
everything on this server, the live site's rain first (KI-106, KI-264). Research gets **3,000 weighted calls a day, at
most 1,000 an hour, at least 10 s apart** — the owner's budget, enforced here rather than by discipline: on 2026-10-06 a
fetch paced by hand used about 4,800 in a day against the written ≲ 1,000 (KI-264).

Weight, from the pricing page: "Requests for data covering more than 10 weather variables or extending over a period of
more than 2 weeks for a single location are considered multiple API calls … a request for 2 weeks of data with 15
weather variables will be calculated as 1.5 API calls"; each location counts on its own (KI-264). Several `models` are
counted as more variables ⚠️ (Open-Meteo does not say; the cautious reading). APIs whose counting is not documented here
(ensemble members, for one) are refused until someone adds them with evidence.

Every research process appends to the same ledger: $FLOODWATCH_RESEARCH_DIR, else /data/research inside a container
(mount it: -v "$PWD/data/research:/data/research"), else data/research in the checkout (git-ignored). A run that sees
none of them stops — a counter that forgets is no counter. Use `get_json(url)`; `take(weight)` is for other clients.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

DAY_LIMIT, HOUR_LIMIT, MIN_GAP_S = 3000.0, 1000.0, 10.0  # owner 2026-10-06 (D-108)
DAY_S, HOUR_S = 86400.0, 3600.0
LEDGER, LOCK = "openmeteo_ledger.jsonl", "openmeteo_ledger.lock"
PRUNE_LINES = 10_000
MOUNT = Path("/data/research")
CHECKOUT = Path(__file__).resolve().parents[2]
# APIs the pricing page's counting covers, with the days each returns when no dates are given (forecast: 7, flood: 92,
# per their documentation; the archive and historical APIs need dates)
HOSTS = {"api.open-meteo.com": 7, "previous-runs-api.open-meteo.com": 7, "historical-forecast-api.open-meteo.com": 7,
         "archive-api.open-meteo.com": 7, "flood-api.open-meteo.com": 92}
log = logging.getLogger(__name__)


class QuotaError(RuntimeError):
    """The research budget would be exceeded, or the shared ledger cannot be reached."""


def weight(url: str) -> float:
    """Open-Meteo's weighted call count of one request: locations × max(1, variables/10) × max(1, days/14)."""
    u = urllib.parse.urlsplit(url)
    if u.hostname not in HOSTS:
        raise ValueError(f"no documented weighting for {u.hostname}: add it to research_quota.HOSTS with evidence")
    q = urllib.parse.parse_qs(u.query)

    def items(key: str) -> list[str]:
        return [x for x in ",".join(q.get(key, [])).split(",") if x.strip()]

    locations = max(1, len(items("latitude")))
    names = sum(len(items(k)) for k in ("hourly", "daily", "minutely_15", "current"))
    variables = max(1, names) * max(1, len(items("models")))
    if q.get("start_date") and q.get("end_date"):
        days = (dt.date.fromisoformat(q["end_date"][0]) - dt.date.fromisoformat(q["start_date"][0])).days + 1
    else:
        days = int((q.get("forecast_days") or [HOSTS[u.hostname]])[0]) + int((q.get("past_days") or [0])[0])
    return locations * max(1.0, variables / 10) * max(1.0, days / 14)


def ledger_dir() -> Path:
    """The shared ledger's directory (see the module note); QuotaError when no shared place is visible."""
    env = os.environ.get("FLOODWATCH_RESEARCH_DIR", "").strip()
    if env:
        return Path(env)
    if MOUNT.is_dir():
        return MOUNT
    if (CHECKOUT / ".git").exists():
        return CHECKOUT / "data" / "research"
    raise QuotaError('no shared research ledger here: mount it (-v "$PWD/data/research:/data/research") or set '
                     "FLOODWATCH_RESEARCH_DIR")


def _rows(f: Path, since: float) -> tuple[list[dict], int]:
    """Ledger rows newer than `since`, and the number of lines read."""
    if not f.exists():
        return [], 0
    lines = f.read_text().splitlines()
    out = []
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("t", 0) > since:
            out.append(r)
    return out, len(lines)


def _free_at(rows: list[dict], w: float, limit: float, window: float) -> float:
    """The time at which enough of `rows` has left the window for `w` more to fit under `limit`."""
    total, at = sum(r["w"] for r in rows), 0.0
    for r in sorted(rows, key=lambda r: r["t"]):
        if total + w <= limit:
            break
        total -= r["w"]
        at = r["t"] + window
    return at


def take(w: float, path: Path | None = None, now=time.time, sleep=time.sleep) -> dict:
    """Count one request of weight `w`: waits for the 10 s gap and the hourly budget; QuotaError when the day's budget is
    spent (saying when it frees up) or when one request is heavier than an hour's budget."""
    if w > HOUR_LIMIT:
        raise QuotaError(f"one request weighs {w:.0f} calls, more than the hourly research budget ({HOUR_LIMIT:.0f}): "
                         "split it (fewer days, variables or points per request)")
    d = Path(path) if path is not None else ledger_dir()
    d.mkdir(parents=True, exist_ok=True)
    with open(d / LOCK, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # one research process at a time reads, waits and writes
        while True:
            t = now()
            rows, n_lines = _rows(d / LEDGER, t - DAY_S)
            day = sum(r["w"] for r in rows)
            if day + w > DAY_LIMIT:
                at = dt.datetime.fromtimestamp(_free_at(rows, w, DAY_LIMIT, DAY_S), dt.UTC)
                raise QuotaError(f"research budget for 24 h spent: {day:.0f} of {DAY_LIMIT:.0f} weighted calls; this "
                                 f"request ({w:.1f}) fits again at {at:%Y-%m-%d %H:%M} UTC")
            in_hour = [r for r in rows if r["t"] > t - HOUR_S]
            hour = sum(r["w"] for r in in_hour)
            wait = max(r["t"] for r in rows) + MIN_GAP_S - t if rows else 0.0
            if hour + w > HOUR_LIMIT:
                wait = max(wait, _free_at(in_hour, w, HOUR_LIMIT, HOUR_S) - t)
            if wait <= 0:
                break
            if wait > 60:
                log.warning("research quota: waiting %.0f s for the hourly budget (%.0f of %.0f used)",
                            wait, hour, HOUR_LIMIT)
            sleep(wait)
        if n_lines > PRUNE_LINES:  # keep the ledger small: only the last 24 h decide anything
            (d / LEDGER).write_text("".join(json.dumps(r) + "\n" for r in rows))
        with open(d / LEDGER, "a") as f:
            f.write(json.dumps({"t": round(t, 3), "w": round(w, 3)}) + "\n")
    return {"day": day + w, "hour": hour + w}


def get_json(url: str, timeout: float = 120.0, path: Path | None = None):
    """One Open-Meteo request, counted first, with the project's User-Agent (GUIDELINES §5)."""
    from floodwatch.config import settings

    take(weight(url), path=path)
    req = urllib.request.Request(url, headers={"User-Agent": settings.user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())
