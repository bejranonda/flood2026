# `edge/` — Cloudflare edge configuration

> **Status:** empty scaffold. The Cloudflare Tunnel for `flood.bejranonda.com` is already live, but its configuration isn't in this repo yet ([OPEN_QUESTIONS.md](../docs/plan/OPEN_QUESTIONS.md)). Most of this folder is built in **Phases 3–4**.

## Scope
- Cache rules for the public API: short TTL (1–5 min) plus `stale-while-revalidate`, so traffic at the flood peak doesn't reach the VPS.
- Cloudflare Pages project settings for [`web/`](../web/README.md).
- An optional Worker, **only** as a caching layer in front of **our own** API. It must not scrape or proxy government sites around their access controls ([GUIDELINES §5](../docs/GUIDELINES.md)).
- R2 bucket and lifecycle notes for the raw archive replica and database backups.

Never commit secrets here. Tokens belong in `.env` or in Cloudflare's own secret storage.
