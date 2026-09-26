# OPEN_QUESTIONS.md — Questions for the owner

> The brief asks the team to keep asking until the picture is clear. These are the questions that change what gets built.
> When one is answered, move it to "Answered" with the date, and record any resulting decision in [DECISIONS.md](DECISIONS.md).

## Open

| # | Question | Why it matters | Blocks |
|---|---|---|---|
| Q1 | **Production VPS details:** provider, region (Singapore or Thailand?), vCPU/RAM/**disk**, OS, egress IP. Is it separate from this dev host (`HZ-Agent`, Germany, ~11 GB free, no `cloudflared`)? | Phase 0 tests must run on the VPS. BMA blocks the German host. Disk sizing for the archive | Phase 0 |
| Q2 | What does `flood.bejranonda.com` serve today, and where is the tunnel configured (dashboard or config file)? | README status; bringing the config into `infra/` | Phase 1/4 |
| Q3 | Who contacts **HII**, **BMA DDS** and **BMA/NECTEC (Traffy)** about permission and official feeds, ideally in Thai from a named person or organisation? | Public redistribution depends on it | Public launch |
| Q4 | Will you register **TMD** (uid/ukey), **GISTDA**, **Copernicus GFM** and **NASA Earthdata**? The keys go in `.env` on the VPS | P2 sources | Phase 1 (optional) |
| Q5 | Confirm the **v1 area**: Bangkok + Nonthaburi, Pathum Thani, Samut Prakan, Ayutthaya, Ang Thong, Sing Buri, Chai Nat, Nakhon Sawan? Any specific neighbourhoods to prioritise? | Station inventory and polder mapping effort | G0 |
| Q6 | Will the app ever be **commercial** (ads, sponsorship, paid tier)? | Open-Meteo and FABDEM are non-commercial ([KI-106](../KNOWN_ISSUES.md)) | Launch |
| Q7 | **Notifications:** LINE (OA / Messaging API) or Web Push, in v1 or later? | Scope, and whether user data needs storing | Phase 3 |
| Q8 | Dates in the **Buddhist era (พ.ศ.)** by default, or the Gregorian year? | UI | Phase 3 |
| Q9 | Any **frontend framework** preference (Next.js, SvelteKit, Astro/static, plain)? The recommendation is a small static-first build on Cloudflare Pages | Phase 3 setup | Phase 3 |
| Q10 | **Repository license** and visibility. The repo was published to GitHub as **private** on 2026-09-26 (D-011). Make it public? If so, which license (MIT, Apache-2.0, AGPL-3.0 …)? There is no LICENSE file yet | Legal, contributions, and whether third parties may reuse the code | Going public |
| Q11 | **Budget** for R2 storage and the VPS, and how long to keep the raw archive (default: forever)? | Sizing and retention | Phase 1 |
| Q12 | **Operations:** who is on call during a flood, and how many maintainers? | Alert routing, runbooks | Phase 4 |
| Q13 | During the **current event**, do you want an **interim "observed levels only" public page** before the forecasts pass G2? This would be an exception to D-002 | Possible new decision | — |
| Q14 | If BMA also blocks the VPS, may we run a **small collector on a Thai IP** (e.g. a Thai cloud provider or a home connection), after asking BMA? | BMA khlong coverage | Phase 1 |

## New (2026-09-26, after the tunnel and VPN work)
| # | Question | Why it matters |
|---|---|---|
| Q15 | **Cloudflare token:** which token did you add Tunnel + R2 permissions to? The one in `.env` gets "Not authorized" on the tunnel and 403 on R2. Please re-paste the updated token. | Managing the tunnel via API; R2 |
| Q16 | **R2 backups:** please create an R2 bucket and an **S3 API token** (Access Key ID + Secret) and put `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT`, `R2_BUCKET` in `.env`. | Off-site copy of the archive and database |
| Q17 | **Thai IP for BMA:** the VPN relay reaches `dds.bangkok.go.th`, but `weather.bangkok.go.th` still returns 403. Do you have a Thai server or home connection we can use as an SSH SOCKS exit (`ssh -N -D`)? | BMA khlong data |

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
