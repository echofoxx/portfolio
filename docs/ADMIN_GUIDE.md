# Administrator Guide

## v0.8.0 administration

The current migration head is `0009_self_service_v080`. See `docs/UPGRADE_0.8.0.md` before upgrading an existing installation.

Administrators can open **Resources → Import / Export** to download the governed CSV template, export current capacity and request data, preview a correction/seed file, inspect every row, and explicitly commit valid changes. The importer matches an existing row by stable `record_id` or by the natural key `(division_code, role_name, skill, period)`. Invalid divisions, missing keys, duplicate natural keys, and invalid hour values remain errors and are not committed. Every batch and changed row retains import and audit evidence.

Administrators can also review local-project promotion requests, create either project governance type, and reset their own dashboard layout. Resource import remains Admin-only in v0.8.0.

## Responsibilities

The platform administrator owns local deployment configuration, migrations, backups, health monitoring, demonstration-user lifecycle, release installation, and coordination of security and integration decisions. The administrator does not become the business owner of portfolio data merely by holding technical privileges.

## Administration page

Sign in as `admin` and open **Administration** to inspect:

- user identities, roles, division scope, and sensitive-access flag;
- record counts;
- configured integration boundaries and unresolved authoritative-field decisions;
- local demonstration-authentication warning.

v0.5.0 includes local demonstration user create/update screens. Administrators can assign roles, division scope, sensitive-access state, and active status. These controls do not replace an approved identity-management system, account-provisioning workflow, access certification, or enterprise group/claim governance. Future enterprise identity should provision stable subject identifiers and approved role/scope claims through the authentication adapter.

## Configuration

Primary local configuration is through `.env`. Never commit `.env`. The checked-in `.env.example` contains placeholders only.

Required production changes include:

- replace `SECRET_KEY` and database password;
- set `ENVIRONMENT=production` for secure cookie behavior;
- disable demonstration authentication when an approved identity adapter exists;
- publish behind an approved TLS reverse proxy;
- restrict Mailpit and database networks;
- move secrets to an approved secrets manager;
- configure centralized logs, monitoring, backup retention, and alerting.

## Migrations

Migrations live in `migrations/versions`. Startup applies them automatically. The current v0.8.0 migration head is `0009_self_service_v080`. It adds project governance/promotion and dashboard-preference persistence and reconciles the legacy Front Office code without changing its stable organization ID. Earlier migration foundations remain intact. Before a production migration:

1. back up the database;
2. test upgrade against a restored copy;
3. review generated DDL;
4. document rollback or forward-fix steps;
5. schedule downtime when required;
6. validate record counts and key workflows after upgrade.

## Seed behavior

`python -m app.seed` is idempotent. On an existing installation it preserves user-created business data, ensures required v0.5.0 reference/demo records exist, and synchronizes packaged RTM implementation evidence. Use volume reset only for a deliberate demonstration reset.

## RTM administration

The RTM is seeded from `app/data/requirements.json`. In the UI, authorized administrators, PMO users, and data stewards can update:

- implementation status;
- design reference;
- module/API reference;
- test case;
- UAT result;
- release;
- acceptance notes;
- decision/comments.

Material RTM changes are audited. Do not bulk-mark requirements Implemented without evidence.

## Import administration

Only XLSX demand imports are committed in this MVP. Uploads are size-limited and parsed locally. Preview results must be reviewed before commit. Valid and warning rows may be committed; error rows remain excluded. Every committed row carries source-system and batch-row lineage.

## Backup and recovery

Use `scripts/backup.sh` and `scripts/restore.sh`. Test restore procedures on a separate environment. PostgreSQL backup does not include the file-storage volume. Versioned task attachments use that volume, so back it up and restore it in coordination with attachment metadata. A database-only restore may leave metadata pointing to missing files, while a volume-only restore may create unreferenced files.

## Health and logs

- `/health/live` confirms process liveness.
- `/health/ready` performs a database query.
- `docker compose ps` shows container health.
- `docker compose logs -f web db` shows application/startup/database logs.

The current logger is container stdout/stderr. Production requires structured log aggregation, correlation identifiers, retention, access controls, and alerting.

