# Phase 4 — Deployment and operations (VPS core + Cloudflare edge)

> **Status:** ⏳. Parts are already live (VPS, tunnel). The minimum infrastructure for collectors is built in Phase 1. **Gate G4:** load test, redeploy drill and alert test passed.

## Goal
Survive flood-peak traffic and component failures. Redeploy the whole stack on a new VPS from backups in **under 1 hour**.

## Inputs
[ARCHITECTURE §4–§6, §9](../ARCHITECTURE.md) · [KI-501, KI-502](../KNOWN_ISSUES.md) · scaffold: [infra](../../infra/README.md), [edge](../../edge/README.md)

## Tasks
- [ ] Bring the live tunnel config into the repo as a template (no credentials)
- [ ] Edge cache rules: public API 1–5 min + `stale-while-revalidate`; Pages for `web/`
- [ ] Firewall: only SSH (key-only); every service on 127.0.0.1; `CORS_ORIGIN` set to the production domain
- [ ] Monitoring and alerts: uptime, collector failures, stale data per source, disk usage, backup success, **forecast skill drift and coverage**
- [ ] Load test through the edge (simulate a flood-peak spike)
- [ ] Redeploy runbook + drill (target < 1 h); restore drill from R2
- [ ] README: setup, data-flow diagram, adding a source or station (already in [ARCHITECTURE §8](../ARCHITECTURE.md))
- [ ] Operations handbook: who is on call during a flood ([OPEN_QUESTIONS](OPEN_QUESTIONS.md) Q12) → **stop for G4**

## Exit criteria (G4)
The load test is served mostly from the edge with the VPS stable. The redeploy drill takes under 1 hour. The alerts fire and reach the operator.
