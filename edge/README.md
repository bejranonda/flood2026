# `edge/` — Cloudflare edge configuration

> **Status:** empty scaffold. The Cloudflare Tunnel is live: `flood.autobahn.bot` (main, D-017) and `flood.bejranonda.com` (alias) are proxied CNAMEs to tunnel `d62b426d…`. `cloudflared` runs in `docker-compose.yml` (`--url http://app:3000`, no remote ingress rules). Zone security settings (the `autobahn.bot` bot challenge, [KI-506](../docs/KNOWN_ISSUES.md)) are managed in the dashboard. Most of this folder is built in **Phases 3–4**.

## Scope
- Cache rules for the public API: short TTL (1–5 min) plus `stale-while-revalidate`, so traffic at the flood peak doesn't reach the VPS.
- Cloudflare Pages project settings for [`web/`](../web/README.md).
- An optional Worker, **only** as a caching layer in front of **our own** API. It must not scrape or proxy government sites around their access controls ([GUIDELINES §5](../docs/GUIDELINES.md)).
- R2 bucket and lifecycle notes for the raw archive replica and database backups.

Never commit secrets here. Tokens belong in `.env` or in Cloudflare's own secret storage.
