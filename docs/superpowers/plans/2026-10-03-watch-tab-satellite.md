# จับตา tab, satellite sheet line + map toggle, every gauge on the map — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a fourth tab "⚠️ จับตา" listing the next 24–48 h risks with measured track records, satellite flooding in the station sheet and as a map layer, and a map that shows every gauge with data.

**Architecture:** pure functions (`floodwatch/risks.py`, `point.py` satellite aggregates) fed by the existing station rows, rain points and `sat_flood`; a daily forecaster task stores track records in `collector_state`; two new read-only endpoints (`/api/risks`, `/api/satellite`); vanilla-JS rendering in `web/app.js`.

**Tech Stack:** Python 3.12, FastAPI, psycopg 3, PostgreSQL, numpy; Leaflet 1.9.4 (canvas); pytest via `t.sh` (docker compose, source mounted).

**Spec:** `docs/superpowers/specs/2026-10-03-watch-tab-satellite-design.md`

## Global Constraints

- Tab name `⚠️ จับตา`; never "เฝ้าระวัง" (yellow status) or "เตือนภัย" as its name.
- Track-record chip text `N ใน 10` (`< 1 ใน 10` below 0.05); hidden when n < 30; one function formats it.
- A gauge appears once in groups 1–4 (order 1 → 4); stale gauges are left out of 1–4.
- Group 2 bands: `>50%` and `25-50%` only. Group 3: status watch/warning, upstream lag 3–48 h, upstream `observed24.change_cm` ≥ 30, upstream not stale. Group 4: `change24.level == "strong_rise"`. Group 5: ≥ 35.1 mm/24 h. Satellite sheet line: ≥ 100 rai within 5 km.
- Every UI line fits one line at 390 px; details behind ⓘ (`title` + toast). Ranges, never countdowns (D-005).
- No interpolated water surfaces (D-019): the satellite layer draws observed cells merged into a grid.
- No secrets in git; bump `?v=` on `app.js`/`style.css`; version v0.21.0 (D-025).
- Tests: `bash $SCRATCH/t.sh` (= `docker compose run --rm --no-deps … worker pytest -q`); suite must stay green.

## Review Focus

1. A gauge that is critical **and** strong_rise must appear only in group 1 (dedupe) — tested in Task 2.
2. `/api/risks` with an empty `sat_flood` / no records / no rain must still answer (groups omitted, no chip) — Task 2 and Task 5.
3. Upstream gauge stale or with `observed24 = None` must not trigger group 3 — Task 2.
4. Satellite grid at country zoom must stay ≤ 5,000 items (coarsen) — Task 4.
5. Map: a critical gauge without a forecast must be drawn (ring) — Task 6 wording/JS test + live C16.

---

### Task 1: 48 h bank chance in the forecast payload and the station rows

**Files:** Modify `src/floodwatch/forecast/__init__.py` (outlook24 → uses new `bank_chance`; payload adds `outlook48`), `src/floodwatch/api/__init__.py` (STATIONS_SQL + `_station_row`); Test `tests/test_forecast.py`, `tests/test_api.py`.

**Interfaces:** Produces `forecast.bank_chance(path, bank, hours) -> str | None` (`">50%" | "25-50%" | "5-25%" | "<5%"`); station rows gain `bank_chance24`, `bank_chance48` (None for status unknown or no bank).

- [ ] **Step 1: failing tests**

```python
# tests/test_forecast.py
def test_bank_chance_bands_over_a_window():
    from floodwatch.forecast import bank_chance
    path = [{"h": h, "q": [1.0, 1.1, 1.2, 1.3, 1.4 + (0.5 if h == 40 else 0)], "method": "star"} for h in range(1, 49)]
    assert bank_chance(path, 1.25, 24) == "25-50%"
    assert bank_chance(path, 1.85, 24) == "<5%" and bank_chance(path, 1.85, 48) == "5-25%"
    assert bank_chance(path, 1.15, 48) == ">50%" and bank_chance(path, None, 24) is None
```

```python
# tests/test_api.py
def test_station_row_carries_bank_chances():
    from floodwatch.api import _station_row
    r = _row(level_msl=1.0, bank_msl=2.0, outlook24={"bank_chance": "25-50%"}, outlook48={"bank_chance": ">50%"})
    out = _station_row(r)
    assert out["bank_chance24"] == "25-50%" and out["bank_chance48"] == ">50%"
```
(`_row` = the existing test helper in `tests/test_api.py` that builds a STATIONS_SQL row; extend it with `outlook48=None` default if missing.)

- [ ] **Step 2:** run `bash $SCRATCH/t.sh tests/test_forecast.py tests/test_api.py -k bank_chance` → FAIL (ImportError / KeyError).
- [ ] **Step 3: implement**

