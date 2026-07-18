from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import (
    Action,
    Assessment,
    AuditEvent,
    Benefit,
    BoardColumn,
    CoreFunction,
    Decision,
    Demand,
    Dependency,
    FinancialRecord,
    FinancialTransaction,
    FieldOwnershipRuleRecord,
    IntegrationConnection,
    JobRun,
    MetricDefinition,
    Milestone,
    Mission,
    Notification,
    Organization,
    Portfolio,
    PortfolioReview,
    PortfolioReviewItem,
    Project,
    ProjectTemplate,
    RaidItem,
    RequirementTrace,
    ResourceCapacity,
    ResourceRequest,
    ReportPack,
    Scenario,
    ScenarioChange,
    StatusReport,
    Task,
    TaskComment,
    TaskNoteRevision,
    TaskRelationship,
    User,
)
from app.services.scoring import calculate_weighted_score
from app.services.security import hash_password

DIVISIONS = [
    ("JAD", "Joint Assessment Division", "Plans and executes decision-centered Joint assessments, operational demonstrations, and evidence-based recommendations."),
    ("DSD", "Data and Standards Division", "Advances data, messaging, semantic, API, and interoperability standards for Joint and coalition command and control."),
    ("AID", "Architecture and Integration Division", "Integrates architectures, mission threads, technical baselines, and cross-enterprise solutions."),
    ("CID", "Cyber and Infrastructure Division", "Strengthens resilient infrastructure, cybersecurity, Zero Trust, and mission-partner connectivity."),
    ("JFID", "Joint Force Integration Division", "Accelerates integration of Joint Force capabilities, concepts, and operational priorities."),
    ("C3OD2", "Command, Control, Communications and Operations Division", "Coordinates command-and-control operations, readiness, and enterprise decision support."),
]

MISSIONS = [
    ("M-INT", "Joint and Coalition Interoperability", "Improve trusted information exchange and operational interoperability across the Joint Force and mission partners."),
    ("M-DATA", "Data Advantage", "Make operational data visible, accessible, understandable, linked, trustworthy, interoperable, and secure."),
    ("M-ASSESS", "Decision-Centered Assessment", "Provide rigorous evidence that informs senior leader decisions, investment choices, and operational risk."),
    ("M-ARCH", "Integrated C2 Architecture", "Align architectures, mission threads, services, and standards to accelerate CJADC2 outcomes."),
    ("M-RES", "C5 Readiness and Resilience", "Improve readiness, cyber resilience, continuity, and operational availability."),
    ("M-MOD", "Digital Modernization", "Modernize processes, tools, data products, and delivery methods while reducing duplication and technical debt."),
]

DEMO_PASSWORD_HASH = hash_password("Demo123!")

ROLE_USERS = [
    ("leader", "Jordan Lee", "SENIOR_LEADER", None, True),
    ("portfolio", "Morgan Reed", "ENTERPRISE_PORTFOLIO_OWNER", None, True),
    ("pmo", "Taylor Brooks", "PMO", None, True),
    ("approver", "Casey Morgan", "APPROVAL_AUTHORITY", None, True),
    ("auditor", "Riley Chen", "AUDITOR", None, True),
    ("admin", "Alex Parker", "ADMIN", None, True),
]


def _user(username: str, full_name: str, role: str, division_id: str | None, sensitive: bool = False) -> User:
    return User(
        username=username,
        full_name=full_name,
        email=f"{username}@demo.ddc5i.local",
        password_hash=DEMO_PASSWORD_HASH,
        roles=[role],
        division_id=division_id,
        sensitive_access=sensitive,
    )


def next_action_id(db: Session) -> str:
    n = db.query(Action).count() + 1
    while db.query(Action).filter(Action.human_id == f"ACT-26-{n:03d}").first():
        n += 1
    return f"ACT-26-{n:03d}"



