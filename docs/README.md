# docs/ — Documentation index

> Maintained documentation for BKK FloodWatch 2026. When `research/` and `docs/` disagree, **docs/ wins**.

## Reading order
1. [../README.md](../README.md): what the project is and its current status
2. [brief/first_prompt.md](brief/first_prompt.md): the original brief (the owner's words)
3. [plan/PLAN.md](plan/PLAN.md): roadmap, phase gates, where we are
4. [KNOWLEDGE.md](KNOWLEDGE.md): the hydrology and domain facts you need
5. [ARCHITECTURE.md](ARCHITECTURE.md): how the system fits together
6. [SOURCES.md](SOURCES.md): every data source, how to call it, and its test status
7. [APPROACH_AND_METHODS.md](APPROACH_AND_METHODS.md): the calculations and models, including the spatio-temporal framework
8. [GUIDELINES.md](GUIDELINES.md): rules for engineering, modelling, data ethics and UX
9. [KNOWN_ISSUES.md](KNOWN_ISSUES.md): limitations and workarounds (KI-IDs)

## Map
| File | Purpose | Update when… |
|---|---|---|
| [plan/PLAN.md](plan/PLAN.md) | Roadmap, gates G0–G4, risks | A phase starts or ends |
| [plan/phase-0 … phase-4](plan/) | Task checklists and exit criteria per phase | Tasks progress |
| [plan/DECISIONS.md](plan/DECISIONS.md) | Decision log (D-001…) | A decision is made or superseded |
| [plan/OPEN_QUESTIONS.md](plan/OPEN_QUESTIONS.md) | Questions for the owner | Asked or answered |
| [SOURCES.md](SOURCES.md) | Source registry (the brief's Phase 0 format) | A source is tested, changes or fails |
| [KNOWLEDGE.md](KNOWLEDGE.md) | Domain knowledge, stations, datums, contacts | A fact is learned or corrected |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | Pitfalls with status | Something breaks or is worked around |
| [APPROACH_AND_METHODS.md](APPROACH_AND_METHODS.md) | Methods (= the brief's `docs/METHODS.md`) | A method changes |
| [GUIDELINES.md](GUIDELINES.md) | Standards | A standard changes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, storage, security, repo layout | The architecture changes |

## Evidence markers used across the docs
| Mark | Meaning |
|---|---|
| ✅ | Confirmed: live call, observed data, or cited source |
| 🟡 | From careful research or documentation; not re-checked yet |
| ⚠️ | Unverified or indicative. Don't hard-code it; there's a task to verify it |
| 🔴 | Blocked or unavailable |
| 🔑 | Needs a key or registration |
| ❌ | Refuted |

Research validity (🟢 reliable / 🟠 mixed) is explained in [../research/README.md](../research/README.md).
