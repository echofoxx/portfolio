"""Travel, engagement outcomes, and trip reports v0.7.6.

Revision ID: 0008_travel_engagements_v076
Revises: 0007_division_experience_v075
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0008_travel_engagements_v076"
down_revision = "0007_division_experience_v075"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("travel_engagements"):
        op.create_table(
            "travel_engagements",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("human_id", sa.String(40), nullable=False, unique=True),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("normalized_title", sa.String(300), nullable=False, server_default=""),
            sa.Column("location", sa.String(240), nullable=False, server_default=""),
            sa.Column("country_code", sa.String(8), nullable=False, server_default=""),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="Planned"),
            sa.Column("lead_org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("cross_division", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("source_system", sa.String(100), nullable=False, server_default="Travel Approval Export"),
            sa.Column("source_record", sa.String(160), nullable=False, server_default=""),
            sa.Column("source_filename", sa.String(260), nullable=False, server_default=""),
            sa.Column("source_row", sa.Integer(), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        for name, cols in [
            ("ix_travel_engagements_human_id", ["human_id"]),
            ("ix_travel_engagements_title", ["title"]),
            ("ix_travel_engagements_normalized_title", ["normalized_title"]),
            ("ix_travel_engagements_lead_org_id", ["lead_org_id"]),
        ]:
            op.create_index(name, "travel_engagements", cols, unique=(cols == ["human_id"]))

    if not inspector.has_table("travel_requests"):
        op.create_table(
            "travel_requests",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("human_id", sa.String(40), nullable=False, unique=True),
            sa.Column("external_id", sa.String(100), nullable=False),
            sa.Column("engagement_id", sa.String(36), sa.ForeignKey("travel_engagements.id"), nullable=True),
            sa.Column("traveler_name", sa.String(220), nullable=False),
            sa.Column("traveler_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("location", sa.String(240), nullable=False, server_default=""),
            sa.Column("determination", sa.String(40), nullable=False, server_default="Pending"),
            sa.Column("departure_date", sa.Date(), nullable=False),
            sa.Column("return_date", sa.Date(), nullable=False),
            sa.Column("estimated_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("purpose_roi", sa.Text(), nullable=False, server_default=""),
            sa.Column("impact_if_not", sa.Text(), nullable=False, server_default=""),
            sa.Column("funding", sa.String(120), nullable=False, server_default=""),
            sa.Column("exemption_category", sa.Text(), nullable=False, server_default=""),
            sa.Column("report_required", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("report_due_date", sa.Date(), nullable=True),
            sa.Column("sensitivity", sa.String(40), nullable=False, server_default="Controlled Unclassified"),
            sa.Column("source_system", sa.String(100), nullable=False, server_default="Travel Approval Export"),
            sa.Column("source_record", sa.String(160), nullable=False, server_default=""),
            sa.Column("source_filename", sa.String(260), nullable=False, server_default=""),
            sa.Column("source_row", sa.Integer(), nullable=True),
            sa.Column("import_batch_id", sa.String(36), sa.ForeignKey("import_batches.id"), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("source_system", "external_id", name="uq_travel_request_source_external"),
        )
        for name, cols in [
            ("ix_travel_requests_human_id", ["human_id"]),
            ("ix_travel_requests_external_id", ["external_id"]),
            ("ix_travel_requests_engagement_id", ["engagement_id"]),
            ("ix_travel_requests_traveler_name", ["traveler_name"]),
            ("ix_travel_requests_org_id", ["org_id"]),
            ("ix_travel_requests_determination", ["determination"]),
            ("ix_travel_requests_departure_date", ["departure_date"]),
            ("ix_travel_requests_return_date", ["return_date"]),
        ]:
            op.create_index(name, "travel_requests", cols, unique=(cols == ["human_id"]))

    if not inspector.has_table("travel_approval_steps"):
        op.create_table(
            "travel_approval_steps",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("request_id", sa.String(36), sa.ForeignKey("travel_requests.id"), nullable=False),
            sa.Column("step_order", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("approver_name", sa.String(220), nullable=False, server_default=""),
            sa.Column("approver_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("approver_role", sa.String(100), nullable=False, server_default=""),
            sa.Column("determination", sa.String(40), nullable=False, server_default="Pending"),
            sa.Column("comments", sa.Text(), nullable=False, server_default=""),
            sa.Column("determination_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("request_id", "step_order", name="uq_travel_approval_request_step"),
        )
        op.create_index("ix_travel_approval_steps_request_id", "travel_approval_steps", ["request_id"])

    if not inspector.has_table("trip_reports"):
        op.create_table(
            "trip_reports",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("human_id", sa.String(40), nullable=False, unique=True),
            sa.Column("request_id", sa.String(36), sa.ForeignKey("travel_requests.id"), nullable=True),
            sa.Column("engagement_id", sa.String(36), sa.ForeignKey("travel_engagements.id"), nullable=True),
            sa.Column("traveler_name", sa.String(220), nullable=False),
            sa.Column("traveler_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("return_date", sa.Date(), nullable=False),
            sa.Column("location", sa.String(240), nullable=False, server_default=""),
            sa.Column("purpose_objectives", sa.Text(), nullable=False, server_default=""),
            sa.Column("discussion", sa.Text(), nullable=False, server_default=""),
            sa.Column("key_findings", sa.Text(), nullable=False, server_default=""),
            sa.Column("recommendations", sa.Text(), nullable=False, server_default=""),
            sa.Column("action_items", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(40), nullable=False, server_default="Submitted"),
            sa.Column("review_status", sa.String(40), nullable=False, server_default="Awaiting Review"),
            sa.Column("review_comments", sa.Text(), nullable=False, server_default=""),
            sa.Column("reviewed_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sensitivity", sa.String(40), nullable=False, server_default="Controlled Unclassified"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("match_status", sa.String(40), nullable=False, server_default="Unmatched"),
            sa.Column("match_confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("match_rationale", sa.Text(), nullable=False, server_default=""),
            sa.Column("matched_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("source_system", sa.String(100), nullable=False, server_default="Trip Reports SharePoint"),
            sa.Column("source_record", sa.String(260), nullable=False, server_default=""),
            sa.Column("source_filename", sa.String(260), nullable=False, server_default=""),
            sa.Column("source_row", sa.Integer(), nullable=True),
            sa.Column("import_batch_id", sa.String(36), sa.ForeignKey("import_batches.id"), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        for name, cols in [
            ("ix_trip_reports_human_id", ["human_id"]),
            ("ix_trip_reports_request_id", ["request_id"]),
            ("ix_trip_reports_engagement_id", ["engagement_id"]),
            ("ix_trip_reports_traveler_name", ["traveler_name"]),
            ("ix_trip_reports_org_id", ["org_id"]),
            ("ix_trip_reports_title", ["title"]),
            ("ix_trip_reports_match_status", ["match_status"]),
        ]:
            op.create_index(name, "trip_reports", cols, unique=(cols == ["human_id"]))

    if not inspector.has_table("trip_report_items"):
        op.create_table(
            "trip_report_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("human_id", sa.String(40), nullable=False, unique=True),
            sa.Column("report_id", sa.String(36), sa.ForeignKey("trip_reports.id"), nullable=False),
            sa.Column("item_type", sa.String(60), nullable=False, server_default="Finding"),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("title", sa.String(260), nullable=False, server_default=""),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="Candidate"),
            sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("promoted_entity_type", sa.String(60), nullable=False, server_default=""),
            sa.Column("promoted_entity_id", sa.String(80), nullable=False, server_default=""),
            sa.Column("source_excerpt", sa.Text(), nullable=False, server_default=""),
            sa.Column("reviewed_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_trip_report_items_human_id", "trip_report_items", ["human_id"], unique=True)
        op.create_index("ix_trip_report_items_report_id", "trip_report_items", ["report_id"])
        op.create_index("ix_trip_report_items_item_type", "trip_report_items", ["item_type"])

    if not inspector.has_table("travel_entity_links"):
        op.create_table(
            "travel_entity_links",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("source_entity_type", sa.String(60), nullable=False),
            sa.Column("source_entity_id", sa.String(80), nullable=False),
            sa.Column("target_entity_type", sa.String(60), nullable=False),
            sa.Column("target_entity_id", sa.String(80), nullable=False),
            sa.Column("link_type", sa.String(80), nullable=False, server_default="Related"),
            sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("source_entity_type", "source_entity_id", "target_entity_type", "target_entity_id", name="uq_travel_entity_link"),
        )
        for col in ("source_entity_type", "source_entity_id", "target_entity_type", "target_entity_id"):
            op.create_index(f"ix_travel_entity_links_{col}", "travel_entity_links", [col])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    for table in ["travel_entity_links", "trip_report_items", "trip_reports", "travel_approval_steps", "travel_requests", "travel_engagements"]:
        if inspector.has_table(table):
            op.drop_table(table)
