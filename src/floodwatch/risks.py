"""The "⚠️ จับตา" tab (owner 2026-10-03: "the list of potential risks according to the water level in next 24 or 48 hr
… link to the stations or areas … with the confidence"; D-077). Pure: the API passes the station rows, rain per
province and the track records (compute_records). A gauge is listed once, in its worst group; provinces are listed
for heavy rain (satellite removed 2026-10-04, D-084). Evidence for every threshold: research/2026-10-03_verify_*.py."""
from __future__ import annotations

import datetime as dt
import math

import numpy as np

from floodwatch import qc, regions

RAIN_MM = 35.1         # the top strip's heavy-rain threshold (SUMMARY_RAIN_MIN_MM, KI-265)
UP_RISE_CM = 30        # upstream rose this much in 24 h: 69 % led to a >= 10 cm rise downstream (24 % without), 2026-10-03
UP_LAG_H = (3, 48)     # learned travel times inside the tab's window
BANDS = (">50%", "25-50%")  # bank-chance bands whose record is >= 1 in 10 (61 % and 12 % came true, 2026-10-03)
ORDER = ("over_bank", "may_reach", "upstream", "fast_rise", "rain")


def _item(s: dict, **k) -> dict:
    return {"code": s["code"], "name_th": s.get("name_th") or s["code"], "province": s.get("province"),
            "region": s.get("region"), "freeboard_m": s.get("freeboard_m"), **k}


def _upstream_hit(s: dict, by: dict) -> dict | None:
    """The learned upstream gauge (fresh, travel time 3-48 h) with the biggest measured 24 h rise >= UP_RISE_CM."""
    best = None
    for u in s.get("upstream") or []:
        o = by.get(u.get("code"))
        lag = u.get("lag_h")
        if not o or o.get("stale") or lag is None or not (UP_LAG_H[0] <= lag <= UP_LAG_H[1]):
            continue
        rise = (o.get("observed24") or {}).get("change_cm")
        if rise is not None and rise >= UP_RISE_CM and (best is None or rise > best["rise_cm"]):
            best = {"code": o["code"], "name_th": o.get("name_th") or o["code"], "lag_h": lag, "rise_cm": rise}
    return best


def _group_of(s: dict, by: dict) -> tuple[str | None, dict]:
    st = s.get("status")
    b24, b48 = s.get("bank_chance24"), s.get("bank_chance48")
    if st == "critical":
        return "over_bank", {}
    if b24 in BANDS or b48 in BANDS:
        band, hours = (b24, 24) if b24 in BANDS else (b48, 48)
        return "may_reach", {"band": band, "hours": hours}
    up = _upstream_hit(s, by) if st in ("watch", "warning") else None
    if up:
        return "upstream", {"up": up}
    ch = s.get("change24") or {}
    if ch.get("level") == "strong_rise":
        return "fast_rise", {"rise_cm": round((ch.get("median") or 0) * 100)}
    return None, {}


def build(stations: list[dict], rain_by_prov: dict[str, float], records: dict | None) -> dict:
    by = {s["code"]: s for s in stations}
    groups: dict[str, list] = {k: [] for k in ORDER}
    stale = {k: 0 for k in ORDER}
    for s in stations:
        key, extra = _group_of(s, by)
        if key is None:
            continue
        if s.get("stale"):  # old data cannot say what happens next: counted, not listed
            stale[key] += 1
            continue
        groups[key].append(_item(s, trend=s.get("trend"), **extra))
    # over the bank: น้ำยังขึ้น first, then ทรงตัวหรือลดลง, then (if any) ไม่ทราบแนวโน้ม; provinces inside (owner 2026-10-04)
    subs = []
    for sub in ("rising", "flat_or_falling", "unknown"):
        mine = [i for i in groups["over_bank"] if ((i.get("trend") or {}).get("group") or "unknown") == sub]
        prov: dict[str, list] = {}
        for i in mine:
            prov.setdefault(i["province"] or "ไม่ทราบจังหวัด", []).append(i)
        if prov:
            subs.append({"sub": sub, "provinces": [
                {"province": p, "region": regions.region_of(p),
                 "gauges": sorted(v, key=lambda i: i["freeboard_m"] if i["freeboard_m"] is not None else 0)}
                for p, v in sorted(prov.items(), key=lambda x: (-len(x[1]), x[0]))]})
    groups["over_bank"] = subs
    # may reach the bank: น้ำยังขึ้น first (owner 2026-10-04: steady gauges inside the band read as "water is coming"),
    # then ทรงตัวหรือลดลง (near the bank, touching it by small ups and downs), then ไม่ทราบแนวโน้ม
    subs_order = ("rising", "flat_or_falling", "unknown")
    for i in groups["may_reach"]:
        i["sub"] = (i.get("trend") or {}).get("group") or "unknown"
    groups["may_reach"].sort(key=lambda i: (subs_order.index(i["sub"]), BANDS.index(i["band"]), i["hours"],
                                            i["freeboard_m"] if i["freeboard_m"] is not None else 9e9))
    groups["upstream"].sort(key=lambda i: -i["up"]["rise_cm"])
    groups["fast_rise"].sort(key=lambda i: -i["rise_cm"])
    groups["rain"] = [{"province": p, "region": regions.region_of(p), "mm24": round(mm, 1)}
                      for p, mm in sorted(rain_by_prov.items(), key=lambda x: -x[1]) if mm >= RAIN_MM]
    return {"groups": [{"key": k, "items": groups[k], "left_stale": stale[k]} for k in ORDER if groups[k]],
            "records": records or {}}


