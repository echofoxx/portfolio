# Release Notes

## v0.6.0 — Premium Enterprise UX and Dashboard Modernization

### Changed

- Rebranded the application shell and login experience for JSJ6 Enterprise Portfolio Management.
- Introduced a premium high-contrast dark default theme and a complete light alternate theme using shared design tokens.
- Added the requested top navigation and reorganized the left navigation for faster portfolio, quick-access, and administration workflows.
- Rebuilt Portfolio Overview with six KPIs, portfolio health, investment category distribution, recent decisions, assigned work, and a portfolio-at-a-glance table.
- Standardized control heights, action alignment, field sizing, grid behavior, card geometry, table rendering, drawer layout, and responsive breakpoints across the application.
- Removed the legacy War Room route and interface. Its source capabilities remain accessible in Portfolio Overview, Decisions, Risks & Dependencies, Portfolio Reviews, Status Reporting, Scenarios, and Reports & Analytics.

### Validation

- Python and JavaScript static validation pass.
- All Jinja templates compile.
- Automated tests cover the JSJ6 application shell, dashboard content, requested navigation, dark-theme default, light-theme support, and removal of the legacy route.

## v0.5.0 — Portfolio Governance and Enterprise Integration

### Added — platform administration

- Create and update local demonstration users with multiple roles, division scope, active status, and sensitive-record access.
- Register acting-role delegations with delegator, delegate, roles, organization scope, effective dates, rationale, and audit evidence.
- Prevent an active administrator from disabling their own account.
- Expand the Administration workspace with user, organization, delegation, runtime, and security-configuration views.

### Added — portfolio review forum

- Create enterprise or division portfolio reviews with period, chair, participants, agenda, summary, and decisions required.
- Add review items for projects and other governed records with recommendation, rationale, owner, and status.
- Record a review outcome as linked Decision and Action records.
- Complete the review and retain searchable, auditable meeting evidence.

### Added — integration governance and ProjectOS dry run

- Register integration connections and record type, base URL, mode, authentication type, enabled state, health, and configuration metadata.
- Maintain field-ownership rules identifying authoritative system, allowed writers, and conflict policy.
- Generate a canonical ProjectOS project/task/milestone payload and store a dry-run synchronization result without contacting an external endpoint.
- Show recent synchronization attempts, payload evidence, result details, status, attempts, and operator.

### Added — resource and financial workflows

- Submit role- and skill-based resource requests with hours, period, project, organization, priority, rationale, requester, and approver.
- Approve or decline resource requests with resolution and audit evidence.
- Append commitment, obligation, expenditure, forecast-adjustment, and other transaction records to project financial baselines.
- Preserve stable transaction identifiers, source system, reference, date, amount, notes, and creator.

### Added — non-destructive scenario planning

- Create enterprise or division what-if scenarios with baseline date and assumptions.
- Propose supported changes to project, capacity, and financial fields without changing authoritative records.
- Calculate and store baseline-versus-scenario metrics and explanations.
- Separate scenario approval from application.
- Apply only approved changes and record before/after audit evidence for each affected record.

### Added — data-quality and operations command centers

- Run deterministic data-quality scans and persist detected or refreshed issues.
- Assign issue owners and due dates, record dispositions, and resolve issues.
- Generate source-grounded report packs for an organization and reporting period.
- Approve report packs and retain section metrics, narrative, approval metadata, and job-history evidence.
- Persist data-quality and report-generation job runs for operator visibility.

### Search and traceability

- Global search now includes portfolio reviews, scenarios, data-quality issues, report packs, and resource requests while retaining server-side access filtering.
- Updated the 307-row RTM with conservative v0.5.0 design, module, test, acceptance, UAT, and release references.
- Current status: 91 Implemented, 56 Partially implemented, 111 Planned, 27 Requires integration, 12 Requires policy or governance decision, and 10 Deferred.

### Validation

- 57 automated tests passed.
- 83% application-code coverage.
- 44 Jinja templates compiled.
- Clean migration through `0005_portfolio_governance_v050` passed.
- An actual v0.4.0 database upgraded and reseeded without loss of 25 users, 20 demands, 17 projects, 80 tasks, or 307 RTM records.
- Authenticated HTTP smoke checks returned HTTP 200 for Executive, Portfolio Reviews, Scenarios, Integrations, Resources, Financials, Data Quality, Operations, and Administration.
- Docker runtime validation remains required on the target host because a Docker daemon is unavailable in the artifact environment.

### Important boundaries

- The ProjectOS operation is a canonical-contract dry run, not a live external synchronization.
- Microsoft 365 and SharePoint connections are registry entries only until credentials, network access, approved APIs, and field mappings are configured in the target environment.
- Delegation records are governed and auditable, but delegated roles are not yet automatically injected into every authorization decision.
- Job history is persistent, but v0.5.0 does not include an external durable scheduler or distributed worker.
- Resource and financial features remain planning and evidence registers, not authoritative workforce or accounting systems.

## v0.4.0 — Execution and Roadmap Expansion

See the packaged v0.4.0 upgrade guide and repository history for prior release details.
