"""Q52 experiment E-UQ: for RID gauges whose learned upstream gauges measure discharge, the upstream flow change (log Q,
24 and 48 h) as a `star` input next to the upstream level change — routing by flow rather than by level. Honest protocol,
two disjoint samples; the target stays the level (as served).
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src:/research -v "$PWD/src:/app/src:ro" \
     -v "$PWD/research:/research:ro" worker python - < research/2026-10-05_upstream_flow_input.py"""
import numpy as np
import q52_harness as H
from floodwatch import db, forecast as F

WHERE = "s.agency IS DISTINCT FROM 'BMA' AND s.lat IS NOT NULL"


def on_grid(t, tq, q):
    """q (on its own hourly grid tq) placed on t (hours since the epoch), NaN where missing."""
    out = np.full(len(t), np.nan)
    pos = {int(h): i for i, h in enumerate(tq)}
    for i, h in enumerate(t):
        j = pos.get(int(h))
        if j is not None:
            out[i] = q[j]
    return out


def load_q(c, code):
    rows = c.execute("""SELECT obs_time, discharge FROM observation WHERE code=%s AND quality_flag='ok' AND discharge IS NOT NULL
                        AND discharge >= 0 AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""", (code, F.LOOKBACK_DAYS)).fetchall()
    if len(rows) < 24 * 60:
        return None
    return F.hourly_grid([r["obs_time"] for r in rows], [float(np.log1p(r["discharge"])) for r in rows])


with db.connect_readonly() as c:
    chain = F._chainage()
    learned = db.get_state(c, "upstream_learned") or {}
    for k in (1, 2):
        sc = H.Score()
        codes = H.sample_codes(c, 200, k, where=WHERE)
        meta = {r["code"]: r for r in c.execute("SELECT code, lat, lon, in_focus, agency FROM station WHERE code = ANY(%s)", (codes,)).fetchall()}
        cache, qcache, done, with_uq = {}, {}, 0, 0
        for code in codes:
            s = meta.get(code)
            if not s:
                continue
            ups = F.upstream_codes(code, chain, s["in_focus"], learned)
            uqs = []
            for u in ups:
                if u not in qcache:
                    qcache[u] = load_q(c, u)
                if qcache[u] is not None:
                    uqs.append(qcache[u])
            if not uqs:
                continue  # only gauges with at least one flow-measured upstream gauge are in this test
            t, y = H.load_series(c, code)
            if len(y) < 24 * 60:
                continue
            exo = F.load_exo(c, code, s["lat"], s["lon"], cache, s["in_focus"], s["agency"])
            if not exo:
                continue
            ex = F.align_exo(t, exo)
            own, split = F._backtest_errors(t, y, None)
            cols = []
            for tq, q in uqs:
                g = on_grid(t, tq, q)
                cols += [F._lagdiff(g, 24), F._lagdiff(g, 48)]
            extra = np.column_stack(cols)
            plus = lambda t_, yf, eta, ybf, h, ex_: np.column_stack([F.star_features(t_, yf, eta, ybf, h, ex_), extra])
            sc.add("star (today)", own, H.star_errs(t, y, ex, own, split))
            sc.add("star + upstream flow", own, H.star_errs(t, y, ex, own, split, feats=plus))
            done += 1
            if done % 10 == 0:
                print("…", done, flush=True)
        print(f"\n=== sample {k}: {done} gauges with a flow-measured upstream gauge (of {len(codes)} sampled)")
        print(sc.report(horizons=(12, 24, 48, 72)))