```python
# forecast/__init__.py, above outlook24
def bank_chance(path: list[dict], bank: float | None, hours: int) -> str | None:
    """Coarse chance that the level reaches the bank within `hours` (max over horizons of the 50/75/95 % quantiles).
    It ranks gauges well but is ~3x too high in the middle bands (2026-10-03, research/2026-10-03_verify_bank.py),
    so the UI shows the measured track record (risk_record), never this band as a percent."""
    qs = [p for p in path[:hours] if p.get("q")]
    if bank is None or not qs:
        return None
    top = lambda k: max(p["q"][k] for p in qs)
    return ">50%" if top(2) >= bank else "25-50%" if top(3) >= bank else "5-25%" if top(4) >= bank else "<5%"
```
In `outlook24`: `out["bank_chance"] = bank_chance(path, bank, 24)` when bank is not None (same values as before). Payload (line ~392): add `"outlook48": {"bank_chance": bank_chance(path, bank, 48)}`.
STATIONS_SQL: add `f.payload->'outlook48' AS outlook48,`. `_station_row` return dict: 
```python
        "bank_chance24": None if status == "unknown" else (r.get("outlook24") or {}).get("bank_chance"),
        "bank_chance48": None if status == "unknown" else (r.get("outlook48") or {}).get("bank_chance"),
```
- [ ] **Step 4:** run the two tests → PASS; full suite green.
- [ ] **Step 5:** commit `feat: 48 h bank chance in the forecast payload and station rows`.

### Task 2: `risks.build` — the six groups

**Files:** Create `src/floodwatch/risks.py`; Test `tests/test_risks.py`.

**Interfaces:** Produces
`build(stations: list[dict], rain_by_prov: dict[str, float], sat: dict | None, records: dict | None) -> dict` returning `{"groups": [{"key", "items": [...], "left_stale": int}], "records": records or {}, "sat_dates": [from, to] | None}`. Group keys in order: `over_bank, may_reach, upstream, fast_rise, rain, satellite`. Gauge items: `{"code","name_th","province","region","freeboard_m", ...}` plus `band`+`hours` (may_reach), `up: {"code","name_th","lag_h","rise_cm"}` (upstream), `rise_cm` (fast_rise). Area items: `{"province","region","mm24"}` / `{"province","region","rai"}`. Empty groups are omitted.

- [ ] **Step 1: failing tests** (`tests/test_risks.py`)

```python
from floodwatch import risks

def g(code, status="normal", **k):
    base = {"code": code, "name_th": code, "province": "ชัยนาท", "region": "up", "status": status, "stale": False,
            "freeboard_m": 0.5, "bank_chance24": "<5%", "bank_chance48": "<5%", "change24": None, "upstream": None,
            "observed24": None}
    return {**base, **k}

def keys(out):
    return {grp["key"]: [i.get("code") or i.get("province") for i in grp["items"]] for grp in out["groups"]}

def test_a_gauge_appears_once_in_its_worst_group():
    st = [g("A", "critical", freeboard_m=-0.2, change24={"level": "strong_rise"}),
          g("B", "warning", bank_chance24=">50%", change24={"level": "strong_rise"}),
          g("C", change24={"level": "strong_rise"})]
    assert keys(risks.build(st, {}, None, None)) == {"over_bank": ["ชัยนาท"], "may_reach": ["B"], "fast_rise": ["C"]}

def test_over_bank_is_grouped_by_province_with_its_gauges():
    st = [g("A", "critical"), g("B", "critical"), g("C", "critical", province="สิงห์บุรี")]
    grp = risks.build(st, {}, None, None)["groups"][0]
    assert grp["key"] == "over_bank" and [(i["province"], len(i["gauges"])) for i in grp["items"]] == [("ชัยนาท", 2), ("สิงห์บุรี", 1)]

def test_may_reach_uses_only_the_two_upper_bands_and_says_which_window():
    st = [g("A", bank_chance24="25-50%"), g("B", bank_chance24="<5%", bank_chance48=">50%"), g("C", bank_chance24="5-25%")]
    items = risks.build(st, {}, None, None)["groups"][0]["items"]
    assert [(i["code"], i["band"], i["hours"]) for i in items] == [("A", "25-50%", 24), ("B", ">50%", 48)]

def test_upstream_needs_a_fresh_strong_rise_upstream_and_a_gauge_at_watch_or_warning():
    up = g("U", observed24={"change_cm": 45, "level": "strong_rise"})
    st = [up, g("W", "watch", upstream=[{"code": "U", "lag_h": 20}]),
          g("N", "normal", upstream=[{"code": "U", "lag_h": 20}]),          # normal: not listed
          g("L", "warning", upstream=[{"code": "U", "lag_h": 60}]),         # lag too long
          g("S", "watch", upstream=[{"code": "V", "lag_h": 10}]), g("V", stale=True, observed24={"change_cm": 80})]
    items = [grp for grp in risks.build(st, {}, None, None)["groups"] if grp["key"] == "upstream"][0]["items"]
    assert [(i["code"], i["up"]["code"], i["up"]["lag_h"], i["up"]["rise_cm"]) for i in items] == [("W", "U", 20, 45)]

def test_stale_gauges_are_counted_not_listed():
    out = risks.build([g("A", "critical", stale=True), g("B", "critical")], {}, None, None)
    assert out["groups"][0]["left_stale"] == 1 and len(out["groups"][0]["items"][0]["gauges"]) == 1

def test_area_groups_rain_and_satellite_sorted_by_amount():
    sat = {"province": {"นครสวรรค์": 483000, "พิจิตร": 196000}, "img_from": "2026-09-28", "img_to": "2026-10-02"}
    out = risks.build([], {"เชียงใหม่": 20.0, "น่าน": 52.4, "ตาก": 36.0}, sat, None)
    assert keys(out) == {"rain": ["น่าน", "ตาก"], "satellite": ["นครสวรรค์", "พิจิตร"]}
    assert out["sat_dates"] == ["2026-09-28", "2026-10-02"]

def test_nothing_to_report_gives_no_groups():
    assert risks.build([g("A")], {}, None, None)["groups"] == []
```

