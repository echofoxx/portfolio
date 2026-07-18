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

### Editing a submitted demand

Open the demand detail page and select **Edit Demand**. The link appears only when the current user and lifecycle stage permit direct changes.

- Requesters and sponsors can edit Draft, Submitted, and Clarification Required records.
- PMO, Division Portfolio Manager, Enterprise Portfolio Owner, and Administrator roles can also edit eligible Triage records.
- Enter a clear change summary before saving.
- Saving increments the version, adds a revision-history entry, records an audit event, and notifies the current owner, requester, and sponsor as applicable.
- For Clarification Required records, use **Validate & Resubmit** after addressing the requested information.
- Once Assessment begins, direct editing is locked. Return the work through a governed clarification or change decision rather than silently changing the evaluated baseline.

The form uses the version that was displayed when the page opened. When another user has already saved a newer version, the application rejects the older submission and asks the user to review the current record.

## Project Manager

Open **Projects** and select a project. Tabs include:

- Overview and status update;
- WBS/task list;
- Kanban;
- Milestones;
- RAID and dependencies;
- Decisions and actions;
- Financials and benefits.

Update owner-reported health, progress, and narrative. Create tasks with title, description, priority, owner, due date, estimated effort, initial notes, and board column. Move cards across Kanban columns. Select **Open details** on a Kanban card, or **Details** on a WBS row, to open the task workspace without leaving the project. Add milestones and RAID records. The executive and division roll-ups use the same canonical project records.

### Task workspace

The task drawer contains:

- description and acceptance criteria;
- priority, status, board column, owner, and contributors;
- start, due, and baseline dates;
- estimated and actual effort and percent complete;
- tags, persistent working notes, and acceptance evidence;
- checklist;
- incoming and outgoing task relationships;
- attachments and evidence;
- comments and mentions;
- linked requirements and recent audit activity.

Use **Open Full Record** for the standalone task record and complete audit context. Material changes are audited.

### Task files and evidence

In **Files and Evidence**, select a permitted file and optionally add a description and sensitivity. Supported extensions are PDF, DOCX, XLSX, PPTX, CSV, TXT, MD, JSON, PNG, JPG, and JPEG. The server validates the configured size limit, safe filename, extension, and selected binary signatures before writing the file to the storage volume. Each file shows uploader, timestamp, size, media type, description, and SHA-256 hash.

Download requires current project access. Removal is limited to authorized users and should follow applicable records policy. Version history, preview, malware scanning, and formal disposition remain future capabilities.

### WBS and relationships

Use the WBS row controls to move an item, adjust its indent level, or copy the current due date into the baseline due date. In the task drawer, add finish-to-start, start-to-start, finish-to-finish, or related task links. v0.3.1 records these relationships but does not calculate critical path or all schedule violations.

## Team Member

Use **My Work** for assigned tasks, actions, and owned RAID records. Open the parent project, then open the task drawer or the shareable full task page to update authorized task details, notes, checklist, files, evidence, and comments. Use `@username` in a task comment to create an in-app mention notification. Team-member edit access remains within organization and project scope.

## Resource Manager

Use **Resources** for role and skill capacity, planned allocation, actual effort, utilization, minimum recurring-function coverage, over-allocation, coverage warnings, and the v0.5.0 resource-request register. Authorized users can request a role/skill/hour profile for an organization and project, then Resource Managers can approve or decline it with a documented resolution. Named personnel calendars, vacancies, contractors, and authoritative skill records remain roadmap/integration capabilities.

## Financial Manager

Use **Financials** for approved budget, actual cost, forecast, variance, minimum viable funding, full requirement, cost category, underfunded indicators, and the v0.5.0 transaction register. Authorized Financial Managers can add commitment, obligation, expenditure, forecast-adjustment, and related evidence with a date, source, reference, amount, and notes. These entries are planning/evidence records; authoritative accounting and rates still require a governed financial connector.

## Benefits Owner

Use **Benefits** to review target, realized value, unit, status, owner, and review date. The MVP demonstrates a benefit register; advanced benefit baselines, attribution, and value-increment forecasting are roadmap work.