## Data-quality operations

Review stale project indicators, unaligned work, missing status, import errors, over-allocation, underfunding, low milestone confidence, open critical RAID, and RTM gaps. Assign the owning division or data steward rather than silently correcting authoritative business facts.

## Integration governance

Before registering a live adapter, populate field-ownership rules. A connector must not independently overwrite a field already owned by another source. Define retry and reconciliation thresholds, operator ownership, dead-letter handling, idempotency, source lineage, and audit requirements.

## Production readiness gate

The MVP must not be represented as operationally authorized until the organization completes identity integration, threat modeling, vulnerability management, dependency scanning, secrets management, backup/recovery exercises, records/privacy review, accessibility review, performance testing, high-availability design, monitoring, incident response, and RMF/authorization processes.


## Task-file administration

`MAX_UPLOAD_MB` controls the per-file limit. `UPLOAD_DIR` is `/app/storage` in Compose and is backed by the `ddc5i_storage` named volume. Allowed extensions are maintained in `app/services/storage.py`. Do not expand the allow-list without security and records review.

Operational deployment should add malware scanning, content disarm/reconstruction where required, DLP, encryption/key management, retention and disposition, storage monitoring, backup reconciliation, and orphan-file reporting. SHA-256 values in the application are evidence metadata, not a substitute for malware scanning or a digital signature.

## Search operations

Search uses database queries and current authorization scope. When investigating a missing result, verify the user’s role, division, project access, and sensitive-access flag before changing data. The type-ahead endpoint requires authentication and returns only scoped records. Search does not index attachment contents in v0.3.0.

v0.4.0 versions the local JavaScript and CSS URLs, so normal browser reloads should retrieve the current bundle. The global-search template contains no visible `K` marker. If an old bundle still appears, confirm the running container reports v0.4.0 and was rebuilt rather than only restarted.

## v0.4.0 administration

### Trusted proxy and rate limit

Set the following in `.env`, then rebuild the web container:

```env
PUBLIC_BASE_URL=https://portfolio.example.mil
TRUST_PROXY_HOPS=1
RATE_LIMIT_REQUESTS=300
RATE_LIMIT_WINDOW_SECONDS=900
```

Use `0` for direct access and the exact number of controlled proxy hops for proxied access. The application does not use unrestricted proxy trust. See `docs/REVERSE_PROXY.md`.

The Administration page displays effective non-secret runtime values. Secrets remain environment-managed.

### Board governance

Project Managers and Administrators can configure board states. Before archiving a state, move all tasks to active states. Do not lower a WIP limit below the current task count.

### Blueprint governance

v0.4.0 seeds three immutable template versions. Template records use a unique code/version pair. Operational governance should add author, reviewer, approval, publication, and retirement controls before allowing broad administrator authoring.

### Status-report governance

- Project delivery roles create Draft or Submitted reports.
- PMO/portfolio leadership returns or approves Submitted reports.
- Approved reports are authoritative governed reporting baselines for project and enterprise reporting views.
- Audit records retain submit, return, resubmit, and approve events.

### File policy

`MAX_UPLOAD_MB` controls size. The allowed extension set is code-governed in the local storage adapter. An operational environment must add approved malware scanning, DLP/CDR, encryption, repository/records integration, and retention policy.


## v0.4.0 runtime and delivery administration

The Administration page exposes non-secret effective settings for `PUBLIC_BASE_URL`, `TRUST_PROXY_HOPS`, rate-limit window/request values, and upload policy. Secrets remain environment-only.

- Configure the exact number of controlled proxy hops; keep `TRUST_PROXY_HOPS=0` for direct access.
- Use Board Configuration to create, order, constrain, and archive project columns. WIP limits are enforced on server-side creates, edits, and moves.
- Manage immutable project blueprint versions in source/configuration until a governed blueprint-administration workflow is approved.
- Treat approved status reports as reporting baselines. Return submitted reports for correction rather than directly altering approved records.
- Review storage usage and version history before backup or disposition. Soft-deleted files remain referenced until an approved purge/records workflow exists.