- [ ] **Step 2:** run `bash $SCRATCH/t.sh tests/test_risks.py` → FAIL (no module).
- [ ] **Step 3: implement** `src/floodwatch/risks.py`

```python
"""The "⚠️ จับตา" tab (owner 2026-10-03: "the list of potential risks according to the water level in next 24 or
48 hr … link to the stations or areas … with the confidence"; D-077). Pure: the API passes the station rows, rain
per province, the satellite summary and the track records (risk_record). A gauge is listed once, in its worst group."""
from __future__ import annotations

from floodwatch import regions

RAIN_MM = 35.1         # the top strip's heavy-rain threshold (SUMMARY_RAIN_MIN_MM, KI-265)
UP_RISE_CM = 30        # upstream rose this much in 24 h (69 % led to a >= 10 cm rise downstream, 2026-10-03)
UP_LAG_H = (3, 48)
BANDS = (">50%", "25-50%")  # the bands whose record is >= 1 in 10 (61 % / 12 %, 2026-10-03)
ORDER = ("over_bank", "may_reach", "upstream", "fast_rise", "rain", "satellite")


def _item(s: dict, **k) -> dict:
    return {"code": s["code"], "name_th": s.get("name_th") or s["code"], "province": s.get("province"),
            "region": s.get("region"), "freeboard_m": s.get("freeboard_m"), **k}


def _upstream_hit(s: dict, by: dict) -> dict | None:
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


def build(stations: list[dict], rain_by_prov: dict[str, float], sat: dict | None, records: dict | None) -> dict:
    by = {s["code"]: s for s in stations}
    groups = {k: [] for k in ORDER}
    stale = {k: 0 for k in ORDER}
    for s in stations:
        st = s.get("status")
        ch = (s.get("change24") or {}).get("level")
        b24, b48 = s.get("bank_chance24"), s.get("bank_chance48")
        up = _upstream_hit(s, by) if st in ("watch", "warning") else None
        key = ("over_bank" if st == "critical" else
               "may_reach" if (b24 in BANDS or b48 in BANDS) else
               "upstream" if up else
               "fast_rise" if ch == "strong_rise" else None)
        if key is None:
            continue
        if s.get("stale"):
            stale[key] += 1
            continue
        if key == "may_reach":
            band, hours = (b24, 24) if b24 in BANDS else (b48, 48)
            groups[key].append(_item(s, band=band, hours=hours))
        elif key == "upstream":
            groups[key].append(_item(s, up=up))
        elif key == "fast_rise":
            groups[key].append(_item(s, rise_cm=round((s.get("change24") or {}).get("median", 0) * 100)))
        else:
            groups[key].append(_item(s))
    # 1: per province, most gauges first
    prov: dict[str, list] = {}
    for i in groups["over_bank"]:
        prov.setdefault(i["province"] or "ไม่ทราบจังหวัด", []).append(i)
    groups["over_bank"] = [{"province": p, "region": regions.region_of(p), "gauges": sorted(v, key=lambda i: i["freeboard_m"] or 0)}
                           for p, v in sorted(prov.items(), key=lambda x: (-len(x[1]), x[0]))]
    groups["may_reach"].sort(key=lambda i: (BANDS.index(i["band"]), i["hours"], i["freeboard_m"] if i["freeboard_m"] is not None else 9e9))
    groups["upstream"].sort(key=lambda i: -i["up"]["rise_cm"])
    groups["fast_rise"].sort(key=lambda i: -i["rise_cm"])
    groups["rain"] = [{"province": p, "region": regions.region_of(p), "mm24": round(mm, 1)}
                      for p, mm in sorted(rain_by_prov.items(), key=lambda x: -x[1]) if mm >= RAIN_MM]
    sp = (sat or {}).get("province") or {}
    groups["satellite"] = [{"province": p, "region": regions.region_of(p), "rai": int(r)}
                           for p, r in sorted(sp.items(), key=lambda x: -x[1]) if r > 0]
    return {"groups": [{"key": k, "items": groups[k], "left_stale": stale[k]} for k in ORDER if groups[k]],
            "records": records or {},
            "sat_dates": [sat["img_from"], sat["img_to"]] if sat and sat.get("img_from") else None}
```
- [ ] **Step 4:** run → PASS; suite green.
- [ ] **Step 5:** commit `feat: risks.build — the six จับตา groups, one place per gauge`.

### Task 3: track records (`risk_record`)

**Files:** Modify `src/floodwatch/risks.py` (pure record functions + `compute_records(c)`), `src/floodwatch/worker.py` (task); Test `tests/test_risks.py`, `tests/test_worker.py`.

