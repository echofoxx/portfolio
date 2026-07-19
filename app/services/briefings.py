from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import (
    Action,
    Benefit,
    BriefingSection,
    Demand,
    Dependency,
    FinancialRecord,
    Milestone,
    Organization,
    PortfolioReview,
    Project,
    RaidItem,
    ResourceCapacity,
    StatusReport,
    TravelRequest,
    TripReport,
)

DEFAULT_BRIEFING_SECTIONS: list[tuple[str, str]] = [
    ("mission-context", "Mission and operating context"),
    ("executive-summary", "Executive summary"),
    ("accomplishments", "Major accomplishments"),
    ("portfolio-health", "Portfolio health"),
    ("leadership-attention", "Projects requiring leadership attention"),
    ("demand-pipeline", "Demand and upcoming work"),
    ("milestones", "Milestones and delivery commitments"),
    ("risks-dependencies", "Risks, issues, and dependencies"),
    ("workforce-capacity", "Workforce and capacity"),
    ("investment-position", "Investment and financial position"),
    ("benefits-outcomes", "Benefits and mission outcomes"),
    ("cross-division", "Cross-division coordination"),
    ("travel-engagements", "Travel, forums, and external engagement outcomes"),
    ("decisions-required", "Decisions and assistance required"),
    ("next-30-60-90", "Next 30 / 60 / 90-day priorities"),
    ("prior-actions", "Previous-review action status"),
]


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value else None


RESTRICTED_SENSITIVITIES = {"restricted", "sensitive", "limited distribution"}


