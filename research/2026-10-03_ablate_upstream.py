"""Does a gauge's forecast gain from more stations? Ablation on our own network (2026-10-03): the same rolling backtest
(forecast.evaluate) with the learned upstream gauges as inputs (2), only the first (1), none (0)."""
import json, random, sys
import numpy as np
from floodwatch import db, forecast as F
random.seed(7)
out = []
with db.connect() as c:
    learned = db.get_state(c, "upstream_learned") or {}
    codes = [k for k, v in learned.items() if len(v) >= 2]
    sample = random.sample(codes, min(int(sys.argv[1]) if len(sys.argv) > 1 else 50, len(codes)))
    meta = {r["code"]: r for r in c.execute("SELECT code, lat, lon, in_focus FROM station WHERE code = ANY(%s)", (sample,)).fetchall()}
    cache = {}
    for code in sample:
        m = meta.get(code)
        if not m:
            continue
        rows = c.execute("""SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                            AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""", (code, F.LOOKBACK_DAYS)).fetchall()
        if len(rows) < 24 * 60:
            continue
        exo = F.load_exo(c, code, m["lat"], m["lon"], cache, m["in_focus"])
        if not exo or len(exo["up"]) < 2:
            continue
        t, y = F.hourly_grid([r["obs_time"] for r in rows], [float(r["level_msl"]) for r in rows])
        res = {"code": code}
        for k in (2, 1, 0):
            ev = F.evaluate(t, y, F.align_exo(t, {**exo, "up": exo["up"][:k]}))
            res[k] = {h: {"star": ev[h]["rmse"].get("star"), "best": min(ev[h]["rmse"].values()),
                          "persist": ev[h]["rmse"]["persistence"], "chosen": ev[h]["method"]} for h in (12, 24, 48) if h in ev}
        out.append(res)
        print(code, {k: {h: round(v["best"] * 100, 1) for h, v in res[k].items()} for k in (2, 1, 0)}, flush=True)
json.dump(out, open("/out/ablate_upstream.json", "w"))
print("done", len(out))
