"""D-099 pilot: does B.18 (below Kaeng Krachan) carry the dam's reported release? Daily mean B.18 flow vs RID's daily
release (dam id 13) and EGAT's (dam id 57), converted to m³/s; by month and lag 0/1 day. Read-only.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker python - < research/2026-10-05_impact_release_vs_b18.py"""
import numpy as np
from floodwatch import db

with db.connect_readonly() as c:
    q = {str(r["d"]): float(r["q"]) for r in c.execute(
        """SELECT (obs_time AT TIME ZONE 'Asia/Bangkok')::date AS d, avg(discharge) AS q FROM observation
           WHERE code='B.18' AND quality_flag='ok' AND discharge IS NOT NULL GROUP BY 1 HAVING count(*) >= 12""").fetchall()}
    rel = {}
    for dam in (13, 57):
        rel[dam] = {str(r["dam_date"]): float(r["released_mcm"]) * 1e6 / 86400 for r in c.execute(
            "SELECT dam_date, released_mcm FROM dam_daily WHERE dam_id=%s AND released_mcm IS NOT NULL", (dam,)).fetchall()}
for dam, name in ((13, "RID"), (57, "EGAT")):
    days = sorted(set(q) & set(rel[dam]))
    if len(days) < 20:
        print(name, "too few common days", len(days)); continue
    a, b = np.array([rel[dam][d] for d in days]), np.array([q[d] for d in days])
    print(f"{name}: {len(days)} days {days[0]}..{days[-1]} | median (B.18 − release) {np.median(b - a):+.1f} m³/s"
          f" | r {np.corrcoef(a, b)[0, 1]:.2f} | median release {np.median(a):.1f}, B.18 {np.median(b):.1f} m³/s")
    for m in sorted({d[:7] for d in days}):
        mm = [d for d in days if d.startswith(m)]
        aa, bb = np.array([rel[dam][d] for d in mm]), np.array([q[d] for d in mm])
        print(f"   {m}: n {len(mm):2d} release {np.median(aa):6.1f}  B.18 {np.median(bb):6.1f}  diff {np.median(bb - aa):+6.1f}")
    # does a change in the release show up at B.18 the same day or the next?
    da = np.diff(a); db_ = np.diff(b)
    for lag in (0, 1, 2):
        x, y = (da[:len(da) - lag], db_[lag:]) if lag else (da, db_)
        print(f"   day-to-day change, lag {lag} d: r {np.corrcoef(x, y)[0, 1]:.2f}")
