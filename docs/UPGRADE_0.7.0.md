# Upgrade to v0.7.0

v0.7.0 adds the Division Briefing & Review workspace and includes database migration `0006_division_briefing_v070`.

## Before upgrading

1. Back up the PostgreSQL database using `scripts/backup.sh`.
2. Back up the file-storage volume separately.
3. Test the upgrade against a restored copy of the production-like database.
4. Retain the existing `.env` values and compare them with `.env.example`.

## Upgrade

1. Extract v0.7.0 into a clean directory.
2. Copy the existing `.env` into the new directory.
3. Rebuild and start:

   ```bash
   docker compose up -d --build
   ```

4. Startup applies Alembic migration `0006_division_briefing_v070`.
5. Open the application in a new browser tab. Static assets use version `0.7.0`.

## Database changes

The migration adds these tables:

- `briefing_sections`
- `briefing_snapshots`
- `review_questions`
- `review_change_requests`
- `review_notes`

The migration does not rewrite existing Portfolio Review, Decision, Action, Project, Demand, Resource, Financial, Benefit, Status Report, or Audit rows.

## Verification

- Confirm the application reports v0.7.0.
- Confirm **Briefings** appears in the primary navigation.
- Create a **Division Briefing** with a division scope and confirm 15 standard sections are generated.
- Confirm source-backed project, demand, milestone, RAID, dependency, workforce, investment, benefit, status-report, and prior-action evidence appears.
- Update a section narrative and mark it Ready for Division Review.
- Mark every section ready, submit the briefing, approve it, and confirm a snapshot is captured.
- Start the live review and open Presentation mode.
- Create a question, response, note, change request, action, and decision.
- Confirm assigned questions and change requests appear in My Work.
- Confirm completion requires acknowledgement when unresolved follow-up remains.
- Run `pytest -q` and confirm the packaged suite passes.

- Confirm standard briefing payloads omit Restricted, Sensitive, and Limited Distribution projects and demands.
- Confirm auditor-only users can view permitted briefings but cannot create or change briefing content.

## Rollback

Prefer a forward fix when possible.

Application rollback to v0.6.1 can use the upgraded database because the older application will ignore the new tables, but operators must prevent v0.6.1 from being represented as supporting briefing records created in v0.7.0.

A database downgrade drops all v0.7.0 briefing tables and destroys briefing sections, snapshots, questions, change requests, and notes. Perform that destructive downgrade only under an approved rollback plan and after preserving required evidence.