**Interfaces:** Produces `risks.bank_record(runs, obs, banks, hours) -> {band: {"n","hit"}}`, `risks.upstream_record(pairs, series) -> {"n","hit"}`, `risks.rise_record(runs, obs) -> {"n","hit"}`, `risks.compute_records(c) -> dict` (stores `collector_state.risk_record`). Worker: `("risk_record", 24 * 3600)` in FORECASTER_TASKS and FIRST_RUN["forecaster"] after "forecast".

- [ ] **Step 1: failing tests**

```python
import datetime as dt
T0 = dt.datetime(2026, 9, 26, tzinfo=dt.timezone.utc)
H = dt.timedelta(hours=1)

def test_bank_record_counts_runs_below_bank_that_reached_it():
    path = [{"h": h, "q": [0.0, 0.0, 2.0, 2.0, 2.0]} for h in range(1, 49)]   # median over bank -> ">50%"
    runs = [{"code": "A", "issue_time": T0, "path": path, "now": 1.0}, {"code": "B", "issue_time": T0, "path": path, "now": 1.0},
            {"code": "C", "issue_time": T0, "path": path, "now": 2.5}]          # C already over bank: not counted
    obs = {"A": [(T0 + k * H, 1.0 + (1.0 if k == 10 else 0)) for k in range(1, 25)],
           "B": [(T0 + k * H, 1.0) for k in range(1, 25)], "C": [(T0 + k * H, 2.5) for k in range(1, 25)]}
    rec = risks.bank_record(runs, obs, {"A": 1.5, "B": 1.5, "C": 1.5}, 24)
    assert rec == {">50%": {"n": 2, "hit": 0.5}}

def test_rise_record_checks_the_reading_24_h_later():
    path = [{"h": 24, "q": [0, 0, 1.3, 0, 0]}]
    runs = [{"code": "A", "issue_time": T0, "path": path, "now": 1.0}, {"code": "B", "issue_time": T0, "path": path, "now": 1.0}]
    obs = {"A": [(T0 + 24 * H, 1.15)], "B": [(T0 + 24 * H, 1.02)]}
    assert risks.rise_record(runs, obs) == {"n": 2, "hit": 0.5}

def test_upstream_record_uses_the_fitted_24_h_change_like_the_live_rule():
    import numpy as np
    up = np.concatenate([np.full(30, 1.0), np.linspace(1.0, 1.5, 25), np.full(40, 1.5)])   # +50 cm over 24 h
    down = np.concatenate([np.full(60, 2.0), np.full(35, 2.3)])                              # +30 cm a few hours later
    rec = risks.upstream_record([("D", "U", 6)], {"U": up, "D": down}, step=1)
    assert rec["n"] >= 1 and rec["hit"] > 0.5

def test_chip_text_rounds_to_tenths():
    assert risks.chip_text({"n": 132, "hit": 0.614}) == "6 ใน 10"
    assert risks.chip_text({"n": 345, "hit": 0.035}) == "< 1 ใน 10"
    assert risks.chip_text({"n": 12, "hit": 0.9}) is None
```

```python
# tests/test_worker.py
def test_risk_record_runs_daily_in_the_forecaster_after_the_forecast():
    from floodwatch import worker
    assert ("risk_record", 24 * 3600) in worker.FORECASTER_TASKS
    f = worker.FIRST_RUN["forecaster"]
    assert f.index("risk_record") > f.index("forecast")
```
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: implement** in `risks.py`:

