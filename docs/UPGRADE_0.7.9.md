# Upgrade to v0.7.9 — Adoption, Focus & Workflow Simplification

## Scope

v0.7.9 is a schema-compatible application upgrade from v0.7.8. It is a focused adoption release: simplified navigation, a unified My Work Action Center with governed quick actions, a decision-first executive dashboard with explainable health rollups, focused Travel workspaces with server-side pagination, adaptive guidance and onboarding, a searchable help/glossary drawer, privacy-conscious adoption telemetry hooks, and a release-integrity sweep that makes the `VERSION` file the single source of truth.

**No Alembic migration is required.** Migration head remains `0008_travel_engagements_v076`. No model or schema changes were made.

## Upgrade steps

1. Stop the running v0.7.8 stack (`docker compose down` or stop uvicorn).
2. Replace the application directory with the v0.7.9 package (preserve `.env` and any external volumes).
3. Rebuild and start (`docker compose up --build -d` or reinstall requirements and start uvicorn). No new Python or JavaScript dependencies were added.
4. Hard-refresh browsers once; static assets are cache-busted to `?v=0.7.9`.
5. Optional: run `pytest` — the packaged suite is 89 tests, all passing.

## Behavior changes to communicate to users

- The sidebar now shows nine primary destinations; Strategy, Scenarios, Decisions, Risks & Dependencies, Roadmaps, Blueprints, Notifications, and saved views are under **More workspaces**, and Administration & Assurance is collapsible. Nothing was removed; group open/closed state persists per user and expands automatically when a contained page is active.
- The top strip is now contextual shortcuts (Home, My Work with open-item count, top role actions, Notifications) instead of duplicating the sidebar.
- **My Work** is now the Action Center. Users complete tasks, set percent complete, record blockers, and close actions inline; each update is audited (`QUICK_UPDATE` / `QUICK_CLOSE`) and permission-checked (owner or managing PM only).
- The Portfolio Overview leads with Decisions Required and Significant Changes; the Investment Flow Sankey lives under Investment analysis further down.
- Travel is split into Overview / Requests / Trip Reports / Reconciliation / Engagement Outcomes tabs; long tables paginate at 25 rows and filters carry across tabs.
- Returning users see a compact role-focus banner and collapsed page guides; both can be reopened from the topbar **?** Help drawer, which also hosts the searchable glossary and a "Restart getting started" control.

## Governance, audit, and security posture

- No authorization rules were weakened. Quick actions enforce owner/PM/ADMIN/PMO checks server-side, require CSRF, and write audit events with before/after values.
- Explainable rollups distinguish calculated health, owner-reported health, and leadership overrides; the precedence and contributing records are displayed, not changed.
- Telemetry is local-only (localStorage ring buffer, 200 events max), contains no record content, identifiers, or network calls, and is drainable via `window.jsj6Telemetry.drain()` when approved analytics tooling is connected. The air-gap posture is unchanged.

## Files changed

| Area | Files |
| ---- | ----- |
| Version single source | `VERSION`, `app/config.py`, `app/main.py` |
| Navigation, shell, help drawer | `app/templates/base.html`, `app/static/app.css`, `app/static/app.js` |
| Action Center + quick actions | `app/main.py` (`my_work`, `POST /quick/tasks/{id}`, `POST /quick/actions/{id}/close`), `app/templates/my_work.html` |
| Decision-first dashboard + explainer + onboarding | `app/main.py` (`dashboard`), `app/templates/dashboard.html` |
| Travel focused views + pagination | `app/main.py` (`travel_dashboard`), `app/templates/travel.html` |
| Tests | `tests/test_v079.py` (new), `tests/test_v031.py`, `tests/test_v040.py`, `tests/test_v050.py`, `tests/test_v060.py`, `tests/test_v070.py`, `tests/test_v075.py`, `tests/test_v076.py`, `tests/test_v077.py` (stale expectations root-caused) |
| Documentation | `README.md`, `docs/RELEASE_NOTES.md`, `docs/UPGRADE_0.7.9.md`, `docs/FEATURE_INVENTORY.md`, `docs/ROADMAP.md`, `docs/USER_GUIDE.md`, `docs/ADMIN_GUIDE.md`, `docs/REQUIREMENTS_TRACEABILITY.md`, `docs/DDC5I_RTM_MVP_Status.csv`, `docs/TEST_RESULTS.md`, `docs/BUILD_SUMMARY.md`, `docs/BUILD_VALIDATION.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/BUILD_MANIFEST.txt` |

