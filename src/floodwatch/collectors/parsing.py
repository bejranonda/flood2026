"""Pure parsers for source payloads (unit-tested with recorded fixtures). No I/O here."""
from __future__ import annotations

import datetime as dt
import math
import re
from typing import Any

from floodwatch.config import FOCUS_PROVINCES

ICT = dt.timezone(dt.timedelta(hours=7))
SENTINEL_ABS = 1000.0  # HII uses 999999 for missing/bad values (KI-206)
# Physically implausible: > 3 m above the bank. Evidence 2026-09-26 (30 days, all focus gauges): genuine maxima
# reach +1.90 m (C.67); above +3 m only broken readings (BKK003 stuck at a 7.45 m ceiling, spikes at BKK006, CPY012).
MAX_ABOVE_BANK_M = 3.0


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
    hi = (bank + MAX_ABOVE_BANK_M) if bank is not None else 200.0
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
            "river": r.get("river_name"), "basin": _name((r.get("basin") or {}).get("basin_name"), "th"), "sub_basin": s.get("sub_basin_id"),
            "in_focus": province in FOCUS_PROVINCES, "meta_source": "hii_load",
        })
        t = parse_local(r.get("waterlevel_datetime"))
        if t is None:
            continue
        level, flag = qc_level(to_float(r.get("waterlevel_msl")), bank, ground)
        if flag == "ok" and t > dt.datetime.now(dt.timezone.utc) + FUTURE_TOLERANCE:
            flag = "future_time"  # 28 gauges arrived stamped ~21 h ahead in one fetch (2026-09-30); never the "latest" reading
        obs.append({"code": code, "obs_time": t, "level_msl": level, "discharge": to_float(r.get("discharge")),
                    "situation_level": r.get("situation_level"), "source": "hii_load",
                    "quality_flag": flag, "raw_ref": raw_ref})
    return stations, obs


def parse_waterlevel_graph(code: str, payload: dict, bank: float | None, ground: float | None,
                           raw_ref: str) -> list[dict]:
    out = []
    if not isinstance(payload, dict) or not isinstance(payload.get("data") or {}, dict):
        raise ValueError(f"unexpected waterlevel_graph payload for {code}: {str(payload)[:80]!r}")  # e.g. an HII error string
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
        b = to_float(r[2]) if len(r) > 2 else None
        g = to_float(r[3]) if len(r) > 3 else None
        if b == 0 and g == 0:  # chart placeholders for "unknown" (seen at ATG011)
            b = g = None
        bank, ground = b if b is not None else bank, g if g is not None else ground
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
        province = _name(geo.get("province_name"), "th")  # every province since v0.16.3 (D-064 parity)
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


def parse_map_feed(rows: list) -> list[dict]:
    """HII map feed json/telemetering/wl/warning: the only place chart-only stations expose coordinates."""
    out = []
    for r in rows or []:
        code = (r.get("code") or "").strip()
        lat, lon = to_float(r.get("lat")), to_float(r.get("lng"))
        if not code or lat in (None, 0.0) or lon in (None, 0.0):
            continue
        out.append({"code": code, "name_th": r.get("name"), "lat": lat, "lon": lon,
                    "bank_msl": to_float(r.get("bank")), "ground_msl": to_float(r.get("ground_level")),
                    "province": r.get("province_name"), "amphoe": r.get("amphoe_name"), "basin": r.get("basin")})
    return out


FUTURE_TOLERANCE = dt.timedelta(minutes=15)
BMA_MISSING = -99.0  # BMA KlongMap marks absent readings (e.g. no outside gauge) with -99


def _ms_date(v: str | None) -> dt.datetime | None:
    """BMA/.NET '/Date(1790438700000)/' -> aware UTC datetime (epoch milliseconds)."""
    m = re.fullmatch(r"/Date\((-?\d+)\)/", v or "")
    return dt.datetime.fromtimestamp(int(m.group(1)) / 1000, dt.timezone.utc) if m else None


