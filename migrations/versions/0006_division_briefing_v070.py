"""Division briefing and interactive review workspace v0.7.0.

Revision ID: 0006_division_briefing_v070
Revises: 0005_portfolio_governance_v050
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0006_division_briefing_v070"
down_revision = "0005_portfolio_governance_v050"
branch_labels = None
depends_on = None


def _create_if_missing(name: str, *columns, indexes: tuple[tuple[str, list[str]], ...] = (), constraints: tuple = ()) -> None:
    bind = op.get_bind()
    if inspect(bind).has_table(name):
        return
    op.create_table(name, *columns, *constraints)
    for index_name, fields in indexes:
        op.create_index(index_name, name, fields)


def upgrade():
    _create_if_missing(
        "briefing_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("review_id", sa.String(36), sa.ForeignKey("portfolio_reviews.id"), nullable=False),
        sa.Column("section_key", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="Not Started"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_summary", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(("ix_briefing_sections_review_id", ["review_id"]),),
        constraints=(sa.UniqueConstraint("review_id", "section_key", name="uq_briefing_section_review_key"),),
    )
    _create_if_missing(
        "briefing_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("review_id", sa.String(36), sa.ForeignKey("portfolio_reviews.id"), nullable=False, unique=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("captured_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(("ix_briefing_snapshots_review_id", ["review_id"]),),
    )
    _create_if_missing(
        "review_questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("human_id", sa.String(40), nullable=False, unique=True),
        sa.Column("review_id", sa.String(36), sa.ForeignKey("portfolio_reviews.id"), nullable=False),
        sa.Column("section_id", sa.String(36), sa.ForeignKey("briefing_sections.id"), nullable=True),
        sa.Column("entity_type", sa.String(60), nullable=False, server_default=""),
        sa.Column("entity_id", sa.String(80), nullable=False, server_default=""),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("asked_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("priority", sa.String(30), nullable=False, server_default="Normal"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("response", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(40), nullable=False, server_default="Open"),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(("ix_review_questions_human_id", ["human_id"]), ("ix_review_questions_review_id", ["review_id"])),
    )
    _create_if_missing(
        "review_change_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("human_id", sa.String(40), nullable=False, unique=True),
        sa.Column("review_id", sa.String(36), sa.ForeignKey("portfolio_reviews.id"), nullable=False),
        sa.Column("section_id", sa.String(36), sa.ForeignKey("briefing_sections.id"), nullable=True),
        sa.Column("entity_type", sa.String(60), nullable=False, server_default=""),
        sa.Column("entity_id", sa.String(80), nullable=False, server_default=""),
        sa.Column("field_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("current_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("requested_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="Open"),
        sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(("ix_review_change_requests_human_id", ["human_id"]), ("ix_review_change_requests_review_id", ["review_id"])),
    )
    _create_if_missing(
        "review_notes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("review_id", sa.String(36), sa.ForeignKey("portfolio_reviews.id"), nullable=False),
        sa.Column("section_id", sa.String(36), sa.ForeignKey("briefing_sections.id"), nullable=True),
        sa.Column("note_type", sa.String(40), nullable=False, server_default="Discussion"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(("ix_review_notes_review_id", ["review_id"]),),
    )


def downgrade():
    for table in ["review_notes", "review_change_requests", "review_questions", "briefing_snapshots", "briefing_sections"]:
        if inspect(op.get_bind()).has_table(table):
            op.drop_table(table)