```python
import datetime as dt
import numpy as np
from floodwatch import qc

MIN_N = 30
WINDOW_DAYS = 30


def chip_text(rec: dict | None) -> str | None:
    """"6 ใน 10": counts, like the existing "ในอดีตเป็นแบบนี้ต่อ 7 ใน 10 ครั้ง" (owner 2026-10-03 kept it over percent)."""
    if not rec or (rec.get("n") or 0) < MIN_N or rec.get("hit") is None:
        return None
    return "< 1 ใน 10" if rec["hit"] < 0.05 else f"{round(rec['hit'] * 10)} ใน 10"


def _rate(xs: list[bool]) -> dict:
    return {"n": len(xs), "hit": round(sum(xs) / len(xs), 3)} if xs else {"n": 0, "hit": None}


def bank_record(runs, obs, banks, hours: int) -> dict:
    from floodwatch.forecast import bank_chance
    out: dict = {}
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


def rise_record(runs, obs) -> dict:
    hits = []
    for r in runs:
        p = [x for x in (r.get("path") or []) if x.get("h") == 24 and x.get("q")]
        if not p or r.get("now") is None or p[0]["q"][2] - r["now"] < 0.20:
            continue
        t = r["issue_time"] + dt.timedelta(hours=24)
        v = [l for ti, l in obs.get(r["code"], []) if abs((ti - t).total_seconds()) <= 1800]
        if v:
            hits.append(v[0] - r["now"] >= 0.10)
    return _rate(hits)


def upstream_record(pairs, series: dict, step: int = 6) -> dict:
    """pairs = (gauge, upstream, lag_h); series = hourly arrays on one grid. Signal: the upstream's fitted 24 h change
    (qc.observed24, as the live rule) >= UP_RISE_CM; hit: the gauge rises >= 10 cm within lag + 6 h."""
    hits = []
    for g, u, lag in pairs:
        y, x = series.get(g), series.get(u)
        if y is None or x is None:
            continue
        for i in range(24, len(x) - lag - 6, step):
            w = [(k * 3600.0, float(x[k])) for k in range(i - 24, i + 1) if np.isfinite(x[k])]
            o = qc.observed24(w) if len(w) >= 12 else None
            if not o or o["change_cm"] < UP_RISE_CM or not np.isfinite(y[i]):
                continue
            fut = y[i + 1:i + lag + 7]
            if np.isfinite(fut).any():
                hits.append(float(np.nanmax(fut)) - float(y[i]) >= 0.10)
    return _rate(hits)


def compute_records(c) -> dict:
    """Daily (forecaster): the record of each forecast-based group over the last WINDOW_DAYS (forecast archive since
    2026-09-26). One run per gauge per 6 h, as research/2026-10-03_verify_*.py."""
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=WINDOW_DAYS)
    banks = {r["code"]: r["bank_msl"] for r in c.execute("SELECT code, bank_msl FROM station WHERE bank_msl IS NOT NULL")}
    runs = c.execute("""SELECT DISTINCT ON (code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6)
            code, issue_time, payload->'path' AS path, (payload->>'level_now')::float AS now FROM forecast_run
            WHERE issue_time > %s AND issue_time < now() - interval '24 hours'
            ORDER BY code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6, issue_time""", (since,)).fetchall()
    obs: dict = {}
    for r in c.execute("""SELECT code, obs_time, level_msl FROM observation WHERE obs_time > %s AND level_msl IS NOT NULL
                          AND quality_flag='ok'""", (since,)):
        obs.setdefault(r["code"], []).append((r["obs_time"], r["level_msl"]))
    old48 = [r for r in runs if r["issue_time"] < dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=48)]
    from floodwatch.api import upstream_map, _chainage
    learned = (c.execute("SELECT value FROM collector_state WHERE key='upstream_learned'").fetchone() or {}).get("value") or {}
    ups = upstream_map(learned, _chainage())
    pairs = [(g, u["code"], u["lag_h"]) for g, v in ups.items() for u in v if u.get("lag_h") and UP_LAG_H[0] <= u["lag_h"] <= UP_LAG_H[1]]
    n_h = int((dt.datetime.now(dt.timezone.utc) - since).total_seconds() // 3600) + 1
    series: dict = {}
    for code, xs in obs.items():
        a = np.full(n_h, np.nan)
        for t, v in xs:
            k = int((t - since).total_seconds() // 3600)
            if 0 <= k < n_h:
                a[k] = v
        series[code] = a
    rec = {"bank_24": bank_record(runs, obs, banks, 24), "bank_48": bank_record(old48, obs, banks, 48),
           "upstream": upstream_record(pairs, series), "fast_rise": rise_record(runs, obs),
           "window_days": WINDOW_DAYS, "computed_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    from floodwatch import db
    db.set_state(c, "risk_record", rec)
    return rec
```
(The rain record is deferred: `rain_obs` holds only days of history; the chip stays hidden — spec allows. Ruling recorded in the ledger.)
Worker: add `("risk_record", 24 * 3600)` to FORECASTER_TASKS; FIRST_RUN forecaster `("upstream_learn", "forecast", "risk_record", "gistda_flood")`; `run_task` branch:
```python
    elif name == "risk_record":
        try:
            from floodwatch import risks
            with db.connect() as c:
                risks.compute_records(c)
            db.record_health("risk_record", True)
        except Exception as e:
            log.exception("risk_record failed")
            db.record_health("risk_record", False, error=str(e))
```
- [ ] **Step 4:** run → PASS; suite green (update any test pinning FIRST_RUN exactly).
- [ ] **Step 5:** commit `feat: daily track records for the จับตา groups (risk_record)`.

### Task 4: satellite aggregates, `/api/satellite`, `sat_near_rai`

**Files:** Modify `src/floodwatch/point.py`, `src/floodwatch/collectors/__init__.py` (after the `sat_flood` replace), `src/floodwatch/api/__init__.py`; Test `tests/test_point.py`, `tests/test_api.py`.

**Interfaces:** Produces `point.sat_summary(cells, gauges, km=5.0) -> {"near": {code: rai}, "province": {prov: rai}, "img_from", "img_to"}` (near only ≥ 100 rai), `point.sat_grid(cells, g) -> [[lat, lon, rai]]` (cell centres of a g-degree grid), `api.sat_grid_size(z) -> float`; collector_state `sat_summary`; `/api/satellite?bbox=w,s,e,n&z=` → `{"g", "cells": [[lat, lon, rai]], "img_from", "img_to"}`; station rows gain `sat_near_rai`.

- [ ] **Step 1: failing tests**

