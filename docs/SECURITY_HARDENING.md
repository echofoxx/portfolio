# Security and Production-Hardening Guide

## Implemented baseline

- PBKDF2-SHA256 passwords with random salt and 310,000 iterations.
- signed, expiring, HTTP-only, same-site session cookie.
- secure cookie when `ENVIRONMENT=production`.
- CSRF token on state-changing forms and Kanban JSON operation.
- role, organization, record, and sensitivity checks on the server.
- inaccessible direct-object requests return 404.
- read-only auditor behavior.
- login throttling: ten attempts per IP in five minutes in the local process.
- CSP, frame denial, MIME sniffing prevention, same-origin referrer, permissions policy.
- validation of workflow transitions, scoring ranges, import rows, file extension/name/path/size.
- material before/after audit events.
- environment-based secrets and no committed `.env`.

## Required before operational use

### Identity and access

- integrate approved OIDC/SAML/CAC/PIV provider;
- disable local demonstration credentials;
- enforce MFA/CAC policy and session assurance;
- provision/deprovision roles from authoritative groups;
- implement project membership, field policy, delegation approval, recertification, SoD alerts;
- separate platform administration from business approval authority.

### Application security

- complete threat model and abuse cases;
- perform SAST, dependency/SBOM, container, IaC, DAST, and penetration testing;
- add distributed rate limiting and account lockout policy;
- add optimistic concurrency, idempotency, and replay controls;
- remove unsafe-inline CSP through nonce/hash strategy;
- enforce TLS/HSTS through an approved reverse proxy;
- add secure error correlation without exposing details;
- validate all uploads by MIME/signature, scan for malware, and apply DLP.

### Data protection

- approve sensitivity/classification taxonomy and marking behavior;
- encrypt database, files, backups, and traffic with approved mechanisms;
- implement field-level controls for workforce, rate, privacy, and sensitive mission data;
- define retention, disposition, legal hold, export, and records schedules;
- minimize copies into analytics and integrations;
- document lineage and authorized use.

### Operations

- centralized structured logging and SIEM forwarding;
- metrics, traces, alerting, uptime and capacity monitoring;
- vulnerability patch SLAs and image signing;
- immutable deployment artifacts and CI/CD approvals;
- backup encryption, off-host copies, restore exercises, recovery objectives;
- high-availability database, web replicas, queue workers, object storage;
- incident response, access review, audit review, and continuity exercises.

### Compliance and authorization

- Section 508/WCAG 2.2 AA expert testing;
- privacy impact and records review;
- security control implementation and evidence;
- RMF categorization, assessment, authorization, POA&M, and continuous monitoring as applicable;
- approved hosting/network boundary and data-flow diagrams.

## Secrets

Do not store production secrets in `.env` files on shared systems. Use an approved secret manager and short-lived service credentials. Rotate the local `SECRET_KEY` invalidates sessions. Rotate database credentials through an approved process and update service configuration atomically.

## Audit

The MVP audit log is application evidence, not a tamper-evident enterprise ledger. Production should protect audit writes, restrict deletion, forward events off-host, include correlation IDs and actor assurance, monitor gaps, and define retention.

## AI gate

Do not connect generative AI to operational data until access-aware retrieval, source citation, data lineage, evaluation, human approval, prompt/model versioning, feedback, monitoring, and audit controls are approved. AI must not autonomously approve, prioritize, allocate, or overwrite authoritative records.

## v0.4.0 deployment controls

- Keep Uvicorn proxy-header rewriting disabled; the application exact-hop resolver is the authoritative client-IP path.

- Configure the exact trusted-proxy hop count; never infer trust from the mere presence of `X-Forwarded-For`.
- Require upstream proxies to overwrite forwarding headers and restrict direct access to the application container.
- Replace the in-memory rate limiter with a shared approved store for multi-replica deployment.
- Add malware scanning, DLP/content disarm, encrypted object/repository storage, records retention, legal hold, and disposition controls before operational file use.
- Restrict blueprint and board configuration permissions and include configuration promotion in change management.
- Treat approved status reports as business records and define retention, signature, distribution, and release policy.
