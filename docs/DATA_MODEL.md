# Canonical Data Model

![Canonical domains](diagrams/data-model.svg)

## Implemented relational core

The MVP schema implements the records required for the usable vertical slices:

- Organization and User
- Mission and Core Function
- Demand and Demand Revision
- Assessment
- Portfolio and Project
- Task and Milestone
- RAID Item and Dependency
- Decision and Action
- Resource Capacity
- Financial Record and Benefit
- Notification and Audit Event
- Requirement Traceability
- Import Batch and Import Row
- Saved View and Metric Definition

All primary business records use UUIDs. Operational records also use stable human-readable identifiers such as `DMD-26-001`, `PRJ-26-001`, `TSK-26-0001`, `RAID-26-001`, `DEP-26-001`, and `DEC-26-001`.

## Metadata pattern

Implemented entities carry relevant combinations of:

- UUID primary key;
- human-readable identifier;
- created and updated timestamp;
- version/revision;
- source system and source record;
- organization, mission, sponsor, owner, or manager;
- sensitivity or access scope;
- audit before/after evidence.

The full enterprise model in the requirements includes additional normalized entities. Some are represented in the MVP as fields or JSON collections to keep the first vertical slices transactional and usable. They should be normalized when their workflows are implemented.

## Domain mapping

| Required enterprise concept | MVP representation | Next normalization |
|---|---|---|
| Strategy, objective, key result, mandate, capability, customer, outcome, measure | Mission/CoreFunction plus mission outcome and measure JSON | dedicated records and many-to-many alignment |
| Team, position, skill, proficiency, vacancy | User and ResourceCapacity role/skill rows | workforce module and authoritative connector |
| Intake responses and conditional form schema | Demand fields | configurable form/version/question tables |
| Assessment criteria and score | configured Python weights plus Assessment JSON | database-configured models and criterion versions |
| Program, product/service, value stream, roadmap, baseline | Portfolio/Project fields | portfolio taxonomy and baseline tables |
| Workstream, WBS item, board column, deliverable, schedule baseline, status report | Task/Project/Milestone fields | full execution schema and baseline/version tables |
| Risk, assumption, issue, roadblock, control, evidence, lesson | polymorphic RaidItem plus Action | normalized assurance subtypes and evidence records |
| Funding source, cost, commitment, actual, forecast, value increment, ROI | FinancialRecord and Benefit | multi-year investment ledger and benefit baseline |
| Source system, interface, event, reconciliation, data quality | service contracts and audit/import metadata | persistent integration governance tables |

## Data integrity

- UUID primary keys prevent cross-environment collision.
- human identifiers are unique.
- a demand can convert to only one project.
- foreign keys connect mission, organization, user, demand, project, and portfolio records.
- a saved-view name is unique per user.
- state transitions and field completeness are enforced at the service/route layer.
- import updates match by stable Human ID.

Production should add database-level check constraints for health/status enumerations, stronger temporal constraints, optimistic concurrency enforcement, retention markers, and immutable event identifiers.
