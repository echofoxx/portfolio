# Demonstration Walkthrough

Allow 35–45 minutes for the full scenario, including the v0.7.0 leadership briefing workflow.

## v0.7.7 visual intelligence

Open **Home** and select nodes in **Investment Flow** to demonstrate approved-budget reconciliation and drill-through. Then open **Travel**, select a map marker and matching Top Location, and show the monthly trend, division determination mix, outcome funnel, compliance, and engagement-impact views. Explain that all geometry and coordinates are local and that the visuals use only already-authorized aggregates.

## 1. Executive orientation

Sign in as `leader / Demo123!`. Review the five exception KPIs, demand pipeline, leadership exceptions, forecast variance, benefit realization, critical milestones, dependencies, six division pulses, source-grounded narrative, and metric governance cards.

Open a metric card under Metric governance and point out definition, formula, owner, source, refresh, thresholds, and limitations.

## 2. Division drill-down

Open **Divisions → DSD**. Review mission, recurring core functions, demand stages, active projects, capacity, budget, RAID, dependencies, and required leadership action. Open an at-risk project, then a milestone or dependency to demonstrate traceability from enterprise exception to accountable source.


## 3. Prepare and conduct a Division Briefing

Sign in as `admin`, `pmo`, or an authorized division portfolio leader and open **Briefings**. Open the seeded Division Briefing or create one with a division scope.

1. Show the 16 standard sections and the source-backed evidence for projects, demands, milestones, RAID, dependencies, workforce, investment, benefits, status reports, and prior actions.
2. Add a short leadership narrative to a section, assign an owner, and mark the section **Ready for Division Review**.
3. Explain that all sections must be ready before submission. For a prepared demonstration record, submit and approve the briefing.
4. Point out that approval freezes a snapshot of exactly what leadership will see; later source changes do not rewrite the approved evidence.
5. Start the live review and select **Presentation mode**. Navigate sections from the left rail and use direct links for authorized source drill-down.
6. Record a question, assign it with a due date, add a review note or parking-lot item, create a governed change request, and assign an action. Record a decision through the existing review decision workflow.
7. Open **My Work** and show that assigned questions and change requests appear with the other operational follow-up.
8. Attempt to close with an open item and demonstrate the required acknowledgement before review completion.

Emphasize that the workspace replaces manual slide assembly while retaining division validation, authoritative records, decisions, actions, snapshots, and audit evidence.

## 4. Travel & Engagement Outcomes

Open **Travel & Engagements** as `admin` or `pmo`.

1. Confirm the dashboard shows 385 approval-source travel requests totaling **$1,082,395.25** and clearly labels costs as estimates rather than authoritative actual expenditures.
2. Filter by division, month, determination, traveler, event, or location and drill from a summary into the contributing request list.
3. Open source request `426` to show $11,040 estimated cost, J6 funding, purpose/ROI, impact if not accomplished, exemption category, approval chain, and row/file provenance.
4. Open a reusable engagement to show multiple travelers/divisions, aggregate estimate, related reports, and structured outcomes.
5. Open a Trip Report and show the complete purpose, discussion, findings, recommendations, and action narrative.
6. For an unmatched report, compare candidate scores and rationale, confirm a request, then demonstrate clear/rematch as an auditable correction.
7. Enter review comments and move the report through In Review, Reviewed, or Changes Required.
8. Promote an accepted outcome to an Action, Risk, Decision, or Dependency. Open the created canonical record from the clickable traceability link and return to the source report.
9. Open the division page and a Division Briefing to show period-specific travel, report compliance, findings, and linked follow-through.
10. Explain the retained source anomaly: request `303` remains in the dataset with a data-quality warning instead of being silently changed.

## 4. Submit a demand

Sign in as `admin` or `pmo`. Open **Demand → New Demand** and enter:

- Title: `Coalition Data Exchange Evidence Pilot`
- Category: `Experiment`
- Lead division: DSD
- Mission: Data Advantage
- Sponsor: any seeded sponsor
- Purpose: validate a governed, standards-based exchange pattern
- Problem: inconsistent exchange paths create repeated integration effort
- Desired end state: a repeatable pilot with measurable interoperability evidence
- Urgency: High
- ROM: 450000
- Benefits: reduced integration cycle time and improved confidence

Save as draft first. Reopen and demonstrate current owner/next action. Submit after required fields are complete.

## 5. Triage and clarification

Move Submitted to Triage. Optionally choose Clarification Required and enter missing evidence. The requester notification links back to the same record. Return to Submitted/Triage/Assessment as the workflow allows.

## 6. Assess and compare

At Assessment, enter criterion values and rationale. Record a second assessment with a different value to show score variance. Open **Assessments** and compare cost, score, confidence, division, and stage across candidates.

Move the demand to Awaiting Portfolio Recommendation and Awaiting Decision.

## 7. Record leadership decision

Sign in as `approver`, `leader`, or `admin`. Record Approve with:

- participants;
- evidence considered;
- conditions on separate lines;
- resource and financial implications;
- review date.

Check “approval exceeds available capacity” and leave the tradeoff blank to demonstrate validation. Then identify work to delay, reduce, de-scope, or an approved capacity increase. Save. Show that each condition became an action.

## 8. Convert without rekeying

Select a project manager and convert the approved demand. The project title, description/purpose, mission, division, sponsor, desired end state, scope, deliverables, dates, cost, benefits, and sensitivity are carried forward. Three starter tasks are created.

## 9. Execute and roll up

Open the project Kanban and move a task. Add a milestone and RAID item. Update project status to At Risk or Off Track with a narrative and percent complete. Return to DSD and Executive; the same project now appears in the exception roll-up.

## 10. Excel import

Open **Excel Imports** and use `sample-imports/DDC5I_Demand_Import_Demo_v1.0.xlsx`. The preview contains:

- a valid create row;
- a possible duplicate warning;
- a duplicate upload identifier error;
- invalid organization/mission/numeric errors.

Download the correction workbook, then commit valid/warning rows. Open the resulting demand and show source-system/batch lineage in audit evidence.

## 11. Requirements and audit

Open **Requirements RTM**. Explain the 307-row source baseline plus six v0.7.5, twelve v0.7.6, and ten v0.7.7 release requirements (335 packaged rows) and conservative categories. Filter by `Requires integration` or a domain. Update a test/reference field as admin and show the corresponding Audit record.

Sign in as `auditor` and show that business mutation is denied while audit and RTM evidence remain visible.

## 12. Close

Review Known Limitations and Roadmap. Emphasize that CAC/PIV, production authorization, live ProjectOS/ServiceNow/Microsoft/financial/workforce connections, detailed schedules, authoritative workforce/financials, and AI are not claimed in the MVP.
