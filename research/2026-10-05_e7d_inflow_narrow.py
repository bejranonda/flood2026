"""E-7D-IN, two narrow changes to what is served (the full replacements failed the two-sample gate on dams made worse,
research/2026-10-05_e7d_inflow_strategies.log): (a) S+F — keep the served model where it is served, add family F only
where persistence is served now and F beat persistence by ≥ 10 % on the first half; (b) S·rain — the served model's
dams and horizons unchanged, its rain from the mean of several forecast models instead of best_match alone. Same per-dam
errors, same two samples, same gate (better than persistence and served-now at 3 d and 7 d in both samples, no more dams
worse than persistence than served-now). Run: python3 research/2026-10-05_e7d_inflow_narrow.py"""
import json

D = json.loads(next(l for l in open("research/2026-10-05_e7d_inflow.log") if l.startswith("PER_DAM_JSON "))[13:])
rows = [D[k] for k in sorted(D, key=int)]
samples = {1: rows[0::2], 2: rows[1::2]}
HS = [str(h) for h in range(1, 8)]


def run(chooser):
    out = {}
    for s, rs in samples.items():
        for h in HS:
            P = sum(r["B"][h]["P"] for r in rs)
            tot = worse = 0
            for r in rs:
                k = chooser(r, h)
                v = r["B"][h].get(k)
                v = r["B"][h]["P"] if v is None else v
                tot += v; worse += v > r["B"][h]["P"]
            out[(s, h)] = (tot / P - 1, worse)
    return out


S = run(lambda r, h: r["served"][h])
def gated(r, h, f):
    a = r["A"][h]
    return f if a.get(f) is not None and a[f] < 0.9 * a["P"] else "P"
strategies = {}
for f in ("D_E3", "D_ec", "D_bm", "L_E3", "L_bm", "R_E4", "R_bm", "D_E4", "KF_E3"):
    strategies[f"S+{f}"] = run(lambda r, h, f=f: r["served"][h] if r["served"][h] != "P" else gated(r, h, f))
strategies["S·rain(E4)"] = run(lambda r, h: "R_E4" if r["served"][h] == "R_bm" else "P")
print("strategy        " + " ".join(f"{h}d s1|s2" .rjust(17) for h in HS))
print("served now      " + " ".join(f"{100*S[(1,h)][0]:+5.1f}({S[(1,h)][1]})|{100*S[(2,h)][0]:+5.1f}({S[(2,h)][1]})".rjust(17) for h in HS))
for name, res in strategies.items():
    ok = all(res[(s, h)][0] < 0 and res[(s, h)][0] < S[(s, h)][0] and res[(s, h)][1] <= S[(s, h)][1] for s in (1, 2) for h in ("3", "7"))
    print(f"{name:15s} " + " ".join(f"{100*res[(1,h)][0]:+5.1f}({res[(1,h)][1]})|{100*res[(2,h)][0]:+5.1f}({res[(2,h)][1]})".rjust(17) for h in HS)
          + ("   GATE PASS" if ok else "   gate fail"))
kk = D["13"]
print("\nแก่งกระจาน (13): served", kk["served"], "\n  B half MAE per horizon (P · R_bm · R_E4 · D_E3 · D_E4 · L_E3):")
for h in HS:
    b = kk["B"][h]; a = kk["A"][h]
    print(f"  {h} d: B {b['P']:.2f} · {b['R_bm']:.2f} · {b['R_E4']:.2f} · {b['D_E3']:.2f} · {b['D_E4']:.2f} · {b['L_E3']:.2f}"
          f"   | A (choosing) P {a['P']:.2f} D_E3 {a['D_E3']:.2f} R_E4 {a['R_E4']:.2f}")