## Data Steward

Use **Strategy & Mission**, **Requirements RTM**, **Excel Imports**, metric metadata, and data-quality/stale indicators. Maintain traceability fields and ensure source, owner, refresh, limitations, and lineage remain clear.

## Security / Privacy Reviewer

Review restricted records, audit evidence, security notes, integration ownership rules, and proposed field-level access decisions. The MVP is a reference implementation, not an authorization package.

## Auditor

The auditor can view governance and material audit history but cannot change business data. Audit rows include actor, entity type, entity identifier, action, timestamp, and before/after JSON when applicable.

## Platform Administrator

Use **Administration** to create and update local demonstration users, assign multiple roles and division scope, control active/sensitive-access state, inspect organizations, and register acting-role delegations. Delegations are dated and audited, but v0.5.0 does not yet apply delegated roles automatically to every authorization check. Production user lifecycle, identity federation, access certification, policy configuration, and secrets management require hardening and enterprise integration.

## Search, filters, exports, and saved views

Global search covers accessible demands, projects, tasks, task comments, milestones, RAID records, dependencies, decisions, missions, core functions, organizations, and RTM requirements. Enter at least two characters for type-ahead suggestions. Use the arrow keys and Enter to select a suggestion, or submit the complete query to open grouped results. Exact stable identifiers rank first.

Command/Ctrl+K focuses the search input, but v0.3.1 intentionally does not show a visible `K` marker in the field. Search honors role, division, project, and sensitive-record restrictions. Filter index pages by query, status, health, or division. Save the current route and query as a named view. CSV exports are generated from the user’s scoped query rather than bypassing permissions.

## Notifications

Notifications link back to authoritative records and contain minimal information. Read all notifications from the notification center. Digest scheduling and Microsoft Graph delivery are future adapter capabilities.

## Interface themes and navigation

Use the theme control in the top command bar to switch between **Premium Enterprise Dark** and **Premium Enterprise Light**. Dark is the first-run default. Both themes retain the same navigation, data, forms, tables, drill-downs, and responsive behavior.

Use **Portfolio Overview** for enterprise KPIs and drill-downs. Open **Decisions**, **Risks & Dependencies**, **Portfolio Reviews**, **Scenarios**, or an individual project for authoritative leadership and governance records. Project and demand workspaces include a **Bidirectional Traceability** section. Select a requirement ID to view its source text, implementation classification, design/module reference, test evidence, release, and links back to operational application pages.


## Common v0.3.1 troubleshooting

- **Task drawer does not open:** v0.3.1 task controls are links. The browser should open the full task page even when the drawer JavaScript is unavailable. Confirm the page reports v0.3.1 and that `/static/app.js?v=0.3.1` loads. Rebuild the container if an older unversioned bundle is still served.
- **File rejected:** verify the extension, configured `MAX_UPLOAD_MB`, and that a PDF/image/Office file has a valid binary signature. Renaming an unrelated file to an allowed extension will not pass.
- **Search result missing:** confirm the record is within your role/division/project scope and use the stable identifier. Restricted records are intentionally excluded.
- **Visible K remains after upgrade:** clear site data or hard refresh. The v0.3.1 template contains no visible keyboard marker and versions its static assets.

## v0.4.0 execution management

### Configure a project board

1. Open a project and select **Board Configuration**.
2. Edit a column name, WIP limit, entry criteria, or exit criteria and select **Save**.
3. Use the up/down controls to change workflow order.
4. Move all tasks out of a column before archiving it.
5. Create a new state with **Create Column**.

WIP limits are enforced by the server on new tasks, edits, and drag-and-drop moves. A WIP limit of `0` means no limit.

### Manage WBS and schedule

- Open **WBS** to review hierarchical numbering, parent relationships, baseline/current dates, planned/actual effort, and critical-path indicators.
- Use Move Up, Move Down, Indent, Outdent, and Baseline actions. Each action is audited.
- Open **Schedule** to review the Gantt window, baseline markers, dependency duration, schedule integrity, and the calculated finish-to-start critical path.
- Add task relationships in the task workspace. Circular finish-to-start chains are rejected.

