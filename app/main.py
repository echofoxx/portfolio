from __future__ import annotations

import csv
import io
import json
import os
import re
import time
from collections import Counter, defaultdict
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
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.models import (
    Action,
    Assessment,
    AuditEvent,
    Benefit,
    CoreFunction,
    Decision,
    Demand,
    DemandRevision,
    Dependency,
    FinancialRecord,
    ImportBatch,
    ImportRow,
    MetricDefinition,
    Milestone,
    Mission,
    Notification,
    Organization,
    Portfolio,
    Project,
    RaidItem,
    RequirementTrace,
    ResourceCapacity,
    SavedView,
    Task,
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
)
from app.services.workflow import ALLOWED_TRANSITIONS, validate_transition
from app.services.xlsx_reader import read_first_sheet_xlsx

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Vendor-neutral DDC5I enterprise demand, portfolio, project, resource, financial, benefit, and traceability reference implementation.",
    docs_url=None,
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)


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
        "app_version": "0.1.0",
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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
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
    ip = request.client.host if request.client else "unknown"
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
    divisions = db.query(Organization).filter(Organization.org_type == "Division").order_by(Organization.code).all()
    division_rows = []
    for org in divisions:
        ps = db.query(Project).filter(Project.lead_org_id == org.id, Project.status == "Active").all()
        ds = db.query(Demand).filter(Demand.lead_org_id == org.id).all()
        caps = db.query(ResourceCapacity).filter(ResourceCapacity.org_id == org.id).all()
        division_rows.append({"org":org,"projects":len(ps),"at_risk":sum((p.health_override or p.health_owner) in exception_states for p in ps),"demands":len(ds),"capacity":round(sum(c.allocated_hours for c in caps)/sum(c.capacity_hours for c in caps)*100,1) if caps else 0})
    metrics = {m.key:m for m in db.query(MetricDefinition).all()}
    narrative = f"DDC5I is managing {len(projects)} active projects and {len(demands)} demands across mission, assessment, standards, architecture, infrastructure, and integration portfolios. Leadership attention is required for {len(at_risk)} project exceptions, {len(decisions_required)} pending demand decisions, {len(stale)} stale status records, and capacity utilization of {capacity_pct:.0f}%. Current accessible forecast is {money(forecast)} against an approved budget of {money(budget)}."
    return render(request, "dashboard.html", user, db, projects=projects, demands=demands, at_risk=at_risk, decisions_required=decisions_required, capacity_pct=capacity_pct, budget=budget, actual=actual, forecast=forecast, benefit_target=benefit_target, benefit_realized=benefit_realized, stale=stale, pipeline=pipeline, pipeline_order=pipeline_order, max_pipeline=max_pipeline, milestones=milestones, dependencies=dependencies, division_rows=division_rows, metrics=metrics, narrative=narrative)


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
    return render(request,"demand_detail.html",user,db,demand=d,assessments=assessments,decisions=decisions,actions=actions,revisions=revisions,project=project,users_map=users,orgs_map=orgs,missions_map=missions,allowed_transitions=allowed,weights=DEFAULT_WEIGHTS,labels=LABELS)


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
def project_detail(project_id: str, request: Request, tab: str = "overview", db: Session = Depends(get_db), user: User = Depends(current_user)):
    p=get_accessible_project(db,user,project_id)
    tasks=db.query(Task).filter(Task.project_id==p.id).order_by(Task.sequence).all(); milestones=db.query(Milestone).filter(Milestone.project_id==p.id).order_by(Milestone.current_date).all(); raid=db.query(RaidItem).filter(RaidItem.project_id==p.id).order_by(RaidItem.exposure.desc()).all(); dependencies=db.query(Dependency).filter(Dependency.source_project_id==p.id).order_by(Dependency.due_date).all(); decisions=db.query(Decision).filter(Decision.project_id==p.id).order_by(Decision.created_at.desc()).all(); actions=db.query(Action).filter(Action.project_id==p.id).order_by(Action.due_date).all(); financials=db.query(FinancialRecord).filter(FinancialRecord.project_id==p.id).all(); benefits=db.query(Benefit).filter(Benefit.project_id==p.id).all()
    users={u.id:u for u in db.query(User).all()}; orgs={o.id:o for o in db.query(Organization).all()}; missions={m.id:m for m in db.query(Mission).all()}; projects={x.id:x for x in db.query(Project).all()}
    columns=["Backlog","Ready","In Progress","Review","Done"]; tasks_by_col={c:[t for t in tasks if t.board_column==c] for c in columns}
    audit=db.query(AuditEvent).filter(AuditEvent.entity_id.in_([p.id]+[t.id for t in tasks])).order_by(AuditEvent.created_at.desc()).limit(30).all()
    return render(request,"project_detail.html",user,db,project=p,tasks=tasks,milestones=milestones,raid=raid,dependencies=dependencies,decisions=decisions,actions=actions,financials=financials,benefits=benefits,users_map=users,orgs_map=orgs,missions_map=missions,projects_map=projects,columns=columns,tasks_by_col=tasks_by_col,tab=tab,audit=audit)


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


@app.post("/projects/{project_id}/tasks")
def task_create(project_id: str, request: Request, csrf: str = Form(...), title: str = Form(...), owner_id: str = Form(""), due_date: str = Form(""), estimated_effort: float = Form(0), board_column: str = Form("Backlog"), notes: str = Form(""), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,csrf); require_roles(user,"PROJECT_MANAGER","TEAM_MEMBER","ADMIN"); p=get_accessible_project(db,user,project_id)
    t=Task(human_id=next_human_id(db,Task,"TSK"),project_id=p.id,title=title,owner_id=owner_id or None,due_date=date.fromisoformat(due_date) if due_date else None,estimated_effort=estimated_effort,board_column=board_column,status="Not Started",notes=notes,sequence=db.query(Task).filter(Task.project_id==p.id).count()+1); db.add(t); db.flush(); record_audit(db,user.id,"Task",t.id,"CREATE",after=snapshot(t)); db.commit(); return flash_redirect(f"/projects/{p.id}?tab=board",f"Task {t.human_id} created.")


