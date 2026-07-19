# Canonical Data Model

![Canonical domains](diagrams/data-model.svg)

## Implemented relational core

The MVP schema implements the records required for the usable vertical slices:

- Organization and User
- Mission and Core Function
- Demand and Demand Revision
- Assessment
- Portfolio and Project
- Task, Task Comment, Task Attachment, Task Relationship, and Milestone
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
| Workstream, WBS item, board column, deliverable, schedule baseline, status report | Task/Project/Milestone fields plus TaskRelationship | full execution schema, calendars, dependency validation and baseline/version tables |
| Risk, assumption, issue, roadblock, control, evidence, lesson | polymorphic RaidItem plus Action; task acceptance evidence and TaskAttachment | normalized assurance subtypes, evidence records, repository versions and retention |
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


## v0.3.0 task execution entities

### Task

In addition to the stable task ID and project foreign key, the task record includes description/acceptance criteria, priority, owner, contributor UUIDs, status, board column, sequence, indent level, start/due/baseline dates, planned/actual effort, percent complete, tags, checklist JSON, notes, and acceptance evidence.

### TaskComment

Stores the task, author, body, mention UUIDs, resolved flag, and timestamps. Mention notifications are separate Notification records so delivery state does not alter the comment.

### TaskAttachment

Stores task/project linkage, original and stored names, storage key, media type, extension, size, SHA-256, uploader, sensitivity, description, and timestamps. File bytes remain in the storage adapter rather than in PostgreSQL.

### TaskRelationship

Stores source task, target task, relationship type, creator, and timestamps. v0.3.0 prevents duplicate/self links at the route/data-integrity layer; future schedule services should add lag/lead, calendars, critical path, and invalid-relationship analysis.

## v0.5.0 canonical entities

| Domain | Entities | Purpose |
|---|---|---|
| Delegation | `Delegation` | dated acting-role and organization-scope governance evidence |
| Integration | `IntegrationConnection`, `FieldOwnershipRuleRecord`, `SyncRun` | connection metadata, authoritative ownership, dry-run/live result evidence |
| Governance forum | `PortfolioReview`, `PortfolioReviewItem` | period-based review agenda, recommendation, decision/action linkage |
| Resource | `ResourceRequest` | role/skill/hour demand, period, priority, decision and resolution |
| Financial | `FinancialTransaction` | transaction-like planning/evidence entries linked to a financial baseline |
| Scenario | `Scenario`, `ScenarioChange`, `ScenarioResult` | non-destructive proposed values, comparison metrics, approval/apply status |
| Data quality | `DataQualityIssue` | rule finding, source record, severity, owner, due date, disposition, resolution |
| Operations/reporting | `ReportPack`, `JobRun` | source-grounded report snapshot and persistent operation evidence |

All new entities use UUID primary keys. Business-facing records use stable human IDs where appropriate (`REV`, `RRQ`, `FTX`, `SCN`, `DQI`, `RPT`). Existing audit events retain actor, entity, action, timestamp, client address, and before/after evidence.

## v0.7.0 division briefing entities

| Entity | Purpose |
|---|---|
| `BriefingSection` | standard division briefing section, narrative, owner, readiness, order, and source-summary evidence |
| `BriefingSnapshot` | one approved/frozen source and narrative payload per Portfolio Review |
| `ReviewQuestion` | assigned in-review question, priority, due date, response, and status |
| `ReviewChangeRequest` | governed request describing current/proposed values, rationale, owner, due date, disposition, and resolution |
| `ReviewNote` | time-stamped discussion, parking-lot, clarification, or observation note |

The `PortfolioReview` remains the lifecycle and scope anchor. Existing `Decision` and `Action` records remain authoritative for meeting outcomes. Briefing change requests intentionally do not provide a generic arbitrary-field mutation mechanism; accountable owners use the existing source-record workflow and document the result.

## v0.7.5 division profile entity

### `division_profiles`

One governed profile exists for each division organization.