See `REVERSE_PROXY.md` and `UPGRADE_0.4.0.md` for deployment-specific procedures.

## v0.5.0 governance administration

### Local users and delegations

- Create local users only for demonstration, test, or approved isolated use. Require at least a 10-character initial password and transmit credentials through an approved separate channel.
- Assign the minimum role set and the narrowest division scope. Sensitive access is a separate flag and should require documented approval.
- Use deactivation instead of deletion to preserve audit references. The application prevents the current administrator from deactivating their own account.
- Delegations require delegator, delegate, role set, scope, start, expiry, and reason. v0.5.0 records and audits delegations but does not automatically augment every authorization decision; manually verify acting authority until v0.6.0 enforcement is delivered.

### Integration connections and field ownership

- Keep external connections disabled or in Mock mode until the target endpoint, service identity, secret storage, allowed network path, authoritative fields, idempotency behavior, retries, and reconciliation procedure are approved.
- Never store plaintext secrets in the connection `configuration` JSON or browser-visible forms. Use environment/secret-manager references in a production adapter.
- Define an ownership rule for every synchronized field. A safe default conflict policy is **Reject and reconcile**.
- Use ProjectOS dry run to validate canonical payload shape and record counts. The dry run is evidence only and performs no remote write.

### Data quality

- Run scans from **Data Quality** or a future durable scheduler. Assign issues to the accountable data owner rather than silently rewriting source records.
- Resolve an issue only after correction, approved exception, or documented non-applicability. Retain the disposition.
- Add rule versioning, approval, thresholds, and enterprise lineage before treating the current scanner as a formal quality-control service.

### Report packs and jobs

- Generated packs are snapshots of source records at generation time. Review organization scope and reporting period before approval.
- Job records in v0.5.0 are persistent execution evidence, not a distributed queue. A failed process will not automatically retry unless an operator invokes the action again.
- Introduce a durable worker, retry/backoff, dead-letter, cancellation, replay, and monitoring before scheduling critical operational jobs.

### Scenario governance

- Require documented assumptions and recalculate when source data changes.
- Keep calculation, approval, and apply permissions separated where staffing allows.
- Review every proposed field and impact explanation before approval. Apply writes authoritative records and creates audit evidence; it should not be used as a substitute for required financial, workforce, or leadership approvals.

See `UPGRADE_0.5.0.md`, `KNOWN_LIMITATIONS.md`, and `ROADMAP.md` for operational boundaries and next-release controls.
## v0.7.0 division briefing administration

### Briefing governance

- Use **Division Briefing** only with a division organization scope. The application requires that scope before creating the standard briefing structure.
- The existing Portfolio Review record remains the governance anchor. Decisions and actions created during the forum continue to use the authoritative Decision and Action tables.
- Section narrative is supplemental leadership context. Metrics and drill-downs continue to come from source project, demand, milestone, RAID, dependency, workforce, financial, benefit, status-report, and action records.
- Approval captures a snapshot of the evidence and section narratives. Do not delete or replace that snapshot to make later source data appear as though it was presented during the meeting.
- A review change request is a governed request, not an automatic arbitrary-field update. The accountable source-record owner must use the appropriate authoritative workflow and document the disposition.
- Open questions and change requests remain assigned after review completion. Closing authorities must acknowledge unresolved follow-up rather than representing it as complete.

### Migration and rollback

Before applying `0006_division_briefing_v070`, back up PostgreSQL and the file-storage volume using the packaged procedures. The migration creates new tables and does not rewrite existing portfolio review, decision, action, project, demand, resource, financial, benefit, or status-report rows.

Application rollback to v0.6.1 is possible only after confirming that the older application will not interact with newly created briefing records. Database downgrade removes v0.7.0 briefing tables and therefore destroys briefing preparation, snapshots, questions, change requests, and notes. Prefer forward-fix or application rollback while retaining the upgraded database unless an approved destructive downgrade is explicitly required.

### Operational checks

