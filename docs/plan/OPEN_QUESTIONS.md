# OPEN_QUESTIONS.md — Questions for the owner

> The brief asks the team to keep asking until the picture is clear. These are the questions that change what gets built.
> When one is answered, move it to "Answered" with the date, and record any resulting decision in [DECISIONS.md](DECISIONS.md).

## Open
> **Steps, costs and verification for each item are in [../OWNER_ACTIONS.md](../OWNER_ACTIONS.md)** (D-026). Check status with `python3 scripts/owner_status.py`. Last verified 2026-09-27 ~10:10 UTC.

| # | Question | Why it matters | Priority |
|---|---|---|---|
| **Q28** | **Review of branch `research/nationwide-scope`**: merge the issue #1 fix and the validated plan? Then which step of D-045 first (HII canal feed as primary, BMA road sensors, tide, RID thresholds)? | Nothing from the branch is live until you review (A30) | **1** |
| ~~**Q51**~~ | ✅ **Resolved 2026-10-04 (D-091 amended: lean only where the chart's line goes the same way ≥ 3 cm).** **Lean word vs model range (D-091):** where they point different ways (HDA009: "↘ น่าจะลดลง", −5 to +15 cm), show the range only on tap, or let the lean shift the shown range? | A quick reader may see a contradiction; the record supports the word (75 %), the model the numbers | 2 |
| **Q49** | **Google Flood Hub after 1–2 weeks (D-087):** show a "Google คาด 3–9 วัน" line where it agreed with our gauges, or keep it as a back-office cross-check? | It adds lead time and 31 river points without our gauges, but missed 7 over-bank places in the first snapshot | 2 |
| **Q50** | **A จับตา group for dams above their upper rule curve (D-090)?** Same HII call; "a release increase is likely" | Operations decide the lower rivers; this is the closest public signal we have | 2 |
| **Q46** | **DWR posts after 2–4 weeks of archive (D-081):** show them beyond the trend-only layer (e.g. in pin panels where no gauge is within 10 km), and test them as upstream inputs? | 362 fresh posts, mostly where our gauges are thin; quality unknown until our own history exists | 2 |
| **Q47** | **Allow 3–4 learned upstream gauges per gauge?** The ablation showed the second upstream gauge adds as much as the first (no saturation at 2) | Cheap gain from stations we already have; needs a backtest of 3–4 | 2 |
| **Q48** | **Bank values (KI-272):** may we spot-check RID's published bank ("ตลิ่ง") for the 14 red gauges whose HII fields disagree, and correct confirmed ones? | A wrong bank makes a red "ล้นตลิ่ง" or hides one | 1 |
| **Q44** | **WeatherNext after its backtest (D-069)** — owner 2026-10-03: "keep weathernext for later, I will update the subscription first": if its rain beats Open-Meteo in our 48 h model, may the public forecast use it? That needs Google's notice "experimental … not intended, validated, or approved for real world use" on the site and handling of the Japan/South Korea/Indonesia clause (or a written permission from weathernext@google.com). | Decides whether a backtest win can ever reach users | after WNEXT ✅ + backtest |
| **Q45** | ~~A satellite line outside Bangkok?~~ **Answered 2026-10-03: "yes" → built v0.19.0 (D-071).** | | done |
| Q41 | **More gauges for Nonthaburi (user request, 2026-10-01):** ปากเกร็ด, เมืองนนทบุรี, บางกรวย, บางใหญ่, บางบัวทอง have only 3 live HII gauges. Do you know a public source (อบจ./เทศบาลนครนนทบุรี/เทศบาลนครปากเกร็ด, RID canal gauges) or a contact who could share one? | Canal level where the user asked | 1 |
| Q38 | **Dam-controlled reaches (v0.16):** gauges such as E.29/URTU07 (Nam Phong, above Ubol Ratana) move with releases; only C.13 (Chao Phraya Dam) enters the model. Worth asking EGAT/RID for release plans, or should these gauges show measured data and ranges only? | Forecast honesty upstream/downstream of large dams | 2 |
| Q39 | **Status words for rivers (v0.16):** the status chip "ใกล้ตลิ่ง/คลองเต็ม" names canals, but most nationwide gauges are rivers. Change the label everywhere (e.g. "ใกล้ตลิ่ง") or keep the v0.15 wording (D-063)? | One status vocabulary for the whole country | 3 |
| Q33 | **Report rate after the popup (issue #2):** baseline 57 reports/24 h (56 with depth) on 2026-09-27. If it drops by more than ~30 % in a week, keep the button but show the depth choice inline? | Reports are our only ground truth at street level | 2 |
| Q30 | **Flood season priority for the national view:** which region first after Bangkok? (South Gulf floods mainly Oct–Jan per the research ⚠️; Northeast/Mekong now) | Order of D-046 collectors and thresholds | 2 |
| Q31 | **Officials/volunteers:** what do they need that residents don't (a table view, an export, LINE alerts, a login)? Anyone to ask? | Scope of the "officials" audience (A28) | 2 |
| RID | **Gate coordinates** (`code,lat,lon`) for the 15 unplaced and 14 approximate stations | Exact map positions, point checks ([KI-207](../KNOWN_ISSUES.md)) | 2 |
| Q23 | **GLM API Key** (`GLM_API_KEY` in `.env`) when ready for AI triage of citizen feedback notes | Enables background AI classification of feedback notes | 3 |
| Q19 | Who reads **feedback notes**, how often; a review page or SQL? (first real report arrived 10:17 UTC) | Feedback is only useful if someone acts on it ([D-020](DECISIONS.md)) | — |
| Q22 | Workers AI for **Traffy text labelling** or **voice reports**? ($5/month Workers Paid if over the free quota) | Cost vs value ([APPROACH §3.6](../APPROACH_AND_METHODS.md)) | — |
| Q7 | **Notifications:** LINE or Web Push? | Scope; whether user data must be stored | — |
| Q8 | Dates in the **Buddhist era (พ.ศ.)**? | UI | — |
| Q11 | **Budget/retention** for R2 and the raw archive | Sizing | — |
| Q12 | **Who is on call** during a flood? | Alert routing | — |
| Q3 | Permission mails to **HII / BMA / Traffy**, and **DWR / RID** before national data goes public (drafts in OWNER_ACTIONS, D-046) | Public redistribution; national launch | 3 |
| Q4 | **TMD / GISTDA / Copernicus GFM / NASA** keys? | Optional P2 sources. **2026-10-02:** GISTDA ✅, GFM account ✅ (maps keyless), EWDS ✅; TMD and NASA not needed so far | — |
| Q6 | Will the app ever be **commercial**? | Open-Meteo and FABDEM are non-commercial ([KI-106](../KNOWN_ISSUES.md)) | — |
| Q9 | **Frontend framework** preference? | The plain-JS app is enough so far | — |

## Answered
| # | Question | Answer (date) | Decision |
|---|---|---|---|
| **Q43** | Measured rain as a forecast input | **Answered 2026-10-01 ("Continue … validate"):** daily HII totals tested, no gain → not adopted; hourly archive kept 400 days near water gauges; re-test ~mid-December 2026 ([research](../../research/2026-10-01_measured_rain.md)) |
| **Q42** | Finer rain forecast for Bangkok and its neighbours | **Answered 2026-10-01: "Continue as suggested"** → v0.16.4 (111 points at the ~8 km grid) |
| **Q40** | Default region by location | **Answered 2026-10-01: "Allow GPS"** → D-065 (v0.16.2) |
| A27 | What should "whole Thailand" mean next? | **Monitor first, forecast later** (2026-09-27) | [D-044](DECISIONS.md) |
| A28 | Who should the national version serve? | **Residents in any province and local officials / volunteers** (2026-09-27) | [D-044](DECISIONS.md) |
| A29 | Bangkok improvements found by the probes vs national work? | **Bangkok before national** (2026-09-27) | [D-045](DECISIONS.md) |
| A30 | What should this session build, and where does it go? | First "Bangkok live + national collectors behind a flag"; then **"keep on the branch"** and **"do not follow everything, review and validate first"** → validated docs, the issue #1 fix and the status-script fix only, on branch `research/nationwide-scope` (2026-09-27) | [D-045](DECISIONS.md), [D-046](DECISIONS.md) |
| A31 | Storage with 12 GB free and no backup? | **Lean + local backup** (2026-09-27) | [D-046](DECISIONS.md) |
| A32 | Agencies (Q3) for national endpoints? | **Collect quietly, ask before public** (2026-09-27) | [D-046](DECISIONS.md) |
| A33 | Keep `Research_Thailand.md` in the public repo? | **Keep, with a validation banner** (2026-09-27) | [KI-404](../KNOWN_ISSUES.md) |
| A34 | Thai egress for DWR/RID in a prototype? | **Use the VPN for now**; a reliable egress before public (2026-09-27) | [D-046](DECISIONS.md) |
| A35 | How to use the 262 BMA road sensors? | **Map layer + point-check evidence** (2026-09-27) | [D-045](DECISIONS.md) |
| A36 | Owner steps | **Fix the GISTDA key; apply for the Google Flood API** (2026-09-27). GISTDA: the owner sent the API docs; the agent fixed our outdated path/header, the key works ✅ (KI-510). Google: open | [OWNER_ACTIONS](../OWNER_ACTIONS.md) |
| A37 | Q18 (bot challenge) | Bot Fight Mode off (owner, 2026-09-26 17:33 UTC); removed from the open list 2026-09-27 | [D-035](DECISIONS.md) |
| A48 | BMA history from HII: how much? | **1 year, hourly** (2026-09-27) | [D-054](DECISIONS.md) |
| A49 | How to judge the canal factor at a pin? | **Nearest gauges first** (2026-09-27) | [D-054](DECISIONS.md) |
| A50 | 48 h line where unproven? | **Show, honestly labelled** (range, no direction) (2026-09-27) | [D-055](DECISIONS.md) |
| A51 | Scope / release | **All, then deploy** (2026-09-27); station types: BMA gauges keep BMA's own thresholds (D-038) and an agency tag | [D-054](DECISIONS.md), [D-055](DECISIONS.md) |
| A46 | Q32: build network STAR + rain? | **"continue"** (2026-09-27) → built, validated on 3 windows + out of sample, released v0.8.0 | [D-052](DECISIONS.md) |
| A47 | Q29: local database backup? | **"no backup for now"** (2026-09-27): risk accepted by the owner; re-ask if data volume or feedback grows (KI-511) | [D-046](DECISIONS.md) |
| A38 | 12/24 h → 24/48 h? | **12 + 24 h; 48 h only where skilled** (2026-09-27) | [D-050](DECISIONS.md) |
| A39 | Wording when no fall is forecast | **"No sign of falling yet"**, never "stable for 48 h" (2026-09-27) | [D-050](DECISIONS.md) |
| A40 | HII's official forecast | **Prove it first**; research whether our own model can be improved (2026-09-27) → archived + scored; experiments in the research note | [D-050](DECISIONS.md) |
| A41 | Should the model use forecast rain? | Asked by the owner; measured: **yes** (research §3b) — next model | [D-050](DECISIONS.md) |
| A42 | STAR / SSN / k-NN / GTWR / ST-GNN? | Tested/assessed; **network STAR + rain next**; others kept for the national phase (owner: "keep the results") | [research 2026-09-27](../../research/2026-09-27_forecast_48h.md) |
| A43 | Issue #3 disclaimers | **Everything into ⓘ** (2026-09-27) | [D-051](DECISIONS.md) |
| A44 | Issue #3 district line / dot colours | **Reverse geocode if fast** (0.15–0.23 s, filled in after render); **dots follow the confidence gate** | [D-051](DECISIONS.md) |
| A45 | Issue #2 / release | **Button → popup**; **full bundle, deploy** (2026-09-27) | [D-051](DECISIONS.md) |
| A22 | Q24: BMA khlong data via the People's Party relay? | **Use and show it**, credit BMA and the relay (2026-09-26) | [D-031](DECISIONS.md) |
| A23 | Q27: Who is the app for in the next two weeks? | **Bangkok residents** (2026-09-26) | D-031, D-033 |
| A24 | Q26: Default list region? | **Bangkok, this week**; revisit 2026-10-03 (2026-09-26) | [D-033](DECISIONS.md) |
| A25 | Q17: A Thai machine as an SSH SOCKS exit for BMA? | **No** (2026-09-26): BMA only via the relay | [D-031](DECISIONS.md) |
| A26 | Q25: Integrate the BMA road-flood artifact? | Owner asked for advice; answer: **link only** (static hand-made snapshot, approximate positions, private sensor host) (2026-09-26) | [APPROACH §3.7](../APPROACH_AND_METHODS.md) |
| A1 | How to treat research of uncertain validity | Validate claim by claim, don't blanket-quarantine (2026-09-26) | [D-003](DECISIONS.md) |
| A2 | Priority for the first weeks | Archive-first, strict phases (2026-09-26) | [D-002](DECISIONS.md) |
| A3 | How far to go with the folder reorganisation | Also scaffold code folders (2026-09-26) | [D-006](DECISIONS.md) |
| A4 | Infrastructure status | VPS + tunnel live; app not deployed (2026-09-26) | [ARCHITECTURE §1](../ARCHITECTURE.md) |
| A5 | Should space and time be considered in calculations and models? | Yes, explicitly (2026-09-26) | [D-008](DECISIONS.md) |
| A6 | Q1 (VPS details) | There is only this single server (2026-09-26) | [D-013](DECISIONS.md) |
| A7 | Q3 (permissions from agencies) | Don't wait; find alternatives (proxy/VPN/scripts) (2026-09-26) | [D-014](DECISIONS.md), [D-016](DECISIONS.md) |
| A8 | Q13 (interim public page) | Yes, build everything in parallel and ship now (2026-09-26) | [D-012](DECISIONS.md) |
| A9 | Q14 (Thai collector node) | The owner added an OpenVPN (VPN Gate, Thailand) config (2026-09-26) | [D-016](DECISIONS.md) |
| A10 | Q2 (what the domain serves; tunnel config) | Main domain is now `flood.autobahn.bot`; new tunnel token supplied (2026-09-26) | [D-017](DECISIONS.md) |
| A11 | Can users give feedback on predictions? | Yes: collect privately and feed evaluation and review (2026-09-26) | [D-020](DECISIONS.md) |
| A12 | How to answer a pin with no station? | An evidence card, no interpolated level (2026-09-26) | [D-021](DECISIONS.md) |
| A13 | How to use Cloudflare AI safely? | Background triage only; the site never depends on it (2026-09-26) | [D-022](DECISIONS.md) |
| A14 | Q5 (v1 area) | Whole Bangkok Metropolitan Region + the lower Chao Phraya, and show every station (2026-09-26) | [D-023](DECISIONS.md), [D-024](DECISIONS.md) |
| A15 | Q15a (tunnel rights on the API token) | Fixed by the owner; verified 11:15 UTC | [KI-504](../KNOWN_ISSUES.md) |
| A16 | Q20 (old tunnel `ecd8a7b9…`) | Deleted by the owner; verified 11:15 UTC | [KI-504](../KNOWN_ISSUES.md) |
| A17 | Release cadence / version on screen | Versioned releases with the version in the UI (2026-09-26) | [D-025](DECISIONS.md) |
| A18 | Q1, Q3, Q13, Q14 | Answered earlier as A6–A9 (single server; don't wait for agencies; ship now; OpenVPN added). Removed from the open list on 2026-09-26 | D-012…D-016 |
| A19 | Q10 (visibility & license) | Repository made public (2026-09-26); open source MIT License applied by owner request (2026-09-27) | [D-028](DECISIONS.md), [D-043](DECISIONS.md) |
| A20 | Q15b / Q16 (R2 off-site backups) | Owner decided to keep R2 disabled; telemetry and DB remain local to VPS disk (2026-09-26) | [D-029](DECISIONS.md) |
| A21 | Q21 / Q23 (AI provider switch) | Switch to GLM (Zhipu AI `glm-4-flash`) for feedback triage; `.env` prepared for GLM key (2026-09-26) | [D-030](DECISIONS.md) |