@app.post("/api/tasks/{task_id}/move")
def task_move(task_id: str, payload: dict, request: Request, x_csrf_token: str | None = Header(None), db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_csrf(request,user,header_token=x_csrf_token); require_roles(user,"PROJECT_MANAGER","TEAM_MEMBER","ADMIN"); t=db.get(Task,task_id)
    if not t: raise HTTPException(404,"Task not found")
    p=get_accessible_project(db,user,t.project_id); column=payload.get("column")
    if column not in {"Backlog","Ready","In Progress","Review","Done"}: raise HTTPException(400,"Invalid board column")
    before=snapshot(t); t.board_column=column; t.status="Completed" if column=="Done" else "In Progress" if column in {"In Progress","Review"} else "Not Started"; t.percent_complete={"Backlog":0,"Ready":10,"In Progress":50,"Review":85,"Done":100}[column]; record_audit(db,user.id,"Task",t.id,"BOARD_MOVE",before=before,after=snapshot(t)); db.commit(); return {"ok":True,"task":t.human_id,"column":column}


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
    q=db.query(ResourceCapacity)
    if not is_enterprise_user(user): q=q.filter(ResourceCapacity.org_id==user.division_id)
    rows=q.order_by(ResourceCapacity.org_id,ResourceCapacity.role_name).all(); orgs={o.id:o for o in db.query(Organization).all()}
    total_cap=sum(r.capacity_hours for r in rows); total_alloc=sum(r.allocated_hours for r in rows); over=[r for r in rows if r.allocated_hours>r.capacity_hours]; gaps=[r for r in rows if r.allocated_hours+r.minimum_core_coverage>r.capacity_hours]
    return render(request,"resources.html",user,db,rows=rows,orgs_map=orgs,total_cap=total_cap,total_alloc=total_alloc,over=over,gaps=gaps)


@app.get("/financials", response_class=HTMLResponse)
def financials_page(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q=db.query(FinancialRecord,Project).join(Project,FinancialRecord.project_id==Project.id)
    if not is_enterprise_user(user): q=q.filter(Project.lead_org_id==user.division_id)
    rows=q.all(); budget=sum(float(f.approved_budget) for f,p in rows); actual=sum(float(f.actual_cost) for f,p in rows); forecast=sum(float(f.forecast) for f,p in rows); unfunded=sum(float(f.full_requirement)-float(f.approved_budget) for f,p in rows if f.funding_status!="Funded")
    return render(request,"financials.html",user,db,rows=rows,budget=budget,actual=actual,forecast=forecast,unfunded=unfunded)


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


@app.get("/search", response_class=HTMLResponse)
def global_search(request: Request, q: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    demands=scoped_demands(db,user).filter(or_(Demand.title.ilike(f"%{q}%"),Demand.human_id.ilike(f"%{q}%"))).limit(20).all(); projects=scoped_projects(db,user).filter(or_(Project.title.ilike(f"%{q}%"),Project.human_id.ilike(f"%{q}%"))).limit(20).all(); requirements=[]
    if has_role(user,"ADMIN","PMO","DATA_STEWARD","AUDITOR","SENIOR_LEADER","ENTERPRISE_PORTFOLIO_OWNER"): requirements=db.query(RequirementTrace).filter(or_(RequirementTrace.requirement_id.ilike(f"%{q}%"),RequirementTrace.title.ilike(f"%{q}%"))).limit(20).all()
    return render(request,"search.html",user,db,q=q,demands=demands,projects=projects,requirements=requirements)


@app.get("/administration", response_class=HTMLResponse)
def administration(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_roles(user,"ADMIN"); users=db.query(User).order_by(User.username).all(); orgs={o.id:o for o in db.query(Organization).all()}; integrations=[
        {"name":"ProjectOS","authority":"Tasks, schedules, documents: unresolved field ownership","status":"Adapter defined; live connection not required","mode":"Bidirectional registry planned"},
        {"name":"ServiceNow SPM","authority":"Portfolio/investment fields require synchronization contract","status":"Not connected","mode":"REST/events/reconciliation planned"},
        {"name":"Microsoft 365 / Outlook","authority":"Notification and approval action policy required","status":"Mailpit local option only","mode":"Microsoft Graph adapter planned"},
        {"name":"SharePoint","authority":"Document and list ownership requires governance decision","status":"Not connected","mode":"Document/list adapter planned"},
        {"name":"Advana / WDP / Power BI","authority":"Analytics feed; source remains operational record","status":"Not connected","mode":"Read-optimized data product planned"},
    ]; counts={"users":db.query(User).count(),"demands":db.query(Demand).count(),"projects":db.query(Project).count(),"requirements":db.query(RequirementTrace).count(),"audit":db.query(AuditEvent).count()}
    return render(request,"administration.html",user,db,users=users,orgs_map=orgs,integrations=integrations,counts=counts)


@app.get("/api/docs", response_class=HTMLResponse)
def api_docs(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return render(request,"api_docs.html",user,db)


@app.get("/api/openapi.json", include_in_schema=False)
def openapi_document(user: User = Depends(current_user)):
    return JSONResponse(app.openapi())