- Confirm a division briefing can be created and generates 15 sections.
- Confirm division and enterprise scope restrictions on briefing access.
- Confirm source refresh does not overwrite section narrative.
- Confirm approval captures a stable snapshot.
- Confirm questions and change requests appear in the assigned user's My Work view.
- Confirm review completion requires unresolved follow-up acknowledgement.
- Confirm audit events exist for preparation, approval, questions, responses, changes, actions, and closure.



### v0.7.0 protected-source boundary

Standard division briefings exclude records marked Restricted, Sensitive, or Limited Distribution; those records must be reviewed in a separately approved restricted forum. Do not use free-text narrative to reproduce restricted source content into a standard briefing.

## v0.7.5 Division profile administration

Migration `0007_division_experience_v075` creates `division_profiles` and corrects the display names for CID, JFID, and C3OD2. The idempotent seed reconciles missing profiles and missing banner metadata without overwriting user-maintained profile content.

Authorized maintainers are:

- Administrator
- PMO
- Enterprise Portfolio Owner
- Data Steward
- Division Chief within scope
- Division Portfolio Manager within scope

Profile edits and imports are audit recorded. JSON/CSV exports are also logged. Stable organization codes and IDs are not editable through the profile workflow.

Optimized runtime banner assets are stored in `app/static/division-banners`. Content source documents are packaged under `docs/source/division-profiles` for traceability and should be handled according to the deployment's records and information-protection rules.

## v0.7.6 Travel administration

### Reference data

Travel imports recognize the configured division codes and the source aliases `DDC5I <code>`. The demonstration build adds `CCD` and `FRONT` source-only division records so supplied approval data is not discarded. Administrators should reconcile these with authoritative organization reference data before production use.

### Import governance

Use the controlled import page; do not load travel tables directly. Preview results distinguish Valid, Warning, and Error rows. Warning rows retain source values and may be committed; Error rows are excluded. The Power BI travel export contains one warning where source ID `303` returns before departure.

### Matching thresholds

`app/services/travel.py` applies a conservative high-confidence auto-match threshold and requires a clear margin over the next candidate. Adjusting this threshold changes governance behavior and must be treated as a configuration-controlled release change with regression tests.

### Data quality

Run the data-quality scan after each import. v0.7.6 rules include:

- `TRAVEL-DATE-SEQUENCE`
- `TRIP-REPORT-MISSING`
- `TRIP-REPORT-UNMATCHED`

Resolve the authoritative source or document a disposition; do not silently edit historical source evidence.

### Production controls

Before production deployment, connect approved identity/SSO, authoritative organization and traveler directories, classification/handling workflows, actual financial sources, and approved mapping/geocoding services. Review all outbound integrations for destination and narrative sensitivity.


## v0.7.9 administration notes

### Quick-action governance
`POST /quick/tasks/{id}` and `POST /quick/actions/{id}/close` enforce, server-side: CSRF; owner or managing-PM (or ADMIN/PMO) authorization; the standard task status set; and audit events `QUICK_UPDATE` / `QUICK_CLOSE` with before/after values visible in Audit & Activity. Explicit-submission workflows (approvals, financial changes, published status, governance decisions) are unchanged — quick actions cover only low-risk immediate-save updates.

### Adoption telemetry
Telemetry is local-only and privacy-conscious by construction: a 200-event localStorage ring buffer per browser recording event name, path, and timestamp — never record content, usernames, or identifiers — with zero network calls (air-gap posture unchanged). Inspect with `JSON.parse(localStorage.getItem('jsj6-telemetry'))`; export and clear with `window.jsj6Telemetry.drain()`. To connect approved analytics tooling later, ship a collector that drains this queue.

### Version management
`VERSION` at the repository root is the single source of truth. `app.config.APP_VERSION` reads it and feeds FastAPI metadata, the sidebar footer, static asset cache-busting strings, division-export schema/filename versions, and the CSV package README. To cut a release: update `VERSION`, update release documentation, and repackage — no code edits required for the version bump itself.

### User-state storage
Guidance, onboarding, role-focus compaction, and navigation-group state persist per browser in localStorage under `jsj6-*` keys. `Help → Restart getting started` clears the onboarding flags for a user having trouble; clearing site data resets all adaptive state.
