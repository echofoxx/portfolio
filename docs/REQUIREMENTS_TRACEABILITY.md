# Requirements Traceability Report

## Source and treatment

The attached DDC5I Requirements Traceability Matrix Draft 1.2 contains **307 requirements**, all marked Must. The MVP imports every row into `RequirementTrace`, makes the rows filterable in the Administration/Governance area, and exports the implementation baseline to `DDC5I_RTM_MVP_Status.csv`.

No claim is made that all requirements are implemented. Status was assigned conservatively based on a usable feature, module evidence, integration dependency, policy dependency, phase, and known limitation.

## Baseline summary

| Implementation status | Count | Meaning in this release |
|---|---:|---|
| Implemented | 84 | usable vertical slice exists in the MVP with design/module reference |
| Partially implemented | 40 | meaningful capability exists but required depth or configuration is incomplete |
| Planned | 131 | not implemented in the MVP; assigned to roadmap work |
| Requires integration | 30 | cannot be completed without an authoritative external system or connector |
| Requires policy or governance decision | 12 | technical implementation must wait for an approved operating/policy decision |
| Deferred | 10 | deliberately beyond the five-phase MVP scope or responsible-AI gate |
| **Total** | **307** | complete imported matrix |

## Phase distribution in source RTM

| Source phase | Count |
|---|---:|
| Phase 1 | 146 |
| Phase 2 | 49 |
| Phase 3 | 71 |
| Phase 4 | 31 |
| Phase 5 | 10 |

## Evidence fields

Each RTM record supports:

- requirement ID, domain, title, statement, priority, and phase;
- preliminary fit and accountable owner;
- verification method and source status;
- implementation status;
- design reference;
- module or API reference;
- test case;
- UAT result;
- release;
- acceptance notes;
- decision/comments.

## MVP requirement-ID groups

The usable MVP emphasizes these groups:

- `GOV-*` strategy, mission alignment, governance, decisions, roll-up;
- `ORG-*` organization, roles, accountability, lead/support scope;
- `DMD-*` governed intake and demand lifecycle;
- `ASM-*` assessment, prioritization, stage gates, approvals;
- `PFM-*` portfolio and recurring-function management;
- selected `PRJ-*` built-in execution management;
- selected `RES-*` role/skill capacity;
- selected `FIN-*` basic budget, actual, forecast, and underfunding;
- selected `COL-*` in-app notifications and traceable collaboration;
- selected `DSH-*` executive/division dashboards, reports, narrative, metric metadata;
- selected `DAT-*` Excel demand import/export, OpenAPI, lineage, IDs;
- selected `SEC-*`, `ADM-*`, `NFR-*`, and `IMP-*` security, audit, configuration, quality, operations, migration, and documentation.

## v0.3.1 evidence additions

- **DMD-008** links to the submitted-demand edit workflow, optimistic version check, revision history, audit evidence, notification behavior, and assessment-stage lock test.
- **PRJ-007** links to the task drawer, full-page fallback route, versioned local bundle, task workspace, and automated fallback-route test.
- Migration `0003_v031_reliability_hotfix` updates these evidence references in existing databases without modifying business-data schema.

## Verification evidence

Automated tests are linked at the suite level in the imported trace records. The suite covers primary workflow, status roll-up, drill-down route access, import validation, scoped access, auditor read-only behavior, scoring, workflow transitions, audit evidence, database uniqueness, comprehensive search, task workspace persistence, comments/mentions, checklist, task relationships, WBS actions, and secure task-file handling. Rows with automated release evidence record Automated test passed; organization-level UAT remains open until an authorized DDC5I user group executes and signs the acceptance checklist.

## How to update status

1. Sign in as `admin`, `pmo`, or an authorized data steward.
2. Open **Requirements RTM**.
3. Filter by ID, domain, phase, fit, or status.
4. Update only with evidence: design reference, module/API, test case, UAT result, release, notes.
5. Preserve rationale for Partially implemented, Requires integration, or governance-dependent status.
6. Export the updated report for release governance.

## Traceability artifacts

- JSON seed: `app/data/requirements.json`
- In-app RTM: `/requirements`
- CSV baseline: `docs/DDC5I_RTM_MVP_Status.csv`
- Tests: `tests/` and `e2e/`
- Architecture and module references: `docs/` and `app/`
- Roadmap linkage: `docs/ROADMAP.md`

## Acceptance caution

“Implemented” in this reference package means the capability can be demonstrated locally. It does not mean production authorization, enterprise integration acceptance, records approval, operational data certification, accessibility certification, or policy approval.


## v0.4.0 evidence additions

- **PRJ-003** links configurable board columns, WIP validation, criteria, ordering, archival, UI, and tests.
- **PRJ-004** links WBS hierarchy, sequencing, baselines, Gantt, cycle rejection, and basic critical-path evidence.
- **PRJ-008** links versioned task files, preview, integrity metadata, download evidence, soft deletion, and restoration.
- **PRJ-012** links versioned project blueprints, complete instantiation, and immutable project provenance.
- **PRJ-014** links project status-report lifecycle, approval, print view, notifications, audit, and governed reporting roll-up.
- Migration `0004_execution_roadmap_v040` applies those evidence references to upgraded installations while creating the supporting canonical records.

## v0.5.0 evidence additions

The v0.5.0 release updates conservative design, module, test, release, acceptance, and UAT references for administration, governance forums, integration ownership, resource/financial planning, scenarios, data quality, and report operations. Representative anchors include ORG-007, GOV-006, PFM-015, COL-010, DSH-015, ADM-005, DAT-003, DAT-010, DAT-016–019, RES-004, RES-012, FIN-002, FIN-007–009, FIN-013, and SCN-002–013.

Current 307-row classification:

| Status | Count |
|---|---:|
| Implemented | 91 |
| Partially implemented | 56 |
| Planned | 111 |
| Requires integration | 27 |
| Requires policy or governance decision | 12 |
| Deferred | 10 |
| **Total** | **307** |

A requirement is not marked Implemented merely because a database table or screen exists. Live ProjectOS, Microsoft 365, SharePoint, identity, workforce, and financial-system capabilities remain Partially implemented or Requires integration where the external authority, authentication, reconciliation, accreditation, or governance decision is absent.
