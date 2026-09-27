# research/ — research snapshots, validation and trust index

The files here are **research records** from 26 Sep 2026, produced with assistant-assisted research (claude.ai and Gemini). They are kept as written, apart from a validity banner at the top of each. The maintained, reconciled documentation lives in [`docs/`](../docs/README.md). When the two disagree, `docs/` wins.

**Every file was validated claim by claim** in [VALIDATION_2026-09-26.md](VALIDATION_2026-09-26.md). The checks used live endpoint calls, 30 days of observed HII data, and published sources. The checks can be re-run with [validation/validate_research_claims.py](validation/validate_research_claims.py).

## Validity levels
| Level | Meaning |
|---|---|
| 🟢 Reliable | Most testable claims confirmed; limits stated honestly. Main input to `docs/` |
| 🟠 Mixed | Contains useful, confirmed ideas **and** refuted or unverified claims. Use only the items marked ✅/💡 in the validation report |
| 🔴 Do not use | Mostly refuted, invented or against project rules; kept only as a record. Ideas may be reused after independent checks |

## Files
| File | Validity | Content | Useful parts adopted into |
|---|---|---|---|
| [sources_survey.md](sources_survey.md) | 🟢 | Source audit: HII public JSON, RID, BMA DDS, Navy tide, Open-Meteo (+GloFAS), TMD, GISTDA, Traffy, DEMs; v1 stations; schedule | [docs/SOURCES.md](../docs/SOURCES.md), [docs/KNOWLEDGE.md](../docs/KNOWLEDGE.md) |
| [methods_survey.md](methods_survey.md) | 🟢 | Regimes A–D, tide, rating curves, routing, LightGBM, conformal, recovery, depth at location, validation, literature | [docs/APPROACH_AND_METHODS.md](../docs/APPROACH_AND_METHODS.md) |
| [keyless_access.md](keyless_access.md) | 🟢 | Keyless sources vs optional free registrations (TMD, GISTDA), Copernicus GFM, NASA GPM | [docs/SOURCES.md](../docs/SOURCES.md) §7 |
| [API_noKey-1.md](API_noKey-1.md) | 🟠 | Keyless strategy matrix, Open-Meteo recipe, JS tide function, elevation lookup, Worker proxy | Open-Meteo usage ✅. The tide function ❌ (inverted against observations). See [validation §A](VALIDATION_2026-09-26.md) |
| [bangkok_flood_intelligence_data_sources.md](bangkok_flood_intelligence_data_sources.md) | 🟠 | Five-domain source audit, BMA assets, crowd sources, canonical JSON payload, harvester script | The domains, Traffy idea (working URL found), tunnel capacities, payload design 💡. Its HII/Traffy URLs ❌. See [validation §B](VALIDATION_2026-09-26.md) |
| [bangkok_flood_calculation_forecasting_engine.md](bangkok_flood_calculation_forecasting_engine.md) | 🟠 | Three Waters physics, surge, polder balance, street depth, T_dry, Python engine | Equations and UX bands 💡. Engine output and tide constants ❌. See [validation §C](VALIDATION_2026-09-26.md) |
| [Nationwide/Research_NATIONWIDE.md](Nationwide/Research_NATIONWIDE.md) | 🟢 | Scaling to all of Thailand: flood types F1–F8, data tiers, reservoirs, flash floods, Thai and international sources, rollout (2026-09-27) | [docs/APPROACH_AND_METHODS.md §19](../docs/APPROACH_AND_METHODS.md), [docs/SOURCES.md §2d](../docs/SOURCES.md), [D-044](../docs/plan/DECISIONS.md) |
| [Nationwide/Research_Thailand.md](Nationwide/Research_Thailand.md) | 🔴 | Zoning, SCS-CN / Muskingum-Cunge / HAND spec, ingestion code, UI ideas (2026-09-27) | Ideas only; its endpoints, numbers and HAND street depth are refuted or against the rules. See [validation §C](VALIDATION_2026-09-27_nationwide.md) |
| [VALIDATION_2026-09-27_nationwide.md](VALIDATION_2026-09-27_nationwide.md) | — | Live probes of 22 national/international endpoints, freshness, claim-by-claim verdicts | [docs/SOURCES.md](../docs/SOURCES.md), [docs/KNOWN_ISSUES.md](../docs/KNOWN_ISSUES.md) |
| [VALIDATION_2026-09-26.md](VALIDATION_2026-09-26.md) | — | Claim-by-claim verdicts with evidence; station metadata vs HII live; new findings | [docs/KNOWN_ISSUES.md](../docs/KNOWN_ISSUES.md), [docs/SOURCES.md](../docs/SOURCES.md) |
| [validation/](validation/validate_research_claims.py) | — | Scripts that re-run the endpoint probes and the tide check (`probe_nationwide_2026-09-27.py` for the national sources) | — |

## Adding research
1. Put new research in a new file named with the date (for example `2026-10-02_rid_telemetry.md`), with a validity banner at the top.
2. Validate its testable claims (live call, data or cited source) and add the verdicts to a validation report.
3. Carry only ✅/💡 items into `docs/`, in the same change.
