"""E-7D-IN, the choice (owner 2026-10-05: "Try validating many possibilities, models, theories, inputs, parameters for 7-day
forecast"; the two-sample gate): which way of choosing a forecaster per dam and horizon holds on dams it was not chosen on?
Reads the per-dam errors of research/2026-10-05_e7d_inflow.log (first half A = choosing, second half B = scoring) — no
new fit, no new data. Strategies, each scored on B:
  S        served now (D-102: the Q58 rain model where it passed, persistence elsewhere)
  C        per dam and horizon, the best of all candidates on A if ≥ 10 % better than P there, else P
  F:<fam>  one family for every dam, used per dam and horizon only where it beat P by ≥ 10 % on A, else P
  G        one candidate per horizon picked on the other sample's A (no per-dam gate)
Two samples = alternating dams in dam_id order (as the experiment). Gate: better than P AND than S at 3 d and 7 d in both
samples, no more dams worse than P than S has. Prints the leaderboard per horizon and the gate per strategy.
Run: python3 research/2026-10-05_e7d_inflow_strategies.py"""
import json, sys

LOG = "research/2026-10-05_e7d_inflow.log"
line = next(l for l in open(LOG) if l.startswith("PER_DAM_JSON "))
D = json.loads(line[len("PER_DAM_JSON "):])
dams = sorted(D.values(), key=lambda r: next(int(k) for k, v in D.items() if v is r))
ids = sorted(int(k) for k in D)
rows = [D[str(i)] for i in ids]
samples = {1: rows[0::2], 2: rows[1::2]}
HS = [str(h) for h in range(1, 8)]
GATE = 0.10
names = sorted({k for r in rows for k in r["A"]["1"]})
families = sorted({n for n in names if n not in ("P",)})


def pick_family(r, h, fam):
    a = r["A"][h]
    v = a.get(fam)
    return fam if v is not None and a["P"] is not None and v < (1 - GATE) * a["P"] else "P"


def pick_c(r, h):
    a = r["A"][h]
    c = [(v, k) for k, v in a.items() if v is not None and k != "P"]
    b = min(c)[1] if c else "P"
    return b if a[b] < (1 - GATE) * a["P"] else "P"


def score(rows_, h, chooser):
    P = sum(r["B"][h]["P"] for r in rows_)
    tot, worse = 0.0, 0
    for r in rows_:
        k = chooser(r)
        v = r["B"][h].get(k)
        v = r["B"][h]["P"] if v is None else v
        tot += v
        worse += v > r["B"][h]["P"]
    return tot / P - 1, worse


strategies = {"S": lambda h: (lambda r: r["served"][h] if r["B"][h].get(r["served"][h]) is not None else "P"),
              "C": lambda h: (lambda r: pick_c(r, h))}
for f in families:
    strategies[f"F:{f}"] = (lambda f_: (lambda h: (lambda r: pick_family(r, h, f_))))(f)

res = {}
for s_name, mk in strategies.items():
    for s, rs in samples.items():
        for h in HS:
            res[(s_name, s, h)] = score(rs, h, mk(h))
# G: one candidate per horizon picked on the other sample's A (sum of A errors), no per-dam gate
for s, rs in samples.items():
    other = samples[2 if s == 1 else 1]
    for h in HS:
        tots = {n: sum(r["A"][h][n] for r in other) for n in names if n != "P" and all(r["A"][h].get(n) is not None for r in other)}
        g = min(tots, key=tots.get)
        res[("G", s, h)] = score(rs, h, lambda r, g=g: g) + (g,)

print(f"dams {len(rows)} (sample 1: {len(samples[1])}, sample 2: {len(samples[2])})")
for h in HS:
    board = []
    for s_name in list(strategies) + ["G"]:
        a, b = res[(s_name, 1, h)], res[(s_name, 2, h)]
        board.append((max(a[0], b[0]), s_name, a, b))
    board.sort()
    print(f"\n=== {h} d — error vs persistence on the scored half (sample 1 | sample 2), dams worse than persistence")
    for worst, s_name, a, b in board[:12]:
        extra = f" [{a[2]} | {b[2]}]" if s_name == "G" else ""
        print(f"  {s_name:10s} {100 * a[0]:+6.1f} % ({a[1]:2d} worse) | {100 * b[0]:+6.1f} % ({b[1]:2d} worse){extra}")
    s_ = res[("S", 1, h)], res[("S", 2, h)]
    print(f"  served now {100 * s_[0][0]:+6.1f} % ({s_[0][1]:2d}) | {100 * s_[1][0]:+6.1f} % ({s_[1][1]:2d})")

print("\n=== GATE: better than persistence and than served-now at 3 d and 7 d in both samples, no more dams worse than served-now")
passed = []
for s_name in list(strategies) + ["G"]:
    if s_name == "S":
        continue
    ok = all(res[(s_name, s, h)][0] < 0 and res[(s_name, s, h)][0] < res[("S", s, h)][0] and res[(s_name, s, h)][1] <= res[("S", s, h)][1]
             for s in (1, 2) for h in ("3", "7"))
    if ok:
        passed.append((max(res[(s_name, s, h)][0] for s in (1, 2) for h in ("3", "7")), s_name))
for worst, s_name in sorted(passed)[:10]:
    print(f"PASS {s_name:10s} worst of (3 d, 7 d) × (sample 1, 2): {100 * worst:+.1f} %  · per horizon (s1|s2): " +
          " ".join(f"{h}d {100 * res[(s_name, 1, h)][0]:+.0f}|{100 * res[(s_name, 2, h)][0]:+.0f}" for h in HS))
if not passed:
    print("no strategy passes")
print("\n6 vs 7 days (owner: 'limit to 6 days if necessary') — the best passing strategy's gain at 6 d and 7 d:",
      {s_name: [round(100 * res[(s_name, s, h)][0], 1) for s in (1, 2) for h in ("6", "7")] for _, s_name in sorted(passed)[:3]})
