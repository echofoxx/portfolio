"""Portfolio governance and enterprise integration v0.5.0.

Revision ID: 0005_portfolio_governance_v050
Revises: 0004_execution_roadmap_v040
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0005_portfolio_governance_v050"
down_revision = "0004_execution_roadmap_v040"
branch_labels = None
depends_on = None


def _create_if_missing(name: str, *columns, indexes: tuple[tuple[str, list[str]], ...] = ()) -> None:
    bind = op.get_bind()
    if inspect(bind).has_table(name):
        return
    op.create_table(name, *columns)
    for index_name, fields in indexes:
        op.create_index(index_name, name, fields)


def upgrade():
    now = datetime.now(timezone.utc)
    _create_if_missing(
        "delegations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("delegator_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("delegate_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("roles", sa.JSON(), nullable=False),
        sa.Column("org_scope_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(("ix_delegations_delegator_id", ["delegator_id"]), ("ix_delegations_delegate_id", ["delegate_id"])),
    )
    _create_if_missing(
        "integration_connections",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("code", sa.String(60), nullable=False, unique=True),
        sa.Column("name", sa.String(180), nullable=False), sa.Column("kind", sa.String(80), nullable=False, server_default="ProjectOS"),
        sa.Column("base_url", sa.String(500), nullable=False, server_default=""), sa.Column("mode", sa.String(40), nullable=False, server_default="Mock"),
        sa.Column("auth_type", sa.String(40), nullable=False, server_default="None"), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(40), nullable=False, server_default="Not Tested"), sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(("ix_integration_connections_code", ["code"]),),
    )
    _create_if_missing(
        "field_ownership_rules",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("field_name", sa.String(120), nullable=False), sa.Column("authoritative_system", sa.String(120), nullable=False),
        sa.Column("allowed_writers", sa.JSON(), nullable=False), sa.Column("conflict_policy", sa.String(80), nullable=False, server_default="Reject and reconcile"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("entity_type", "field_name", name="uq_field_ownership_entity_field"),
        indexes=(("ix_field_ownership_rules_entity_type", ["entity_type"]), ("ix_field_ownership_rules_field_name", ["field_name"])),
    )
    _create_if_missing(
        "sync_runs",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("connection_id", sa.String(36), sa.ForeignKey("integration_connections.id"), nullable=False),
        sa.Column("direction", sa.String(30), nullable=False, server_default="Outbound"), sa.Column("entity_type", sa.String(80), nullable=False, server_default="Project"),
        sa.Column("canonical_id", sa.String(80), nullable=False, server_default=""), sa.Column("status", sa.String(40), nullable=False, server_default="Queued"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True), indexes=(("ix_sync_runs_connection_id", ["connection_id"]),),
    )
    _create_if_missing(
        "portfolio_reviews",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("human_id", sa.String(40), nullable=False, unique=True),
        sa.Column("title", sa.String(240), nullable=False), sa.Column("review_type", sa.String(80), nullable=False, server_default="Portfolio Review"),
        sa.Column("portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id"), nullable=True), sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False), sa.Column("period_end", sa.Date(), nullable=False), sa.Column("status", sa.String(40), nullable=False, server_default="Draft"),
        sa.Column("chair_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("participant_ids", sa.JSON(), nullable=False),
        sa.Column("agenda", sa.JSON(), nullable=False), sa.Column("summary", sa.Text(), nullable=False, server_default=""), sa.Column("decisions_required", sa.Text(), nullable=False, server_default=""),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(("ix_portfolio_reviews_human_id", ["human_id"]),),
    )
    _create_if_missing(
        "portfolio_review_items",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("review_id", sa.String(36), sa.ForeignKey("portfolio_reviews.id"), nullable=False),
        sa.Column("item_type", sa.String(60), nullable=False, server_default="Decision"), sa.Column("entity_type", sa.String(60), nullable=False, server_default="Project"),
        sa.Column("entity_id", sa.String(80), nullable=False, server_default=""), sa.Column("title", sa.String(240), nullable=False),
        sa.Column("recommendation", sa.String(80), nullable=False, server_default="Continue"), sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True), sa.Column("status", sa.String(40), nullable=False, server_default="Open"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), sa.Column("decision_id", sa.String(36), sa.ForeignKey("decisions.id"), nullable=True),
        sa.Column("action_id", sa.String(36), sa.ForeignKey("actions.id"), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(("ix_portfolio_review_items_review_id", ["review_id"]),),
    )
    _create_if_missing(
        "resource_requests",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("human_id", sa.String(40), nullable=False, unique=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False), sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("role_name", sa.String(120), nullable=False), sa.Column("skill", sa.String(120), nullable=False, server_default=""),
        sa.Column("requested_hours", sa.Float(), nullable=False, server_default="0"), sa.Column("period_start", sa.Date(), nullable=False), sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("priority", sa.String(30), nullable=False, server_default="Medium"), sa.Column("status", sa.String(40), nullable=False, server_default="Submitted"),
        sa.Column("requested_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("approver_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""), sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(("ix_resource_requests_human_id", ["human_id"]), ("ix_resource_requests_org_id", ["org_id"])),
    )
    _create_if_missing(
        "financial_transactions",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("human_id", sa.String(40), nullable=False, unique=True),
        sa.Column("financial_record_id", sa.String(36), sa.ForeignKey("financial_records.id"), nullable=False), sa.Column("transaction_type", sa.String(60), nullable=False, server_default="Commitment"),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"), sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(160), nullable=False, server_default=""), sa.Column("source_system", sa.String(80), nullable=False, server_default="DDC5I-PM"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""), sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), indexes=(("ix_financial_transactions_human_id", ["human_id"]), ("ix_financial_transactions_financial_record_id", ["financial_record_id"])),
    )
    _create_if_missing(
        "scenarios",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("human_id", sa.String(40), nullable=False, unique=True), sa.Column("name", sa.String(240), nullable=False),
        sa.Column("scenario_type", sa.String(80), nullable=False, server_default="Portfolio What-if"), sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("baseline_date", sa.Date(), nullable=False), sa.Column("status", sa.String(40), nullable=False, server_default="Draft"), sa.Column("assumptions", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("approved_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), indexes=(("ix_scenarios_human_id", ["human_id"]),),
    )
    _create_if_missing(
        "scenario_changes",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("scenario_id", sa.String(36), sa.ForeignKey("scenarios.id"), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False), sa.Column("entity_id", sa.String(80), nullable=False), sa.Column("field_name", sa.String(80), nullable=False),
        sa.Column("baseline_value", sa.JSON(), nullable=True), sa.Column("proposed_value", sa.JSON(), nullable=True), sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), indexes=(("ix_scenario_changes_scenario_id", ["scenario_id"]),),
    )
    _create_if_missing(
        "scenario_results",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("scenario_id", sa.String(36), sa.ForeignKey("scenarios.id"), nullable=False),
        sa.Column("metric_key", sa.String(100), nullable=False), sa.Column("baseline_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("scenario_value", sa.Float(), nullable=False, server_default="0"), sa.Column("delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(40), nullable=False, server_default="count"), sa.Column("impact_level", sa.String(30), nullable=False, server_default="Informational"),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""), indexes=(("ix_scenario_results_scenario_id", ["scenario_id"]),),
    )
    _create_if_missing(
        "data_quality_issues",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("human_id", sa.String(40), nullable=False, unique=True),
        sa.Column("rule_code", sa.String(60), nullable=False), sa.Column("entity_type", sa.String(60), nullable=False), sa.Column("entity_id", sa.String(80), nullable=False),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True), sa.Column("severity", sa.String(30), nullable=False, server_default="Medium"),
        sa.Column("status", sa.String(40), nullable=False, server_default="Open"), sa.Column("title", sa.String(240), nullable=False), sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True), sa.Column("due_date", sa.Date(), nullable=True), sa.Column("disposition", sa.Text(), nullable=False, server_default=""),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False), sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        indexes=(("ix_data_quality_issues_human_id", ["human_id"]), ("ix_data_quality_issues_rule_code", ["rule_code"]), ("ix_data_quality_issues_entity_id", ["entity_id"])),
    )
    _create_if_missing(
        "report_packs",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("human_id", sa.String(40), nullable=False, unique=True), sa.Column("name", sa.String(240), nullable=False),
        sa.Column("pack_type", sa.String(80), nullable=False, server_default="Executive Portfolio Summary"), sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False), sa.Column("period_end", sa.Date(), nullable=False), sa.Column("status", sa.String(40), nullable=False, server_default="Draft"),
        sa.Column("sections", sa.JSON(), nullable=False), sa.Column("narrative", sa.Text(), nullable=False, server_default=""), sa.Column("generated_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True), sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), indexes=(("ix_report_packs_human_id", ["human_id"]),),
    )
    _create_if_missing(
        "job_runs",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("job_type", sa.String(100), nullable=False), sa.Column("status", sa.String(40), nullable=False, server_default="Queued"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True), sa.Column("started_at", sa.DateTime(timezone=True), nullable=True), sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False, server_default=""), sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), indexes=(("ix_job_runs_job_type", ["job_type"]),),
    )

    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("integration_connections"):
        count = bind.execute(sa.text("SELECT COUNT(*) FROM integration_connections")).scalar_one()
        if not count:
            admin_id = bind.execute(sa.text("SELECT id FROM users WHERE username='admin' LIMIT 1")).scalar()
            for code, name, kind, mode in [
                ("PROJECTOS-MOCK", "ProjectOS Local Sandbox", "ProjectOS", "Mock"),
                ("M365", "Microsoft 365 / Graph", "Microsoft Graph", "Disabled"),
                ("SHAREPOINT", "SharePoint", "SharePoint", "Disabled"),
            ]:
                bind.execute(sa.text("""INSERT INTO integration_connections
                  (id,code,name,kind,base_url,mode,auth_type,enabled,status,configuration,last_health_at,created_by_id,created_at,updated_at)
                  VALUES (:id,:code,:name,:kind,'',:mode,'None',:enabled,'Not Tested',:config,NULL,:admin,:created,:created)"""),
                  {"id":str(uuid.uuid4()),"code":code,"name":name,"kind":kind,"mode":mode,"enabled":mode=="Mock","config":"{}","admin":admin_id,"created":now})
    if inspector.has_table("field_ownership_rules"):
        count = bind.execute(sa.text("SELECT COUNT(*) FROM field_ownership_rules")).scalar_one()
        if not count:
            rules = [
                ("Demand","status","DDC5I-PM",'["DDC5I-PM"]'),
                ("Project","portfolio_id","DDC5I-PM",'["DDC5I-PM"]'),
                ("Task","percent_complete","ProjectOS",'["ProjectOS"]'),
                ("FinancialRecord","actual_cost","Financial System",'["Financial System"]'),
                ("User","employment_status","Workforce System",'["Workforce System"]'),
            ]
            for entity, field, authority, writers in rules:
                bind.execute(sa.text("""INSERT INTO field_ownership_rules
                  (id,entity_type,field_name,authoritative_system,allowed_writers,conflict_policy,active,created_at)
                  VALUES (:id,:entity,:field,:authority,:writers,'Reject and reconcile',:active,:created)"""),
                  {"id":str(uuid.uuid4()),"entity":entity,"field":field,"authority":authority,"writers":writers,"active":True,"created":now})
    if inspector.has_table("requirement_trace"):
        updates = [
            ("GOV-001", "Partially implemented", "Administration, delegations, portfolio reviews, data-quality ownership, and audit are operational; enterprise identity remains integration-dependent."),
            ("INT-001", "Partially implemented", "Persistent connection registry, field ownership, dry-run ProjectOS synchronization, run history, retry evidence, and reconciliation status are operational."),
            ("RES-001", "Partially implemented", "Resource requests, approval workflow, capacity visibility, and over-allocation analysis are operational; authoritative workforce integration remains planned."),
            ("FIN-001", "Partially implemented", "Commitment, obligation, expenditure, and forecast-adjustment transactions are operational; authoritative financial-system integration remains planned."),
        ]
        for requirement_id, status, notes in updates:
            bind.execute(sa.text("""UPDATE requirement_trace SET implementation_status=:status, release='0.5.0',
              design_reference='docs/USER_GUIDE.md#v050-portfolio-governance',
              module_reference='app/main.py; app/models.py; app/templates/portfolio_reviews.html; app/templates/scenarios.html; app/templates/integrations.html',
              test_case='tests/test_v050.py', uat_result='Automated test passed', acceptance_notes=:notes
              WHERE requirement_id=:requirement_id"""), {"status":status,"notes":notes,"requirement_id":requirement_id})


def downgrade():
    # Restore the pre-upgrade database backup instead of dropping v0.5 governance evidence.
    pass