def ensure_v040_reference_data(db: Session) -> None:
    """Idempotently add v0.4 board, template, note, and reporting demonstration data."""
    projects = db.query(Project).order_by(Project.human_id).all()
    default_columns = [
        ("Backlog", 0, 0, "Captured and ready for refinement", "Ready for prioritization"),
        ("Ready", 1, 8, "Scope and owner are clear", "Capacity is available"),
        ("In Progress", 2, 6, "Owner accepted work", "Acceptance criteria are satisfied"),
        ("Review", 3, 4, "Evidence is attached", "Reviewer accepts completion"),
        ("Done", 4, 0, "Acceptance evidence approved", "Work is closed"),
    ]
    for project in projects:
        if db.query(BoardColumn).filter(BoardColumn.project_id == project.id).count() == 0:
            for name, position, wip_limit, entry, exit_criteria in default_columns:
                db.add(BoardColumn(project_id=project.id, name=name, position=position, wip_limit=wip_limit, entry_criteria=entry, exit_criteria=exit_criteria))

    admin = db.query(User).filter(User.username == "admin").first()
    templates = [
        {
            "code": "GENERAL", "name": "General Governed Project", "category": "General",
            "description": "A balanced delivery blueprint with initiation, delivery, validation, and transition controls.",
            "blueprint": {
                "columns": [
                    {"name": "Backlog", "wip_limit": 0}, {"name": "Ready", "wip_limit": 8},
                    {"name": "In Progress", "wip_limit": 6}, {"name": "Review", "wip_limit": 4}, {"name": "Done", "wip_limit": 0}
                ],
                "tasks": [
                    {"title": "Confirm charter and decision authority", "type": "Approval", "priority": "High", "offset": 7, "effort": 16},
                    {"title": "Baseline scope, WBS, schedule, resources, and risks", "type": "Summary", "priority": "High", "offset": 14, "effort": 40},
                    {"title": "Deliver approved capability increment", "type": "Deliverable", "priority": "High", "offset": 60, "effort": 160},
                    {"title": "Validate acceptance evidence", "type": "Approval", "priority": "High", "offset": 75, "effort": 48},
                    {"title": "Transition, close, and capture lessons", "type": "Task", "priority": "Medium", "offset": 90, "effort": 32}
                ],
                "milestones": [
                    {"title": "Baseline approved", "offset": 14, "critical": True},
                    {"title": "Operational acceptance", "offset": 75, "critical": True},
                    {"title": "Transition complete", "offset": 90, "critical": False}
                ]
            }
        },
        {
            "code": "ASSESSMENT", "name": "Joint Assessment Event", "category": "Assessment",
            "description": "Decision-centered assessment planning, execution, analysis, adjudication, and reporting blueprint.",
            "blueprint": {
                "columns": [
                    {"name": "Planned", "wip_limit": 0}, {"name": "Ready for Collection", "wip_limit": 10},
                    {"name": "Collecting", "wip_limit": 6}, {"name": "Analysis", "wip_limit": 5},
                    {"name": "Adjudication", "wip_limit": 4}, {"name": "Complete", "wip_limit": 0}
                ],
                "tasks": [
                    {"title": "Approve purpose, hypothesis, objectives, and critical questions", "type": "Approval", "priority": "Critical", "offset": 10, "effort": 24},
                    {"title": "Build measures and data collection plan", "type": "Deliverable", "priority": "High", "offset": 25, "effort": 80},
                    {"title": "Validate instruments, collectors, and evidence handling", "type": "Approval", "priority": "High", "offset": 40, "effort": 48},
                    {"title": "Execute event data collection", "type": "Task", "priority": "Critical", "offset": 65, "effort": 200},
                    {"title": "Analyze and adjudicate findings", "type": "Summary", "priority": "High", "offset": 85, "effort": 120},
                    {"title": "Deliver executive report and action tracker", "type": "Deliverable", "priority": "Critical", "offset": 100, "effort": 64}
                ],
                "milestones": [
                    {"title": "Assessment plan approved", "offset": 40, "critical": True},
                    {"title": "On-site execution complete", "offset": 65, "critical": True},
                    {"title": "Final report accepted", "offset": 100, "critical": True}
                ]
            }
        },
        {
            "code": "DATASTD", "name": "Data and Standards Initiative", "category": "Data and Standards",
            "description": "Standards modernization blueprint with governance, engineering, conformance support, and transition evidence.",
            "blueprint": {
                "columns": [
                    {"name": "Candidate", "wip_limit": 0}, {"name": "Governance Review", "wip_limit": 5},
                    {"name": "Engineering", "wip_limit": 6}, {"name": "Validation", "wip_limit": 4}, {"name": "Published", "wip_limit": 0}
                ],
                "tasks": [
                    {"title": "Confirm authoritative baseline and stakeholder need", "type": "Approval", "priority": "High", "offset": 10, "effort": 32},
                    {"title": "Develop canonical model and change package", "type": "Deliverable", "priority": "High", "offset": 50, "effort": 160},
                    {"title": "Conduct implementation and conformance-support review", "type": "Task", "priority": "High", "offset": 70, "effort": 96},
                    {"title": "Resolve comments and publish transition package", "type": "Deliverable", "priority": "Critical", "offset": 95, "effort": 80}
                ],
                "milestones": [
                    {"title": "Change package accepted for coordination", "offset": 50, "critical": True},
                    {"title": "Validation evidence complete", "offset": 70, "critical": True},
                    {"title": "Publication decision", "offset": 95, "critical": True}
                ]
            }
        }
    ]
    for spec in templates:
        if not db.query(ProjectTemplate).filter_by(code=spec["code"], version=1).first():
            db.add(ProjectTemplate(code=spec["code"], name=spec["name"], description=spec["description"], version=1, category=spec["category"], blueprint=spec["blueprint"], created_by_id=admin.id if admin else None))

    # Preserve initial working-note evidence in a revision stream.
    for task in db.query(Task).filter(Task.notes != "").all():
        if db.query(TaskNoteRevision).filter(TaskNoteRevision.task_id == task.id).count() == 0:
            db.add(TaskNoteRevision(task_id=task.id, author_id=task.owner_id or (admin.id if admin else task.owner_id), revision=1, body=task.notes, change_summary="Initial imported working notes"))

    # Seed approved status reports for executive comparison and governed reporting roll-up.
    if admin:
        for index, project in enumerate(projects[:8]):
            if db.query(StatusReport).filter(StatusReport.project_id == project.id).count() == 0:
                period_end = date.today() - timedelta(days=(index % 3) * 14)
                report = StatusReport(
                    human_id=f"SR-26-{index + 1:03d}", project_id=project.id,
                    period_start=period_end - timedelta(days=13), period_end=period_end, version=1,
                    status="Approved", health=project.health_owner, percent_complete=project.percent_complete,
                    accomplishments=f"Advanced the approved scope for {project.title} and retained supporting evidence.",
                    planned_work="Resolve open dependencies, complete the next milestone, and update acceptance evidence.",
                    decisions_required="Leadership decision required on capacity or dependency escalation." if project.health_owner in {"At Risk", "Off Track", "Blocked"} else "No immediate leadership decision required.",
                    risks_and_dependencies="See linked RAID and dependency records in the authoritative project workspace.",
                    summary=f"{project.human_id} is {project.health_owner.lower()} at {project.percent_complete}% complete. Current evidence is sourced from project tasks, milestones, RAID, dependencies, resources, and financial records.",
                    submitted_by_id=project.manager_id, submitted_at=datetime.now(timezone.utc) - timedelta(days=2),
                    approved_by_id=admin.id, approved_at=datetime.now(timezone.utc) - timedelta(days=1),
                )
                db.add(report)
    db.flush()