```python
# tests/test_point.py
def test_sat_summary_near_gauges_and_per_province():
    cells = [{"lat": 15.70, "lon": 100.10, "area_m2": 160000.0, "province": "นครสวรรค์", "img_from": dt.date(2026, 9, 28), "img_to": dt.date(2026, 10, 2)}] * 2 \
          + [{"lat": 16.50, "lon": 100.30, "area_m2": 1600.0, "province": "พิจิตร", "img_from": dt.date(2026, 9, 28), "img_to": dt.date(2026, 10, 2)}]
    gauges = [{"code": "N", "lat": 15.72, "lon": 100.10}, {"code": "P", "lat": 16.50, "lon": 100.30}, {"code": "F", "lat": 14.0, "lon": 100.0}]
    out = point.sat_summary(cells, gauges)
    assert out["near"] == {"N": 200}                       # P has 1 rai: below 100, not listed; F nothing
    assert out["province"] == {"นครสวรรค์": 200, "พิจิตร": 1}
    assert (out["img_from"], out["img_to"]) == ("2026-09-28", "2026-10-02")

def test_sat_grid_merges_cells_into_squares():
    cells = [{"lat": 15.701, "lon": 100.101, "area_m2": 1600.0}, {"lat": 15.709, "lon": 100.109, "area_m2": 3200.0},
             {"lat": 15.75, "lon": 100.15, "area_m2": 1600.0}]
    out = point.sat_grid(cells, 0.02)
    assert sorted(out) == [[15.71, 100.11, 3], [15.75, 100.15, 1]]
```

```python
# tests/test_api.py
def test_sat_grid_size_coarsens_when_zoomed_out():
    from floodwatch.api import sat_grid_size
    assert sat_grid_size(6) == 0.02 and sat_grid_size(9) == 0.005 and sat_grid_size(12) == 0.002
```
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: implement**

```python
# point.py, after satellite_seen
SAT_NEAR_KM = 5.0
SAT_NEAR_MIN_RAI = 100  # below this the sheet line says nothing (spec §4)


def sat_summary(cells: list[dict], gauges: list[dict], km: float = SAT_NEAR_KM) -> dict:
    """Per gauge (rai seen flooded within `km`, only >= SAT_NEAR_MIN_RAI) and per province, at each GISTDA download
    (D-078). A 0.1° bucket index keeps 72k cells x 1k gauges to a few seconds."""
    grid: dict = {}
    prov: dict = {}
    dates = []
    for c in cells:
        grid.setdefault((round(c["lat"] * 10), round(c["lon"] * 10)), []).append(c)
        if c.get("province"):
            prov[c["province"]] = prov.get(c["province"], 0.0) + (c.get("area_m2") or 0)
        dates += [d for d in (c.get("img_from"), c.get("img_to")) if d is not None]
    near = {}
    for g in gauges:
        if g.get("lat") is None or g.get("lon") is None:
            continue
        bi, bj = round(g["lat"] * 10), round(g["lon"] * 10)
        a = sum(c.get("area_m2") or 0 for i in (-1, 0, 1) for j in (-1, 0, 1) for c in grid.get((bi + i, bj + j), [])
                if haversine_km(g["lat"], g["lon"], c["lat"], c["lon"]) <= km)
        if a / RAI_M2 >= SAT_NEAR_MIN_RAI:
            near[g["code"]] = int(round(a / RAI_M2))
    return {"near": near, "province": {p: int(round(a / RAI_M2)) for p, a in prov.items()},
            "img_from": min(dates).isoformat() if dates else None, "img_to": max(dates).isoformat() if dates else None}


def sat_grid(cells: list[dict], g: float) -> list[list]:
    """Observed cells merged into g-degree squares (centre lat, lon, rai): drawn as squares, never interpolated (D-019)."""
    acc: dict = {}
    for c in cells:
        k = (int(c["lat"] // g), int(c["lon"] // g))
        acc[k] = acc.get(k, 0.0) + (c.get("area_m2") or 0)
    return [[round((i + 0.5) * g, 4), round((j + 0.5) * g, 4), int(round(a / RAI_M2))] for (i, j), a in acc.items()]
```
Collector (`gistda_flood`, after the insert, same transaction):
```python
            gauges = cur.execute("SELECT code, lat, lon FROM station WHERE lat IS NOT NULL").fetchall()
            summ = point.sat_summary([dict(zip(("lat", "lon", "area_m2", "province", "img_from", "img_to"), (x[1], x[2], x[3], x[4], x[7], x[8]))) for x in rows], gauges)
            cur.execute("""INSERT INTO collector_state (key, value, updated_at) VALUES ('sat_summary', %s, now())
                           ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()""", (Jsonb(summ),))
```
(adapt the tuple indices to the actual `rows` tuples built for the INSERT; read them first.) Also a one-off: compute `sat_summary` from the current table at first forecaster start if the key is missing (`risks`-independent helper `collectors.sat_summary_refresh(c)` used by both).
API:
```python
def sat_grid_size(z: int) -> float:
    return 0.02 if z < 9 else 0.005 if z < 11 else 0.002


def _sat_summary() -> dict:
    def build():
        with db.connect() as c:
            return db.get_state(c, "sat_summary") or {}
    return _memo(("sat_summary",), build, ttl=600)


@app.get("/api/satellite")
def satellite(bbox: str = Query(..., pattern=r"^-?[\d.]+,-?[\d.]+,-?[\d.]+,-?[\d.]+$"), z: int = Query(8, ge=3, le=19)):
    w, s, e, n = map(float, bbox.split(","))
    g = sat_grid_size(z)
    with db.connect() as c:
        cells = c.execute("SELECT lat, lon, area_m2 FROM sat_flood WHERE lat BETWEEN %s AND %s AND lon BETWEEN %s AND %s",
                          (s, n, w, e)).fetchall()
    out = point.sat_grid(cells, g)
    while len(out) > 5000:  # country view: coarsen until the phone can draw it
        g *= 2
        out = point.sat_grid(cells, g)
    sm = _sat_summary()
    return _json({"g": g, "cells": out, "img_from": sm.get("img_from"), "img_to": sm.get("img_to"), "source": "GISTDA"})
```
`_stations_data`: after `street_counts`, `near = (_sat_summary().get("near") or {}); for s in items: s["sat_near_rai"] = near.get(s["code"])`. `/api/stations/{code}` station dict gets the same field.
- [ ] **Step 4:** run → PASS; suite green.
- [ ] **Step 5:** commit `feat: satellite per gauge and province at each GISTDA download; /api/satellite grid`.