| Field | Purpose |
|---|---|
| `org_id` | Stable one-to-one link to the existing organization record |
| `mission`, `vision` | Leadership-facing mission context |
| `focus_areas` | Ordered list of concise focus tags |
| `responsibilities` | Ordered list of core responsibilities |
| `branches` | Named organizational elements with focus descriptions |
| `initiatives` | Major initiatives, programs, or recurring work |
| `relationships` | External organization, role, and category records |
| `forums` | Forum name, division role, and purpose records |
| `doctrine` | Publication/standard, division role, and notes records |
| `banner_asset`, `banner_alt` | Managed asset reference and accessible alternative text |
| `focal_x`, `focal_y` | Responsive image focal point from 0–100 |
| `status` | Draft, Published, or Needs Review |
| `source_documents`, `source_notes` | Content lineage and stewardship notes |
| `last_reviewed_at`, `updated_by_id`, `updated_at` | Governance and audit-support metadata |

Migration `0007_division_experience_v075` creates the table and updates only organization display names. Organization codes and IDs remain unchanged.

## v0.7.6 travel and engagement entities

### TravelEngagement

Represents the reusable forum, exercise, conference, working group, site survey, or other external engagement. It carries a stable human ID, canonical title and location, normalized matching key, date range, lead division, cross-division indicator, source provenance, and raw source payload. Many traveler-level requests and trip reports may link to one engagement.

### TravelRequest

Represents one traveler-level approval-source record. Key fields include stable ID, external source ID, traveler, division, engagement, destination, determination, departure/return dates, estimated approval cost, funding, exemption category, purpose/ROI, impact if not accomplished, report-due date, sensitivity, source filename/row/record, import batch, raw payload, and timestamps.

### TravelApprovalStep

Stores a variable-length approval chain. Each step retains order, approver, role, determination, comments, determination date, and source provenance. This avoids hardcoding only Division Chief and DDS approval fields.

### TripReport

Stores the complete post-trip narrative: purpose/objectives, discussion, findings, recommendations, and DDC5I action items. It also retains division, traveler, event/destination/dates, sensitivity, version, review status, linked request/engagement, match status/confidence/rationale, human confirmation, source evidence, and timestamps.

### TripReportItem

Stores structured, reviewable outcome candidates extracted from the original narrative. Item types include Finding, Recommendation, Action, Risk, Decision, and Dependency. Promotion state and target entity identifiers provide an exact backlink without changing the authoritative narrative.

### TravelEntityLink

Provides a polymorphic, audited link from a travel request, engagement, report, or report item to a canonical project, demand, action, decision, RAID item, dependency, milestone, review, core function, or division record.

### Integrity and traceability

- Traveler-level estimated costs remain on `TravelRequest`; engagement totals are calculated, not duplicated.
- A report may be unmatched, suggested, needs reconciliation, or confirmed.
- Match confidence and rationale are retained even after confirmation.
- Source values are preserved in `raw_payload`; validation warnings do not silently rewrite source evidence.
- Independent sensitivity fields apply to requests and reports.
- Stable human IDs support user navigation; UUIDs support canonical internal links.


## v0.7.7 analytical projections

v0.7.7 introduces no new persistence tables or database migration. The new dashboard elements are governed, read-only projections over existing canonical records:

- **Geographic Footprint** resolves preserved travel destination text through a locally packaged alias-and-coordinate registry. The original request and report values remain authoritative; the resolved canonical place, coordinate, confidence, and mapped/unmapped state are presentation metadata only.
- **Investment Flow** derives a conserved flow from approved budget through financial category, owning division, project, actual cost to date, and unspent approved amount. It does not create ledger entries and must not be interpreted as an authoritative accounting or cash-disbursement statement.
- Travel trend, determination mix, outcome funnel, compliance, and engagement-impact views are calculated from `TravelRequest`, `TripReport`, `TripReportItem`, and `TravelEngagement` records at request time.
- Every visual projection retains drill-through to the contributing canonical records and applies the same server-side role, organization, and sensitivity scope as the underlying workspace.