def ensure_v050_reference_data(db: Session) -> None:
    admin = db.query(User).filter_by(username="admin").first()
    pmo = db.query(User).filter_by(username="pmo").first() or admin
    approver = db.query(User).filter_by(username="approver").first() or admin
    if not admin:
        return
    connections = [
        ("PROJECTOS-MOCK", "ProjectOS Local Sandbox", "ProjectOS", "Mock", True),
        ("M365", "Microsoft 365 / Graph", "Microsoft Graph", "Disabled", False),
        ("SHAREPOINT", "SharePoint", "SharePoint", "Disabled", False),
    ]
    for code, name, kind, mode, enabled in connections:
        if not db.query(IntegrationConnection).filter_by(code=code).first():
            db.add(IntegrationConnection(code=code, name=name, kind=kind, mode=mode, enabled=enabled, status="Healthy (Mock)" if mode=="Mock" else "Not Tested", created_by_id=admin.id))
    rules = [
        ("Demand", "status", "DDC5I-PM", ["DDC5I-PM"]),
        ("Project", "portfolio_id", "DDC5I-PM", ["DDC5I-PM"]),
        ("Task", "percent_complete", "ProjectOS", ["ProjectOS"]),
        ("FinancialRecord", "actual_cost", "Financial System", ["Financial System"]),
        ("User", "employment_status", "Workforce System", ["Workforce System"]),
    ]
    for entity, field, authority, writers in rules:
        if not db.query(FieldOwnershipRuleRecord).filter_by(entity_type=entity, field_name=field).first():
            db.add(FieldOwnershipRuleRecord(entity_type=entity, field_name=field, authoritative_system=authority, allowed_writers=writers))
    db.flush()
    if not db.query(PortfolioReview).count():
        portfolio = db.query(Portfolio).order_by(Portfolio.code).first()
        org = db.query(Organization).filter_by(org_type="Division").first()
        review = PortfolioReview(human_id="REV-26-001", title="FY26 Q4 Enterprise Portfolio Review", review_type="Portfolio Review", portfolio_id=portfolio.id if portfolio else None, org_id=None, period_start=date.today()-timedelta(days=90), period_end=date.today(), status="In Review", chair_id=approver.id, participant_ids=[admin.id, pmo.id, approver.id], summary="Review mission impact, capacity conflicts, funding posture, dependencies, and decisions required across the DDC5I portfolio.", decisions_required="Resolve at-risk delivery and approve capacity tradeoffs for the next reporting period.")
        db.add(review); db.flush()
        project = db.query(Project).filter(Project.status=="Active").order_by(Project.human_id).first()
        if project:
            db.add(PortfolioReviewItem(review_id=review.id, item_type="Decision", entity_type="Project", entity_id=project.id, title=f"Recovery decision for {project.human_id}", recommendation="Accelerate" if project.health_owner in {"At Risk","Off Track","Blocked"} else "Continue", rationale="Source record indicates schedule, dependency, capacity, and funding posture should be reviewed together.", owner_id=project.manager_id, sort_order=1))
    if not db.query(ResourceRequest).count():
        org = db.query(Organization).filter_by(org_type="Division").first(); project = db.query(Project).filter(Project.lead_org_id==org.id).first() if org else None
        db.add(ResourceRequest(human_id="RRQ-26-001", org_id=org.id, project_id=project.id if project else None, role_name="Data Engineer", skill="Semantic interoperability", requested_hours=240, period_start=date.today(), period_end=date.today()+timedelta(days=90), priority="High", status="Submitted", requested_by_id=project.manager_id if project else pmo.id, rationale="Resolve a forecast skill gap affecting a cross-division mission dependency."))
    if not db.query(FinancialTransaction).count():
        financial = db.query(FinancialRecord).first()
        if financial:
            db.add(FinancialTransaction(human_id="FIN-26-001", financial_record_id=financial.id, transaction_type="Commitment", amount=25000, transaction_date=date.today()-timedelta(days=10), reference="DEMO-COMMIT-001", source_system="DDC5I-PM", notes="Demonstration commitment retained for investment-review workflow.", created_by_id=admin.id))
    if not db.query(Scenario).count():
        scenario = Scenario(human_id="SCN-26-001", name="Enterprise 10 Percent Budget Reduction", scenario_type="Budget Change", baseline_date=date.today(), status="Draft", assumptions="Model a non-destructive reduction against selected project funding while preserving mission-critical and mandatory work.", created_by_id=pmo.id)
        db.add(scenario); db.flush()
        project = db.query(Project).filter(Project.status=="Active").order_by(Project.budget.desc()).first()
        if project:
            db.add(ScenarioChange(scenario_id=scenario.id, entity_type="Project", entity_id=project.id, field_name="budget", baseline_value=float(project.budget), proposed_value=float(project.budget)*0.9, rationale="Illustrate mission and portfolio effects of a constrained funding profile."))
    if not db.query(ReportPack).count():
        db.add(ReportPack(human_id="RPT-26-001", name="DDC5I Enterprise Portfolio Summary", pack_type="Executive Portfolio Summary", period_start=date.today()-timedelta(days=30), period_end=date.today(), status="Generated", sections=[{"title":"Portfolio health","value":db.query(Project).count(),"detail":"Seeded operational portfolio inventory"},{"title":"Demand pipeline","value":db.query(Demand).count(),"detail":"Seeded governed demand funnel"}], narrative="This source-grounded demonstration pack summarizes the current portfolio and demand pipeline without fabricating external facts.", generated_by_id=pmo.id))
    if not db.query(JobRun).count():
        db.add(JobRun(job_type="Initial v0.5.0 Seed Validation", status="Succeeded", started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc), attempts=1, result={"status":"reference data available"}, created_by_id=admin.id))
    # Keep upgraded databases synchronized with the packaged RTM evidence without
    # creating duplicate requirement rows.
    requirements_path = Path(__file__).parent / "data" / "requirements.json"
    for spec in json.loads(requirements_path.read_text(encoding="utf-8")):
        trace = db.query(RequirementTrace).filter_by(requirement_id=spec["requirement_id"]).first()
        if not trace:
            continue
        for field in ("implementation_status", "design_reference", "module_reference", "test_case", "uat_result", "release", "acceptance_notes", "decision_comments"):
            if field in spec:
                setattr(trace, field, spec[field])
    db.flush()

