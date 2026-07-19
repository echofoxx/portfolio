from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    DataQualityIssue,
    Demand,
    Dependency,
    FinancialRecord,
    Milestone,
    Project,
    RaidItem,
    RequirementTrace,
    ResourceCapacity,
    Scenario,
    ScenarioChange,
    ScenarioResult,
    StatusReport,
    Task,
    TravelRequest,
    TripReport,
)


def projectos_payload(db: Session, project: Project) -> dict[str, Any]:
    tasks = db.query(Task).filter(Task.project_id == project.id).order_by(Task.sequence).all()
    milestones = db.query(Milestone).filter(Milestone.project_id == project.id).order_by(Milestone.current_date).all()
    return {
        "schema_version": "1.0",
        "canonical_id": project.id,
        "stable_id": project.human_id,
        "title": project.title,
        "status": project.status,
        "health": project.health_override or project.health_owner,
        "percent_complete": project.percent_complete,
        "lead_org_id": project.lead_org_id,
        "mission_id": project.mission_id,
        "tasks": [
            {
                "canonical_id": task.id,
                "stable_id": task.human_id,
                "title": task.title,
                "status": task.status,
                "board_column": task.board_column,
                "percent_complete": task.percent_complete,
                "owner_id": task.owner_id,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "updated_at": task.updated_at.isoformat(),
            }
            for task in tasks
        ],
        "milestones": [
            {
                "canonical_id": milestone.id,
                "stable_id": milestone.human_id,
                "title": milestone.title,
                "status": milestone.status,
                "current_date": milestone.current_date.isoformat() if milestone.current_date else None,
                "critical": milestone.critical,
            }
            for milestone in milestones
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def scenario_baseline(db: Session, scenario: Scenario) -> dict[str, float]:
    projects = db.query(Project)
    resources = db.query(ResourceCapacity)
    financials = db.query(FinancialRecord).join(Project, FinancialRecord.project_id == Project.id)
    if scenario.org_id:
        projects = projects.filter(Project.lead_org_id == scenario.org_id)
        resources = resources.filter(ResourceCapacity.org_id == scenario.org_id)
        financials = financials.filter(Project.lead_org_id == scenario.org_id)
    project_rows = projects.all()
    resource_rows = resources.all()
    financial_rows = financials.all()
    return {
        "portfolio_budget": sum(float(project.budget or 0) for project in project_rows),
        "portfolio_forecast": sum(float(project.forecast or 0) for project in project_rows),
        "at_risk_projects": float(sum(1 for project in project_rows if (project.health_override or project.health_owner) in {"At Risk", "Off Track", "Blocked"})),
        "active_projects": float(sum(1 for project in project_rows if project.status == "Active")),
        "capacity_hours": sum(float(row.capacity_hours or 0) for row in resource_rows),
        "allocated_hours": sum(float(row.allocated_hours or 0) for row in resource_rows),
        "approved_budget": sum(float(row.approved_budget or 0) for row in financial_rows),
        "financial_forecast": sum(float(row.forecast or 0) for row in financial_rows),
    }


def calculate_scenario(db: Session, scenario: Scenario) -> list[ScenarioResult]:
    baseline = scenario_baseline(db, scenario)
    projected = dict(baseline)
    changes = db.query(ScenarioChange).filter(ScenarioChange.scenario_id == scenario.id).all()
    for change in changes:
        proposed = change.proposed_value
        original = change.baseline_value
        if change.entity_type == "Project":
            if change.field_name == "budget":
                projected["portfolio_budget"] += float(proposed or 0) - float(original or 0)
            elif change.field_name == "forecast":
                projected["portfolio_forecast"] += float(proposed or 0) - float(original or 0)
            elif change.field_name == "health_owner":
                risky = {"At Risk", "Off Track", "Blocked"}
                projected["at_risk_projects"] += (1 if proposed in risky else 0) - (1 if original in risky else 0)
            elif change.field_name == "status":
                projected["active_projects"] += (1 if proposed == "Active" else 0) - (1 if original == "Active" else 0)
        elif change.entity_type == "ResourceCapacity":
            if change.field_name == "capacity_hours":
                projected["capacity_hours"] += float(proposed or 0) - float(original or 0)
            elif change.field_name == "allocated_hours":
                projected["allocated_hours"] += float(proposed or 0) - float(original or 0)
        elif change.entity_type == "FinancialRecord":
            if change.field_name == "approved_budget":
                projected["approved_budget"] += float(proposed or 0) - float(original or 0)
            elif change.field_name == "forecast":
                projected["financial_forecast"] += float(proposed or 0) - float(original or 0)
    db.query(ScenarioResult).filter(ScenarioResult.scenario_id == scenario.id).delete()
    labels = {
        "portfolio_budget": ("USD", "Total project budget after proposed changes."),
        "portfolio_forecast": ("USD", "Total project forecast after proposed changes."),
        "at_risk_projects": ("projects", "Count of projects in At Risk, Off Track, or Blocked health."),
        "active_projects": ("projects", "Count of active projects."),
        "capacity_hours": ("hours", "Available role-based capacity."),
        "allocated_hours": ("hours", "Planned allocation against available capacity."),
        "approved_budget": ("USD", "Approved budget represented by financial records."),
        "financial_forecast": ("USD", "Financial forecast represented by financial records."),
    }
    results: list[ScenarioResult] = []
    for key, baseline_value in baseline.items():
        scenario_value = projected[key]
        delta = scenario_value - baseline_value
        magnitude = abs(delta) / max(abs(baseline_value), 1)
        impact = "High" if magnitude >= 0.2 else "Medium" if magnitude >= 0.05 else "Low"
        unit, explanation = labels[key]
        result = ScenarioResult(
            scenario_id=scenario.id,
            metric_key=key,
            baseline_value=baseline_value,
            scenario_value=scenario_value,
            delta=delta,
            unit=unit,
            impact_level=impact,
            explanation=explanation,
        )
        db.add(result)
        results.append(result)
    scenario.status = "Compared"
    db.commit()
    return results


def _issue_id(db: Session) -> str:
    return f"DQ-26-{db.query(DataQualityIssue).count() + 1:04d}"


def upsert_quality_issue(
    db: Session,
    *,
    rule_code: str,
    entity_type: str,
    entity_id: str,
    org_id: str | None,
    severity: str,
    title: str,
    description: str,
    owner_id: str | None,
    due_date: date | None,
) -> DataQualityIssue:
    issue = db.query(DataQualityIssue).filter(
        DataQualityIssue.rule_code == rule_code,
        DataQualityIssue.entity_id == entity_id,
        DataQualityIssue.status != "Resolved",
    ).first()
    if issue:
        issue.severity = severity
        issue.title = title
        issue.description = description
        issue.owner_id = owner_id
        issue.due_date = due_date
        return issue
    issue = DataQualityIssue(
        human_id=_issue_id(db),
        rule_code=rule_code,
        entity_type=entity_type,
        entity_id=entity_id,
        org_id=org_id,
        severity=severity,
        title=title,
        description=description,
        owner_id=owner_id,
        due_date=due_date,
    )
    db.add(issue)
    db.flush()
    return issue


def scan_data_quality(db: Session, default_owner_id: str | None = None) -> list[DataQualityIssue]:
    today = date.today()
    now = datetime.now(timezone.utc)
    detected: list[DataQualityIssue] = []
    for project in db.query(Project).all():
        last = project.last_status_date
        if last and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last and (now - last).days > 30 and project.status == "Active":
            detected.append(upsert_quality_issue(
                db, rule_code="STALE-PROJECT-STATUS", entity_type="Project", entity_id=project.id,
                org_id=project.lead_org_id, severity="High", title=f"Stale status: {project.human_id}",
                description=f"Project status has not been refreshed for {(now-last).days} days.", owner_id=project.manager_id or default_owner_id,
                due_date=today + timedelta(days=5),
            ))
        if not project.mission_id:
            detected.append(upsert_quality_issue(
                db, rule_code="MISSING-ALIGNMENT", entity_type="Project", entity_id=project.id,
                org_id=project.lead_org_id, severity="High", title=f"Missing mission alignment: {project.human_id}",
                description="Every project must link to a mission, objective, or mandate.", owner_id=project.manager_id or default_owner_id,
                due_date=today + timedelta(days=10),
            ))
    for milestone in db.query(Milestone).filter(Milestone.current_date < today, Milestone.status.notin_(["Completed", "Closed"])).all():
        project = db.get(Project, milestone.project_id)
        detected.append(upsert_quality_issue(
            db, rule_code="OVERDUE-MILESTONE", entity_type="Milestone", entity_id=milestone.id,
            org_id=project.lead_org_id if project else None, severity="High" if milestone.critical else "Medium",
            title=f"Overdue milestone: {milestone.human_id}", description=f"{milestone.title} is past its current date and is not complete.",
            owner_id=milestone.owner_id or (project.manager_id if project else default_owner_id), due_date=today + timedelta(days=3),
        ))
    for dependency in db.query(Dependency).filter(Dependency.due_date < today, Dependency.status != "Closed").all():
        project = db.get(Project, dependency.source_project_id)
        detected.append(upsert_quality_issue(
            db, rule_code="OVERDUE-DEPENDENCY", entity_type="Dependency", entity_id=dependency.id,
            org_id=project.lead_org_id if project else None, severity="High", title=f"Overdue dependency: {dependency.human_id}",
            description=dependency.impact or dependency.title, owner_id=dependency.owner_id or default_owner_id, due_date=today + timedelta(days=3),
        ))
    for row in db.query(ResourceCapacity).all():
        if float(row.allocated_hours or 0) > float(row.capacity_hours or 0):
            detected.append(upsert_quality_issue(
                db, rule_code="RESOURCE-OVERALLOCATED", entity_type="ResourceCapacity", entity_id=row.id,
                org_id=row.org_id, severity="High", title=f"Overallocated resource role: {row.role_name}",
                description=f"Allocated {row.allocated_hours:.0f} hours against {row.capacity_hours:.0f} hours capacity for {row.period}.",
                owner_id=default_owner_id, due_date=today + timedelta(days=7),
            ))
    matched_request_ids = {item.request_id for item in db.query(TripReport).filter(TripReport.request_id.is_not(None)).all()}
    for request in db.query(TravelRequest).all():
        if request.return_date < request.departure_date:
            detected.append(upsert_quality_issue(
                db, rule_code="TRAVEL-DATE-SEQUENCE", entity_type="TravelRequest", entity_id=request.id,
                org_id=request.org_id, severity="High", title=f"Travel date sequence: {request.human_id}",
                description="The authoritative source lists a return date before the departure date. Source values were retained and require steward correction.",
                owner_id=default_owner_id, due_date=today + timedelta(days=5),
            ))
        if request.determination == "Approved" and request.report_due_date and request.report_due_date < today and request.id not in matched_request_ids:
            detected.append(upsert_quality_issue(
                db, rule_code="TRIP-REPORT-MISSING", entity_type="TravelRequest", entity_id=request.id,
                org_id=request.org_id, severity="Medium", title=f"Trip report due: {request.human_id}",
                description=f"Approved travel returned {request.return_date.isoformat()} and has no matched trip report.",
                owner_id=default_owner_id, due_date=today + timedelta(days=7),
            ))
    for report in db.query(TripReport).filter(TripReport.request_id.is_(None)).all():
        detected.append(upsert_quality_issue(
            db, rule_code="TRIP-REPORT-UNMATCHED", entity_type="TripReport", entity_id=report.id,
            org_id=report.org_id, severity="Medium", title=f"Trip report reconciliation: {report.human_id}",
            description="The trip report has no confirmed link to an approval-source travel request.",
            owner_id=default_owner_id, due_date=today + timedelta(days=7),
        ))
    for trace in db.query(RequirementTrace).filter(
        (RequirementTrace.implementation_status.in_(["Implemented", "Partially implemented"]))
    ).all():
        if not trace.design_reference or not trace.test_case:
            detected.append(upsert_quality_issue(
                db, rule_code="RTM-EVIDENCE-GAP", entity_type="RequirementTrace", entity_id=trace.id,
                org_id=None, severity="Medium", title=f"RTM evidence gap: {trace.requirement_id}",
                description="Implemented or partially implemented requirement is missing design or automated-test evidence.",
                owner_id=default_owner_id, due_date=today + timedelta(days=14),
            ))
    db.commit()
    return detected


def report_pack_sections(db: Session, org_id: str | None = None) -> list[dict[str, Any]]:
    projects = db.query(Project)
    demands = db.query(Demand)
    raids = db.query(RaidItem).join(Project, RaidItem.project_id == Project.id)
    dependencies = db.query(Dependency).join(Project, Dependency.source_project_id == Project.id)
    reports = db.query(StatusReport).join(Project, StatusReport.project_id == Project.id)
    if org_id:
        projects = projects.filter(Project.lead_org_id == org_id)
        demands = demands.filter(Demand.lead_org_id == org_id)
        raids = raids.filter(Project.lead_org_id == org_id)
        dependencies = dependencies.filter(Project.lead_org_id == org_id)
        reports = reports.filter(Project.lead_org_id == org_id)
    project_rows = projects.all()
    demand_rows = demands.all()
    return [
        {"title": "Portfolio health", "value": len(project_rows), "detail": f"{sum(1 for p in project_rows if (p.health_override or p.health_owner) in {'At Risk','Off Track','Blocked'})} require attention"},
        {"title": "Demand pipeline", "value": len(demand_rows), "detail": f"{sum(1 for d in demand_rows if d.status in {'Awaiting Decision','Awaiting Portfolio Recommendation'})} awaiting governance action"},
        {"title": "Open RAID", "value": raids.filter(RaidItem.status != 'Closed').count(), "detail": "Risks, assumptions, issues, and roadblocks requiring ownership"},
        {"title": "Open dependencies", "value": dependencies.filter(Dependency.status != 'Closed').count(), "detail": "Cross-project or external dependencies"},
        {"title": "Approved reports", "value": reports.filter(StatusReport.status == 'Approved').count(), "detail": "Approved reporting baselines in the selected scope"},
    ]
