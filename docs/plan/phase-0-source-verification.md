# Phase 0 — Source research and verification

> **Status:** 🟡 in progress. The dev-host probes were done on 2026-09-26 ([VALIDATION](../../research/VALIDATION_2026-09-26.md)). **The VPS tests and the report are still to do.**
> **Gate G0:** the owner approves the recommended source set → Phase 1 collectors start immediately.

## Goal
For every candidate source, know from the **production VPS**: whether it works, how to call it, what it returns (datum, units, timezone), how often it updates, how far back its history goes, and on what terms it may be used. Deliverables: [SOURCES.md](../SOURCES.md) completed in the brief's format, and a recommended v1 source set.

## Inputs
[SOURCES.md](../SOURCES.md) · [VALIDATION_2026-09-26.md](../../research/VALIDATION_2026-09-26.md) · [validation script](../../research/validation/validate_research_claims.py) · [sources_survey.md](../../research/sources_survey.md) · [KNOWN_ISSUES §1–2](../KNOWN_ISSUES.md)

## Tasks

### A. Environment
- [ ] Confirm the production VPS: region, specs, disk, OS, Docker, egress IP ([OPEN_QUESTIONS](OPEN_QUESTIONS.md))
- [ ] Clone the repo on the VPS; run `python3 research/validation/validate_research_claims.py` **there** and record the results in SOURCES.md (the "VPS-tested" column)

### B. HII ThaiWater (P1)
- [x] `waterlevel_load` and `rain_24h` work without a key (dev host) — *repeat on the VPS*
- [x] Capture the XHR calls behind the chart pages: `getGraphFirst/{CODE}` (30 days, 10 min), `POST getGraph` (ranges, CSRF token), `queryStation`
- [ ] Find out **how far back** `getGraph` and `waterlevel_graph` go (loop over 30-day windows until empty; note the limits)
- [ ] Pull `queryStation` and the full station list; filter to the 9 target provinces; build the draft station inventory (code, numeric id, name, lat/lon, `min_bank`, `ground_level`, agency, river)
- [ ] Measure the update cadence per agency (HII 10 min; RID hourly?), payload sizes and timings from the VPS
- [ ] Record the sentinel values and QC quirks (`999999`, stale stations) → [KI-206](../KNOWN_ISSUES.md)
- [ ] Email HII (info_thaiwater@hii.or.th) about permission to archive and redistribute; ask about the exchange-standard API

### C. RID (P1)
- [ ] Find a machine-readable source for **C.29A Bang Sai**, Memorial Bridge / Pak Khlong Talat (**resolve C.4 vs C.22**) and dam releases / diversions ([KI-109](../KNOWN_ISSUES.md))
- [ ] Check the station lists (`water.rid.go.th/hyd/…`) and the `wmsc.rid.go.th` data pages
- [ ] Resolve the C.13 bank level (17.21 / 15.77 / HII 16.34)

### D. Tide (P1)
- [ ] Find the **current** Navy tide-table URL by hand (the old one returns 404; the site has a bot challenge) and download the 2026 tables for Fort Phra Chulachomklao, Bangkok Bar and Bangkok Port
- [ ] Find the per-station **LLW → MSL offsets** ([KI-201](../KNOWN_ISSUES.md))
- [x] Feasibility of our own harmonic fit on HII tidal stations: CPY015, 30 days, 4 constituents → 92 % of variance explained (interim)

### E. BMA (P2)
- [ ] From the VPS (and, if blocked, from a Thai IP): probe `dds.bangkok.go.th`, `weather.bangkok.go.th`; capture the XHR calls, station list, datum per station, and flow and pump station pages
- [ ] Ask BMA DDS for access or permission

### F. Weather, satellite, crowd, terrain (P1–P3)
- [x] Open-Meteo forecast, ensemble, flood and elevation work without a key
- [ ] Decide the NWP models and ensemble members to archive; check the terms (non-commercial) ([KI-106](../KNOWN_ISSUES.md))
- [ ] Owner registers TMD (uid/ukey) and GISTDA; create a Copernicus GFM account and draw AOIs for Bangkok and Ayutthaya/Pathum Thani
- [x] Traffy public API works (`publicapi.traffy.in.th`) — decide on privacy-safe use and ask BMA/NECTEC ([KI-107](../KNOWN_ISSUES.md))
- [ ] Ask GISTDA, BMA and RTSD whether any survey or LiDAR elevation data is available

### G. Report
- [ ] Complete SOURCES.md (every row VPS-tested) and the station inventory
- [ ] Write the Phase 0 report: recommended source set, gaps, risks, permissions status → **stop for G0**

## Exit criteria (G0)
- Every P1 source is tested from the VPS, with archived sample payloads as fixtures.
- The recommended v1 source set and station inventory are approved by the owner.
- Permission requests have been sent (replies may still be pending).

## Open questions for this phase
See [OPEN_QUESTIONS](OPEN_QUESTIONS.md) Q1–Q5.