def division_briefing_payload(db: Session, review: PortfolioReview) -> dict[str, Any]:
    org = db.get(Organization, review.org_id) if review.org_id else None
    project_query = db.query(Project)
    demand_query = db.query(Demand)
    resource_query = db.query(ResourceCapacity)
    if review.org_id:
        project_query = project_query.filter(Project.lead_org_id == review.org_id)
        demand_query = demand_query.filter(Demand.lead_org_id == review.org_id)
        resource_query = resource_query.filter(ResourceCapacity.org_id == review.org_id)

    scoped_projects = project_query.order_by(Project.human_id).all()
    scoped_demands = demand_query.order_by(Demand.human_id).all()
    projects = [p for p in scoped_projects if (p.sensitivity or "").strip().lower() not in RESTRICTED_SENSITIVITIES]
    demands = [d for d in scoped_demands if (d.sensitivity or "").strip().lower() not in RESTRICTED_SENSITIVITIES]
    excluded_sensitive_projects = len(scoped_projects) - len(projects)
    excluded_sensitive_demands = len(scoped_demands) - len(demands)
    project_ids = [p.id for p in projects]
    milestones = db.query(Milestone).filter(Milestone.project_id.in_(project_ids)).order_by(Milestone.current_date).all() if project_ids else []
    raid = db.query(RaidItem).filter(RaidItem.project_id.in_(project_ids), RaidItem.status != "Closed").order_by(RaidItem.exposure.desc()).all() if project_ids else []
    dependencies = db.query(Dependency).filter(Dependency.source_project_id.in_(project_ids), Dependency.status != "Closed").order_by(Dependency.due_date).all() if project_ids else []
    resources = resource_query.order_by(ResourceCapacity.period, ResourceCapacity.role_name).all()
    financials = db.query(FinancialRecord).filter(FinancialRecord.project_id.in_(project_ids)).all() if project_ids else []
    benefits = db.query(Benefit).filter(Benefit.project_id.in_(project_ids)).all() if project_ids else []
    actions = db.query(Action).filter(Action.project_id.in_(project_ids), Action.status != "Closed").order_by(Action.due_date).all() if project_ids else []
    latest_reports: list[StatusReport] = []
    for project_id in project_ids:
        report = db.query(StatusReport).filter(StatusReport.project_id == project_id, StatusReport.status == "Approved").order_by(StatusReport.period_end.desc(), StatusReport.version.desc()).first()
        if report:
            latest_reports.append(report)

    project_map = {p.id: p for p in projects}
    health = Counter((p.health_override or p.health_owner or "Not Reported") for p in projects)
    active_projects = [p for p in projects if p.status not in {"Completed", "Cancelled"}]
    attention_projects = [p for p in active_projects if (p.health_override or p.health_owner) in {"At Risk", "Off Track", "Blocked", "Not Reported"}]
    def is_stale(project: Project) -> bool:
        if not project.last_status_date:
            return True
        last_status = project.last_status_date
        if last_status.tzinfo is None:
            last_status = last_status.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last_status).days > 30

    stale_projects = [p for p in active_projects if is_stale(p)]
    critical_milestones = [m for m in milestones if m.critical and m.status != "Completed"]
    open_demands = [d for d in demands if d.status not in {"Converted to Execution", "Declined", "Deferred"}]
    high_raid = [r for r in raid if r.severity in {"High", "Critical"} or r.exposure >= 12]
    overdue_actions = [a for a in actions if a.due_date and a.due_date < date.today()]
    travel_query = db.query(TravelRequest).filter(
        TravelRequest.departure_date <= review.period_end,
        TravelRequest.return_date >= review.period_start,
    )
    report_query = db.query(TripReport).filter(
        TripReport.start_date <= review.period_end,
        TripReport.return_date >= review.period_start,
    )
    if review.org_id:
        travel_query = travel_query.filter(TravelRequest.org_id == review.org_id)
        report_query = report_query.filter(TripReport.org_id == review.org_id)
    scoped_travel = travel_query.order_by(TravelRequest.departure_date).all()
    scoped_trip_reports = report_query.order_by(TripReport.return_date).all()
    travel_requests = [item for item in scoped_travel if (item.sensitivity or "").strip().lower() not in RESTRICTED_SENSITIVITIES]
    trip_reports = [item for item in scoped_trip_reports if (item.sensitivity or "").strip().lower() not in RESTRICTED_SENSITIVITIES]
    travel_estimated_cost = sum(_money(item.estimated_cost) for item in travel_requests)
    travel_reports_awaiting_review = sum(item.review_status not in {"Reviewed", "Closed"} for item in trip_reports)
    travel_reconciliation = sum(not item.request_id for item in trip_reports)

    total_capacity = sum(float(r.capacity_hours or 0) for r in resources)
    total_allocated = sum(float(r.allocated_hours or 0) for r in resources)
    total_actual_hours = sum(float(r.actual_hours or 0) for r in resources)
    utilization = round((total_allocated / total_capacity * 100), 1) if total_capacity else 0.0
    budget = sum(_money(f.approved_budget) for f in financials) or sum(_money(p.budget) for p in projects)
    actual = sum(_money(f.actual_cost) for f in financials) or sum(_money(p.actual) for p in projects)
    forecast = sum(_money(f.forecast) for f in financials) or sum(_money(p.forecast) for p in projects)
    target_benefit = sum(float(b.target_value or 0) for b in benefits)
    realized_benefit = sum(float(b.realized_value or 0) for b in benefits)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {"start": review.period_start.isoformat(), "end": review.period_end.isoformat()},
        "scope": {"org_id": review.org_id, "code": org.code if org else "ENT", "name": org.name if org else "Enterprise"},
        "metrics": {
            "projects": len(projects),
            "active_projects": len(active_projects),
            "attention_projects": len(attention_projects),
            "stale_projects": len(stale_projects),
            "open_demands": len(open_demands),
            "critical_milestones": len(critical_milestones),
            "open_high_risks": len(high_raid),
            "open_dependencies": len(dependencies),
            "open_actions": len(actions),
            "overdue_actions": len(overdue_actions),
            "budget": round(budget, 2),
            "actual": round(actual, 2),
            "forecast": round(forecast, 2),
            "forecast_variance": round(forecast - budget, 2),
            "capacity_hours": round(total_capacity, 1),
            "allocated_hours": round(total_allocated, 1),
            "actual_hours": round(total_actual_hours, 1),
            "utilization": utilization,
            "benefit_target": round(target_benefit, 2),
            "benefit_realized": round(realized_benefit, 2),
            "excluded_sensitive_projects": excluded_sensitive_projects,
            "excluded_sensitive_demands": excluded_sensitive_demands,
            "travel_requests": len(travel_requests),
            "trip_reports": len(trip_reports),
            "travel_estimated_cost": round(travel_estimated_cost, 2),
            "travel_reports_awaiting_review": travel_reports_awaiting_review,
            "travel_reconciliation": travel_reconciliation,
            "excluded_sensitive_travel": len(scoped_travel) - len(travel_requests),
            "excluded_sensitive_trip_reports": len(scoped_trip_reports) - len(trip_reports),
        },
        "security_notice": "Restricted, Sensitive, and Limited Distribution project and demand records are excluded from the standard division briefing payload.",
        "health_counts": dict(health),
        "projects": [
            {
                "id": p.id,
                "human_id": p.human_id,
                "title": p.title,
                "status": p.status,
                "health": p.health_override or p.health_owner,
                "percent_complete": p.percent_complete,
                "budget": _money(p.budget),
                "forecast": _money(p.forecast),
                "current_end_date": _iso(p.current_end_date),
                "last_status_date": _iso(p.last_status_date),
            }
            for p in projects
        ],
        "attention_projects": [
            {"id": p.id, "human_id": p.human_id, "title": p.title, "health": p.health_override or p.health_owner, "percent_complete": p.percent_complete}
            for p in attention_projects
        ],
        "demands": [
            {"id": d.id, "human_id": d.human_id, "title": d.title, "status": d.status, "urgency": d.urgency, "next_action": d.next_action}
            for d in open_demands
        ],
        "milestones": [
            {"id": m.id, "project_id": m.project_id, "project": project_map[m.project_id].human_id if m.project_id in project_map else "", "title": m.title, "date": _iso(m.current_date), "status": m.status, "critical": bool(m.critical), "confidence": m.confidence}
            for m in critical_milestones[:20]
        ],
        "raid": [
            {"id": r.id, "project_id": r.project_id, "project": project_map[r.project_id].human_id if r.project_id in project_map else "", "human_id": r.human_id, "type": r.type, "title": r.title, "severity": r.severity, "status": r.status, "due_date": _iso(r.due_date)}
            for r in high_raid[:20]
        ],
        "dependencies": [
            {"id": d.id, "project_id": d.source_project_id, "project": project_map[d.source_project_id].human_id if d.source_project_id in project_map else "", "human_id": d.human_id, "title": d.title, "status": d.status, "due_date": _iso(d.due_date), "external_party": d.external_party}
            for d in dependencies[:20]
        ],
        "resource_gaps": [
            {"id": r.id, "role": r.role_name, "skill": r.skill, "period": r.period, "capacity": round(float(r.capacity_hours or 0), 1), "allocated": round(float(r.allocated_hours or 0), 1), "gap": round(float(r.capacity_hours or 0) - float(r.allocated_hours or 0), 1)}
            for r in resources if float(r.allocated_hours or 0) > float(r.capacity_hours or 0) or float(r.minimum_core_coverage or 0) > max(0, float(r.capacity_hours or 0) - float(r.allocated_hours or 0))
        ],
        "financials": [
            {"id": f.id, "project_id": f.project_id, "project": project_map[f.project_id].human_id if f.project_id in project_map else "", "budget": _money(f.approved_budget), "actual": _money(f.actual_cost), "forecast": _money(f.forecast), "funding_status": f.funding_status}
            for f in financials
        ],
        "benefits": [
            {"id": b.id, "project_id": b.project_id, "project": project_map[b.project_id].human_id if b.project_id in project_map else "", "title": b.title, "target": float(b.target_value or 0), "realized": float(b.realized_value or 0), "unit": b.unit, "status": b.status}
            for b in benefits
        ],
        "actions": [
            {"id": a.id, "human_id": a.human_id, "project_id": a.project_id, "title": a.title, "owner_id": a.owner_id, "status": a.status, "due_date": _iso(a.due_date), "overdue": bool(a.due_date and a.due_date < date.today())}
            for a in actions
        ],
        "status_reports": [
            {"id": r.id, "human_id": r.human_id, "project_id": r.project_id, "project": project_map[r.project_id].human_id if r.project_id in project_map else "", "period_end": _iso(r.period_end), "health": r.health, "percent_complete": r.percent_complete, "summary": r.summary, "accomplishments": r.accomplishments, "planned_work": r.planned_work, "decisions_required": r.decisions_required}
            for r in latest_reports
        ],
        "travel_requests": [
            {"id": item.id, "human_id": item.human_id, "external_id": item.external_id, "traveler": item.traveler_name, "location": item.location,
             "determination": item.determination, "departure_date": _iso(item.departure_date), "return_date": _iso(item.return_date),
             "estimated_cost": _money(item.estimated_cost), "engagement_id": item.engagement_id}
            for item in travel_requests
        ],
        "trip_reports": [
            {"id": item.id, "human_id": item.human_id, "title": item.title, "traveler": item.traveler_name, "location": item.location,
             "return_date": _iso(item.return_date), "review_status": item.review_status, "request_id": item.request_id,
             "match_confidence": item.match_confidence, "key_findings": item.key_findings, "recommendations": item.recommendations, "action_items": item.action_items}
            for item in trip_reports
        ],
    }


