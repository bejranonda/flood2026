# ONWR legal basins (owner download): same 22 basins as HII's map, and what basin data can still add

**Date:** 2026-10-02 · **Owner:** downloaded "Shp_Basin_ONWR" from the DWR page and asked "validate and check, whether the basin data is useful".
**Scripts (re-runnable):** [2026-10-02_onwr_basins.py](2026-10-02_onwr_basins.py) (file vs HII map) · [2026-10-02_cross_basin.py](2026-10-02_cross_basin.py) (backtest).

## The file (inspected 2026-10-02 10:10 UTC)
- Page: `division.dwr.go.th/rdhd/index.php/th/services/12/2024-04-17-02-39-05/160-shapefiles` — "ขอบเขตลุ่มน้ำหลักของสำนักงานทรัพยากรน้ำแห่งชาติ", source สทนช. (ONWR), dated 7 Jul 2021; files on Google Drive. **No licence or terms stated** ⚠️ — so the raw file is kept out of the public repo (stored in `data/basins/raw/`, git-ignored); only derived counts are published here.
- Content: `MainBasin_ONWR_Law_WGS84` — **only the 22 main basins** of the 2021 legal scheme (28 records: 22 + 6 island parts), UTM 47N, CP874 attributes `MB_CODE, MBASIN_T, MBASIN_E, AREA_SQKM, Basin_T`, 669,589 vertices. **No sub-basins** (the download folder holds only this layer), so it cannot replace HydroBASINS for upstream catchments.

## Validation against HII's `basin.json` (the map production uses, 7,167 vertices)
- Same 22 basins; names identical except the spelling โตนเลสาบ (ONWR) / โตนเลสาป (HII). Areas agree within ~2 % (e.g. Mun 70,948 vs 70,716 km², Chao Phraya 20,440 vs 20,595).
- All 1,026 placed gauges: **1,011 in the same basin (98.5 %)**; 2 differ only by the spelling (SKE003, TON001); 8 sit on a basin boundary (≤ 0.1 km from ONWR's line: BKK001, WL.SST.01, PAS009, DIV004, MKG006, X.119A, MYA005, GLF003), where either answer is defensible; 5 lie outside both maps (abroad). HII's simplified map is good enough; the ONWR file adds precision at a handful of boundary gauges and no new information for the model.

## Can the basin hierarchy add upstream gauges? (cross-basin backtest, run 10:17–10:33 UTC)
Idea: production learns upstream gauges only inside the gauge's own basin, but the 22 basins are nested (Ping, Wang, Yom, Nan, Sakae Krang, Pasak → Chao Phraya; Chi → Mun → Mekong), so a gauge below a confluence cannot learn from the rivers that feed it. 228 gauges on main rivers whose river system spans several basins; learned before the backtest window as in production.

| Variant | Gauges whose upstream set changed | 12 / 24 / 48 h over gate (of 10) | star RMSE median vs A (12 / 24 / 48 h) |
|---|---|---|---|
| A production (same basin + same river system) | — | 6 / 5 / 5 | — |
| X any basin on the same river system | 10 | 7 / 4 / 3 | +1.5 / +3.5 / +4.4 % (better at 4 / 3 / 1 of 9) |
| Y only basins that drain into the gauge's basin | **0** | — | — |

X picked physically wrong links: Ping ← Yom (CHM004 ← Y.1C), Yom ← Nan, Pasak ← Ping (S.28 ← P.17, a shared rain signal 44 h apart), Mun ← Mekong (AIT011 ← AIT008/009, downstream backwater: 24 h skill 0.27 → 0.12), Mae Klong ← Phetchaburi (MKG006, a boundary gauge). Y — the hydrologically allowed links — found none that qualify (r ≥ 0.5, lag 1–48 h, ≤ 250 km). **Conclusion: the current rule stands** — the basin boundary is what keeps spurious links out; the hierarchy adds no usable link for today's gauges.

## Verdict
The ONWR file **validates** the basin map production uses (98.5 % identical, differences only on boundary lines) and confirms the "same basin" rule; it adds no new forecasting input. Not adopted in code (nothing to gain, and no licence stated). Upstream-catchment rain is tested with HydroBASINS instead: [2026-10-02_catchment_rain.md](2026-10-02_catchment_rain.md).
