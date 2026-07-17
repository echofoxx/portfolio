# Test Results

## Automated result

Release workspace command:

```bash
pytest -q --disable-warnings
```

Result:

```text
25 passed
```

Coverage result: **88% of application code**.

## Covered behaviors

| Test area | Evidence |
|---|---|
| Scoring | weights total 100; expected weighted result; missing/out-of-range rejection; assessor variance |
| Permissions | enterprise/division scope; sensitive access; auditor read-only |
| Workflow | allowed gate transitions; invalid transition rejection; role restriction |
| Import | versioned XLSX parser; valid, warning/possible duplicate, duplicate ID, invalid references and numeric error; formula-injection-safe correction output |
| Database | unique stable human identifier constraint |
| Audit | material update records distinct before/after values |
| Health and routes | live/ready and major navigation routes return successfully |
| Accessibility smoke | main/nav/headings and labeled global search on critical pages |
| IDOR/access denial | division user receives 404 for inaccessible other-division demand |
| Auditor mutation denial | business transition returns 403 |
| Acceptance scenario 1 | demand submission through triage, assessment, recommendation, decision and no-rekey project conversion |
| Acceptance scenario 2 | project status update appears in executive exception roll-up |
| Service interfaces | integration field-ownership registry, background-job abstraction and secure local storage adapter |

## Manual/local validation

- Alembic migration ran against a clean local test database.
- idempotent seed created 25 users, 7 organizations, 6 missions, 12 core functions, 20 demands, 17 projects, 80 tasks, 35 milestones, 20 RAID records, 15 dependencies, 10 decisions, 12 actions and 307 RTM records.
- 29 Jinja templates compiled successfully.
- Python modules compiled successfully.
- authenticated route smoke tests covered dashboards, strategy, demands, assessments, decisions, projects and tabs, risks, resources, financials, benefits, reports, notifications, imports, RTM, audit, administration, search and OpenAPI.
- ten screenshots were rendered from authenticated seeded pages.
- versioned XLSX workbooks were imported back and inspected; expected sheets/values were present and formula-error scan returned no matches.

## Not executed in artifact-build environment

The environment did not expose a Docker daemon, so these commands must be run on the target Docker Desktop host:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://localhost:8080/health/ready
docker compose run --rm web pytest -q
```

Formal UAT, Section 508/WCAG audit, security assessment, load test, restore exercise, Edge/Chrome enterprise-version matrix, high availability and external-integration tests remain open.
