"""Division identity, banners, and profiles v0.7.5.

Revision ID: 0007_division_experience_v075
Revises: 0006_division_briefing_v070
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0007_division_experience_v075"
down_revision = "0006_division_briefing_v070"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not inspect(bind).has_table("division_profiles"):
        op.create_table(
            "division_profiles",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, unique=True),
            sa.Column("mission", sa.Text(), nullable=False, server_default=""),
            sa.Column("vision", sa.Text(), nullable=False, server_default=""),
            sa.Column("focus_areas", sa.JSON(), nullable=False),
            sa.Column("responsibilities", sa.JSON(), nullable=False),
            sa.Column("branches", sa.JSON(), nullable=False),
            sa.Column("initiatives", sa.JSON(), nullable=False),
            sa.Column("relationships", sa.JSON(), nullable=False),
            sa.Column("forums", sa.JSON(), nullable=False),
            sa.Column("doctrine", sa.JSON(), nullable=False),
            sa.Column("banner_asset", sa.String(240), nullable=False, server_default=""),
            sa.Column("banner_alt", sa.Text(), nullable=False, server_default=""),
            sa.Column("focal_x", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("focal_y", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("status", sa.String(30), nullable=False, server_default="Published"),
            sa.Column("source_documents", sa.JSON(), nullable=False),
            sa.Column("source_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_division_profiles_org_id", "division_profiles", ["org_id"], unique=True)

    # Correct the authoritative display names without changing stable codes or IDs.
    names = {
        "CID": "Coalition Interoperability Division",
        "JFID": "Joint Fires Integration Division",
        "C3OD2": "Cyber & C2 Operational Development Division",
    }
    orgs = sa.table("organizations", sa.column("code", sa.String), sa.column("name", sa.String))
    for code, name in names.items():
        op.execute(orgs.update().where(orgs.c.code == code).values(name=name))


def downgrade():
    bind = op.get_bind()
    if inspect(bind).has_table("division_profiles"):
        op.drop_table("division_profiles")
