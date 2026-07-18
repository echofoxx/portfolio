from __future__ import annotations

import csv
import io
import json
import os
import re
import time
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import xlsxwriter
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.models import (
    Action,
    Assessment,
    DataQualityIssue,
    Delegation,
    BoardColumn,
    AuditEvent,
    Benefit,
    CoreFunction,
    Decision,
    Demand,
    DemandRevision,
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
    ProjectTemplate,
    RaidItem,
    RequirementTrace,
    ResourceCapacity,
    ResourceRequest,
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
    User,
)
from app.services.audit import record_audit, snapshot
from app.services.imports import validate_demand_rows
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
from app.services.schedule import critical_path, gantt_layout, wbs_numbers, would_create_cycle
from app.services.v050 import calculate_scenario, projectos_payload, report_pack_sections, scan_data_quality

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title=settings.app_name,
    version="0.6.0",
    description="JSJ6 enterprise demand, portfolio, project, resource, investment, benefit, and traceability reference implementation.",
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


def render(request: Request, template_name: str, user: User, db: Session, **context):
    orgs = db.query(Organization).filter(Organization.active.is_(True)).order_by(Organization.code).all()
    unread = db.query(Notification).filter(Notification.user_id == user.id, Notification.read_at.is_(None)).count()
    saved_views = db.query(SavedView).filter(SavedView.user_id == user.id).order_by(SavedView.name).all()
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
        "app_version": "0.6.0",
        "search_query": request.query_params.get("q", ""),
    }
    base.update(context)
    return templates.TemplateResponse(template_name, base)


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
    benefit_target = sum(b.target_value for b in benefits)
    benefit_realized = sum(b.realized_value for b in benefits)
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
    divisions = db.query(Organization).filter(Organization.org_type == "Division").order_by(Organization.code).all()
    division_rows = []
    for org in divisions:
        ps = db.query(Project).filter(Project.lead_org_id == org.id, Project.status == "Active").all()
        ds = db.query(Demand).filter(Demand.lead_org_id == org.id).all()
        caps = db.query(ResourceCapacity).filter(ResourceCapacity.org_id == org.id).all()
        division_rows.append({"org":org,"projects":len(ps),"at_risk":sum((p.health_override or p.health_owner) in exception_states for p in ps),"demands":len(ds),"capacity":round(sum(c.allocated_hours for c in caps)/sum(c.capacity_hours for c in caps)*100,1) if caps else 0})
    metrics = {m.key:m for m in db.query(MetricDefinition).all()}
    narrative = f"DDC5I is managing {len(projects)} active projects and {len(demands)} demands across mission, assessment, standards, architecture, infrastructure, and integration portfolios. Leadership attention is required for {len(at_risk)} project exceptions, {len(decisions_required)} pending demand decisions, {len(stale)} stale status records, and capacity utilization of {capacity_pct:.0f}%. Current accessible forecast is {money(forecast)} against an approved budget of {money(budget)}."
    return render(
        request, "dashboard.html", user, db,
        projects=projects, demands=demands, at_risk=at_risk, decisions_required=decisions_required,
        capacity_pct=capacity_pct, budget=budget, actual=actual, forecast=forecast,
        benefit_target=benefit_target, benefit_realized=benefit_realized, stale=stale,
        pipeline=pipeline, pipeline_order=pipeline_order, max_pipeline=max_pipeline,
        milestones=milestones, dependencies=dependencies, division_rows=division_rows,
        metrics=metrics, narrative=narrative, recent_decisions=recent_decisions,
        decision_sources=decision_sources, high_risks=high_risks, my_tasks=my_tasks,
        my_actions=my_actions, health_score=health_score, health_segments=health_segments,
        investment_categories=investment_categories, investment_gradient=investment_gradient,
        portfolio_rows=portfolio_rows,
    )

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


