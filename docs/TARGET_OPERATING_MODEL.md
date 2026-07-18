# Target Operating Model

## Mission chain

The platform operationalizes this traceable chain:

**Mission and strategy → core functions and organizational responsibilities → governed work intake → assessment and prioritization → portfolio recommendation → leadership decision → execution → resources and investments → risks and dependencies → outcomes and benefits → executive reporting and the DDC5I narrative.**

The MVP treats recurring core functions and named projects as different work types competing for the same finite capacity. It also supports lead and supporting divisions so cross-division work is not forced into a single-owner fiction.

## Organizational model

The seed includes one configurable enterprise root and six configurable divisions:

- DDC5I Enterprise
- JAD
- DSD
- AID
- CID
- JFID
- C3OD2

Organizations use stable UUIDs and human-readable codes. Parent relationships support future branches, teams, shared services, cross-division constructs, and reorganizations. The present UI is optimized for enterprise and division views; deeper hierarchy administration is a roadmap capability.

## Governance forums and decisions

The operating model separates recommendation from authoritative decision. Stage gates provide a minimum evidence sequence:

| Gate | Purpose | Required evidence in the MVP |
|---|---|---|
| Gate 0 | Submission readiness | mission, purpose, problem, desired end state |
| Gate 1 | Division validation | triage owner, clarification, division context |
| Gate 2 | Assessment complete | weighted score, rationale, confidence |
| Gate 3 | Portfolio recommendation | completed assessment and candidate comparison |
| Gate 4 | Leadership decision | disposition, authority, rationale, evidence, implications, conditions |
| Gate 5 | Execution initiation | approved demand, named project manager, linked project |

A decision condition becomes an action. Approval beyond capacity requires a documented tradeoff. This preserves the distinction between “approved” and “funded/staffed/initiated.”

## Accountabilities

- **Senior leader / approval authority:** decision and documented tradeoff.
- **Enterprise portfolio owner / PMO:** enterprise funnel, portfolio recommendation, governance evidence, roll-up.
- **Division chief / division portfolio manager:** division validation, mission/function ownership, capacity and delivery exceptions.
- **Sponsor / requester:** problem, need, intended outcome, beneficiaries, evidence, clarification.
- **Assessor:** independent criterion score, rationale, and confidence.
- **Project manager:** delivery baseline, status, tasks, milestones, RAID, dependencies, actions, acceptance evidence.
- **Resource and financial managers:** capacity and investment data under appropriate field-level controls.
- **Benefits owner:** benefit target, realization, evidence, and review.
- **Data steward:** definitions, lineage, quality, stale data, traceability, and governed reference data.
- **Security/privacy reviewer and auditor:** access, evidence, review, and independent oversight.
- **Platform administrator:** technical operation without assuming business authority.

## Authoritative-data operating principle

The local MVP is authoritative for its own demonstration records. Once an integration is connected, authority becomes field-specific. The owning system, allowed writers, conflict policy, synchronization direction, and reconciliation responsibility must be approved before data exchange begins.

## Reporting model

Dashboards are exception and decision oriented. Each governed metric carries definition, formula, owner, source, last refresh, thresholds, and known limitations. Narrative text is constructed only from accessible source records and is editable in a future release; the MVP does not invent unsupported operational facts.

## Operating cadence

The MVP can support a practical cadence:

- continuous demand submission and triage;
- weekly division portfolio review;
- biweekly project status update;
- monthly enterprise portfolio and resource review;
- quarterly benefits and investment review;
- release-based RTM verification and UAT.

Cadence automation and governance calendars are partially implemented or planned; policy owners must approve final timelines and escalation rules.

## v0.5.0 operating-model expansion

The platform now supports a closed governance loop beyond demand and delivery:

**Operational records → data-quality controls → portfolio review → decision/action → non-destructive scenario → approved change → report pack → integration/reconciliation evidence**.

Accountability is divided as follows:

- Platform Administrators manage local demonstration users, role/scope configuration, delegation records, and connector metadata.
- Data Stewards own field-ownership rules, data-quality issues, source lineage, and reconciliation governance.
- Portfolio Owners and Division Leaders chair reviews, approve scenarios, and make explicit trade-space decisions.
- Resource and Financial Managers decide planning requests and maintain restricted planning evidence.
- Integration Owners configure and operate adapters only after authority, security, and reconciliation contracts are approved.
- Auditors inspect the decision, synchronization, scenario, quality, report, and record-change evidence without changing business data.