## Recommendation-to-implementation mapping

| Recommendation | Implemented change | Files affected | Validation method |
| -------------- | ------------------ | -------------- | ----------------- |
| 1. Simplify primary navigation | 9 primary destinations; More workspaces + Administration collapsible with persistence; contextual shortcut strip replaces duplicate tabs | `base.html`, `app.css`, `app.js` | `test_v079_simplified_navigation_and_collapsible_groups`, updated `test_v060` nav test |
| 2. Role-specific landing pages | Role-focus strip + role-aware dashboard ordering + role-specific Getting started checklist driven by `role_focus` actions | `dashboard.html`, `base.html` | `test_v079_adaptive_shell_and_help_glossary` |
| 3. Unified My Work Action Center | Six attention groups, per-item why/parent/priority/due/status/primary action, auto-collapsed empty groups, single positive empty state | `main.py`, `my_work.html` | `test_v079_my_work_action_center_groups_and_empty_collapse`, updated `test_v070`/`test_v076` |
| 4. Extremely fast frequent actions | Inline percent-complete, complete, blocker note, action close with immediate-save pattern, audit, and permissions | `main.py`, `my_work.html` | `test_v079_quick_task_update_owner_permission_and_audit`, `test_v079_quick_task_update_rejected_for_non_owner` |
| 5. Adaptive guidance | Compact role-focus for returning users, collapsed page guides with persistence, reopen via Help | `app.js`, `base.html`, `app.css` | JS markers asserted in `test_v079_reduced_motion_and_mobile_rules_present`; manual check |
| 6. First-login onboarding | Role-specific Getting started card, dismiss/persist, restart from Help drawer | `dashboard.html`, `app.js` | Template markers in `test_v079_adaptive_shell_and_help_glossary`; manual check |
| 9. Decision-oriented dashboards | Decisions Required → Significant Changes → health → Investment analysis ordering; Sankey moved to deep-dive | `main.py`, `dashboard.html` | `test_v079_dashboard_is_decision_first_with_explainable_health` |
| 8. Explainable rollups | Health "Why? · View calculation" with formula, counts, precedence, contributors, freshness | `main.py`, `dashboard.html`, `app.css` | Same test as above |
| 11. Simplify Travel workspace | Overview/Requests/Reports/Reconciliation/Outcomes views; 25-row server-side pagination; shorter map with scrolling index | `main.py`, `travel.html`, `app.css` | `test_v079_travel_split_into_focused_views_with_pagination`, existing `test_v077` travel test |
| 12. Tables and mobile behavior | Pagination footers with counts, mobile card reflow for Action Center, 42px touch targets, drawer full-screen on mobile | `app.css`, templates | CSS assertions + manual viewport review |
| 15. Contextual definitions and help | Searchable glossary drawer with meaning, why-it-matters, owner, authoritative source, and location per term | `base.html`, `app.js`, `app.css` | `test_v079_adaptive_shell_and_help_glossary` |
| 16. Accessibility and performance | `prefers-reduced-motion` global rule, touch targets, server-side pagination replacing 200-row renders | `app.css`, `main.py` | `test_v079_reduced_motion_and_mobile_rules_present` |
| 17. Adoption measurement hooks | `window.jsj6Telemetry` local ring buffer (page views, quick actions, help, no-result searches), no network, no sensitive data | `app.js` | JS marker assertion + manual check |
| Release integrity | `VERSION` single source of truth; nine stale test expectations root-caused; release docs synchronized | `VERSION`, `config.py`, `main.py`, tests, docs | `test_v079_version_single_source_of_truth`; full suite 89/89 |

## Deferred by design (kept out of this focused release)

Migration Center expansion (§14), full notification preference/digest system (§13), resource heatmap and scenario staffing (§10), saved table views and role column presets (§12 partial), and server-persisted onboarding/guidance preferences (currently per-browser via localStorage). See `docs/ROADMAP.md`.
