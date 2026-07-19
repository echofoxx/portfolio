"""Self-service projects, promotion, dashboard preferences, and division reconciliation v0.8.0.

Revision ID: 0009_self_service_v080
Revises: 0008_travel_engagements_v076
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0009_self_service_v080"
down_revision = "0008_travel_engagements_v076"
branch_labels = None
depends_on = None


def _columns(bind, table: str) -> set[str]:
    return {column["name"] for column in inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    project_columns = _columns(bind, "projects")
    additions = [
        ("governance_level", sa.Column("governance_level", sa.String(40), nullable=False, server_default="Portfolio Managed")),
        ("funding_posture", sa.Column("funding_posture", sa.String(40), nullable=False, server_default="Existing Funding")),
        ("resource_posture", sa.Column("resource_posture", sa.String(40), nullable=False, server_default="Existing Capacity")),
        ("promotion_status", sa.Column("promotion_status", sa.String(40), nullable=False, server_default="Not Required")),
        ("created_by_id", sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True)),
    ]
    for name, column in additions:
        if name not in project_columns:
            op.add_column("projects", column)
    op.execute(sa.text("UPDATE projects SET governance_level = 'Division Local' WHERE portfolio_id IS NULL AND governance_level = 'Portfolio Managed'"))

    inspector = inspect(bind)
    if not inspector.has_table("project_promotion_requests"):
        op.create_table(
            "project_promotion_requests",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("human_id", sa.String(40), nullable=False, unique=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("requested_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("scope_change", sa.Text(), nullable=False, server_default=""),
            sa.Column("enterprise_impact", sa.Text(), nullable=False, server_default=""),
            sa.Column("funding_requirement", sa.Text(), nullable=False, server_default=""),
            sa.Column("resource_requirement", sa.Text(), nullable=False, server_default=""),
            sa.Column("schedule_risk", sa.Text(), nullable=False, server_default=""),
            sa.Column("requested_portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id"), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="Submitted"),
            sa.Column("reviewed_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("decision_rationale", sa.Text(), nullable=False, server_default=""),
            sa.Column("conditions", sa.Text(), nullable=False, server_default=""),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_project_promotion_requests_project_id", "project_promotion_requests", ["project_id"])
        op.create_index("ix_project_promotion_requests_status", "project_promotion_requests", ["status"])

    if not inspector.has_table("dashboard_preferences"):
        op.create_table(
            "dashboard_preferences",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
            sa.Column("active_lens", sa.String(80), nullable=False, server_default=""),
            sa.Column("panel_order", sa.JSON(), nullable=False),
            sa.Column("hidden_panels", sa.JSON(), nullable=False),
            sa.Column("panel_sizes", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_dashboard_preferences_user_id", "dashboard_preferences", ["user_id"], unique=True)

    # Promote travel-source placeholders without changing their stable row IDs.
    orgs = sa.table(
        "organizations",
        sa.column("code", sa.String), sa.column("name", sa.String), sa.column("narrative", sa.Text),
    )
    existing_fo = bind.execute(sa.text("SELECT 1 FROM organizations WHERE code='FO'")).first()
    if not existing_fo:
        op.execute(orgs.update().where(orgs.c.code == "FRONT").values(code="FO"))
    op.execute(orgs.update().where(orgs.c.code == "FO").values(
        name="DDC5I Front Office",
        narrative="Provides executive leadership, strategic direction, and decision support to integrate C5I priorities across the Joint Force.",
    ))
    op.execute(orgs.update().where(orgs.c.code == "CCD").values(
        name="Command & Control Capabilities Division",
        narrative="Leads joint C2 requirements, CJADC2 priorities, capability sponsorship, and end-to-end traceability from operational need to fielded solution.",
    ))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("dashboard_preferences"):
        op.drop_table("dashboard_preferences")
    if inspector.has_table("project_promotion_requests"):
        op.drop_table("project_promotion_requests")
    project_columns = _columns(bind, "projects")
    for name in ("created_by_id", "promotion_status", "resource_posture", "funding_posture", "governance_level"):
        if name in project_columns:
            op.drop_column("projects", name)
