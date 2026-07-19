from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def uuid4() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    org_type: Mapped[str] = mapped_column(String(40), default="Division")
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    narrative: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DivisionProfile(Base):
    __tablename__ = "division_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), unique=True, index=True)
    mission: Mapped[str] = mapped_column(Text, default="")
    vision: Mapped[str] = mapped_column(Text, default="")
    focus_areas: Mapped[list[str]] = mapped_column(JSON, default=list)
    responsibilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    branches: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    initiatives: Mapped[list[str]] = mapped_column(JSON, default=list)
    relationships: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    forums: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    doctrine: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    banner_asset: Mapped[str] = mapped_column(String(240), default="")
    banner_alt: Mapped[str] = mapped_column(Text, default="")
    focal_x: Mapped[int] = mapped_column(Integer, default=50)
    focal_y: Mapped[int] = mapped_column(Integer, default=50)
    status: Mapped[str] = mapped_column(String(30), default="Published")
    source_documents: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_notes: Mapped[str] = mapped_column(Text, default="")
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TravelEngagement(Base):
    __tablename__ = "travel_engagements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    normalized_title: Mapped[str] = mapped_column(String(300), index=True, default="")
    location: Mapped[str] = mapped_column(String(240), default="")
    country_code: Mapped[str] = mapped_column(String(8), default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Planned")
    lead_org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    cross_division: Mapped[bool] = mapped_column(Boolean, default=False)
    source_system: Mapped[str] = mapped_column(String(100), default="Travel Approval Export")
    source_record: Mapped[str] = mapped_column(String(160), default="")
    source_filename: Mapped[str] = mapped_column(String(260), default="")
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TravelRequest(Base):
    __tablename__ = "travel_requests"
    __table_args__ = (UniqueConstraint("source_system", "external_id", name="uq_travel_request_source_external"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    external_id: Mapped[str] = mapped_column(String(100), index=True)
    engagement_id: Mapped[str | None] = mapped_column(ForeignKey("travel_engagements.id"), nullable=True, index=True)
    traveler_name: Mapped[str] = mapped_column(String(220), index=True)
    traveler_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    location: Mapped[str] = mapped_column(String(240), default="")
    determination: Mapped[str] = mapped_column(String(40), default="Pending", index=True)
    departure_date: Mapped[date] = mapped_column(Date, index=True)
    return_date: Mapped[date] = mapped_column(Date, index=True)
    estimated_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    purpose_roi: Mapped[str] = mapped_column(Text, default="")
    impact_if_not: Mapped[str] = mapped_column(Text, default="")
    funding: Mapped[str] = mapped_column(String(120), default="")
    exemption_category: Mapped[str] = mapped_column(Text, default="")
    report_required: Mapped[bool] = mapped_column(Boolean, default=True)
    report_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sensitivity: Mapped[str] = mapped_column(String(40), default="Controlled Unclassified")
    source_system: Mapped[str] = mapped_column(String(100), default="Travel Approval Export")
    source_record: Mapped[str] = mapped_column(String(160), default="")
    source_filename: Mapped[str] = mapped_column(String(260), default="")
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    import_batch_id: Mapped[str | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TravelApprovalStep(Base):
    __tablename__ = "travel_approval_steps"
    __table_args__ = (UniqueConstraint("request_id", "step_order", name="uq_travel_approval_request_step"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    request_id: Mapped[str] = mapped_column(ForeignKey("travel_requests.id"), index=True)
    step_order: Mapped[int] = mapped_column(Integer, default=1)
    approver_name: Mapped[str] = mapped_column(String(220), default="")
    approver_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approver_role: Mapped[str] = mapped_column(String(100), default="")
    determination: Mapped[str] = mapped_column(String(40), default="Pending")
    comments: Mapped[str] = mapped_column(Text, default="")
    determination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TripReport(Base):
    __tablename__ = "trip_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    request_id: Mapped[str | None] = mapped_column(ForeignKey("travel_requests.id"), nullable=True, index=True)
    engagement_id: Mapped[str | None] = mapped_column(ForeignKey("travel_engagements.id"), nullable=True, index=True)
    traveler_name: Mapped[str] = mapped_column(String(220), index=True)
    traveler_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    return_date: Mapped[date] = mapped_column(Date)
    location: Mapped[str] = mapped_column(String(240), default="")
    purpose_objectives: Mapped[str] = mapped_column(Text, default="")
    discussion: Mapped[str] = mapped_column(Text, default="")
    key_findings: Mapped[str] = mapped_column(Text, default="")
    recommendations: Mapped[str] = mapped_column(Text, default="")
    action_items: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="Submitted")
    review_status: Mapped[str] = mapped_column(String(40), default="Awaiting Review")
    review_comments: Mapped[str] = mapped_column(Text, default="")
    reviewed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sensitivity: Mapped[str] = mapped_column(String(40), default="Controlled Unclassified")
    version: Mapped[int] = mapped_column(Integer, default=1)
    match_status: Mapped[str] = mapped_column(String(40), default="Unmatched", index=True)
    match_confidence: Mapped[float] = mapped_column(Float, default=0)
    match_rationale: Mapped[str] = mapped_column(Text, default="")
    matched_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_system: Mapped[str] = mapped_column(String(100), default="Trip Reports SharePoint")
    source_record: Mapped[str] = mapped_column(String(260), default="")
    source_filename: Mapped[str] = mapped_column(String(260), default="")
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    import_batch_id: Mapped[str | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TripReportItem(Base):
    __tablename__ = "trip_report_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("trip_reports.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(60), default="Finding", index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(260), default="")
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="Candidate")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    promoted_entity_type: Mapped[str] = mapped_column(String(60), default="")
    promoted_entity_id: Mapped[str] = mapped_column(String(80), default="")
    source_excerpt: Mapped[str] = mapped_column(Text, default="")
    reviewed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TravelEntityLink(Base):
    __tablename__ = "travel_entity_links"
    __table_args__ = (UniqueConstraint("source_entity_type", "source_entity_id", "target_entity_type", "target_entity_id", name="uq_travel_entity_link"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    source_entity_type: Mapped[str] = mapped_column(String(60), index=True)
    source_entity_id: Mapped[str] = mapped_column(String(80), index=True)
    target_entity_type: Mapped[str] = mapped_column(String(60), index=True)
    target_entity_id: Mapped[str] = mapped_column(String(80), index=True)
    link_type: Mapped[str] = mapped_column(String(80), default="Related")
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    password_hash: Mapped[str] = mapped_column(String(400))
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    division_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    sensitive_access: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    acting_for_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    delegation_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    owner_org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    status: Mapped[str] = mapped_column(String(30), default="Active")
    outcome: Mapped[str] = mapped_column(Text, default="")
    measures: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class CoreFunction(Base):
    __tablename__ = "core_functions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id"))
    health: Mapped[str] = mapped_column(String(30), default="On Track")
    minimum_capacity_hours: Mapped[float] = mapped_column(Float, default=0)
    allocated_capacity_hours: Mapped[float] = mapped_column(Float, default=0)


class Demand(Base):
    __tablename__ = "demands"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240), index=True)
    category: Mapped[str] = mapped_column(String(80), default="Idea")
    status: Mapped[str] = mapped_column(String(60), default="Draft", index=True)
    sensitivity: Mapped[str] = mapped_column(String(40), default="Controlled Unclassified")
    sponsor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    requesting_org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    lead_org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    mission_id: Mapped[str | None] = mapped_column(ForeignKey("missions.id"), nullable=True)
    purpose: Mapped[str] = mapped_column(Text, default="")
    problem: Mapped[str] = mapped_column(Text, default="")
    desired_end_state: Mapped[str] = mapped_column(Text, default="")
    beneficiaries: Mapped[str] = mapped_column(Text, default="")
    required_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    urgency: Mapped[str] = mapped_column(String(30), default="Normal")
    consequence_of_inaction: Mapped[str] = mapped_column(Text, default="")
    preliminary_scope: Mapped[str] = mapped_column(Text, default="")
    deliverables: Mapped[str] = mapped_column(Text, default="")
    assumptions: Mapped[str] = mapped_column(Text, default="")
    dependencies_text: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[str] = mapped_column(Text, default="")
    rom_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    expected_benefits: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String(30), default="Medium")
    current_owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    next_action: Mapped[str] = mapped_column(String(240), default="Complete intake")
    pending_information: Mapped[str] = mapped_column(Text, default="")
    target_decision_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    disposition: Mapped[str] = mapped_column(Text, default="")
    score_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_variance: Mapped[float | None] = mapped_column(Float, nullable=True)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    mandatory_rationale: Mapped[str] = mapped_column(Text, default="")
    capacity_tradeoff: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_system: Mapped[str] = mapped_column(String(80), default="DDC5I-PM")
    source_record: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DemandRevision(Base):
    __tablename__ = "demand_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    demand_id: Mapped[str] = mapped_column(ForeignKey("demands.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    changed_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    demand_id: Mapped[str] = mapped_column(ForeignKey("demands.id"), index=True)
    assessor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    scores: Mapped[dict[str, float]] = mapped_column(JSON)
    rationale: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(30), default="Medium")
    total_score: Mapped[float] = mapped_column(Float)
    adjudication: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("portfolios.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Active")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    work_type: Mapped[str] = mapped_column(String(40), default="Project")
    status: Mapped[str] = mapped_column(String(40), default="Active")
    health_owner: Mapped[str] = mapped_column(String(30), default="On Track")
    health_calculated: Mapped[str] = mapped_column(String(30), default="On Track")
    health_override: Mapped[str | None] = mapped_column(String(30), nullable=True)
    health_override_reason: Mapped[str] = mapped_column(Text, default="")
    lead_org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    supporting_org_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    portfolio_id: Mapped[str | None] = mapped_column(ForeignKey("portfolios.id"), nullable=True)
    sponsor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    manager_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id"))
    demand_id: Mapped[str | None] = mapped_column(ForeignKey("demands.id"), nullable=True, unique=True)
    template_code: Mapped[str] = mapped_column(String(60), default="")
    template_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    governance_level: Mapped[str] = mapped_column(String(40), default="Portfolio Managed", index=True)
    funding_posture: Mapped[str] = mapped_column(String(40), default="Existing Funding")
    resource_posture: Mapped[str] = mapped_column(String(40), default="Existing Capacity")
    promotion_status: Mapped[str] = mapped_column(String(40), default="Not Required", index=True)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    desired_end_state: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[str] = mapped_column(Text, default="")
    deliverables: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    baseline_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    percent_complete: Mapped[int] = mapped_column(Integer, default=0)
    budget: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    actual: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    forecast: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    benefit_expected: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    benefit_realized: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    sensitivity: Mapped[str] = mapped_column(String(40), default="Controlled Unclassified")
    last_status_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source_system: Mapped[str] = mapped_column(String(80), default="DDC5I-PM")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    task_type: Mapped[str] = mapped_column(String(40), default="Task")
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(30), default="Medium")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), default="To Do")
    board_column: Mapped[str] = mapped_column(String(40), default="Backlog")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    contributor_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    watcher_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    custom_fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_finish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_effort: Mapped[float] = mapped_column(Float, default=0)
    actual_effort: Mapped[float] = mapped_column(Float, default=0)
    percent_complete: Mapped[int] = mapped_column(Integer, default=0)
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    acceptance_evidence: Mapped[str] = mapped_column(Text, default="")
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    indent_level: Mapped[int] = mapped_column(Integer, default=0)
    baseline_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BoardColumn(Base):
    __tablename__ = "board_columns"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_board_column_project_name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0)
    wip_limit: Mapped[int] = mapped_column(Integer, default=0)
    entry_criteria: Mapped[str] = mapped_column(Text, default="")
    exit_criteria: Mapped[str] = mapped_column(Text, default="")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TaskNoteRevision(Base):
    __tablename__ = "task_note_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text, default="")
    change_summary: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TaskComment(Base):
    __tablename__ = "task_comments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    mentions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TaskAttachment(Base):
    __tablename__ = "task_attachments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(300))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    media_type: Mapped[str] = mapped_column(String(160), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    sensitivity: Mapped[str] = mapped_column(String(60), default="Controlled Unclassified")
    category: Mapped[str] = mapped_column(String(60), default="Supporting Document")
    logical_file_id: Mapped[str] = mapped_column(String(36), default=uuid4, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TaskRelationship(Base):
    __tablename__ = "task_relationships"
    __table_args__ = (UniqueConstraint("source_task_id", "target_task_id", "relationship_type", name="uq_task_relationship"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    source_task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    target_task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(40), default="Finish-to-start")
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Milestone(Base):
    __tablename__ = "milestones"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    baseline_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Not Started")
    confidence: Mapped[str] = mapped_column(String(30), default="Medium")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    critical: Mapped[bool] = mapped_column(Boolean, default=False)


class RaidItem(Base):
    __tablename__ = "raid_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Open")
    severity: Mapped[str] = mapped_column(String(30), default="Medium")
    likelihood: Mapped[str] = mapped_column(String(30), default="Possible")
    consequence: Mapped[str] = mapped_column(Text, default="")
    exposure: Mapped[int] = mapped_column(Integer, default=0)
    mitigation: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    escalation_level: Mapped[str] = mapped_column(String(40), default="Project")
    impacted_missions: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    closure_rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Dependency(Base):
    __tablename__ = "dependencies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True)
    source_project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    target_project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(40), default="Open")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    impact: Mapped[str] = mapped_column(Text, default="")
    external_party: Mapped[str] = mapped_column(String(160), default="")


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True)
    demand_id: Mapped[str | None] = mapped_column(ForeignKey("demands.id"), nullable=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    decision: Mapped[str] = mapped_column(String(60))
    authority_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    participants: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text, default="")
    conditions: Mapped[str] = mapped_column(Text, default="")
    caveats: Mapped[str] = mapped_column(Text, default="")
    resource_implications: Mapped[str] = mapped_column(Text, default="")
    financial_implications: Mapped[str] = mapped_column(Text, default="")
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Action(Base):
    __tablename__ = "actions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    demand_id: Mapped[str | None] = mapped_column(ForeignKey("demands.id"), nullable=True)
    decision_id: Mapped[str | None] = mapped_column(ForeignKey("decisions.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(40), default="Open")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_type: Mapped[str] = mapped_column(String(60), default="Decision condition")


class ResourceCapacity(Base):
    __tablename__ = "resource_capacity"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    role_name: Mapped[str] = mapped_column(String(120))
    skill: Mapped[str] = mapped_column(String(120))
    period: Mapped[str] = mapped_column(String(20))
    capacity_hours: Mapped[float] = mapped_column(Float, default=0)
    allocated_hours: Mapped[float] = mapped_column(Float, default=0)
    actual_hours: Mapped[float] = mapped_column(Float, default=0)
    minimum_core_coverage: Mapped[float] = mapped_column(Float, default=0)


class FinancialRecord(Base):
    __tablename__ = "financial_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    demand_id: Mapped[str | None] = mapped_column(ForeignKey("demands.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(80), default="Program")
    approved_budget: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    actual_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    forecast: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    minimum_viable: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    full_requirement: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    funding_status: Mapped[str] = mapped_column(String(40), default="Funded")
    fiscal_year: Mapped[int] = mapped_column(Integer, default=2026)
    restricted_rate_notes: Mapped[str] = mapped_column(Text, default="")


class Benefit(Base):
    __tablename__ = "benefits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    demand_id: Mapped[str | None] = mapped_column(ForeignKey("demands.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    benefit_type: Mapped[str] = mapped_column(String(80), default="Operational")
    target_value: Mapped[float] = mapped_column(Float, default=0)
    realized_value: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(60), default="qualitative score")
    status: Mapped[str] = mapped_column(String(40), default="Expected")
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class ProjectTemplate(Base):
    __tablename__ = "project_templates"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_project_template_code_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    category: Mapped[str] = mapped_column(String(80), default="General")
    blueprint: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProjectPromotionRequest(Base):
    """Auditable request to move division-local work into portfolio governance."""
    __tablename__ = "project_promotion_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    requested_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    scope_change: Mapped[str] = mapped_column(Text, default="")
    enterprise_impact: Mapped[str] = mapped_column(Text, default="")
    funding_requirement: Mapped[str] = mapped_column(Text, default="")
    resource_requirement: Mapped[str] = mapped_column(Text, default="")
    schedule_risk: Mapped[str] = mapped_column(Text, default="")
    requested_portfolio_id: Mapped[str | None] = mapped_column(ForeignKey("portfolios.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Submitted", index=True)
    reviewed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision_rationale: Mapped[str] = mapped_column(Text, default="")
    conditions: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DashboardPreference(Base):
    """Server-side role lens and smart-grid preferences for a user's landing page."""
    __tablename__ = "dashboard_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_dashboard_preference_user"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    active_lens: Mapped[str] = mapped_column(String(80), default="")
    panel_order: Mapped[list[str]] = mapped_column(JSON, default=list)
    hidden_panels: Mapped[list[str]] = mapped_column(JSON, default=list)
    panel_sizes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StatusReport(Base):
    __tablename__ = "status_reports"
    __table_args__ = (UniqueConstraint("project_id", "period_end", "version", name="uq_status_report_period_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="Draft")
    health: Mapped[str] = mapped_column(String(30), default="On Track")
    percent_complete: Mapped[int] = mapped_column(Integer, default=0)
    accomplishments: Mapped[str] = mapped_column(Text, default="")
    planned_work: Mapped[str] = mapped_column(Text, default="")
    decisions_required: Mapped[str] = mapped_column(Text, default="")
    risks_and_dependencies: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    submitted_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(String(300), default="/")
    notification_type: Mapped[str] = mapped_column(String(50), default="Assignment")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    action: Mapped[str] = mapped_column(String(80))
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class RequirementTrace(Base):
    __tablename__ = "requirement_trace"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    requirement_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    domain: Mapped[str] = mapped_column(String(180), index=True)
    title: Mapped[str] = mapped_column(String(240))
    requirement: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20))
    phase: Mapped[str] = mapped_column(String(20), index=True)
    preliminary_fit: Mapped[str] = mapped_column(String(40))
    capability: Mapped[str] = mapped_column(String(180))
    accountable_owner: Mapped[str] = mapped_column(String(180))
    verification_method: Mapped[str] = mapped_column(String(80))
    source_status: Mapped[str] = mapped_column(String(40), default="Proposed")
    implementation_status: Mapped[str] = mapped_column(String(80), index=True)
    design_reference: Mapped[str] = mapped_column(String(240), default="")
    module_reference: Mapped[str] = mapped_column(String(240), default="")
    test_case: Mapped[str] = mapped_column(String(240), default="")
    uat_result: Mapped[str] = mapped_column(String(80), default="Not Run")
    release: Mapped[str] = mapped_column(String(80), default="Roadmap")
    acceptance_notes: Mapped[str] = mapped_column(Text, default="")
    decision_comments: Mapped[str] = mapped_column(Text, default="")


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(String(240))
    template_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="Preview")
    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    rows_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImportRow(Base):
    __tablename__ = "import_rows"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id"), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    record_identifier: Mapped[str] = mapped_column(String(100), default="")
    action_taken: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(30))
    validation_message: Mapped[str] = mapped_column(Text)
    corrective_guidance: Mapped[str] = mapped_column(Text, default="")


