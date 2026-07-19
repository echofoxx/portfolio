# UX Navigation, Role Focus, and Accessibility Review — v0.6.1

## Executive assessment

v0.6.0 contains a broad and usable enterprise portfolio capability set, but its shell assumed that users already understood portfolio-management language, role permissions, and lifecycle sequencing. The primary friction was not missing records or workflows; it was missing orientation:

- users could see many menu choices without knowing which choices mattered for their role;
- top and left navigation repeated destinations without explaining the difference between a summary and an authoritative workspace;
- most pages described their contents but did not show the sequence of work;
- editable forms looked similar to read-only cards, so the place to provide input was not always obvious;
- many labels, table cells, badges, and navigation items used 9–12 px text;
- theme choice existed, but text size and spacing were not user preferences;
- My Work was a collection of paragraphs rather than a prioritized personal workbench.

v0.6.1 addresses these issues without changing database schema, authorization rules, or authoritative business workflows.

## Implemented in v0.6.1

### Role-oriented navigation

The shell now derives a primary focus profile from the signed-in user's roles. It presents:

- a concise role focus statement on every authenticated page;
- up to three recommended starting actions;
- **Focus** markers on the most relevant left-navigation destinations;
- a role label in the user identity area;
- a direct **Open my work** orientation link in the navigation.

Profiles are included for administrators, decision authorities, portfolio/PMO users, division leaders, project managers, team members, requesters, assessors, resource managers, financial managers, benefits owners, data stewards, and assurance reviewers.

### Contextual process guides

A server-rendered page guide now appears above the page content. Guides explain the purpose of the workspace and show a numbered process flow with completed, current, and upcoming states where record status is available.

Covered flows include:

| Workspace | Process shown |
|---|---|
| Portfolio Overview | Review → Prioritize → Act → Verify |
| My Work | Review → Prioritize → Update → Close |
| Demand Intake | Draft → Validate → Assess → Recommend → Decide → Execute |
| Projects and Tasks | Orient → Plan → Execute → Control → Report |
| Portfolio Reviews | Prepare → Review → Decide → Assign → Complete |
| Resources | Review capacity → Request → Decide → Allocate → Track |
| Investments and Benefits | Baseline → Record → Forecast → Review → Decide |
| Reports and Operations | Prepare → Generate → Validate → Approve → Use |
| Scenarios | Define → Model → Compare → Approve → Apply |
| Excel Imports | Download → Upload → Validate → Commit → Correct |
| Data Quality | Scan → Triage → Assign → Resolve → Verify |
| Integrations | Register → Own fields → Test → Reconcile → Operate |
| Administration | Create/update → Assign roles → Set scope → Delegate → Verify |
| Requirements RTM | Filter → Inspect → Evidence → Classify → Export |
| Audit | Scope → Inspect → Corroborate → Document |

The guide can be collapsed. The preference is saved in the current browser.

### Clear input areas

Client-side enhancement identifies substantial editable forms and marks them with:

- an accent border and subtle input-zone background;
- an **Input area** instruction banner;
- visible required-field markers;
- larger controls and stronger label hierarchy.

Small inline actions, filters, search, and one-click approval controls are intentionally excluded so the interface does not become visually noisy.

### Display preferences

The top command bar now includes **Display preferences** with:

- Standard, Large, and Extra large text;
- Comfortable and Compact spacing;
- browser-local persistence and reset.

The CSS converts the smallest navigation, table, badge, helper, task, and dashboard text to scalable `rem` values. Focus indicators, skip navigation, control sizes, and mobile behavior were also strengthened.

### My Work redesign

My Work is now a role-neutral personal workbench with:

- summary counts for tasks, actions, demands, and managed projects;
- direct links to full authoritative task and action records;
- due dates, priority, progress, health, status, and next action;
- clear separation between “Do First” assignments and stewardship responsibilities.

## Remaining UX backlog

The following improvements are still recommended. They are not claimed as implemented in v0.6.1.

### Priority 1 — adoption and accessibility

1. **Formal WCAG 2.2 AA evaluation.** Complete keyboard-only, screen-reader, 200% zoom, reflow, contrast, error-identification, and target-size testing with documented remediation. v0.6.1 improves accessibility but is not an accessibility certification.
2. **First-login onboarding.** Provide a role-specific checklist or guided tour that records completion and can be reopened from Help.
3. **Server-side preferences.** Store text size, density, theme, guide visibility, and preferred landing page per user so settings follow the user across browsers and devices.
4. **Contextual help and glossary.** Add a help drawer with plain-language definitions, examples, “why this matters,” and links to operating procedures for each field and status.
5. **Accessible Kanban alternatives.** Add keyboard reordering, non-drag movement controls, bulk operations, and clear WIP/criteria announcements.

### Priority 2 — role productivity

1. **True focus queue.** Rank work by overdue status, priority, blocked decisions, risk exposure, stale data, and upcoming due dates rather than listing only by record type.
2. **Role-specific dashboards.** Provide configurable widgets for leadership, PMO, project manager, resource manager, financial manager, data steward, and auditor personas.
3. **Action center.** Combine notifications, approvals, clarifications, assignments, and conditions into a single queue with due-date filters, bulk acknowledgement, and escalation.
4. **Record-level next-step logic.** Extend process indicators so every individual project tab, task state, portfolio review item, resource request, report, import batch, and quality issue highlights its exact next permitted action.
5. **Draft protection.** Add autosave, unsaved-change warnings, field-level validation summaries, and recovery for long intake, assessment, status-report, and scenario forms.

### Priority 3 — configuration and scale

1. **Role-configurable navigation.** Allow administrators to define landing pages, menu visibility, terminology, and help content without code changes while retaining authorization enforcement.
2. **Workflow/form designer.** The product still lacks a governed designer for conditional intake fields and configurable workflow steps.
3. **Cross-device recent/favorite work.** Persist pinned records, recents, saved layouts, and favorites in the application rather than only in browser state.
4. **Usage analytics and usability telemetry.** Measure abandoned forms, repeated navigation, search failures, time-to-complete, and help usage under approved privacy controls.

## Acceptance evidence

v0.6.1 adds automated checks for:

- role-specific focus content;
- page-level process guides for dashboard, demand, project, and import workflows;
- display preference controls and scalable text-size markers;
- client-side input-zone enhancement source;
- continued v0.6.0 navigation, dashboard, theme, and legacy-route behavior.

The complete automated suite passes with 63 tests. Target-host browser and accessibility acceptance remain required.
