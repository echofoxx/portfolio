from __future__ import annotations

import csv
import io
import json
import os
import re
import time
import zipfile
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlencode

import xlsxwriter
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session

from app.config import APP_VERSION, settings
from app.database import SessionLocal, get_db
from app.models import (
    Action,
    Assessment,
    DataQualityIssue,
    Delegation,
    BoardColumn,
    AuditEvent,
    Benefit,
    BriefingSection,
    BriefingSnapshot,
    CoreFunction,
    DashboardPreference,
    Decision,
    Demand,
    DemandRevision,
    DivisionProfile,
    Dependency,
    FinancialRecord,
    FinancialTransaction,
    FieldOwnershipRuleRecord,
    ImportBatch,
    IntegrationConnection,
    JobRun,
    ImportRow,
    MetricDefinition,
    Milestone,
    Mission,
    Notification,
    Organization,
    Portfolio,
    PortfolioReview,
    PortfolioReviewItem,
    Project,
    ProjectPromotionRequest,
    ProjectTemplate,
    RaidItem,
    RequirementTrace,
    ResourceCapacity,
    ResourceRequest,
    ReviewChangeRequest,
    ReviewNote,
    ReviewQuestion,
    ReportPack,
    SavedView,
    Scenario,
    ScenarioChange,
    ScenarioResult,
    StatusReport,
    Task,
    TaskAttachment,
    TaskComment,
    TaskNoteRevision,
    TaskRelationship,
    SyncRun,
    TravelApprovalStep,
    TravelEngagement,
    TravelEntityLink,
    TravelRequest,
    TripReport,
    TripReportItem,
    User,
)
from app.services.audit import record_audit, snapshot
from app.services.imports import validate_demand_rows
from app.services.resource_imports import RESOURCE_COLUMNS, validate_resource_rows
from app.services.scoring import DEFAULT_WEIGHTS, LABELS, calculate_weighted_score, score_variance
from app.services.security import (
    can_access_org,
    can_access_sensitive,
    can_edit_business_data,
    create_session_token,
    csrf_token,
    has_role,
    is_enterprise_user,
    read_session_token,
    verify_csrf,
    verify_password,
    hash_password,
)
from app.services.workflow import ALLOWED_TRANSITIONS, validate_transition
from app.services.storage import ALLOWED_EXTENSIONS, LocalVolumeStorage, validate_file_signature
from app.services.xlsx_reader import read_first_sheet_xlsx
from app.services.travel import (
    apply_best_match,
    commit_travel_request_result,
    commit_trip_report_result,
    ensure_report_items,
    match_candidates,
    refresh_engagement_rollups,
    resolve_location,
    travel_dashboard_payload,
    validate_travel_request_rows,
    validate_trip_report_rows,
)
from app.services.schedule import critical_path, gantt_layout, wbs_numbers, would_create_cycle
from app.services.v050 import calculate_scenario, projectos_payload, report_pack_sections, scan_data_quality
from app.services.briefings import division_briefing_payload, ensure_briefing_sections
from app.services.division_profiles import apply_profile_data, normalize_profile_data, profile_form_values, profile_to_dict

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title=settings.app_name,
    version=APP_VERSION,
    description="JSJ6 enterprise demand, portfolio, project, travel engagement, resource, investment, benefit, and traceability reference implementation.",
    docs_url=None,
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def normalize_badge(value: str | None) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value or "")


def money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def datefmt(value: Any) -> str:
    if not value:
        return "—"
    if isinstance(value, str):
        return value
    return value.strftime("%b %d, %Y")


templates.env.filters["badge"] = normalize_badge
templates.env.filters["money"] = money
templates.env.filters["datefmt"] = datefmt


def safe_local_path(value: str | None, default: str = "/dashboard") -> str:
    """Allow only a single-slash local absolute path for post-login redirects."""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return default
    return value


def flash_redirect(path: str, message: str, level: str = "success") -> RedirectResponse:
    sep = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{sep}message={quote_plus(message)}&level={quote_plus(level)}", status_code=303)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("ddc5i_session")
    user_id = read_session_token(token) if token else None
    user = db.get(User, user_id) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_csrf(request: Request, user: User, form_token: str | None = None, header_token: str | None = None) -> None:
    token = form_token or header_token
    if not verify_csrf(user.id, token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def require_roles(user: User, *roles: str) -> None:
    if not has_role(user, *roles):
        raise HTTPException(status_code=403, detail=f"Requires one of these roles: {', '.join(roles)}")


def require_business_edit(user: User) -> None:
    if not can_edit_business_data(user):
        raise HTTPException(status_code=403, detail="This role has read-only access")


def can_manage_division_profile(user: User, org_id: str) -> bool:
    if has_role(user, "ADMIN", "PMO", "ENTERPRISE_PORTFOLIO_OWNER", "DATA_STEWARD"):
        return True
    return can_access_org(user, org_id) and has_role(user, "DIVISION_CHIEF", "DIVISION_PORTFOLIO_MANAGER")


def require_division_profile_edit(user: User, org_id: str) -> None:
    if not can_manage_division_profile(user, org_id):
        raise HTTPException(status_code=403, detail="Requires division-profile publishing authority")


def scoped_projects(db: Session, user: User):
    query = db.query(Project)
    if not is_enterprise_user(user):
        query = query.filter(Project.lead_org_id == user.division_id)
    if not user.sensitive_access and not has_role(user, "ADMIN", "SECURITY_REVIEWER"):
        query = query.filter(Project.sensitivity != "Restricted")
    return query


def scope_project_join(query, user: User):
    """Apply the same organization and sensitivity rules to queries already joined to Project."""
    if not is_enterprise_user(user):
        query = query.filter(Project.lead_org_id == user.division_id)
    if not user.sensitive_access and not has_role(user, "ADMIN", "SECURITY_REVIEWER"):
        query = query.filter(Project.sensitivity != "Restricted")
    return query


def scoped_demands(db: Session, user: User):
    query = db.query(Demand)
    if not is_enterprise_user(user):
        query = query.filter(Demand.lead_org_id == user.division_id)
    if not user.sensitive_access and not has_role(user, "ADMIN", "SECURITY_REVIEWER"):
        query = query.filter(Demand.sensitivity != "Restricted")
    return query



def scoped_travel_requests(db: Session, user: User):
    query = db.query(TravelRequest)
    if not is_enterprise_user(user):
        query = query.filter(TravelRequest.org_id == user.division_id)
    if not user.sensitive_access and not has_role(user, "ADMIN", "SECURITY_REVIEWER"):
        query = query.filter(TravelRequest.sensitivity != "Restricted")
    return query


def scoped_trip_reports(db: Session, user: User):
    query = db.query(TripReport)
    if not is_enterprise_user(user):
        query = query.filter(TripReport.org_id == user.division_id)
    if not user.sensitive_access and not has_role(user, "ADMIN", "SECURITY_REVIEWER"):
        query = query.filter(TripReport.sensitivity != "Restricted")
    return query


def resolve_travel_entity_links(db: Session, user: User, links: list[TravelEntityLink]) -> list[dict[str, Any]]:
    """Resolve travel trace links into authorized, human-readable drill-through rows."""
    project_ids = {row.id for row in scoped_projects(db, user).all()}
    demand_ids = {row.id for row in scoped_demands(db, user).all()}
    resolved: list[dict[str, Any]] = []
    for link in links:
        record: Any | None = None
        url = ""
        subtitle = ""
        target_type = link.target_entity_type
        if target_type == "Action":
            record = db.get(Action, link.target_entity_id)
            if record and ((record.project_id and record.project_id not in project_ids) or (record.demand_id and record.demand_id not in demand_ids)):
                record = None
            url = f"/records/action/{link.target_entity_id}"
        elif target_type == "RaidItem":
            record = db.get(RaidItem, link.target_entity_id)
            if record and record.project_id not in project_ids:
                record = None
            url = f"/records/raid/{link.target_entity_id}"
        elif target_type == "Decision":
            record = db.get(Decision, link.target_entity_id)
            if record and ((record.project_id and record.project_id not in project_ids) or (record.demand_id and record.demand_id not in demand_ids)):
                record = None
            url = f"/records/decision/{link.target_entity_id}"
        elif target_type == "Dependency":
            record = db.get(Dependency, link.target_entity_id)
            if record and record.source_project_id not in project_ids:
                record = None
            url = f"/records/dependency/{link.target_entity_id}"
        elif target_type == "Project":
            record = scoped_projects(db, user).filter(Project.id == link.target_entity_id).first()
            url = f"/projects/{link.target_entity_id}"
        elif target_type == "Demand":
            record = scoped_demands(db, user).filter(Demand.id == link.target_entity_id).first()
            url = f"/demands/{link.target_entity_id}"
        if not record:
            continue
        title = getattr(record, "title", None) or getattr(record, "decision", None) or target_type
        human_id = getattr(record, "human_id", "")
        if getattr(record, "status", None):
            subtitle = str(record.status)
        elif target_type == "Decision":
            subtitle = "Decision record"
        resolved.append({
            "link": link,
            "target_type": target_type,
            "human_id": human_id,
            "title": title,
            "subtitle": subtitle,
            "url": url,
        })
    return resolved


def get_accessible_travel_request(db: Session, user: User, request_id: str) -> TravelRequest:
    record = scoped_travel_requests(db, user).filter(TravelRequest.id == request_id).first()
    if not record:
        raise HTTPException(404, "Travel request not found")
    return record


def get_accessible_trip_report(db: Session, user: User, report_id: str) -> TripReport:
    record = scoped_trip_reports(db, user).filter(TripReport.id == report_id).first()
    if not record:
        raise HTTPException(404, "Trip report not found")
    return record

def get_accessible_demand(db: Session, user: User, demand_id: str) -> Demand:
    demand = db.get(Demand, demand_id)
    if not demand or not can_access_org(user, demand.lead_org_id) or not can_access_sensitive(user, demand.sensitivity):
        raise HTTPException(status_code=404, detail="Demand not found")
    return demand


def get_accessible_project(db: Session, user: User, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project or not can_access_org(user, project.lead_org_id) or not can_access_sensitive(user, project.sensitivity):
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_accessible_task(db: Session, user: User, task_id: str) -> tuple[Task, Project]:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = get_accessible_project(db, user, task.project_id)
    return task, project


def parse_optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def task_return_path(project_id: str, task_id: str, tab: str = "board") -> str:
    safe_tab = tab if tab in {"overview", "board", "wbs", "schedule", "milestones", "raid", "financial", "status", "board-settings", "activity"} else "board"
    return f"/projects/{project_id}?tab={safe_tab}&task={task_id}"


def task_detail_path(project_id: str, task_id: str) -> str:
    return f"/projects/{project_id}/tasks/{task_id}"


DEFAULT_BOARD_COLUMNS = [
    ("Backlog", 0, 0, "Captured and ready for refinement", "Ready for prioritization"),
    ("Ready", 1, 8, "Scope and owner are clear", "Capacity is available"),
    ("In Progress", 2, 6, "Owner accepted work", "Acceptance criteria are satisfied"),
    ("Review", 3, 4, "Evidence is attached", "Reviewer accepts completion"),
    ("Done", 4, 0, "Acceptance evidence approved", "Work is closed"),
]


def get_board_columns(db: Session, project_id: str, include_archived: bool = False) -> list[BoardColumn]:
    query = db.query(BoardColumn).filter(BoardColumn.project_id == project_id)
    if not include_archived:
        query = query.filter(BoardColumn.archived.is_(False))
    columns = query.order_by(BoardColumn.position, BoardColumn.created_at).all()
    if columns:
        return columns
    for name, position, wip_limit, entry, exit_criteria in DEFAULT_BOARD_COLUMNS:
        db.add(BoardColumn(project_id=project_id, name=name, position=position, wip_limit=wip_limit, entry_criteria=entry, exit_criteria=exit_criteria))
    db.commit()
    return db.query(BoardColumn).filter(BoardColumn.project_id == project_id, BoardColumn.archived.is_(False)).order_by(BoardColumn.position).all()


def board_column_names(db: Session, project_id: str) -> list[str]:
    return [column.name for column in get_board_columns(db, project_id)]


def wip_capacity_available(db: Session, project_id: str, column_name: str, moving_task_id: str | None = None) -> tuple[bool, str]:
    column = db.query(BoardColumn).filter_by(project_id=project_id, name=column_name, archived=False).first()
    if not column:
        return False, "Board column is not available."
    if not column.wip_limit:
        return True, ""
    query = db.query(Task).filter(Task.project_id == project_id, Task.board_column == column_name)
    if moving_task_id:
        query = query.filter(Task.id != moving_task_id)
    count = query.count()
    if count >= column.wip_limit:
        return False, f"{column_name} has reached its WIP limit of {column.wip_limit}."
    return True, ""


REQUESTER_EDITABLE_DEMAND_STATES = {"Draft", "Submitted", "Clarification Required"}
PORTFOLIO_EDITABLE_DEMAND_STATES = REQUESTER_EDITABLE_DEMAND_STATES | {"Triage"}


def can_edit_demand_record(user: User, demand: Demand) -> bool:
    """Permit governed edits before assessment while preserving later decision baselines."""
    if not can_edit_business_data(user) or not can_access_org(user, demand.lead_org_id) or not can_access_sensitive(user, demand.sensitivity):
        return False
    if has_role(user, "ADMIN", "PMO", "DIVISION_PORTFOLIO_MANAGER", "ENTERPRISE_PORTFOLIO_OWNER"):
        return demand.status in PORTFOLIO_EDITABLE_DEMAND_STATES
    return demand.status in REQUESTER_EDITABLE_DEMAND_STATES and user.id in {demand.requester_id, demand.sponsor_id}


def task_workspace_context(db: Session, user: User, task: Task, project: Project) -> dict[str, Any]:
    normalized_checklist = []
    checklist_changed = False
    for raw in task.checklist or []:
        item = dict(raw)
        if not item.get("id"):
            item["id"] = os.urandom(8).hex()
            checklist_changed = True
        normalized_checklist.append(item)
    if checklist_changed:
        task.checklist = normalized_checklist
        db.commit()
        db.refresh(task)
    users = {u.id: u for u in db.query(User).order_by(User.full_name).all()}
    comments = db.query(TaskComment).filter(TaskComment.task_id == task.id).order_by(TaskComment.created_at.desc()).all()
    attachments = db.query(TaskAttachment).filter(
        TaskAttachment.task_id == task.id,
        TaskAttachment.is_current.is_(True),
        TaskAttachment.deleted_at.is_(None),
    ).order_by(TaskAttachment.created_at.desc()).all()
    attachment_history = db.query(TaskAttachment).filter(TaskAttachment.task_id == task.id).order_by(TaskAttachment.logical_file_id, TaskAttachment.version_number.desc()).all()
    note_revisions = db.query(TaskNoteRevision).filter(TaskNoteRevision.task_id == task.id).order_by(TaskNoteRevision.revision.desc()).limit(20).all()
    outgoing = db.query(TaskRelationship).filter(TaskRelationship.source_task_id == task.id).all()
    incoming = db.query(TaskRelationship).filter(TaskRelationship.target_task_id == task.id).all()
    all_tasks = db.query(Task).filter(Task.project_id == project.id, Task.id != task.id).order_by(Task.sequence).all()
    task_map = {t.id: t for t in db.query(Task).filter(Task.project_id == project.id).all()}
    audit = db.query(AuditEvent).filter(AuditEvent.entity_id == task.id).order_by(AuditEvent.created_at.desc()).limit(40).all()
    traceability = trace_for(db, "Task", "WBS", "Project workspace", "Document management", "Dependency")
    editable = has_role(user, "PROJECT_MANAGER", "TEAM_MEMBER", "ADMIN") and can_edit_business_data(user)
    return {
        "task": task,
        "project": project,
        "users_map": users,
        "comments": comments,
        "attachments": attachments,
        "attachment_history": attachment_history,
        "note_revisions": note_revisions,
        "outgoing_relationships": outgoing,
        "incoming_relationships": incoming,
        "all_tasks": all_tasks,
        "task_map": task_map,
        "audit": audit,
        "traceability": traceability,
        "editable": editable,
        "columns": board_column_names(db, project.id),
        "max_upload_mb": settings.max_upload_mb,
    }


def file_size_label(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


templates.env.filters["filesize"] = file_size_label



def role_focus_for(user: User) -> dict[str, Any]:
    """Return a concise, role-oriented starting point for the application shell."""
    roles = set(user.roles or [])
    profiles = [
        ({"ADMIN"}, "Administrator", "Keep access, configuration, integrations, and operational controls healthy.", [
            ("Manage access", "/administration", "Users, roles, scope, and delegations"),
            ("Resolve data issues", "/data-quality", "Scan, assign, and close quality findings"),
            ("Check integrations", "/integrations", "Ownership, health, and synchronization evidence"),
        ], ["administration", "data-quality", "integrations"]),
        ({"SENIOR_LEADER", "APPROVAL_AUTHORITY"}, "Decision Authority", "Focus on decisions, exceptions, tradeoffs, and outcomes that require leadership action.", [
            ("Review decisions", "/decisions", "Open dispositions and conditions"),
            ("Open briefings", "/portfolio-reviews", "Division summaries, questions, decisions, and actions"),
            ("Review scenarios", "/scenarios", "Compare approved baseline tradeoffs"),
        ], ["dashboard", "decisions", "portfolio-reviews", "scenarios"]),
        ({"ENTERPRISE_PORTFOLIO_OWNER", "PMO"}, "Portfolio Owner / PMO", "Balance demand, delivery health, capacity, investment, and governance across the portfolio.", [
            ("Open my work", "/my-work", "Assigned reviews, actions, and project work"),
            ("Manage demand", "/demands", "Triage, assess, recommend, and route"),
            ("Run briefing / review", "/portfolio-reviews", "Prepare the next source-backed leadership forum"),
        ], ["dashboard", "my-work", "demands", "portfolio-reviews"]),
        ({"DIVISION_CHIEF", "DIVISION_PORTFOLIO_MANAGER"}, "Division Portfolio Lead", "Keep the division pipeline, project exceptions, decisions, and commitments current.", [
            ("Open my work", "/my-work", "Assigned responsibilities and due work"),
            ("Review demand", "/demands", "Division intake and next actions"),
            ("Prepare division briefing", "/portfolio-reviews", "Summarize work and conduct leadership review"),
        ], ["my-work", "demands", "projects", "portfolio-reviews"]),
        ({"PROJECT_MANAGER"}, "Project Manager", "Plan executable work, remove blockers, maintain evidence, and report a trustworthy status.", [
            ("Open my work", "/my-work", "Tasks, actions, and managed projects"),
            ("Manage projects", "/projects", "Boards, WBS, schedule, RAID, and reports"),
            ("Review risks", "/risks", "Open risks and cross-project dependencies"),
        ], ["my-work", "projects", "risks"]),
        ({"TEAM_MEMBER"}, "Team Member", "Complete assigned tasks, update progress, and attach the evidence needed for acceptance.", [
            ("Open my work", "/my-work", "Your tasks and actions"),
            ("Open projects", "/projects", "Find the project execution workspace"),
            ("Check notifications", "/notifications", "Mentions, assignments, and changes"),
        ], ["my-work", "projects", "notifications"]),
        ({"REQUESTER"}, "Demand Requester", "Create complete demand records, answer clarification requests, and track decisions.", [
            ("Start a demand", "/demands/new", "Describe the need, outcome, urgency, and alignment"),
            ("Open my work", "/my-work", "Track sponsored and assigned demands"),
            ("View demand pipeline", "/demands", "See status and next action"),
        ], ["my-work", "demands"]),
        ({"ASSESSOR"}, "Assessor", "Score assigned demand consistently and document evidence, rationale, and confidence.", [
            ("Open assessments", "/assessments", "Review and score assigned demand"),
            ("Open my work", "/my-work", "See responsibilities and due work"),
            ("View demand pipeline", "/demands", "Understand lifecycle context"),
        ], ["my-work", "demands", "assessments"]),
        ({"RESOURCE_MANAGER"}, "Resource Manager", "Protect critical capacity, decide resource requests, and resolve over-allocation.", [
            ("Review resources", "/resources", "Capacity, allocation, and requests"),
            ("Open my work", "/my-work", "Assigned actions and project context"),
            ("Review projects", "/projects", "Validate delivery demand"),
        ], ["my-work", "resources", "projects"]),
        ({"FINANCIAL_MANAGER"}, "Financial Manager", "Maintain investment evidence, forecast variance, and funding decisions.", [
            ("Review investments", "/financials", "Budget, actual, forecast, and transactions"),
            ("Open reports", "/reports", "Validate leadership reporting"),
            ("Review scenarios", "/scenarios", "Assess financial tradeoffs"),
        ], ["financials", "reports", "scenarios"]),
        ({"BENEFITS_OWNER"}, "Benefits Owner", "Keep benefit targets, realization evidence, and outcome status current.", [
            ("Review benefits", "/benefits", "Targets, actuals, and status"),
            ("Open my work", "/my-work", "Assigned actions and projects"),
            ("Open reports", "/reports", "Confirm outcome reporting"),
        ], ["my-work", "benefits", "reports"]),
        ({"DATA_STEWARD"}, "Data Steward", "Improve data quality, govern imports, and resolve ownership or integration conflicts.", [
            ("Resolve data issues", "/data-quality", "Scan, assign, disposition, and verify"),
            ("Manage imports", "/imports", "Preview, validate, commit, and correct"),
            ("Check integrations", "/integrations", "Field ownership and sync evidence"),
        ], ["data-quality", "imports", "integrations"]),
        ({"SECURITY_REVIEWER", "AUDITOR"}, "Assurance Reviewer", "Verify access, traceability, evidence, and material changes without altering business records.", [
            ("Review audit", "/audit", "Material actions and before/after evidence"),
            ("Open requirements", "/requirements", "Implementation and verification traceability"),
            ("Review access", "/administration", "Users, roles, scope, and delegations"),
        ], ["audit", "requirements", "administration"]),
    ]
    for matching_roles, label, summary, actions, nav_keys in profiles:
        if roles.intersection(matching_roles):
            return {
                "label": label,
                "summary": summary,
                "actions": [{"label": a, "href": h, "hint": t} for a, h, t in actions],
                "nav_keys": nav_keys,
            }
    return {
        "label": "Portfolio Contributor",
        "summary": "Start with assigned work, then use the portfolio workspaces that match your responsibilities.",
        "actions": [
            {"label": "Open my work", "href": "/my-work", "hint": "Assigned tasks, actions, demands, and projects"},
            {"label": "Open portfolio overview", "href": "/dashboard", "hint": "Current portfolio picture and exceptions"},
        ],
        "nav_keys": ["my-work", "dashboard"],
    }


def page_guide_for(request: Request, template_name: str, context: dict[str, Any]) -> dict[str, Any] | None:
    """Provide contextual process guidance without changing authoritative workflow rules."""
    def guide(title: str, purpose: str, steps: list[tuple[str, str, str]], current: int = 0, tip: str = "") -> dict[str, Any]:
        return {
            "title": title,
            "purpose": purpose,
            "steps": [{"label": label, "detail": detail, "href": href} for label, detail, href in steps],
            "current": max(0, min(current, len(steps) - 1)),
            "tip": tip,
        }

    path = request.url.path
    if template_name == "dashboard.html":
        return guide("Use the portfolio overview", "Orient to the current picture, identify what needs attention, then move into an authoritative workspace.", [
            ("Review", "Scan health, investment, decisions, risks, and benefits.", "/dashboard"),
            ("Prioritize", "Open My Work to see responsibilities assigned to you.", "/my-work"),
            ("Act", "Update the demand, project, review, or control record.", "/my-work"),
            ("Verify", "Confirm the change appears in reports and audit evidence.", "/reports"),
        ], 0, "Start with items marked Focus in the left navigation.")
    if template_name == "my_work.html":
        return guide("Work your personal queue", "Use this page as the safest starting point for daily work; each item links to its authoritative record.", [
            ("Review", "Scan assignments, next actions, due dates, and health.", "/my-work"),
            ("Prioritize", "Open overdue, high-priority, or decision-blocking work first.", "/my-work"),
            ("Update", "Record progress, evidence, comments, or disposition at the source.", "/my-work"),
            ("Close", "Complete the task or action and verify downstream status.", "/my-work"),
        ], 1, "Do not update summary dashboards when an authoritative task, demand, or project record is available.")
    if template_name in {"demands.html", "demand_form.html", "demand_detail.html", "assessments.html"}:
        current = 0
        if template_name == "assessments.html": current = 2
        if template_name == "demand_detail.html":
            status = getattr(context.get("demand"), "status", "Draft")
            current = {"Draft": 0, "Submitted": 1, "Triage": 1, "Clarification Required": 1, "Assessment": 2,
                       "Awaiting Portfolio Recommendation": 3, "Awaiting Decision": 4, "Approved": 5,
                       "Converted to Execution": 5, "Deferred": 4, "Declined": 4}.get(status, 1)
        return guide("Demand lifecycle", "Move a need from a complete intake record to an evidence-based decision and, when approved, into execution.", [
            ("Draft", "Describe the need, outcome, urgency, alignment, and expected value.", "/demands/new"),
            ("Validate", "Submit, review completeness, and resolve clarification requests.", "/demands"),
            ("Assess", "Score consistently and document rationale and confidence.", "/assessments"),
            ("Recommend", "Compare tradeoffs and prepare a portfolio recommendation.", "/demands"),
            ("Decide", "Record disposition, rationale, conditions, and implications.", "/decisions"),
            ("Execute", "Convert approved demand without rekeying and manage delivery.", "/projects"),
        ], current, "Required fields are marked with an asterisk; save evidence at the step where it is created.")
    if template_name in {"projects.html", "project_detail.html", "task_detail.html", "project_templates.html", "roadmaps.html", "status_report_detail.html"}:
        tab = context.get("tab", "overview")
        current = {"overview": 0, "wbs": 1, "board-settings": 1, "board": 2, "schedule": 2, "milestones": 2,
                   "raid": 3, "financial": 3, "status": 4, "activity": 4}.get(tab, 0)
        if template_name == "task_detail.html": current = 2
        if template_name == "status_report_detail.html": current = 4
        return guide("Project delivery cycle", "Plan the work, execute through governed flow, monitor exceptions, and publish a source-grounded status.", [
            ("Orient", "Confirm purpose, accountability, scope, and baseline.", "/projects"),
            ("Plan", "Build WBS, board states, dates, dependencies, and acceptance criteria.", path if path.startswith("/projects/") else "/projects"),
            ("Execute", "Assign tasks, update progress, collaborate, and attach evidence.", path if path.startswith("/projects/") else "/projects"),
            ("Control", "Resolve RAID, schedule, capacity, financial, and dependency exceptions.", "/risks"),
            ("Report", "Prepare, submit, approve, and retain the reporting baseline.", "/reports"),
        ], current, "Open task details from Kanban or WBS; the full task page remains available as a reliable fallback.")
    if template_name in {"travel.html", "travel_request_detail.html", "trip_report_detail.html", "travel_engagement_detail.html"}:
        current = 0 if template_name == "travel.html" else 1 if template_name in {"travel_request_detail.html", "travel_engagement_detail.html"} else 2
        return guide("Travel and engagement outcome cycle", "Connect approval estimates to engagements, trip reports, reviewed outcomes, and canonical portfolio follow-through.", [
            ("Review", "Filter approvals, estimated cost, divisions, destinations, and report gaps.", "/travel"),
            ("Trace", "Open the traveler request and engagement rollup with source provenance.", "/travel"),
            ("Reconcile", "Confirm the trip report-to-request match and review the report narrative.", "/travel#reconciliation"),
            ("Promote", "Turn reviewed recommendations into governed actions, risks, or decisions.", "/travel"),
            ("Verify", "Follow the canonical record and retain the historical trip report link.", "/audit"),
        ], current, "Travel values are approval estimates, not authoritative actual expenditures.")
    if template_name == "division_briefing.html":
        status = getattr(context.get("review"), "status", "In Preparation")
        current = {"Draft": 0, "In Preparation": 0, "Ready for Division Review": 1, "Ready to Brief": 2, "In Review": 3, "Completed": 4}.get(status, 0)
        return guide("Division briefing and review cycle", "Replace disconnected slide preparation with one source-backed operating process for preparation, live review, decisions, and follow-through.", [
            ("Prepare", "Complete the standard division sections and validate source data.", path),
            ("Approve", "Submit for division validation and capture the approved briefing snapshot.", path),
            ("Brief", "Present directly from current portfolio evidence in presentation mode.", path),
            ("Review", "Ask questions, document notes, request changes, decide, and assign actions.", path),
            ("Follow through", "Resolve assigned questions and changes from My Work, then close the forum.", "/my-work"),
        ], current, "The approved snapshot preserves what leadership saw; follow-up changes remain governed at the authoritative source.")
    if template_name in {"portfolio_reviews.html", "portfolio_review_detail.html", "divisions.html", "division_detail.html"}:
        return guide("Portfolio governance cycle", "Prepare evidence, make explicit tradeoffs, record decisions, and follow actions to closure.", [
            ("Prepare", "Select scope, period, participants, agenda, and evidence.", "/portfolio-reviews"),
            ("Review", "Examine health, value, capacity, risks, and recommendations.", "/portfolio-reviews"),
            ("Decide", "Record the authoritative outcome and rationale.", "/decisions"),
            ("Assign", "Create owners, due dates, conditions, and actions.", "/my-work"),
            ("Complete", "Close the forum and verify downstream records.", "/portfolio-reviews"),
        ], 1, "A review is complete only when decisions and actions are linked to authoritative records.")
    if template_name == "resources.html":
        return guide("Resource management flow", "Translate delivery needs into governed requests and capacity decisions.", [
            ("Review capacity", "Identify coverage gaps and over-allocation.", "/resources"),
            ("Request", "State role, skill, period, hours, priority, and rationale.", "/resources"),
            ("Decide", "Approve or decline with a resolution.", "/resources"),
            ("Allocate", "Reflect the approved plan in delivery records.", "/projects"),
            ("Track", "Compare allocation, actual effort, and protected minimums.", "/resources"),
        ], 0, "Resource requests are planning evidence; authoritative workforce assignment remains integration-dependent.")
    if template_name in {"financials.html", "benefits.html"}:
        return guide("Investment and value cycle", "Maintain a trustworthy financial baseline, explain variance, and connect spend to expected outcomes.", [
            ("Baseline", "Confirm approved budget, funding need, and benefit target.", "/financials"),
            ("Record", "Append commitments, obligations, expenditures, or adjustments.", "/financials"),
            ("Forecast", "Update forecast and estimate variance or underfunding.", "/financials"),
            ("Review", "Assess affordability, tradeoffs, and benefit realization.", "/benefits"),
            ("Decide", "Record funding or scope decisions and conditions.", "/decisions"),
        ], 1 if template_name == "financials.html" else 3, "These records support portfolio decisions; they are not the authoritative accounting system.")
    if template_name in {"reports.html", "operations.html"}:
        return guide("Reporting cycle", "Build leadership products from authoritative records and retain approval evidence.", [
            ("Prepare", "Select organization, period, and reporting scope.", "/reports"),
            ("Generate", "Create source-grounded metrics and narrative.", "/operations"),
            ("Validate", "Resolve missing, stale, or inconsistent source data.", "/data-quality"),
            ("Approve", "Lock the reporting baseline with accountable approval.", "/operations"),
            ("Use", "Distribute or print the approved product and track decisions.", "/reports"),
        ], 0 if template_name == "reports.html" else 2, "Narrative should never introduce a claim that is not supported by an accessible source record.")
    if template_name in {"scenarios.html", "scenario_detail.html"}:
        status = getattr(context.get("scenario"), "status", "Draft")
        current = {"Draft": 0, "Calculated": 2, "Compared": 2, "Approved": 3, "Applied": 4}.get(status, 0)
        return guide("Scenario governance flow", "Explore a change without modifying the live baseline, then separate approval from application.", [
            ("Define", "State the decision question, assumptions, scope, and baseline date.", "/scenarios#new-scenario"),
            ("Model", "Add supported changes without applying them.", "/scenarios"),
            ("Compare", "Calculate impacts and explain baseline differences.", "/scenarios"),
            ("Approve", "Authorize the scenario while leaving live records unchanged.", "/scenarios"),
            ("Apply", "Apply only an approved scenario with before/after audit evidence.", "/scenarios"),
        ], current, "Approval is intentionally separate from Apply; draft and compared scenarios do not change live data.")
    if template_name in {"imports.html", "import_preview.html"}:
        return guide("Controlled import flow", "Stage spreadsheet data safely before it changes authoritative records.", [
            ("Download", "Use the versioned template and preserve stable identifiers.", "/imports"),
            ("Upload", "Select the template type and upload the workbook.", "/imports"),
            ("Validate", "Review row-level create, update, warning, error, and permission results.", "/imports"),
            ("Commit", "Commit only valid rows after review.", "/imports"),
            ("Correct", "Download corrections, fix source data, and repeat validation.", "/imports"),
        ], 2 if template_name == "import_preview.html" else 1, "Preview is non-destructive; commit is the explicit write step.")
    if template_name == "data_quality.html":
        return guide("Data-quality resolution flow", "Turn deterministic findings into owned, traceable corrections.", [
            ("Scan", "Run rules against current authoritative records.", "/data-quality"),
            ("Triage", "Confirm severity, source, and disposition.", "/data-quality"),
            ("Assign", "Set an owner and due date.", "/data-quality"),
            ("Resolve", "Correct the source record and document the result.", "/data-quality"),
            ("Verify", "Re-scan or review evidence before closure.", "/data-quality"),
        ], 1, "Fix the source record rather than editing only the quality finding.")
    if template_name == "integrations.html":
        return guide("Integration control flow", "Define ownership before synchronization and keep operator evidence for every run.", [
            ("Register", "Record endpoint, mode, authentication type, and owner.", "/integrations"),
            ("Own fields", "Declare authoritative system, allowed writers, and conflict policy.", "/integrations"),
            ("Test", "Run health checks or a canonical dry run.", "/integrations"),
            ("Reconcile", "Inspect payload, result, conflict, and lineage evidence.", "/integrations"),
            ("Operate", "Monitor jobs, retries, and exceptions.", "/operations"),
        ], 1, "The packaged ProjectOS operation is a dry run; no remote write occurs.")
    if template_name == "administration.html":
        return guide("Access administration flow", "Apply least privilege, explicit scope, and traceable temporary authority.", [
            ("Create / update", "Maintain account identity and active status.", "/administration"),
            ("Assign roles", "Grant only roles needed for accountable work.", "/administration"),
            ("Set scope", "Limit division and restricted-record access.", "/administration"),
            ("Delegate", "Time-bound acting authority with rationale.", "/administration"),
            ("Verify", "Review effective access and audit evidence.", "/audit"),
        ], 1, "Local accounts are for demonstration; enterprise identity and access certification remain deployment dependencies.")
    if template_name in {"requirements.html", "requirement_detail.html"}:
        return guide("Requirements evidence cycle", "Keep implementation claims conservative and link every status to usable evidence.", [
            ("Filter", "Find the requirement by ID, domain, phase, fit, or status.", "/requirements"),
            ("Inspect", "Review statement, owner, design, module, test, and release references.", "/requirements"),
            ("Evidence", "Add test, UAT, acceptance, and decision evidence.", "/requirements"),
            ("Classify", "Update status only when the evidence supports it.", "/requirements"),
            ("Export", "Publish the governed baseline for release review.", "/requirements"),
        ], 1, "A screen or table alone is not sufficient evidence that an enterprise requirement is implemented.")
    if template_name == "audit.html":
        return guide("Assurance review", "Trace material actions back to the actor, source record, and before/after evidence.", [
            ("Scope", "Filter to the entity, actor, time, or action under review.", "/audit"),
            ("Inspect", "Review before/after evidence and related identifiers.", "/audit"),
            ("Corroborate", "Open the authoritative record and linked requirement.", "/requirements"),
            ("Document", "Retain the assurance conclusion outside read-only business data.", "/audit"),
        ], 1, "Auditor access is intentionally read-only for business records.")
    if template_name in {"notifications.html", "decisions.html", "risks.html", "strategy.html", "search.html", "api_docs.html"}:
        labels = {
            "notifications.html": ("Notification handling", "Review the change, open its source record, take the required action, then confirm the notification is no longer outstanding."),
            "decisions.html": ("Decision follow-through", "Review rationale and conditions, open the affected source record, and track resulting actions to closure."),
            "risks.html": ("Exception control", "Identify exposure, confirm an owner and response, update the source project, and verify portfolio impact."),
            "strategy.html": ("Strategy alignment", "Trace mission intent to demand and delivery, then address work that lacks approved alignment."),
            "search.html": ("Find authoritative records", "Search by stable ID or term, filter to the record type, and update only at the authoritative source."),
            "api_docs.html": ("API reference", "Review authenticated contracts and use governed integration ownership before connecting an external system."),
        }
        title, purpose = labels[template_name]
        return guide(title, purpose, [
            ("Find", "Locate the authoritative record or exception.", path),
            ("Understand", "Review status, ownership, evidence, and next action.", path),
            ("Act", "Use the permitted source workflow.", "/my-work"),
            ("Verify", "Confirm downstream status and audit evidence.", "/audit"),
        ], 1)
    return None


def render(request: Request, template_name: str, user: User, db: Session, **context):
    status_code = int(context.pop("status_code", 200))
    orgs = db.query(Organization).filter(Organization.active.is_(True)).order_by(Organization.code).all()
    unread = db.query(Notification).filter(Notification.user_id == user.id, Notification.read_at.is_(None)).count()
    saved_views = db.query(SavedView).filter(SavedView.user_id == user.id).order_by(SavedView.name).all()
    my_work_open_count = (
        db.query(Task).filter(Task.owner_id == user.id, Task.status != "Completed").count()
        + db.query(Action).filter(Action.owner_id == user.id, Action.status != "Closed").count()
    )
    base = {
        "request": request,
        "user": user,
        "csrf_token": csrf_token(user.id),
        "organizations": orgs,
        "unread_notifications": unread,
        "saved_views": saved_views,
        "message": request.query_params.get("message"),
        "level": request.query_params.get("level", "success"),
        "now": datetime.now(timezone.utc),
        "app_version": APP_VERSION,
        "today": date.today(),
        "search_query": request.query_params.get("q", ""),
        "my_work_open_count": my_work_open_count,
    }
    base.update(context)
    division_shortcuts = [org for org in orgs if org.org_type == "Division" and can_access_org(user, org.id)]
    base["division_shortcuts"] = division_shortcuts
    breadcrumb_labels = {
        "dashboard": "Portfolio Overview", "my-work": "My Work", "divisions": "Divisions", "projects": "Projects",
        "demands": "Demand Intake", "resources": "Resources", "financials": "Investments", "reports": "Reports & Analytics",
        "travel": "Travel & Engagements", "portfolio-reviews": "Briefings", "templates": "Blueprints", "roadmaps": "Roadmaps",
        "scenarios": "Scenarios", "requirements": "Requirements RTM", "imports": "Imports", "administration": "Administration",
        "new": "Create", "promotion": "Portfolio Promotion", "requests": "Requests", "import": "Import / Export",
    }
    parts = [part for part in request.url.path.split("/") if part]
    crumbs = [{"label": "Home", "href": "/dashboard"}]
    running = ""
    for index, part in enumerate(parts):
        if part == "dashboard":
            continue
        running += "/" + part
        label = breadcrumb_labels.get(part, part.replace("-", " ").title())
        if index == 1 and parts[0] == "divisions" and context.get("org"):
            label = context["org"].code
        elif index == 1 and parts[0] == "projects" and context.get("project"):
            label = context["project"].human_id
        elif parts[:2] == ["resources", "requests"] and index == 2 and context.get("record"):
            label = context["record"].human_id
        crumbs.append({"label": label, "href": running if index < len(parts) - 1 else ""})
    base["global_breadcrumbs"] = crumbs
    base["has_local_breadcrumbs"] = template_name in {
        "travel_engagement_detail.html", "trip_report_detail.html", "travel_request_detail.html", "portfolio_review_detail.html",
        "requirement_detail.html", "scenario_detail.html", "record_detail.html", "division_briefing.html", "project_form.html",
        "project_promotion.html", "projects.html", "project_templates.html", "project_detail.html", "resources.html",
        "resource_request_form.html", "resource_request_detail.html", "resource_import.html", "resource_import_preview.html",
    }
    base["role_focus"] = role_focus_for(user)
    base["page_guide"] = page_guide_for(request, template_name, base)
    return templates.TemplateResponse(template_name, base, status_code=status_code)


def next_human_id(db: Session, model, prefix: str, attr: str = "human_id") -> str:
    year = str(date.today().year)[-2:]
    count = db.query(model).count() + 1
    while True:
        candidate = f"{prefix}-{year}-{count:03d}"
        if not db.query(model).filter(getattr(model, attr) == candidate).first():
            return candidate
        count += 1


def demand_next_action(status: str) -> str:
    return {
        "Draft": "Complete intake and submit",
        "Submitted": "PMO completeness review",
        "Triage": "Validate scope, ownership, and assessment route",
        "Clarification Required": "Requester provides missing evidence",
        "Assessment": "Assessors complete scoring and rationale",
        "Awaiting Portfolio Recommendation": "Portfolio manager records recommendation",
        "Awaiting Decision": "Approval authority records disposition",
        "Approved": "Initiate execution and satisfy decision conditions",
        "Deferred": "Review on the approved reconsideration date",
        "Declined": "Close and retain decision evidence",
        "Withdrawn": "Revise or close",
        "Converted to Execution": "Manage linked project",
        "Closed": "No further action",
    }.get(status, "Review record")


def trace_for(db: Session, *terms: str, limit: int = 12):
    """Return requirement evidence related to a record or module without inventing compliance."""
    clean=[t.strip() for t in terms if t and t.strip()]
    query=db.query(RequirementTrace)
    clauses=[]
    for term in clean:
        token=f"%{term}%"
        clauses.extend([RequirementTrace.domain.ilike(token), RequirementTrace.title.ilike(token), RequirementTrace.requirement.ilike(token), RequirementTrace.design_reference.ilike(token)])
    if clauses:
        query=query.filter(or_(*clauses))
    return query.order_by(RequirementTrace.requirement_id).limit(limit).all()


def record_audit_events(db: Session, entity_id: str):
    return db.query(AuditEvent).filter(AuditEvent.entity_id == entity_id).order_by(AuditEvent.created_at.desc()).limit(50).all()


def resolved_client_ip(request: Request) -> str:
    """Resolve a client address only across the configured number of trusted proxy hops."""
    direct = request.client.host if request.client else "unknown"
    if settings.trust_proxy_hops <= 0:
        return direct
    forwarded = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    chain = forwarded + [direct]
    index = max(0, len(chain) - 1 - settings.trust_proxy_hops)
    return chain[index]


def _rate_limit_key(request: Request, client_ip: str) -> str:
    scope = "login" if request.url.path == "/login" else "api" if request.url.path.startswith("/api/") else "write"
    return f"{scope}:{client_ip}"


@app.middleware("http")
async def deployment_security(request: Request, call_next):
    client_ip = resolved_client_ip(request)
    request.state.client_ip = client_ip
    should_limit = request.method not in {"GET", "HEAD", "OPTIONS"} or request.url.path.startswith("/api/")
    remaining = settings.rate_limit_requests
    if should_limit:
        now = time.time()
        key = _rate_limit_key(request, client_ip)
        bucket = RATE_LIMIT_BUCKETS[key]
        while bucket and now - bucket[0] >= settings.rate_limit_window_seconds:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_requests:
            retry_after = max(1, int(settings.rate_limit_window_seconds - (now - bucket[0])))
            response = JSONResponse({"detail": "Rate limit exceeded. Try again later."}, status_code=429) if request.url.path.startswith("/api/") else Response("Rate limit exceeded. Try again later.", status_code=429)
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
            response.headers["X-RateLimit-Remaining"] = "0"
            return response
        bucket.append(now)
        remaining = max(0, settings.rate_limit_requests - len(bucket))
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-Resolved-Client-IP-Source"] = "forwarded" if settings.trust_proxy_hops > 0 else "direct"
    return response


@app.exception_handler(401)
async def auth_exception(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": exc.detail}, status_code=401)
    return RedirectResponse(f"/login?next={quote_plus(request.url.path)}", status_code=303)


@app.exception_handler(403)
async def forbidden_exception(request: Request, exc: HTTPException):
    return templates.TemplateResponse("error.html", {"request": request, "status": 403, "title": "Access denied", "detail": exc.detail}, status_code=403)


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "web"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ready", "database": "connected"}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": request.query_params.get("error"), "next": request.query_params.get("next", "/dashboard")})


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/dashboard"),
    db: Session = Depends(get_db),
):
    ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else "unknown")
    now = time.time()
    LOGIN_ATTEMPTS[ip] = [t for t in LOGIN_ATTEMPTS[ip] if now - t < 300]
    if len(LOGIN_ATTEMPTS[ip]) >= 10:
        return RedirectResponse("/login?error=Too+many+attempts.+Try+again+later.", status_code=303)
    LOGIN_ATTEMPTS[ip].append(now)
    user = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse("/login?error=Invalid+username+or+password", status_code=303)
    LOGIN_ATTEMPTS[ip].clear()
    record_audit(db, user.id, "Session", user.id, "LOGIN", after={"username": user.username}, ip_address=ip)
    db.commit()
    response = RedirectResponse(safe_local_path(next), status_code=303)
    response.set_cookie("ddc5i_session", create_session_token(user.id), httponly=True, secure=settings.environment == "production", samesite="strict", max_age=settings.session_hours * 3600)
    return response