def _in(item: dict, region: str, prov: str) -> bool:
    """The tab's filter (app.js REGIONS + wIn): a region ("metro" holds Bangkok too) and an optional province."""
    r = item.get("region")
    ok = region in ("", "all") or r == region or (region == "metro" and r == "bkk")
    return ok and (not prov or item.get("province") == prov)


def only(out: dict, region: str = "all", prov: str = "") -> dict:
    """build()'s output narrowed to what the ⚠️ จับตา tab shows for a region and province (the AI summary reads this)."""
    groups = []
    for g in out.get("groups") or []:
        if g["key"] == "over_bank":
            items = [{**sub, "provinces": [p for p in sub["provinces"] if _in(p, region, prov)]} for sub in g["items"]]
            items = [sub for sub in items if sub["provinces"]]
        else:
            items = [i for i in g["items"] if _in(i, region, prov)]
        if items:
            groups.append({**g, "items": items})
    return {**out, "groups": groups}


# --- track records (D-077): how often each forecast-based group came true, from our own archive -------------------
MIN_N = 30          # fewer cases: no chip (one week and one flood behind the first records, 2026-10-03)
WINDOW_DAYS = 30


def chip_text(rec: dict | None) -> str | None:
    """"6 ใน 10": counts, like the ⓘ "ในอดีตเป็นแบบนี้ต่อ 7 ใน 10 ครั้ง" (owner 2026-10-03 kept it over a percent:
    counts read better and do not look more precise than one flood's data). The UI's recChip mirrors this."""
    if not rec or (rec.get("n") or 0) < MIN_N or rec.get("hit") is None:
        return None
    return "< 1 ใน 10" if rec["hit"] < 0.05 else f"{round(rec['hit'] * 10)} ใน 10"


def _rate(xs: list[bool]) -> dict:
    return {"n": len(xs), "hit": round(sum(xs) / len(xs), 3)} if xs else {"n": 0, "hit": None}


def bank_record(runs: list[dict], obs: dict, banks: dict, hours: int) -> dict:
    """Per band: archived runs of gauges below the bank at issue time -> any reading >= bank within `hours`
    (readings on at least a third of the hours, or the run is skipped)."""
    from floodwatch.forecast import bank_chance
    out: dict[str, list] = {}
    for r in runs:
        bank = banks.get(r["code"])
        if bank is None or r.get("now") is None or not r.get("path") or r["now"] >= bank:
            continue
        band = bank_chance(r["path"], bank, hours)
        if band not in BANDS:
            continue
        t0, t1 = r["issue_time"], r["issue_time"] + dt.timedelta(hours=hours)
        vals = [v for t, v in obs.get(r["code"], []) if t0 < t <= t1]
        if len(vals) < hours / 3:
            continue
        out.setdefault(band, []).append(max(vals) >= bank)
    return {b: _rate(v) for b, v in out.items()}


def rise_record(runs: list[dict], obs: dict) -> dict:
    """Runs whose 24 h median rise is >= 20 cm ("strong_rise") -> the reading 24 h later (± 30 min) is >= 10 cm up."""
    hits = []
    for r in runs:
        p = [x for x in (r.get("path") or []) if x.get("h") == 24 and x.get("q")]
        if not p or r.get("now") is None or p[0]["q"][2] - r["now"] < 0.20:
            continue
        t = r["issue_time"] + dt.timedelta(hours=24)
        v = [lv for ti, lv in obs.get(r["code"], []) if abs((ti - t).total_seconds()) <= 1800]
        if v:
            hits.append(v[0] - r["now"] >= 0.10)
    return _rate(hits)