class SavedView(Base):
    __tablename__ = "saved_views"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_saved_view_user_name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    route: Mapped[str] = mapped_column(String(160))
    query_string: Mapped[str] = mapped_column(Text, default="")


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    definition: Mapped[str] = mapped_column(Text)
    formula: Mapped[str] = mapped_column(Text)
    data_owner: Mapped[str] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(160), default="DDC5I-PM PostgreSQL")
    thresholds: Mapped[str] = mapped_column(Text, default="")
    limitations: Mapped[str] = mapped_column(Text, default="")
    last_refresh: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Delegation(Base):
    __tablename__ = "delegations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    delegator_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    delegate_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    org_scope_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    kind: Mapped[str] = mapped_column(String(80), default="ProjectOS")
    base_url: Mapped[str] = mapped_column(String(500), default="")
    mode: Mapped[str] = mapped_column(String(40), default="Mock")
    auth_type: Mapped[str] = mapped_column(String(40), default="None")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(40), default="Not Tested")
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FieldOwnershipRuleRecord(Base):
    __tablename__ = "field_ownership_rules"
    __table_args__ = (UniqueConstraint("entity_type", "field_name", name="uq_field_ownership_entity_field"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    field_name: Mapped[str] = mapped_column(String(120), index=True)
    authoritative_system: Mapped[str] = mapped_column(String(120))
    allowed_writers: Mapped[list[str]] = mapped_column(JSON, default=list)
    conflict_policy: Mapped[str] = mapped_column(String(80), default="Reject and reconcile")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SyncRun(Base):
    __tablename__ = "sync_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    connection_id: Mapped[str] = mapped_column(ForeignKey("integration_connections.id"), index=True)
    direction: Mapped[str] = mapped_column(String(30), default="Outbound")
    entity_type: Mapped[str] = mapped_column(String(80), default="Project")
    canonical_id: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(40), default="Queued")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PortfolioReview(Base):
    __tablename__ = "portfolio_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    review_type: Mapped[str] = mapped_column(String(80), default="Portfolio Review")
    portfolio_id: Mapped[str | None] = mapped_column(ForeignKey("portfolios.id"), nullable=True)
    org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    chair_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    participant_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    agenda: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    decisions_required: Mapped[str] = mapped_column(Text, default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PortfolioReviewItem(Base):
    __tablename__ = "portfolio_review_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    review_id: Mapped[str] = mapped_column(ForeignKey("portfolio_reviews.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(60), default="Decision")
    entity_type: Mapped[str] = mapped_column(String(60), default="Project")
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(240))
    recommendation: Mapped[str] = mapped_column(String(80), default="Continue")
    rationale: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Open")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    decision_id: Mapped[str | None] = mapped_column(ForeignKey("decisions.id"), nullable=True)
    action_id: Mapped[str | None] = mapped_column(ForeignKey("actions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BriefingSection(Base):
    __tablename__ = "briefing_sections"
    __table_args__ = (UniqueConstraint("review_id", "section_key", name="uq_briefing_section_review_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    review_id: Mapped[str] = mapped_column(ForeignKey("portfolio_reviews.id"), index=True)
    section_key: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200))
    narrative: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Not Started")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    source_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BriefingSnapshot(Base):
    __tablename__ = "briefing_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    review_id: Mapped[str] = mapped_column(ForeignKey("portfolio_reviews.id"), unique=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    captured_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewQuestion(Base):
    __tablename__ = "review_questions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("portfolio_reviews.id"), index=True)
    section_id: Mapped[str | None] = mapped_column(ForeignKey("briefing_sections.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(60), default="")
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    question: Mapped[str] = mapped_column(Text)
    asked_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    assigned_to_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    priority: Mapped[str] = mapped_column(String(30), default="Normal")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    response: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="Open")
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewChangeRequest(Base):
    __tablename__ = "review_change_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("portfolio_reviews.id"), index=True)
    section_id: Mapped[str | None] = mapped_column(ForeignKey("briefing_sections.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(60), default="")
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    field_name: Mapped[str] = mapped_column(String(120), default="")
    current_value: Mapped[str] = mapped_column(Text, default="")
    proposed_value: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    requested_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Open")
    resolution: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewNote(Base):
    __tablename__ = "review_notes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    review_id: Mapped[str] = mapped_column(ForeignKey("portfolio_reviews.id"), index=True)
    section_id: Mapped[str | None] = mapped_column(ForeignKey("briefing_sections.id"), nullable=True)
    note_type: Mapped[str] = mapped_column(String(40), default="Discussion")
    body: Mapped[str] = mapped_column(Text)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ResourceRequest(Base):
    __tablename__ = "resource_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    role_name: Mapped[str] = mapped_column(String(120))
    skill: Mapped[str] = mapped_column(String(120), default="")
    requested_hours: Mapped[float] = mapped_column(Float, default=0)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(30), default="Medium")
    status: Mapped[str] = mapped_column(String(40), default="Submitted")
    requested_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approver_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    rationale: Mapped[str] = mapped_column(Text, default="")
    resolution: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    financial_record_id: Mapped[str] = mapped_column(ForeignKey("financial_records.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(60), default="Commitment")
    amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    transaction_date: Mapped[date] = mapped_column(Date)
    reference: Mapped[str] = mapped_column(String(160), default="")
    source_system: Mapped[str] = mapped_column(String(80), default="DDC5I-PM")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(240))
    scenario_type: Mapped[str] = mapped_column(String(80), default="Portfolio What-if")
    org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    baseline_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    assumptions: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ScenarioChange(Base):
    __tablename__ = "scenario_changes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(80))
    field_name: Mapped[str] = mapped_column(String(80))
    baseline_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    proposed_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ScenarioResult(Base):
    __tablename__ = "scenario_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), index=True)
    metric_key: Mapped[str] = mapped_column(String(100))
    baseline_value: Mapped[float] = mapped_column(Float, default=0)
    scenario_value: Mapped[float] = mapped_column(Float, default=0)
    delta: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(40), default="count")
    impact_level: Mapped[str] = mapped_column(String(30), default="Informational")
    explanation: Mapped[str] = mapped_column(Text, default="")


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    rule_code: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    severity: Mapped[str] = mapped_column(String(30), default="Medium")
    status: Mapped[str] = mapped_column(String(40), default="Open")
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    disposition: Mapped[str] = mapped_column(Text, default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportPack(Base):
    __tablename__ = "report_packs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    human_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(240))
    pack_type: Mapped[str] = mapped_column(String(80), default="Executive Portfolio Summary")
    org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    narrative: Mapped[str] = mapped_column(Text, default="")
    generated_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class JobRun(Base):
    __tablename__ = "job_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(40), default="Queued")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