def parse_bma_klongmap(payload: dict, raw_ref: str) -> tuple[list[dict], list[dict]]:
    """BMA DDS KlongMap JSON (as relayed by flood69.peoplesparty.or.th/api/klongmap, SOURCES §2c).

    Stations: `water_station_info` (code WL.xxx.nn, lat/lon, left/right bank). Latest reading: `water_level_last`
    (`wl_in`; at gates `wl_out01` is the outside level, archived raw only for now). The bank is the lower of the two
    banks. BMA's `warning`/`critical` are operating levels, not banks, and are deliberately not used (KI-215).
    Levels are BMA's own datum: never compare them with HII levels directly (KI-217)."""
    stations: dict[str, dict] = {}
    obs: list[dict] = []
    for w in payload.get("waterStation") or []:
        info, last = w.get("water_station_info"), w.get("water_level_last")
        if not info or not info.get("water_code"):
            continue
        code = info["water_code"].strip()
        banks = [b for b in (to_float(info.get("left_bank")), to_float(info.get("right_bank"))) if b is not None]
        bank = min(banks) if banks else None
        lat, lon = to_float(info.get("latitude")), to_float(info.get("longitude"))
        stations[code] = {
            "code": code, "hii_id": None, "name_th": info.get("water_shortname") or info.get("water_name"),
            "name_en": info.get("water_shortname_en"), "lat": lat if lat else None, "lon": lon if lon else None,
            # BMA's warning/critical are drainage operating levels, not banks (KI-215). Above them the canal can no
            # longer take street water well, which matched street-flood reports better than the bank (D-038).
            "bank_msl": bank, "ground_msl": None, "critical_msl": to_float(info.get("critical")),
            "warning_msl": to_float(info.get("warning")), "agency": "BMA",
            "province": "กรุงเทพมหานคร", "amphoe": None, "river": info.get("river_name"), "basin": None,
            "in_focus": True, "meta_source": "bma_klongmap"}
        t = _ms_date((last or {}).get("site_timestamp"))
        raw = to_float((last or {}).get("wl_in"))
        if t is None or raw is None or raw == BMA_MISSING:
            continue
        level, flag = qc_level(raw, bank, to_float(info.get("bed_bank")))
        if flag == "ok" and t > dt.datetime.now(dt.timezone.utc) + FUTURE_TOLERANCE:
            flag = "future_time"  # logger clock far ahead (a few minutes is normal: WL.KKD.04 +5 min, 2026-09-26)
        obs.append({"code": code, "obs_time": t, "level_msl": level, "discharge": None, "situation_level": None,
                    "source": "bma_klongmap", "quality_flag": flag, "raw_ref": raw_ref})
    return list(stations.values()), obs


def parse_fews_forecast(text: str, issue_time: dt.datetime) -> list[dict[str, Any]]:
    """HII FEWS forecast file (`station,date,time,value`, Thai time, hourly). The file starts ~6 days before the
    issue time (a series matching observations to 1-3 cm, i.e. not a forecast) and runs 7 days ahead; only rows after
    the issue time (the file's Last-Modified) are the forecast (D-050)."""
    out = []
    for line in (text or "").splitlines()[1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4 or not parts[3]:
            continue
        try:
            v = float(parts[3])
        except ValueError:
            continue
        t = parse_local(f"{parts[1]} {parts[2]}")
        # 999999 = missing (KI-206). Not SENTINEL_ABS: discharge files carry real values above 1000 m3/s.
        if t is None or not math.isfinite(v) or abs(v) >= 99999 or t <= issue_time:
            continue
        out.append({"valid_time": t, "value": v})
    return out


def parse_openmeteo_prev(point: str, payload: dict) -> list[dict[str, Any]]:
    """Open-Meteo previous-runs API (timezone=UTC): hourly rain as forecast ~1 and ~2 days before each hour
    (`precipitation_previous_day1/2`). Training data for the rain-aware model (D-052); hours missing either lead are
    dropped so training and backtest use the same information."""
    h = (payload or {}).get("hourly") or {}
    out = []
    for ts, d1, d2 in zip(h.get("time") or [], h.get("precipitation_previous_day1") or [],
                          h.get("precipitation_previous_day2") or []):
        if d1 is None or d2 is None:
            continue
        out.append({"point": point, "valid_time": dt.datetime.fromisoformat(ts).replace(tzinfo=dt.timezone.utc),
                    "day1": float(d1), "day2": float(d2)})
    return out


def parse_canal_graph(code: str, payload: dict, raw_ref: str) -> list[dict[str, Any]]:
    """HII `waterlevel_graph?station_type=canal` for a BMA canal gauge (D-054): the same BMA values as the relay
    (checked 2026-09-27: 46 matching times, difference 0.0 m), 15-min, Thai local time. Kept hourly (on the hour)
    like our other backfills; the relay keeps adding 5-min live readings."""
    out = []
    data = payload.get("data") if isinstance(payload, dict) else None
    graph = data.get("graph_data") if isinstance(data, dict) else None  # some gauges answer data="<message>"
    for g in graph if isinstance(graph, list) else []:
        if not isinstance(g, dict):
            continue
        v, ts = g.get("value"), g.get("datetime") or ""
        if v is None or not ts.endswith(":00"):  # "YYYY-MM-DD HH:MM": keep minute 00 only
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        t = parse_local(ts)
        if t is None or not math.isfinite(v) or abs(v) >= SENTINEL_ABS:
            continue
        out.append({"code": code, "obs_time": t, "level_msl": v, "discharge": None, "situation_level": None,
                    "source": "hii_canal_graph", "quality_flag": "ok", "raw_ref": raw_ref})
    return out


_SAT_FILE = re.compile(r"(?:^|\s|,)[A-Za-z0-9]{2,4}_(\d{8})_\d{4}")


def _strip_admin(name: str | None, prefix: str) -> str | None:
    name = (name or "").strip()
    return name[len(prefix):].strip() if name.startswith(prefix) else (name or None)


def _dwr_time(s: str | None) -> dt.datetime | None:
    """DWR EWS dates: "04/10/69 01:15 น." = day/month/Buddhist short year (2569 = 2026), Thai time."""
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{2})\s+(\d{1,2}):(\d{2})", s or "")
    if not m:
        return None
    d, mo, yy, hh, mi = map(int, m.groups())
    return dt.datetime(2500 + yy - 543, mo, d, hh, mi, tzinfo=ICT).astimezone(dt.timezone.utc)


