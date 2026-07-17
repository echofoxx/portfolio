# User Guide by Role

## Common navigation

The left navigation groups decision support, delivery, personal work, and governance. The top command bar provides global search, current identity and role, light/dark mode, and sign out. Most index pages support filters and saved views. Blue identifiers and titles navigate to authoritative detail records.

Health vocabulary is governed: **On Track, At Risk, Off Track, Blocked, Completed, On Hold, Not Reported**. Project records distinguish owner-reported health, calculated health, and an authorized override with rationale.

## DDC5I Senior Leader

Use **Executive** for exceptions rather than totals. Begin with:

- projects at risk;
- decisions required;
- capacity utilization;
- forecast variance;
- stale status records;
- critical milestones;
- cross-division dependencies.

Select a source record to inspect the owning division, project manager, affected mission, milestones, RAID, decisions, finance, and benefits. Open **Metric governance** to see definition, formula, owner, source, refresh, threshold, and limitation metadata.

Use **Decisions** for the authoritative decision log. On a demand at Gate 4, record rationale, evidence, participants, conditions, caveats, implications, review date, and any required capacity tradeoff. Each condition line becomes a follow-up action.

## Enterprise Portfolio Owner / PMO

Use **Demand** to manage the single funnel. The requester creates a draft or submits a complete intake. The PMO can:

1. move Submitted work to Triage;
2. request clarification and identify pending information;
3. advance complete work to Assessment;
4. compare candidates in Assessments;
5. move assessed work to portfolio recommendation and leadership decision;
6. convert approved work to execution.

Use **Projects**, **Risks & Dependencies**, **Resources**, **Financials**, and **Benefits** for portfolio review. Use **Excel Imports** to preview a workbook before commit. Use **Requirements RTM** and **Audit** for governance evidence.

## Division Chief / Division Portfolio Manager

The role is scoped to its division unless an enterprise role is also assigned. Open **Divisions** or the direct division page for mission, core functions, project inventory, demand stages, milestones, RAID, capacity, budget, dependencies, and required leadership action.

Division users cannot read another division’s inaccessible records by changing the URL. Restricted records also require explicit sensitive access.

## Demand Sponsor / Requester

Open **Demand → New Demand**. Required submission-readiness content includes:

- title and work category;
- lead division and sponsor;
- mission alignment;
- purpose;
- problem or opportunity;
- measurable desired end state.

Add beneficiaries, required date, urgency, consequence of inaction, scope, deliverables, assumptions, dependencies, skills, ROM cost, benefits, confidence, and sensitivity. Save a draft while incomplete. Submitted records show current owner, next action, pending information, target decision date, and disposition.

## Assessor

Open a demand in Assessment. Score each criterion from 0 to 5:

| Criterion | Weight |
|---|---:|
| Mission criticality | 25% |
| Strategic alignment | 20% |
| Operational impact | 15% |
| Urgency and time sensitivity | 10% |
| Risk reduction | 10% |
| Readiness / interoperability contribution | 10% |
| Feasibility and resource confidence | 5% |
| Expected value / ROI | 5% |

Provide evidence and rationale plus confidence. Multiple assessments are averaged and population variance is displayed to expose disagreement. Use **Assessments** to compare candidates with score, cost, risk, confidence, and division context.

## Approval Authority

Open a demand in Awaiting Decision. Available dispositions include Approve, Decline, Defer, Pilot, Merge, Re-scope, Perform as core work, Outsource, and Request additional analysis. Approval beyond available capacity requires a documented stop, delay, reduction, de-scope, or approved capacity increase.

## Project Manager

Open **Projects** and select a project. Tabs include:

- Overview and status update;
- WBS/task list;
- Kanban;
- Milestones;
- RAID and dependencies;
- Decisions and actions;
- Financials and benefits.

Update owner-reported health, progress, and narrative. Create tasks with owner, dates, effort, sequence, baseline due date, and board column. Move cards across Kanban columns. Add milestones and RAID records. The executive and division roll-ups use the same canonical project records.

## Team Member

Use **My Work** for assigned tasks, actions, and owned RAID records. Open the parent project before changing work. Team-member edit access remains within organization and project scope.

## Resource Manager

Use **Resources** for role and skill capacity, planned allocation, actual effort, utilization, minimum recurring-function coverage, over-allocation, and coverage warnings. Named personnel calendars, vacancies, contractors, and authoritative skill records are roadmap/integration capabilities.

## Financial Manager

Use **Financials** for approved budget, actual cost, forecast, variance, minimum viable funding, full requirement, cost category, and underfunded indicators. General dashboards do not expose sensitive rate notes. Authoritative commitments, obligations, expenditures, and rates require a governed financial connector.

## Benefits Owner

Use **Benefits** to review target, realized value, unit, status, owner, and review date. The MVP demonstrates a benefit register; advanced benefit baselines, attribution, and value-increment forecasting are roadmap work.

## Data Steward

Use **Strategy & Mission**, **Requirements RTM**, **Excel Imports**, metric metadata, and data-quality/stale indicators. Maintain traceability fields and ensure source, owner, refresh, limitations, and lineage remain clear.

## Security / Privacy Reviewer

Review restricted records, audit evidence, security notes, integration ownership rules, and proposed field-level access decisions. The MVP is a reference implementation, not an authorization package.

## Auditor

The auditor can view governance and material audit history but cannot change business data. Audit rows include actor, entity type, entity identifier, action, timestamp, and before/after JSON when applicable.

## Platform Administrator

Use **Administration** to inspect users, roles, division assignments, counts, and integration status. Administration in this MVP is intentionally read-oriented; production user lifecycle, identity federation, policy configuration, and secrets management require hardening and enterprise integration.

## Search, filters, exports, and saved views

Global search covers accessible demand and project identifiers/titles and, for authorized roles, RTM entries. Filter index pages by query, status, health, or division. Save the current route and query as a named view. CSV exports are generated from the user’s scoped query rather than bypassing permissions.

## Notifications

Notifications link back to authoritative records and contain minimal information. Read all notifications from the notification center. Digest scheduling and Microsoft Graph delivery are future adapter capabilities.
