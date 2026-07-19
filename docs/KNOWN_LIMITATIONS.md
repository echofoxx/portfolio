# Known Limitations — v0.8.3.1

## v0.8.3.1 boundaries

- The Linked Map Index height correction has automated implementation and route coverage; final cross-browser visual acceptance remains a target-host responsibility.
- All v0.8.3 functional boundaries below remain unchanged.

## v0.8.3 boundaries

- The v0.8.3 map is marker-based. Country choropleth, COCOM AOR boundaries, fiscal-quarter scrubbing, heat/density, saved geographic views, and briefing export are Phase 2 capabilities.
- Map costs are approval-stage estimates, not authoritative actual expenditures.
- Report compliance uses completed, approved, report-required travel and a linked request/report relationship. It does not certify report quality, records disposition, or action completion.
- City coordinates and aliases are locally governed planning references. Unmapped values are shown, but a steward correction UI and per-country geometry registry are not included.
- Direct gestures have automated implementation/route coverage; formal target-browser, touchscreen, Section 508, and assistive-technology certification remain deployment/UAT responsibilities.
- Themes persist in local browser storage and are individual preferences, not centrally managed branding policy.

## v0.8.2 boundaries

- Regional travel lenses normalize the current governed region labels into leadership-friendly rollups. They are presentation lenses, not authoritative geopolitical, combatant-command, or country-taxonomy classifications.
- Zoom and fit operate on the locally packaged world geometry. The application intentionally does not load external tiles, geocoding, routing, or traveler-location services.
- Low-zoom clusters reduce overlap using a deterministic display grid. They are visual summaries, not analytical geospatial clusters.
- Map URLs persist region and measure presentation state. Server-side travel authorization and source filters remain the governing data boundary.
- Formal conference-room browser, 200% zoom/reflow, assistive-technology, Docker Compose, performance, and signed leader UAT remain required on the target environment.

## Prior v0.8.1 boundaries

## v0.8.1 boundaries

- RAID and dependency tables are optimized for the project workspace. The separate enterprise RAID register retains its broader, horizontally scrollable data table because it carries additional portfolio-wide columns.
- Gantt task labels are responsive, but the actual time track remains a contained horizontal schedule surface on narrow devices so dates and bar geometry are not distorted.
- Investment Flow is role-scoped planning and transaction evidence, not an authoritative accounting statement or financial-system reconciliation.
- Dashboard Compact, Standard, and Wide sizes are governed layout tokens. Arbitrary pixel sizing and shared team layouts remain excluded.
- v0.8.1 was fully regression-tested in the application runtime, but Docker daemon and formal target-browser visual validation remain deployment/UAT responsibilities in this environment.

## v0.8.0 boundaries

- Dashboard personalization uses ordered smart-grid placement and compact/standard/wide sizing; it is not an unconstrained pixel canvas and does not support shared team layouts in this release.
- Project promotion is a portfolio-governance decision. It does not itself obligate funds, authorize hiring, certify resources, or synchronize an external project system.
- Resource import/export is Admin-only CSV seeding/correction with explicit preview and commit. It is not an authoritative workforce, billet, timekeeping, HR, or contractor feed.
- Blueprint structures are versioned in code/seed data; a no-code blueprint designer and separate template approval lifecycle are not included.
- Breadcrumbs describe the current hierarchy and provide linked return paths. They do not preserve unsaved form state or act as a browser-session replay history.
- Focused pages replace primary create workflows, but small contextual decisions and board configuration actions remain in their governing record page where losing context would be counterproductive.
- Supplied division banners are optimized derivatives; source-master asset governance, image rights, and formal content-owner approval remain external responsibilities.

## Deployment and authorization

- Docker Compose could not be launched in the artifact environment because a Docker daemon is unavailable. Target-host startup, reverse-proxy, browser, restart-persistence, and backup/restore validation remain required.
- The application is not RMF-authorized, production-authorized, CAC-enabled, PIV-enabled, or connected to an enterprise identity provider.
- Local demonstration authentication and synthetic data are development capabilities only.
- Acting-role delegations are stored, scoped, dated, and audited, but v0.5.0 does not yet inject delegated roles into every authorization decision. Administrators must treat the registry as governance evidence rather than a complete temporary-access engine.
- Rate limiting is process-local. Multiple production replicas require an approved shared rate-limit store.