def _num(v: Any) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def parse_dwr_stations(payload: list) -> tuple[list[dict], list[dict]]:
    """DWR EWS `LoadStation` (2,275 posts, 455 with a level, 2026-10-03): level posts and their latest reading. The
    level is the depth on a local staff post, not m MSL; `alert_max` is mostly a default 4.00 m (kept, never used as
    a bank). Rain-only posts (stn_type "RF") are skipped; the raw payload is archived with them."""
    stations, obs = [], []
    for r in payload or []:
        if (r.get("stn_type") or "").strip() != "wl" or not r.get("stn"):
            continue
        am = _num(r.get("alert_max"))
        stations.append({"code": r["stn"], "name_th": r.get("name"), "lat": _num(r.get("latitude")), "lon": _num(r.get("longitude")),
                         "province": r.get("province"), "amphoe": r.get("amphoe"), "tambon": r.get("tambon"),
                         "main_basin": r.get("main_basin"), "sub_basin": r.get("sub_basin"), "dept": r.get("dept"),
                         "alert_max": am if am else None, "status": None if r.get("status") is None else str(r["status"])})
        lv, t = _num(r.get("wl")), _dwr_time(r.get("date"))
        if lv is not None and t is not None:
            obs.append({"code": r["stn"], "obs_time": t, "level": lv})
    return stations, obs


# --- Google Flood Hub (Flood Forecasting API v1, D-087) ----------------------------------------------------------------
def _gtime(s: str | None) -> dt.datetime | None:
    """RFC 3339 UTC ("2026-10-04T08:24:32.363885Z")."""
    if not s:
        return None
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def parse_gfh_gauges(gauges: list) -> list[dict]:
    """gauges:searchGaugesByArea → one row per gauge (HYBAS virtual gauges in Thailand, 2026-10-04)."""
    return [{"gauge_id": g["gaugeId"], "lat": (g.get("location") or {}).get("latitude"), "lon": (g.get("location") or {}).get("longitude"),
             "source": g.get("source"), "quality_verified": bool(g.get("qualityVerified")), "has_model": bool(g.get("hasModel"))}
            for g in gauges or [] if g.get("gaugeId")]


