# CLAUDE.md — Working rules for AI agents in this repo

**Project:** BKK FloodWatch 2026. Thai-language water-level monitoring and forecasting for canals and rivers across Thailand (1,000+ gauges; it started in Bangkok during the 2026 flood, hence the name, D-073).
**Current state:** MVP live at https://flood.autobahn.bot (the only domain; flood.bejranonda.com just redirects there; single server, docker compose). **Start with [HANDOFF.md](HANDOFF.md)**, then [docs/plan/PLAN.md](docs/plan/PLAN.md).

## Before you do anything
1. Read [docs/README.md](docs/README.md) (index), [docs/plan/PLAN.md](docs/plan/PLAN.md) (phase and gates) and [docs/GUIDELINES.md](docs/GUIDELINES.md) (rules).
2. The owner's brief is [docs/brief/first_prompt.md](docs/brief/first_prompt.md). It asks for frank feedback and for questions whenever something is unclear. Unresolved questions go in [docs/plan/OPEN_QUESTIONS.md](docs/plan/OPEN_QUESTIONS.md).

## Before you ask the owner for anything
Read [docs/OWNER_ACTIONS.md](docs/OWNER_ACTIONS.md) and run `python3 scripts/owner_status.py`: the item may already be tracked or done. Add new needs there first (why, steps, verification). Secrets go only in `.env`; never print them (D-026). Private notes that stay off GitHub are in `private/NOTES.md` on the server (git-ignored): read them before contacting partners or agencies; never commit, quote or print them.

## Non-negotiables
- **Parallel workstreams (D-012, supersedes D-002):** keep the live site working; every change goes through the tests (`docker compose build worker`, then `docker compose run --rm --no-deps -v "$PWD/research:/app/research:ro" worker pytest -q`; the mount lets the research guard run) and a health check before redeploying.
- **Evidence rule:** never invent endpoints, field names, constants or data. Every claim in `docs/` needs evidence (a live call with date and host, observed data, or a citation), or a ⚠️ label. Sample outputs must come from running code (D-003).
- **Research is input, not truth:** validate claims before use, following [research/README.md](research/README.md). Endpoints listed as refuted in [docs/SOURCES.md §3](docs/SOURCES.md) must not be used.
- **Honest User-Agent; no bot-challenge solving, no evading blocks.** The owner's OpenVPN Thai egress (`vpn` sidecar) may be used for geo-blocked **public** pages only, never for credentials (D-014, D-016). Check owner statements against evidence too and report discrepancies (HANDOFF §2).
- Several sessions work on this repo: `git pull --ff-only`, read `git log` and check `git status` before editing. Another session's uncommitted work is tested and committed as its own commit, named as theirs, never folded into yours.
- **Datums and time:** everything is in m MSL (Ko Lak) and stored in UTC. Know each source's timezone convention (KI-201, KI-205).
- **Space and time are explicit:** station graph, polders, lags, issue time vs valid time (D-008, [APPROACH §2](docs/APPROACH_AND_METHODS.md)).
- **No secrets in git** (`.env`, `certs/`, `*.pem`). Don't read or print secret values.
- **Citizen messaging:** ranges, probabilities and conditions, never minute countdowns (D-005). Lead with cm to the bank; check the UI at 390 px; bump `?v=` on static files ([GUIDELINES §6](docs/GUIDELINES.md)).
- **No interpolated water surfaces over land** (D-019). **User feedback is private and never auto-applied** (D-020); never print or publish feedback notes. Point checks show categories and warnings, never a level at the pin (D-021). **AI never writes safety facts, and the site must work without it** (D-022): GLM writes every AI text the app shows — the ✨ card only when a visitor taps it (D-068), the national ticker in the worker (D-089) — and other models are for research only. **Show every station; hide misleading values with a note** (D-024). **Never mix water levels across agencies** (BMA vs HII differ 0.3–0.6 m, KI-217); never use BMA `critical` as a bank (KI-215); BMA gauges are judged by BMA's own warning/critical drainage levels (D-038). **Place-search queries are never logged or stored** (D-032). Releases: bump `__version__`, CHANGELOG, tag, GitHub release (D-025).
- **Judge model changes honestly** ([GUIDELINES §4](docs/GUIDELINES.md)): choose earlier, score later, confirm on a disjoint sample; the newest season counts; a gauge or dam is "made worse" only beyond chance (`floodwatch.model_gate`, D-107); the 7-day impact tab has its own test (§4.5).

## Where things go
Facts → KNOWLEDGE · pitfalls → KNOWN_ISSUES (KI-ID) · source tests → SOURCES · methods → APPROACH_AND_METHODS · decisions → plan/DECISIONS (D-ID) · owner questions → plan/OPEN_QUESTIONS · progress → plan/phase-*.md.

## Useful commands
- Research that calls Open-Meteo: `floodwatch.research_quota.get_json(url)` — 3,000 weighted calls a day shared by all research (D-108); in a container add `-v "$PWD/data/research:/data/research"`.
- Re-run the source validation: `python3 research/validation/validate_research_claims.py` (the result depends on the host country; this dev host is in Germany and is blocked by BMA; see KI-502).

## Git
Remote: `origin` = https://github.com/bejranonda/flood2026 (**PUBLIC** since 2026-09-26, open source under the **MIT License**, [D-043](docs/plan/DECISIONS.md)). Branch from `main` for changes and end commit messages with the attribution line the harness provides. **Everything committed is world-readable: no secrets, IP addresses, account ids, emails or feedback content in files or commit messages (D-028).** **Before any push, confirm nothing secret is staged** (`.env`, `certs/`, `*.pem` are ignored; keep it that way). Rewriting history or force-pushing needs the owner's explicit go-ahead.