### Use task notes and file history

- Open any Kanban card or WBS Details link. JavaScript opens the drawer; the same link is a full-page fallback.
- Update working notes and enter a change summary before saving. Each changed note creates a complete revision snapshot.
- Upload XLSX, DOCX, PPTX, PDF, PNG, JPG/JPEG, Markdown, TXT, CSV, or JSON.
- Select **Upload New Version** on a current file to preserve the logical file history.
- Preview supported PDF/image/text formats in a new tab.
- Remove a file to move it into history. Project Managers and Administrators can restore it.

### Create a project from a blueprint

1. Open **Blueprints**.
2. Review the blueprint tasks, milestones, and board states.
3. Enter title, lead division, mission, sponsor, project manager, and start date.
4. Select **Create Project**.
5. Review the generated WBS and tailor details through governed edits.

The created project retains the source template code and version. A later template version does not silently modify the project.

### Prepare and approve a status report

1. Open a project and select **Status Reporting**.
2. Enter reporting period, health, completion, accomplishments, planned work, decisions required, risks/dependencies, and executive summary.
3. Save a draft or submit for approval.
4. Open a Draft or Returned report to update and resubmit it.
5. A PMO, Division Portfolio Manager, Senior Leader, Enterprise Portfolio Owner, or Administrator approves a Submitted report.
6. The approved report becomes the governed reporting baseline available from the project status workspace and reporting views.

### Review the portfolio roadmap

Open **Roadmaps**, filter by division or status, and select any project bar or label to drill into the authoritative project record.

## v0.5.0 portfolio governance and integration workflows

### Conduct a portfolio review

1. Open **Portfolio Reviews** and create a review with scope, reporting period, chair, participants, summary, and decisions required.
2. Open the review and add agenda/recommendation items linked to a project or other governed record.
3. Record the recommendation and rationale.
4. Select **Record Decision** for a resolved item. The application creates linked Decision and Action records and preserves the relationship on the review item.
5. Complete the review when open items have been addressed.

Enterprise roles can see enterprise reviews; division roles see their permitted division and unscoped enterprise review records.

### Run a ProjectOS dry run

1. Open **Integrations** as an Administrator, PMO user, or Data Steward.
2. Review the ProjectOS Mock connection and the field-ownership rules.
3. Select an accessible project and run synchronization with Dry Run enabled.
4. Inspect the canonical project/task/milestone payload, record counts, mock remote identifier, conflicts, status, and operator evidence.

No external ProjectOS endpoint is contacted in v0.5.0. Do not switch a connection to External and represent it as live until credentials, endpoint, idempotency, conflict, retry, and reconciliation controls are configured and tested.

### Create and compare a scenario

1. Open **Scenarios** and create a what-if scenario with scope, baseline date, and assumptions.
2. Add proposed changes to supported Project, Resource Capacity, or Financial Record fields.
3. Select **Calculate**. Baseline and scenario metrics are stored without altering live records.
4. Review explanations and impact levels.
5. An authorized portfolio leader may approve the scenario. Approval still does not change live records.
6. Select **Apply** only after governance approval. Each applied change generates before/after audit evidence.

### Manage data-quality issues

1. Open **Data Quality** and run a scan.
2. Review severity, rule, source record, organization, owner, due date, and status.
3. Assign an owner and due date.
4. Record a disposition and mark the issue Resolved when the authoritative source has been corrected or an approved exception exists.

### Generate a report pack

1. Open **Operations**.
2. Choose pack name/type, organization scope, and period.
3. Generate the pack from current source records.
4. Review section metrics and the source-grounded narrative.
5. An authorized leader may approve the pack.

Report packs are application snapshots. Scheduled distribution, signed PDF packages, SharePoint publication, and immutable records archiving are future capabilities.

### Search the new governance records

Global search now includes Portfolio Reviews, Scenarios, Data Quality, Report Packs, and Resource Requests. Search results remain filtered by role, organization scope, project access, and sensitive-record permissions.