def upstream_record(pairs: list[tuple[str, str, int]], series: dict, step: int = 6) -> dict:
    """pairs = (gauge, upstream gauge, travel time h); series = hourly arrays on one grid. Signal: the upstream's
    fitted 24 h change (qc.observed24, the same number the live rule reads) >= UP_RISE_CM; came true: the gauge rose
    >= 10 cm within travel time + 6 h."""
    hits = []
    for gcode, ucode, lag in pairs:
        y, x = series.get(gcode), series.get(ucode)
        if y is None or x is None:
            continue
        for i in range(24, len(x) - lag - 6, step):
            if not np.isfinite(y[i]):
                continue
            w = [(k * 3600.0, float(x[k])) for k in range(i - 24, i + 1) if np.isfinite(x[k])]
            o = qc.observed24(w) if len(w) >= 12 else None
            if not o or o["change_cm"] < UP_RISE_CM:
                continue
            fut = y[i + 1:i + lag + 7]
            if np.isfinite(fut).any():
                hits.append(float(np.nanmax(fut)) - float(y[i]) >= 0.10)
    return _rate(hits)


# One run per gauge per 6 h; the database reduces each path to the numbers the records need (whole paths for 30 days
# did not fit the forecaster's 1 GB: killed, 2026-10-03).
def _pace(ser: dict, t0, hours: int):
    import datetime as _dt
    pts = [(-k, ser[t0 - _dt.timedelta(hours=k)]) for k in range(hours + 1) if (t0 - _dt.timedelta(hours=k)) in ser]
    if len(pts) < max(4, hours * 0.6):
        return None
    x = np.array([p[0] for p in pts], float)
    return float(np.polyfit(x, np.array([p[1] for p in pts], float), 1)[0])  # m/h


def lean_record(runs: list[dict], hourly: dict) -> dict:
    """How often a "? ไม่แน่ชัด" row leaned by the measured pace (status.lean: the smaller of the 24 h and 6 h pace, none
    when they disagree, at least 2 cm a day) went that way h hours later (strict sign). runs: {code, issue_time, now,
    path: [{h, q, method}]}; hourly: {code: {hour: level}}."""
    acc: dict = {}
    for r in runs:
        ser, t0 = hourly.get(r["code"]) or {}, r["issue_time"].replace(minute=0, second=0, microsecond=0)
        if r.get("now") is None:
            continue
        r24, r6 = _pace(ser, t0, 24), _pace(ser, t0, 6)
        if r24 is None or r6 is None or r24 == 0 or r6 == 0 or (r24 > 0) != (r6 > 0):
            continue
        rate = math.copysign(min(abs(r24), abs(r6)), r24)
        if abs(rate * 24) < 0.02:
            continue
        for p in r.get("path") or []:
            if not p or not p.get("q") or p.get("h") not in (24, 48, 72):
                continue
            q = p["q"]; lo, med, hi = q[1] - r["now"], q[2] - r["now"], q[3] - r["now"]
            half = (hi - lo) / 2
            d = "steady" if abs(med) <= max(0.02, half) else ("up" if med > 0 else "down")
            proven = d != "steady" and p.get("method") not in (None, "persistence") and ((lo > 0) if d == "up" else (hi < 0))
            if proven or max(abs(lo), abs(hi)) <= 0.05:
                continue  # the row was not "? ไม่แน่ชัด"
            if (med < 0.03) if rate > 0 else (med > -0.03):
                continue  # the model median (the chart's line) does not go the measured way: no lean (status.lean)
            y = ser.get(t0 + dt.timedelta(hours=p["h"]))
            if y is None:
                continue
            acc.setdefault(str(p["h"]), []).append((y - r["now"] > 0) if rate > 0 else (y - r["now"] < 0))
    return {h: _rate(v) for h, v in acc.items()}


