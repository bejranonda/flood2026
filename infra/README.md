# `infra/` — VPS deployment, tunnel, backups

> **Status:** empty scaffold. The minimum needed to run collectors and the database starts in **Phase 1**. Hardening and monitoring come in **Phase 4** ([plan](../docs/plan/phase-4-deployment-ops.md)).

## Planned contents
- `docker-compose.yml`: PostgreSQL + TimescaleDB, the collector scheduler, forecast jobs and the FastAPI backend. Every service binds to `127.0.0.1`.
- A `cloudflared` tunnel configuration template (no credentials).
- Backup scripts: a nightly `pg_dump` to R2, a weekly Parquet export, and a **tested restore runbook**.
- Monitoring: collector failure and stale-data alerts, disk usage, forecast skill drift.
- A redeploy runbook. Goal: the whole stack can be rebuilt on a new VPS from backups in **under one hour**.

The security baseline is in [ARCHITECTURE.md §5](../docs/ARCHITECTURE.md) (tunnel only, SSH by key only, no public web ports).