@app.post("/logout")
def logout(request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    record_audit(db, user.id, "Session", user.id, "LOGOUT")
    db.commit()
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("ddc5i_session")
    return response


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/dashboard", status_code=303)


def _portfolio_investment_flow(financials: list[FinancialRecord], projects: list[Project], organizations: list[Organization]) -> dict[str, Any]:
    project_map = {item.id: item for item in projects}
    org_map = {item.id: item for item in organizations}
    links: dict[tuple[str, str], float] = defaultdict(float)
    nodes: dict[str, dict[str, Any]] = {}
    project_budget: dict[str, float] = defaultdict(float)
    project_actual: dict[str, float] = defaultdict(float)

    def add_node(node_id: str, label: str, stage: int, kind: str, url: str, amount: float = 0.0) -> None:
        node = nodes.setdefault(node_id, {"id": node_id, "label": label, "stage": stage, "kind": kind, "url": url, "amount": 0.0})
        node["amount"] = max(node["amount"], round(amount, 2))

    add_node("approved", "Approved investment", 0, "source", "/financials")
    for record in financials:
        project = project_map.get(record.project_id or "")
        if not project:
            continue
        amount = max(float(record.approved_budget or 0), 0.0)
        if amount <= 0:
            continue
        category = record.category or "Other"
        org = org_map.get(project.lead_org_id)
        org_label = org.code if org else "Unassigned"
        category_id = f"category:{category}"
        division_id = f"division:{project.lead_org_id}"
        project_id = f"project:{project.id}"
        add_node(category_id, category, 1, "category", f"/financials?category={quote_plus(category)}")
        add_node(division_id, org_label, 2, "division", f"/financials?division={quote_plus(org_label)}")
        add_node(project_id, project.title, 3, "project", f"/projects/{project.id}?tab=financial")
        links[("approved", category_id)] += amount
        links[(category_id, division_id)] += amount
        links[(division_id, project_id)] += amount
        project_budget[project.id] += amount
        project_actual[project.id] += max(float(record.actual_cost or 0), 0.0)

    spent_total = 0.0
    remaining_total = 0.0
    add_node("spent", "Actual to date", 4, "outcome", "/financials?view=actual")
    add_node("remaining", "Unspent approved", 4, "outcome", "/financials?view=remaining")
    for project_id, approved in project_budget.items():
        actual = min(project_actual.get(project_id, 0.0), approved)
        remaining = max(approved - actual, 0.0)
        if actual:
            links[(f"project:{project_id}", "spent")] += actual
            spent_total += actual
        if remaining:
            links[(f"project:{project_id}", "remaining")] += remaining
            remaining_total += remaining
    approved_total = sum(project_budget.values())
    nodes["approved"]["amount"] = round(approved_total, 2)
    nodes["spent"]["amount"] = round(spent_total, 2)
    nodes["remaining"]["amount"] = round(remaining_total, 2)
    for (source, target), value in links.items():
        nodes[source]["amount"] = max(nodes[source]["amount"], round(sum(v for (s, _), v in links.items() if s == source), 2))
        nodes[target]["amount"] = max(nodes[target]["amount"], round(sum(v for (_, t), v in links.items() if t == target), 2))
    return {
        "nodes": sorted(nodes.values(), key=lambda item: (item["stage"], -item["amount"], item["label"])),
        "links": [{"source": source, "target": target, "value": round(value, 2)} for (source, target), value in links.items() if value > 0],
        "approved": round(approved_total, 2),
        "spent": round(spent_total, 2),
        "remaining": round(remaining_total, 2),
        "reconciled": abs(approved_total - spent_total - remaining_total) < 0.01,
    }


def dashboard_lens_for(user: User) -> dict[str, Any]:
    """Return an explainable primary lens and smart default panel order."""
    roles = set(user.roles or [])
    lenses = [
        ({"SENIOR_LEADER", "APPROVAL_AUTHORITY"}, "Leader", "Decisions, exceptions, investments, outcomes, and material changes.", ["decisions", "changes", "kpis", "health", "investment", "divisions", "portfolio", "my-work"]),
        ({"ENTERPRISE_PORTFOLIO_OWNER", "PMO"}, "Portfolio", "Demand, delivery health, cross-division capacity, funding, and governance.", ["decisions", "changes", "kpis", "health", "divisions", "portfolio", "investment", "my-work"]),
        ({"DIVISION_CHIEF", "DIVISION_PORTFOLIO_MANAGER"}, "Division", "Division commitments, local projects, promotion candidates, exceptions, and briefings.", ["my-work", "changes", "kpis", "divisions", "health", "portfolio", "decisions", "investment"]),
        ({"PROJECT_MANAGER"}, "Project Manager", "Managed projects, due work, milestones, RAID, reporting, and capacity needs.", ["my-work", "changes", "kpis", "health", "portfolio", "divisions", "decisions", "investment"]),
        ({"TEAM_MEMBER"}, "Contributor", "Assigned work, due dates, priorities, and the projects that need your evidence.", ["my-work", "changes", "portfolio", "kpis", "divisions", "health", "decisions", "investment"]),
        ({"RESOURCE_MANAGER"}, "Resources", "Capacity, skill gaps, over-allocation, requests, and affected delivery.", ["kpis", "my-work", "changes", "divisions", "portfolio", "health", "decisions", "investment"]),
        ({"FINANCIAL_MANAGER"}, "Financial", "Budget, actuals, forecasts, funding gaps, and decisions.", ["investment", "kpis", "changes", "portfolio", "decisions", "divisions", "health", "my-work"]),
        ({"DATA_STEWARD", "ADMIN"}, "Operations", "Data quality, imports, integrations, auditability, and portfolio freshness.", ["changes", "kpis", "divisions", "portfolio", "health", "my-work", "decisions", "investment"]),
    ]
    for match, label, summary, panels in lenses:
        if roles.intersection(match):
            return {"label": label, "summary": summary, "panels": panels}
    return {"label": "Contributor", "summary": "Assigned work and accessible delivery context.", "panels": ["my-work", "changes", "portfolio", "kpis", "divisions", "health", "decisions", "investment"]}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, division: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if division:
        return RedirectResponse(f"/divisions/{division}", status_code=303)
    projects_q = scoped_projects(db, user).filter(Project.status == "Active")
    demands_q = scoped_demands(db, user)
    projects = projects_q.all()
    demands = demands_q.all()
    exception_states = {"At Risk", "Off Track", "Blocked"}
    at_risk = [p for p in projects if (p.health_override or p.health_owner or p.health_calculated) in exception_states]
    decisions_required = [d for d in demands if d.status == "Awaiting Decision"]
    capacities_q = db.query(ResourceCapacity)
    if not is_enterprise_user(user):
        capacities_q = capacities_q.filter(ResourceCapacity.org_id == user.division_id)
    capacities = capacities_q.all()
    capacity_total = sum(r.capacity_hours for r in capacities)
    allocated_total = sum(r.allocated_hours for r in capacities)
    capacity_pct = round((allocated_total / capacity_total * 100) if capacity_total else 0, 1)
    financial_q = db.query(FinancialRecord).join(Project, FinancialRecord.project_id == Project.id)
    if not is_enterprise_user(user):
        financial_q = financial_q.filter(Project.lead_org_id == user.division_id)
    financials = financial_q.all()
    budget = sum(float(f.approved_budget) for f in financials)
    actual = sum(float(f.actual_cost) for f in financials)
    forecast = sum(float(f.forecast) for f in financials)
    benefits_q = db.query(Benefit).join(Project, Benefit.project_id == Project.id)
    if not is_enterprise_user(user):
        benefits_q = benefits_q.filter(Project.lead_org_id == user.division_id)
    benefits = benefits_q.all()
    monetary_units = {"usd", "$", "dollars", "dollar", "us dollars"}
    benefit_is_money = bool(benefits) and all((b.unit or "").strip().lower() in monetary_units for b in benefits)
    benefit_target = sum(b.target_value for b in benefits)
    benefit_realized = sum(b.realized_value for b in benefits)
    benefit_unit = "USD" if benefit_is_money else (benefits[0].unit if benefits and len({(b.unit or "").strip().lower() for b in benefits}) == 1 else "mixed units")
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    stale = [p for p in projects if p.last_status_date and p.last_status_date.replace(tzinfo=p.last_status_date.tzinfo or timezone.utc) < stale_cutoff]
    pipeline = Counter(d.status for d in demands)
    pipeline_order = ["Draft", "Submitted", "Triage", "Clarification Required", "Assessment", "Awaiting Portfolio Recommendation", "Awaiting Decision", "Approved", "Deferred", "Declined", "Converted to Execution"]
    max_pipeline = max(pipeline.values(), default=1)
    milestones_q = db.query(Milestone, Project).join(Project, Milestone.project_id == Project.id).filter(Milestone.current_date >= date.today(), Milestone.current_date <= date.today() + timedelta(days=60))
    if not is_enterprise_user(user):
        milestones_q = milestones_q.filter(Project.lead_org_id == user.division_id)
    milestones = milestones_q.order_by(Milestone.current_date).limit(10).all()
    dependencies_q = db.query(Dependency, Project).join(Project, Dependency.source_project_id == Project.id).filter(Dependency.status.in_(["Open", "At Risk"]))
    if not is_enterprise_user(user):
        dependencies_q = dependencies_q.filter(Project.lead_org_id == user.division_id)
    dependencies = dependencies_q.order_by(Dependency.due_date).limit(8).all()
    project_ids = [p.id for p in projects]
    demand_ids = [d.id for d in demands]
    decision_scope = []
    if project_ids:
        decision_scope.append(Decision.project_id.in_(project_ids))
    if demand_ids:
        decision_scope.append(Decision.demand_id.in_(demand_ids))
    recent_decisions = (
        db.query(Decision).filter(or_(*decision_scope)).order_by(Decision.created_at.desc()).limit(5).all()
        if decision_scope else []
    )
    decision_sources = {p.id: p.title for p in projects}
    decision_sources.update({d.id: d.title for d in demands})

    high_risks_q = db.query(RaidItem, Project).join(Project, RaidItem.project_id == Project.id).filter(
        RaidItem.status != "Closed", RaidItem.severity.in_(["High", "Critical"])
    )
    if not is_enterprise_user(user):
        high_risks_q = high_risks_q.filter(Project.lead_org_id == user.division_id)
    high_risks = high_risks_q.order_by(RaidItem.exposure.desc()).all()

    my_tasks = db.query(Task, Project).join(Project, Task.project_id == Project.id).filter(
        Task.owner_id == user.id, Task.status != "Completed"
    ).order_by(Task.due_date).limit(4).all()
    my_actions = db.query(Action).filter(Action.owner_id == user.id, Action.status != "Closed").order_by(Action.due_date).limit(3).all()

    health_counts = Counter((p.health_override or p.health_owner or p.health_calculated or "On Track") for p in projects)
    on_track_count = health_counts.get("On Track", 0)
    at_risk_count = health_counts.get("At Risk", 0)
    off_track_count = health_counts.get("Off Track", 0) + health_counts.get("Blocked", 0)
    health_total = max(len(projects), 1)
    health_score = round((on_track_count * 100 + at_risk_count * 60 + off_track_count * 20) / health_total)
    health_segments = {
        "on_track": round(on_track_count / health_total * 100, 1),
        "at_risk": round(at_risk_count / health_total * 100, 1),
        "off_track": round(off_track_count / health_total * 100, 1),
    }

    category_totals: dict[str, float] = defaultdict(float)
    financial_by_project: dict[str, dict[str, float]] = defaultdict(lambda: {"budget": 0.0, "actual": 0.0})
    for item in financials:
        amount = float(item.approved_budget)
        category_totals[item.category or "Other"] += amount
        if item.project_id:
            financial_by_project[item.project_id]["budget"] += amount
            financial_by_project[item.project_id]["actual"] += float(item.actual_cost)
    category_colors = ["#2388ff", "#5aa7ff", "#8dbcf0", "#416fa8", "#263e5e", "#7c5cff"]
    investment_categories = []
    investment_total = sum(category_totals.values()) or 1
    cursor = 0.0
    gradient_parts = []
    for index, (name, amount) in enumerate(sorted(category_totals.items(), key=lambda item: item[1], reverse=True)):
        percentage = amount / investment_total * 100
        color = category_colors[index % len(category_colors)]
        investment_categories.append({"name": name, "amount": amount, "percentage": percentage, "color": color})
        gradient_parts.append(f"{color} {cursor:.2f}% {cursor + percentage:.2f}%")
        cursor += percentage
    investment_gradient = ", ".join(gradient_parts) if gradient_parts else "#263e5e 0% 100%"

    risk_counts = Counter(risk.project_id for risk, _project in high_risks)
    portfolio_rows = []
    for project in projects[:7]:
        project_financial = financial_by_project.get(project.id, {})
        project_budget = project_financial.get("budget") or float(project.budget)
        project_spend = project_financial.get("actual") or float(project.actual)
        schedule_status = "On Track"
        if project.current_end_date and project.baseline_end_date and project.current_end_date > project.baseline_end_date:
            schedule_status = "At Risk"
        portfolio_rows.append({
            "project": project,
            "category": project.work_type or "Mission Support",
            "health": project.health_override or project.health_owner or project.health_calculated,
            "stage": "Execution" if project.status == "Active" else project.status,
            "budget": project_budget,
            "spend": project_spend,
            "schedule": schedule_status,
            "benefits": float(project.benefit_realized),
            "risks": risk_counts.get(project.id, 0),
        })
    divisions = [
        org for org in db.query(Organization).filter(Organization.org_type == "Division").order_by(Organization.code).all()
        if can_access_org(user, org.id)
    ]
    division_rows = []
    for org in divisions:
        # Reuse the already role-scoped portfolio collections so division dashboard
        # panels cannot reveal aggregate counts from outside the user's authority.
        ps = [project for project in projects if project.lead_org_id == org.id and project.status == "Active"]
        ds = [demand for demand in demands if demand.lead_org_id == org.id]
        caps = db.query(ResourceCapacity).filter(ResourceCapacity.org_id == org.id).all()
        division_rows.append({"org":org,"projects":len(ps),"at_risk":sum((p.health_override or p.health_owner) in exception_states for p in ps),"demands":len(ds),"capacity":round(sum(c.allocated_hours for c in caps)/sum(c.capacity_hours for c in caps)*100,1) if caps else 0})
    metrics = {m.key:m for m in db.query(MetricDefinition).all()}
    investment_flow = _portfolio_investment_flow(financials, projects, divisions)

    # ---- v0.7.9: decision-first additions -----------------------------------
    changes = []
    for p in at_risk:
        health = p.health_override or p.health_owner or p.health_calculated
        changes.append({"kind": "health", "label": f"{p.human_id} · {p.title}", "detail": f"Health is {health}", "href": f"/projects/{p.id}", "severity": "bad" if health in ("Off Track", "Blocked") else "warn"})
    for risk, project in high_risks[:5]:
        changes.append({"kind": "risk", "label": f"{risk.human_id} · {risk.title}", "detail": f"{risk.severity} risk open on {project.human_id}", "href": f"/projects/{project.id}", "severity": "bad" if risk.severity == "Critical" else "warn"})
    if budget and forecast > budget:
        changes.append({"kind": "cost", "label": "Portfolio cost forecast exceeds approved budget", "detail": f"Forecast {money(forecast)} vs approved {money(budget)}", "href": "/financials", "severity": "warn"})
    slipped = [(m, p) for m, p in milestones if m.baseline_date and m.current_date and m.current_date > m.baseline_date]
    for m, p in slipped[:4]:
        changes.append({"kind": "milestone", "label": f"{m.title}", "detail": f"{p.human_id} milestone moved to {m.current_date.strftime('%d %b %Y')}", "href": f"/projects/{p.id}", "severity": "warn"})
    for p in stale[:4]:
        changes.append({"kind": "stale", "label": f"{p.human_id} · {p.title}", "detail": "Status report is more than 14 days old", "href": f"/projects/{p.id}", "severity": "info"})
    severity_rank = {"bad": 0, "warn": 1, "info": 2}
    changes.sort(key=lambda c: severity_rank.get(c["severity"], 2))

    fresh_count = len(projects) - len(stale)
    health_explain = {
        "formula": "Health score = (On Track ×100 + At Risk ×60 + Off Track/Blocked ×20) ÷ active projects",
        "counts": {"On Track": on_track_count, "At Risk": at_risk_count, "Off Track / Blocked": off_track_count},
        "total": len(projects),
        "fresh": fresh_count,
        "stale": len(stale),
        "basis": "Effective health per project = leadership override → owner-reported → calculated, in that order.",
        "contributors": [
            {"id": p.human_id, "title": p.title, "health": (p.health_override or p.health_owner or p.health_calculated or "On Track"),
             "source": ("Override" if p.health_override else "Owner" if p.health_owner else "Calculated"),
             "href": f"/projects/{p.id}"}
            for p in projects
        ],
    }
    narrative = f"DDC5I is managing {len(projects)} active projects and {len(demands)} demands across mission, assessment, standards, architecture, infrastructure, and integration portfolios. Leadership attention is required for {len(at_risk)} project exceptions, {len(decisions_required)} pending demand decisions, {len(stale)} stale status records, and capacity utilization of {capacity_pct:.0f}%. Current accessible forecast is {money(forecast)} against an approved budget of {money(budget)}."
    dashboard_lens = dashboard_lens_for(user)
    dashboard_preference = db.query(DashboardPreference).filter(DashboardPreference.user_id == user.id).first()
    dashboard_order = list(dashboard_preference.panel_order or []) if dashboard_preference else []
    dashboard_order = dashboard_order + [panel for panel in dashboard_lens["panels"] if panel not in dashboard_order]
    dashboard_hidden = list(dashboard_preference.hidden_panels or []) if dashboard_preference else []
    dashboard_sizes = dict(dashboard_preference.panel_sizes or {}) if dashboard_preference else {}
    return render(
        request, "dashboard.html", user, db,
        projects=projects, demands=demands, at_risk=at_risk, decisions_required=decisions_required,
        capacity_pct=capacity_pct, budget=budget, actual=actual, forecast=forecast,
        benefit_target=benefit_target, benefit_realized=benefit_realized, benefit_is_money=benefit_is_money, benefit_unit=benefit_unit, stale=stale,
        pipeline=pipeline, pipeline_order=pipeline_order, max_pipeline=max_pipeline,
        milestones=milestones, dependencies=dependencies, division_rows=division_rows,
        metrics=metrics, narrative=narrative, recent_decisions=recent_decisions,
        decision_sources=decision_sources, high_risks=high_risks, my_tasks=my_tasks,
        my_actions=my_actions, health_score=health_score, health_segments=health_segments,
        investment_categories=investment_categories, investment_gradient=investment_gradient,
        investment_flow=investment_flow, portfolio_rows=portfolio_rows,
        changes=changes, health_explain=health_explain,
        dashboard_lens=dashboard_lens, dashboard_order=dashboard_order, dashboard_hidden=dashboard_hidden,
        dashboard_sizes=dashboard_sizes,
    )


@app.post("/dashboard/preferences")
def dashboard_preferences_save(
    request: Request, csrf: str = Form(...), panel_order: str = Form(""), hidden_panels: str = Form(""),
    panel_sizes: str = Form("{}"), reset: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    preference = db.query(DashboardPreference).filter(DashboardPreference.user_id == user.id).first()
    if not preference:
        preference = DashboardPreference(user_id=user.id); db.add(preference); db.flush()
    before = snapshot(preference)
    allowed = {"decisions", "changes", "kpis", "health", "my-work", "recent-decisions", "investment", "divisions", "portfolio"}
    if reset:
        preference.panel_order, preference.hidden_panels, preference.panel_sizes = [], [], {}
    else:
        order = [item for item in panel_order.split(",") if item in allowed]
        hidden = [item for item in hidden_panels.split(",") if item in allowed]
        try: sizes = {key: value for key, value in json.loads(panel_sizes or "{}").items() if key in allowed and value in {"compact", "standard", "wide"}}
        except (json.JSONDecodeError, AttributeError): sizes = {}
        preference.active_lens = dashboard_lens_for(user)["label"]
        preference.panel_order, preference.hidden_panels, preference.panel_sizes = list(dict.fromkeys(order)), list(dict.fromkeys(hidden)), sizes
    record_audit(db, user.id, "DashboardPreference", preference.id, "RESET" if reset else "UPDATE", before=before, after=snapshot(preference), ip_address=getattr(request.state, "client_ip", ""))
    db.commit(); return flash_redirect("/dashboard", "Dashboard layout reset to the role default." if reset else "Dashboard layout saved.")

@app.get("/records/{record_type}/{record_id}", response_class=HTMLResponse)
def record_detail(record_type: str, record_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    models={"task":Task,"milestone":Milestone,"raid":RaidItem,"dependency":Dependency,"decision":Decision,"action":Action}
    model=models.get(record_type.lower())
    if not model: raise HTTPException(404,"Record type not found")
    record=db.get(model,record_id)
    if not record: raise HTTPException(404,"Record not found")
    project=None
    project_id=getattr(record,"project_id",None) or getattr(record,"source_project_id",None)
    if project_id:
        project=get_accessible_project(db,user,project_id)
    elif getattr(record,"demand_id",None):
        get_accessible_demand(db,user,record.demand_id)
    users={u.id:u for u in db.query(User).all()}
    traceability=trace_for(db,record_type,record_type.title(),"Project Execution" if project else "Decision")
    return render(request,"record_detail.html",user,db,record=record,record_type=record_type.title(),project=project,users_map=users,audit=record_audit_events(db,record.id),traceability=traceability)

@app.get("/requirements/{req_id}", response_class=HTMLResponse)
def requirement_detail(req_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    req=db.query(RequirementTrace).filter(RequirementTrace.requirement_id==req_id).first()
    if not req: raise HTTPException(404,"Requirement not found")
    evidence=[]
    ref=(req.design_reference or "").lower()
    if "demand" in ref or "intake" in ref: evidence=[("Demand pipeline","/demands"),("Assessment workspace","/assessments")]
    elif "project" in ref or "task" in ref or "milestone" in ref: evidence=[("Project inventory","/projects"),("Portfolio dashboard","/dashboard")]
    elif "resource" in ref: evidence=[("Resource summary","/resources")]
    elif "financial" in ref or "budget" in ref: evidence=[("Financial summary","/financials")]
    elif "audit" in ref or "security" in ref: evidence=[("Audit history","/audit"),("Administration","/administration")]
    else: evidence=[("Executive dashboard","/dashboard"),("RTM filtered view",f"/requirements?q={req.requirement_id}")]
    return render(request,"requirement_detail.html",user,db,requirement=req,evidence=evidence,audit=record_audit_events(db,req.id))


@app.get("/metrics/{key}", response_class=HTMLResponse)
def metric_detail(key: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    metric = db.query(MetricDefinition).filter(MetricDefinition.key == key).first()
    if not metric:
        raise HTTPException(404, "Metric not found")
    return render(request, "metric.html", user, db, metric=metric)


def _division_workspace(db: Session, user: User, org: Organization) -> dict[str, Any]:
    projects = [
        project for project in db.query(Project).filter(Project.lead_org_id == org.id).order_by(Project.status, Project.title).all()
        if can_access_sensitive(user, project.sensitivity)
    ]
    project_ids = [project.id for project in projects]
    demands = [
        demand for demand in db.query(Demand).filter(Demand.lead_org_id == org.id).order_by(Demand.updated_at.desc()).all()
        if can_access_sensitive(user, demand.sensitivity)
    ]
    core = db.query(CoreFunction).filter(CoreFunction.org_id == org.id).all()
    capacities = db.query(ResourceCapacity).filter(ResourceCapacity.org_id == org.id).all()
    if project_ids:
        financials = db.query(FinancialRecord).filter(FinancialRecord.project_id.in_(project_ids)).all()
        milestones = db.query(Milestone, Project).join(Project, Milestone.project_id == Project.id).filter(Milestone.project_id.in_(project_ids)).order_by(Milestone.current_date).limit(12).all()
        raid = db.query(RaidItem, Project).join(Project, RaidItem.project_id == Project.id).filter(RaidItem.project_id.in_(project_ids), RaidItem.status != "Closed").order_by(RaidItem.exposure.desc()).limit(12).all()
        dependencies = db.query(Dependency, Project).join(Project, Dependency.source_project_id == Project.id).filter(Dependency.source_project_id.in_(project_ids)).all()
    else:
        financials, milestones, raid, dependencies = [], [], [], []
    missions = db.query(Mission).filter(Mission.owner_org_id == org.id).all()
    profile = db.query(DivisionProfile).filter(DivisionProfile.org_id == org.id).first()
    latest_briefing = db.query(PortfolioReview).filter(
        PortfolioReview.org_id == org.id,
        PortfolioReview.review_type == "Division Briefing",
    ).order_by(PortfolioReview.created_at.desc()).first()
    pipeline = Counter(demand.status for demand in demands)
    active_count = sum(project.status == "Active" for project in projects)
    exception_count = sum((project.health_override or project.health_owner) in {"At Risk", "Off Track", "Blocked"} for project in projects)
    severe_raid_count = sum(item.severity in {"High", "Critical"} for item, _project in raid)
    travel_requests = scoped_travel_requests(db, user).filter(TravelRequest.org_id == org.id).order_by(TravelRequest.departure_date.desc()).all()
    trip_reports = scoped_trip_reports(db, user).filter(TripReport.org_id == org.id).order_by(TripReport.return_date.desc()).all()
    travel_estimated_cost = sum(Decimal(item.estimated_cost or 0) for item in travel_requests)
    matched_request_ids = {item.request_id for item in trip_reports if item.request_id}
    travel_report_gap = sum(1 for item in travel_requests if item.return_date < date.today() and item.determination == "Approved" and item.id not in matched_request_ids)
    travel_reconciliation = sum(1 for item in trip_reports if not item.request_id)
    narrative = (
        f"{org.name} is executing {active_count} active projects, sustaining {len(core)} governed core functions, "
        f"and shaping {len(demands)} demands. Current exception load includes {exception_count} project health "
        f"exceptions and {severe_raid_count} high-severity assurance records."
    )
    return {
        "org": org,
        "profile": profile,
        "projects": projects,
        "demands": demands,
        "core": core,
        "capacities": capacities,
        "financials": financials,
        "milestones": milestones,
        "raid": raid,
        "dependencies": dependencies,
        "missions": missions,
        "pipeline": pipeline,
        "narrative": narrative,
        "latest_briefing": latest_briefing,
        "active_count": active_count,
        "exception_count": exception_count,
        "severe_raid_count": severe_raid_count,
        "travel_requests": travel_requests,
        "trip_reports": trip_reports,
        "travel_estimated_cost": travel_estimated_cost,
        "travel_report_gap": travel_report_gap,
        "travel_reconciliation": travel_reconciliation,
    }


def _division_export_payload(context: dict[str, Any]) -> dict[str, Any]:
    org: Organization = context["org"]
    profile: DivisionProfile | None = context["profile"]
    return {
        "schema_version": APP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "division": profile_to_dict(profile, org) if profile else {
            "schema_version": APP_VERSION, "division_code": org.code, "official_name": org.name, "narrative": org.narrative
        },
        "summary": {
            "active_projects": context["active_count"],
            "health_exceptions": context["exception_count"],
            "open_demands": len(context["demands"]),
            "core_functions": len(context["core"]),
            "forecast": float(sum((record.forecast or 0) for record in context["financials"])),
        },
        "projects": [
            {
                "id": project.human_id, "title": project.title, "status": project.status,
                "health": project.health_override or project.health_owner, "percent_complete": project.percent_complete,
                "budget": float(project.budget or 0), "actual": float(project.actual or 0), "forecast": float(project.forecast or 0),
                "start_date": project.start_date.isoformat() if project.start_date else None,
                "current_end_date": project.current_end_date.isoformat() if project.current_end_date else None,
            } for project in context["projects"]
        ],
        "demands": [
            {
                "id": demand.human_id, "title": demand.title, "category": demand.category, "status": demand.status,
                "urgency": demand.urgency, "required_date": demand.required_date.isoformat() if demand.required_date else None,
                "rom_cost": float(demand.rom_cost or 0), "next_action": demand.next_action,
            } for demand in context["demands"]
        ],
        "core_functions": [
            {
                "code": item.code, "title": item.title, "description": item.description, "health": item.health,
                "minimum_capacity_hours": item.minimum_capacity_hours, "allocated_capacity_hours": item.allocated_capacity_hours,
            } for item in context["core"]
        ],
        "capacity": [
            {
                "role": item.role_name, "skill": item.skill, "period": item.period,
                "capacity_hours": item.capacity_hours, "allocated_hours": item.allocated_hours, "actual_hours": item.actual_hours,
            } for item in context["capacities"]
        ],
        "financials": [
            {
                "project_id": next((project.human_id for project in context["projects"] if project.id == record.project_id), ""),
                "category": record.category, "approved_budget": float(record.approved_budget or 0),
                "actual_cost": float(record.actual_cost or 0), "forecast": float(record.forecast or 0),
                "funding_status": record.funding_status, "fiscal_year": record.fiscal_year,
            } for record in context["financials"]
        ],
        "milestones": [
            {
                "id": item.human_id, "title": item.title, "project_id": project.human_id,
                "current_date": item.current_date.isoformat() if item.current_date else None,
                "status": item.status, "confidence": item.confidence,
            } for item, project in context["milestones"]
        ],
        "raid": [
            {
                "id": item.human_id, "type": item.type, "title": item.title, "project_id": project.human_id,
                "severity": item.severity, "status": item.status, "owner_response": item.mitigation,
            } for item, project in context["raid"]
        ],
        "travel_requests": [
            {"id": item.human_id, "external_id": item.external_id, "traveler": item.traveler_name, "location": item.location,
             "determination": item.determination, "departure_date": item.departure_date.isoformat(), "return_date": item.return_date.isoformat(),
             "estimated_cost": float(item.estimated_cost or 0), "engagement_id": item.engagement_id, "source_filename": item.source_filename, "source_row": item.source_row}
            for item in context["travel_requests"]
        ],
        "trip_reports": [
            {"id": item.human_id, "title": item.title, "traveler": item.traveler_name, "location": item.location,
             "start_date": item.start_date.isoformat(), "return_date": item.return_date.isoformat(), "review_status": item.review_status,
             "request_id": item.request_id, "match_confidence": item.match_confidence, "source_filename": item.source_filename, "source_row": item.source_row}
            for item in context["trip_reports"]
        ],
    }


def _write_csv_file(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    if not rows:
        output.write("no_records\n")
        return output.getvalue()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value for key, value in row.items()})
    return output.getvalue()


@app.get("/divisions", response_class=HTMLResponse)
def divisions_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    order = {code: index for index, code in enumerate(["FO", "CCD", "AID", "C3OD2", "CID", "DSD", "JAD", "JFID"])}
    orgs = db.query(Organization).filter(Organization.org_type == "Division").all()
    orgs.sort(key=lambda item: (order.get(item.code, 99), item.code))
    rows = []
    for org in orgs:
        if not can_access_org(user, org.id):
            continue
        context = _division_workspace(db, user, org)
        rows.append({
            "org": org,
            "profile": context["profile"],
            "projects": context["projects"],
            "demands": len(context["demands"]),
            "at_risk": context["exception_count"],
            "latest_briefing": context["latest_briefing"],
        })
    return render(request, "divisions.html", user, db, rows=rows)


@app.get("/divisions/{code}", response_class=HTMLResponse)
def division_detail(code: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    org = db.query(Organization).filter(Organization.code == code.upper()).first()
    if not org or not can_access_org(user, org.id):
        raise HTTPException(404, "Division not found")
    context = _division_workspace(db, user, org)
    context["briefing_mode"] = request.query_params.get("mode") == "briefing"
    context["can_edit_profile"] = can_manage_division_profile(user, org.id)
    return render(request, "division_detail.html", user, db, **context)


@app.get("/divisions/{code}/export/{export_format}")
def division_export(code: str, export_format: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    org = db.query(Organization).filter(Organization.code == code.upper()).first()
    if not org or not can_access_org(user, org.id):
        raise HTTPException(404, "Division not found")
    context = _division_workspace(db, user, org)
    payload = _division_export_payload(context)
    filename_base = f"{org.code}_division_export_{APP_VERSION}"
    if export_format.lower() == "json":
        record_audit(db, user.id, "Division", org.id, "EXPORT_JSON", after={"schema_version": APP_VERSION})
        db.commit()
        return Response(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.json"'},
        )
    if export_format.lower() == "csv":
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            profile_row = payload["division"].copy()
            for key in ["focus_areas", "responsibilities", "branches", "initiatives", "relationships", "forums", "doctrine", "source_documents"]:
                if key in profile_row:
                    profile_row[key] = json.dumps(profile_row[key], ensure_ascii=False)
            bundle.writestr("division_profile.csv", _write_csv_file([profile_row]))
            bundle.writestr("projects.csv", _write_csv_file(payload["projects"]))
            bundle.writestr("demands.csv", _write_csv_file(payload["demands"]))
            bundle.writestr("core_functions.csv", _write_csv_file(payload["core_functions"]))
            bundle.writestr("capacity.csv", _write_csv_file(payload["capacity"]))
            bundle.writestr("financials.csv", _write_csv_file(payload["financials"]))
            bundle.writestr("milestones.csv", _write_csv_file(payload["milestones"]))
            bundle.writestr("raid.csv", _write_csv_file(payload["raid"]))
            bundle.writestr("travel_requests.csv", _write_csv_file(payload["travel_requests"]))
            bundle.writestr("trip_reports.csv", _write_csv_file(payload["trip_reports"]))
            bundle.writestr("README.txt", f"CSV package generated by JSJ6 Enterprise Portfolio Management v{APP_VERSION}.\nImport support on the division page applies to division_profile.csv or the JSON division object.\n")
        record_audit(db, user.id, "Division", org.id, "EXPORT_CSV", after={"schema_version": APP_VERSION, "files": 11})
        db.commit()
        archive.seek(0)
        return StreamingResponse(
            archive,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}_csv.zip"'},
        )
    raise HTTPException(400, "Export format must be json or csv")


@app.get("/divisions/{code}/profile/edit", response_class=HTMLResponse)
def division_profile_edit_page(code: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    org = db.query(Organization).filter(Organization.code == code.upper()).first()
    if not org or not can_access_org(user, org.id):
        raise HTTPException(404, "Division not found")
    require_division_profile_edit(user, org.id)
    profile = db.query(DivisionProfile).filter(DivisionProfile.org_id == org.id).first()
    if not profile:
        raise HTTPException(404, "Division profile not found")
    return render(request, "division_profile_edit.html", user, db, org=org, profile=profile, values=profile_form_values(profile))


@app.post("/divisions/{code}/profile/edit")
async def division_profile_edit(code: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    org = db.query(Organization).filter(Organization.code == code.upper()).first()
    if not org or not can_access_org(user, org.id):
        raise HTTPException(404, "Division not found")
    require_division_profile_edit(user, org.id)
    form = await request.form()
    require_csrf(request, user, form_token=str(form.get("csrf", "")))
    profile = db.query(DivisionProfile).filter(DivisionProfile.org_id == org.id).first()
    if not profile:
        raise HTTPException(404, "Division profile not found")
    before = snapshot(profile)
    data = {key: form.get(key, "") for key in [
        "mission", "vision", "focus_areas", "responsibilities", "branches", "initiatives",
        "relationships", "forums", "doctrine", "banner_asset", "banner_alt", "focal_x", "focal_y",
        "status", "source_documents", "source_notes",
    ]}
    normalized = normalize_profile_data(data, profile)
    if not normalized["mission"] or not normalized["banner_alt"]:
        return render(
            request, "division_profile_edit.html", user, db, org=org, profile=profile,
            values={**profile_form_values(profile), **{key: str(value) for key, value in data.items()}},
            error="Mission and banner alternative text are required.", status_code=422,
        )
    apply_profile_data(profile, normalized, user.id)
    org.narrative = profile.mission
    record_audit(db, user.id, "DivisionProfile", profile.id, "UPDATE", before=before, after=snapshot(profile), ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(f"/divisions/{org.code}", "Division profile published.")


@app.get("/divisions/{code}/profile/import", response_class=HTMLResponse)
def division_profile_import_page(code: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    org = db.query(Organization).filter(Organization.code == code.upper()).first()
    if not org or not can_access_org(user, org.id):
        raise HTTPException(404, "Division not found")
    require_division_profile_edit(user, org.id)
    return render(request, "division_profile_import.html", user, db, org=org)


@app.post("/divisions/{code}/profile/import/preview", response_class=HTMLResponse)
async def division_profile_import_preview(code: str, request: Request, file: UploadFile = File(...), csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    org = db.query(Organization).filter(Organization.code == code.upper()).first()
    if not org or not can_access_org(user, org.id):
        raise HTTPException(404, "Division not found")
    require_division_profile_edit(user, org.id)
    require_csrf(request, user, form_token=csrf)
    profile = db.query(DivisionProfile).filter(DivisionProfile.org_id == org.id).first()
    if not profile:
        raise HTTPException(404, "Division profile not found")
    raw = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB")
    suffix = Path(file.filename or "").suffix.lower()
    try:
        if suffix == ".json":
            incoming = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(incoming, dict):
                raise ValueError("JSON must contain an object.")
            incoming = incoming.get("division", incoming.get("profile", incoming))
        elif suffix == ".csv":
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            incoming = next(reader, None)
            if not incoming:
                raise ValueError("CSV must contain a header and one profile row.")
        else:
            raise ValueError("Use a .json or .csv profile file.")
        normalized = normalize_profile_data(incoming, profile)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        return render(request, "division_profile_import.html", user, db, org=org, error=str(exc), status_code=422)
    warnings = []
    if not normalized["mission"]:
        warnings.append("Mission is blank and must be completed before publishing.")
    if not normalized["banner_alt"]:
        warnings.append("Banner alternative text is blank and must be completed for accessibility.")
    if not normalized["focus_areas"]:
        warnings.append("No focus areas were supplied.")
    return render(
        request, "division_profile_import_preview.html", user, db, org=org,
        normalized=normalized, payload_json=json.dumps(normalized, ensure_ascii=False), warnings=warnings, filename=file.filename,
    )


@app.post("/divisions/{code}/profile/import/commit")
async def division_profile_import_commit(code: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    org = db.query(Organization).filter(Organization.code == code.upper()).first()
    if not org or not can_access_org(user, org.id):
        raise HTTPException(404, "Division not found")
    require_division_profile_edit(user, org.id)
    form = await request.form()
    require_csrf(request, user, form_token=str(form.get("csrf", "")))
    profile = db.query(DivisionProfile).filter(DivisionProfile.org_id == org.id).first()
    if not profile:
        raise HTTPException(404, "Division profile not found")
    try:
        incoming = json.loads(str(form.get("payload_json", "{}")))
        normalized = normalize_profile_data(incoming, profile)
    except (json.JSONDecodeError, TypeError, ValueError):
        raise HTTPException(422, "The profile preview payload is invalid. Upload the file again.")
    if not normalized["mission"] or not normalized["banner_alt"]:
        raise HTTPException(422, "Mission and banner alternative text are required before import.")
    before = snapshot(profile)
    apply_profile_data(profile, normalized, user.id)
    org.narrative = profile.mission
    record_audit(db, user.id, "DivisionProfile", profile.id, "IMPORT", before=before, after=snapshot(profile), ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(f"/divisions/{org.code}", "Division profile imported and published.")


@app.get("/strategy", response_class=HTMLResponse)
def strategy_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    missions=db.query(Mission).order_by(Mission.code).all()
    core=db.query(CoreFunction).order_by(CoreFunction.code).all()
    aligned=[]
    for mission in missions:
        aligned.append({"mission":mission,"demands":scoped_demands(db,user).filter(Demand.mission_id==mission.id).count(),"projects":scoped_projects(db,user).filter(Project.mission_id==mission.id).count(),"functions":db.query(CoreFunction).filter(CoreFunction.mission_id==mission.id).count()})
    unaligned=scoped_demands(db,user).filter(Demand.mission_id.is_(None)).all()
    return render(request,"strategy.html",user,db,aligned=aligned,core=core,unaligned=unaligned)


@app.get("/demands", response_class=HTMLResponse)
def demands_page(request: Request, q: str = "", status: str = "", division: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    query=scoped_demands(db,user)
    if q: query=query.filter(or_(Demand.title.ilike(f"%{q}%"),Demand.human_id.ilike(f"%{q}%"),Demand.purpose.ilike(f"%{q}%")))
    if status: query=query.filter(Demand.status==status)
    if division:
        org=db.query(Organization).filter(Organization.code==division).first()
        if org and can_access_org(user,org.id): query=query.filter(Demand.lead_org_id==org.id)
    demands=query.order_by(Demand.updated_at.desc()).all()
    statuses=[s for s in ALLOWED_TRANSITIONS.keys()]
    return render(request,"demands.html",user,db,demands=demands,q=q,status=status,division=division,statuses=statuses)


@app.get("/demands/new", response_class=HTMLResponse)
def demand_new_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user,"REQUESTER","DIVISION_PORTFOLIO_MANAGER","PMO","ADMIN","PROJECT_MANAGER")
    missions=db.query(Mission).order_by(Mission.code).all(); users=db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    return render(request,"demand_form.html",user,db,missions=missions,users=users,demand=None)


@app.post("/demands/new")
def demand_create(
    request: Request,
    csrf: str = Form(...), title: str = Form(...), category: str = Form(...), lead_org_id: str = Form(...), mission_id: str = Form(""), sponsor_id: str = Form(...), purpose: str = Form(""), problem: str = Form(""), desired_end_state: str = Form(""), beneficiaries: str = Form(""), required_date: str = Form(""), urgency: str = Form("Normal"), consequence_of_inaction: str = Form(""), preliminary_scope: str = Form(""), deliverables: str = Form(""), assumptions: str = Form(""), dependencies_text: str = Form(""), required_skills: str = Form(""), rom_cost: float = Form(0), expected_benefits: str = Form(""), confidence: str = Form("Medium"), sensitivity: str = Form("Controlled Unclassified"), action: str = Form("save"), db: Session = Depends(get_db), user: User = Depends(current_user)
):
    require_csrf(request,user,csrf); require_business_edit(user)
    if not can_access_org(user,lead_org_id): raise HTTPException(403,"Cannot create demand for another division")
    if sensitivity=="Restricted" and not user.sensitive_access: raise HTTPException(403,"Restricted submissions require approved access")
    if action=="submit" and (not mission_id or not purpose.strip() or not problem.strip() or not desired_end_state.strip()):
        return flash_redirect("/demands/new","Submission requires mission alignment, purpose, problem, and desired end state.","error")
    d=Demand(human_id=next_human_id(db,Demand,"DMD"),title=title.strip(),category=category,status="Submitted" if action=="submit" else "Draft",sensitivity=sensitivity,sponsor_id=sponsor_id,requester_id=user.id,requesting_org_id=lead_org_id,lead_org_id=lead_org_id,mission_id=mission_id or None,purpose=purpose,problem=problem,desired_end_state=desired_end_state,beneficiaries=beneficiaries,required_date=date.fromisoformat(required_date) if required_date else None,urgency=urgency,consequence_of_inaction=consequence_of_inaction,preliminary_scope=preliminary_scope,deliverables=deliverables,assumptions=assumptions,dependencies_text=dependencies_text,required_skills=required_skills,rom_cost=rom_cost,expected_benefits=expected_benefits,confidence=confidence,current_owner_id=user.id if action=="save" else db.query(User).filter(User.username=="pmo").first().id,next_action=demand_next_action("Submitted" if action=="submit" else "Draft"),target_decision_date=date.today()+timedelta(days=30))
    db.add(d); db.flush(); record_audit(db,user.id,"Demand",d.id,"CREATE",after=snapshot(d),ip_address=request.client.host if request.client else "")
    if action=="submit":
        for pmo in db.query(User).all():
            if has_role(pmo,"PMO","DIVISION_PORTFOLIO_MANAGER") and (is_enterprise_user(pmo) or pmo.division_id==d.lead_org_id): db.add(Notification(user_id=pmo.id,title=f"New demand submitted: {d.human_id}",message="A demand is ready for triage.",link=f"/demands/{d.id}",notification_type="Submission"))
    db.commit(); return flash_redirect(f"/demands/{d.id}",f"{d.human_id} {'submitted' if action=='submit' else 'saved as draft'}.")


@app.get("/demands/{demand_id}", response_class=HTMLResponse)
def demand_detail(demand_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    d=get_accessible_demand(db,user,demand_id)
    assessments=db.query(Assessment).filter(Assessment.demand_id==d.id).order_by(Assessment.created_at.desc()).all()
    decisions=db.query(Decision).filter(Decision.demand_id==d.id).order_by(Decision.created_at.desc()).all()
    actions=db.query(Action).filter(Action.demand_id==d.id).order_by(Action.due_date).all()
    revisions=db.query(DemandRevision).filter(DemandRevision.demand_id==d.id).order_by(DemandRevision.revision.desc()).all()
    project=db.query(Project).filter(Project.demand_id==d.id).first()
    users={u.id:u for u in db.query(User).all()}; orgs={o.id:o for o in db.query(Organization).all()}; missions={m.id:m for m in db.query(Mission).all()}
    allowed=ALLOWED_TRANSITIONS.get(d.status,set())
    traceability=trace_for(db,"Demand","Intake","Assessment","Decision","Stage Gate")
    return render(request,"demand_detail.html",user,db,demand=d,assessments=assessments,decisions=decisions,actions=actions,revisions=revisions,project=project,users_map=users,orgs_map=orgs,missions_map=missions,allowed_transitions=allowed,weights=DEFAULT_WEIGHTS,labels=LABELS,traceability=traceability,demand_editable=can_edit_demand_record(user,d))


@app.get("/demands/{demand_id}/edit", response_class=HTMLResponse)
def demand_edit_page(demand_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    demand = get_accessible_demand(db, user, demand_id)
    if not can_edit_demand_record(user, demand):
        raise HTTPException(403, "This demand is locked for direct editing at its current stage. Use a governed clarification or change decision.")
    missions = db.query(Mission).order_by(Mission.code).all()
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    return render(request, "demand_form.html", user, db, missions=missions, users=users, demand=demand)


@app.post("/demands/{demand_id}/edit")
def demand_edit(
    demand_id: str,
    request: Request,
    csrf: str = Form(...),
    expected_version: int = Form(...),
    title: str = Form(...),
    category: str = Form(...),
    lead_org_id: str = Form(...),
    mission_id: str = Form(""),
    sponsor_id: str = Form(...),
    purpose: str = Form(""),
    problem: str = Form(""),
    desired_end_state: str = Form(""),
    beneficiaries: str = Form(""),
    required_date: str = Form(""),
    urgency: str = Form("Normal"),
    consequence_of_inaction: str = Form(""),
    preliminary_scope: str = Form(""),
    deliverables: str = Form(""),
    assumptions: str = Form(""),
    dependencies_text: str = Form(""),
    required_skills: str = Form(""),
    rom_cost: float = Form(0),
    expected_benefits: str = Form(""),
    confidence: str = Form("Medium"),
    sensitivity: str = Form("Controlled Unclassified"),
    change_summary: str = Form(""),
    action: str = Form("save"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    require_business_edit(user)
    demand = get_accessible_demand(db, user, demand_id)
    if not can_edit_demand_record(user, demand):
        raise HTTPException(403, "This demand is locked for direct editing at its current stage. Use a governed clarification or change decision.")
    if demand.version != expected_version:
        return flash_redirect(f"/demands/{demand.id}/edit", "This demand changed after you opened it. Review the latest version before saving.", "error")
    if demand.status != "Draft" and not change_summary.strip():
        return flash_redirect(f"/demands/{demand.id}/edit", "A change summary is required for submitted demand revisions.", "error")
    if not can_access_org(user, lead_org_id):
        raise HTTPException(403, "Cannot move the demand to another unauthorized division")
    if sensitivity == "Restricted" and not user.sensitive_access:
        raise HTTPException(403, "Restricted demands require approved sensitive access")

    target_status = demand.status
    if action == "resubmit" and demand.status in {"Draft", "Clarification Required"}:
        target_status = "Submitted"
    if target_status == "Submitted" and (not mission_id or not purpose.strip() or not problem.strip() or not desired_end_state.strip()):
        return flash_redirect(f"/demands/{demand.id}/edit", "Submission requires mission alignment, purpose, problem, and desired end state.", "error")

    before = snapshot(demand)
    changes: list[str] = []
    field_values = {
        "title": title.strip(),
        "category": category,
        "lead_org_id": lead_org_id,
        "requesting_org_id": lead_org_id,
        "mission_id": mission_id or None,
        "sponsor_id": sponsor_id,
        "purpose": purpose.strip(),
        "problem": problem.strip(),
        "desired_end_state": desired_end_state.strip(),
        "beneficiaries": beneficiaries.strip(),
        "required_date": parse_optional_date(required_date),
        "urgency": urgency,
        "consequence_of_inaction": consequence_of_inaction.strip(),
        "preliminary_scope": preliminary_scope.strip(),
        "deliverables": deliverables.strip(),
        "assumptions": assumptions.strip(),
        "dependencies_text": dependencies_text.strip(),
        "required_skills": required_skills.strip(),
        "rom_cost": max(0, rom_cost),
        "expected_benefits": expected_benefits.strip(),
        "confidence": confidence,
        "sensitivity": sensitivity,
    }
    for field, value in field_values.items():
        if getattr(demand, field) != value:
            changes.append(field.replace("_", " "))
            setattr(demand, field, value)

    previous_status = demand.status
    demand.status = target_status
    if target_status == "Submitted":
        demand.pending_information = ""
        if previous_status in {"Draft", "Clarification Required"}:
            pmo = db.query(User).filter(User.username == "pmo").first()
            demand.current_owner_id = pmo.id if pmo else demand.current_owner_id
        demand.next_action = demand_next_action("Submitted")
    else:
        demand.next_action = demand_next_action(demand.status)
    demand.version += 1
    demand.updated_at = datetime.now(timezone.utc)

    summary = change_summary.strip() or ("Updated " + ", ".join(changes) if changes else "Reviewed submitted demand without field changes")
    if previous_status != target_status:
        summary += f"; moved from {previous_status} to {target_status}"
    db.add(DemandRevision(demand_id=demand.id, revision=demand.version, changed_by_id=user.id, snapshot=snapshot(demand), comment=summary))
    audit_action = "UPDATE_AFTER_SUBMISSION" if previous_status != "Draft" else "UPDATE"
    record_audit(db, user.id, "Demand", demand.id, audit_action, before=before, after=snapshot(demand), ip_address=request.client.host if request.client else "")

    recipients = {demand.current_owner_id, demand.requester_id, demand.sponsor_id}
    recipients.discard(None)
    recipients.discard(user.id)
    for recipient_id in recipients:
        db.add(Notification(
            user_id=recipient_id,
            title=f"Demand updated: {demand.human_id}",
            message=f"{user.full_name} updated version {demand.version}. Review the authoritative record and revision summary.",
            link=f"/demands/{demand.id}",
            notification_type="Demand Update",
        ))
    db.commit()
    verb = "resubmitted" if previous_status != target_status and target_status == "Submitted" else "updated"
    return flash_redirect(f"/demands/{demand.id}", f"{demand.human_id} {verb}; version {demand.version} recorded in revision history.")


@app.post("/demands/{demand_id}/transition")
def demand_transition(demand_id: str, request: Request, csrf: str = Form(...), target_status: str = Form(...), comment: str = Form(""), pending_information: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_business_edit(user); d=get_accessible_demand(db,user,demand_id)
    try: validate_transition(d.status,target_status,user.roles or [])
    except PermissionError as e: raise HTTPException(403,str(e))
    except ValueError as e: return flash_redirect(f"/demands/{d.id}",str(e),"error")
    if target_status=="Submitted" and (not d.mission_id or not d.purpose or not d.problem or not d.desired_end_state): return flash_redirect(f"/demands/{d.id}","Submission readiness failed: mission, purpose, problem, and desired end state are required.","error")
    if target_status=="Awaiting Portfolio Recommendation" and not db.query(Assessment).filter(Assessment.demand_id==d.id).first(): return flash_redirect(f"/demands/{d.id}","At least one completed assessment is required.","error")
    before=snapshot(d); d.version+=1; d.status=target_status; d.next_action=demand_next_action(target_status); d.pending_information=pending_information if target_status=="Clarification Required" else ""; d.updated_at=datetime.now(timezone.utc)
    db.add(DemandRevision(demand_id=d.id,revision=d.version,changed_by_id=user.id,snapshot=snapshot(d),comment=comment or f"Transitioned to {target_status}")); record_audit(db,user.id,"Demand",d.id,"STATUS_TRANSITION",before=before,after=snapshot(d),ip_address=request.client.host if request.client else "")
    db.add(Notification(user_id=d.requester_id,title=f"Demand {d.human_id}: {target_status}",message=d.next_action,link=f"/demands/{d.id}",notification_type="Workflow")); db.commit()
    return flash_redirect(f"/demands/{d.id}",f"Demand moved to {target_status}.")


@app.post("/demands/{demand_id}/assess")
def demand_assess(demand_id: str, request: Request, csrf: str = Form(...), rationale: str = Form(...), confidence: str = Form("Medium"), adjudication: str = Form(""), mission_criticality: float = Form(...), strategic_alignment: float = Form(...), operational_impact: float = Form(...), urgency: float = Form(...), risk_reduction: float = Form(...), readiness_interoperability: float = Form(...), feasibility: float = Form(...), expected_value: float = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"ASSESSOR","PMO","DIVISION_PORTFOLIO_MANAGER","ADMIN"); d=get_accessible_demand(db,user,demand_id)
    scores={"mission_criticality":mission_criticality,"strategic_alignment":strategic_alignment,"operational_impact":operational_impact,"urgency":urgency,"risk_reduction":risk_reduction,"readiness_interoperability":readiness_interoperability,"feasibility":feasibility,"expected_value":expected_value}
    try: total=calculate_weighted_score(scores)
    except ValueError as e: return flash_redirect(f"/demands/{d.id}",str(e),"error")
    a=Assessment(demand_id=d.id,assessor_id=user.id,scores=scores,rationale=rationale,confidence=confidence,total_score=total,adjudication=adjudication); db.add(a); db.flush()
    totals=[x.total_score for x in db.query(Assessment).filter(Assessment.demand_id==d.id).all()]
    before=snapshot(d); d.score_total=round(sum(totals)/len(totals),2); d.score_variance=score_variance(totals); d.status="Assessment"; d.next_action=demand_next_action(d.status); d.updated_at=datetime.now(timezone.utc)
    record_audit(db,user.id,"Assessment",a.id,"CREATE",after=snapshot(a)); record_audit(db,user.id,"Demand",d.id,"SCORE_UPDATED",before=before,after=snapshot(d)); db.commit()
    return flash_redirect(f"/demands/{d.id}",f"Assessment recorded. Weighted score: {total:.1f}.")


@app.get("/assessments", response_class=HTMLResponse)
def assessments_page(request: Request, ids: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    query=scoped_demands(db,user).filter(Demand.status.in_(["Assessment","Awaiting Portfolio Recommendation","Awaiting Decision","Approved","Deferred"]))
    if ids:
        selected=[x for x in ids.split(",") if x]; query=query.filter(Demand.id.in_(selected))
    demands=query.order_by(Demand.score_total.desc().nullslast()).all()
    users={u.id:u for u in db.query(User).all()}; orgs={o.id:o for o in db.query(Organization).all()}
    assessment_map={d.id:db.query(Assessment).filter(Assessment.demand_id==d.id).all() for d in demands}
    return render(request,"assessments.html",user,db,demands=demands,users_map=users,orgs_map=orgs,assessment_map=assessment_map,weights=DEFAULT_WEIGHTS,labels=LABELS)


@app.post("/demands/{demand_id}/decision")
def demand_decision(demand_id: str, request: Request, csrf: str = Form(...), decision: str = Form(...), rationale: str = Form(...), participants: str = Form(""), evidence: str = Form(""), conditions: str = Form(""), caveats: str = Form(""), resource_implications: str = Form(""), financial_implications: str = Form(""), review_date: str = Form(""), beyond_capacity: str = Form(""), capacity_tradeoff: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"APPROVAL_AUTHORITY","SENIOR_LEADER","ADMIN"); d=get_accessible_demand(db,user,demand_id)
    if d.status not in {"Awaiting Decision","Approved","Deferred"}: return flash_redirect(f"/demands/{d.id}","Demand is not at a leadership decision gate.","error")
    if decision=="Approve" and beyond_capacity and not capacity_tradeoff.strip(): return flash_redirect(f"/demands/{d.id}","Approval beyond capacity requires a stop, delay, reduce, de-scope, or capacity-increase tradeoff.","error")
    status_map={"Approve":"Approved","Decline":"Declined","Defer":"Deferred","Pilot":"Approved","Merge":"Deferred","Re-scope":"Assessment","Perform as core work":"Approved","Outsource":"Approved","Request additional analysis":"Assessment"}
    before=snapshot(d); d.status=status_map.get(decision,d.status); d.disposition=decision; d.capacity_tradeoff=capacity_tradeoff; d.next_action=demand_next_action(d.status)
    dec=Decision(human_id=next_human_id(db,Decision,"DEC"),demand_id=d.id,decision=decision,authority_id=user.id,participants=participants,rationale=rationale,evidence=evidence,conditions=conditions,caveats=caveats,resource_implications=resource_implications,financial_implications=financial_implications,review_date=date.fromisoformat(review_date) if review_date else None); db.add(dec); db.flush()
    for line in [x.strip(" -") for x in conditions.splitlines() if x.strip()]:
        db.add(Action(human_id=next_human_id(db,Action,"ACT"),demand_id=d.id,decision_id=dec.id,title=line,owner_id=d.current_owner_id or d.requester_id,due_date=(date.fromisoformat(review_date) if review_date else date.today()+timedelta(days=30)),source_type="Decision condition"))
    record_audit(db,user.id,"Decision",dec.id,"CREATE",after=snapshot(dec)); record_audit(db,user.id,"Demand",d.id,"DECISION_APPLIED",before=before,after=snapshot(d)); db.add(Notification(user_id=d.requester_id,title=f"Decision recorded for {d.human_id}",message=f"Disposition: {decision}. Review the authoritative decision record.",link=f"/demands/{d.id}",notification_type="Approval")); db.commit()
    return flash_redirect(f"/demands/{d.id}",f"Decision recorded: {decision}.")


@app.post("/demands/{demand_id}/convert")
def demand_convert(demand_id: str, request: Request, csrf: str = Form(...), manager_id: str = Form(...), start_date: str = Form(""), end_date: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"PMO","PROJECT_MANAGER","ADMIN","ENTERPRISE_PORTFOLIO_OWNER"); d=get_accessible_demand(db,user,demand_id)
    if d.status!="Approved": return flash_redirect(f"/demands/{d.id}","Only an approved demand can be converted.","error")
    existing=db.query(Project).filter(Project.demand_id==d.id).first()
    if existing: return flash_redirect(f"/projects/{existing.id}","This demand is already linked to a project.")
    portfolio=db.query(Portfolio).filter(Portfolio.org_id==d.lead_org_id).first()
    p=Project(human_id=next_human_id(db,Project,"PRJ"),title=d.title,description=d.purpose,lead_org_id=d.lead_org_id,portfolio_id=portfolio.id if portfolio else None,sponsor_id=d.sponsor_id,manager_id=manager_id,mission_id=d.mission_id,demand_id=d.id,desired_end_state=d.desired_end_state,scope=d.preliminary_scope,deliverables=d.deliverables,start_date=date.fromisoformat(start_date) if start_date else date.today(),baseline_end_date=date.fromisoformat(end_date) if end_date else d.required_date,current_end_date=date.fromisoformat(end_date) if end_date else d.required_date,budget=d.rom_cost,forecast=d.rom_cost,benefit_expected=float(d.rom_cost)*0.4,sensitivity=d.sensitivity); db.add(p); db.flush()
    for i,title in enumerate(["Initiate and baseline","Deliver approved scope","Validate and transition"]): db.add(Task(human_id=next_human_id(db,Task,"TSK"),project_id=p.id,title=title,board_column="Backlog",status="Not Started",owner_id=manager_id,sequence=i+1,estimated_effort=40))
    before=snapshot(d); d.status="Converted to Execution"; d.disposition=f"Converted to {p.human_id}"; d.next_action=demand_next_action(d.status); record_audit(db,user.id,"Project",p.id,"CREATE_FROM_DEMAND",after=snapshot(p)); record_audit(db,user.id,"Demand",d.id,"CONVERTED",before=before,after=snapshot(d)); db.commit()
    return flash_redirect(f"/projects/{p.id}",f"{d.human_id} converted to {p.human_id} without re-entering approved data.")


@app.get("/templates", response_class=HTMLResponse)
def project_templates_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    templates_rows = db.query(ProjectTemplate).filter(ProjectTemplate.active.is_(True)).order_by(ProjectTemplate.category, ProjectTemplate.name, ProjectTemplate.version.desc()).all()
    orgs = [org for org in db.query(Organization).filter(Organization.org_type == "Division", Organization.active.is_(True)).order_by(Organization.code).all() if can_access_org(user, org.id)]
    missions = db.query(Mission).filter(Mission.status == "Active").order_by(Mission.code).all()
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    return render(request, "project_templates.html", user, db, templates_rows=templates_rows, eligible_orgs=orgs, missions=missions, eligible_users=users)


def _generate_blueprint_structure(db: Session, user: User, project: Project, template: ProjectTemplate, start: date) -> None:
    """Generate version-traceable board, task, milestone, and dependency records."""
    blueprint = dict(template.blueprint or {})
    column_specs = list(blueprint.get("columns", [])) or [{"name": item[0], "wip_limit": item[2]} for item in DEFAULT_BOARD_COLUMNS]
    for position, spec in enumerate(column_specs):
        db.add(BoardColumn(
            project_id=project.id, name=str(spec.get("name", f"Column {position + 1}"))[:80], position=position,
            wip_limit=max(0, int(spec.get("wip_limit", 0))), entry_criteria=str(spec.get("entry_criteria", "")),
            exit_criteria=str(spec.get("exit_criteria", "")),
        ))
    db.flush()
    generated: list[Task] = []
    first_column = str(column_specs[0].get("name", "Backlog"))
    for sequence, spec in enumerate(list(blueprint.get("tasks", [])), start=1):
        task = Task(
            human_id=next_human_id(db, Task, "TSK"), project_id=project.id,
            title=str(spec.get("title", f"Blueprint task {sequence}"))[:240], task_type=str(spec.get("type", "Task"))[:40],
            priority=str(spec.get("priority", "Medium"))[:30],
            description=f"Generated from {template.code} v{template.version}; tailor execution details while preserving traceability.",
            owner_id=project.manager_id, start_date=start if sequence == 1 else None,
            due_date=start + timedelta(days=max(0, int(spec.get("offset", sequence * 14)))),
            estimated_effort=max(0, float(spec.get("effort", 0))), board_column=first_column, status="Not Started",
            sequence=sequence, tags=["blueprint", template.code.lower()], notes=f"Blueprint source: {template.code} v{template.version}.",
            custom_fields={"template_code": template.code, "template_version": template.version},
        )
        db.add(task); db.flush(); generated.append(task)
        db.add(TaskNoteRevision(task_id=task.id, author_id=user.id, revision=1, body=task.notes, change_summary="Blueprint-generated notes"))
    for index, spec in enumerate(list(blueprint.get("milestones", [])), start=1):
        milestone_date = start + timedelta(days=max(0, int(spec.get("offset", index * 30))))
        db.add(Milestone(
            human_id=next_human_id(db, Milestone, "MS"), project_id=project.id,
            title=str(spec.get("title", f"Blueprint milestone {index}"))[:240], baseline_date=milestone_date,
            current_date=milestone_date, status="Not Started", confidence="Medium", owner_id=project.manager_id,
            critical=bool(spec.get("critical", False)),
        ))
    for index in range(1, len(generated)):
        db.add(TaskRelationship(
            source_task_id=generated[index].id, target_task_id=generated[index - 1].id,
            relationship_type="Finish-to-start", created_by_id=user.id,
        ))


@app.get("/projects/new", response_class=HTMLResponse)
def project_new_page(request: Request, template: str = "", division: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "PROJECT_MANAGER", "PMO", "DIVISION_PORTFOLIO_MANAGER", "DIVISION_CHIEF", "ADMIN")
    template_rows = db.query(ProjectTemplate).filter(ProjectTemplate.active.is_(True)).order_by(ProjectTemplate.category, ProjectTemplate.name).all()
    orgs = [org for org in db.query(Organization).filter(Organization.org_type == "Division", Organization.active.is_(True)).order_by(Organization.code).all() if can_access_org(user, org.id)]
    missions = db.query(Mission).filter(Mission.status == "Active").order_by(Mission.code).all()
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    portfolios = db.query(Portfolio).order_by(Portfolio.code).all()
    selected_template = next((item for item in template_rows if item.id == template or item.code == template.upper()), None)
    selected_org = next((item for item in orgs if item.code == division.upper()), None)
    return render(request, "project_form.html", user, db, templates_rows=template_rows, eligible_orgs=orgs,
                  missions=missions, eligible_users=users, portfolios=portfolios, selected_template=selected_template,
                  selected_org=selected_org, return_to=safe_local_path(request.query_params.get("return_to"), "/projects"))


@app.post("/projects")
def project_create(
    request: Request, csrf: str = Form(...), title: str = Form(...), description: str = Form(""),
    governance_level: str = Form("Division Local"), lead_org_id: str = Form(...), mission_id: str = Form(...),
    sponsor_id: str = Form(...), manager_id: str = Form(...), template_id: str = Form(...),
    start_date: str = Form(""), target_end_date: str = Form(""), scope: str = Form(""),
    desired_end_state: str = Form(""), deliverables: str = Form(""), funding_posture: str = Form("No Additional Funding"),
    resource_posture: str = Form("Existing Capacity"), sensitivity: str = Form("Controlled Unclassified"),
    portfolio_id: str = Form(""), return_to: str = Form("/projects"),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "PMO", "DIVISION_PORTFOLIO_MANAGER", "DIVISION_CHIEF", "ADMIN")
    if not can_access_org(user, lead_org_id):
        raise HTTPException(403, "You cannot create a project for that division")
    template = db.get(ProjectTemplate, template_id)
    mission, sponsor, manager = db.get(Mission, mission_id), db.get(User, sponsor_id), db.get(User, manager_id)
    if not template or not template.active or not mission or not sponsor or not manager:
        return flash_redirect("/projects/new", "Blueprint, mission, sponsor, and project manager are required.", "error")
    if governance_level not in {"Division Local", "Portfolio Managed"}:
        return flash_redirect("/projects/new", "Choose a valid project governance level.", "error")
    start = parse_optional_date(start_date) or date.today()
    blueprint = dict(template.blueprint or {})
    specs = list(blueprint.get("tasks", [])) + list(blueprint.get("milestones", []))
    horizon = max([int(item.get("offset", 0)) for item in specs] or [90])
    end = parse_optional_date(target_end_date) or start + timedelta(days=horizon)
    selected_portfolio = db.get(Portfolio, portfolio_id) if portfolio_id else db.query(Portfolio).filter(Portfolio.org_id == lead_org_id).first()
    if governance_level == "Division Local":
        selected_portfolio = None
    project = Project(
        human_id=next_human_id(db, Project, "PRJ"), title=title.strip(), description=description.strip(),
        work_type="Local Project" if governance_level == "Division Local" else "Portfolio Project",
        lead_org_id=lead_org_id, portfolio_id=selected_portfolio.id if selected_portfolio else None,
        sponsor_id=sponsor.id, manager_id=manager.id, mission_id=mission.id, template_code=template.code,
        template_version=template.version, governance_level=governance_level, funding_posture=funding_posture,
        resource_posture=resource_posture, promotion_status="Eligible" if governance_level == "Division Local" else "Not Required",
        created_by_id=user.id, desired_end_state=desired_end_state.strip(), scope=scope.strip(), deliverables=deliverables.strip(),
        start_date=start, baseline_end_date=end, current_end_date=end, status="Active", sensitivity=sensitivity,
        health_owner="On Track", health_calculated="On Track",
    )
    db.add(project); db.flush(); _generate_blueprint_structure(db, user, project, template, start)
    record_audit(db, user.id, "Project", project.id, "CREATE", after={**snapshot(project), "template_id": template.id}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(f"/projects/{project.id}?tab=wbs", f"{project.human_id} created as a {governance_level.lower()} project.")


@app.post("/templates/{template_id}/instantiate")
def project_template_instantiate(
    template_id: str,
    request: Request,
    csrf: str = Form(...),
    title: str = Form(...),
    lead_org_id: str = Form(...),
    mission_id: str = Form(...),
    sponsor_id: str = Form(...),
    manager_id: str = Form(...),
    start_date: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN")
    template = db.get(ProjectTemplate, template_id)
    if not template or not template.active:
        raise HTTPException(404, "Project template not found")
    if not can_access_org(user, lead_org_id):
        raise HTTPException(403, "You cannot create a project for that division")
    mission = db.get(Mission, mission_id)
    sponsor = db.get(User, sponsor_id)
    manager = db.get(User, manager_id)
    if not mission or not sponsor or not manager:
        return flash_redirect("/templates", "Mission, sponsor, and project manager are required.", "error")
    start = parse_optional_date(start_date) or date.today()
    blueprint = dict(template.blueprint or {})
    task_specs = list(blueprint.get("tasks", []))
    milestone_specs = list(blueprint.get("milestones", []))
    horizon = max([int(item.get("offset", 0)) for item in task_specs + milestone_specs] or [90])
    portfolio = db.query(Portfolio).filter(Portfolio.org_id == lead_org_id).first()
    project = Project(
        human_id=next_human_id(db, Project, "PRJ"),
        title=title.strip(),
        description=f"Created from {template.name} v{template.version}. {template.description}",
        lead_org_id=lead_org_id,
        portfolio_id=portfolio.id if portfolio else None,
        sponsor_id=sponsor.id,
        manager_id=manager.id,
        mission_id=mission.id,
        template_code=template.code,
        template_version=template.version,
        desired_end_state="The approved template outcomes are delivered, accepted, transitioned, and measured.",
        scope=f"Execute the immutable {template.code} v{template.version} blueprint with governed tailoring.",
        deliverables="See template-generated WBS, milestones, evidence, and status reports.",
        start_date=start,
        baseline_end_date=start + timedelta(days=horizon),
        current_end_date=start + timedelta(days=horizon),
        status="Active",
        health_owner="On Track",
        health_calculated="On Track",
    )
    db.add(project)
    db.flush()
    column_specs = list(blueprint.get("columns", [])) or [{"name": item[0], "wip_limit": item[2]} for item in DEFAULT_BOARD_COLUMNS]
    for position, spec in enumerate(column_specs):
        db.add(BoardColumn(project_id=project.id, name=str(spec.get("name", f"Column {position + 1}"))[:80], position=position, wip_limit=max(0, int(spec.get("wip_limit", 0))), entry_criteria=str(spec.get("entry_criteria", "")), exit_criteria=str(spec.get("exit_criteria", ""))))
    db.flush()
    generated_tasks: list[Task] = []
    first_column = str(column_specs[0].get("name", "Backlog"))
    for sequence, spec in enumerate(task_specs, start=1):
        due = start + timedelta(days=max(0, int(spec.get("offset", sequence * 14))))
        task = Task(
            human_id=next_human_id(db, Task, "TSK"), project_id=project.id, title=str(spec.get("title", f"Template task {sequence}"))[:240],
            task_type=str(spec.get("type", "Task"))[:40], priority=str(spec.get("priority", "Medium"))[:30],
            description=f"Generated from {template.code} v{template.version}; tailor details while preserving traceability.",
            owner_id=manager.id, start_date=start if sequence == 1 else None, due_date=due,
            estimated_effort=max(0, float(spec.get("effort", 0))), board_column=first_column,
            status="Not Started", sequence=sequence, tags=["template", template.code.lower()],
            notes=f"Template source: {template.code} v{template.version}.",
            custom_fields={"template_code": template.code, "template_version": template.version},
        )
        db.add(task)
        db.flush()
        generated_tasks.append(task)
        db.add(TaskNoteRevision(task_id=task.id, author_id=user.id, revision=1, body=task.notes, change_summary="Template-generated notes"))
    for index, spec in enumerate(milestone_specs, start=1):
        milestone_date = start + timedelta(days=max(0, int(spec.get("offset", index * 30))))
        db.add(Milestone(human_id=next_human_id(db, Milestone, "MS"), project_id=project.id, title=str(spec.get("title", f"Template milestone {index}"))[:240], baseline_date=milestone_date, current_date=milestone_date, status="Not Started", confidence="Medium", owner_id=manager.id, critical=bool(spec.get("critical", False))))
    for index in range(1, len(generated_tasks)):
        db.add(TaskRelationship(source_task_id=generated_tasks[index].id, target_task_id=generated_tasks[index - 1].id, relationship_type="Finish-to-start", created_by_id=user.id))
    record_audit(db, user.id, "Project", project.id, "CREATE_FROM_TEMPLATE", after={**snapshot(project), "template_id": template.id, "template_code": template.code, "template_version": template.version}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(f"/projects/{project.id}?tab=wbs", f"{project.human_id} created from {template.name} v{template.version}.")


@app.get("/roadmaps", response_class=HTMLResponse)
def roadmaps_page(request: Request, division: str = "", status: str = "Active", db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = scoped_projects(db, user)
    if status:
        query = query.filter(Project.status == status)
    if division:
        org = db.query(Organization).filter(Organization.code == division).first()
        if org and can_access_org(user, org.id):
            query = query.filter(Project.lead_org_id == org.id)
    projects = query.order_by(Project.start_date, Project.current_end_date).all()
    starts = [project.start_date for project in projects if project.start_date]
    ends = [project.current_end_date or project.baseline_end_date for project in projects if project.current_end_date or project.baseline_end_date]
    timeline_start = min(starts) if starts else date.today()
    timeline_end = max(ends) if ends else timeline_start + timedelta(days=180)
    total_days = max(1, (timeline_end - timeline_start).days + 1)
    rows = []
    for project in projects:
        start = project.start_date or timeline_start
        end = project.current_end_date or project.baseline_end_date or start
        left = max(0.0, min(100.0, ((start - timeline_start).days / total_days) * 100))
        width = max(1.5, min(100.0 - left, (((end - start).days + 1) / total_days) * 100))
        rows.append({"project": project, "left": left, "width": width, "start": start, "end": end})
    orgs = {org.id: org for org in db.query(Organization).all()}
    return render(request, "roadmaps.html", user, db, rows=rows, orgs_map=orgs, timeline_start=timeline_start, timeline_end=timeline_end, total_days=total_days, selected_division=division, selected_status=status)


@app.get("/projects", response_class=HTMLResponse)
def projects_page(request: Request, q: str = "", health: str = "", status: str = "", division: str = "", promotion: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    query=scoped_projects(db,user)
    if q: query=query.filter(or_(Project.title.ilike(f"%{q}%"),Project.human_id.ilike(f"%{q}%")))
    if health: query=query.filter(or_(Project.health_owner==health,Project.health_override==health,Project.health_calculated==health))
    if status: query=query.filter(Project.status==status)
    if promotion:
        promoted_project_ids = db.query(ProjectPromotionRequest.project_id).filter(ProjectPromotionRequest.status == promotion)
        query = query.filter(Project.id.in_(promoted_project_ids))
    if division:
        org=db.query(Organization).filter(Organization.code==division).first()
        if org and can_access_org(user,org.id): query=query.filter(Project.lead_org_id==org.id)
    projects=query.order_by(Project.updated_at.desc()).all(); orgs={o.id:o for o in db.query(Organization).all()}; users={u.id:u for u in db.query(User).all()}
    pending_promotions = db.query(ProjectPromotionRequest).filter(ProjectPromotionRequest.status == "Submitted").count() if has_role(user, "DIVISION_CHIEF", "PMO", "ENTERPRISE_PORTFOLIO_OWNER", "ADMIN") else 0
    return render(request,"projects.html",user,db,projects=projects,orgs_map=orgs,users_map=users,q=q,health=health,status=status,division=division,promotion=promotion,pending_promotions=pending_promotions)


@app.get("/projects/{project_id}/promotion", response_class=HTMLResponse)
def project_promotion_page(project_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = get_accessible_project(db, user, project_id)
    promotions = db.query(ProjectPromotionRequest).filter(ProjectPromotionRequest.project_id == project.id).order_by(ProjectPromotionRequest.created_at.desc()).all()
    portfolios = db.query(Portfolio).order_by(Portfolio.code).all()
    can_request = project.governance_level == "Division Local" and has_role(user, "PROJECT_MANAGER", "DIVISION_PORTFOLIO_MANAGER", "DIVISION_CHIEF", "PMO", "ADMIN")
    can_decide = has_role(user, "DIVISION_CHIEF", "PMO", "ENTERPRISE_PORTFOLIO_OWNER", "ADMIN")
    return render(request, "project_promotion.html", user, db, project=project, promotions=promotions, portfolios=portfolios,
                  can_request=can_request, can_decide=can_decide, users_map={item.id: item for item in db.query(User).all()})


@app.post("/projects/{project_id}/promotion")
def project_promotion_submit(
    project_id: str, request: Request, csrf: str = Form(...), reason: str = Form(...), scope_change: str = Form(""),
    enterprise_impact: str = Form(""), funding_requirement: str = Form(""), resource_requirement: str = Form(""),
    schedule_risk: str = Form(""), requested_portfolio_id: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "PROJECT_MANAGER", "DIVISION_PORTFOLIO_MANAGER", "DIVISION_CHIEF", "PMO", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    if project.governance_level != "Division Local":
        return flash_redirect(f"/projects/{project.id}/promotion", "Only division-local projects require portfolio promotion.", "error")
    if db.query(ProjectPromotionRequest).filter(ProjectPromotionRequest.project_id == project.id, ProjectPromotionRequest.status == "Submitted").first():
        return flash_redirect(f"/projects/{project.id}/promotion", "A promotion request is already awaiting review.", "error")
    promotion = ProjectPromotionRequest(
        human_id=next_human_id(db, ProjectPromotionRequest, "PPR"), project_id=project.id, requested_by_id=user.id,
        reason=reason.strip(), scope_change=scope_change.strip(), enterprise_impact=enterprise_impact.strip(),
        funding_requirement=funding_requirement.strip(), resource_requirement=resource_requirement.strip(),
        schedule_risk=schedule_risk.strip(), requested_portfolio_id=requested_portfolio_id or None,
    )
    before = snapshot(project); project.promotion_status = "Submitted"
    db.add(promotion); db.flush()
    record_audit(db, user.id, "ProjectPromotionRequest", promotion.id, "SUBMIT", after=snapshot(promotion), ip_address=getattr(request.state, "client_ip", ""))
    record_audit(db, user.id, "Project", project.id, "PROMOTION_REQUESTED", before=before, after=snapshot(project), ip_address=getattr(request.state, "client_ip", ""))
    db.commit(); return flash_redirect(f"/projects/{project.id}/promotion", f"{promotion.human_id} submitted for portfolio review.")


@app.post("/projects/{project_id}/promotion/{promotion_id}/decision")
def project_promotion_decide(
    project_id: str, promotion_id: str, request: Request, csrf: str = Form(...), decision: str = Form(...),
    decision_rationale: str = Form(...), conditions: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "DIVISION_CHIEF", "PMO", "ENTERPRISE_PORTFOLIO_OWNER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    promotion = db.get(ProjectPromotionRequest, promotion_id)
    if not promotion or promotion.project_id != project.id or promotion.status != "Submitted":
        raise HTTPException(404, "Open promotion request not found")
    if decision not in {"Approved", "Returned", "Declined"}:
        return flash_redirect(f"/projects/{project.id}/promotion", "Choose a valid decision.", "error")
    before_promotion, before_project = snapshot(promotion), snapshot(project)
    promotion.status, promotion.reviewed_by_id, promotion.reviewed_at = decision, user.id, datetime.now(timezone.utc)
    promotion.decision_rationale, promotion.conditions = decision_rationale.strip(), conditions.strip()
    if decision == "Approved":
        portfolio = db.get(Portfolio, promotion.requested_portfolio_id) if promotion.requested_portfolio_id else db.query(Portfolio).filter(Portfolio.org_id == project.lead_org_id).first()
        project.portfolio_id = portfolio.id if portfolio else project.portfolio_id
        project.governance_level, project.work_type, project.promotion_status = "Portfolio Managed", "Portfolio Project", "Approved"
        if promotion.funding_requirement:
            project.funding_posture = "Funding Required"
        if promotion.resource_requirement:
            project.resource_posture = "Additional Resources Required"
    else:
        project.promotion_status = decision
    record_audit(db, user.id, "ProjectPromotionRequest", promotion.id, "DECISION", before=before_promotion, after=snapshot(promotion), ip_address=getattr(request.state, "client_ip", ""))
    record_audit(db, user.id, "Project", project.id, "PROMOTION_DECISION", before=before_project, after=snapshot(project), ip_address=getattr(request.state, "client_ip", ""))
    db.commit(); return flash_redirect(f"/projects/{project.id}/promotion", f"{promotion.human_id} {decision.lower()}.")


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(project_id: str, request: Request, tab: str = "overview", task: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = get_accessible_project(db, user, project_id)
    valid_tabs = {"overview", "board", "wbs", "schedule", "milestones", "raid", "financial", "status", "board-settings", "activity"}
    if tab not in valid_tabs:
        tab = "overview"
    tasks = db.query(Task).filter(Task.project_id == p.id).order_by(Task.sequence, Task.created_at).all()
    milestones = db.query(Milestone).filter(Milestone.project_id == p.id).order_by(Milestone.current_date).all()
    raid = db.query(RaidItem).filter(RaidItem.project_id == p.id).order_by(RaidItem.exposure.desc()).all()
    dependencies = db.query(Dependency).filter(Dependency.source_project_id == p.id).order_by(Dependency.due_date).all()
    decisions = db.query(Decision).filter(Decision.project_id == p.id).order_by(Decision.created_at.desc()).all()
    actions = db.query(Action).filter(Action.project_id == p.id).order_by(Action.due_date).all()
    financials = db.query(FinancialRecord).filter(FinancialRecord.project_id == p.id).all()
    benefits = db.query(Benefit).filter(Benefit.project_id == p.id).all()
    promotions = db.query(ProjectPromotionRequest).filter(ProjectPromotionRequest.project_id == p.id).order_by(ProjectPromotionRequest.created_at.desc()).all()
    status_reports = db.query(StatusReport).filter(StatusReport.project_id == p.id).order_by(StatusReport.period_end.desc(), StatusReport.version.desc()).all()
    users = {u.id: u for u in db.query(User).all()}
    orgs = {o.id: o for o in db.query(Organization).all()}
    missions = {m.id: m for m in db.query(Mission).all()}
    projects = {x.id: x for x in db.query(Project).all()}
    board_columns = get_board_columns(db, p.id)
    columns = [column.name for column in board_columns]
    tasks_by_col = {column: [item for item in tasks if item.board_column == column] for column in columns}
    # Surface legacy/archived column tasks instead of losing them from the board.
    orphaned = [item for item in tasks if item.board_column not in columns]
    if orphaned:
        columns.append("Unmapped")
        tasks_by_col["Unmapped"] = orphaned
    relationships = db.query(TaskRelationship).filter(or_(TaskRelationship.source_task_id.in_([t.id for t in tasks]), TaskRelationship.target_task_id.in_([t.id for t in tasks]))).all() if tasks else []
    path = critical_path(tasks, relationships)
    gantt = gantt_layout(tasks, p.start_date, p.current_end_date or p.baseline_end_date)
    wbs_map = wbs_numbers(tasks)
    audit = db.query(AuditEvent).filter(AuditEvent.entity_id.in_([p.id] + [t.id for t in tasks])).order_by(AuditEvent.created_at.desc()).limit(40).all()
    traceability = trace_for(db, "Project", "Execution", "WBS", "Task", "Milestone", "RAID", "Dependency", "Status report")
    comment_counts = dict(db.query(TaskComment.task_id, func.count(TaskComment.id)).filter(TaskComment.task_id.in_([t.id for t in tasks])).group_by(TaskComment.task_id).all()) if tasks else {}
    attachment_counts = dict(db.query(TaskAttachment.task_id, func.count(TaskAttachment.id)).filter(TaskAttachment.task_id.in_([t.id for t in tasks]), TaskAttachment.deleted_at.is_(None), TaskAttachment.is_current.is_(True)).group_by(TaskAttachment.task_id).all()) if tasks else {}
    if task and not any(t.id == task for t in tasks):
        task = ""
    return render(
        request, "project_detail.html", user, db,
        project=p, tasks=tasks, milestones=milestones, raid=raid, dependencies=dependencies,
        decisions=decisions, actions=actions, financials=financials, benefits=benefits,
        status_reports=status_reports, users_map=users, orgs_map=orgs, missions_map=missions,
        projects_map=projects, board_columns=board_columns, columns=columns, tasks_by_col=tasks_by_col,
        tab=tab, audit=audit, traceability=traceability, open_task_id=task,
        comment_counts=comment_counts, attachment_counts=attachment_counts,
        critical_path=path, gantt=gantt, wbs_map=wbs_map,
        promotions=promotions,
    )


@app.post("/projects/{project_id}/status")
def project_status(project_id: str, request: Request, csrf: str = Form(...), health_owner: str = Form(...), percent_complete: int = Form(...), current_end_date: str = Form(""), status_summary: str = Form(""), health_override: str = Form(""), health_override_reason: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"PROJECT_MANAGER","PMO","DIVISION_PORTFOLIO_MANAGER","ADMIN"); p=get_accessible_project(db,user,project_id)
    if health_override and not has_role(user,"PMO","DIVISION_PORTFOLIO_MANAGER","ADMIN"): raise HTTPException(403,"Only an authorized portfolio role may override calculated health")
    if health_override and not health_override_reason.strip(): return flash_redirect(f"/projects/{p.id}","Health override requires a rationale.","error")
    before=snapshot(p); p.health_owner=health_owner; p.percent_complete=max(0,min(100,percent_complete)); p.current_end_date=date.fromisoformat(current_end_date) if current_end_date else p.current_end_date; p.health_override=health_override or None; p.health_override_reason=health_override_reason; p.last_status_date=datetime.now(timezone.utc); p.version+=1
    # Simple transparent health calculation
    overdue_critical=db.query(Milestone).filter(Milestone.project_id==p.id,Milestone.critical.is_(True),Milestone.current_date<date.today(),Milestone.status!="Completed").count(); high_raid=db.query(RaidItem).filter(RaidItem.project_id==p.id,RaidItem.status!="Closed",RaidItem.severity.in_(["High","Critical"])).count()
    p.health_calculated="Off Track" if overdue_critical>=2 else "At Risk" if overdue_critical or high_raid>=2 else "On Track"
    record_audit(db,user.id,"Project",p.id,"STATUS_UPDATE",before=before,after={**snapshot(p),"status_summary":status_summary}); db.commit()
    return flash_redirect(f"/projects/{p.id}","Project status updated; enterprise and division roll-ups now reflect the change.")


@app.get("/projects/{project_id}/status-reports/new", response_class=HTMLResponse)
def status_report_new(project_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "PROJECT_MANAGER", "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    return render(request, "project_record_form.html", user, db, project=project, record_type="status-report",
                  breadcrumbs=[("Projects", "/projects"), (project.human_id, f"/projects/{project.id}"), ("Status Reports", f"/projects/{project.id}?tab=status"), ("New Report", "")])


@app.post("/projects/{project_id}/status-reports")
def status_report_create(
    project_id: str,
    request: Request,
    csrf: str = Form(...),
    period_start: str = Form(""),
    period_end: str = Form(""),
    health: str = Form("On Track"),
    percent_complete: int = Form(0),
    accomplishments: str = Form(""),
    planned_work: str = Form(""),
    decisions_required: str = Form(""),
    risks_and_dependencies: str = Form(""),
    summary: str = Form(""),
    action: str = Form("submit"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    end_date = parse_optional_date(period_end) or date.today()
    start_date = parse_optional_date(period_start) or (end_date - timedelta(days=13))
    if start_date > end_date:
        return flash_redirect(f"/projects/{project.id}?tab=status", "Reporting period start cannot be after period end.", "error")
    if health not in {"On Track", "At Risk", "Off Track", "Blocked", "Completed", "On Hold", "Not Reported"}:
        return flash_redirect(f"/projects/{project.id}?tab=status", "Invalid project health.", "error")
    latest_version = db.query(func.max(StatusReport.version)).filter(StatusReport.project_id == project.id, StatusReport.period_end == end_date).scalar() or 0
    status = "Draft" if action == "draft" else "Submitted"
    report = StatusReport(
        human_id=next_human_id(db, StatusReport, "SR"),
        project_id=project.id,
        period_start=start_date,
        period_end=end_date,
        version=latest_version + 1,
        status=status,
        health=health,
        percent_complete=max(0, min(100, percent_complete)),
        accomplishments=accomplishments.strip(),
        planned_work=planned_work.strip(),
        decisions_required=decisions_required.strip(),
        risks_and_dependencies=risks_and_dependencies.strip(),
        summary=summary.strip() or f"{project.human_id} is {health.lower()} at {max(0, min(100, percent_complete))}% complete for the period ending {end_date.isoformat()}.",
        submitted_by_id=user.id if status == "Submitted" else None,
        submitted_at=datetime.now(timezone.utc) if status == "Submitted" else None,
    )
    db.add(report)
    db.flush()
    if status == "Submitted":
        before = snapshot(project)
        project.health_owner = health
        project.percent_complete = report.percent_complete
        project.last_status_date = datetime.now(timezone.utc)
        project.version += 1
        record_audit(db, user.id, "Project", project.id, "STATUS_REPORT_SUBMITTED", before=before, after={**snapshot(project), "status_report_id": report.id}, ip_address=getattr(request.state, "client_ip", ""))
        reviewers = db.query(User).all()
        for reviewer in reviewers:
            if reviewer.id != user.id and has_role(reviewer, "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN") and (is_enterprise_user(reviewer) or reviewer.division_id == project.lead_org_id):
                db.add(Notification(user_id=reviewer.id, title=f"Status report submitted: {project.human_id}", message=f"{report.human_id} is ready for review and approval.", link=f"/projects/{project.id}?tab=status", notification_type="Approval"))
    else:
        record_audit(db, user.id, "StatusReport", report.id, "DRAFT_CREATED", after=snapshot(report), ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(f"/projects/{project.id}?tab=status", f"Status report {report.human_id} {status.lower()}.")


@app.post("/projects/{project_id}/status-reports/{report_id}/update")
def status_report_update(
    project_id: str,
    report_id: str,
    request: Request,
    csrf: str = Form(...),
    health: str = Form("On Track"),
    percent_complete: int = Form(0),
    accomplishments: str = Form(""),
    planned_work: str = Form(""),
    decisions_required: str = Form(""),
    risks_and_dependencies: str = Form(""),
    summary: str = Form(""),
    action: str = Form("draft"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    report = db.get(StatusReport, report_id)
    if not report or report.project_id != project.id:
        raise HTTPException(404, "Status report not found")
    if report.status not in {"Draft", "Returned"}:
        return flash_redirect(f"/status-reports/{report.id}", "Only draft or returned reports can be edited.", "error")
    if health not in {"On Track", "At Risk", "Off Track", "Blocked", "Completed", "On Hold", "Not Reported"}:
        return flash_redirect(f"/status-reports/{report.id}", "Invalid project health.", "error")
    before = snapshot(report)
    report.health = health
    report.percent_complete = max(0, min(100, percent_complete))
    report.accomplishments = accomplishments.strip()
    report.planned_work = planned_work.strip()
    report.decisions_required = decisions_required.strip()
    report.risks_and_dependencies = risks_and_dependencies.strip()
    report.summary = summary.strip() or f"{project.human_id} is {health.lower()} at {report.percent_complete}% complete for the period ending {report.period_end.isoformat()}."
    if action == "submit":
        report.status = "Submitted"
        report.submitted_by_id = user.id
        report.submitted_at = datetime.now(timezone.utc)
        reviewers = db.query(User).all()
        for reviewer in reviewers:
            if reviewer.id != user.id and has_role(reviewer, "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN") and (is_enterprise_user(reviewer) or reviewer.division_id == project.lead_org_id):
                db.add(Notification(user_id=reviewer.id, title=f"Status report resubmitted: {project.human_id}", message=f"{report.human_id} is ready for review.", link=f"/status-reports/{report.id}", notification_type="Approval"))
        audit_action = "RESUBMITTED"
    else:
        report.status = "Draft"
        audit_action = "DRAFT_UPDATED"
    record_audit(db, user.id, "StatusReport", report.id, audit_action, before=before, after=snapshot(report), ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(f"/status-reports/{report.id}", f"{report.human_id} {'submitted' if action == 'submit' else 'saved as a draft'}.")


@app.post("/projects/{project_id}/status-reports/{report_id}/approve")
def status_report_approve(project_id: str, report_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PMO", "DIVISION_PORTFOLIO_MANAGER", "SENIOR_LEADER", "ENTERPRISE_PORTFOLIO_OWNER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    report = db.get(StatusReport, report_id)
    if not report or report.project_id != project.id:
        raise HTTPException(404, "Status report not found")
    if report.status != "Submitted":
        return flash_redirect(f"/projects/{project.id}?tab=status", "Only a submitted report can be approved.", "error")
    before = snapshot(report)
    report.status = "Approved"
    report.approved_by_id = user.id
    report.approved_at = datetime.now(timezone.utc)
    project.health_owner = report.health
    project.percent_complete = report.percent_complete
    project.last_status_date = report.approved_at
    project.version += 1
    record_audit(db, user.id, "StatusReport", report.id, "APPROVED", before=before, after=snapshot(report), ip_address=getattr(request.state, "client_ip", ""))
    db.add(Notification(user_id=report.submitted_by_id or project.manager_id, title=f"Status report approved: {project.human_id}", message=f"{report.human_id} is now the approved reporting baseline.", link=f"/projects/{project.id}?tab=status", notification_type="Approval"))
    db.commit()
    return flash_redirect(f"/projects/{project.id}?tab=status", f"{report.human_id} approved and rolled up to executive views.")


@app.post("/projects/{project_id}/status-reports/{report_id}/return")
def status_report_return(project_id: str, report_id: str, request: Request, csrf: str = Form(...), reason: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    report = db.get(StatusReport, report_id)
    if not report or report.project_id != project.id:
        raise HTTPException(404, "Status report not found")
    if report.status != "Submitted":
        return flash_redirect(f"/projects/{project.id}?tab=status", "Only a submitted report can be returned.", "error")
    before = snapshot(report)
    report.status = "Returned"
    report.summary = (report.summary + "\n\nReturned for revision: " + reason.strip()).strip()
    record_audit(db, user.id, "StatusReport", report.id, "RETURNED", before=before, after=snapshot(report), ip_address=getattr(request.state, "client_ip", ""))
    db.add(Notification(user_id=report.submitted_by_id or project.manager_id, title=f"Status report returned: {project.human_id}", message=reason.strip()[:300], link=f"/projects/{project.id}?tab=status", notification_type="Approval"))
    db.commit()
    return flash_redirect(f"/projects/{project.id}?tab=status", f"{report.human_id} returned for revision.")


@app.get("/status-reports/{report_id}", response_class=HTMLResponse)
def status_report_detail(report_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    report = db.get(StatusReport, report_id)
    if not report:
        raise HTTPException(404, "Status report not found")
    project = get_accessible_project(db, user, report.project_id)
    users = {item.id: item for item in db.query(User).all()}
    editable = report.status in {"Draft", "Returned"} and has_role(user, "PROJECT_MANAGER", "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN") and can_edit_business_data(user)
    return render(request, "status_report_detail.html", user, db, report=report, project=project, users_map=users, editable=editable, audit=record_audit_events(db, report.id), traceability=trace_for(db, "Status report", "Project status", "Executive brief"))


@app.post("/projects/{project_id}/board-columns")
def board_column_create(project_id: str, request: Request, csrf: str = Form(...), name: str = Form(...), wip_limit: int = Form(0), entry_criteria: str = Form(""), exit_criteria: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    clean_name = name.strip()[:80]
    if not clean_name:
        return flash_redirect(f"/projects/{project.id}?tab=board-settings", "Column name is required.", "error")
    if db.query(BoardColumn).filter(func.lower(BoardColumn.name) == clean_name.lower(), BoardColumn.project_id == project.id).first():
        return flash_redirect(f"/projects/{project.id}?tab=board-settings", "A board column with that name already exists.", "error")
    position = (db.query(func.max(BoardColumn.position)).filter(BoardColumn.project_id == project.id).scalar() or -1) + 1
    column = BoardColumn(project_id=project.id, name=clean_name, position=position, wip_limit=max(0, wip_limit), entry_criteria=entry_criteria.strip(), exit_criteria=exit_criteria.strip())
    db.add(column)
    db.flush()
    record_audit(db, user.id, "BoardColumn", column.id, "CREATE", after=snapshot(column), ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(f"/projects/{project.id}?tab=board-settings", f"Board column {clean_name} created.")


@app.post("/projects/{project_id}/board-columns/{column_id}/update")
def board_column_update(project_id: str, column_id: str, request: Request, csrf: str = Form(...), name: str = Form(...), wip_limit: int = Form(0), entry_criteria: str = Form(""), exit_criteria: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    column = db.get(BoardColumn, column_id)
    if not column or column.project_id != project.id:
        raise HTTPException(404, "Board column not found")
    clean_name = name.strip()[:80]
    duplicate = db.query(BoardColumn).filter(BoardColumn.project_id == project.id, func.lower(BoardColumn.name) == clean_name.lower(), BoardColumn.id != column.id).first()
    if not clean_name or duplicate:
        return flash_redirect(f"/projects/{project.id}?tab=board-settings", "Column name is blank or already in use.", "error")
    current_count = db.query(Task).filter(Task.project_id == project.id, Task.board_column == column.name).count()
    if wip_limit > 0 and current_count > wip_limit:
        return flash_redirect(f"/projects/{project.id}?tab=board-settings", f"WIP limit cannot be lower than the {current_count} tasks currently in this column.", "error")
    before = snapshot(column)
    old_name = column.name
    column.name = clean_name
    column.wip_limit = max(0, wip_limit)
    column.entry_criteria = entry_criteria.strip()
    column.exit_criteria = exit_criteria.strip()
    if old_name != clean_name:
        db.query(Task).filter(Task.project_id == project.id, Task.board_column == old_name).update({Task.board_column: clean_name}, synchronize_session=False)
    record_audit(db, user.id, "BoardColumn", column.id, "UPDATE", before=before, after=snapshot(column), ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(f"/projects/{project.id}?tab=board-settings", f"Board column {clean_name} updated.")


@app.post("/projects/{project_id}/board-columns/{column_id}/move")
def board_column_move(project_id: str, column_id: str, request: Request, csrf: str = Form(...), direction: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    columns = get_board_columns(db, project.id, include_archived=True)
    column = next((item for item in columns if item.id == column_id), None)
    if not column:
        raise HTTPException(404, "Board column not found")
    index = columns.index(column)
    target_index = index - 1 if direction == "up" else index + 1 if direction == "down" else index
    if target_index < 0 or target_index >= len(columns) or target_index == index:
        return flash_redirect(f"/projects/{project.id}?tab=board-settings", "Column is already at that edge.", "error")
    target = columns[target_index]
    column.position, target.position = target.position, column.position
    record_audit(db, user.id, "BoardColumn", column.id, "REORDER", after={"direction": direction, "position": column.position}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(f"/projects/{project.id}?tab=board-settings", "Board order updated.")


@app.post("/projects/{project_id}/board-columns/{column_id}/archive")
def board_column_archive(project_id: str, column_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    column = db.get(BoardColumn, column_id)
    if not column or column.project_id != project.id:
        raise HTTPException(404, "Board column not found")
    if db.query(Task).filter(Task.project_id == project.id, Task.board_column == column.name).count() > 0:
        return flash_redirect(f"/projects/{project.id}?tab=board-settings", "Move all tasks out of the column before archiving it.", "error")
    active_count = db.query(BoardColumn).filter(BoardColumn.project_id == project.id, BoardColumn.archived.is_(False)).count()
    if active_count <= 2:
        return flash_redirect(f"/projects/{project.id}?tab=board-settings", "A project board must retain at least two active columns.", "error")
    column.archived = True
    record_audit(db, user.id, "BoardColumn", column.id, "ARCHIVE", before={"name": column.name}, after={"archived": True}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(f"/projects/{project.id}?tab=board-settings", f"{column.name} archived.")


@app.get("/projects/{project_id}/tasks/new", response_class=HTMLResponse)
def task_new(project_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    tasks = db.query(Task).filter(Task.project_id == project.id).order_by(Task.sequence, Task.created_at).all()
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    return render(request, "project_record_form.html", user, db, project=project, record_type="task", tasks=tasks,
                  users=users, board_columns=board_column_names(db, project.id),
                  breadcrumbs=[("Projects", "/projects"), (project.human_id, f"/projects/{project.id}"), ("Board", f"/projects/{project.id}?tab=board"), ("New Task", "")])


@app.post("/projects/{project_id}/tasks")
def task_create(
    project_id: str,
    request: Request,
    csrf: str = Form(...),
    title: str = Form(...),
    task_type: str = Form("Task"),
    description: str = Form(""),
    priority: str = Form("Medium"),
    owner_id: str = Form(""),
    parent_id: str = Form(""),
    start_date: str = Form(""),
    due_date: str = Form(""),
    estimated_effort: float = Form(0),
    board_column: str = Form("Backlog"),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "ADMIN")
    p = get_accessible_project(db, user, project_id)
    valid_columns = set(board_column_names(db, p.id))
    if board_column not in valid_columns:
        return flash_redirect(f"/projects/{p.id}?tab=board", "Invalid or archived board column.", "error")
    capacity_ok, capacity_message = wip_capacity_available(db, p.id, board_column)
    if not capacity_ok:
        return flash_redirect(f"/projects/{p.id}?tab=board", capacity_message, "error")
    if priority not in {"Low", "Medium", "High", "Critical"}:
        priority = "Medium"
    if task_type not in {"Task", "Summary", "Milestone", "Deliverable", "Approval", "Recurring"}:
        task_type = "Task"
    start_value = parse_optional_date(start_date)
    due_value = parse_optional_date(due_date)
    if start_value and due_value and start_value > due_value:
        return flash_redirect(f"/projects/{p.id}?tab=board", "Task start date cannot be after its due date.", "error")
    if task_type == "Milestone" and start_value and due_value and start_value != due_value:
        return flash_redirect(f"/projects/{p.id}?tab=board", "Milestones must have the same start and due date.", "error")
    parent = db.get(Task, parent_id) if parent_id else None
    if parent and parent.project_id != p.id:
        parent = None
    t = Task(
        human_id=next_human_id(db, Task, "TSK"),
        project_id=p.id,
        parent_id=parent.id if parent else None,
        indent_level=min(8, (parent.indent_level + 1) if parent else 0),
        title=title.strip(),
        task_type=task_type,
        description=description.strip(),
        priority=priority,
        owner_id=owner_id or None,
        start_date=start_value,
        due_date=due_value,
        estimated_effort=0 if task_type == "Milestone" else max(0, estimated_effort),
        board_column=board_column,
        status="Completed" if board_column == "Done" else "In Progress" if board_column in {"In Progress", "Review"} else "Not Started",
        notes=notes.strip(),
        sequence=db.query(Task).filter(Task.project_id == p.id).count() + 1,
    )
    db.add(t)
    db.flush()
    if t.notes:
        db.add(TaskNoteRevision(task_id=t.id, author_id=user.id, revision=1, body=t.notes, change_summary="Initial task notes"))
    record_audit(db, user.id, "Task", t.id, "CREATE", after=snapshot(t), ip_address=getattr(request.state, "client_ip", ""))
    if t.owner_id and t.owner_id != user.id:
        db.add(Notification(user_id=t.owner_id, title=f"Task assigned: {t.human_id}", message=f"You were assigned to {t.title} in {p.human_id}.", link=task_return_path(p.id, t.id), notification_type="Assignment"))
    db.commit()
    return flash_redirect(task_return_path(p.id, t.id), f"Task {t.human_id} created.")


@app.get("/projects/{project_id}/tasks/{task_id}/panel", response_class=HTMLResponse)
def task_panel(project_id: str, task_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    task, project = get_accessible_task(db, user, task_id)
    if project.id != project_id:
        raise HTTPException(404, "Task not found")
    context = task_workspace_context(db, user, task, project)
    context.update({"request": request, "user": user, "csrf_token": csrf_token(user.id), "task_full_page": False})
    return templates.TemplateResponse("_task_drawer.html", context)


@app.get("/projects/{project_id}/tasks/{task_id}", response_class=HTMLResponse)
def task_detail_page(project_id: str, task_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Reliable non-JavaScript fallback and shareable authoritative task workspace."""
    task, project = get_accessible_task(db, user, task_id)
    if project.id != project_id:
        raise HTTPException(404, "Task not found")
    context = task_workspace_context(db, user, task, project)
    context["task_full_page"] = True
    return render(request, "task_detail.html", user, db, **context)


@app.post("/projects/{project_id}/tasks/{task_id}/update")
def task_update(
    project_id: str,
    task_id: str,
    request: Request,
    csrf: str = Form(...),
    title: str = Form(...),
    task_type: str = Form("Task"),
    description: str = Form(""),
    priority: str = Form("Medium"),
    status: str = Form("Not Started"),
    board_column: str = Form("Backlog"),
    owner_id: str = Form(""),
    contributor_ids: list[str] = Form(default=[]),
    watcher_ids: list[str] = Form(default=[]),
    start_date: str = Form(""),
    due_date: str = Form(""),
    actual_start_date: str = Form(""),
    actual_finish_date: str = Form(""),
    baseline_due_date: str = Form(""),
    estimated_effort: float = Form(0),
    actual_effort: float = Form(0),
    percent_complete: int = Form(0),
    tags: str = Form(""),
    custom_fields: str = Form(""),
    notes: str = Form(""),
    notes_change_summary: str = Form("Updated working notes"),
    acceptance_evidence: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "ADMIN")
    task, project = get_accessible_task(db, user, task_id)
    if project.id != project_id:
        raise HTTPException(404, "Task not found")
    valid_columns = set(board_column_names(db, project.id))
    valid_statuses = {"Not Started", "In Progress", "Blocked", "Completed", "On Hold"}
    valid_priorities = {"Low", "Medium", "High", "Critical"}
    valid_task_types = {"Task", "Summary", "Milestone", "Deliverable", "Approval", "Recurring"}
    if board_column not in valid_columns or status not in valid_statuses:
        return flash_redirect(task_return_path(project.id, task.id), "Invalid task status or board column.", "error")
    if board_column != task.board_column:
        capacity_ok, capacity_message = wip_capacity_available(db, project.id, board_column, task.id)
        if not capacity_ok:
            return flash_redirect(task_return_path(project.id, task.id), capacity_message, "error")
    start_value = parse_optional_date(start_date)
    due_value = parse_optional_date(due_date)
    actual_start_value = parse_optional_date(actual_start_date)
    actual_finish_value = parse_optional_date(actual_finish_date)
    if start_value and due_value and start_value > due_value:
        return flash_redirect(task_return_path(project.id, task.id), "Task start date cannot be after its due date.", "error")
    selected_type = task_type if task_type in valid_task_types else "Task"
    if selected_type == "Milestone" and start_value and due_value and start_value != due_value:
        return flash_redirect(task_return_path(project.id, task.id), "Milestones must have the same start and due date.", "error")
    if actual_start_value and actual_finish_value and actual_start_value > actual_finish_value:
        return flash_redirect(task_return_path(project.id, task.id), "Actual start cannot be after actual finish.", "error")
    custom_payload: dict[str, Any] = {}
    if custom_fields.strip():
        try:
            parsed = json.loads(custom_fields)
            if not isinstance(parsed, dict):
                raise ValueError
            custom_payload = {str(k)[:80]: str(v)[:500] for k, v in parsed.items()}
        except (json.JSONDecodeError, ValueError):
            return flash_redirect(task_return_path(project.id, task.id), "Custom fields must be a JSON object.", "error")
    before = snapshot(task)
    old_owner = task.owner_id
    old_notes = task.notes or ""
    task.title = title.strip()
    task.task_type = selected_type
    task.description = description.strip()
    task.priority = priority if priority in valid_priorities else "Medium"
    task.status = status
    task.board_column = board_column
    task.owner_id = owner_id or None
    task.contributor_ids = list(dict.fromkeys([x for x in contributor_ids if db.get(User, x)]))
    task.watcher_ids = list(dict.fromkeys([x for x in watcher_ids if db.get(User, x)]))
    task.custom_fields = custom_payload
    task.start_date = start_value
    task.due_date = due_value
    task.actual_start_date = actual_start_value
    task.actual_finish_date = actual_finish_value
    task.baseline_due_date = parse_optional_date(baseline_due_date)
    task.estimated_effort = 0 if task.task_type == "Milestone" else max(0, estimated_effort)
    task.actual_effort = max(0, actual_effort)
    task.percent_complete = max(0, min(100, percent_complete))
    if task.board_column == "Done" or task.status == "Completed":
        task.board_column = "Done" if "Done" in valid_columns else task.board_column
        task.status = "Completed"
        task.percent_complete = 100
        task.actual_finish_date = task.actual_finish_date or date.today()
    elif task.status == "In Progress":
        task.actual_start_date = task.actual_start_date or date.today()
    task.tags = list(dict.fromkeys([x.strip() for x in tags.split(",") if x.strip()]))[:20]
    task.notes = notes.strip()
    task.acceptance_evidence = acceptance_evidence.strip()
    if task.notes != old_notes:
        latest_revision = db.query(func.max(TaskNoteRevision.revision)).filter(TaskNoteRevision.task_id == task.id).scalar() or 0
        db.add(TaskNoteRevision(task_id=task.id, author_id=user.id, revision=latest_revision + 1, body=task.notes, change_summary=notes_change_summary.strip()[:300] or "Updated working notes"))
    record_audit(db, user.id, "Task", task.id, "UPDATE", before=before, after=snapshot(task), ip_address=getattr(request.state, "client_ip", ""))
    recipients = set(task.watcher_ids or []) | set(task.contributor_ids or [])
    if task.owner_id and task.owner_id != old_owner:
        recipients.add(task.owner_id)
    recipients.discard(user.id)
    for recipient_id in recipients:
        db.add(Notification(user_id=recipient_id, title=f"Task updated: {task.human_id}", message=f"{user.full_name} updated {task.title} in {project.human_id}.", link=task_return_path(project.id, task.id), notification_type="Task Update"))
    db.commit()
    return flash_redirect(task_return_path(project.id, task.id), f"{task.human_id} updated.")


@app.post("/projects/{project_id}/tasks/{task_id}/comments")
def task_comment_create(project_id: str, task_id: str, request: Request, csrf: str = Form(...), body: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN")
    task, project = get_accessible_task(db, user, task_id)
    if project.id != project_id:
        raise HTTPException(404, "Task not found")
    text = body.strip()
    if not text:
        return flash_redirect(task_return_path(project.id, task.id), "Comment cannot be empty.", "error")
    usernames = sorted(set(re.findall(r"@([A-Za-z0-9._-]+)", text)))
    mentioned_users = db.query(User).filter(User.username.in_(usernames)).all() if usernames else []
    comment = TaskComment(task_id=task.id, author_id=user.id, body=text, mentions=[u.id for u in mentioned_users])
    db.add(comment)
    db.flush()
    record_audit(db, user.id, "Task", task.id, "COMMENT_ADDED", after={"comment_id": comment.id, "body": text[:500]})
    recipients = {u.id for u in mentioned_users if u.id != user.id}
    if task.owner_id and task.owner_id != user.id:
        recipients.add(task.owner_id)
    for uid in recipients:
        db.add(Notification(user_id=uid, title=f"New comment on {task.human_id}", message=f"{user.full_name} commented on {task.title}.", link=task_return_path(project.id, task.id), notification_type="Mention"))
    db.commit()
    return flash_redirect(task_return_path(project.id, task.id), "Comment added.")


@app.post("/projects/{project_id}/tasks/{task_id}/checklist")
def task_checklist_add(project_id: str, task_id: str, request: Request, csrf: str = Form(...), text: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "ADMIN")
    task, project = get_accessible_task(db, user, task_id)
    if project.id != project_id:
        raise HTTPException(404, "Task not found")
    item_text = text.strip()
    if not item_text:
        return flash_redirect(task_return_path(project.id, task.id), "Checklist item cannot be empty.", "error")
    before = snapshot(task)
    items = list(task.checklist or [])
    items.append({"id": os.urandom(8).hex(), "text": item_text, "done": False})
    task.checklist = items
    record_audit(db, user.id, "Task", task.id, "CHECKLIST_ITEM_ADDED", before=before, after=snapshot(task))
    db.commit()
    return flash_redirect(task_return_path(project.id, task.id), "Checklist item added.")


@app.post("/projects/{project_id}/tasks/{task_id}/checklist/{item_id}/toggle")
def task_checklist_toggle(project_id: str, task_id: str, item_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "ADMIN")
    task, project = get_accessible_task(db, user, task_id)
    if project.id != project_id:
        raise HTTPException(404, "Task not found")
    before = snapshot(task)
    found = False
    items = []
    for raw in task.checklist or []:
        item = dict(raw)
        if str(item.get("id")) == item_id:
            item["done"] = not bool(item.get("done"))
            found = True
        items.append(item)
    if not found:
        raise HTTPException(404, "Checklist item not found")
    task.checklist = items
    record_audit(db, user.id, "Task", task.id, "CHECKLIST_ITEM_TOGGLED", before=before, after=snapshot(task))
    db.commit()
    return flash_redirect(task_return_path(project.id, task.id), "Checklist updated.")


@app.post("/projects/{project_id}/tasks/{task_id}/checklist/{item_id}/delete")
def task_checklist_delete(project_id: str, task_id: str, item_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "ADMIN")
    task, project = get_accessible_task(db, user, task_id)
    if project.id != project_id:
        raise HTTPException(404, "Task not found")
    before = snapshot(task)
    items = [dict(x) for x in (task.checklist or []) if str(x.get("id")) != item_id]
    if len(items) == len(task.checklist or []):
        raise HTTPException(404, "Checklist item not found")
    task.checklist = items
    record_audit(db, user.id, "Task", task.id, "CHECKLIST_ITEM_DELETED", before=before, after=snapshot(task))
    db.commit()
    return flash_redirect(task_return_path(project.id, task.id), "Checklist item removed.")


@app.post("/projects/{project_id}/tasks/{task_id}/attachments")
def task_attachment_upload(
    project_id: str,
    task_id: str,
    request: Request,
    csrf: str = Form(...),
    description: str = Form(""),
    sensitivity: str = Form("Controlled Unclassified"),
    category: str = Form("Supporting Document"),
    replace_attachment_id: str = Form(""),
    attachment: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "ADMIN")
    task, project = get_accessible_task(db, user, task_id)
    if project.id != project_id:
        raise HTTPException(404, "Task not found")
    if not attachment.filename:
        return flash_redirect(task_return_path(project.id, task.id), "Choose a file to upload.", "error")
    previous = db.get(TaskAttachment, replace_attachment_id) if replace_attachment_id else None
    if previous and (previous.task_id != task.id or previous.deleted_at is not None):
        return flash_redirect(task_return_path(project.id, task.id), "The file selected for replacement is unavailable.", "error")
    try:
        attachment.file.seek(0, 2)
        size = attachment.file.tell()
        attachment.file.seek(0)
        validate_file_signature(attachment.file, attachment.filename)
        stored = LocalVolumeStorage().save(attachment.file, attachment.filename, attachment.content_type or "application/octet-stream", size)
    except ValueError as exc:
        return flash_redirect(task_return_path(project.id, task.id), str(exc), "error")
    logical_file_id = previous.logical_file_id if previous else os.urandom(18).hex()
    version_number = 1
    if previous:
        versions = db.query(TaskAttachment).filter(TaskAttachment.logical_file_id == logical_file_id).all()
        version_number = max((item.version_number for item in versions), default=0) + 1
        for item in versions:
            item.is_current = False
    record = TaskAttachment(
        task_id=task.id,
        uploaded_by_id=user.id,
        original_name=stored.original_name,
        storage_key=stored.storage_key,
        media_type=stored.media_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        description=description.strip(),
        sensitivity=sensitivity,
        category=category.strip()[:60] or "Supporting Document",
        logical_file_id=logical_file_id,
        version_number=version_number,
        is_current=True,
    )
    db.add(record)
    db.flush()
    action = "ATTACHMENT_VERSION_ADDED" if previous else "ATTACHMENT_ADDED"
    record_audit(db, user.id, "Task", task.id, action, after={"attachment_id": record.id, "logical_file_id": logical_file_id, "version": version_number, "filename": record.original_name, "sha256": record.sha256, "size_bytes": record.size_bytes}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    verb = f"Uploaded version {version_number} of" if previous else "Uploaded"
    return flash_redirect(task_return_path(project.id, task.id), f"{verb} {record.original_name}.")


def _accessible_attachment(db: Session, user: User, project_id: str, task_id: str, attachment_id: str, include_deleted: bool = False) -> tuple[Task, Project, TaskAttachment]:
    task, project = get_accessible_task(db, user, task_id)
    if project.id != project_id:
        raise HTTPException(404, "Task not found")
    attachment = db.get(TaskAttachment, attachment_id)
    if not attachment or attachment.task_id != task.id or (attachment.deleted_at is not None and not include_deleted):
        raise HTTPException(404, "Attachment not found")
    if attachment.sensitivity == "Restricted" and not can_access_sensitive(user, "Restricted"):
        raise HTTPException(404, "Attachment not found")
    return task, project, attachment


@app.get("/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}")
def task_attachment_download(project_id: str, task_id: str, attachment_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    task, project, attachment = _accessible_attachment(db, user, project_id, task_id, attachment_id)
    try:
        stream = LocalVolumeStorage().open(attachment.storage_key)
    except FileNotFoundError:
        raise HTTPException(410, "Attachment metadata exists but the stored file is unavailable")
    attachment.download_count += 1
    record_audit(db, user.id, "Task", task.id, "ATTACHMENT_DOWNLOADED", after={"attachment_id": attachment.id, "filename": attachment.original_name, "version": attachment.version_number}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote_plus(attachment.original_name)}", "X-Content-Type-Options": "nosniff"}
    return StreamingResponse(stream, media_type=attachment.media_type or "application/octet-stream", headers=headers)


@app.get("/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}/preview")
def task_attachment_preview(project_id: str, task_id: str, attachment_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    task, project, attachment = _accessible_attachment(db, user, project_id, task_id, attachment_id)
    extension = Path(attachment.original_name).suffix.lower()
    previewable = {".pdf", ".png", ".jpg", ".jpeg", ".md", ".txt", ".csv", ".json"}
    if extension not in previewable:
        return flash_redirect(task_return_path(project.id, task.id), "This file type downloads securely but does not support browser preview.", "error")
    try:
        stream = LocalVolumeStorage().open(attachment.storage_key)
    except FileNotFoundError:
        raise HTTPException(410, "Attachment metadata exists but the stored file is unavailable")
    media_type = attachment.media_type
    if extension in {".md", ".txt", ".csv", ".json"}:
        media_type = "text/plain; charset=utf-8"
    headers = {"Content-Disposition": f"inline; filename*=UTF-8''{quote_plus(attachment.original_name)}", "X-Content-Type-Options": "nosniff"}
    record_audit(db, user.id, "Task", task.id, "ATTACHMENT_PREVIEWED", after={"attachment_id": attachment.id, "filename": attachment.original_name, "version": attachment.version_number}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return StreamingResponse(stream, media_type=media_type or "application/octet-stream", headers=headers)


@app.post("/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}/delete")
def task_attachment_delete(project_id: str, task_id: str, attachment_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    task, project, attachment = _accessible_attachment(db, user, project_id, task_id, attachment_id)
    if attachment.uploaded_by_id != user.id and not has_role(user, "PROJECT_MANAGER", "ADMIN"):
        raise HTTPException(403, "Only the uploader, project manager, or administrator may remove this file")
    attachment.deleted_at = datetime.now(timezone.utc)
    attachment.deleted_by_id = user.id
    attachment.is_current = False
    record_audit(db, user.id, "Task", task.id, "ATTACHMENT_SOFT_DELETED", before={"attachment_id": attachment.id, "filename": attachment.original_name, "sha256": attachment.sha256, "version": attachment.version_number}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(task_return_path(project.id, task.id), "Attachment moved to task file history and can be restored.")


@app.post("/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}/restore")
def task_attachment_restore(project_id: str, task_id: str, attachment_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "ADMIN")
    task, project, attachment = _accessible_attachment(db, user, project_id, task_id, attachment_id, include_deleted=True)
    if attachment.deleted_at is None:
        return flash_redirect(task_return_path(project.id, task.id), "Attachment is already active.")
    current = db.query(TaskAttachment).filter(TaskAttachment.logical_file_id == attachment.logical_file_id, TaskAttachment.is_current.is_(True), TaskAttachment.deleted_at.is_(None)).first()
    if current:
        current.is_current = False
    attachment.deleted_at = None
    attachment.deleted_by_id = None
    attachment.is_current = True
    record_audit(db, user.id, "Task", task.id, "ATTACHMENT_RESTORED", after={"attachment_id": attachment.id, "filename": attachment.original_name, "version": attachment.version_number}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit()
    return flash_redirect(task_return_path(project.id, task.id), "Attachment restored as the current version.")


@app.post("/projects/{project_id}/tasks/{task_id}/relationships")
def task_relationship_add(project_id: str, task_id: str, request: Request, csrf: str = Form(...), target_task_id: str = Form(...), relationship_type: str = Form("Finish-to-start"), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "ADMIN")
    task, project = get_accessible_task(db, user, task_id)
    target, target_project = get_accessible_task(db, user, target_task_id)
    if project.id != project_id or target_project.id != project.id or target.id == task.id:
        return flash_redirect(task_return_path(project.id, task.id), "Task dependency must reference another task in this project.", "error")
    if relationship_type not in {"Finish-to-start", "Start-to-start", "Finish-to-finish", "Related"}:
        relationship_type = "Finish-to-start"
    exists = db.query(TaskRelationship).filter_by(source_task_id=task.id, target_task_id=target.id, relationship_type=relationship_type).first()
    if exists:
        return flash_redirect(task_return_path(project.id, task.id), "That task relationship already exists.", "error")
    project_tasks = db.query(Task).filter(Task.project_id == project.id).all()
    project_relationships = db.query(TaskRelationship).filter(
        or_(
            TaskRelationship.source_task_id.in_([item.id for item in project_tasks]),
            TaskRelationship.target_task_id.in_([item.id for item in project_tasks]),
        )
    ).all()
    if relationship_type == "Finish-to-start" and would_create_cycle(project_tasks, project_relationships, task.id, target.id):
        return flash_redirect(task_return_path(project.id, task.id), "This dependency would create a circular schedule chain.", "error")
    rel = TaskRelationship(source_task_id=task.id, target_task_id=target.id, relationship_type=relationship_type, created_by_id=user.id)
    db.add(rel)
    db.flush()
    record_audit(db, user.id, "Task", task.id, "RELATIONSHIP_ADDED", after={"relationship_id": rel.id, "target_task_id": target.id, "type": relationship_type})
    db.commit()
    return flash_redirect(task_return_path(project.id, task.id), "Task dependency added.")


@app.post("/projects/{project_id}/tasks/{task_id}/relationships/{relationship_id}/delete")
def task_relationship_delete(project_id: str, task_id: str, relationship_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "ADMIN")
    task, project = get_accessible_task(db, user, task_id)
    rel = db.get(TaskRelationship, relationship_id)
    if project.id != project_id or not rel or rel.source_task_id != task.id:
        raise HTTPException(404, "Task relationship not found")
    record_audit(db, user.id, "Task", task.id, "RELATIONSHIP_DELETED", before={"relationship_id": rel.id, "target_task_id": rel.target_task_id, "type": rel.relationship_type})
    db.delete(rel)
    db.commit()
    return flash_redirect(task_return_path(project.id, task.id), "Task dependency removed.")


@app.post("/projects/{project_id}/tasks/{task_id}/wbs-action")
def task_wbs_action(project_id: str, task_id: str, request: Request, csrf: str = Form(...), action: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    require_roles(user, "PROJECT_MANAGER", "ADMIN")
    task, project = get_accessible_task(db, user, task_id)
    if project.id != project_id:
        raise HTTPException(404, "Task not found")
    tasks = db.query(Task).filter(Task.project_id == project.id).order_by(Task.sequence, Task.created_at).all()
    index = next((i for i, item in enumerate(tasks) if item.id == task.id), -1)
    before = snapshot(task)
    if action == "move-up" and index > 0:
        previous = tasks[index - 1]
        task.sequence, previous.sequence = previous.sequence, task.sequence
    elif action == "move-down" and 0 <= index < len(tasks) - 1:
        following = tasks[index + 1]
        task.sequence, following.sequence = following.sequence, task.sequence
    elif action == "indent" and index > 0:
        task.indent_level = min(5, tasks[index - 1].indent_level + 1)
        task.parent_id = tasks[index - 1].id
    elif action == "outdent":
        task.indent_level = max(0, task.indent_level - 1)
        if task.indent_level == 0:
            task.parent_id = None
    elif action == "baseline":
        task.baseline_due_date = task.due_date
    else:
        return flash_redirect(task_return_path(project.id, task.id, "wbs"), "That WBS action is not available for this task.", "error")
    record_audit(db, user.id, "Task", task.id, f"WBS_{action.upper().replace('-', '_')}", before=before, after=snapshot(task))
    db.commit()
    return flash_redirect(task_return_path(project.id, task.id, "wbs"), "WBS updated.")


@app.post("/api/tasks/{task_id}/move")
def task_move(task_id: str, payload: dict, request: Request, x_csrf_token: str | None = Header(None), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,header_token=x_csrf_token); require_roles(user,"PROJECT_MANAGER","TEAM_MEMBER","ADMIN"); t=db.get(Task,task_id)
    if not t: raise HTTPException(404,"Task not found")
    p=get_accessible_project(db,user,t.project_id); column=str(payload.get("column", "")).strip()
    valid_columns = board_column_names(db, p.id)
    if column not in valid_columns:
        raise HTTPException(400,"Invalid or archived board column")
    capacity_ok, capacity_message = wip_capacity_available(db, p.id, column, t.id)
    if not capacity_ok:
        raise HTTPException(409, capacity_message)
    before=snapshot(t)
    t.board_column=column
    done_column = valid_columns[-1] if valid_columns else "Done"
    t.status="Completed" if column==done_column else "In Progress" if column not in {valid_columns[0], valid_columns[1] if len(valid_columns)>1 else valid_columns[0]} else "Not Started"
    if t.status == "Completed":
        t.percent_complete=100
        t.actual_finish_date=t.actual_finish_date or date.today()
    elif t.status == "In Progress":
        t.percent_complete=max(t.percent_complete, 50)
        t.actual_start_date=t.actual_start_date or date.today()
    else:
        t.percent_complete=min(t.percent_complete, 10)
    record_audit(db,user.id,"Task",t.id,"BOARD_MOVE",before=before,after=snapshot(t),ip_address=getattr(request.state,"client_ip",""))
    db.commit()
    return {"ok":True,"task":t.human_id,"column":column}


@app.get("/projects/{project_id}/milestones/new", response_class=HTMLResponse)
def milestone_new(project_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "PROJECT_MANAGER", "PMO", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    return render(request, "project_record_form.html", user, db, project=project, record_type="milestone", users=users,
                  breadcrumbs=[("Projects", "/projects"), (project.human_id, f"/projects/{project.id}"), ("Milestones", f"/projects/{project.id}?tab=milestones"), ("New Milestone", "")])


@app.post("/projects/{project_id}/milestones")
def milestone_create(project_id: str, request: Request, csrf: str = Form(...), title: str = Form(...), current_date: str = Form(...), confidence: str = Form("Medium"), critical: str = Form(""), owner_id: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"PROJECT_MANAGER","PMO","ADMIN"); p=get_accessible_project(db,user,project_id); due=date.fromisoformat(current_date); m=Milestone(human_id=next_human_id(db,Milestone,"MS"),project_id=p.id,title=title,baseline_date=due,current_date=due,confidence=confidence,critical=bool(critical),owner_id=owner_id or user.id); db.add(m); db.flush(); record_audit(db,user.id,"Milestone",m.id,"CREATE",after=snapshot(m)); db.commit(); return flash_redirect(f"/projects/{p.id}?tab=milestones",f"Milestone {m.human_id} created.")


@app.get("/projects/{project_id}/raid/new", response_class=HTMLResponse)
def raid_new(project_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "PROJECT_MANAGER", "TEAM_MEMBER", "PMO", "ADMIN")
    project = get_accessible_project(db, user, project_id)
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    return render(request, "project_record_form.html", user, db, project=project, record_type="raid", users=users,
                  breadcrumbs=[("Projects", "/projects"), (project.human_id, f"/projects/{project.id}"), ("RAID", f"/projects/{project.id}?tab=raid"), ("New RAID Record", "")])


@app.post("/projects/{project_id}/raid")
def raid_create(project_id: str, request: Request, csrf: str = Form(...), type: str = Form(...), title: str = Form(...), description: str = Form(""), severity: str = Form("Medium"), likelihood: str = Form("Possible"), mitigation: str = Form(""), due_date: str = Form(""), owner_id: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"PROJECT_MANAGER","TEAM_MEMBER","PMO","ADMIN"); p=get_accessible_project(db,user,project_id); exposure={"Low":1,"Medium":2,"High":3,"Critical":4}.get(severity,2)*{"Unlikely":1,"Possible":2,"Likely":3}.get(likelihood,2); r=RaidItem(human_id=next_human_id(db,RaidItem,"RAID"),project_id=p.id,type=type,title=title,description=description,severity=severity,likelihood=likelihood,exposure=exposure,mitigation=mitigation,due_date=date.fromisoformat(due_date) if due_date else None,owner_id=owner_id or user.id); db.add(r); db.flush(); record_audit(db,user.id,"RAID",r.id,"CREATE",after=snapshot(r)); db.commit(); return flash_redirect(f"/projects/{p.id}?tab=raid",f"{type} {r.human_id} created.")


@app.get("/risks", response_class=HTMLResponse)
def risks_page(request: Request, type: str = "", severity: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    query=db.query(RaidItem,Project).join(Project,RaidItem.project_id==Project.id)
    if not is_enterprise_user(user): query=query.filter(Project.lead_org_id==user.division_id)
    if type: query=query.filter(RaidItem.type==type)
    if severity: query=query.filter(RaidItem.severity==severity)
    items=query.order_by(RaidItem.exposure.desc()).all(); users={u.id:u for u in db.query(User).all()}; orgs={o.id:o for o in db.query(Organization).all()}
    deps=db.query(Dependency,Project).join(Project,Dependency.source_project_id==Project.id)
    if not is_enterprise_user(user): deps=deps.filter(Project.lead_org_id==user.division_id)
    return render(request,"risks.html",user,db,items=items,dependencies=deps.all(),users_map=users,orgs_map=orgs,type=type,severity=severity)


@app.get("/decisions", response_class=HTMLResponse)
def decisions_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    query=db.query(Decision).order_by(Decision.created_at.desc()); decisions=query.all(); users={u.id:u for u in db.query(User).all()}; demands={d.id:d for d in scoped_demands(db,user).all()}; projects={p.id:p for p in scoped_projects(db,user).all()}; decisions=[d for d in decisions if (d.demand_id in demands or d.project_id in projects)]
    return render(request,"decisions.html",user,db,decisions=decisions,users_map=users,demands_map=demands,projects_map=projects)


@app.get("/resources", response_class=HTMLResponse)
def resources_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q=db.query(ResourceCapacity); requests_q=db.query(ResourceRequest)
    if not is_enterprise_user(user):
        q=q.filter(ResourceCapacity.org_id==user.division_id); requests_q=requests_q.filter(ResourceRequest.org_id==user.division_id)
    rows=q.order_by(ResourceCapacity.org_id,ResourceCapacity.role_name).all(); orgs={o.id:o for o in db.query(Organization).all()}
    requests=requests_q.order_by(ResourceRequest.created_at.desc()).all(); users={u.id:u for u in db.query(User).all()}; projects={p.id:p for p in scoped_projects(db,user).all()}
    total_cap=sum(r.capacity_hours for r in rows); total_alloc=sum(r.allocated_hours for r in rows); over=[r for r in rows if r.allocated_hours>r.capacity_hours]; gaps=[r for r in rows if r.allocated_hours+r.minimum_core_coverage>r.capacity_hours]
    return render(request,"resources.html",user,db,rows=rows,orgs_map=orgs,total_cap=total_cap,total_alloc=total_alloc,over=over,gaps=gaps,resource_requests=requests,users_map=users,projects_map=projects,project_options=list(projects.values()))


@app.get("/resources/requests/new", response_class=HTMLResponse)
def resource_request_new(request: Request, project: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "PROJECT_MANAGER", "RESOURCE_MANAGER", "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN")
    orgs = [item for item in db.query(Organization).filter(Organization.org_type == "Division", Organization.active.is_(True)).order_by(Organization.code).all() if can_access_org(user, item.id)]
    projects = scoped_projects(db, user).order_by(Project.human_id).all()
    return render(request, "resource_request_form.html", user, db, eligible_orgs=orgs, project_options=projects,
                  selected_project=next((item for item in projects if item.id == project), None))


@app.get("/resources/requests/{request_id}", response_class=HTMLResponse)
def resource_request_detail(request_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.get(ResourceRequest, request_id)
    if not item or not can_access_org(user, item.org_id):
        raise HTTPException(404, "Resource request not found")
    return render(request, "resource_request_detail.html", user, db, record=item, org=db.get(Organization, item.org_id),
                  project=db.get(Project, item.project_id) if item.project_id else None,
                  requester=db.get(User, item.requested_by_id), approver=db.get(User, item.approver_id) if item.approver_id else None,
                  can_decide=item.status == "Submitted" and has_role(user, "RESOURCE_MANAGER", "PMO", "DIVISION_CHIEF", "ADMIN"),
                  audit=record_audit_events(db, item.id))


@app.get("/resources/import", response_class=HTMLResponse)
def resource_import_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "ADMIN")
    batches = db.query(ImportBatch).filter(ImportBatch.template_type == "Resource Capacity").order_by(ImportBatch.created_at.desc()).limit(20).all()
    return render(request, "resource_import.html", user, db, batches=batches, columns=RESOURCE_COLUMNS)


@app.post("/resources/import/preview", response_class=HTMLResponse)
async def resource_import_preview(request: Request, csrf: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN")
    if not (file.filename or "").lower().endswith(".csv"):
        return flash_redirect("/resources/import", "Resource import currently requires the provided CSV template.", "error")
    raw = await file.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        return flash_redirect("/resources/import", "Upload exceeds the configured size limit.", "error")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or any(column not in reader.fieldnames for column in RESOURCE_COLUMNS):
            missing = [column for column in RESOURCE_COLUMNS if column not in (reader.fieldnames or [])]
            return flash_redirect("/resources/import", f"Missing required columns: {', '.join(missing)}", "error")
        source_rows = list(reader)
    except UnicodeDecodeError:
        return flash_redirect("/resources/import", "CSV must be UTF-8 encoded.", "error")
    results, summary = validate_resource_rows(db, source_rows)
    batch = ImportBatch(filename=(file.filename or "resources.csv")[:240], template_type="Resource Capacity", status="Preview", uploaded_by_id=user.id, rows_json=results, summary_json=summary)
    db.add(batch); db.flush()
    for result in results:
        db.add(ImportRow(batch_id=batch.id, row_number=result["row_number"], record_identifier=result["record_identifier"], action_taken=result["action"], severity=result["severity"], validation_message=result["message"], corrective_guidance="Correct the CSV and preview again." if result["severity"] == "Error" else ""))
    record_audit(db, user.id, "ImportBatch", batch.id, "PREVIEW_RESOURCE_IMPORT", after={"filename": batch.filename, "summary": summary}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit(); return render(request, "resource_import_preview.html", user, db, batch=batch, results=results, summary=summary)


@app.post("/resources/import/{batch_id}/commit")
def resource_import_commit(batch_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN")
    batch = db.get(ImportBatch, batch_id)
    if not batch or batch.template_type != "Resource Capacity" or batch.status != "Preview":
        raise HTTPException(404, "Resource import preview not found")
    if (batch.summary_json or {}).get("errors"):
        return flash_redirect("/resources/import", "Correct all rejected rows before commit.", "error")
    changed = 0
    for result in batch.rows_json or []:
        if result.get("action") == "Unchanged":
            continue
        data = result["data"]
        record = db.get(ResourceCapacity, data.get("existing_id")) if data.get("existing_id") else ResourceCapacity()
        before = snapshot(record) if data.get("existing_id") else None
        record.org_id, record.role_name, record.skill, record.period = data["org_id"], data["role_name"], data["skill"], data["period"]
        for field in ("capacity_hours", "allocated_hours", "actual_hours", "minimum_core_coverage"):
            setattr(record, field, data[field])
        if not data.get("existing_id"): db.add(record)
        db.flush(); changed += 1
        record_audit(db, user.id, "ResourceCapacity", record.id, result["action"].upper(), before=before, after=snapshot(record), ip_address=getattr(request.state, "client_ip", ""))
    batch.status = "Committed"
    record_audit(db, user.id, "ImportBatch", batch.id, "COMMIT_RESOURCE_IMPORT", after={"changed": changed, "summary": batch.summary_json}, ip_address=getattr(request.state, "client_ip", ""))
    db.commit(); return flash_redirect("/resources", f"Resource import committed: {changed} records created or updated.")


@app.get("/financials", response_class=HTMLResponse)
def financials_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = db.query(FinancialRecord, Project).join(Project, FinancialRecord.project_id == Project.id)
    category = request.query_params.get("category", "").strip()
    division = request.query_params.get("division", "").strip().upper()
    view = request.query_params.get("view", "").strip().lower()
    if not is_enterprise_user(user):
        q = q.filter(Project.lead_org_id == user.division_id)
    if category:
        q = q.filter(FinancialRecord.category == category)
    if division:
        org = db.query(Organization).filter(Organization.code == division).first()
        q = q.filter(Project.lead_org_id == org.id) if org else q.filter(False)
    if view == "actual":
        q = q.filter(FinancialRecord.actual_cost > 0)
    elif view == "remaining":
        q = q.filter(FinancialRecord.approved_budget > FinancialRecord.actual_cost)
    rows = q.order_by(FinancialRecord.fiscal_year.desc(), Project.title).all()
    allowed_ids = [f.id for f, _p in rows]
    transactions = db.query(FinancialTransaction).filter(FinancialTransaction.financial_record_id.in_(allowed_ids)).order_by(FinancialTransaction.transaction_date.desc(), FinancialTransaction.created_at.desc()).limit(100).all() if allowed_ids else []
    financial_map = {f.id: (f, p) for f, p in rows}
    budget = sum(float(f.approved_budget) for f, _p in rows)
    actual = sum(float(f.actual_cost) for f, _p in rows)
    forecast = sum(float(f.forecast) for f, _p in rows)
    unfunded = sum(float(f.full_requirement) - float(f.approved_budget) for f, _p in rows if f.funding_status != "Funded")
    transaction_totals = Counter(t.transaction_type for t in transactions)
    return render(request, "financials.html", user, db, rows=rows, budget=budget, actual=actual, forecast=forecast, unfunded=unfunded, transactions=transactions, financial_map=financial_map, transaction_totals=transaction_totals, filters={"category": category, "division": division, "view": view})


@app.get("/benefits", response_class=HTMLResponse)
def benefits_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q=db.query(Benefit,Project).join(Project,Benefit.project_id==Project.id)
    if not is_enterprise_user(user): q=q.filter(Project.lead_org_id==user.division_id)
    rows=q.all(); users={u.id:u for u in db.query(User).all()}; target=sum(b.target_value for b,p in rows); realized=sum(b.realized_value for b,p in rows)
    return render(request,"benefits.html",user,db,rows=rows,users_map=users,target=target,realized=realized)


@app.get("/notifications", response_class=HTMLResponse)
def notifications_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    notes=db.query(Notification).filter(Notification.user_id==user.id).order_by(Notification.created_at.desc()).all(); return render(request,"notifications.html",user,db,notifications=notes)


@app.post("/notifications/read-all")
def notifications_read_all(request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); db.query(Notification).filter(Notification.user_id==user.id,Notification.read_at.is_(None)).update({"read_at":datetime.now(timezone.utc)}); db.commit(); return flash_redirect("/notifications","All notifications marked read.")


@app.get("/my-work", response_class=HTMLResponse)
def my_work(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    demands = scoped_demands(db, user).filter(or_(Demand.requester_id == user.id, Demand.current_owner_id == user.id, Demand.sponsor_id == user.id)).all()
    projects = scoped_projects(db, user).filter(or_(Project.manager_id == user.id, Project.sponsor_id == user.id)).all()
    tasks = db.query(Task, Project).join(Project, Task.project_id == Project.id).filter(Task.owner_id == user.id, Task.status != "Completed").order_by(Task.due_date).all()
    actions = db.query(Action).filter(Action.owner_id == user.id, Action.status != "Closed").order_by(Action.due_date).all()
    review_questions = db.query(ReviewQuestion).filter(ReviewQuestion.assigned_to_id == user.id, ReviewQuestion.status != "Closed").order_by(ReviewQuestion.due_date, ReviewQuestion.created_at).all()
    change_requests = db.query(ReviewChangeRequest).filter(ReviewChangeRequest.owner_id == user.id, ReviewChangeRequest.status.in_(["Open", "Clarification Required"])).order_by(ReviewChangeRequest.due_date, ReviewChangeRequest.created_at).all()
    review_ids = {item.review_id for item in review_questions} | {item.review_id for item in change_requests}
    review_map = {review.id: review for review in db.query(PortfolioReview).filter(PortfolioReview.id.in_(review_ids)).all()} if review_ids else {}
    travel_followups = []
    if has_role(user, "ADMIN", "PMO", "DATA_STEWARD", "DIVISION_CHIEF", "DIVISION_PORTFOLIO_MANAGER"):
        travel_followups = scoped_trip_reports(db, user).filter(or_(TripReport.request_id.is_(None), TripReport.review_status.notin_(["Reviewed", "Closed"]))).order_by(TripReport.return_date).all()

    # ---- Unified Action Center queue (v0.7.9) -------------------------------
    today_date = date.today()
    soon = today_date + timedelta(days=7)
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=14)

    def _item(kind, title, why, parent, priority, due, href, primary_label, quick=None, status=None):
        return {"kind": kind, "title": title, "why": why, "parent": parent, "priority": priority,
                "due": due, "href": href, "primary_label": primary_label, "quick": quick or {}, "status": status}

    groups = {"critical": [], "awaiting": [], "due_soon": [], "needs_update": [], "watching": [], "done_recent": []}

    for t, p in tasks:
        overdue = bool(t.due_date and t.due_date < today_date)
        base_item = _item(
            "task", f"{t.human_id} · {t.title}",
            (f"Overdue since {t.due_date.strftime('%d %b')}" if overdue else f"{t.priority} priority · {t.percent_complete}% complete"),
            p.human_id, t.priority, t.due_date, f"/projects/{p.id}/tasks/{t.id}", "Update task",
            quick={"task_id": t.id, "percent": t.percent_complete}, status=t.status,
        )
        if overdue and t.priority in ("Critical", "High"):
            groups["critical"].append(base_item)
        elif t.due_date and t.due_date <= soon:
            groups["due_soon"].append(base_item)
        elif overdue:
            groups["needs_update"].append(base_item)
        else:
            groups["watching"].append(base_item)

    for a in actions:
        overdue = bool(a.due_date and a.due_date < today_date)
        item = _item(
            "action", f"{a.human_id} · {a.title}",
            (f"Overdue commitment from {a.source_type}" if overdue else f"Follow-through on {a.source_type}"),
            a.source_type, "High" if overdue else "Medium", a.due_date, f"/records/action/{a.id}", "Close out",
            quick={"action_id": a.id}, status=a.status,
        )
        (groups["critical"] if overdue else groups["awaiting"]).append(item)

    for q in review_questions:
        review = review_map.get(q.review_id)
        groups["awaiting"].append(_item(
            "question", f"{q.human_id} · {q.question}",
            "Leadership briefing question awaiting your answer",
            review.title if review else "Division briefing", q.priority, q.due_date,
            f"/portfolio-reviews/{q.review_id}/brief?section={q.section_id or ''}", "Respond", status=q.status,
        ))
    for c in change_requests:
        review = review_map.get(c.review_id)
        groups["awaiting"].append(_item(
            "change", f"{c.human_id} · {c.field_name or 'Source-record change'}",
            "Governed change request awaiting disposition",
            review.title if review else "Division briefing", "High", c.due_date,
            f"/portfolio-reviews/{c.review_id}/brief?section={c.section_id or ''}", "Resolve", status=c.status,
        ))
    for r in travel_followups:
        groups["awaiting"].append(_item(
            "trip", f"{r.human_id} · {r.title}",
            ("Report is not matched to a travel request" if not r.request_id else "Outcome review pending"),
            r.traveler_name or "Travel", "Medium", r.return_date, f"/travel/reports/{r.id}",
            ("Reconcile" if not r.request_id else "Review outcome"), status=r.review_status,
        ))

    for p in projects:
        last = p.last_status_date.replace(tzinfo=p.last_status_date.tzinfo or timezone.utc) if p.last_status_date else None
        if last is None or last < stale_cutoff:
            groups["needs_update"].append(_item(
                "project", f"{p.human_id} · {p.title}",
                ("No status has been submitted yet" if last is None else f"Status is stale · last updated {last.strftime('%d %b')}"),
                p.human_id, "Medium", None, f"/projects/{p.id}", "Submit status", status=p.status,
            ))
        health = p.health_override or p.health_owner or p.health_calculated
        if health in ("At Risk", "Off Track", "Blocked"):
            groups["watching"].append(_item(
                "project", f"{p.human_id} · {p.title}",
                f"Project health is {health}", p.human_id, "High", None, f"/projects/{p.id}", "Open project", status=health,
            ))

    done_recent = (
        db.query(Task, Project).join(Project, Task.project_id == Project.id)
        .filter(Task.owner_id == user.id, Task.status == "Completed")
        .order_by(Task.updated_at.desc() if hasattr(Task, "updated_at") else Task.due_date.desc()).limit(5).all()
    )
    for t, p in done_recent:
        groups["done_recent"].append(_item(
            "task", f"{t.human_id} · {t.title}", f"Completed — feeds {p.human_id} progress and health",
            p.human_id, t.priority, t.due_date, f"/projects/{p.id}/tasks/{t.id}", "View", status="Completed",
        ))

    priority_rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    for key in ("critical", "awaiting", "due_soon", "needs_update", "watching"):
        groups[key].sort(key=lambda i: (i["due"] or date.max, priority_rank.get(i["priority"], 2)))
    open_total = sum(len(groups[k]) for k in ("critical", "awaiting", "due_soon", "needs_update"))
    group_meta = [
        ("critical", "Critical now", "Overdue critical work and expired commitments"),
        ("awaiting", "Awaiting me", "Reviews, answers, dispositions, and reconciliation"),
        ("due_soon", "Due soon", "Work due within the next seven days"),
        ("needs_update", "Needs update", "Stale status and records missing current information"),
        ("watching", "Watching", "Health deterioration and longer-horizon work"),
        ("done_recent", "Recently completed", "Confirmation that finished work rolled up"),
    ]
    return render(request, "my_work.html", user, db, demands=demands, projects=projects, tasks=tasks, actions=actions,
                  review_questions=review_questions, change_requests=change_requests, review_map=review_map,
                  travel_followups=travel_followups, groups=groups, group_meta=group_meta, open_total=open_total)


TASK_QUICK_STATUSES = {"Not Started", "In Progress", "Blocked", "Completed"}


@app.post("/quick/tasks/{task_id}")
def quick_task_update(task_id: str, request: Request, csrf: str = Form(...), status: str = Form(None), percent_complete: int = Form(None), blocker_note: str = Form(None), db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Fast inline task update from the My Work Action Center (v0.7.9).

    Governance: limited to the task owner or the managing PM; writes an audit
    record with before/after values; status values restricted to the standard set.
    """
    require_csrf(request, user, csrf)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    project = get_accessible_project(db, user, task.project_id)
    if task.owner_id != user.id and project.manager_id != user.id and not has_role(user, "ADMIN", "PMO"):
        raise HTTPException(403, "Only the task owner or project manager can quick-update this task")
    before = {"status": task.status, "percent_complete": task.percent_complete}
    changed = []
    if status:
        if status not in TASK_QUICK_STATUSES:
            return flash_redirect("/my-work", "That status is not a valid quick update.", "error")
        task.status = status
        if status == "Completed":
            task.percent_complete = 100
        changed.append(f"status → {status}")
    if percent_complete is not None:
        task.percent_complete = max(0, min(100, int(percent_complete)))
        if task.percent_complete == 100 and task.status != "Completed":
            task.status = "Completed"
        changed.append(f"{task.percent_complete}% complete")
    if blocker_note:
        task.status = "Blocked"
        comment = TaskComment(task_id=task.id, author_id=user.id, body=f"Blocker: {blocker_note.strip()[:2000]}")
        db.add(comment)
        changed.append("blocker recorded")
    if not changed:
        return flash_redirect("/my-work", "No quick-update values were provided.", "error")
    record_audit(db, user.id, "Task", task.id, "QUICK_UPDATE", before=before, after={"status": task.status, "percent_complete": task.percent_complete})
    db.commit()
    return flash_redirect("/my-work", f"{task.human_id} updated: {', '.join(changed)}.")


@app.post("/quick/actions/{action_id}/close")
def quick_action_close(action_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Close an assigned action from the Action Center with an audit trail (v0.7.9)."""
    require_csrf(request, user, csrf)
    action = db.get(Action, action_id)
    if not action:
        raise HTTPException(404, "Action not found")
    if action.owner_id != user.id and not has_role(user, "ADMIN", "PMO"):
        raise HTTPException(403, "Only the action owner can quick-close this action")
    before = {"status": action.status}
    action.status = "Closed"
    record_audit(db, user.id, "Action", action.id, "QUICK_CLOSE", before=before, after={"status": action.status})
    db.commit()
    return flash_redirect("/my-work", f"{action.human_id} closed.")



@app.get("/travel", response_class=HTMLResponse)
def travel_dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = scoped_travel_requests(db, user)
    division = request.query_params.get("division", "").strip().upper()
    determination = request.query_params.get("determination", "").strip()
    location = request.query_params.get("location", "").strip()
    q = request.query_params.get("q", "").strip()
    start_text = request.query_params.get("start", "").strip()
    end_text = request.query_params.get("end", "").strip()
    if division:
        org = db.query(Organization).filter(Organization.code == division).first()
        query = query.filter(TravelRequest.org_id == org.id) if org else query.filter(False)
    if determination:
        query = query.filter(TravelRequest.determination == determination)
    if q:
        pattern = f"%{q}%"
        engagement_ids = [e.id for e in db.query(TravelEngagement).filter(TravelEngagement.title.ilike(pattern)).all()]
        query = query.filter(or_(TravelRequest.traveler_name.ilike(pattern), TravelRequest.location.ilike(pattern), TravelRequest.external_id.ilike(pattern), TravelRequest.engagement_id.in_(engagement_ids or ["-"])))
    try:
        if start_text:
            query = query.filter(TravelRequest.departure_date >= date.fromisoformat(start_text))
        if end_text:
            query = query.filter(TravelRequest.departure_date <= date.fromisoformat(end_text))
    except ValueError:
        return flash_redirect("/travel", "Date filters must use YYYY-MM-DD.", "error")
    requests = query.order_by(TravelRequest.departure_date.desc(), TravelRequest.external_id).all()
    if location:
        requests = [item for item in requests if resolve_location(item.location)["canonical"] == location]
    request_ids = {item.id for item in requests}
    reports = scoped_trip_reports(db, user).filter(or_(TripReport.request_id.in_(request_ids or ["-"]), TripReport.request_id.is_(None))).order_by(TripReport.return_date.desc()).all()
    if location:
        reports = [item for item in reports if item.request_id in request_ids or (not item.request_id and resolve_location(item.location)["canonical"] == location)]
    engagement_ids = {item.engagement_id for item in requests if item.engagement_id}
    engagements = db.query(TravelEngagement).filter(TravelEngagement.id.in_(engagement_ids or ["-"])).all()
    report_ids = [item.id for item in reports]
    report_items = db.query(TripReportItem).filter(TripReportItem.report_id.in_(report_ids)).all() if report_ids else []
    payload = travel_dashboard_payload(requests, reports, engagements, report_items)
    orgs = {org.id: org for org in db.query(Organization).filter(Organization.org_type == "Division").order_by(Organization.code).all()}
    engagement_map = {item.id: item for item in engagements}
    report_by_request = {item.request_id: item for item in reports if item.request_id}
    max_division_cost = max(payload["division_costs"].values(), default=1)
    max_month_cost = max(payload["month_costs"].values(), default=1)
    max_month_count = max(payload["month_counts"].values(), default=1)
    reconciliation = [r for r in reports if r.match_status in {"Unmatched", "Suggested Match", "Needs Reconciliation"}]
    filters = {"division": division, "determination": determination, "location": location, "q": q, "start": start_text, "end": end_text}
    for row in payload["location_rows"]:
        params = {key: value for key, value in filters.items() if value and key != "location"}
        params["location"] = row["location"]
        row["url"] = f"/travel?{urlencode(params)}"
        row["key"] = re.sub(r"[^a-z0-9]+", "-", row["location"].lower()).strip("-")
        row["division_codes"] = [orgs[org_id].code for org_id in {item.org_id for item in requests if resolve_location(item.location)["canonical"] == row["location"]} if org_id in orgs]
    compliance_rows = []
    for org_id, values in payload["compliance"].items():
        org = orgs.get(org_id)
        if org:
            compliance_rows.append({"org": org, **values})
    compliance_rows.sort(key=lambda item: (item["overdue"], item["approved_completed"]), reverse=True)
    division_status_rows = [{"org": orgs[org_id], **counts} for org_id, counts in payload["division_status"].items() if org_id in orgs]
    division_status_rows.sort(key=lambda row: sum(row.get(status, 0) for status in ["Approved", "Pending", "Canceled", "Disapproved"]), reverse=True)
    report_items_by_report = defaultdict(list)
    for item in report_items:
        report_items_by_report[item.report_id].append(item)
    engagement_rows = []
    for engagement in engagements:
        engagement_requests = [item for item in requests if item.engagement_id == engagement.id]
        engagement_reports = [item for item in reports if item.engagement_id == engagement.id or item.request_id in {request_item.id for request_item in engagement_requests}]
        engagement_rows.append({
            "engagement": engagement,
            "cost": sum(float(item.estimated_cost or 0) for item in engagement_requests),
            "travelers": len(engagement_requests),
            "divisions": len({item.org_id for item in engagement_requests}),
            "reports": len(engagement_reports),
            "reviewed": sum(item.review_status in {"Reviewed", "Closed"} for item in engagement_reports),
            "promoted": sum(bool(outcome.promoted_entity_type) for report in engagement_reports for outcome in report_items_by_report.get(report.id, [])),
        })
    engagement_rows.sort(key=lambda row: (row["cost"], row["reports"], row["travelers"]), reverse=True)
    # ---- v0.7.9: focused workspaces + server-side pagination ---------------
    view = request.query_params.get("view", "overview")
    if view not in {"overview", "requests", "reports", "reconciliation", "outcomes"}:
        view = "overview"
    page_size = 25
    try:
        page = max(1, int(request.query_params.get("page", "1")))
    except ValueError:
        page = 1
    requests_total = len(requests)
    reports_total = len(reports)
    reconciliation_total = len(reconciliation)

    def _paginate(items):
        pages = max(1, (len(items) + page_size - 1) // page_size)
        current = min(page, pages)
        return items[(current - 1) * page_size: current * page_size], pages, current

    requests_page, requests_pages, requests_current = _paginate(requests)
    reports_page, reports_pages, reports_current = _paginate(reports)
    reconciliation_page, reconciliation_pages, reconciliation_current = _paginate(reconciliation)
    view_query = urlencode({k: v for k, v in filters.items() if v})
    return render(
        request, "travel.html", user, db,
        requests=requests, reports=reports, engagements=engagements, payload=payload,
        orgs=orgs, engagement_map=engagement_map, report_by_request=report_by_request,
        max_division_cost=max_division_cost, max_month_cost=max_month_cost, max_month_count=max_month_count,
        reconciliation=reconciliation, compliance_rows=compliance_rows, division_status_rows=division_status_rows, engagement_rows=engagement_rows,
        filters=filters, active_filter_count=sum(bool(value) for value in filters.values()),
        can_manage=has_role(user, "ADMIN", "PMO", "DATA_STEWARD", "DIVISION_PORTFOLIO_MANAGER", "DIVISION_CHIEF"),
        view=view, view_query=view_query, page_size=page_size,
        requests_total=requests_total, requests_page=requests_page, requests_pages=requests_pages, requests_current=requests_current,
        reports_total=reports_total, reports_page=reports_page, reports_pages=reports_pages, reports_current=reports_current,
        reconciliation_total=reconciliation_total, reconciliation_page=reconciliation_page, reconciliation_pages=reconciliation_pages, reconciliation_current=reconciliation_current,
    )


@app.get("/travel/requests/{request_id}", response_class=HTMLResponse)
def travel_request_detail(request_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = get_accessible_travel_request(db, user, request_id)
    engagement = db.get(TravelEngagement, record.engagement_id) if record.engagement_id else None
    reports = scoped_trip_reports(db, user).filter(TripReport.request_id == record.id).order_by(TripReport.version.desc()).all()
    approvals = db.query(TravelApprovalStep).filter(TravelApprovalStep.request_id == record.id).order_by(TravelApprovalStep.step_order).all()
    org = db.get(Organization, record.org_id)
    links = db.query(TravelEntityLink).filter(or_(and_(TravelEntityLink.source_entity_type == "TravelRequest", TravelEntityLink.source_entity_id == record.id), and_(TravelEntityLink.source_entity_type == "TravelEngagement", TravelEntityLink.source_entity_id == record.engagement_id))).all()
    link_rows = resolve_travel_entity_links(db, user, links)
    audit = db.query(AuditEvent).filter(AuditEvent.entity_id.in_([record.id] + ([record.engagement_id] if record.engagement_id else []))).order_by(AuditEvent.created_at.desc()).limit(30).all()
    return render(request, "travel_request_detail.html", user, db, record=record, engagement=engagement, reports=reports, approvals=approvals, org=org, links=links, link_rows=link_rows, audit=audit)


@app.get("/travel/reports/{report_id}", response_class=HTMLResponse)
def trip_report_detail(report_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    report = get_accessible_trip_report(db, user, report_id)
    request_record = db.get(TravelRequest, report.request_id) if report.request_id else None
    engagement = db.get(TravelEngagement, report.engagement_id) if report.engagement_id else None
    items = db.query(TripReportItem).filter(TripReportItem.report_id == report.id).order_by(TripReportItem.sequence).all()
    candidates = match_candidates(db, report, 5) if report.match_status in {"Unmatched", "Suggested Match", "Needs Reconciliation"} else []
    org = db.get(Organization, report.org_id)
    links = db.query(TravelEntityLink).filter(TravelEntityLink.source_entity_type.in_(["TripReport", "TripReportItem"]), or_(TravelEntityLink.source_entity_id == report.id, TravelEntityLink.source_entity_id.in_([i.id for i in items] or ["-"]))).all()
    link_rows = resolve_travel_entity_links(db, user, links)
    links_by_source = defaultdict(list)
    for row in link_rows:
        links_by_source[row["link"].source_entity_id].append(row)
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    projects = scoped_projects(db, user).order_by(Project.human_id).all()
    demands = scoped_demands(db, user).order_by(Demand.human_id).all()
    audit = db.query(AuditEvent).filter(or_(AuditEvent.entity_id == report.id, AuditEvent.entity_id.in_([i.id for i in items] or ["-"]))).order_by(AuditEvent.created_at.desc()).limit(40).all()
    can_manage = has_role(user, "ADMIN", "PMO", "DATA_STEWARD", "DIVISION_PORTFOLIO_MANAGER", "DIVISION_CHIEF") and can_edit_business_data(user)
    return render(request, "trip_report_detail.html", user, db, report=report, request_record=request_record, engagement=engagement, items=items, candidates=candidates, org=org, links=links, link_rows=link_rows, links_by_source=links_by_source, users=users, projects=projects, demands=demands, audit=audit, can_manage=can_manage)


@app.post("/travel/reports/{report_id}/match")
def match_trip_report(report_id: str, request: Request, csrf: str = Form(...), travel_request_id: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN", "PMO", "DATA_STEWARD", "DIVISION_PORTFOLIO_MANAGER", "DIVISION_CHIEF")
    report = get_accessible_trip_report(db, user, report_id)
    before = snapshot(report)
    if not travel_request_id:
        report.request_id = None
        report.engagement_id = None
        report.match_status = "Needs Reconciliation"
        report.match_confidence = 0
        report.match_rationale = "Prior link cleared by an authorized reviewer; reconciliation is required."
        report.matched_by_id = user.id
        report.matched_at = datetime.now(timezone.utc)
        record_audit(db, user.id, "TripReport", report.id, "MATCH_CLEAR", before=before, after=snapshot(report), ip_address=request.state.client_ip)
        db.commit()
        return flash_redirect(f"/travel/reports/{report.id}", f"Link cleared for {report.human_id}; select a new candidate match.", "warning")
    travel_request = get_accessible_travel_request(db, user, travel_request_id)
    if report.org_id != travel_request.org_id and not is_enterprise_user(user):
        raise HTTPException(403, "Cannot reconcile across division scope")
    report.request_id = travel_request.id
    report.engagement_id = travel_request.engagement_id
    report.match_status = "Confirmed"
    report.match_confidence = 1.0
    report.match_rationale = "Human-confirmed reconciliation from the candidate queue."
    report.matched_by_id = user.id
    report.matched_at = datetime.now(timezone.utc)
    record_audit(db, user.id, "TripReport", report.id, "MATCH_CONFIRM", before=before, after=snapshot(report), ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/travel/reports/{report.id}", f"{report.human_id} linked to travel request {travel_request.human_id}.")


@app.post("/travel/reports/{report_id}/review")
def review_trip_report(report_id: str, request: Request, csrf: str = Form(...), review_status: str = Form(...), review_comments: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN", "PMO", "DATA_STEWARD", "DIVISION_PORTFOLIO_MANAGER", "DIVISION_CHIEF")
    report = get_accessible_trip_report(db, user, report_id)
    allowed = {"Awaiting Review", "In Review", "Reviewed", "Changes Required", "Closed"}
    if review_status not in allowed:
        raise HTTPException(400, "Unsupported report review status")
    before = snapshot(report); report.review_status = review_status
    report.review_comments = review_comments.strip()[:8000]
    report.reviewed_by_id = user.id
    report.reviewed_at = datetime.now(timezone.utc)
    record_audit(db, user.id, "TripReport", report.id, "REVIEW_STATUS", before=before, after=snapshot(report), ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/travel/reports/{report.id}", "Trip report review status updated.")


@app.post("/travel/report-items/{item_id}/promote")
def promote_trip_report_item(
    item_id: str, request: Request, csrf: str = Form(...), promotion_type: str = Form(...),
    owner_id: str = Form(""), due_date: str = Form(""), project_id: str = Form(""), demand_id: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN", "PMO", "DIVISION_PORTFOLIO_MANAGER", "DIVISION_CHIEF")
    item = db.get(TripReportItem, item_id)
    if not item:
        raise HTTPException(404, "Trip report item not found")
    report = get_accessible_trip_report(db, user, item.report_id)
    if item.promoted_entity_id:
        return flash_redirect(f"/travel/reports/{report.id}", "This outcome has already been promoted.", "warning")
    try:
        parsed_due = date.fromisoformat(due_date) if due_date else None
    except ValueError:
        return flash_redirect(f"/travel/reports/{report.id}", "Due date must use YYYY-MM-DD.", "error")
    if owner_id and not db.get(User, owner_id):
        raise HTTPException(400, "Unknown owner")
    linked_project = scoped_projects(db, user).filter(Project.id == project_id).first() if project_id else None
    linked_demand = scoped_demands(db, user).filter(Demand.id == demand_id).first() if demand_id else None
    if project_id and not linked_project:
        raise HTTPException(403, "Project is outside the accessible scope")
    if demand_id and not linked_demand:
        raise HTTPException(403, "Demand is outside the accessible scope")
    entity_type = ""; entity_id = ""
    if promotion_type == "Action":
        if not owner_id:
            return flash_redirect(f"/travel/reports/{report.id}", "Select an action owner.", "error")
        action = Action(human_id=next_human_id(db, Action, "ACT"), title=item.title or item.body[:240], owner_id=owner_id, due_date=parsed_due, project_id=project_id or None, demand_id=demand_id or None, source_type="Trip report outcome")
        db.add(action); db.flush(); entity_type, entity_id = "Action", action.id
    elif promotion_type == "Risk":
        if not project_id:
            return flash_redirect(f"/travel/reports/{report.id}", "Select a project before promoting a risk.", "error")
        risk = RaidItem(human_id=next_human_id(db, RaidItem, "RAID"), project_id=project_id, type="Risk", title=item.title or item.body[:240], description=item.body, owner_id=owner_id or user.id, status="Open", severity="Medium", likelihood="Possible", consequence="Outcome identified in a trip report; impact requires project review.", mitigation="Assign owner and disposition through the project RAID process.", due_date=parsed_due, evidence=f"Source: {report.human_id} / {item.human_id}")
        db.add(risk); db.flush(); entity_type, entity_id = "RaidItem", risk.id
    elif promotion_type == "Decision":
        decision = Decision(human_id=next_human_id(db, Decision, "DEC"), project_id=project_id or None, demand_id=demand_id or None, decision="Decision Requested", authority_id=owner_id or user.id, participants=f"Source trip report {report.human_id}", rationale=item.body, evidence=f"Trip report outcome {item.human_id}")
        db.add(decision); db.flush(); entity_type, entity_id = "Decision", decision.id
    elif promotion_type == "Dependency":
        if not project_id:
            return flash_redirect(f"/travel/reports/{report.id}", "Select a source project before promoting a dependency.", "error")
        dependency = Dependency(human_id=next_human_id(db, Dependency, "DEP"), source_project_id=project_id, title=item.title or item.body[:240], status="Open", owner_id=owner_id or user.id, due_date=parsed_due, impact=item.body, external_party=report.location)
        db.add(dependency); db.flush(); entity_type, entity_id = "Dependency", dependency.id
    elif promotion_type == "Retain as Finding":
        item.status = "Reviewed Finding"; item.reviewed_by_id = user.id; item.reviewed_at = datetime.now(timezone.utc)
        record_audit(db, user.id, "TripReportItem", item.id, "RETAIN_FINDING", after=snapshot(item), ip_address=request.state.client_ip); db.commit()
        return flash_redirect(f"/travel/reports/{report.id}", "Outcome retained as a reviewed finding without creating portfolio work.")
    elif promotion_type == "Dismiss":
        item.status = "Dismissed"; item.reviewed_by_id = user.id; item.reviewed_at = datetime.now(timezone.utc)
        record_audit(db, user.id, "TripReportItem", item.id, "DISMISS", after=snapshot(item), ip_address=request.state.client_ip); db.commit()
        return flash_redirect(f"/travel/reports/{report.id}", "Outcome retained as historical narrative and dismissed from promotion.")
    else:
        raise HTTPException(400, "Unsupported promotion type")
    item.status = "Promoted"; item.promoted_entity_type = entity_type; item.promoted_entity_id = entity_id; item.owner_id = owner_id or item.owner_id; item.due_date = parsed_due; item.reviewed_by_id = user.id; item.reviewed_at = datetime.now(timezone.utc)
    link = TravelEntityLink(source_entity_type="TripReportItem", source_entity_id=item.id, target_entity_type=entity_type, target_entity_id=entity_id, link_type="Promoted to", rationale=f"Promoted from {report.human_id}", created_by_id=user.id)
    db.add(link)
    record_audit(db, user.id, "TripReportItem", item.id, "PROMOTE", after={"promotion_type": entity_type, "target_id": entity_id, "report": report.human_id}, ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/travel/reports/{report.id}", f"{item.human_id} promoted to {entity_type}.")


@app.get("/travel/engagements/{engagement_id}", response_class=HTMLResponse)
def travel_engagement_detail(engagement_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    engagement = db.get(TravelEngagement, engagement_id)
    if not engagement:
        raise HTTPException(404, "Engagement not found")
    requests = scoped_travel_requests(db, user).filter(TravelRequest.engagement_id == engagement.id).order_by(TravelRequest.traveler_name).all()
    if not requests:
        raise HTTPException(404, "Engagement not found")
    request_ids = [r.id for r in requests]
    reports = scoped_trip_reports(db, user).filter(or_(TripReport.engagement_id == engagement.id, TripReport.request_id.in_(request_ids))).order_by(TripReport.return_date.desc()).all()
    orgs = {org.id: org for org in db.query(Organization).all()}
    items = db.query(TripReportItem).filter(TripReportItem.report_id.in_([r.id for r in reports] or ["-"])).order_by(TripReportItem.item_type, TripReportItem.sequence).all()
    total_cost = sum(float(r.estimated_cost or 0) for r in requests)
    return render(request, "travel_engagement_detail.html", user, db, engagement=engagement, requests=requests, reports=reports, items=items, orgs=orgs, total_cost=total_cost)


@app.get("/exports/travel-requests.csv")
def export_travel_requests(db: Session = Depends(get_db), user: User = Depends(current_user)):
    orgs = {org.id: org for org in db.query(Organization).all()}
    rows = []
    for item in scoped_travel_requests(db, user).order_by(TravelRequest.departure_date, TravelRequest.human_id).all():
        engagement = db.get(TravelEngagement, item.engagement_id) if item.engagement_id else None
        rows.append([item.human_id, item.external_id, item.traveler_name, orgs.get(item.org_id).code if orgs.get(item.org_id) else item.org_id, engagement.title if engagement else "", item.location, item.determination, item.departure_date, item.return_date, float(item.estimated_cost or 0), item.source_filename, item.source_row])
    return csv_response("ddc5i-travel-requests.csv", ["Stable ID", "Source ID", "Traveler", "Division", "Engagement", "Location", "Determination", "Departure", "Return", "Estimated Cost", "Source File", "Source Row"], rows)


@app.get("/exports/trip-reports.csv")
def export_trip_reports(db: Session = Depends(get_db), user: User = Depends(current_user)):
    orgs = {org.id: org for org in db.query(Organization).all()}
    rows = []
    for item in scoped_trip_reports(db, user).order_by(TripReport.return_date, TripReport.human_id).all():
        rows.append([item.human_id, item.title, item.traveler_name, orgs.get(item.org_id).code if orgs.get(item.org_id) else item.org_id, item.start_date, item.return_date, item.location, item.match_status, item.match_confidence, item.review_status, item.request_id or "", item.source_filename, item.source_row])
    return csv_response("ddc5i-trip-reports.csv", ["Stable ID", "Title", "Traveler", "Division", "Start", "Return", "Location", "Match Status", "Match Confidence", "Review Status", "Travel Request UUID", "Source File", "Source Row"], rows)

@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return render(request,"reports.html",user,db)


def csv_safe(value: Any) -> Any:
    """Prevent spreadsheet formula execution when an export is opened in Excel."""
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return "'" + value
    return value


def csv_response(filename: str, headers: list[str], rows: list[list[Any]]) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows([[csv_safe(value) for value in row] for row in rows])
    content = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(iter([content]),media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="{filename}"'})


@app.get("/exports/resources.csv")
def export_resources(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "ADMIN")
    orgs = {item.id: item for item in db.query(Organization).all()}
    rows = [[
        item.id, orgs.get(item.org_id).code if orgs.get(item.org_id) else item.org_id, item.role_name, item.skill,
        item.period, item.capacity_hours, item.allocated_hours, item.actual_hours, item.minimum_core_coverage,
    ] for item in db.query(ResourceCapacity).order_by(ResourceCapacity.org_id, ResourceCapacity.role_name, ResourceCapacity.skill, ResourceCapacity.period).all()]
    return csv_response("jsj6-resource-capacity-v0.8.0.csv", RESOURCE_COLUMNS, rows)


@app.get("/exports/resource-template.csv")
def export_resource_template(user: User = Depends(current_user)):
    require_roles(user, "ADMIN")
    return csv_response("jsj6-resource-capacity-import-template-v0.8.0.csv", RESOURCE_COLUMNS, [])


@app.get("/exports/resource-requests.csv")
def export_resource_requests(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "ADMIN")
    orgs = {item.id: item for item in db.query(Organization).all()}; projects = {item.id: item for item in db.query(Project).all()}
    rows = [[item.human_id, orgs.get(item.org_id).code if orgs.get(item.org_id) else item.org_id,
             projects.get(item.project_id).human_id if item.project_id and projects.get(item.project_id) else "",
             item.role_name, item.skill, item.requested_hours, item.period_start, item.period_end, item.priority,
             item.status, item.rationale, item.resolution] for item in db.query(ResourceRequest).order_by(ResourceRequest.created_at).all()]
    return csv_response("jsj6-resource-requests-v0.8.0.csv", ["request_id", "division_code", "project_id", "role_name", "skill", "requested_hours", "period_start", "period_end", "priority", "status", "rationale", "resolution"], rows)


@app.get("/exports/demands.csv")
def export_demands(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows=[]
    for d in scoped_demands(db,user).order_by(Demand.human_id).all(): rows.append([d.human_id,d.title,d.category,d.status,d.lead_org_id,d.mission_id,d.urgency,float(d.rom_cost),d.sensitivity,d.created_at.isoformat(),d.updated_at.isoformat(),d.source_system])
    return csv_response("ddc5i-demands.csv",["Stable ID","Title","Category","Status","Lead Organization UUID","Mission UUID","Urgency","ROM Cost","Sensitivity","Created Timestamp","Updated Timestamp","Source System"],rows)


@app.get("/exports/projects.csv")
def export_projects(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows=[]
    for p in scoped_projects(db,user).order_by(Project.human_id).all(): rows.append([p.human_id,p.title,p.status,p.health_override or p.health_owner,p.lead_org_id,p.mission_id,p.percent_complete,float(p.budget),float(p.actual),float(p.forecast),p.updated_at.isoformat()])
    return csv_response("ddc5i-projects.csv",["Stable ID","Title","Status","Effective Health","Lead Organization UUID","Mission UUID","Percent Complete","Budget","Actual","Forecast","Updated Timestamp"],rows)


@app.get("/imports", response_class=HTMLResponse)
def imports_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user,"ADMIN","PMO","DIVISION_PORTFOLIO_MANAGER","DATA_STEWARD"); batches=db.query(ImportBatch).order_by(ImportBatch.created_at.desc()).limit(20).all(); return render(request,"imports.html",user,db,batches=batches)


@app.post("/imports")
async def import_upload(request: Request, csrf: str = Form(...), template_type: str = Form("Demands"), file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"ADMIN","PMO","DIVISION_PORTFOLIO_MANAGER","DATA_STEWARD")
    if not file.filename or not file.filename.lower().endswith(".xlsx"): return flash_redirect("/imports","Only .xlsx files are accepted.","error")
    content=await file.read()
    if len(content)>settings.max_upload_mb*1024*1024: return flash_redirect("/imports",f"File exceeds {settings.max_upload_mb} MB limit.","error")
    try: rows=read_first_sheet_xlsx(content)
    except Exception as e: return flash_redirect("/imports",f"Unable to read workbook: {e}","error")
    validators = {
        "Demands": validate_demand_rows,
        "Travel Requests": validate_travel_request_rows,
        "Trip Reports": validate_trip_report_rows,
    }
    validator = validators.get(template_type)
    if not validator:
        return flash_redirect("/imports", "Unsupported import template type.", "error")
    results,summary=validator(db,rows,user)
    batch=ImportBatch(filename=os.path.basename(file.filename),template_type=template_type,status="Preview",uploaded_by_id=user.id,rows_json=results,summary_json=summary)
    db.add(batch); db.flush()
    for r in results: db.add(ImportRow(batch_id=batch.id,row_number=r["row_number"],record_identifier=r["record_identifier"],action_taken=r["action"],severity=r["severity"],validation_message=r["message"],corrective_guidance=r["guidance"]))
    record_audit(db,user.id,"ImportBatch",batch.id,"PREVIEW",after={"filename":batch.filename,"summary":summary}); db.commit(); return RedirectResponse(f"/imports/{batch.id}",status_code=303)


@app.get("/imports/{batch_id}", response_class=HTMLResponse)
def import_preview(batch_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user,"ADMIN","PMO","DIVISION_PORTFOLIO_MANAGER","DATA_STEWARD"); batch=db.get(ImportBatch,batch_id)
    if not batch: raise HTTPException(404,"Import batch not found")
    if batch.uploaded_by_id!=user.id and not is_enterprise_user(user): raise HTTPException(403,"Cannot view another user's batch")
    rows=db.query(ImportRow).filter(ImportRow.batch_id==batch.id).order_by(ImportRow.row_number).all(); return render(request,"import_preview.html",user,db,batch=batch,rows=rows)


@app.post("/imports/{batch_id}/commit")
def import_commit(batch_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"ADMIN","PMO","DIVISION_PORTFOLIO_MANAGER","DATA_STEWARD"); batch=db.get(ImportBatch,batch_id)
    if not batch or batch.status!="Preview": return flash_redirect("/imports","Batch is not available for commit.","error")
    if batch.uploaded_by_id != user.id and not is_enterprise_user(user):
        raise HTTPException(403, "Cannot commit another user's batch")
    committed=0
    for result in batch.rows_json:
        if result["severity"]=="Error":
            continue
        if batch.template_type == "Travel Requests":
            item, action = commit_travel_request_result(db, result, source_filename=batch.filename, import_batch_id=batch.id)
            record_audit(db, user.id, "TravelRequest", item.id, action, after=snapshot(item))
        elif batch.template_type == "Trip Reports":
            item, action, candidates = commit_trip_report_result(db, result, source_filename=batch.filename, import_batch_id=batch.id, actor_id=user.id)
            record_audit(db, user.id, "TripReport", item.id, action, after={**snapshot(item), "match_candidates": candidates[:3]})
        else:
            data=result["data"]; rid=data.get("Human ID") or next_human_id(db,Demand,"DMD"); d=db.query(Demand).filter(Demand.human_id==rid).first(); before=snapshot(d) if d else None
            if not d:
                d=Demand(human_id=rid,title=data["Title"],category=data.get("Category") or "Idea",status=data.get("Status") or "Draft",lead_org_id=data["_org_id"],requesting_org_id=data["_org_id"],mission_id=data["_mission_id"],sponsor_id=user.id,requester_id=user.id,current_owner_id=user.id); db.add(d); db.flush(); action="IMPORT_CREATE"
            else: action="IMPORT_UPDATE"
            d.title=data["Title"]; d.category=data.get("Category") or d.category; d.status=data.get("Status") or d.status; d.lead_org_id=data["_org_id"]; d.requesting_org_id=data["_org_id"]; d.mission_id=data["_mission_id"]; d.purpose=data.get("Purpose") or "Imported demand"; d.problem=data.get("Problem or Opportunity") or "Imported problem statement pending refinement"; d.desired_end_state=data.get("Desired End State") or "Imported desired end state pending refinement"; d.urgency=data.get("Urgency") or "Normal"; d.rom_cost=data["_rom"]; d.expected_benefits=data.get("Expected Benefits") or ""; d.sensitivity=data.get("Sensitivity") or "Controlled Unclassified"; d.next_action=demand_next_action(d.status); d.source_system="Excel Import"; d.source_record=f"{batch.id}:{result['row_number']}"; record_audit(db,user.id,"Demand",d.id,action,before=before,after=snapshot(d))
        committed+=1
    if batch.template_type in {"Travel Requests", "Trip Reports"}:
        refresh_engagement_rollups(db)
    batch.status="Committed"; record_audit(db,user.id,"ImportBatch",batch.id,"COMMIT",after={"committed":committed,"summary":batch.summary_json,"template_type":batch.template_type}); db.commit(); return flash_redirect(f"/imports/{batch.id}",f"Committed {committed} valid rows. Errors remained excluded.")


@app.get("/imports/{batch_id}/corrections.xlsx")
def import_correction(batch_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user,"ADMIN","PMO","DIVISION_PORTFOLIO_MANAGER","DATA_STEWARD")
    batch=db.get(ImportBatch,batch_id)
    if not batch: raise HTTPException(404,"Import batch not found")
    if batch.uploaded_by_id != user.id and not is_enterprise_user(user):
        raise HTTPException(403, "Cannot download another user's correction file")
    output=io.BytesIO(); workbook=xlsxwriter.Workbook(output,{"in_memory":True,"strings_to_formulas":False,"strings_to_urls":False}); ws=workbook.add_worksheet("Corrections"); headers=["Row","Record Identifier","Action","Severity","Validation Message","Corrective Guidance"]; header_fmt=workbook.add_format({"bold":True,"bg_color":"#1D4ED8","font_color":"#FFFFFF","border":1})
    for c,h in enumerate(headers): ws.write(0,c,h,header_fmt)
    errors=[r for r in batch.rows_json if r["severity"] in {"Error","Warning"}]
    for i,r in enumerate(errors,1): ws.write_row(i,0,[r["row_number"],r["record_identifier"],r["action"],r["severity"],r["message"],r["guidance"]])
    ws.set_column(0,3,18); ws.set_column(4,5,55); workbook.close(); output.seek(0)
    return StreamingResponse(output,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":f'attachment; filename="corrections-{batch.id[:8]}.xlsx"'})


@app.get("/requirements", response_class=HTMLResponse)
def requirements_page(request: Request, q: str = "", domain: str = "", phase: str = "", status: str = "", fit: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user,"ADMIN","PMO","DATA_STEWARD","AUDITOR","ENTERPRISE_PORTFOLIO_OWNER","SENIOR_LEADER"); query=db.query(RequirementTrace)
    if q: query=query.filter(or_(RequirementTrace.requirement_id.ilike(f"%{q}%"),RequirementTrace.title.ilike(f"%{q}%"),RequirementTrace.requirement.ilike(f"%{q}%")))
    if domain: query=query.filter(RequirementTrace.domain==domain)
    if phase: query=query.filter(RequirementTrace.phase==phase)
    if status: query=query.filter(RequirementTrace.implementation_status==status)
    if fit: query=query.filter(RequirementTrace.preliminary_fit==fit)
    reqs=query.order_by(RequirementTrace.requirement_id).all(); domains=[x[0] for x in db.query(RequirementTrace.domain).distinct().order_by(RequirementTrace.domain).all()]; statuses=[x[0] for x in db.query(RequirementTrace.implementation_status).distinct().order_by(RequirementTrace.implementation_status).all()]; fits=[x[0] for x in db.query(RequirementTrace.preliminary_fit).distinct().order_by(RequirementTrace.preliminary_fit).all()]; summary=dict(db.query(RequirementTrace.implementation_status,func.count(RequirementTrace.id)).group_by(RequirementTrace.implementation_status).all())
    return render(request,"requirements.html",user,db,requirements=reqs,domains=domains,statuses=statuses,fits=fits,summary=summary,q=q,domain=domain,phase=phase,status=status,fit=fit)


@app.post("/requirements/{req_id}/status")
def requirement_status(req_id: str, request: Request, csrf: str = Form(...), implementation_status: str = Form(...), design_reference: str = Form(""), test_case: str = Form(""), release: str = Form(""), acceptance_notes: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"ADMIN","PMO","DATA_STEWARD"); req=db.query(RequirementTrace).filter(RequirementTrace.requirement_id==req_id).first()
    if not req: raise HTTPException(404,"Requirement not found")
    before=snapshot(req); req.implementation_status=implementation_status; req.design_reference=design_reference; req.test_case=test_case; req.release=release; req.acceptance_notes=acceptance_notes; record_audit(db,user.id,"RequirementTrace",req.id,"UPDATE",before=before,after=snapshot(req)); db.commit(); return flash_redirect(f"/requirements?q={req_id}",f"{req_id} traceability updated.")


@app.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request, entity_type: str = "", q: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user,"AUDITOR","ADMIN","SECURITY_REVIEWER","PMO"); query=db.query(AuditEvent)
    if entity_type: query=query.filter(AuditEvent.entity_type==entity_type)
    if q: query=query.filter(or_(AuditEvent.entity_id.ilike(f"%{q}%"),AuditEvent.action.ilike(f"%{q}%")))
    events=query.order_by(AuditEvent.created_at.desc()).limit(500).all(); users={u.id:u for u in db.query(User).all()}; types=[x[0] for x in db.query(AuditEvent.entity_type).distinct().order_by(AuditEvent.entity_type).all()]
    return render(request,"audit.html",user,db,events=events,users_map=users,types=types,entity_type=entity_type,q=q)


@app.post("/views/save")
def save_view(request: Request, csrf: str = Form(...), name: str = Form(...), route: str = Form(...), query_string: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); existing=db.query(SavedView).filter(SavedView.user_id==user.id,SavedView.name==name).first()
    if existing: existing.route=route; existing.query_string=query_string
    else: db.add(SavedView(user_id=user.id,name=name,route=route,query_string=query_string))
    db.commit(); return flash_redirect(f"{route}?{query_string}" if query_string else route,f"Saved view '{name}'.")


def _search_rank(query: str, identifier: str, title: str, body: str = "") -> int:
    needle = query.casefold().strip()
    identifier_l = (identifier or "").casefold()
    title_l = (title or "").casefold()
    body_l = (body or "").casefold()
    if needle == identifier_l:
        return 100
    if needle == title_l:
        return 95
    if identifier_l.startswith(needle):
        return 90
    if title_l.startswith(needle):
        return 80
    if needle in title_l:
        return 70
    if needle in body_l:
        return 50
    return 10


def _snippet(*values: str, max_length: int = 180) -> str:
    value = next((str(v).strip() for v in values if v and str(v).strip()), "")
    return value if len(value) <= max_length else value[: max_length - 1].rstrip() + "…"


def build_search_results(db: Session, user: User, q: str, limit: int = 80) -> list[dict[str, Any]]:
    query = q.strip()[:160]
    if not query:
        return []
    pattern = f"%{query}%"
    results: list[dict[str, Any]] = []

    def add(kind: str, identifier: str, title: str, url: str, subtitle: str = "", snippet: str = "", badge: str = "") -> None:
        results.append({
            "kind": kind,
            "identifier": identifier,
            "title": title,
            "url": url,
            "subtitle": subtitle,
            "snippet": snippet,
            "badge": badge,
            "score": _search_rank(query, identifier, title, f"{subtitle} {snippet}"),
        })

    for d in scoped_demands(db, user).filter(or_(
        Demand.human_id.ilike(pattern), Demand.title.ilike(pattern), Demand.purpose.ilike(pattern),
        Demand.problem.ilike(pattern), Demand.desired_end_state.ilike(pattern), Demand.beneficiaries.ilike(pattern),
        Demand.expected_benefits.ilike(pattern), Demand.required_skills.ilike(pattern),
    )).limit(30).all():
        add("Demand", d.human_id, d.title, f"/demands/{d.id}", f"{d.status} · {d.category}", _snippet(d.problem, d.purpose, d.desired_end_state), d.status)

    project_query = scoped_projects(db, user).filter(or_(
        Project.human_id.ilike(pattern), Project.title.ilike(pattern), Project.description.ilike(pattern),
        Project.desired_end_state.ilike(pattern), Project.scope.ilike(pattern), Project.deliverables.ilike(pattern),
    )).limit(30)
    for project in project_query.all():
        add("Project", project.human_id, project.title, f"/projects/{project.id}", f"{project.status} · {project.health_override or project.health_owner}", _snippet(project.description, project.scope), project.health_override or project.health_owner)

    travel_query = scoped_travel_requests(db, user).filter(or_(
        TravelRequest.human_id.ilike(pattern), TravelRequest.external_id.ilike(pattern), TravelRequest.traveler_name.ilike(pattern),
        TravelRequest.location.ilike(pattern), TravelRequest.purpose_roi.ilike(pattern), TravelRequest.impact_if_not.ilike(pattern),
    ))
    for item in travel_query.limit(30).all():
        engagement = db.get(TravelEngagement, item.engagement_id) if item.engagement_id else None
        add("Travel Request", item.human_id, engagement.title if engagement else item.location, f"/travel/requests/{item.id}", f"{item.traveler_name} · {item.determination}", _snippet(item.location, item.purpose_roi, item.impact_if_not), item.determination)

    report_query = scoped_trip_reports(db, user).filter(or_(
        TripReport.human_id.ilike(pattern), TripReport.title.ilike(pattern), TripReport.traveler_name.ilike(pattern), TripReport.location.ilike(pattern),
        TripReport.purpose_objectives.ilike(pattern), TripReport.discussion.ilike(pattern), TripReport.key_findings.ilike(pattern), TripReport.recommendations.ilike(pattern), TripReport.action_items.ilike(pattern),
    ))
    for item in report_query.limit(30).all():
        add("Trip Report", item.human_id, item.title, f"/travel/reports/{item.id}", f"{item.traveler_name} · {item.review_status}", _snippet(item.key_findings, item.recommendations, item.action_items), item.review_status)

    task_query = db.query(Task, Project).join(Project, Task.project_id == Project.id).filter(or_(
        Task.human_id.ilike(pattern), Task.title.ilike(pattern), Task.description.ilike(pattern),
        Task.notes.ilike(pattern), Task.acceptance_evidence.ilike(pattern), cast(Task.tags, String).ilike(pattern),
    ))
    task_query = scope_project_join(task_query, user)
    for task, project in task_query.limit(35).all():
        add("Task", task.human_id, task.title, task_return_path(project.id, task.id), f"{project.human_id} · {task.status} · {task.priority}", _snippet(task.description, task.notes, task.acceptance_evidence), task.priority)

    related_specs = [
        (Milestone, "Milestone", Milestone.project_id, [Milestone.human_id, Milestone.title], lambda item, project: f"/records/milestone/{item.id}", lambda item: f"{item.status} · Confidence {item.confidence}", lambda item: item.title),
        (RaidItem, "RAID", RaidItem.project_id, [RaidItem.human_id, RaidItem.title, RaidItem.description, RaidItem.mitigation], lambda item, project: f"/records/raid/{item.id}", lambda item: f"{item.type} · {item.status} · {item.severity}", lambda item: _snippet(item.description, item.mitigation)),
    ]
    for model, kind, project_fk, fields, url_fn, subtitle_fn, snippet_fn in related_specs:
        clauses = [field.ilike(pattern) for field in fields]
        rq = db.query(model, Project).join(Project, project_fk == Project.id).filter(or_(*clauses))
        rq = scope_project_join(rq, user)
        for item, project in rq.limit(20).all():
            add(kind, item.human_id, item.title, url_fn(item, project), f"{project.human_id} · {subtitle_fn(item)}", snippet_fn(item), getattr(item, "status", ""))

    dep_query = db.query(Dependency, Project).join(Project, Dependency.source_project_id == Project.id).filter(or_(Dependency.human_id.ilike(pattern), Dependency.title.ilike(pattern), Dependency.impact.ilike(pattern), Dependency.external_party.ilike(pattern)))
    dep_query = scope_project_join(dep_query, user)
    for item, project in dep_query.limit(20).all():
        add("Dependency", item.human_id, item.title, f"/records/dependency/{item.id}", f"{project.human_id} · {item.status}", _snippet(item.impact, item.external_party), item.status)

    decision_query = db.query(Decision).filter(or_(Decision.human_id.ilike(pattern), Decision.decision.ilike(pattern), Decision.rationale.ilike(pattern), Decision.evidence.ilike(pattern), Decision.conditions.ilike(pattern)))
    for item in decision_query.limit(20).all():
        accessible = False
        if item.project_id:
            project = db.get(Project, item.project_id)
            accessible = bool(project and can_access_org(user, project.lead_org_id))
        elif item.demand_id:
            demand = db.get(Demand, item.demand_id)
            accessible = bool(demand and can_access_org(user, demand.lead_org_id) and can_access_sensitive(user, demand.sensitivity))
        if accessible:
            add("Decision", item.human_id, item.decision, f"/records/decision/{item.id}", "Leadership decision", _snippet(item.rationale, item.evidence, item.conditions), item.decision)

    mission_query = db.query(Mission).filter(or_(Mission.code.ilike(pattern), Mission.title.ilike(pattern), Mission.description.ilike(pattern), Mission.outcome.ilike(pattern)))
    if not is_enterprise_user(user):
        mission_query = mission_query.filter(Mission.owner_org_id == user.division_id)
    for item in mission_query.limit(20).all():
        add("Mission", item.code, item.title, "/strategy", item.status, _snippet(item.description, item.outcome), item.status)

    function_query = db.query(CoreFunction).filter(or_(CoreFunction.code.ilike(pattern), CoreFunction.title.ilike(pattern), CoreFunction.description.ilike(pattern)))
    if not is_enterprise_user(user):
        function_query = function_query.filter(CoreFunction.org_id == user.division_id)
    for item in function_query.limit(20).all():
        owner_org = db.get(Organization, item.org_id)
        add("Core Function", item.code, item.title, f"/divisions/{owner_org.code}" if owner_org else "/divisions", item.health, _snippet(item.description), item.health)

    org_query = db.query(Organization).filter(Organization.active.is_(True), or_(Organization.code.ilike(pattern), Organization.name.ilike(pattern), Organization.narrative.ilike(pattern)))
    if not is_enterprise_user(user):
        org_query = org_query.filter(Organization.id == user.division_id)
    for item in org_query.limit(15).all():
        url = "/divisions" if item.org_type != "Division" else f"/divisions/{item.code}"
        add("Organization", item.code, item.name, url, item.org_type, _snippet(item.narrative), item.org_type)

    if has_role(user, "ADMIN", "PMO", "DATA_STEWARD", "AUDITOR", "SENIOR_LEADER", "ENTERPRISE_PORTFOLIO_OWNER"):
        req_query = db.query(RequirementTrace).filter(or_(RequirementTrace.requirement_id.ilike(pattern), RequirementTrace.title.ilike(pattern), RequirementTrace.requirement.ilike(pattern), RequirementTrace.domain.ilike(pattern), RequirementTrace.design_reference.ilike(pattern), RequirementTrace.module_reference.ilike(pattern)))
        for item in req_query.limit(30).all():
            add("Requirement", item.requirement_id, item.title, f"/requirements/{item.requirement_id}", f"{item.domain} · Phase {item.phase}", _snippet(item.requirement), item.implementation_status)

    if has_role(user, "ADMIN", "PMO", "DATA_STEWARD", "AUDITOR", "SENIOR_LEADER", "ENTERPRISE_PORTFOLIO_OWNER", "DIVISION_CHIEF", "DIVISION_PORTFOLIO_MANAGER"):
        review_query = db.query(PortfolioReview).filter(or_(PortfolioReview.human_id.ilike(pattern), PortfolioReview.title.ilike(pattern), PortfolioReview.summary.ilike(pattern), PortfolioReview.decisions_required.ilike(pattern)))
        scenario_query = db.query(Scenario).filter(or_(Scenario.human_id.ilike(pattern), Scenario.name.ilike(pattern), Scenario.assumptions.ilike(pattern), Scenario.scenario_type.ilike(pattern)))
        if not is_enterprise_user(user):
            review_query = review_query.filter(or_(PortfolioReview.org_id == user.division_id, PortfolioReview.org_id.is_(None)))
            scenario_query = scenario_query.filter(or_(Scenario.org_id == user.division_id, Scenario.org_id.is_(None)))
        for item in review_query.limit(20).all():
            add("Portfolio Review", item.human_id, item.title, f"/portfolio-reviews/{item.id}", f"{item.review_type} · {item.status}", _snippet(item.summary, item.decisions_required), item.status)
        for item in scenario_query.limit(20).all():
            add("Scenario", item.human_id, item.name, f"/scenarios/{item.id}", f"{item.scenario_type} · {item.status}", _snippet(item.assumptions), item.status)

    if has_role(user, "ADMIN", "PMO", "DATA_STEWARD", "AUDITOR", "SECURITY_REVIEWER", "SENIOR_LEADER"):
        quality_query = db.query(DataQualityIssue).filter(or_(DataQualityIssue.human_id.ilike(pattern), DataQualityIssue.title.ilike(pattern), DataQualityIssue.description.ilike(pattern), DataQualityIssue.rule_code.ilike(pattern), DataQualityIssue.disposition.ilike(pattern)))
        if not is_enterprise_user(user):
            quality_query = quality_query.filter(or_(DataQualityIssue.org_id == user.division_id, DataQualityIssue.org_id.is_(None)))
        for item in quality_query.limit(20).all():
            add("Data Quality", item.human_id, item.title, "/data-quality", f"{item.rule_code} · {item.status}", _snippet(item.description, item.disposition), item.severity)

    if has_role(user, "ADMIN", "PMO", "DATA_STEWARD", "SENIOR_LEADER", "ENTERPRISE_PORTFOLIO_OWNER"):
        pack_query = db.query(ReportPack).filter(or_(ReportPack.human_id.ilike(pattern), ReportPack.name.ilike(pattern), ReportPack.narrative.ilike(pattern), ReportPack.pack_type.ilike(pattern)))
        if not is_enterprise_user(user):
            pack_query = pack_query.filter(or_(ReportPack.org_id == user.division_id, ReportPack.org_id.is_(None)))
        for item in pack_query.limit(20).all():
            add("Report Pack", item.human_id, item.name, "/operations", f"{item.pack_type} · {item.status}", _snippet(item.narrative), item.status)

    resource_request_query = db.query(ResourceRequest).filter(or_(ResourceRequest.human_id.ilike(pattern), ResourceRequest.role_name.ilike(pattern), ResourceRequest.skill.ilike(pattern), ResourceRequest.rationale.ilike(pattern), ResourceRequest.resolution.ilike(pattern)))
    if not is_enterprise_user(user):
        resource_request_query = resource_request_query.filter(ResourceRequest.org_id == user.division_id)
    for item in resource_request_query.limit(20).all():
        add("Resource Request", item.human_id, item.role_name, "/resources", f"{item.skill} · {item.status}", _snippet(item.rationale, item.resolution), item.priority)

    comment_query = db.query(TaskComment, Task, Project).join(Task, TaskComment.task_id == Task.id).join(Project, Task.project_id == Project.id).filter(TaskComment.body.ilike(pattern))
    comment_query = scope_project_join(comment_query, user)
    for comment, task, project in comment_query.limit(15).all():
        add("Task Comment", task.human_id, task.title, task_return_path(project.id, task.id), f"Comment in {project.human_id}", _snippet(comment.body), "Comment")

    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for result in results:
        key = (result["kind"], result["identifier"], result["url"])
        if key not in deduped or result["score"] > deduped[key]["score"]:
            deduped[key] = result
    return sorted(deduped.values(), key=lambda item: (-item["score"], item["kind"], item["identifier"]))[:limit]


@app.get("/search", response_class=HTMLResponse)
def global_search(request: Request, q: str = "", type: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = q.strip()[:160]
    all_results = build_search_results(db, user, query)
    type_counts = Counter(item["kind"] for item in all_results)
    results = [item for item in all_results if item["kind"] == type] if type else all_results
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        grouped[item["kind"]].append(item)
    types = sorted(type_counts)
    return render(request, "search.html", user, db, q=query, results=results, grouped=grouped, types=types, type_counts=type_counts, selected_type=type, total=len(results), total_all=len(all_results))


@app.get("/api/search/suggest")
def search_suggest(q: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = q.strip()[:160]
    if len(query) < 2:
        return {"results": []}
    return {"results": build_search_results(db, user, query, limit=8)}


@app.get("/administration", response_class=HTMLResponse)
def administration(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user,"ADMIN")
    users=db.query(User).order_by(User.username).all(); org_list=db.query(Organization).order_by(Organization.code).all(); orgs={o.id:o for o in org_list}
    connections=db.query(IntegrationConnection).order_by(IntegrationConnection.name).all(); delegations=db.query(Delegation).order_by(Delegation.created_at.desc()).all()
    counts={"users":db.query(User).count(),"active users":db.query(User).filter(User.is_active.is_(True)).count(),"delegations":db.query(Delegation).filter(Delegation.active.is_(True)).count(),"integrations":db.query(IntegrationConnection).count(),"audit":db.query(AuditEvent).count()}
    runtime={"public_base_url":settings.public_base_url,"trust_proxy_hops":settings.trust_proxy_hops,"rate_limit_requests":settings.rate_limit_requests,"rate_limit_window_seconds":settings.rate_limit_window_seconds,"max_upload_mb":settings.max_upload_mb,"allowed_extensions":sorted(ALLOWED_EXTENSIONS)}
    return render(request,"administration.html",user,db,users=users,orgs_map=orgs,org_list=org_list,connections=connections,delegations=delegations,counts=counts,runtime=runtime,role_catalog=ROLE_CATALOG)



# ---------------------------------------------------------------------------
# v0.5.0 portfolio governance, integration, scenarios, and operations
# ---------------------------------------------------------------------------

ROLE_CATALOG = [
    "SENIOR_LEADER", "ENTERPRISE_PORTFOLIO_OWNER", "PMO", "DIVISION_CHIEF",
    "DIVISION_PORTFOLIO_MANAGER", "REQUESTER", "ASSESSOR", "APPROVAL_AUTHORITY",
    "PROJECT_MANAGER", "TEAM_MEMBER", "RESOURCE_MANAGER", "FINANCIAL_MANAGER",
    "BENEFITS_OWNER", "DATA_STEWARD", "SECURITY_REVIEWER", "AUDITOR", "ADMIN",
]


def _split_values(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,\n]", value or "") if item.strip()]


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _review_access(user: User, review: PortfolioReview) -> bool:
    return is_enterprise_user(user) or review.org_id in {None, user.division_id}


BRIEFING_EDIT_ROLES = {"DIVISION_PORTFOLIO_MANAGER", "DIVISION_CHIEF", "PMO", "ENTERPRISE_PORTFOLIO_OWNER", "ADMIN"}
BRIEFING_APPROVE_ROLES = {"DIVISION_CHIEF", "SENIOR_LEADER", "APPROVAL_AUTHORITY", "ENTERPRISE_PORTFOLIO_OWNER", "PMO", "ADMIN"}
BRIEFING_FACILITATE_ROLES = BRIEFING_APPROVE_ROLES | {"DIVISION_PORTFOLIO_MANAGER"}


def _is_briefing_review(review: PortfolioReview) -> bool:
    return review.review_type in {"Division Briefing", "Division Briefing & Review"}


def _briefing_can_edit(user: User, review: PortfolioReview) -> bool:
    return bool(set(user.roles or []).intersection(BRIEFING_EDIT_ROLES)) and _review_access(user, review) and review.status in {"Draft", "In Preparation"}


def _briefing_can_approve(user: User, review: PortfolioReview) -> bool:
    return bool(set(user.roles or []).intersection(BRIEFING_APPROVE_ROLES)) and _review_access(user, review)


def _briefing_can_facilitate(user: User, review: PortfolioReview) -> bool:
    return bool(set(user.roles or []).intersection(BRIEFING_FACILITATE_ROLES)) and _review_access(user, review)


def _briefing_can_participate(user: User, review: PortfolioReview) -> bool:
    return _review_access(user, review) and set(user.roles or []) != {"AUDITOR"}


def _briefing_readiness(sections: list[BriefingSection]) -> int:
    if not sections:
        return 0
    ready_states = {"Ready for Division Review", "Division Approved", "Ready to Brief"}
    return round(sum(1 for section in sections if section.status in ready_states) / len(sections) * 100)


def _notify_review_assignment(db: Session, user_id: str | None, review: PortfolioReview, title: str, message: str) -> None:
    if user_id:
        db.add(Notification(user_id=user_id, title=title, message=message, link=f"/portfolio-reviews/{review.id}/brief", notification_type="Review Follow-up"))


def _briefing_snapshot(db: Session, review: PortfolioReview, user: User) -> BriefingSnapshot:
    sections, payload = ensure_briefing_sections(db, review, user.id)
    payload["sections"] = [
        {
            "id": section.id,
            "section_key": section.section_key,
            "title": section.title,
            "narrative": section.narrative,
            "owner_id": section.owner_id,
            "status": section.status,
            "source_summary": section.source_summary,
        }
        for section in sections
    ]
    snapshot_record = db.query(BriefingSnapshot).filter_by(review_id=review.id).first()
    if snapshot_record:
        snapshot_record.payload = payload
        snapshot_record.captured_by_id = user.id
        snapshot_record.captured_at = datetime.now(timezone.utc)
    else:
        snapshot_record = BriefingSnapshot(review_id=review.id, payload=payload, captured_by_id=user.id)
        db.add(snapshot_record)
    db.flush()
    return snapshot_record


def _scenario_access(user: User, scenario: Scenario) -> bool:
    return is_enterprise_user(user) or scenario.org_id in {None, user.division_id}


def _scenario_target(db: Session, entity_type: str, entity_id: str, field_name: str):
    allowed = {
        "Project": (Project, {"budget", "forecast", "health_owner", "status", "current_end_date"}),
        "ResourceCapacity": (ResourceCapacity, {"capacity_hours", "allocated_hours"}),
        "FinancialRecord": (FinancialRecord, {"approved_budget", "forecast"}),
    }
    if entity_type not in allowed or field_name not in allowed[entity_type][1]:
        raise HTTPException(status_code=400, detail="Unsupported scenario field")
    record = db.get(allowed[entity_type][0], entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Scenario target not found")
    return record


def _convert_scenario_value(field_name: str, value: str):
    if field_name in {"budget", "forecast", "capacity_hours", "allocated_hours", "approved_budget"}:
        return float(value)
    if field_name == "current_end_date":
        return value or None
    return value


@app.get("/integrations", response_class=HTMLResponse)
def integrations_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "ADMIN", "PMO", "DATA_STEWARD", "AUDITOR")
    connections = db.query(IntegrationConnection).order_by(IntegrationConnection.name).all()
    ownership = db.query(FieldOwnershipRuleRecord).filter(FieldOwnershipRuleRecord.active.is_(True)).order_by(FieldOwnershipRuleRecord.entity_type, FieldOwnershipRuleRecord.field_name).all()
    runs = db.query(SyncRun).order_by(SyncRun.started_at.desc()).limit(50).all()
    projects = scoped_projects(db, user).order_by(Project.human_id).all()
    return render(request, "integrations.html", user, db, connections=connections, ownership=ownership, runs=runs, projects=projects)


@app.post("/integrations")
def create_integration(
    request: Request,
    csrf: str = Form(...), code: str = Form(...), name: str = Form(...), kind: str = Form(...),
    base_url: str = Form(""), mode: str = Form("Mock"), auth_type: str = Form("None"),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN")
    normalized = re.sub(r"[^A-Z0-9_-]", "-", code.upper()).strip("-")
    if not normalized or db.query(IntegrationConnection).filter_by(code=normalized).first():
        return flash_redirect("/integrations", "Integration code is invalid or already exists.", "error")
    connection = IntegrationConnection(code=normalized, name=name.strip(), kind=kind, base_url=base_url.strip(), mode=mode, auth_type=auth_type, enabled=(mode == "Mock"), created_by_id=user.id)
    db.add(connection); db.flush(); record_audit(db, user.id, "IntegrationConnection", connection.id, "CREATE", after=snapshot(connection), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/integrations", f"Integration {connection.name} created.")


@app.post("/integrations/{connection_id}/health")
def integration_health(connection_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN", "PMO", "DATA_STEWARD")
    connection = db.get(IntegrationConnection, connection_id)
    if not connection: raise HTTPException(status_code=404, detail="Integration not found")
    before = snapshot(connection)
    connection.last_health_at = datetime.now(timezone.utc)
    if connection.mode == "Mock":
        connection.status = "Healthy (Mock)"
        message = "Local mock adapter is healthy. No external system was contacted."
    elif not connection.enabled:
        connection.status = "Disabled"
        message = "Connection is disabled."
    elif not connection.base_url.startswith(("https://", "http://")):
        connection.status = "Configuration Error"
        message = "Enabled external connections require an HTTP(S) base URL."
    else:
        connection.status = "Configured — External Test Required"
        message = "Configuration is structurally valid; live authentication and connectivity require the target enterprise environment."
    record_audit(db, user.id, "IntegrationConnection", connection.id, "HEALTH_CHECK", before=before, after=snapshot(connection), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/integrations", message, "success" if "Healthy" in connection.status else "warning")


@app.post("/integrations/{connection_id}/sync")
def integration_sync(
    connection_id: str, request: Request, csrf: str = Form(...), project_id: str = Form(...),
    direction: str = Form("Outbound"), dry_run: str | None = Form(None),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN", "PMO", "DATA_STEWARD")
    connection = db.get(IntegrationConnection, connection_id)
    project = get_accessible_project(db, user, project_id)
    if not connection: raise HTTPException(status_code=404, detail="Integration not found")
    payload = projectos_payload(db, project)
    run = SyncRun(connection_id=connection.id, direction=direction, entity_type="Project", canonical_id=project.id, dry_run=bool(dry_run) or connection.mode != "External", attempt_count=1, payload=payload, created_by_id=user.id)
    if connection.mode == "Mock" or run.dry_run:
        run.status = "Succeeded"
        run.message = "Dry-run payload validated against the ProjectOS canonical contract; no remote write occurred."
        run.result = {"remote_id": f"mock-{project.human_id}", "records": {"projects": 1, "tasks": len(payload["tasks"]), "milestones": len(payload["milestones"])}, "conflicts": []}
    elif not connection.enabled:
        run.status = "Failed"; run.message = "Connection is disabled."; run.result = {"retryable": False}
    else:
        run.status = "Requires External Environment"; run.message = "Live synchronization requires configured credentials and access to the target endpoint."; run.result = {"retryable": True}
    run.completed_at = datetime.now(timezone.utc)
    db.add(run); db.flush(); record_audit(db, user.id, "SyncRun", run.id, "EXECUTE", after=snapshot(run), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/integrations", run.message, "success" if run.status == "Succeeded" else "warning")


@app.post("/integrations/rules")
def integration_rule(
    request: Request, csrf: str = Form(...), entity_type: str = Form(...), field_name: str = Form(...),
    authoritative_system: str = Form(...), allowed_writers: str = Form(...), conflict_policy: str = Form("Reject and reconcile"),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN")
    rule = db.query(FieldOwnershipRuleRecord).filter_by(entity_type=entity_type.strip(), field_name=field_name.strip()).first()
    if rule:
        before = snapshot(rule); rule.authoritative_system = authoritative_system.strip(); rule.allowed_writers = _split_values(allowed_writers); rule.conflict_policy = conflict_policy
        action = "UPDATE"
    else:
        rule = FieldOwnershipRuleRecord(entity_type=entity_type.strip(), field_name=field_name.strip(), authoritative_system=authoritative_system.strip(), allowed_writers=_split_values(allowed_writers), conflict_policy=conflict_policy)
        db.add(rule); db.flush(); before = None; action = "CREATE"
    record_audit(db, user.id, "FieldOwnershipRule", rule.id, action, before=before, after=snapshot(rule), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/integrations", "Field ownership rule saved.")


@app.get("/portfolio-reviews", response_class=HTMLResponse)
def portfolio_reviews_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "SENIOR_LEADER", "ENTERPRISE_PORTFOLIO_OWNER", "PMO", "DIVISION_CHIEF", "DIVISION_PORTFOLIO_MANAGER", "APPROVAL_AUTHORITY", "ADMIN")
    query = db.query(PortfolioReview)
    if not is_enterprise_user(user): query = query.filter(or_(PortfolioReview.org_id == user.division_id, PortfolioReview.org_id.is_(None)))
    reviews = query.order_by(PortfolioReview.period_end.desc(), PortfolioReview.created_at.desc()).all()
    portfolios = db.query(Portfolio).order_by(Portfolio.name).all(); users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    return render(request, "portfolio_reviews.html", user, db, reviews=reviews, portfolios=portfolios, users=users)


@app.post("/portfolio-reviews")
def create_portfolio_review(
    request: Request, csrf: str = Form(...), title: str = Form(...), review_type: str = Form("Portfolio Review"),
    portfolio_id: str = Form(""), org_id: str = Form(""), period_start: str = Form(...), period_end: str = Form(...),
    chair_id: str = Form(...), participant_ids: list[str] = Form([]), summary: str = Form(""), decisions_required: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "SENIOR_LEADER", "ENTERPRISE_PORTFOLIO_OWNER", "PMO", "DIVISION_CHIEF", "DIVISION_PORTFOLIO_MANAGER", "ADMIN")
    scoped_org = org_id or None
    if scoped_org and not can_access_org(user, scoped_org): raise HTTPException(status_code=403, detail="Organization outside permitted scope")
    if review_type in {"Division Briefing", "Division Briefing & Review"} and not scoped_org:
        return flash_redirect("/portfolio-reviews", "A division briefing requires an organization scope.", "error")
    status = "In Preparation" if review_type in {"Division Briefing", "Division Briefing & Review"} else "Draft"
    review = PortfolioReview(human_id=next_human_id(db, PortfolioReview, "REV"), title=title.strip(), review_type=review_type, portfolio_id=portfolio_id or None, org_id=scoped_org, period_start=date.fromisoformat(period_start), period_end=date.fromisoformat(period_end), status=status, chair_id=chair_id, participant_ids=participant_ids, summary=summary, decisions_required=decisions_required)
    db.add(review); db.flush()
    if _is_briefing_review(review):
        ensure_briefing_sections(db, review, user.id)
    record_audit(db, user.id, "PortfolioReview", review.id, "CREATE", after=snapshot(review), ip_address=request.state.client_ip); db.commit()
    return RedirectResponse(f"/portfolio-reviews/{review.id}/brief" if _is_briefing_review(review) else f"/portfolio-reviews/{review.id}", status_code=303)


@app.get("/portfolio-reviews/{review_id}", response_class=HTMLResponse)
def portfolio_review_detail(review_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    review = db.get(PortfolioReview, review_id)
    if not review or not _review_access(user, review): raise HTTPException(status_code=404, detail="Review not found")
    items = db.query(PortfolioReviewItem).filter_by(review_id=review.id).order_by(PortfolioReviewItem.sort_order, PortfolioReviewItem.created_at).all()
    projects = scoped_projects(db, user).order_by(Project.human_id).all(); demands = scoped_demands(db, user).order_by(Demand.human_id).all()
    users = {u.id: u for u in db.query(User).all()}; decisions = {d.id: d for d in db.query(Decision).all()}; actions = {a.id: a for a in db.query(Action).all()}
    return render(request, "portfolio_review_detail.html", user, db, review=review, items=items, projects=projects, demands=demands, users_map=users, decisions_map=decisions, actions_map=actions, audit=record_audit_events(db, review.id))


@app.get("/portfolio-reviews/{review_id}/brief", response_class=HTMLResponse)
def division_briefing_workspace(review_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    review = db.get(PortfolioReview, review_id)
    if not review or not _review_access(user, review) or not _is_briefing_review(review):
        raise HTTPException(status_code=404, detail="Division briefing not found")
    sections, live_payload = ensure_briefing_sections(db, review, user.id)
    db.commit()
    snapshot_record = db.query(BriefingSnapshot).filter_by(review_id=review.id).first()
    display_payload = snapshot_record.payload if snapshot_record and review.status in {"Ready to Brief", "In Review", "Completed"} else live_payload
    questions = db.query(ReviewQuestion).filter_by(review_id=review.id).order_by(ReviewQuestion.status, ReviewQuestion.created_at.desc()).all()
    changes = db.query(ReviewChangeRequest).filter_by(review_id=review.id).order_by(ReviewChangeRequest.status, ReviewChangeRequest.created_at.desc()).all()
    notes = db.query(ReviewNote).filter_by(review_id=review.id).order_by(ReviewNote.created_at.desc()).limit(100).all()
    items = db.query(PortfolioReviewItem).filter_by(review_id=review.id).order_by(PortfolioReviewItem.sort_order, PortfolioReviewItem.created_at).all()
    users = {u.id: u for u in db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()}
    org = db.get(Organization, review.org_id) if review.org_id else None
    section_ref = request.query_params.get("section")
    current_section = next((section for section in sections if section.id == section_ref or section.section_key == section_ref), sections[0] if sections else None)
    frozen_sections = {item.get("id"): item for item in (snapshot_record.payload.get("sections", []) if snapshot_record and review.status in {"Ready to Brief", "In Review", "Completed"} else [])}
    current_content = frozen_sections.get(current_section.id) if current_section else None
    if current_section and not current_content:
        current_content = {
            "id": current_section.id,
            "section_key": current_section.section_key,
            "title": current_section.title,
            "narrative": current_section.narrative,
            "owner_id": current_section.owner_id,
            "status": current_section.status,
            "source_summary": current_section.source_summary,
        }
    audit_ids = [review.id] + [section.id for section in sections] + [question.id for question in questions] + [change.id for change in changes]
    audit = db.query(AuditEvent).filter(AuditEvent.entity_id.in_(audit_ids)).order_by(AuditEvent.created_at.desc()).limit(100).all() if audit_ids else []
    return render(
        request,
        "division_briefing.html",
        user,
        db,
        review=review,
        org=org,
        sections=sections,
        current_section=current_section,
        current_content=current_content,
        payload=display_payload,
        live_payload=live_payload,
        snapshot_record=snapshot_record,
        questions=questions,
        changes=changes,
        notes=notes,
        items=items,
        users_map=users,
        readiness=_briefing_readiness(sections),
        can_edit=_briefing_can_edit(user, review),
        can_approve=_briefing_can_approve(user, review),
        can_facilitate=_briefing_can_facilitate(user, review),
        can_participate=_briefing_can_participate(user, review),
        presentation_mode=request.query_params.get("mode") == "present",
        audit=audit,
    )


@app.post("/portfolio-reviews/{review_id}/briefing/refresh")
def refresh_division_briefing(review_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    review = db.get(PortfolioReview, review_id)
    if not review or not _is_briefing_review(review) or not _briefing_can_edit(user, review):
        raise HTTPException(status_code=404, detail="Division briefing not found")
    sections, _ = ensure_briefing_sections(db, review, user.id)
    record_audit(db, user.id, "PortfolioReview", review.id, "BRIEFING_SOURCE_REFRESH", after={"sections": len(sections)}, ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}/brief", "Source-backed briefing data refreshed.")


@app.post("/portfolio-reviews/{review_id}/briefing/sections/{section_id}")
def update_briefing_section(
    review_id: str,
    section_id: str,
    request: Request,
    csrf: str = Form(...),
    narrative: str = Form(""),
    owner_id: str = Form(""),
    status: str = Form("In Preparation"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    review = db.get(PortfolioReview, review_id)
    section = db.get(BriefingSection, section_id)
    if not review or not section or section.review_id != review.id or not _is_briefing_review(review) or not _briefing_can_edit(user, review):
        raise HTTPException(status_code=404, detail="Briefing section not found")
    allowed_statuses = {"Not Started", "In Preparation", "Ready for Division Review", "Changes Required", "Division Approved", "Ready to Brief"}
    before = snapshot(section)
    section.narrative = narrative.strip()
    section.owner_id = owner_id or None
    section.status = status if status in allowed_statuses else "In Preparation"
    if review.status == "Draft":
        review.status = "In Preparation"
    record_audit(db, user.id, "BriefingSection", section.id, "UPDATE", before=before, after=snapshot(section), ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}/brief?section={section.id}", f"{section.title} updated.")


@app.post("/portfolio-reviews/{review_id}/briefing/lifecycle")
def update_briefing_lifecycle(
    review_id: str,
    request: Request,
    csrf: str = Form(...),
    action: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    review = db.get(PortfolioReview, review_id)
    if not review or not _is_briefing_review(review) or not _review_access(user, review):
        raise HTTPException(status_code=404, detail="Division briefing not found")
    sections, _ = ensure_briefing_sections(db, review, user.id)
    before = snapshot(review)
    if action == "submit":
        if not _briefing_can_edit(user, review):
            raise HTTPException(status_code=403, detail="Insufficient briefing permissions")
        if _briefing_readiness(sections) < 100:
            return flash_redirect(f"/portfolio-reviews/{review.id}/brief", "All sections must be marked Ready for Division Review before submission.", "error")
        review.status = "Ready for Division Review"
        message = "Division briefing submitted for approval."
    elif action == "approve":
        if not _briefing_can_approve(user, review):
            raise HTTPException(status_code=403, detail="Insufficient briefing approval permissions")
        if review.status != "Ready for Division Review" or _briefing_readiness(sections) < 100:
            return flash_redirect(f"/portfolio-reviews/{review.id}/brief", "Submit all ready sections for division review before approval.", "error")
        for section in sections:
            section.status = "Division Approved"
        review.status = "Ready to Brief"
        _briefing_snapshot(db, review, user)
        message = "Division briefing approved and presentation snapshot captured."
    elif action == "start":
        if not _briefing_can_facilitate(user, review):
            raise HTTPException(status_code=403, detail="Insufficient facilitation permissions")
        if review.status not in {"Ready to Brief", "In Review"}:
            return flash_redirect(f"/portfolio-reviews/{review.id}/brief", "Approve the division briefing before starting the live review.", "error")
        if not db.query(BriefingSnapshot).filter_by(review_id=review.id).first():
            _briefing_snapshot(db, review, user)
        review.status = "In Review"
        message = "Live leadership review started."
    elif action == "return":
        if not _briefing_can_approve(user, review):
            raise HTTPException(status_code=403, detail="Insufficient briefing approval permissions")
        review.status = "In Preparation"
        for section in sections:
            if section.status in {"Division Approved", "Ready to Brief"}:
                section.status = "Changes Required"
        message = "Briefing returned for changes."
    else:
        raise HTTPException(status_code=400, detail="Unsupported briefing lifecycle action")
    record_audit(db, user.id, "PortfolioReview", review.id, f"BRIEFING_{action.upper()}", before=before, after=snapshot(review), ip_address=request.state.client_ip)
    db.commit()
    suffix = "?mode=present" if action == "start" else ""
    return flash_redirect(f"/portfolio-reviews/{review.id}/brief{suffix}", message)


@app.post("/portfolio-reviews/{review_id}/briefing/questions")
def create_review_question(
    review_id: str,
    request: Request,
    csrf: str = Form(...),
    section_id: str = Form(""),
    entity_type: str = Form(""),
    entity_id: str = Form(""),
    question: str = Form(...),
    assigned_to_id: str = Form(""),
    priority: str = Form("Normal"),
    due_date: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    review = db.get(PortfolioReview, review_id)
    if not review or not _is_briefing_review(review) or not _review_access(user, review) or review.status == "Completed":
        raise HTTPException(status_code=404, detail="Division briefing not found")
    if not _briefing_can_participate(user, review):
        raise HTTPException(status_code=403, detail="This role has read-only briefing access")
    text = question.strip()
    if not text:
        return flash_redirect(f"/portfolio-reviews/{review.id}/brief", "Question text is required.", "error")
    assignee = assigned_to_id or review.chair_id
    record = ReviewQuestion(
        human_id=next_human_id(db, ReviewQuestion, "QUE"),
        review_id=review.id,
        section_id=section_id or None,
        entity_type=entity_type.strip(),
        entity_id=entity_id.strip(),
        question=text,
        asked_by_id=user.id,
        assigned_to_id=assignee or None,
        priority=priority if priority in {"Low", "Normal", "High", "Critical"} else "Normal",
        due_date=parse_optional_date(due_date),
    )
    db.add(record); db.flush()
    _notify_review_assignment(db, record.assigned_to_id, review, f"Briefing question {record.human_id}", f"{user.full_name} assigned a question during {review.title}.")
    record_audit(db, user.id, "ReviewQuestion", record.id, "CREATE", after=snapshot(record), ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}/brief?section={section_id}", f"Question {record.human_id} recorded.")


@app.post("/portfolio-reviews/{review_id}/briefing/questions/{question_id}/respond")
def respond_review_question(
    review_id: str,
    question_id: str,
    request: Request,
    csrf: str = Form(...),
    response: str = Form(...),
    status: str = Form("Answered"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    review = db.get(PortfolioReview, review_id)
    question_record = db.get(ReviewQuestion, question_id)
    if not review or not question_record or question_record.review_id != review.id or not _review_access(user, review):
        raise HTTPException(status_code=404, detail="Review question not found")
    if not _briefing_can_participate(user, review):
        raise HTTPException(status_code=403, detail="This role has read-only briefing access")
    if user.id != question_record.assigned_to_id and not _briefing_can_facilitate(user, review) and not _briefing_can_edit(user, review):
        raise HTTPException(status_code=403, detail="Question is assigned to another user")
    before = snapshot(question_record)
    question_record.response = response.strip()
    question_record.status = status if status in {"Open", "Answered", "Closed"} else "Answered"
    question_record.answered_at = datetime.now(timezone.utc) if question_record.status in {"Answered", "Closed"} else None
    record_audit(db, user.id, "ReviewQuestion", question_record.id, "RESPOND", before=before, after=snapshot(question_record), ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}/brief?section={question_record.section_id or ''}", f"Question {question_record.human_id} updated.")


@app.post("/portfolio-reviews/{review_id}/briefing/change-requests")
def create_review_change_request(
    review_id: str,
    request: Request,
    csrf: str = Form(...),
    section_id: str = Form(""),
    entity_type: str = Form(""),
    entity_id: str = Form(""),
    field_name: str = Form(""),
    current_value: str = Form(""),
    proposed_value: str = Form(""),
    rationale: str = Form(...),
    owner_id: str = Form(""),
    due_date: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    review = db.get(PortfolioReview, review_id)
    if not review or not _is_briefing_review(review) or not _review_access(user, review) or review.status == "Completed":
        raise HTTPException(status_code=404, detail="Division briefing not found")
    if not _briefing_can_participate(user, review):
        raise HTTPException(status_code=403, detail="This role has read-only briefing access")
    if not rationale.strip():
        return flash_redirect(f"/portfolio-reviews/{review.id}/brief", "A change-request rationale is required.", "error")
    assigned_owner = owner_id or review.chair_id
    change = ReviewChangeRequest(
        human_id=next_human_id(db, ReviewChangeRequest, "CHG"),
        review_id=review.id,
        section_id=section_id or None,
        entity_type=entity_type.strip(),
        entity_id=entity_id.strip(),
        field_name=field_name.strip(),
        current_value=current_value.strip(),
        proposed_value=proposed_value.strip(),
        rationale=rationale.strip(),
        requested_by_id=user.id,
        owner_id=assigned_owner or None,
        due_date=parse_optional_date(due_date),
    )
    db.add(change); db.flush()
    _notify_review_assignment(db, change.owner_id, review, f"Briefing change request {change.human_id}", f"{user.full_name} requested a governed source-record change during {review.title}.")
    record_audit(db, user.id, "ReviewChangeRequest", change.id, "CREATE", after=snapshot(change), ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}/brief?section={section_id}", f"Change request {change.human_id} recorded.")


@app.post("/portfolio-reviews/{review_id}/briefing/change-requests/{change_id}/resolve")
def resolve_review_change_request(
    review_id: str,
    change_id: str,
    request: Request,
    csrf: str = Form(...),
    status: str = Form(...),
    resolution: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    review = db.get(PortfolioReview, review_id)
    change = db.get(ReviewChangeRequest, change_id)
    if not review or not change or change.review_id != review.id or not _review_access(user, review):
        raise HTTPException(status_code=404, detail="Review change request not found")
    if not _briefing_can_participate(user, review):
        raise HTTPException(status_code=403, detail="This role has read-only briefing access")
    if user.id != change.owner_id and not _briefing_can_edit(user, review) and not _briefing_can_facilitate(user, review):
        raise HTTPException(status_code=403, detail="Change request is assigned to another user")
    allowed = {"Open", "Accepted", "Partially Accepted", "Rejected", "Clarification Required", "Applied", "Closed"}
    before = snapshot(change)
    change.status = status if status in allowed else "Open"
    change.resolution = resolution.strip()
    change.resolved_at = datetime.now(timezone.utc) if change.status not in {"Open", "Clarification Required"} else None
    record_audit(db, user.id, "ReviewChangeRequest", change.id, "RESOLVE", before=before, after=snapshot(change), ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}/brief?section={change.section_id or ''}", f"Change request {change.human_id} updated.")


@app.post("/portfolio-reviews/{review_id}/briefing/notes")
def create_review_note(
    review_id: str,
    request: Request,
    csrf: str = Form(...),
    section_id: str = Form(""),
    note_type: str = Form("Discussion"),
    body: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    review = db.get(PortfolioReview, review_id)
    if not review or not _is_briefing_review(review) or not _review_access(user, review) or review.status == "Completed":
        raise HTTPException(status_code=404, detail="Division briefing not found")
    if not _briefing_can_participate(user, review):
        raise HTTPException(status_code=403, detail="This role has read-only briefing access")
    if not body.strip():
        return flash_redirect(f"/portfolio-reviews/{review.id}/brief", "A review note cannot be empty.", "error")
    note = ReviewNote(review_id=review.id, section_id=section_id or None, note_type=note_type if note_type in {"Discussion", "Parking Lot", "Clarification", "Observation"} else "Discussion", body=body.strip(), author_id=user.id)
    db.add(note); db.flush()
    record_audit(db, user.id, "ReviewNote", note.id, "CREATE", after=snapshot(note), ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}/brief?section={section_id}", "Review note recorded.")


@app.post("/portfolio-reviews/{review_id}/briefing/actions")
def create_briefing_action(
    review_id: str,
    request: Request,
    csrf: str = Form(...),
    title: str = Form(...),
    owner_id: str = Form(...),
    due_date: str = Form(""),
    entity_type: str = Form(""),
    entity_id: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_csrf(request, user, csrf)
    review = db.get(PortfolioReview, review_id)
    if not review or not _is_briefing_review(review) or not _briefing_can_facilitate(user, review):
        raise HTTPException(status_code=404, detail="Division briefing not found")
    project_id = entity_id if entity_type == "Project" else None
    demand_id = entity_id if entity_type == "Demand" else None
    action_record = Action(human_id=next_human_id(db, Action, "ACT"), project_id=project_id, demand_id=demand_id, title=title.strip(), owner_id=owner_id, due_date=parse_optional_date(due_date), source_type=f"Division briefing {review.human_id}")
    db.add(action_record); db.flush()
    _notify_review_assignment(db, owner_id, review, f"Briefing action {action_record.human_id}", f"{user.full_name} assigned an action during {review.title}.")
    record_audit(db, user.id, "Action", action_record.id, "CREATE_FROM_BRIEFING", after=snapshot(action_record), ip_address=request.state.client_ip)
    db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}/brief", f"Action {action_record.human_id} assigned.")


@app.post("/portfolio-reviews/{review_id}/items")
def add_review_item(
    review_id: str, request: Request, csrf: str = Form(...), item_type: str = Form("Decision"), entity_type: str = Form("Project"),
    entity_id: str = Form(""), title: str = Form(...), recommendation: str = Form("Continue"), rationale: str = Form(""), owner_id: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_business_edit(user)
    review = db.get(PortfolioReview, review_id)
    if not review or not _review_access(user, review): raise HTTPException(status_code=404, detail="Review not found")
    item = PortfolioReviewItem(review_id=review.id, item_type=item_type, entity_type=entity_type, entity_id=entity_id, title=title.strip(), recommendation=recommendation, rationale=rationale, owner_id=owner_id or None, sort_order=db.query(PortfolioReviewItem).filter_by(review_id=review.id).count()+1)
    db.add(item); db.flush(); record_audit(db, user.id, "PortfolioReviewItem", item.id, "CREATE", after=snapshot(item), ip_address=request.state.client_ip); db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}", "Review item added.")


@app.post("/portfolio-reviews/{review_id}/items/{item_id}/decide")
def decide_review_item(
    review_id: str, item_id: str, request: Request, csrf: str = Form(...), decision: str = Form(...),
    rationale: str = Form(...), conditions: str = Form(""), action_title: str = Form(""), action_due_date: str = Form(""), action_owner_id: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "SENIOR_LEADER", "APPROVAL_AUTHORITY", "ENTERPRISE_PORTFOLIO_OWNER", "PMO", "ADMIN")
    review = db.get(PortfolioReview, review_id); item = db.get(PortfolioReviewItem, item_id)
    if not review or not item or item.review_id != review.id or not _review_access(user, review): raise HTTPException(status_code=404, detail="Review item not found")
    project_id = item.entity_id if item.entity_type == "Project" else None; demand_id = item.entity_id if item.entity_type == "Demand" else None
    decision_record = Decision(human_id=next_human_id(db, Decision, "DEC"), project_id=project_id, demand_id=demand_id, decision=decision, authority_id=user.id, participants=", ".join([db.get(User, uid).full_name for uid in review.participant_ids if db.get(User, uid)]), rationale=rationale, evidence=f"Portfolio review {review.human_id}", conditions=conditions)
    db.add(decision_record); db.flush(); item.decision_id = decision_record.id; item.status = "Decided"
    if action_title:
        owner = action_owner_id or item.owner_id or user.id
        action = Action(human_id=next_human_id(db, Action, "ACT"), project_id=project_id, demand_id=demand_id, decision_id=decision_record.id, title=action_title, owner_id=owner, due_date=parse_optional_date(action_due_date), source_type="Portfolio review decision")
        db.add(action); db.flush(); item.action_id = action.id
    record_audit(db, user.id, "PortfolioReviewItem", item.id, "DECIDE", after=snapshot(item), ip_address=request.state.client_ip); db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}", "Decision and follow-up evidence recorded.")


@app.post("/portfolio-reviews/{review_id}/complete")
def complete_review(review_id: str, request: Request, csrf: str = Form(...), summary: str = Form(""), acknowledge_open_items: str | None = Form(None), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "SENIOR_LEADER", "APPROVAL_AUTHORITY", "ENTERPRISE_PORTFOLIO_OWNER", "PMO", "ADMIN")
    review = db.get(PortfolioReview, review_id)
    if not review or not _review_access(user, review): raise HTTPException(status_code=404, detail="Review not found")
    if _is_briefing_review(review):
        open_questions = db.query(ReviewQuestion).filter(ReviewQuestion.review_id == review.id, ReviewQuestion.status == "Open").count()
        open_changes = db.query(ReviewChangeRequest).filter(ReviewChangeRequest.review_id == review.id, ReviewChangeRequest.status.in_(["Open", "Clarification Required"])).count()
        if (open_questions or open_changes) and not acknowledge_open_items:
            return flash_redirect(f"/portfolio-reviews/{review.id}/brief", f"Acknowledge {open_questions} open questions and {open_changes} open change requests before completing the review.", "error")
    before = snapshot(review); review.status = "Completed"; review.completed_at = datetime.now(timezone.utc); review.summary = summary or review.summary
    record_audit(db, user.id, "PortfolioReview", review.id, "COMPLETE", before=before, after=snapshot(review), ip_address=request.state.client_ip); db.commit()
    target = f"/portfolio-reviews/{review.id}/brief" if _is_briefing_review(review) else f"/portfolio-reviews/{review.id}"
    return flash_redirect(target, "Portfolio review completed.")


@app.post("/resources/requests")
def create_resource_request(
    request: Request, csrf: str = Form(...), org_id: str = Form(...), project_id: str = Form(""), role_name: str = Form(...), skill: str = Form(""),
    requested_hours: float = Form(...), period_start: str = Form(...), period_end: str = Form(...), priority: str = Form("Medium"), rationale: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "PROJECT_MANAGER", "RESOURCE_MANAGER", "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN")
    if not can_access_org(user, org_id): raise HTTPException(status_code=403, detail="Organization outside permitted scope")
    resource_request = ResourceRequest(human_id=next_human_id(db, ResourceRequest, "RRQ"), org_id=org_id, project_id=project_id or None, role_name=role_name.strip(), skill=skill.strip(), requested_hours=requested_hours, period_start=date.fromisoformat(period_start), period_end=date.fromisoformat(period_end), priority=priority, requested_by_id=user.id, rationale=rationale)
    db.add(resource_request); db.flush(); record_audit(db, user.id, "ResourceRequest", resource_request.id, "SUBMIT", after=snapshot(resource_request), ip_address=request.state.client_ip); db.commit()
    return flash_redirect(f"/resources/requests/{resource_request.id}", f"Resource request {resource_request.human_id} submitted.")


@app.post("/resources/requests/{request_id}/decision")
def decide_resource_request(request_id: str, request: Request, csrf: str = Form(...), decision: str = Form(...), resolution: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "RESOURCE_MANAGER", "PMO", "DIVISION_CHIEF", "ADMIN")
    resource_request = db.get(ResourceRequest, request_id)
    if not resource_request or not can_access_org(user, resource_request.org_id): raise HTTPException(status_code=404, detail="Resource request not found")
    before = snapshot(resource_request); resource_request.status = decision; resource_request.approver_id = user.id; resource_request.resolution = resolution
    record_audit(db, user.id, "ResourceRequest", resource_request.id, "DECISION", before=before, after=snapshot(resource_request), ip_address=request.state.client_ip); db.commit()
    return flash_redirect(f"/resources/requests/{resource_request.id}", f"Resource request {decision.lower()}.")


@app.post("/financials/transactions")
def create_financial_transaction(
    request: Request, csrf: str = Form(...), financial_record_id: str = Form(...), transaction_type: str = Form(...), amount: float = Form(...),
    transaction_date: str = Form(...), reference: str = Form(""), source_system: str = Form("DDC5I-PM"), notes: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "FINANCIAL_MANAGER", "PMO", "ADMIN")
    financial = db.get(FinancialRecord, financial_record_id)
    if not financial: raise HTTPException(status_code=404, detail="Financial record not found")
    project = db.get(Project, financial.project_id) if financial.project_id else None
    if project and not can_access_org(user, project.lead_org_id): raise HTTPException(status_code=404, detail="Financial record not found")
    transaction = FinancialTransaction(human_id=next_human_id(db, FinancialTransaction, "FIN"), financial_record_id=financial.id, transaction_type=transaction_type, amount=amount, transaction_date=date.fromisoformat(transaction_date), reference=reference, source_system=source_system, notes=notes, created_by_id=user.id)
    db.add(transaction)
    if transaction_type == "Expenditure": financial.actual_cost = Decimal(str(float(financial.actual_cost or 0) + amount))
    elif transaction_type == "Forecast Adjustment": financial.forecast = Decimal(str(float(financial.forecast or 0) + amount))
    db.flush(); record_audit(db, user.id, "FinancialTransaction", transaction.id, "CREATE", after=snapshot(transaction), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/financials", f"Transaction {transaction.human_id} recorded.")


@app.get("/scenarios", response_class=HTMLResponse)
def scenarios_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "SENIOR_LEADER", "ENTERPRISE_PORTFOLIO_OWNER", "PMO", "DIVISION_CHIEF", "DIVISION_PORTFOLIO_MANAGER", "RESOURCE_MANAGER", "FINANCIAL_MANAGER", "ADMIN")
    query = db.query(Scenario)
    if not is_enterprise_user(user): query = query.filter(or_(Scenario.org_id == user.division_id, Scenario.org_id.is_(None)))
    return render(request, "scenarios.html", user, db, scenarios=query.order_by(Scenario.created_at.desc()).all())


@app.post("/scenarios")
def create_scenario(
    request: Request, csrf: str = Form(...), name: str = Form(...), scenario_type: str = Form("Portfolio What-if"), org_id: str = Form(""), baseline_date: str = Form(...), assumptions: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_business_edit(user)
    scoped_org = org_id or None
    if scoped_org and not can_access_org(user, scoped_org): raise HTTPException(status_code=403, detail="Organization outside permitted scope")
    scenario = Scenario(human_id=next_human_id(db, Scenario, "SCN"), name=name.strip(), scenario_type=scenario_type, org_id=scoped_org, baseline_date=date.fromisoformat(baseline_date), assumptions=assumptions, created_by_id=user.id)
    db.add(scenario); db.flush(); record_audit(db, user.id, "Scenario", scenario.id, "CREATE", after=snapshot(scenario), ip_address=request.state.client_ip); db.commit()
    return RedirectResponse(f"/scenarios/{scenario.id}", status_code=303)


@app.get("/scenarios/{scenario_id}", response_class=HTMLResponse)
def scenario_detail(scenario_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    scenario = db.get(Scenario, scenario_id)
    if not scenario or not _scenario_access(user, scenario): raise HTTPException(status_code=404, detail="Scenario not found")
    changes = db.query(ScenarioChange).filter_by(scenario_id=scenario.id).order_by(ScenarioChange.created_at).all()
    results = db.query(ScenarioResult).filter_by(scenario_id=scenario.id).order_by(ScenarioResult.metric_key).all()
    projects = scoped_projects(db, user).order_by(Project.human_id).all()
    resource_rows = db.query(ResourceCapacity); financial_rows = db.query(FinancialRecord, Project).join(Project, FinancialRecord.project_id == Project.id)
    if not is_enterprise_user(user): resource_rows = resource_rows.filter(ResourceCapacity.org_id == user.division_id); financial_rows = financial_rows.filter(Project.lead_org_id == user.division_id)
    entity_names = {p.id: f"{p.human_id} · {p.title}" for p in projects}
    entity_names.update({r.id: f"{r.period} · {r.role_name} · {r.skill}" for r in resource_rows.all()})
    entity_names.update({f.id: f"{p.human_id} · FY{f.fiscal_year} {f.category}" for f,p in financial_rows.all()})
    return render(request, "scenario_detail.html", user, db, scenario=scenario, changes=changes, results=results, projects=projects, resources=resource_rows.all(), financials=financial_rows.all(), entity_names=entity_names, audit=record_audit_events(db, scenario.id))


@app.post("/scenarios/{scenario_id}/changes")
def add_scenario_change(
    scenario_id: str, request: Request, csrf: str = Form(...), entity_type: str = Form(...), entity_id: str = Form(...), field_name: str = Form(...), proposed_value: str = Form(...), rationale: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_business_edit(user)
    scenario = db.get(Scenario, scenario_id)
    if not scenario or not _scenario_access(user, scenario): raise HTTPException(status_code=404, detail="Scenario not found")
    if scenario.status in {"Approved", "Applied"}: return flash_redirect(f"/scenarios/{scenario.id}", "Approved or applied scenarios are locked.", "warning")
    record = _scenario_target(db, entity_type, entity_id, field_name)
    if entity_type == "Project" and not can_access_org(user, record.lead_org_id): raise HTTPException(status_code=403, detail="Scenario target outside scope")
    baseline = getattr(record, field_name)
    if isinstance(baseline, (Decimal, date, datetime)): baseline = baseline.isoformat() if hasattr(baseline, "isoformat") else float(baseline)
    proposed = _convert_scenario_value(field_name, proposed_value)
    change = ScenarioChange(scenario_id=scenario.id, entity_type=entity_type, entity_id=entity_id, field_name=field_name, baseline_value=baseline, proposed_value=proposed, rationale=rationale)
    db.add(change); db.flush(); scenario.status = "Draft"; record_audit(db, user.id, "ScenarioChange", change.id, "CREATE", after=snapshot(change), ip_address=request.state.client_ip); db.commit()
    return flash_redirect(f"/scenarios/{scenario.id}", "Scenario change added without modifying live records.")


@app.post("/scenarios/{scenario_id}/calculate")
def calculate_scenario_route(scenario_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf)
    scenario = db.get(Scenario, scenario_id)
    if not scenario or not _scenario_access(user, scenario): raise HTTPException(status_code=404, detail="Scenario not found")
    results = calculate_scenario(db, scenario); record_audit(db, user.id, "Scenario", scenario.id, "COMPARE", after={"results": len(results)}, ip_address=request.state.client_ip); db.commit()
    return flash_redirect(f"/scenarios/{scenario.id}", "Scenario comparison calculated from current authoritative records.")


@app.post("/scenarios/{scenario_id}/approve")
def approve_scenario(scenario_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "SENIOR_LEADER", "APPROVAL_AUTHORITY", "ENTERPRISE_PORTFOLIO_OWNER", "ADMIN")
    scenario = db.get(Scenario, scenario_id)
    if not scenario or not _scenario_access(user, scenario): raise HTTPException(status_code=404, detail="Scenario not found")
    if not db.query(ScenarioResult).filter_by(scenario_id=scenario.id).count(): return flash_redirect(f"/scenarios/{scenario.id}", "Calculate the scenario before approval.", "warning")
    before = snapshot(scenario); scenario.status = "Approved"; scenario.approved_by_id = user.id; record_audit(db, user.id, "Scenario", scenario.id, "APPROVE", before=before, after=snapshot(scenario), ip_address=request.state.client_ip); db.commit()
    return flash_redirect(f"/scenarios/{scenario.id}", "Scenario approved. Live records remain unchanged until Apply.")


@app.post("/scenarios/{scenario_id}/apply")
def apply_scenario(scenario_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "ENTERPRISE_PORTFOLIO_OWNER", "PMO", "ADMIN")
    scenario = db.get(Scenario, scenario_id)
    if not scenario or not _scenario_access(user, scenario): raise HTTPException(status_code=404, detail="Scenario not found")
    if scenario.status != "Approved": return flash_redirect(f"/scenarios/{scenario.id}", "Only an approved scenario can be applied.", "warning")
    applied = 0
    for change in db.query(ScenarioChange).filter_by(scenario_id=scenario.id).all():
        record = _scenario_target(db, change.entity_type, change.entity_id, change.field_name)
        before = snapshot(record); value = change.proposed_value
        if change.field_name == "current_end_date": value = date.fromisoformat(value) if value else None
        elif change.field_name in {"budget", "forecast", "approved_budget"}: value = Decimal(str(value))
        setattr(record, change.field_name, value); record_audit(db, user.id, change.entity_type, change.entity_id, "SCENARIO_APPLY", before=before, after=snapshot(record), ip_address=request.state.client_ip); applied += 1
    scenario.status = "Applied"; record_audit(db, user.id, "Scenario", scenario.id, "APPLY", after={"changes_applied": applied}, ip_address=request.state.client_ip); db.commit()
    return flash_redirect(f"/scenarios/{scenario.id}", f"Applied {applied} governed scenario changes.")


@app.get("/data-quality", response_class=HTMLResponse)
def data_quality_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "DATA_STEWARD", "PMO", "ADMIN", "AUDITOR", "SECURITY_REVIEWER", "SENIOR_LEADER")
    query = db.query(DataQualityIssue)
    if not is_enterprise_user(user): query = query.filter(or_(DataQualityIssue.org_id == user.division_id, DataQualityIssue.org_id.is_(None)))
    issues = query.order_by(DataQualityIssue.status, DataQualityIssue.severity.desc(), DataQualityIssue.detected_at.desc()).all()
    users = {u.id: u for u in db.query(User).all()}; counts = Counter(issue.status for issue in issues); severities = Counter(issue.severity for issue in issues)
    return render(request, "data_quality.html", user, db, issues=issues, users_map=users, counts=counts, severities=severities)


@app.post("/data-quality/scan")
def data_quality_scan(request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "DATA_STEWARD", "PMO", "ADMIN")
    job = JobRun(job_type="Data Quality Scan", status="Running", started_at=datetime.now(timezone.utc), attempts=1, created_by_id=user.id)
    db.add(job); db.flush()
    issues = scan_data_quality(db, user.id); job.status = "Succeeded"; job.completed_at = datetime.now(timezone.utc); job.result = {"issues_detected_or_refreshed": len(issues)}
    record_audit(db, user.id, "JobRun", job.id, "EXECUTE", after=snapshot(job), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/data-quality", f"Data-quality scan completed; {len(issues)} issues detected or refreshed.")


@app.post("/data-quality/{issue_id}/update")
def update_quality_issue(
    issue_id: str, request: Request, csrf: str = Form(...), owner_id: str = Form(""), due_date: str = Form(""), status: str = Form(...), disposition: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "DATA_STEWARD", "PMO", "ADMIN")
    issue = db.get(DataQualityIssue, issue_id)
    if not issue or (not is_enterprise_user(user) and issue.org_id not in {None, user.division_id}): raise HTTPException(status_code=404, detail="Data quality issue not found")
    before = snapshot(issue); issue.owner_id = owner_id or issue.owner_id; issue.due_date = parse_optional_date(due_date); issue.status = status; issue.disposition = disposition
    issue.resolved_at = datetime.now(timezone.utc) if status == "Resolved" else None
    record_audit(db, user.id, "DataQualityIssue", issue.id, "UPDATE", before=before, after=snapshot(issue), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/data-quality", "Data-quality issue updated.")


@app.get("/operations", response_class=HTMLResponse)
def operations_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user, "ADMIN", "PMO", "DATA_STEWARD", "SENIOR_LEADER", "ENTERPRISE_PORTFOLIO_OWNER")
    jobs = db.query(JobRun).order_by(JobRun.created_at.desc()).limit(100).all(); packs = db.query(ReportPack).order_by(ReportPack.created_at.desc()).all()
    return render(request, "operations.html", user, db, jobs=jobs, packs=packs)


@app.post("/operations/report-packs")
def generate_report_pack(
    request: Request, csrf: str = Form(...), name: str = Form(...), pack_type: str = Form(...), org_id: str = Form(""), period_start: str = Form(...), period_end: str = Form(...),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "PMO", "DATA_STEWARD", "ADMIN", "ENTERPRISE_PORTFOLIO_OWNER")
    scoped_org = org_id or None
    if scoped_org and not can_access_org(user, scoped_org): raise HTTPException(status_code=403, detail="Organization outside permitted scope")
    sections = report_pack_sections(db, scoped_org)
    narrative = " ".join(f"{section['title']}: {section['value']} ({section['detail']})." for section in sections)
    pack = ReportPack(human_id=next_human_id(db, ReportPack, "RPT"), name=name.strip(), pack_type=pack_type, org_id=scoped_org, period_start=date.fromisoformat(period_start), period_end=date.fromisoformat(period_end), status="Generated", sections=sections, narrative=narrative, generated_by_id=user.id)
    job = JobRun(job_type="Report Pack Generation", status="Succeeded", started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc), attempts=1, payload={"pack_type": pack_type, "org_id": scoped_org}, result={"sections": len(sections)}, created_by_id=user.id)
    db.add_all([pack, job]); db.flush(); record_audit(db, user.id, "ReportPack", pack.id, "GENERATE", after=snapshot(pack), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/operations", f"Report pack {pack.human_id} generated from source records.")


@app.post("/operations/report-packs/{pack_id}/approve")
def approve_report_pack(pack_id: str, request: Request, csrf: str = Form(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "SENIOR_LEADER", "APPROVAL_AUTHORITY", "ENTERPRISE_PORTFOLIO_OWNER", "ADMIN")
    pack = db.get(ReportPack, pack_id)
    if not pack or (pack.org_id and not can_access_org(user, pack.org_id)): raise HTTPException(status_code=404, detail="Report pack not found")
    before = snapshot(pack); pack.status = "Approved"; pack.approved_by_id = user.id; pack.approved_at = datetime.now(timezone.utc); record_audit(db, user.id, "ReportPack", pack.id, "APPROVE", before=before, after=snapshot(pack), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/operations", f"Report pack {pack.human_id} approved.")


@app.post("/administration/users")
def create_user_admin(
    request: Request, csrf: str = Form(...), username: str = Form(...), full_name: str = Form(...), email: str = Form(...), password: str = Form(...),
    roles: list[str] = Form([]), division_id: str = Form(""), sensitive_access: str | None = Form(None),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN")
    normalized = username.strip().lower()
    if len(password) < 10: return flash_redirect("/administration", "Password must contain at least 10 characters.", "error")
    if db.query(User).filter(or_(User.username == normalized, User.email == email.strip().lower())).first(): return flash_redirect("/administration", "Username or email already exists.", "error")
    account = User(username=normalized, full_name=full_name.strip(), email=email.strip().lower(), password_hash=hash_password(password), roles=roles or ["TEAM_MEMBER"], division_id=division_id or None, sensitive_access=bool(sensitive_access), is_active=True)
    db.add(account); db.flush(); record_audit(db, user.id, "User", account.id, "CREATE", after={"username": account.username, "roles": account.roles, "division_id": account.division_id, "sensitive_access": account.sensitive_access}, ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/administration", f"User {account.username} created.")


@app.post("/administration/users/{user_id}/update")
def update_user_admin(
    user_id: str, request: Request, csrf: str = Form(...), full_name: str = Form(...), email: str = Form(...), roles: list[str] = Form([]),
    division_id: str = Form(""), sensitive_access: str | None = Form(None), is_active: str | None = Form(None),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN")
    account = db.get(User, user_id)
    if not account: raise HTTPException(status_code=404, detail="User not found")
    if account.id == user.id and not is_active: return flash_redirect("/administration", "You cannot disable your own active administrator account.", "error")
    before = {"full_name": account.full_name, "email": account.email, "roles": account.roles, "division_id": account.division_id, "sensitive_access": account.sensitive_access, "is_active": account.is_active}
    account.full_name = full_name.strip(); account.email = email.strip().lower(); account.roles = roles or account.roles; account.division_id = division_id or None; account.sensitive_access = bool(sensitive_access); account.is_active = bool(is_active)
    record_audit(db, user.id, "User", account.id, "UPDATE", before=before, after={"full_name": account.full_name, "email": account.email, "roles": account.roles, "division_id": account.division_id, "sensitive_access": account.sensitive_access, "is_active": account.is_active}, ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/administration", f"User {account.username} updated.")


@app.post("/administration/delegations")
def create_delegation(
    request: Request, csrf: str = Form(...), delegator_id: str = Form(...), delegate_id: str = Form(...), roles: list[str] = Form([]),
    org_scope_id: str = Form(""), starts_at: str = Form(...), expires_at: str = Form(""), reason: str = Form(""),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    require_csrf(request, user, csrf); require_roles(user, "ADMIN")
    if delegator_id == delegate_id: return flash_redirect("/administration", "Delegator and delegate must be different users.", "error")
    delegation = Delegation(delegator_id=delegator_id, delegate_id=delegate_id, roles=roles, org_scope_id=org_scope_id or None, starts_at=_parse_datetime(starts_at) or datetime.now(timezone.utc), expires_at=_parse_datetime(expires_at), reason=reason, created_by_id=user.id)
    db.add(delegation); db.flush(); record_audit(db, user.id, "Delegation", delegation.id, "CREATE", after=snapshot(delegation), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/administration", "Delegation created and auditable.")


@app.get("/api/docs", response_class=HTMLResponse)
def api_docs(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return render(request,"api_docs.html",user,db)


@app.get("/api/openapi.json", include_in_schema=False)
def openapi_document(user: User = Depends(current_user)):
    return JSONResponse(app.openapi())
