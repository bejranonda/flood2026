# OPEN_QUESTIONS.md — Questions for the owner

> The brief asks the team to keep asking until the picture is clear. These are the questions that change what gets built.
> When one is answered, move it to "Answered" with the date, and record any resulting decision in [DECISIONS.md](DECISIONS.md).

## Open
> **Steps, costs and verification for each item are in [../OWNER_ACTIONS.md](../OWNER_ACTIONS.md)** (D-026). Check status with `python3 scripts/owner_status.py`. Last verified 2026-09-26 ~11:20 UTC.

| # | Question | Why it matters | Priority |
|---|---|---|---|
| **Q18** | **`autobahn.bot` bot challenge** (`cf-mitigated: challenge`, evidence points to Bot Fight Mode, which WAF rules can't skip): turn Bot Fight Mode off for the zone, upgrade to Pro (Super Bot Fight Mode + Skip), or keep sharing the alias? Then: may we 301 the old domain (`REDIRECT_LEGACY_HOST=1`, built and tested, off)? ([KI-506](../KNOWN_ISSUES.md)) | LINE/Facebook previews, monitors, API users | **1** |
| **Q15b / Q16** | **Enable R2** (the API says "Please enable R2 through the Cloudflare Dashboard"), create a bucket and an R2 S3 token, and put `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_ENDPOINT` in `.env`. Free tier covers ~2 months, then well under $1/month | Off-site backup; today everything is on one disk ([KI-504](../KNOWN_ISSUES.md)) | **2** |
| Q21 | A Cloudflare token limited to **Workers AI** as `CF_AI_TOKEN` (the worker uses the general token today) | Least privilege ([KI-508](../KNOWN_ISSUES.md)) | 3 |
| RID | **Gate coordinates** (`code,lat,lon`) for the 15 unplaced and 14 approximate stations | Exact map positions, point checks ([KI-207](../KNOWN_ISSUES.md)) | 4 |
| Q10 | **Repository license.** Visibility was answered by the owner's action (**public**, 2026-09-26; scanned, [D-028](DECISIONS.md)); there is still **no LICENSE**, so all rights are reserved | Legal; whether others may reuse the code | 5 |
| Q19 | Who reads **feedback notes**, how often; a review page or SQL? (first real report arrived 10:17 UTC) | Feedback is only useful if someone acts on it ([D-020](DECISIONS.md)) | — |
| Q17 | A **Thai server/home connection** as an SSH SOCKS exit for BMA sites? | BMA khlong data; the VPN relay is flaky | — |
| Q22 | Workers AI for **Traffy text labelling** or **voice reports**? ($5/month Workers Paid if over the free quota) | Cost vs value ([APPROACH §3.6](../APPROACH_AND_METHODS.md)) | — |
| Q7 | **Notifications:** LINE or Web Push? | Scope; whether user data must be stored | — |
| Q8 | Dates in the **Buddhist era (พ.ศ.)**? | UI | — |
| Q11 | **Budget/retention** for R2 and the raw archive | Sizing | — |
| Q12 | **Who is on call** during a flood? | Alert routing | — |
| Q3 | Permission mails to **HII / BMA / Traffy**? (optional since D-014) | Public redistribution | — |
| Q4 | **TMD / GISTDA / Copernicus GFM / NASA** keys? | Optional P2 sources | — |
| Q6 | Will the app ever be **commercial**? | Open-Meteo and FABDEM are non-commercial ([KI-106](../KNOWN_ISSUES.md)) | — |
| Q9 | **Frontend framework** preference? | The plain-JS app is enough so far | — |

## Answered
| # | Question | Answer (date) | Decision |
|---|---|---|---|
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
| A19 | Q10 (visibility) | The owner made the repository public (seen 2026-09-26 15:20 UTC) | [D-028](DECISIONS.md) |
