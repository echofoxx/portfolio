# Known Limitations — v0.5.0

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