## Integration depth

- The ProjectOS connector is a canonical-payload mock/dry run. It does not authenticate to, read from, or write to a live ProjectOS instance.
- Microsoft 365 and SharePoint entries are disabled registry records. Microsoft Graph mail/calendar, SharePoint List/library, Teams, Power BI, Advana/WDP, ServiceNow, Jira, Azure DevOps, financial, workforce, records, and identity adapters remain integration work.
- External retries, durable queues, dead-letter handling, scheduled synchronization, credential vault integration, reconciliation assignment, and conflict-resolution UI require a target enterprise environment.
- Field-ownership rules are operational governance data; they do not yet block every possible external write because no live external writers are enabled.

## Portfolio reviews

- Review agendas, recommendations, decisions, and actions are operational. Calendar invitations, electronic signatures, formal meeting-minute approval, document-package versioning, and Outlook/Teams integration remain planned.
- Review items support governed record references but do not yet provide automated agenda optimization or comprehensive meeting transcription.

## Resources and financials

- Resource requests are role/skill/hour planning records, not authoritative billets, personnel assignments, labor calendars, timekeeping, or contractor data.
- Financial transactions are planning/evidence entries, not official commitments, obligations, expenditures, disbursements, accounting postings, or reconciliation with a financial system.
- Multi-year profiles, appropriations controls, labor-rate protection, EAC methods, cost-account structures, and formal funds-control rules remain planned or integration-dependent.

## Scenarios

- Scenarios support a controlled set of project, resource-capacity, and financial fields. They do not yet simulate dependency propagation, resource leveling, schedule critical-path changes, benefit probability, risk Monte Carlo analysis, or portfolio optimization.
- Apply is governed and audited but is not an enterprise electronic approval/signature workflow.
- A scenario should be recalculated if authoritative source records change materially before approval or application; automatic staleness invalidation is not yet implemented.

## Data quality and operations

- Data-quality scans use deterministic application rules. Rule authoring, version approval, threshold configuration, lineage to enterprise data catalogs, and federated quality monitoring need expansion.
- Report packs are source-grounded snapshots with editable narrative and approval. Scheduled distribution, immutable signed archives, server-generated PDF, SharePoint publication, and recurring delivery are not included.
- Job runs are persistent evidence, but there is no external durable scheduler, distributed worker, automatic retry daemon, or high-availability queue.

## Existing execution limitations

- Critical path remains a basic finish-to-start calculation without calendars, lag/lead, resource leveling, constraints, probabilistic risk, or portfolio critical path.
- Gantt remains a review/edit companion rather than a full drag-reschedule engine.
- Office documents download rather than render in-browser; local file controls are not malware scanning, DLP, content disarm/reconstruction, or records disposition.
- Search does not index attachment contents and is not semantic or federated search.

## Nonfunctional evidence

- Formal WCAG 2.2 AA/Section 508 certification, approved-browser certification, load testing, 99.9% availability evidence, recovery exercise, penetration testing, SAST/DAST, container scanning, and RMF control evidence are not included.
- New v0.5.0 screenshots should be captured on the target Docker host; the artifact environment cannot reliably capture authenticated local browser views.
- AI remains intentionally deferred until source authority, access, lineage, quality, evaluation, audit, and human-review controls are established.

## v0.7.0 Division Briefing & Review boundaries

- Presentation mode is browser-based; it does not integrate with conference-room systems or provide offline briefing packages.
- The approved briefing snapshot is an application governance record, not a cryptographic signature or immutable external records archive.
- Review change requests track the requested correction and disposition but do not automatically write arbitrary fields to authoritative records.
- Calendar invitations, transcripts, recording, email digests, and external document publication require future Microsoft 365/SharePoint or other approved adapters.
- Standard briefing sections are code-governed in v0.7.0; a configurable template authoring and approval lifecycle remains planned.
- Formal WCAG 2.2 AA certification, target-host browser testing, performance testing, and signed user acceptance remain required.

