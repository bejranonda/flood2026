"""Place search for areas without a gauge (a real user near สะพานใหม่ asked for their soi, 2026-09-26).

OpenStreetMap Nominatim, called by our server only when the user presses search (never per keystroke), limited to
the Bangkok region, at most 1 request/s across all app workers (Nominatim usage policy), cached in memory.
Privacy: queries are what people type, often their own street, so they are never logged or stored in the database.
"""
from __future__ import annotations

import re
import threading
import time
from collections import OrderedDict

import requests

from floodwatch.config import settings

URL = "https://nominatim.openstreetmap.org/search"
VIEWBOX = "99.8,14.6,101.0,13.4"  # lon1,lat1,lon2,lat2: Bangkok, suburbs and Ayutthaya
# Thailand-wide since v0.16 (D-064): the Bangkok box only ranks Bangkok first (bounded=0), it no longer limits results
SEARCH_PARAMS = {"format": "jsonv2", "limit": 5, "countrycodes": "th", "viewbox": VIEWBOX, "bounded": 0,
                 "accept-language": "th"}
MIN_INTERVAL_S = 1.1
CACHE_MAX, CACHE_TTL_S = 500, 7 * 24 * 3600
_cache: OrderedDict[str, tuple[float, list[dict]]] = OrderedDict()
_lock = threading.Lock()


def parse(rows: list) -> list[dict]:
    """Nominatim jsonv2 rows -> [{name, area, lat, lon}]: the first address part as the name, the next parts
    (usually แขวง, เขต) as the area. Duplicates (same name at ~100 m) are dropped."""
    out: list[dict] = []
    for r in rows or []:
        parts = [p.strip() for p in (r.get("display_name") or "").split(",") if p.strip()]
        try:
            lat, lon = round(float(r["lat"]), 5), round(float(r["lon"]), 5)
        except (KeyError, TypeError, ValueError):
            continue
        if not parts:
            continue
        area = ", ".join(p for p in parts[1:4] if not p.isdigit() and p != "ประเทศไทย")
        if any(o["name"] == parts[0] and abs(o["lat"] - lat) < 0.001 and abs(o["lon"] - lon) < 0.001 for o in out):
            continue
        out.append({"name": parts[0], "area": area, "lat": lat, "lon": lon})
    return out


# How people write Bangkok addresses vs how OSM names them: "ซ.", "ถ.", "พหล" for พหลโยธิน.
ALIASES = [(r"(^|\s)ซ\.\s*", r"\1ซอย"), (r"(^|\s)ถ\.\s*", r"\1ถนน"), (r"พหล(?!โยธิน)", "พหลโยธิน")]


def variants(q: str) -> list[str]:
    """Queries to send. A name ending in a number without "ซอย" is usually a soi ("ลาดพร้าว 71" is
    "ซอยลาดพร้าว 71" in OSM, while "พหลโยธิน 52" is found as is), so both forms are tried."""
    q = " ".join(q.split())
    for pat, rep in ALIASES:
        q = re.sub(pat, rep, q)
    out = [q]
    if re.search(r"\d+$", q) and not q.startswith(("ซอย", "ถนน")):
        out.append("ซอย" + q)
    return out


def rank(q_variants: list[str], results: list[dict]) -> list[dict]:
    """Exact name matches first (the soi the user typed), then the rest in Nominatim's order."""
    wanted = {v.replace(" ", "") for v in q_variants}
    return sorted(results, key=lambda r: r["name"].replace(" ", "") not in wanted)


def _throttle(conn) -> None:
    """One request per MIN_INTERVAL_S across processes: a Postgres advisory lock serialises the uvicorn workers and
    collector_state keeps the time of the last call (only a timestamp, never the query)."""
    conn.execute("SELECT pg_advisory_xact_lock(727001)")
    row = conn.execute("SELECT value FROM collector_state WHERE key='nominatim_last'").fetchone()
    last = float(row["value"]) if row else 0.0
    wait = last + MIN_INTERVAL_S - time.time()
    if wait > 5:
        raise TimeoutError("busy")
    if wait > 0:
        time.sleep(wait)
    conn.execute("""INSERT INTO collector_state (key, value, updated_at) VALUES ('nominatim_last', to_jsonb(%s::float), now())
                    ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()""", (time.time(),))


def search(q: str, conn) -> list[dict]:
    key = " ".join(q.lower().split())
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL_S:
            _cache.move_to_end(key)
            return hit[1]
    qs, results = variants(q), []
    for v in qs:
        _throttle(conn)
        r = requests.get(URL, params={"q": v, **SEARCH_PARAMS},
                         headers={"User-Agent": settings.user_agent}, timeout=10)
        conn.commit()  # release the advisory lock only after the call, so calls stay ≥ 1.1 s apart
        r.raise_for_status()
        for hit in parse(r.json()):
            if not any(h["name"] == hit["name"] and abs(h["lat"] - hit["lat"]) < 0.001 for h in results):
                results.append(hit)
    results = rank(qs, results)[:5]
    with _lock:
        _cache[key] = (time.time(), results)
        while len(_cache) > CACHE_MAX:
            _cache.popitem(last=False)
    return results


# --- Reverse lookup for the point panel's district line (issue #3). Same rules as search: our server calls
# Nominatim at most 1/s, coordinates are rounded to ~1 km before the call and cached, nothing is logged or stored.
REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
PREFIXES = ("แขวง", "เขต", "ตำบล", "อำเภอ", "จังหวัด")
_rcache: OrderedDict[tuple[float, float], tuple[float, str | None]] = OrderedDict()


def reverse_key(lat: float, lon: float) -> tuple[float, float]:
    return (round(lat, 2), round(lon, 2))  # ~1.1 km cells: enough for แขวง/เขต, and never the exact position


def reverse_label(addr: dict) -> str | None:
    """"คลองจั่น, บางกะปิ, กรุงเทพมหานคร": subdistrict, district, province without the administrative prefixes."""
    parts = []
    for keys in (("quarter", "village", "town", "municipality", "suburb_sub"), ("suburb", "county", "city_district"),
                 ("city", "province", "state")):
        v = next((addr[k] for k in keys if addr.get(k)), None)
        if v:
            for p in PREFIXES:
                if v.startswith(p) and len(v) > len(p):
                    v = v[len(p):]
                    break
            parts.append(v.strip())
    return ", ".join(parts) or None


def reverse(lat: float, lon: float, conn) -> str | None:
    key = reverse_key(lat, lon)
    with _lock:
        hit = _rcache.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL_S:
            return hit[1]
    _throttle(conn)
    r = requests.get(REVERSE_URL, params={"lat": key[0], "lon": key[1], "format": "jsonv2", "zoom": 14,
                                          "addressdetails": 1, "accept-language": "th"},
                     headers={"User-Agent": settings.user_agent}, timeout=4)
    conn.commit()
    r.raise_for_status()
    label = reverse_label((r.json() or {}).get("address") or {})
    with _lock:
        _rcache[key] = (time.time(), label)
        while len(_rcache) > CACHE_MAX:
            _rcache.popitem(last=False)
    return label
