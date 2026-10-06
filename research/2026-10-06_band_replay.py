"""E-BAND — do the daily range factors make the next day's ranges hold as stated? (KI-287, re-opened 2026-10-06; owner
2026-10-06: "Continue all the rest to finish"; Q54/D-098: ranges that hold as stated)

Read-only. Replays `risks.band90_factors` day by day on the stored forecasts (one run per gauge per 6 h, as the daily
record): at 00:00 UTC of day D, a factor per horizon (24/48/72 h) and kind (a model / "no change") from the outcomes known
by then, found on the RAW range (stored ranges un-widened by the factor in force — the KI-287 fix); applied to the raw
ranges of the runs issued on day D; scored on what happened. Rules: a window of W days and a target coverage, for the 90 %
range (q0–q4, calibrated since v0.26.0) and the 50 % range (q1–q3, the numbers on the rows, never calibrated so far).
Factors never narrow a range (k ≥ 1). Rules are chosen on the first test days and scored on the later ones (MODELS §5d).
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker nice python - \
       < research/2026-10-06_band_replay.py"""
import collections as C
import datetime as dt
import json

import numpy as np

from floodwatch import db, risks

START = dt.datetime(2026, 9, 26, tzinfo=dt.UTC)
HS = (24, 48, 72)
RULES = {"none": None, "W5 t90": (5, 0.90), "W3 t90": (3, 0.90), "W5 t93": (5, 0.93), "W3 t93": (3, 0.93),
         "W5 t50": (5, 0.50), "W3 t50": (3, 0.50), "W5 t53": (5, 0.53), "W3 t53": (3, 0.53)}
BAND_OF = lambda name: "50" if name.endswith(("t50", "t53")) else "90"

with db.connect_readonly() as c:
    c.execute("SET statement_timeout = '180s'")
    mean: dict = {}
    for r in c.execute(risks.HOURLY_SQL, {"since": START}):
        mean.setdefault(r["code"], {})[r["t"]] = r["mean"]
    runs = c.execute(risks.LEAN_SQL.replace("issue_time < now() - interval '24 hours'", "issue_time < now()"),
                     {"since": START}).fetchall()

rec = []  # (issue_time, h, kind, lo90, hi90, lo50, hi50, outcome − median)
for r in runs:
    t0 = r["issue_time"].replace(minute=0, second=0, microsecond=0)
    for p in (r["p24"], r["p48"], r["p72"]):
        if not p or not p.get("q") or p.get("h") not in HS or None in p["q"]:
            continue
        y = (mean.get(r["code"]) or {}).get(t0 + dt.timedelta(hours=p["h"]))
        if y is None:
            continue
        kind = "no change" if p.get("method") in (None, "persistence") else "model"
        k_prev = float(((r["band90"] or {}).get(str(p["h"])) or {}).get(kind) or 1.0)
        q = p["q"]
        rec.append((r["issue_time"], p["h"], kind, (q[0] - q[2]) / k_prev, (q[4] - q[2]) / k_prev, q[1] - q[2], q[3] - q[2],
                    y - q[2]))
print(f"stored runs (one per gauge per 6 h) {len(runs)}; scored ranges {len(rec)}")
T = np.array([x[0].timestamp() for x in rec]); HH = np.array([x[1] for x in rec]); KIND = np.array([x[2] for x in rec])
LO = {"90": np.array([x[3] for x in rec]), "50": np.array([x[5] for x in rec])}
HI = {"90": np.array([x[4] for x in rec]), "50": np.array([x[6] for x in rec])}
A = np.array([x[7] for x in rec])
GRID = np.array(risks.BAND90_GRID)


def factor(sel, band, target):
    """The smallest k ≥ 1 on the grid with `target` of the selected outcomes inside the k-widened raw range."""
    if sel.sum() < risks.BAND90_MIN_N:
        return 1.0
    lo, hi, a = LO[band][sel], HI[band][sel], A[sel]
    inside = (GRID[:, None] * lo - 1e-9 <= a) & (a <= GRID[:, None] * hi + 1e-9)
    ok = np.flatnonzero(inside.mean(1) >= target)
    return float(GRID[ok[0]]) if len(ok) else float(GRID[-1])


days = [START + dt.timedelta(days=d) for d in range(5, 11)]  # 10-01 … 10-06: every rule has ≥ 3 days behind it from 10-01
res = C.defaultdict(dict)  # (rule, h) -> {day: (coverage, n, mean factor)}
for D in days:
    d0, d1 = D.timestamp(), (D + dt.timedelta(days=1)).timestamp()
    for h in HS:
        test = (HH == h) & (T >= d0) & (T < d1)
        if test.sum() < 100:
            continue
        for name, rule in RULES.items():
            band = BAND_OF(name)
            k = np.ones(len(A))
            if rule is not None:
                W, target = rule
                for kind in ("model", "no change"):
                    train = (HH == h) & (KIND == kind) & (T + h * 3600 <= d0) & (T >= d0 - W * 86400 - h * 3600)
                    k[KIND == kind] = factor(train, band, target)
            for b in (("90", "50") if rule is None else (band,)):
                inside = (k[test] * LO[b][test] - 1e-9 <= A[test]) & (A[test] <= k[test] * HI[b][test] + 1e-9)
                res[(f"{name} ({b} %)", h)][D.strftime("%m-%d")] = (float(inside.mean()), int(test.sum()),
                                                                    float(k[test].mean()))

out = {}
for h in HS:
    keys = sorted({d for (n, hh), v in res.items() if hh == h for d in v})
    if not keys:
        continue
    half = len(keys) // 2 or 1
    choose, score = keys[:half], keys[half:]
    print(f"\n=== +{h} h — next-day coverage of the range (choose on {choose[0]}…{choose[-1]}, score on "
          f"{score[0] if score else '–'}…{score[-1] if score else '–'}); mean factor")
    for (name, hh), v in sorted(res.items()):
        if hh != h:
            continue
        cov = lambda ds: float(np.mean([v[d][0] for d in ds if d in v])) if any(d in v for d in ds) else float("nan")
        fac = float(np.mean([v[d][2] for d in v]))
        per_day = " ".join(f"{d}:{v[d][0] * 100:4.1f}" for d in keys if d in v)
        out[f"{name}|{h}"] = {"choose": round(cov(choose) * 100, 1), "score": round(cov(score) * 100, 1),
                              "factor": round(fac, 2), "days": {d: round(v[d][0] * 100, 1) for d in v}}
        print(f"{name:16s} choose {cov(choose) * 100:5.1f} % · score {cov(score) * 100:5.1f} % · factor {fac:4.2f} · {per_day}")
print("\n=== which side the misses fall on (raw ranges, as issued): share of outcomes below / above the range, by issue day")
for h in HS:
    for b in ("50", "90"):
        line = []
        for D in days:
            d0, d1 = D.timestamp(), (D + dt.timedelta(days=1)).timestamp()
            sel = (HH == h) & (T >= d0) & (T < d1)
            if sel.sum() < 100:
                continue
            below, above = (A[sel] < LO[b][sel] - 1e-9).mean(), (A[sel] > HI[b][sel] + 1e-9).mean()
            out[f"side|{b}|{h}|{D:%m-%d}"] = {"below": round(below * 100, 1), "above": round(above * 100, 1)}
            line.append(f"{D:%m-%d} {below * 100:4.1f}/{above * 100:4.1f}")
        print(f"+{h} h, {b} % range (below/above %): " + " · ".join(line))
print("SUMMARY_JSON", json.dumps(out))