RUNS_SQL = """
WITH pick AS (
  SELECT DISTINCT ON (code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6) id
  FROM forecast_run WHERE issue_time > %(since)s AND issue_time < now() - interval '24 hours'
  ORDER BY code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6, issue_time)
SELECT f.code, f.issue_time, (f.payload->>'level_now')::float AS now, x.*
FROM forecast_run f JOIN pick USING (id), LATERAL (
  SELECT max((e->'q'->>2)::float) FILTER (WHERE (e->>'h')::int <= 24) AS a2,
         max((e->'q'->>3)::float) FILTER (WHERE (e->>'h')::int <= 24) AS a3,
         max((e->'q'->>4)::float) FILTER (WHERE (e->>'h')::int <= 24) AS a4,
         max((e->'q'->>2)::float) FILTER (WHERE (e->>'h')::int <= 48) AS b2,
         max((e->'q'->>3)::float) FILTER (WHERE (e->>'h')::int <= 48) AS b3,
         max((e->'q'->>4)::float) FILTER (WHERE (e->>'h')::int <= 48) AS b4,
         max((e->'q'->>2)::float) FILTER (WHERE (e->>'h')::int = 24) AS m24
  FROM jsonb_array_elements(f.payload->'path') e) x"""
LEAN_SQL = """SELECT f.code, f.issue_time, (f.payload->>'level_now')::float AS now,
    f.payload->'path'->23 AS p24, f.payload->'path'->47 AS p48, f.payload->'path'->71 AS p72
  FROM forecast_run f JOIN (SELECT DISTINCT ON (code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6) id
    FROM forecast_run WHERE issue_time > %(since)s AND issue_time < now() - interval '24 hours'
    ORDER BY code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6, issue_time) pick USING (id)"""

HOURLY_SQL = """SELECT code, date_trunc('hour', obs_time) AS t, max(level_msl) AS hi, avg(level_msl) AS mean
    FROM observation WHERE obs_time > %(since)s AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1, 2"""


def compute_records(c) -> dict:
    """Daily in the forecaster: each group's record over the last WINDOW_DAYS (forecast archive since 2026-09-26),
    one run per gauge per 6 h as research/2026-10-03_verify_*.py, readings as hourly max (bank) or mean (rises).
    Stored in collector_state 'risk_record'."""
    from floodwatch import db
    now = dt.datetime.now(dt.timezone.utc)
    since = now - dt.timedelta(days=WINDOW_DAYS)
    banks = {r["code"]: r["bank_msl"] for r in c.execute("SELECT code, bank_msl FROM station WHERE bank_msl IS NOT NULL")}
    runs = c.execute(RUNS_SQL, {"since": since}).fetchall()
    hi: dict[str, list] = {}
    mean: dict[str, list] = {}
    for r in c.execute(HOURLY_SQL, {"since": since}):
        hi.setdefault(r["code"], []).append((r["t"], r["hi"]))
        mean.setdefault(r["code"], []).append((r["t"], r["mean"]))
    q = lambda h, a, b, d: [{"h": h, "q": [None, None, a, b, d]}] if None not in (a, b, d) else []
    r24 = [{"code": r["code"], "issue_time": r["issue_time"], "now": r["now"], "path": q(24, r["a2"], r["a3"], r["a4"])} for r in runs]
    old = now - dt.timedelta(hours=48)
    r48 = [{"code": r["code"], "issue_time": r["issue_time"], "now": r["now"], "path": q(48, r["b2"], r["b3"], r["b4"])}
           for r in runs if r["issue_time"] < old]
    rise = [{"code": r["code"], "issue_time": r["issue_time"], "now": r["now"],
             "path": [{"h": 24, "q": [0, 0, r["m24"], 0, 0]}] if r["m24"] is not None else []} for r in runs]
    learned = db.get_state(c, "upstream_learned") or {}
    pairs = [(gc, u[0], int(u[1])) for gc, v in learned.items() for u in v
             if u[1] is not None and UP_LAG_H[0] <= int(u[1]) <= UP_LAG_H[1]]
    n_h = int((now - since).total_seconds() // 3600) + 1
    series = {}
    for code in {p for pr in pairs for p in pr[:2]}:
        a = np.full(n_h, np.nan)
        for t, v in mean.get(code, []):
            k = int((t - since).total_seconds() // 3600)
            if 0 <= k < n_h:
                a[k] = v
        series[code] = a
    by_hour = {code: dict(v) for code, v in mean.items()}
    lean_runs = [{"code": r["code"], "issue_time": r["issue_time"], "now": r["now"], "path": [r["p24"], r["p48"], r["p72"]]}
                 for r in c.execute(LEAN_SQL, {"since": since}).fetchall()]
    rec = {"lean": lean_record(lean_runs, by_hour),
           "bank_24": bank_record(r24, hi, banks, 24), "bank_48": bank_record(r48, hi, banks, 48),
           "upstream": upstream_record(pairs, series), "fast_rise": rise_record(rise, mean),
           "window_days": WINDOW_DAYS, "computed_at": now.isoformat()}
    db.set_state(c, "risk_record", rec)
    return rec