def parse_gfh_status(statuses: list) -> list[dict]:
    """floodStatus:searchLatestFloodStatusByArea → severity, trend and the forecast window per gauge and issue."""
    out = []
    for s in statuses or []:
        if not s.get("gaugeId") or not s.get("issuedTime"):
            continue
        rng = s.get("forecastTimeRange") or {}
        out.append({"gauge_id": s["gaugeId"], "issued_time": _gtime(s["issuedTime"]), "severity": s.get("severity"),
                    "trend": s.get("forecastTrend"), "range_start": _gtime(rng.get("start")), "range_end": _gtime(rng.get("end")),
                    "inundation": (s.get("inundationMapSet") or {}).get("inundationMapType")})
    return out


def parse_gfh_models(models: list) -> list[dict]:
    """gaugeModels:batchGet → Google's warning / danger / extreme-danger thresholds (m³/s for HYBAS gauges)."""
    out = []
    for m in models or []:
        t = m.get("thresholds") or {}
        out.append({"gauge_id": m.get("gaugeId"), "warning": t.get("warningLevel"), "danger": t.get("dangerLevel"),
                    "extreme": t.get("extremeDangerLevel"), "unit": m.get("gaugeValueUnit")})
    return [m for m in out if m["gauge_id"]]


def parse_gfh_forecasts(payload: dict) -> list[dict]:
    """gauges:queryGaugeForecasts → one row per gauge, issue and daily step (value in the gauge's unit)."""
    out = []
    for gid, v in ((payload or {}).get("forecasts") or {}).items():
        for f in v.get("forecasts") or []:
            it = _gtime(f.get("issuedTime"))
            for r in f.get("forecastRanges") or []:
                if r.get("value") is None:
                    continue
                out.append({"gauge_id": gid, "issued_time": it, "start_time": _gtime(r.get("forecastStartTime")),
                            "end_time": _gtime(r.get("forecastEndTime")), "value": float(r["value"])})
    return out


def parse_hii_dams(payload: dict) -> list[dict]:
    """HII analyst/dam → `dam_daily`: one row per large dam and day (RID, EGAT; values in million m³ and m MSL). A level of
    0 means "not reported". The two Kaeng Krachan records disagree (RID 10.8 vs EGAT 3.04 ล้าน ลบ.ม./วัน on 4-5 Oct 2026);
    RID's matches the gauge below the dam (D-099)."""
    out = []
    for x in ((payload or {}).get("data") or {}).get("dam_daily") or []:
        dam = x.get("dam") or {}
        if dam.get("id") is None or not x.get("dam_date"):
            continue
        num = lambda k: None if x.get(k) is None else float(x[k])
        lvl = num("dam_level")
        out.append({"dam_id": int(dam["id"]),
                    "agency": (((x.get("agency") or {}).get("agency_shortname")) or {}).get("en"),
                    "name_th": (dam.get("dam_name") or {}).get("th"), "dam_date": str(x["dam_date"])[:10],
                    "storage_mcm": num("dam_storage"), "storage_pct": num("dam_storage_percent"), "inflow_mcm": num("dam_inflow"),
                    "released_mcm": num("dam_released"), "spilled_mcm": num("dam_spilled"), "level_m": lvl if lvl else None})
    return out


def parse_hii_dam_year(payload: dict) -> dict:
    """HII analyst/dam_yearly_graph (one dam, one year, one data_type): the daily values with Thai dates (empty days dropped),
    the upper/lower rule curves by day of year ("MM-DD", ล้าน ลบ.ม.; HII lists them for a leap year) and the storage bounds
    (normal_bound = the storage RID's percent divides by; checked 2026-10-05: 725.85 / 710 = 102.23 %)."""
    d = payload.get("data") or {}
    series = [(x["date"][:10], float(x["value"])) for g in d.get("graph_data") or [] for x in g.get("data") or []
              if x.get("value") is not None and x.get("date")]

    def curve(key: str) -> dict:
        return {x["date"][5:10]: float(x["value"]) for x in d.get(key) or [] if x.get("value") is not None and x.get("date")}

    def num(v):
        return float(v) if v is not None else None

    name = next((g.get("dam_name") for g in d.get("graph_data") or [] if g.get("dam_name")), None)
    return {"name_th": name, "series": series, "upper": curve("upper_rule_curve"), "lower": curve("lower_rule_curve"),
            "normal": num(d.get("normal_bound")), "upper_bound": num(d.get("upper_bound")), "lower_bound": num(d.get("lower_bound"))}

