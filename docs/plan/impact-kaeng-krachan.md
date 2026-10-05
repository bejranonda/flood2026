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
| Travel times from B.18 | 24 h-change cross-correlation | first estimate (all year): B.10 ~32 h, B.16 ~43 h, B.15 ~45 h, PCH001 ≥ 48 h; as built (first 60 % vs whole year): B.10 24–30 h, B.16 31–37 h, B.15 38–43 h, PCH001 36–44 h, r 0.29–0.46 (the diversion dam in between) |
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

## Validation result (2026-10-05, honest replay — read before building any screen)
Ratings and lags fitted on the first 60 % of the year, judged on the last 40 % (`research/2026-10-05_impact_anchored_replay.log`),
level error vs simply keeping today's level:
| Method | B.10 ท่ายาง | B.16 บ้านลาด | B.15 / PCH001 เมือง |
|---|---|---|---|
| Absolute (mass balance + rating curve) | 44 vs 13 cm | 56 vs 14 cm | 55 vs 33 / 52 vs 17 cm |
| Anchored to today's level, change passed 1:1 | 25 vs 13 cm (big changes 108 vs 25) | 99 vs 14 cm | 112 vs 33 / 89 vs 17 cm |
| Anchored, learned pass-through gain | 12.0 vs 12.5 cm (big 29.7 vs 24.9) | 13.4 vs 13.5 cm | 45 vs 33 / 23 vs 17 cm |
**Finding:** in the past year flow changes at B.18 (≤ 143 m³/s) did not travel down the river — เขื่อนเพชร's operation absorbed
them; downstream levels followed the diversion, local rain and (in the city) the tide. No model built on our public data beats
"keep today's level". The steep ratings (B.10 ≈ 4–5 cm per m³/s) turn small flow errors into large level errors. For
flood-size releases the surplus must pass the diversion dam (the 1:1 assumption becomes physical), but the year holds no such
event to check it. **What makes the what-if credible:** (1) เขื่อนเพชร gate settings and canal intake flows (hourly/daily);
(2) past flood events with dam release, downstream levels and flooded areas (e.g. Aug 2018); (3) canal capacity.

## As built (v0.27.0, 2026-10-05)
Owner chose **"Board + validation + data request now"** after the replay. `/impact` shows: the dam's RID record against
HII's rule curve and its yearly maxima since 2018 (`analyst/dam_yearly_graph`), EGAT's record and open doubts as questions;
the river now; the replay (four methods, rebuilt hourly); the what-if table **off** (HTTP 409) until a method beats keeping
today's level by ≥ 10 % at B.10 and B.16; the data request with five CSV templates; the method with a live check that
B.18 carries RID's release (r 0.93 over a year). Security as above plus a strict CSP and `X-Frame-Options: DENY`.
Numbers and ratings: MODELS §11; facts: KNOWLEDGE §25; doubts: KI-293–KI-297; owner questions: Q56.

## v0.28.0: the main app plus a "💧 ผลกระทบ" tab (D-100)
Owner: "similar map and functions to main page but add the risk and impacts as additional tab" → `/impact` serves the main
app with one more tab: national dams at risk (rule-curve position, both agencies, release history) and the cases (this
pilot first, drawn on the map with the real river line). The board above is the case view; the gate is unchanged.