def section_source_summary(section_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    metrics = payload.get("metrics", {})
    mappings: dict[str, dict[str, Any]] = {
        "mission-context": {"scope": payload.get("scope"), "period": payload.get("period")},
        "executive-summary": {"metrics": metrics, "health_counts": payload.get("health_counts", {})},
        "accomplishments": {"status_reports": payload.get("status_reports", [])},
        "portfolio-health": {"metrics": metrics, "health_counts": payload.get("health_counts", {}), "projects": payload.get("projects", [])},
        "leadership-attention": {"attention_projects": payload.get("attention_projects", [])},
        "demand-pipeline": {"demands": payload.get("demands", [])},
        "milestones": {"milestones": payload.get("milestones", [])},
        "risks-dependencies": {"raid": payload.get("raid", []), "dependencies": payload.get("dependencies", [])},
        "workforce-capacity": {"capacity": {k: metrics.get(k) for k in ("capacity_hours", "allocated_hours", "actual_hours", "utilization")}, "resource_gaps": payload.get("resource_gaps", [])},
        "investment-position": {"financial_metrics": {k: metrics.get(k) for k in ("budget", "actual", "forecast", "forecast_variance")}, "financials": payload.get("financials", [])},
        "benefits-outcomes": {"benefit_metrics": {k: metrics.get(k) for k in ("benefit_target", "benefit_realized")}, "benefits": payload.get("benefits", [])},
        "cross-division": {"dependencies": [d for d in payload.get("dependencies", []) if d.get("external_party")]},
        "travel-engagements": {"travel_metrics": {k: metrics.get(k) for k in ("travel_requests", "trip_reports", "travel_estimated_cost", "travel_reports_awaiting_review", "travel_reconciliation")}, "travel_requests": payload.get("travel_requests", []), "trip_reports": payload.get("trip_reports", [])},
        "decisions-required": {"attention_projects": payload.get("attention_projects", []), "milestones": payload.get("milestones", []), "raid": payload.get("raid", [])},
        "next-30-60-90": {"projects": payload.get("projects", []), "demands": payload.get("demands", [])},
        "prior-actions": {"actions": payload.get("actions", [])},
    }
    return mappings.get(section_key, {})


def ensure_briefing_sections(db: Session, review: PortfolioReview, owner_id: str | None = None) -> tuple[list[BriefingSection], dict[str, Any]]:
    payload = division_briefing_payload(db, review)
    existing = {s.section_key: s for s in db.query(BriefingSection).filter_by(review_id=review.id).all()}
    for order, (section_key, title) in enumerate(DEFAULT_BRIEFING_SECTIONS, 1):
        section = existing.get(section_key)
        if not section:
            section = BriefingSection(review_id=review.id, section_key=section_key, title=title, owner_id=owner_id, sort_order=order)
            db.add(section)
            existing[section_key] = section
        section.source_summary = section_source_summary(section_key, payload)
    db.flush()
    return sorted(existing.values(), key=lambda section: section.sort_order), payload