@app.get("/divisions", response_class=HTMLResponse)
def divisions_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    orgs = db.query(Organization).filter(Organization.org_type == "Division").order_by(Organization.code).all()
    rows=[]
    for org in orgs:
        if not can_access_org(user, org.id):
            continue
        projects=db.query(Project).filter(Project.lead_org_id==org.id,Project.status=="Active").all()
        demands=db.query(Demand).filter(Demand.lead_org_id==org.id).count()
        rows.append({"org":org,"projects":projects,"demands":demands,"at_risk":sum(p.health_owner in {"At Risk","Off Track","Blocked"} for p in projects)})
    return render(request,"divisions.html",user,db,rows=rows)


@app.get("/divisions/{code}", response_class=HTMLResponse)
def division_detail(code: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    org = db.query(Organization).filter(Organization.code == code.upper()).first()
    if not org or not can_access_org(user, org.id):
        raise HTTPException(404, "Division not found")
    projects=db.query(Project).filter(Project.lead_org_id==org.id).order_by(Project.status,Project.title).all()
    demands=db.query(Demand).filter(Demand.lead_org_id==org.id).order_by(Demand.updated_at.desc()).all()
    core=db.query(CoreFunction).filter(CoreFunction.org_id==org.id).all()
    capacities=db.query(ResourceCapacity).filter(ResourceCapacity.org_id==org.id).all()
    financials=db.query(FinancialRecord).join(Project,FinancialRecord.project_id==Project.id).filter(Project.lead_org_id==org.id).all()
    milestones=db.query(Milestone,Project).join(Project,Milestone.project_id==Project.id).filter(Project.lead_org_id==org.id).order_by(Milestone.current_date).limit(12).all()
    raid=db.query(RaidItem,Project).join(Project,RaidItem.project_id==Project.id).filter(Project.lead_org_id==org.id,RaidItem.status!="Closed").order_by(RaidItem.exposure.desc()).limit(12).all()
    dependencies=db.query(Dependency,Project).join(Project,Dependency.source_project_id==Project.id).filter(Project.lead_org_id==org.id).all()
    missions=db.query(Mission).filter(Mission.owner_org_id==org.id).all()
    pipeline=Counter(d.status for d in demands)
    narrative=f"{org.name} is executing {len([p for p in projects if p.status=='Active'])} active projects, sustaining {len(core)} governed core functions, and shaping {len(demands)} demands. Current exception load includes {sum(p.health_owner in {'At Risk','Off Track','Blocked'} for p in projects)} project health exceptions and {sum(r.RaidItem.severity in {'High','Critical'} for r in raid)} high-severity assurance records."
    return render(request,"division_detail.html",user,db,org=org,projects=projects,demands=demands,core=core,capacities=capacities,financials=financials,milestones=milestones,raid=raid,dependencies=dependencies,missions=missions,pipeline=pipeline,narrative=narrative)


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
def projects_page(request: Request, q: str = "", health: str = "", status: str = "", division: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    query=scoped_projects(db,user)
    if q: query=query.filter(or_(Project.title.ilike(f"%{q}%"),Project.human_id.ilike(f"%{q}%")))
    if health: query=query.filter(or_(Project.health_owner==health,Project.health_override==health,Project.health_calculated==health))
    if status: query=query.filter(Project.status==status)
    if division:
        org=db.query(Organization).filter(Organization.code==division).first()
        if org and can_access_org(user,org.id): query=query.filter(Project.lead_org_id==org.id)
    projects=query.order_by(Project.updated_at.desc()).all(); orgs={o.id:o for o in db.query(Organization).all()}; users={u.id:u for u in db.query(User).all()}
    return render(request,"projects.html",user,db,projects=projects,orgs_map=orgs,users_map=users,q=q,health=health,status=status,division=division)


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


@app.post("/projects/{project_id}/milestones")
def milestone_create(project_id: str, request: Request, csrf: str = Form(...), title: str = Form(...), current_date: str = Form(...), confidence: str = Form("Medium"), critical: str = Form(""), owner_id: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"PROJECT_MANAGER","PMO","ADMIN"); p=get_accessible_project(db,user,project_id); due=date.fromisoformat(current_date); m=Milestone(human_id=next_human_id(db,Milestone,"MS"),project_id=p.id,title=title,baseline_date=due,current_date=due,confidence=confidence,critical=bool(critical),owner_id=owner_id or user.id); db.add(m); db.flush(); record_audit(db,user.id,"Milestone",m.id,"CREATE",after=snapshot(m)); db.commit(); return flash_redirect(f"/projects/{p.id}?tab=milestones",f"Milestone {m.human_id} created.")


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


@app.get("/financials", response_class=HTMLResponse)
def financials_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q=db.query(FinancialRecord,Project).join(Project,FinancialRecord.project_id==Project.id)
    if not is_enterprise_user(user): q=q.filter(Project.lead_org_id==user.division_id)
    rows=q.all(); allowed_ids=[f.id for f,p in rows]
    transactions=db.query(FinancialTransaction).filter(FinancialTransaction.financial_record_id.in_(allowed_ids)).order_by(FinancialTransaction.transaction_date.desc(),FinancialTransaction.created_at.desc()).limit(100).all() if allowed_ids else []
    financial_map={f.id:(f,p) for f,p in rows}; budget=sum(float(f.approved_budget) for f,p in rows); actual=sum(float(f.actual_cost) for f,p in rows); forecast=sum(float(f.forecast) for f,p in rows); unfunded=sum(float(f.full_requirement)-float(f.approved_budget) for f,p in rows if f.funding_status!="Funded")
    transaction_totals=Counter(t.transaction_type for t in transactions)
    return render(request,"financials.html",user,db,rows=rows,budget=budget,actual=actual,forecast=forecast,unfunded=unfunded,transactions=transactions,financial_map=financial_map,transaction_totals=transaction_totals)


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
    demands=scoped_demands(db,user).filter(or_(Demand.requester_id==user.id,Demand.current_owner_id==user.id,Demand.sponsor_id==user.id)).all(); projects=scoped_projects(db,user).filter(or_(Project.manager_id==user.id,Project.sponsor_id==user.id)).all(); tasks=db.query(Task,Project).join(Project,Task.project_id==Project.id).filter(Task.owner_id==user.id,Task.status!="Completed").order_by(Task.due_date).all(); actions=db.query(Action).filter(Action.owner_id==user.id,Action.status!="Closed").order_by(Action.due_date).all()
    return render(request,"my_work.html",user,db,demands=demands,projects=projects,tasks=tasks,actions=actions)


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
    if template_type!="Demands": return flash_redirect("/imports","MVP row-level commit currently supports the Demands template. Other versioned templates are provided for controlled staging.","error")
    results,summary=validate_demand_rows(db,rows,user); batch=ImportBatch(filename=os.path.basename(file.filename),template_type=template_type,status="Preview",uploaded_by_id=user.id,rows_json=results,summary_json=summary); db.add(batch); db.flush()
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
        if result["severity"]=="Error": continue
        data=result["data"]; rid=data.get("Human ID") or next_human_id(db,Demand,"DMD"); d=db.query(Demand).filter(Demand.human_id==rid).first(); before=snapshot(d) if d else None
        if not d:
            d=Demand(human_id=rid,title=data["Title"],category=data.get("Category") or "Idea",status=data.get("Status") or "Draft",lead_org_id=data["_org_id"],requesting_org_id=data["_org_id"],mission_id=data["_mission_id"],sponsor_id=user.id,requester_id=user.id,current_owner_id=user.id); db.add(d); db.flush(); action="IMPORT_CREATE"
        else: action="IMPORT_UPDATE"
        d.title=data["Title"]; d.category=data.get("Category") or d.category; d.status=data.get("Status") or d.status; d.lead_org_id=data["_org_id"]; d.requesting_org_id=data["_org_id"]; d.mission_id=data["_mission_id"]; d.purpose=data.get("Purpose") or "Imported demand"; d.problem=data.get("Problem or Opportunity") or "Imported problem statement pending refinement"; d.desired_end_state=data.get("Desired End State") or "Imported desired end state pending refinement"; d.urgency=data.get("Urgency") or "Normal"; d.rom_cost=data["_rom"]; d.expected_benefits=data.get("Expected Benefits") or ""; d.sensitivity=data.get("Sensitivity") or "Controlled Unclassified"; d.next_action=demand_next_action(d.status); d.source_system="Excel Import"; d.source_record=f"{batch.id}:{result['row_number']}"; record_audit(db,user.id,"Demand",d.id,action,before=before,after=snapshot(d)); committed+=1
    batch.status="Committed"; record_audit(db,user.id,"ImportBatch",batch.id,"COMMIT",after={"committed":committed,"summary":batch.summary_json}); db.commit(); return flash_redirect(f"/imports/{batch.id}",f"Committed {committed} valid rows. Errors remained excluded.")


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
    review = PortfolioReview(human_id=next_human_id(db, PortfolioReview, "REV"), title=title.strip(), review_type=review_type, portfolio_id=portfolio_id or None, org_id=scoped_org, period_start=date.fromisoformat(period_start), period_end=date.fromisoformat(period_end), chair_id=chair_id, participant_ids=participant_ids, summary=summary, decisions_required=decisions_required)
    db.add(review); db.flush(); record_audit(db, user.id, "PortfolioReview", review.id, "CREATE", after=snapshot(review), ip_address=request.state.client_ip); db.commit()
    return RedirectResponse(f"/portfolio-reviews/{review.id}", status_code=303)


@app.get("/portfolio-reviews/{review_id}", response_class=HTMLResponse)
def portfolio_review_detail(review_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    review = db.get(PortfolioReview, review_id)
    if not review or not _review_access(user, review): raise HTTPException(status_code=404, detail="Review not found")
    items = db.query(PortfolioReviewItem).filter_by(review_id=review.id).order_by(PortfolioReviewItem.sort_order, PortfolioReviewItem.created_at).all()
    projects = scoped_projects(db, user).order_by(Project.human_id).all(); demands = scoped_demands(db, user).order_by(Demand.human_id).all()
    users = {u.id: u for u in db.query(User).all()}; decisions = {d.id: d for d in db.query(Decision).all()}; actions = {a.id: a for a in db.query(Action).all()}
    return render(request, "portfolio_review_detail.html", user, db, review=review, items=items, projects=projects, demands=demands, users_map=users, decisions_map=decisions, actions_map=actions, audit=record_audit_events(db, review.id))


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
def complete_review(review_id: str, request: Request, csrf: str = Form(...), summary: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "SENIOR_LEADER", "APPROVAL_AUTHORITY", "ENTERPRISE_PORTFOLIO_OWNER", "PMO", "ADMIN")
    review = db.get(PortfolioReview, review_id)
    if not review or not _review_access(user, review): raise HTTPException(status_code=404, detail="Review not found")
    before = snapshot(review); review.status = "Completed"; review.completed_at = datetime.now(timezone.utc); review.summary = summary or review.summary
    record_audit(db, user.id, "PortfolioReview", review.id, "COMPLETE", before=before, after=snapshot(review), ip_address=request.state.client_ip); db.commit()
    return flash_redirect(f"/portfolio-reviews/{review.id}", "Portfolio review completed.")


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
    return flash_redirect("/resources", f"Resource request {resource_request.human_id} submitted.")


@app.post("/resources/requests/{request_id}/decision")
def decide_resource_request(request_id: str, request: Request, csrf: str = Form(...), decision: str = Form(...), resolution: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request, user, csrf); require_roles(user, "RESOURCE_MANAGER", "PMO", "DIVISION_CHIEF", "ADMIN")
    resource_request = db.get(ResourceRequest, request_id)
    if not resource_request or not can_access_org(user, resource_request.org_id): raise HTTPException(status_code=404, detail="Resource request not found")
    before = snapshot(resource_request); resource_request.status = decision; resource_request.approver_id = user.id; resource_request.resolution = resolution
    record_audit(db, user.id, "ResourceRequest", resource_request.id, "DECISION", before=before, after=snapshot(resource_request), ip_address=request.state.client_ip); db.commit()
    return flash_redirect("/resources", f"Resource request {decision.lower()}.")


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