- Standard division briefings exclude records marked Restricted, Sensitive, or Limited Distribution; those records must be reviewed in a separately approved restricted forum. A dedicated restricted-briefing workflow is not included in v0.7.0.

## v0.7.5 Division Experience boundaries

- Division portfolio JSON and CSV exports are implemented, but bulk import in v0.7.5 is intentionally limited to governed division-profile content.
- Profile publishing is permission-controlled and audited; a separate author-review-approve content workflow is not included.
- CID, C3OD2, and AID branch structures remain blank where the supplied material did not provide an authoritative branch outline.
- Banner assets are optimized WebP derivatives. Asset-library versioning, image-rights workflow, and source-master management are outside the application.
- Full-screen presentation uses the browser Fullscreen API and must be accepted on target conference-room browsers and display systems.
- Smooth loading and reduced-motion behavior are implemented, but formal WCAG 2.2 AA certification remains required.
- Export packages are not cryptographically signed and do not replace an approved records-management repository.

## v0.7.6 Travel & Engagement Outcomes boundaries

- Travel cost fields are estimates captured during approval; they are not official commitments, obligations, expenditures, disbursements, vouchers, or reconciled actuals.
- The supplied Travel Request workbook represents approved records. Pending, canceled, and disapproved dashboard totals shown in the reference PDF cannot be reconstructed from that workbook alone and are not fabricated.
- The local dashboard uses destination summaries and stored text. Live geocoding, external maps, network calls, and authoritative country/location reference data require an approved integration.
- Report/request matching uses deterministic similarity evidence and conservative thresholds. Ambiguous reports remain in reconciliation until an authorized reviewer confirms a source request.
- Text-based sensitivity detection is a safeguard. Authorized classification, CUI marking, dissemination, foreign-disclosure, retention, and records-management decisions remain external governance responsibilities.
- Report outcome extraction creates review candidates; it does not autonomously assign work or alter authoritative project/demand records.
- Approval steps are extensible, but the supplied spreadsheet does not include full approval-chain fields. Detailed approval data is shown only where available from the supplied dashboard evidence.
- Notifications are in-app. Scheduled reminders, escalations, email/Teams delivery, and durable background execution require the planned worker and approved collaboration connectors.
- CSV/JSON exports are point-in-time data products and are not cryptographically signed records packages.

## v0.7.7 visual-intelligence boundaries

- The travel map uses a locally maintained reference registry rather than a live authoritative geospatial source. Unmapped and ambiguous values require data-steward review.
- Markers represent aggregate city-level destination activity; the application does not model traveler routes, origin points, precise traveler positions, or live travel status.
- The Investment Flow Sankey conserves approved planning budget into actual-to-date capped to approved and unspent approved. It is not an authoritative accounting, obligation, expenditure, or cash-flow statement.
- Advanced visuals provide accessible alternatives and keyboard behavior, but formal WCAG 2.2 AA certification and target-browser assistive-technology testing remain required.
- Very large future portfolios may require server-side aggregation thresholds or progressive rendering beyond the current reference dataset.


## v0.7.9

- Guidance, onboarding, role-focus compaction, navigation-group state, and the telemetry queue persist per browser (localStorage), not per server-side user profile. Clearing browser storage resets them.
- Telemetry is collection-only: events accumulate in a local 200-event ring buffer with no reporting UI; connect approved analytics tooling via `window.jsj6Telemetry.drain()`.
- Snooze/delegate on Action Center items, notification digests and preferences, resource heatmaps, role-specific table column presets, and the expanded Migration Center are deferred to the roadmap.
- Packaged release screenshots were not regenerated in the build environment (no headless browser available). To capture: run the stack, sign in as each demonstration role, and capture `/dashboard`, `/my-work`, `/travel?view=requests`, and the Help drawer at 1440px and 390px widths into `docs/screenshots/`.
