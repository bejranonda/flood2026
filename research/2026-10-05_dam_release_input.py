"""Q52 experiment E-DAM: a large dam's daily release as a `star` input for the gauges below it (owner 2026-10-05: "use the
data mixing data across various sources"; the dams' daily releases are in dam_daily since v0.28.0).
- Gauges "below" a dam: on the HII main-river line nearest the dam (≤ 8 km), downstream along the line within 150 km
  (rivers.chainage with the dam snapped onto the line as a pseudo-gauge), pre-declared;
- the input at hour i is the RID record's release of the previous Thai day (what is known that morning): log1p changes
  over 1 and 3 days and against the trailing 30-day mean — never a future value;
- star trained before the backtest window; method + 10 % gate chosen on the first half, scored on the second (q52_harness).
A variant that is never served at any horizon is a bug signal (NaN features drop every training row): the first run had
the time axis read as seconds instead of hours. The finite share of the input is now printed.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src:/research -v "$PWD/src:/app/src:ro" \
     -v "$PWD/research:/research:ro" worker python - < research/2026-10-05_dam_release_input.py"""
import datetime as dt, math
import numpy as np
import q52_harness as H
from floodwatch import db, forecast as F, rivers

MAX_LINE_KM, MAX_DOWN_KM = 8.0, 150.0
ICT = dt.timezone(dt.timedelta(hours=7))


def km(a, b):  # (lat, lon)
    p = math.pi / 180
    h = math.sin((b[0] - a[0]) * p / 2) ** 2 + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def nearest_line(feat, lat, lon):
    g = feat["geometry"]; parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
    best = None
    for part in parts:
        for x, y in part:
            d = km((lat, lon), (y, x))
            if best is None or d < best[0]:
                best = (d, (y, x))
    return best


def release_feature(t, series):
    """Hourly step series of the previous Thai day's release (ล้าน ลบ.ม./วัน), aligned to t (UTC hours)."""
    out = np.full(len(t), np.nan)
    for i, ts in enumerate(t):  # t = hours since the epoch (forecast.hourly_grid); the first run read it as seconds → all NaN
        d = (dt.datetime.fromtimestamp(float(ts) * 3600.0, tz=dt.timezone.utc).astimezone(ICT).date() - dt.timedelta(days=1)).isoformat()
        v = series.get(d)
        if v is not None:
            out[i] = v
    return out


sc = H.Score()
with db.connect_readonly() as c:
    feats = (db.get_state(c, "geo_rivers") or {}).get("features") or []
    dams = c.execute("""SELECT d.dam_id, d.name_th, d.lat, d.lon FROM dam d WHERE d.agency='RID'
                        AND (SELECT count(*) FROM dam_daily x WHERE x.dam_id=d.dam_id AND x.released_mcm IS NOT NULL
                             AND x.dam_date > now() - interval '400 days') >= 300 ORDER BY d.dam_id""").fetchall()
    gauges = c.execute("""SELECT s.code, s.lat, s.lon, s.bank_msl, s.in_focus, s.agency FROM station s
                          WHERE s.lat IS NOT NULL AND s.code !~ '^TEST' AND s.agency IS DISTINCT FROM 'BMA'
                          AND EXISTS (SELECT 1 FROM forecast_run f WHERE f.code=s.code AND f.issue_time > now() - interval '3 hours')""").fetchall()
    gl = [dict(g) for g in gauges]
    pairs = []  # (gauge, dam, river km below the dam)
    for d in dams:
        cands = [(nearest_line(f, d["lat"], d["lon"]), f) for f in feats]
        best = min(cands, key=lambda x: x[0][0])
        if best[0][0] > MAX_LINE_KM:
            print(f"{d['name_th']}: no main-river line within {MAX_LINE_KM} km (nearest {best[0][0]:.1f})"); continue
        snap, feat = best[0][1], best[1]
        ch = rivers.chainage(feat, gl + [{"code": "__DAM__", "lat": snap[0], "lon": snap[1], "bank_msl": None}])
        st = ch["stations"]
        if "__DAM__" not in st:
            print(f"{d['name_th']}: dam not placed on {feat['properties'].get('STR_NAMT')}"); continue
        up_dam = st["__DAM__"]["up"]
        below = [(g, up_dam - st[g["code"]]["up"]) for g in gl if g["code"] in st and 0 < up_dam - st[g["code"]]["up"] <= MAX_DOWN_KM]
        print(f"{d['name_th']:16s} on {feat['properties'].get('STR_NAMT')} (line {best[0][0]:.1f} km away, agree {ch['agree']}): {len(below)} gauges below within {MAX_DOWN_KM:.0f} km")
        for g, dist in below:
            pairs.append((g, d, dist))
    seen = set(); uniq = []
    for g, d, dist in sorted(pairs, key=lambda x: x[2]):  # a gauge below two dams takes the nearer one
        if g["code"] not in seen:
            seen.add(g["code"]); uniq.append((g, d, dist))
    print(f"gauges below a dam: {len(uniq)} (of {len(gl)} with a forecast)", flush=True)
    rel_cache, cache, done, finite_share = {}, {}, 0, []
    for g, d, dist in uniq:
        if d["dam_id"] not in rel_cache:
            rel_cache[d["dam_id"]] = {r["d"]: float(r["released_mcm"]) for r in c.execute(
                "SELECT dam_date::text AS d, released_mcm FROM dam_daily WHERE dam_id=%s AND released_mcm IS NOT NULL", (d["dam_id"],)).fetchall()}
        t, y = H.load_series(c, g["code"])
        if len(y) < 24 * 60:
            continue
        exo = F.load_exo(c, g["code"], g["lat"], g["lon"], cache, g["in_focus"], g.get("agency"))
        if not exo:
            continue
        ex = F.align_exo(t, exo)
        own, split = F._backtest_errors(t, y, None)
        raw = release_feature(t, rel_cache[d["dam_id"]])
        finite = float(np.isfinite(raw).mean())
        finite_share.append(finite)
        if finite < 0.5:
            print(f"  {g['code']}: only {finite:.0%} of hours have a release value for {d['name_th']} — skipped", flush=True)
            continue
        rel = np.log1p(np.clip(raw, 0, None))
        extra = np.column_stack([F._lagdiff(rel, 24), F._lagdiff(rel, 72), rel - F.trailing_mean(rel, 24 * 30)])
        plus = lambda t_, yf, eta, ybf, h, ex_: np.column_stack([F.star_features(t_, yf, eta, ybf, h, ex_), extra])
        sc.add("star (today)", own, H.star_errs(t, y, ex, own, split))
        sc.add("star + dam release", own, H.star_errs(t, y, ex, own, split, feats=plus))
        if dist <= 60:
            sc.add("star (today) ≤ 60 km", own, H.star_errs(t, y, ex, own, split))
            sc.add("star + dam release ≤ 60 km", own, H.star_errs(t, y, ex, own, split, feats=plus))
        done += 1
        if done % 10 == 0:
            print("…", done, flush=True)
print(f"gauges scored: {done} · release values present for {np.median(finite_share) if finite_share else 0:.0%} of hours (median gauge)")
print(sc.report(horizons=(12, 24, 48, 72)))
