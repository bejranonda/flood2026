# Impact analysis page — pilot: Kaeng Krachan Dam (เขื่อนแก่งกระจาน), Phetchaburi River

> Owner 2026-10-05: "Make extra tab to make case for flood impact analysis, the pilot is แก่งกระจาน … might need a password
> … Test & Validate as view from onwr." Decisions (grill-me, 2026-10-05): audience **ONWR/RID engineers** (release
> decisions); access **one shared password in the app**; placement **separate page `/impact`** (public tabs untouched);
> first answer **a what-if release table**; model **rating curves + travel times**; input **ล้าน ลบ.ม./วัน** with m³/s
> shown; diversion at เขื่อนเพชร **an input, default from recent data**. Decision record: D-099.

## Question it answers
"If Kaeng Krachan releases X ล้าน ลบ.ม./วัน (and เขื่อนเพชร diverts D m³/s), when and how high does the water get at each
point downstream, and does it overflow?" — for engineers, with units, data age, uncertainty and the limits stated.

## Data (2026-10-05)
| Item | Source | Evidence |
|---|---|---|
| Dam daily release, storage, inflow | HII `analyst/dam` → `dam_daily`, **RID record (dam id 13)** | 10.8 ล้าน ลบ.ม./วัน ≈ 125 m³/s matches B.18 below the dam (128–142 m³/s, 1–5 Oct). EGAT's record (id 57: 3.04 ≈ 35 m³/s, 58.6 %) looks like the turbines only — shown as a note |
| River points | our gauges, 1 year hourly: B.18 เขาลูกช้าง (Q, h), B.10 ตลาดท่ายาง (Q, h), B.16 สะพานบ้านลาด (Q, h), B.15 ข้างจวนผู้ว่าฯ (h), PCH001 เมืองเพชรบุรี (HII, h) | PCH003 "ท่ายาง" moves with B.18 (r 0.98, lag 0, same 23–26 m): it sits near the dam, not in Tha Yang town |
| Travel times from B.18 | 24 h-change cross-correlation | B.10 ~32 h, B.16 ~43 h, B.15 ~45 h, PCH001 ≥ 48 h (r ≈ 0.5: the diversion dam in between) |
| Range seen | B.18 max 143 m³/s in the year | anything above is **outside the data** and flagged |

## Method (pilot)
1. **Flow down the river (mass balance):** B.18 = release + local inflow (today's B.18 − today's release); after เขื่อนเพชร:
   B.10 = max(0, B.18 − diversion) + local (today's B.10 − (today's B.18 − today's diversion), ≥ 0); B.16 = B.10 + today's
   (B.16 − B.10). A steady release is assumed (held ≥ 1 day); short pulses arrive lower (attenuation not modelled yet).
2. **Flow → level:** a rating curve h = h₀ + a·Qᵇ per gauge with flow (B.18, B.10, B.16), fitted on the year's hourly pairs;
   the city gauges (B.15, PCH001 — no flow) against B.16's flow at the learned lag. Level range = the 10–90 % residuals.
3. **When:** the learned lag per point ± a window; B.18 within a few hours of the dam.
4. **Compare with the bank** of each gauge's own agency (never mixed, KI-217): margin, overflow flag.
5. **Outside the data** when a point's flow exceeds the highest it carried in the year (rating curve extrapolated).
6. **Validation:** replay the year — use B.18's observed flow as the "release" and the model's flows/levels at the
   learned lags against what was measured (MAE, timing); extremes wait for ONWR's past events.

## Security
Password only in `.env` (`IMPACT_PASSWORD`, never in git or logs); constant-time compare; a signed HttpOnly, Secure,
SameSite=Strict cookie (12 h) that also binds to the password (changing it logs everyone out); 5 failed tries per 15 min per
client; `/impact` and `/api/impact/*` are `noindex` and disallowed in robots. The pilot shows public data only; **before
ONWR/RID data are loaded the password must be a long passphrase** (OWNER_ACTIONS IMPACT).

## Next (when ONWR data arrive)
Hourly releases and planned releases; เขื่อนเพชร gate operations and canal diversions; verified banks and rating curves;
channel capacity at Tha Yang, Ban Lat and the city; past events (Aug 2018 spillway overflow) for the replay of extremes.