### Task 5: `/api/risks`

**Files:** Modify `src/floodwatch/api/__init__.py`; Test `tests/test_api.py`.

**Interfaces:** Consumes `risks.build`, `_sat_summary`, `_rain_data`. Produces `point_provinces(rows) -> {point_id: set(province)}` and `rain_by_province(points, pp) -> {province: mm24}`; `/api/risks` → `risks.build(...)` + `"generated"`.

- [ ] **Step 1: failing test**

```python
def test_rain_by_province_takes_the_wettest_point_serving_each_province():
    from floodwatch.api import rain_by_province
    pts = [{"point": "c1", "mm24": 40.0}, {"point": "c2", "mm24": 12.0}, {"point": "f9", "mm24": None}]
    pp = {"c1": {"น่าน", "แพร่"}, "c2": {"น่าน"}}
    assert rain_by_province(pts, pp) == {"น่าน": 40.0, "แพร่": 40.0}
```
- [ ] **Step 2:** FAIL. **Step 3:** implement
```python
def point_provinces(rows: list[dict]) -> dict[str, set]:
    """Provinces of the gauges each 0.5° cell and fine point serves (as point_regions)."""
    out: dict[str, set] = {}
    for r in rows:
        if r.get("lat") is None or not r.get("province"):
            continue
        out.setdefault(rain_cells.cell_of(r["lat"], r["lon"])[0], set()).add(r["province"])
        for pid in rain_cells.fine_points([r]):
            out.setdefault(pid, set()).add(r["province"])
    return out


def rain_by_province(points: list[dict], pp: dict[str, set]) -> dict[str, float]:
    out: dict[str, float] = {}
    for p in points:
        if p.get("mm24") is None:
            continue
        for prov in pp.get(p["point"], ()):
            out[prov] = max(out.get(prov, 0.0), p["mm24"])
    return out


@app.get("/api/risks")
def risks_api():
    def build():
        st = stations("all")  # reuse the cached station payload
        items = json.loads(st.body)["stations"]
        rd = _memo(("rain",), _rain_data)
        pp = _memo(("point_provinces",), lambda: point_provinces(_station_rows(True)), ttl=3600)
        with db.connect() as c:
            rec = db.get_state(c, "risk_record") or {}
        out = risks.build(items, rain_by_province(rd["points"], pp), _sat_summary() or None, rec)
        return {**out, "generated": dt.datetime.now(dt.timezone.utc).isoformat()}
    return _json(_memo(("risks",), build, ttl=300))
```
(Check how `_json` responses expose the body; if `stations()` returns a Response, call `_stations_data("all")` through the same memo instead of parsing.)
- [ ] **Step 4:** PASS + suite. **Step 5:** commit `feat: /api/risks`.

### Task 6: web — tab, groups, chips, links; map rings; satellite toggle; sheet line; chip removal

**Files:** Modify `web/index.html`, `web/app.js`, `web/style.css`, `src/floodwatch/api/__init__.py` (cache busters if served there); Test `tests/test_wording.py`.

- [ ] **Step 1: failing wording tests** (`tests/test_wording.py`, reading `web/app.js` / `web/index.html` like the existing tests)

