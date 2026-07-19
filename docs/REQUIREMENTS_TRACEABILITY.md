# Requirements Traceability Report

## Packaged baseline

The governed source baseline contains **307 requirements**. v0.7.5 added six division-experience requirements, v0.7.6 added twelve travel-and-engagement requirements, and v0.7.7 adds ten visual-intelligence requirements. The packaged application, in-app RTM, JSON source, and CSV status report therefore contain **335 rows**.

No claim is made that every source requirement is implemented. Status remains conservative and distinguishes usable implementation from partial capability, planned work, external integration, policy/governance dependency, and deliberate deferral.

## Status summary

| Implementation status | Count |
|---|---:|
| Implemented | 119 |
| Partially implemented | 56 |
| Planned | 111 |
| Requires integration | 27 |
| Requires policy or governance decision | 12 |
| Deferred | 10 |
| **Total** | **335** |

## Phase distribution

| Phase | Count |
|---|---:|
| Phase 1 | 174 |
| Phase 2 | 49 |
| Phase 3 | 71 |
| Phase 4 | 31 |
| Phase 5 | 10 |

## v0.7.7 requirements

| ID | Requirement | Evidence summary |
|---|---|---|
| `UX-077-001` | Simplified Briefings navigation | User-facing relabel with stable routes and records |
| `TRV-077-001` | Interactive geographic footprint | Local map, proportional markers, aggregate detail, drill-through |
| `TRV-077-002` | Governed location normalization | Alias registry, mapping coverage, unmapped stewardship |
| `TRV-077-003` | Map and Top Locations cross-filtering | Synchronized focus and stable location-filter URLs |
| `TRV-077-004` | Travel trend and determination analytics | Monthly cost/volume and division status mix |
| `TRV-077-005` | Outcome funnel and report compliance | Approved-to-promoted flow and division gaps |
| `FIN-077-001` | Portfolio Investment Flow Sankey | Category/division/project/outcome flow |
| `FIN-077-002` | Reconciled flow and drill-through | Conservation check, basis, financial/project links |
| `UX-077-002` | Accessible visual alternatives | Keyboard labels, table/list alternatives, source access |
| `SEC-077-001` | Local visualization assets | Same-origin assets, CSP compatibility, no external data transfer |

## v0.7.6 requirements

| ID | Requirement | Evidence summary |
|---|---|---|
| `TRV-076-001` | Controlled travel-request import | XLSX validation, preview, commit, provenance, tests |
| `TRV-076-002` | Controlled trip-report import | Full narrative retention, validation, preview, commit, tests |
| `TRV-076-003` | Matching and human reconciliation | Candidate score/rationale, auto-match threshold, confirm/clear/rematch |
| `TRV-076-004` | Dashboard and drill-through | Enterprise filters, KPIs, summaries, request/report/engagement routes |
| `TRV-076-005` | Engagement-level consolidation | Reusable engagement records and multi-traveler/division rollup |
| `TRV-076-006` | Promote report outcomes | Canonical Actions, RAID risks, Decisions, Dependencies, and backlinks |
| `TRV-076-007` | Division travel integration | Division travel metrics, reports, compliance, and source links |
| `TRV-076-008` | Briefing snapshot integration | Sixteenth section and immutable approved briefing payload |
| `TRV-076-009` | Provenance and audit evidence | Source file/row/system/record, raw payload, batch, audit history |
| `TRV-076-010` | Role and sensitivity enforcement | Enterprise/division scope, write authority, restricted-content checks |
| `TRV-076-011` | Data-quality controls | Date sequence, missing reports, unmatched reports |
| `TRV-076-012` | CSV export and linked portability | Travel CSV exports and division package integration |

## Evidence fields

Each traceability row can include requirement ID, domain, title, statement, priority, phase, fit, capability, accountable owner, verification method, source status, implementation status, design reference, module/API reference, test case, UAT result, release, acceptance notes, and decision/comments.

## Packaged evidence

- Machine-readable source: `app/data/requirements.json`
- CSV status report: `docs/DDC5I_RTM_MVP_Status.csv`
- In-app route: **Requirements RTM**
- Migration evidence: `migrations/versions/0008_travel_engagements_v076.py` (v0.7.7 is schema-compatible)
- Functional tests: `tests/test_v076.py` and `tests/test_v077.py`
- Build evidence: `docs/BUILD_VALIDATION.md` and `docs/TEST_RESULTS.md`


## v0.7.9 requirements

Ten v0.7.9 requirements (`UX-079-01` … `REL-079-10`) were appended to `DDC5I_RTM_MVP_Status.csv`, bringing the packaged traceability set from 335 to 345 rows. Each row links the requirement to its implementation files and its validating test in `tests/test_v079.py`. The nine stale pre-existing test expectations that were intentionally updated (asset version strings, the Outcome pipeline label, the inline world map, and the navigation/My Work redesign markers) are documented in `docs/RELEASE_NOTES.md` and `docs/UPGRADE_0.7.9.md` rather than suppressed.
