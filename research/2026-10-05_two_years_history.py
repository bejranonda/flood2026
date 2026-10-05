"""Q52 experiment E-2Y (owner 2026-10-05): does `star` improve with two years of history instead of one? HII serves a year
per request, so each gauge (and its upstream gauges) gets 2024-09-01…2025-10-05 added in front of our 370-day archive.
Honest A/B on the same test window (forecast._backtest_errors scores the fixed last EVAL_HOURS whatever the length):
- arm "1 year": the production features, training rows restricted to the last 400 days;
- arm "2 years": the same features, all rows;
- both arms use the same inputs: upstream levels extended to two years (HII), ERA5 hourly rain at the gauge (the
  hindcast rain covers one year), no Flood Hub (its archive covers one year); so the baseline arm is production-like,
  not production. Two disjoint samples of 60 non-BMA gauges with an HII id; the served method + 10 % gate chosen on the
  first half of the window, scored on the second.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src:/research -v "$PWD/src:/app/src:ro" \
     -v "$PWD/research:/research:ro" worker python - < research/2026-10-05_two_years_history.py"""
import datetime as dt, json, time, urllib.parse, urllib.request
import numpy as np
import q52_harness as H
from floodwatch import db, forecast as F
from floodwatch.collectors import HII
from floodwatch.collectors import parsing
from floodwatch.config import settings

OLD_FROM, OLD_TO = "2024-09-01", "2025-10-05"
CUT_DAYS = 400


def get(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": settings.user_agent})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())
        except Exception:
            if k == tries - 1:
                return None
            time.sleep(2 * (k + 1))


def hii_year(hii_id):
    """(times UTC, levels) for the extra year from HII's graph (ICT stamps, no zone)."""
    d = get(f"{HII}/waterlevel_graph?station_type=tele_waterlevel&station_id={hii_id}&start_date={OLD_FROM}&end_date={OLD_TO}%2023:59")
    out_t, out_v = [], []
    for p in ((d or {}).get("data") or {}).get("graph_data") or []:
        t = parsing.parse_local(p.get("datetime"))
        v = parsing.to_float(p.get("value"))
        if t is not None and v is not None:
            out_t.append(t); out_v.append(v)
    time.sleep(0.7)
    return out_t, out_v


def era5_hourly(lat, lon):
    d = get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat:.3f}&longitude={lon:.3f}&start_date={OLD_FROM}&end_date=2026-10-05&hourly=precipitation&timezone=UTC")
    hind = {}
    for ts, v in zip(d["hourly"]["time"], d["hourly"]["precipitation"]):
        h = int(dt.datetime.fromisoformat(ts).replace(tzinfo=dt.timezone.utc).timestamp() // 3600)
        hind[h] = (float(v or 0.0), float(v or 0.0))
    time.sleep(0.3)
    return hind


with db.connect_readonly() as c:
    chain = F._chainage()
    learned = db.get_state(c, "upstream_learned") or {}
    hii_ids = {r["code"]: r["hii_id"] for r in c.execute("SELECT code, hii_id FROM station WHERE hii_id IS NOT NULL").fetchall()}
    for k in (1, 2):
        sc = H.Score()
        codes = H.sample_codes(c, 60, k, where="s.agency IS DISTINCT FROM 'BMA' AND s.hii_id IS NOT NULL AND s.lat IS NOT NULL")
        meta = {r["code"]: r for r in c.execute("SELECT code, lat, lon, in_focus, agency, hii_id FROM station WHERE code = ANY(%s)", (codes,)).fetchall()}
        series_cache, done, rows1, rows2, longer = {}, 0, [], [], 0

        def two_year_series(code):
            if code not in series_cache:
                t_db, v_db = H.load_raw(c, code)
                t_old, v_old = hii_year(hii_ids[code]) if code in hii_ids else ([], [])
                series_cache[code] = (list(t_old) + list(t_db), list(v_old) + list(v_db), len(t_old))
            return series_cache[code]
        for code in codes:
            s = meta.get(code)
            if not s:
                continue
            times, vals, n_old = two_year_series(code)
            if n_old < 24 * 200:
                continue  # HII gave no usable extra year: this gauge cannot test the question
            longer += 1
            t, y = F.hourly_grid(times, vals)
            if len(y) < 24 * 500:
                continue
            ups = [two_year_series(u) for u in F.upstream_codes(code, chain, s["in_focus"], learned) if u in hii_ids]
            exo = {"up": [(u[0], u[1]) for u in ups if u[0]], "q": None, "rain": {"hind": era5_hourly(s["lat"], s["lon"]), "live": {}}, "gfh": None}
            ex = F.align_exo(t, exo)
            own, split = F._backtest_errors(t, y, None)
            cut = len(y) - CUT_DAYS * 24
            def one_year(t_, yf, eta, ybf, h, ex_):
                X = F.star_features(t_, yf, eta, ybf, h, ex_)
                X = X.copy(); X[:max(0, cut)] = np.nan  # rows before the last 400 days leave the fit
                return X
            e1 = H.star_errs(t, y, ex, own, split, feats=one_year)
            e2 = H.star_errs(t, y, ex, own, split)
            sc.add("star, 1 year (same inputs)", own, e1)
            sc.add("star, 2 years", own, e2)
            done += 1
            if done % 10 == 0:
                print("…", done, flush=True)
        print(f"\n=== sample {k}: {done} gauges with two years (HII gave an extra year for {longer} of {len(codes)})")
        print(sc.report(horizons=(12, 24, 48, 72)))