```python
def test_watch_tab_is_named_jabta_not_an_official_or_status_word():
    html = INDEX.read_text()
    assert 'data-tab="watch"' in html and "⚠️ จับตา" in html
    assert ">⚠️ เฝ้าระวัง<" not in html and "เตือนภัย</button>" not in html

def test_track_record_chip_is_counts_out_of_ten():
    js = APP.read_text()
    assert "ใน 10`" in js and "function recChip" in js and "%`" not in js.split("function recChip")[1][:400]

def test_map_has_no_forecast_checkbox_and_draws_rings():
    js = APP.read_text()
    assert "แสดงสถานีที่ยังคาดการณ์ไม่ได้" not in js and "เฉพาะที่คาดการณ์ได้" not in js
    assert "ยังไม่มีพยากรณ์" in js and "🛰 ดาวเทียม" in js

def test_satellite_sheet_line_says_seen_only():
    js = APP.read_text()
    assert "ดาวเทียมเห็นน้ำท่วมรอบสถานี" in js
```
- [ ] **Step 2:** FAIL. **Step 3: implement**
  - `index.html`: 4th tab `<button role="tab" data-tab="watch" aria-selected="false">⚠️ จับตา</button>`; `<div id="view-watch" class="view" hidden></div>` after `view-river`; bump `?v=`.
  - `app.js`:
    - `whereRow(r = region, p = prov, cls = "")` → select classes `pick-region${cls}` / `pick-prov${cls}`; change handler routes `.pick-region-w` / `.pick-prov-w` to `wRegion`/`wProv` (tab state, start `"all"`/`""` each time the tab opens) and re-renders the tab only.
    - `recChip(rec, tip)`: `rec && rec.n >= 30` → `<button type="button" class="conf-badge rec" title="${tip}">${rec.hit < 0.05 ? "< 1" : Math.round(rec.hit * 10)} ใน 10</button>`.
    - `renderWatch()`: fetch `/api/risks` (cache 5 min in a variable, refreshed by `load()`); filter items by `REGIONS[wRegion].test(item)` and `!wProv || item.province === wProv`; header `24–48 ชม. ข้างหน้า · อัปเดต HH:MM ⓘ`; groups with titles `🔴 ล้นตลิ่งแล้ว`, `🟠 อาจถึงตลิ่ง`, `🟠 น้ำเหนือกำลังมา`, `🟡 น้ำขึ้นเร็ว`, `🌧 ฝนหนักคาดการณ์`, `🛰 ดาวเทียมเห็นน้ำท่วม · ภาพ d–d`; rows as in spec §3; first 5 rows + `+ อีก N ›`; empty → `ไม่พบความเสี่ยงใน <area> ✓`. Clicks: `[data-code]` → `showDetail`; over_bank province row toggles its gauge list; rain row → `setTab("list")` + `setRegion(regionOf)` + `setProv(p)`; satellite row → `setTab("map")`, `satOn(true)`, fit to that province's gauges.
    - `setTab`: hide/show `view-watch`; render on open with `wRegion = "all"; wProv = ""`.
    - Map: remove the `nodata` control and `forecastOnly` chip; `onMap = (s) => s.status !== "unknown" || (s.age_min != null && s.age_min <= 1440)` → draw when data < 24 h; ring style when `!hasForecast(s)`: `fillOpacity: 0, weight: 3, color: st.color`; legend adds `○ ยังไม่มีพยากรณ์` and `ไม่แสดง N สถานีที่ไม่ส่งข้อมูลเกิน 24 ชม.`; top-left control `<label><input type="checkbox" id="sat"> 🛰 ดาวเทียม</label>`.
    - Satellite layer: pane `sat` (zIndex 300); on toggle / `moveend` while on: fetch `/api/satellite?bbox=…&z=…`, draw `L.rectangle` per cell (`[lat±g/2, lon±g/2]`, fill `#0277bd`, `fillOpacity = 0.15 + 0.6 * min(1, rai / (g*111.2)²*625/1e0 …)` — use share = rai·1600 / (g·111,200 m)² clipped to 1), non-interactive; legend line `▒ ดาวเทียมเห็นน้ำท่วม (ภาพ …)` while on.
    - Sheet: after `upstreamLine(s)` area, when `s.sat_near_rai`: `<p class="pf-obs">🛰 ดาวเทียมเห็นน้ำท่วมรอบสถานี (5 กม.) ราว ${n.toLocaleString("th-TH")} ไร่ · ภาพ ${dates} ${infoBtn(tip,…)}</p>`; tip: "ภาพเรดาร์ GISTDA รวม 7 วัน เห็นเฉพาะที่โล่ง ไม่เห็นใต้อาคารหรือต้นไม้ จึงไม่ได้แปลว่าที่อื่นไม่ท่วม".
  - `style.css`: `.wgrp`, `.wrow` (one line, ellipsis), `.rec` chip; bump `?v=`.
- [ ] **Step 4:** wording tests PASS; suite green; local render check with Playwright at 390 px (four tabs on one line).
- [ ] **Step 5:** commit `feat: จับตา tab, satellite map toggle and sheet line, every gauge with data on the map`.

### Task 7: live checks, release, docs

**Files:** `scripts/ux_consistency.py` (C15, C16), `src/floodwatch/__init__.py` (0.21.0), CHANGELOG, HANDOFF, README, docs/*.

- [ ] C15: for every gauge item in `/api/risks` groups 1–4: same `status`/`freeboard_m`/`change24.level` as `/api/stations`; no code twice; province counts add up. C16: every gauge with `age_min <= 1440` and lat is drawn on the map (count markers in the page vs stations).
- [ ] Deploy (`docker compose up -d --build app worker forecaster`), health, run `risk_record` once in the forecaster, run C1–C16, Playwright screenshots at 390 px of the tab, a sheet with the satellite line, the map with the toggle on.
- [ ] Release v0.21.0 (tag + GitHub release), docs per spec §7, memory/feedback notes, commit + push.
