# `floodwatch.api` — FastAPI backend

> **Status:** empty scaffold. An internal read API may start in **Phase 1** (health, latest observations). The public endpoints come in **Phase 3** ([plan](../../../docs/plan/phase-3-web-app.md)).

## Responsibility
Serve JSON to the web app. The browser never calls government APIs directly ([GUIDELINES §1](../../../docs/GUIDELINES.md)).

## Rules
- Bind to `127.0.0.1:${PORT}`. Public traffic arrives only through the Cloudflare Tunnel ([ARCHITECTURE.md §5](../../../docs/ARCHITECTURE.md)).
- Every response carries the **observation time**, **data age**, **source attribution** and a `degraded` flag with a reason.
- Cache headers are designed for the Cloudflare edge: `Cache-Control: public, max-age=60..300, stale-while-revalidate`.
- Forecast payloads always include quantiles or intervals, the model level actually served (L0–L5), and the conditions they depend on (for example "no further heavy rain", "RID release plan X m³/s").

## Planned endpoints (draft)
`/health`, `/stations`, `/stations/{id}/observations`, `/stations/{id}/forecast`, `/near?lat=&lon=`, `/about/model-skill`.
