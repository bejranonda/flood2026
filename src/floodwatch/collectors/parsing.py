"""Pure parsers for source payloads (unit-tested with recorded fixtures). No I/O here."""
from __future__ import annotations

import datetime as dt
import math
from typing import Any

from floodwatch.config import FOCUS_PROVINCES

ICT = dt.timezone(dt.timedelta(hours=7))
SENTINEL_ABS = 1000.0  # HII uses 999999 for missing/bad values (KI-206)


def parse_local(ts: str | None) -> dt.datetime | None:
    """HII local timestamps have no timezone -> Asia/Bangkok (+07:00) (KI-205)."""
    if not ts:
        return None
    ts = ts.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return dt.datetime.strptime(ts, fmt).replace(tzinfo=ICT).astimezone(dt.timezone.utc)
        except ValueError:
            continue
    return None


def to_float(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def qc_level(level: float | None, bank: float | None, ground: float | None) -> tuple[float | None, str]:
    """Flag, don't delete: returns (value_or_None, flag)."""
    if level is None:
        return None, "missing"
    if abs(level) >= SENTINEL_ABS:
        return None, "sentinel"
    lo = (ground - 5.0) if ground is not None else -30.0
    hi = (bank + 8.0) if bank is not None else 200.0
    if not (lo <= level <= hi):
        return level, "out_of_range"
    return level, "ok"


def _name(d: dict | None, lang: str) -> str | None:
    return (d or {}).get(lang) or None


def parse_waterlevel_load(payload: dict, raw_ref: str) -> tuple[list[dict], list[dict]]:
    stations: list[dict] = []
    obs: list[dict] = []
    for r in payload.get("waterlevel_data", {}).get("data", []) or []:
        s = r.get("station") or {}
        code = (s.get("tele_station_oldcode") or "").strip() or f"hii:{s.get('id')}"
        geo = r.get("geocode") or {}
        province = _name(geo.get("province_name"), "th")
        lat, lon = to_float(s.get("tele_station_lat")), to_float(s.get("tele_station_long"))
        if lat == 0 and lon == 0:
            lat = lon = None
        bank, ground = to_float(s.get("min_bank")), to_float(s.get("ground_level"))
        stations.append({
            "code": code, "hii_id": s.get("id"), "name_th": _name(s.get("tele_station_name"), "th"),
            "name_en": _name(s.get("tele_station_name"), "en"), "lat": lat, "lon": lon,
            "bank_msl": bank, "ground_msl": ground, "critical_msl": to_float(s.get("critical_level_msl")),
            "agency": ((r.get("agency") or {}).get("agency_shortname") or {}).get("en"),
            "province": province, "amphoe": _name(geo.get("amphoe_name"), "th"),
            "river": r.get("river_name"), "basin": _name((r.get("basin") or {}).get("basin_name"), "th"),
            "in_focus": province in FOCUS_PROVINCES, "meta_source": "hii_load",
        })
        t = parse_local(r.get("waterlevel_datetime"))
        if t is None:
            continue
        level, flag = qc_level(to_float(r.get("waterlevel_msl")), bank, ground)
        obs.append({"code": code, "obs_time": t, "level_msl": level, "discharge": to_float(r.get("discharge")),
                    "situation_level": r.get("situation_level"), "source": "hii_load",
                    "quality_flag": flag, "raw_ref": raw_ref})
    return stations, obs


def parse_waterlevel_graph(code: str, payload: dict, bank: float | None, ground: float | None,
                           raw_ref: str) -> list[dict]:
    out = []
    for p in (payload.get("data") or {}).get("graph_data") or []:
        t = parse_local(p.get("datetime"))
        if t is None:
            continue
        v = to_float(p.get("value"))
        if v is None and p.get("discharge") is None:
            continue
        level, flag = qc_level(v, bank, ground)
        out.append({"code": code, "obs_time": t, "level_msl": level, "discharge": to_float(p.get("discharge")),
                    "situation_level": None, "source": "hii_graph", "quality_flag": flag, "raw_ref": raw_ref})
    return out


def parse_chart(code: str, rows: list, raw_ref: str) -> tuple[list[dict], float | None, float | None]:
    """HII chart XHR rows: [epoch_ms_UTC, level_msl, bank, ground, level_str]."""
    out: list[dict] = []
    bank = ground = None
    for r in rows or []:
        if not isinstance(r, list) or len(r) < 2:
            continue
        bank = to_float(r[2]) if len(r) > 2 else bank
        ground = to_float(r[3]) if len(r) > 3 else ground
        t = dt.datetime.fromtimestamp(r[0] / 1000.0, tz=dt.timezone.utc)
        level, flag = qc_level(to_float(r[1]), bank, ground)
        out.append({"code": code, "obs_time": t, "level_msl": level, "discharge": None, "situation_level": None,
                    "source": "hii_chart", "quality_flag": flag, "raw_ref": raw_ref})
    return out, bank, ground


def parse_rain(payload: dict) -> list[dict]:
    out = []
    for r in payload.get("data", []) or []:
        s = r.get("station") or {}
        geo = r.get("geocode") or {}
        province = _name(geo.get("province_name"), "th")
        if province not in FOCUS_PROVINCES:
            continue
        t = parse_local(r.get("rainfall_datetime"))
        if t is None:
            continue
        out.append({"code": str(s.get("tele_station_oldcode") or s.get("id")), "obs_time": t,
                    "rain_1h": to_float(r.get("rain_1h")), "rain_24h": to_float(r.get("rain_24h")),
                    "lat": to_float(s.get("tele_station_lat")), "lon": to_float(s.get("tele_station_long")),
                    "name_th": _name(s.get("tele_station_name"), "th"), "province": province})
    return out


FLOOD_WORDS = ("น้ำท่วม", "น้ำขัง", "ท่วมขัง", "น้ำเอ่อ", "ระบายน้ำ")


def parse_traffy(payload: dict) -> list[dict]:
    """Keep only id, time, coordinates, state and a flood flag. Text and photos are discarded (KI-107)."""
    out = []
    for r in payload.get("results", []) or []:
        coords = r.get("coords") or []
        if len(coords) != 2:
            continue
        lon, lat = to_float(coords[0]), to_float(coords[1])
        ts = r.get("timestamp")
        try:
            t = dt.datetime.fromisoformat(ts.replace("+00", "+00:00")) if ts else None
        except ValueError:
            t = None
        if t is None or lat is None or lon is None:
            continue
        text = " ".join([r.get("description") or "", " ".join(r.get("problem_type_abdul") or [])])
        out.append({"ticket_id": r.get("ticket_id"), "report_time": t, "lat": lat, "lon": lon,
                    "state": r.get("state"), "is_flood": any(w in text for w in FLOOD_WORDS)})
    return [o for o in out if o["ticket_id"]]


def parse_openmeteo(point: str, payload: dict, issue_time: dt.datetime, model: str = "best_match") -> list[dict]:
    hourly = payload.get("hourly") or {}
    times, precip = hourly.get("time") or [], hourly.get("precipitation") or []
    offset = dt.timedelta(seconds=int(payload.get("utc_offset_seconds") or 0))
    out = []
    for t, p in zip(times, precip):
        vt = (dt.datetime.fromisoformat(t) - offset).replace(tzinfo=dt.timezone.utc)
        out.append({"point": point, "issue_time": issue_time, "valid_time": vt, "model": model,
                    "precip_mm": to_float(p)})
    return out