def seed_database(db: Session) -> None:
    if db.query(User).count() > 0:
        ensure_v040_reference_data(db)
        ensure_v050_reference_data(db)
        db.commit()
        return
    random.seed(42)
    enterprise = Organization(code="DDC5I", name="DDC5I Enterprise", org_type="Enterprise", narrative="DDC5I synchronizes command-and-control, data, standards, architecture, assessment, infrastructure, and integration portfolios to improve Joint and coalition decision advantage.")
    db.add(enterprise)
    db.flush()
    divisions: dict[str, Organization] = {}
    for code, name, narrative in DIVISIONS:
        org = Organization(code=code, name=name, parent_id=enterprise.id, narrative=narrative)
        db.add(org)
        divisions[code] = org
    db.flush()

    users: dict[str, User] = {}
    for username, full_name, role, _, sensitive in ROLE_USERS:
        u = _user(username, full_name, role, None, sensitive)
        db.add(u); users[username] = u
    first_names = ["Avery", "Cameron", "Drew", "Emerson", "Finley", "Harper", "Jamie", "Kendall", "Logan", "Micah", "Nico", "Peyton", "Quinn", "Reese", "Skyler", "Terry", "Val", "Winter", "Zion"]
    roles = ["DIVISION_CHIEF", "DIVISION_PORTFOLIO_MANAGER", "REQUESTER", "ASSESSOR", "PROJECT_MANAGER", "TEAM_MEMBER", "RESOURCE_MANAGER", "FINANCIAL_MANAGER", "BENEFITS_OWNER", "DATA_STEWARD", "SECURITY_REVIEWER"]
    for i, name in enumerate(first_names):
        code = DIVISIONS[i % len(DIVISIONS)][0]
        role = roles[i % len(roles)]
        username = f"{name.lower()}.{code.lower()}"
        u = _user(username, f"{name} {code}", role, divisions[code].id, sensitive=(role in {"SECURITY_REVIEWER", "DIVISION_CHIEF"}))
        if i < 6:
            u.roles = ["DIVISION_CHIEF", "DIVISION_PORTFOLIO_MANAGER"]
        db.add(u); users[username] = u
    db.flush()

    missions: dict[str, Mission] = {}
    for i, (code, title, description) in enumerate(MISSIONS):
        owner = divisions[DIVISIONS[i][0]]
        m = Mission(code=code, title=title, description=description, owner_org_id=owner.id, outcome=f"Measurable improvement in {title.lower()}.", measures=[{"name":"Outcome confidence","unit":"percent","target":80}])
        db.add(m); missions[code] = m
    db.flush()

    for i, (code, name, _) in enumerate(DIVISIONS):
        for j in range(2):
            db.add(CoreFunction(
                code=f"CF-{code}-{j+1:02d}",
                title=["Governance and Mission Support", "Technical Delivery and Assurance"][j],
                description=f"Recurring {name} core function supporting enterprise mission outcomes.",
                org_id=divisions[code].id,
                mission_id=list(missions.values())[(i+j) % len(missions)].id,
                health=["On Track", "At Risk", "On Track", "Blocked"][((i*2)+j) % 4],
                minimum_capacity_hours=640,
                allocated_capacity_hours=580 + (i*20) + j*40,
            ))
        db.add(Portfolio(code=f"PF-{code}", name=f"{code} Division Portfolio", org_id=divisions[code].id, description=f"Enterprise portfolio for {name}."))
    db.flush()

    demand_titles = [
        "Joint Assessment Evidence Repository", "Coalition API Interoperability Pilot", "Mission Thread Digital Baseline", "Zero Trust Data Exchange Demonstration", "Federated Data Catalog Expansion", "C5 Readiness Exception Dashboard", "Standards Change Proposal Automation", "Cross-Division Resource Planning", "Operational Data Product Certification", "Bold Quest Assessment Package", "NATO CWIX Integration Support", "ProjectOS Enterprise Connector", "Mission Partner Identity Federation", "Portfolio Governance Calendar", "Legacy Tracker Retirement", "AI-Ready Metadata Improvement", "JINTACCS Interface Standardization", "Dependency Analytics Pilot", "Executive Decision Brief Automation", "Sensitive Capability Gap Review",
    ]
    statuses = ["Draft", "Submitted", "Triage", "Clarification Required", "Assessment", "Awaiting Portfolio Recommendation", "Awaiting Decision", "Approved", "Deferred", "Declined", "Converted to Execution", "Submitted", "Assessment", "Approved", "Triage", "Awaiting Decision", "Approved", "Deferred", "Draft", "Assessment"]
    demands: list[Demand] = []
    sponsor_pool = [u for u in users.values() if "DIVISION_CHIEF" in u.roles] or list(users.values())
    requester_pool = [u for u in users.values() if set(u.roles).intersection({"REQUESTER","PROJECT_MANAGER","DIVISION_PORTFOLIO_MANAGER"})]
    for i, title in enumerate(demand_titles):
        div_code = DIVISIONS[i % 6][0]
        org = divisions[div_code]
        requester = requester_pool[i % len(requester_pool)]
        sponsor = sponsor_pool[i % len(sponsor_pool)]
        mission = list(missions.values())[i % len(missions)]
        d = Demand(
            human_id=f"DMD-26-{i+1:03d}", title=title,
            category=["Named Project", "Capability Gap", "Data and Standards Work", "Experiment", "Modernization Effort", "Technical Debt"][i % 6],
            status=statuses[i], sensitivity="Restricted" if i == 19 else "Controlled Unclassified",
            sponsor_id=sponsor.id, requester_id=requester.id, requesting_org_id=org.id, lead_org_id=org.id, mission_id=mission.id,
            purpose=f"Deliver {title.lower()} to improve DDC5I mission execution.", problem=f"Current processes for {title.lower()} are fragmented, manual, or lack authoritative visibility.", desired_end_state=f"A governed, measurable, and reusable capability for {title.lower()} is operational.", beneficiaries="DDC5I leadership, division staff, Joint Force mission partners", required_date=date.today()+timedelta(days=30+i*9), urgency=["Normal","High","Critical"][i%3], consequence_of_inaction="Decision latency, duplicated effort, reduced readiness, and increased mission risk.", preliminary_scope="Discover, design, implement, validate, transition, and measure value.", deliverables="Working capability; operational guide; decision brief; acceptance evidence", assumptions="Stakeholders provide SMEs and timely review.", dependencies_text="Enterprise identity, authoritative reference data, and division participation.", required_skills="Portfolio management; data engineering; UX; security; integration", rom_cost=150000 + i*45000, expected_benefits="Reduced decision latency, improved traceability, and increased delivery confidence.", confidence=["Low","Medium","High"][i%3], current_owner_id=(users["pmo"].id if statuses[i] not in {"Draft","Submitted"} else requester.id), next_action={"Draft":"Complete and submit intake","Submitted":"PMO completeness review","Triage":"Validate scope and route","Clarification Required":"Requester provides missing evidence","Assessment":"Complete scoring","Awaiting Portfolio Recommendation":"Portfolio recommendation","Awaiting Decision":"Leadership decision","Approved":"Initiate execution","Deferred":"Review at next decision forum","Declined":"Close with rationale","Converted to Execution":"Manage linked project"}[statuses[i]], target_decision_date=date.today()+timedelta(days=14+i), mandatory=(i in {2,10,16}), mandatory_rationale="Directed interoperability or governance requirement." if i in {2,10,16} else "",
        )
        if statuses[i] in {"Assessment","Awaiting Portfolio Recommendation","Awaiting Decision","Approved","Deferred","Declined","Converted to Execution"}:
            scores = {"mission_criticality":4+(i%2),"strategic_alignment":4,"operational_impact":3+(i%3)/2,"urgency":3+(i%2),"risk_reduction":3.5,"readiness_interoperability":4,"feasibility":3,"expected_value":3.5}
            d.score_total = calculate_weighted_score(scores)
        db.add(d); demands.append(d)
    db.flush()

    assessor_users = [u for u in users.values() if "ASSESSOR" in u.roles] or [users["pmo"]]
    for d in demands:
        if d.score_total is not None:
            for a_idx in range(2 if int(d.human_id[-1]) % 2 == 0 else 1):
                scores = {"mission_criticality":4.0+a_idx*.2,"strategic_alignment":4.0,"operational_impact":3.5,"urgency":3.0+a_idx*.5,"risk_reduction":3.5,"readiness_interoperability":4.0,"feasibility":3.0,"expected_value":3.5}
                db.add(Assessment(demand_id=d.id, assessor_id=assessor_users[a_idx % len(assessor_users)].id, scores=scores, rationale="Evidence supports strong mission alignment with manageable delivery risk.", confidence="Medium", total_score=calculate_weighted_score(scores)))

    portfolios = {p.org_id:p for p in db.query(Portfolio).all()}
    active_titles = [
        "Enterprise Portfolio MVP", "Joint Assessment Command Center", "NCDF Standards Modernization", "Coalition API Gateway Pilot", "Mission Thread Architecture Repository", "Zero Trust Demonstration Support", "Data Product Command Center", "C5 Readiness Dashboard", "CWIX 2027 Preparation", "JINTACCS XML Modernization", "Resource and Skills Baseline", "Records and Evidence Modernization",
    ]
    completed_titles = ["Bold Quest 2025 Assessment", "Data Catalog Initial Load", "Governance Operating Model Sprint"]
    archived_titles = ["Legacy Spreadsheet Consolidation Pilot", "Retired Status Portal"]
    project_titles = active_titles + completed_titles + archived_titles
    projects: list[Project] = []
    pm_users = [u for u in users.values() if "PROJECT_MANAGER" in u.roles] or [users["pmo"]]
    for i, title in enumerate(project_titles):
        div_code = DIVISIONS[i % 6][0]; org=divisions[div_code]; mission=list(missions.values())[i%6]
        status = "Active" if i < 12 else "Completed" if i < 15 else "Archived"
        health = ["On Track","At Risk","On Track","Off Track","Blocked","On Track"][i%6] if status=="Active" else "Completed"
        p = Project(human_id=f"PRJ-26-{i+1:03d}", title=title, description=f"Deliver {title.lower()} through governed cross-division execution.", status=status, health_owner=health, health_calculated=health, lead_org_id=org.id, supporting_org_ids=[divisions[DIVISIONS[(i+1)%6][0]].id] if i%3==0 else [], portfolio_id=portfolios[org.id].id, sponsor_id=sponsor_pool[i%len(sponsor_pool)].id, manager_id=pm_users[i%len(pm_users)].id, mission_id=mission.id, demand_id=(demands[10].id if i==0 else None), desired_end_state=f"{title} is accepted, operational, and producing measurable value.", scope="Plan, build, test, transition, and measure.", deliverables="Capability increment; training; acceptance package", start_date=date.today()-timedelta(days=90+i*7), baseline_end_date=date.today()+timedelta(days=120-i*3), current_end_date=date.today()+timedelta(days=120-i*2+(14 if health in {"At Risk","Off Track","Blocked"} else 0)), percent_complete=100 if status=="Completed" else 0 if status=="Archived" else 25+(i*6)%70, budget=500000+i*125000, actual=210000+i*55000, forecast=520000+i*130000+(50000 if health in {"At Risk","Off Track"} else 0), benefit_expected=250000+i*35000, benefit_realized=180000 if status=="Completed" else i*5000, last_status_date=datetime.now(timezone.utc)-timedelta(days=(21 if i in {3,7} else i%9)))
        db.add(p); projects.append(p)
    db.flush()
    demands[10].status = "Converted to Execution"
    demands[10].disposition = f"Converted to {projects[0].human_id}"

    columns = ["Backlog", "Ready", "In Progress", "Review", "Done"]
    tasks: list[Task] = []
    for i in range(80):
        p = projects[i % 12]
        col = columns[i % len(columns)]
        complete = {"Backlog":0,"Ready":10,"In Progress":50,"Review":85,"Done":100}[col]
        task = Task(
            human_id=f"TSK-26-{i+1:04d}", project_id=p.id,
            title=f"{['Define','Design','Build','Validate','Transition'][i%5]} work package {i+1}",
            description=f"Execute the {['definition','design','build','validation','transition'][i%5]} activities, retain evidence, and coordinate affected stakeholders for {p.title}.",
            priority=["Low","Medium","High","Critical"][i%4],
            tags=[["planning","mission"],["design","architecture"],["delivery","integration"],["validation","evidence"]][i%4],
            status="Completed" if col=="Done" else "In Progress" if col in {"In Progress","Review"} else "Not Started",
            board_column=col, owner_id=pm_users[i%len(pm_users)].id,
            contributor_ids=[pm_users[(i+1)%len(pm_users)].id],
            start_date=date.today()-timedelta(days=i%30), due_date=date.today()+timedelta(days=7+(i%45)),
            estimated_effort=16+(i%5)*8, actual_effort=complete/100*(16+(i%5)*8), percent_complete=complete,
            checklist=[{"id":f"seed-{i}-definition","text":"Definition complete","done":complete>=25},{"id":f"seed-{i}-evidence","text":"Evidence attached","done":complete>=85}],
            notes="Coordinate with the accountable owner, document blockers, and capture handoff notes in this task workspace.",
            acceptance_evidence="Demonstration evidence reviewed and accepted." if col=="Done" else "",
            sequence=i+1, indent_level=i%3, baseline_due_date=date.today()+timedelta(days=5+(i%45))
        )
        db.add(task)
        tasks.append(task)
    db.flush()
    for i, task in enumerate(tasks[:24]):
        db.add(TaskComment(task_id=task.id, author_id=pm_users[(i+1)%len(pm_users)].id, body=f"Initial coordination note for {task.human_id}: confirm evidence owner and next review date.", mentions=[task.owner_id] if task.owner_id else []))
    for i in range(12):
        source = tasks[i]
        target = tasks[i+12]
        db.add(TaskRelationship(source_task_id=source.id, target_task_id=target.id, relationship_type=["Finish-to-start","Start-to-start","Finish-to-finish"][i%3], created_by_id=source.owner_id or users["admin"].id))
    for i in range(35):
        p=projects[i%12]; status="Completed" if i%6==0 else "At Risk" if i%7==0 else "In Progress"
        db.add(Milestone(human_id=f"MS-26-{i+1:03d}", project_id=p.id, title=f"{['Requirements approved','Prototype ready','Integration test','Operational demonstration','Transition decision'][i%5]}", baseline_date=date.today()+timedelta(days=i*8-40), current_date=date.today()+timedelta(days=i*8-40+(12 if status=="At Risk" else 0)), status=status, confidence="Low" if status=="At Risk" else "High" if status=="Completed" else "Medium", owner_id=pm_users[i%len(pm_users)].id, critical=(i%4==0)))
    for i in range(20):
        p=projects[i%12]; typ=["Risk","Issue","Assumption","Roadblock"][i%4]; sev=["Low","Medium","High","Critical"][i%4]
        db.add(RaidItem(human_id=f"RAID-26-{i+1:03d}", project_id=p.id, type=typ, title=f"{typ}: {['SME availability','External interface delay','Funding timing','Evidence quality'][i%4]}", description="Seeded assurance record supporting exception-focused management.", owner_id=pm_users[i%len(pm_users)].id, status="Open" if i%5 else "Mitigated", severity=sev, likelihood=["Unlikely","Possible","Likely"][i%3], consequence="May affect schedule, confidence, cost, or operational acceptance.", exposure=(i%4+1)*(i%3+1), mitigation="Assign accountable owner, monitor trigger, and execute contingency.", due_date=date.today()+timedelta(days=10+i*3), escalation_level="Enterprise" if sev=="Critical" else "Division", impacted_missions=list(missions.keys())[i%6]))
    for i in range(15):
        source=projects[i%12]; target=projects[(i+3)%12]
        db.add(Dependency(human_id=f"DEP-26-{i+1:03d}", source_project_id=source.id, target_project_id=target.id, title=f"{source.title} requires output from {target.title}", status="At Risk" if i%5==0 else "Open", owner_id=pm_users[i%len(pm_users)].id, due_date=date.today()+timedelta(days=20+i*4), impact="Schedule and acceptance evidence depend on timely delivery.", external_party="NCIA" if i%4==0 else ""))

    decision_demands = [d for d in demands if d.status in {"Approved","Deferred","Declined","Converted to Execution","Awaiting Decision"}][:10]
    for i, d in enumerate(decision_demands):
        decision = "Approve" if d.status in {"Approved","Converted to Execution"} else "Defer" if d.status in {"Deferred","Awaiting Decision"} else "Decline"
        dec=Decision(human_id=f"DEC-26-{i+1:03d}", demand_id=d.id, decision=decision, authority_id=users["approver"].id, participants="DDC5I leadership; division chief; portfolio manager", rationale="Mission value and urgency justify the documented disposition, subject to capacity and evidence conditions.", evidence="Assessment score, cost estimate, mission alignment, dependency review", conditions="Provide monthly status; resolve critical dependency before Gate 5." if decision=="Approve" else "Reassess during next quarterly review.", caveats="Confidence is based on ROM estimates.", resource_implications="Requires cross-division SME support.", financial_implications=f"ROM ${float(d.rom_cost):,.0f}", review_date=date.today()+timedelta(days=60+i*10))
        db.add(dec); db.flush()
        if decision=="Approve":
            db.add(Action(human_id=next_action_id(db), demand_id=d.id, decision_id=dec.id, title="Resolve decision condition and attach evidence", owner_id=d.current_owner_id or users["pmo"].id, due_date=date.today()+timedelta(days=30+i*2)))
    while db.query(Decision).count() < 10:
        p = projects[db.query(Decision).count() % 12]
        db.add(Decision(human_id=f"DEC-26-{db.query(Decision).count()+1:03d}", project_id=p.id, decision="Continue", authority_id=users["approver"].id, participants="Portfolio review forum", rationale="Continue execution with the current approved baseline while monitoring documented exceptions.", evidence="Current status report and RAID review", conditions="Escalate any new critical dependency within two business days.", review_date=date.today()+timedelta(days=45)))
        db.flush()

    while db.query(Action).count() < 12:
        i=db.query(Action).count()+1; p=projects[i%12]
        db.add(Action(human_id=next_action_id(db), project_id=p.id, title=f"Leadership action for {p.title}", owner_id=p.manager_id, status="Open", due_date=date.today()+timedelta(days=7+i*3), source_type="Roadblock response"))

    for i, (code, _, _) in enumerate(DIVISIONS):
        org=divisions[code]
        for j, role in enumerate(["Portfolio Manager","Project Manager","Data Engineer","Security Engineer"]):
            capacity=640.0
            allocated=560 + i*18 + j*25
            db.add(ResourceCapacity(org_id=org.id, role_name=role, skill=["Portfolio governance","Delivery management","Data integration","Zero Trust"][j], period="FY26-Q4", capacity_hours=capacity, allocated_hours=allocated, actual_hours=allocated*0.72, minimum_core_coverage=160 if j<2 else 80))
    for i,p in enumerate(projects[:12]):
        db.add(FinancialRecord(project_id=p.id, category=["Labor","Technology","Travel","Support"][i%4], approved_budget=p.budget, actual_cost=p.actual, forecast=p.forecast, minimum_viable=float(p.budget)*0.7, full_requirement=float(p.budget)*1.15, funding_status="Underfunded" if i%5==0 else "Funded", fiscal_year=2026, restricted_rate_notes="Restricted workforce rate details are not exposed in general dashboards."))
        db.add(Benefit(project_id=p.id, title=f"Operational value from {p.title}", benefit_type=["Operational","Cost Avoidance","Readiness","Interoperability"][i%4], target_value=80+i, realized_value=(30+i*3 if p.status=="Active" else 90), unit="benefit index", status="Realizing" if p.status=="Active" else "Realized", owner_id=p.sponsor_id, review_date=date.today()+timedelta(days=45+i*5)))

    metric_defs = [
        ("at_risk_projects","Projects at risk","Active projects with effective health At Risk, Off Track, or Blocked.","COUNT(active projects where effective health in exception states)","Enterprise Portfolio Owner","At Risk ≥4; Critical ≥7","Owner and calculated health may differ until adjudicated."),
        ("decisions_required","Decisions required","Demands awaiting leadership disposition and open decision conditions.","COUNT(demands awaiting decision) + COUNT(overdue decision actions)","Approval Authority","Attention ≥3","Does not include decisions recorded in external systems."),
        ("capacity_utilization","Capacity utilization","Allocated division hours as a percentage of available capacity.","SUM(allocated hours) / SUM(capacity hours)","Resource Manager","At Risk >90%; Overallocated >100%","Role-based demand is an MVP estimate, not authoritative workforce data."),
        ("budget_variance","Forecast variance","Forecast minus approved budget for accessible projects.","SUM(forecast) - SUM(approved budget)","Financial Manager","At Risk >5%","ROM and forecast figures are demonstration data."),
        ("stale_records","Stale project records","Active projects without a status update in the last 14 days.","COUNT(active projects where last status date older than 14 days)","Data Steward","Attention ≥1","Reporting cadence is configurable in a future release."),
    ]
    for key,title,definition,formula,owner,thresholds,limitations in metric_defs:
        db.add(MetricDefinition(key=key,title=title,definition=definition,formula=formula,data_owner=owner,thresholds=thresholds,limitations=limitations))

    requirements_path = Path(__file__).parent / "data" / "requirements.json"
    for item in json.loads(requirements_path.read_text(encoding="utf-8")):
        db.add(RequirementTrace(**item))

    for i,u in enumerate(list(users.values())[:12]):
        db.add(Notification(user_id=u.id, title="Portfolio action assigned", message="Review the latest decision, milestone, or demand assignment in the authoritative record.", link="/my-work", notification_type="Assignment"))
    db.add(AuditEvent(actor_id=users["admin"].id, entity_type="System", entity_id="seed", action="DEMO_DATA_SEEDED", after_json={"demands":20,"projects":17,"tasks":80,"requirements":307}))
    db.flush()
    ensure_v040_reference_data(db)
    ensure_v050_reference_data(db)
    db.commit()


if __name__ == "__main__":
    from app.database import Base, SessionLocal, engine
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_database(session)
