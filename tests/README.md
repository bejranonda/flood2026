# `tests/` — automated tests

> **Status:** empty scaffold. Tests are added alongside the code in each phase.

## Priorities
- **Datum conversion tests** (highest priority). Known bank levels and LLW/MSL/gauge-zero offsets per station must round-trip correctly. A 1 m datum error flips the answer ([KNOWLEDGE.md §2](../docs/KNOWLEDGE.md)).
- **Collector parser tests** against **recorded raw payloads** from the archive (fixtures), never against live endpoints.
- **Timezone tests.** Source times without a timezone are parsed as +07:00 and stored as UTC.
- **QC tests** for spikes, flatlines, gaps and clock errors. Data is flagged, never dropped.
- **Model tests.** The polder storage balance conserves mass (closure error < 3 %). Monotonic constraints hold. The backtest harness never leaks future data.
