"""Execution management, configurable boards, documents, templates, and status reporting.

Revision ID: 0004_execution_roadmap_v040
Revises: 0003_v031_reliability_hotfix
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_execution_roadmap_v040"
down_revision = "0003_v031_reliability_hotfix"
branch_labels = None
depends_on = None


def _columns(bind, table: str) -> set[str]:
    inspector = inspect(bind)
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade():
    bind = op.get_bind()
    project_columns = _columns(bind, "projects")
    with op.batch_alter_table("projects") as batch:
        if "template_code" not in project_columns:
            batch.add_column(sa.Column("template_code", sa.String(60), nullable=False, server_default=""))
        if "template_version" not in project_columns:
            batch.add_column(sa.Column("template_version", sa.Integer(), nullable=True))

    task_columns = _columns(bind, "tasks")
    with op.batch_alter_table("tasks") as batch:
        if "task_type" not in task_columns:
            batch.add_column(sa.Column("task_type", sa.String(40), nullable=False, server_default="Task"))
        if "watcher_ids" not in task_columns:
            batch.add_column(sa.Column("watcher_ids", sa.JSON(), nullable=False, server_default="[]"))
        if "custom_fields" not in task_columns:
            batch.add_column(sa.Column("custom_fields", sa.JSON(), nullable=False, server_default="{}"))
        if "actual_start_date" not in task_columns:
            batch.add_column(sa.Column("actual_start_date", sa.Date(), nullable=True))
        if "actual_finish_date" not in task_columns:
            batch.add_column(sa.Column("actual_finish_date", sa.Date(), nullable=True))

    attachment_columns = _columns(bind, "task_attachments")
    logical_file_added = "logical_file_id" not in attachment_columns
    with op.batch_alter_table("task_attachments") as batch:
        if "category" not in attachment_columns:
            batch.add_column(sa.Column("category", sa.String(60), nullable=False, server_default="Supporting Document"))
        if "logical_file_id" not in attachment_columns:
            batch.add_column(sa.Column("logical_file_id", sa.String(36), nullable=True))
        if "version_number" not in attachment_columns:
            batch.add_column(sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
        if "is_current" not in attachment_columns:
            batch.add_column(sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))
        if "download_count" not in attachment_columns:
            batch.add_column(sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"))
        if "deleted_at" not in attachment_columns:
            batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        if "deleted_by_id" not in attachment_columns:
            batch.add_column(sa.Column("deleted_by_id", sa.String(36), sa.ForeignKey("users.id", name="fk_task_attachments_deleted_by_id_users"), nullable=True))

    # Backfill a stable logical file id for every pre-v0.4 attachment.
    if inspect(bind).has_table("task_attachments"):
        rows = bind.execute(sa.text("SELECT id FROM task_attachments WHERE logical_file_id IS NULL OR logical_file_id = ''")).fetchall()
        for row in rows:
            bind.execute(sa.text("UPDATE task_attachments SET logical_file_id=:logical WHERE id=:id"), {"logical": str(uuid.uuid4()), "id": row[0]})
        # Fresh installations import the current model in migration 0001, so the
        # column/index may already be present. Only tighten nullability when this
        # migration added the column and create the index when it is absent.
        if logical_file_added:
            with op.batch_alter_table("task_attachments") as batch:
                batch.alter_column("logical_file_id", existing_type=sa.String(36), nullable=False)
        attachment_indexes = {item["name"] for item in inspect(bind).get_indexes("task_attachments")}
        if "ix_task_attachments_logical_file_id" not in attachment_indexes:
            op.create_index("ix_task_attachments_logical_file_id", "task_attachments", ["logical_file_id"], unique=False)

    inspector = inspect(bind)
    if not inspector.has_table("board_columns"):
        op.create_table(
            "board_columns",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("wip_limit", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("entry_criteria", sa.Text(), nullable=False, server_default=""),
            sa.Column("exit_criteria", sa.Text(), nullable=False, server_default=""),
            sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("project_id", "name", name="uq_board_column_project_name"),
        )
        op.create_index("ix_board_columns_project_id", "board_columns", ["project_id"])

    inspector = inspect(bind)
    if not inspector.has_table("task_note_revisions"):
        op.create_table(
            "task_note_revisions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id"), nullable=False),
            sa.Column("author_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("change_summary", sa.String(300), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_task_note_revisions_task_id", "task_note_revisions", ["task_id"])
        op.create_index("ix_task_note_revisions_author_id", "task_note_revisions", ["author_id"])

    inspector = inspect(bind)
    if not inspector.has_table("project_templates"):
        op.create_table(
            "project_templates",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("code", sa.String(60), nullable=False),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("category", sa.String(80), nullable=False, server_default="General"),
            sa.Column("blueprint", sa.JSON(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("code", "version", name="uq_project_template_code_version"),
        )
        op.create_index("ix_project_templates_code", "project_templates", ["code"])

    inspector = inspect(bind)
    if not inspector.has_table("status_reports"):
        op.create_table(
            "status_reports",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("human_id", sa.String(40), nullable=False, unique=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("status", sa.String(30), nullable=False, server_default="Draft"),
            sa.Column("health", sa.String(30), nullable=False, server_default="On Track"),
            sa.Column("percent_complete", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("accomplishments", sa.Text(), nullable=False, server_default=""),
            sa.Column("planned_work", sa.Text(), nullable=False, server_default=""),
            sa.Column("decisions_required", sa.Text(), nullable=False, server_default=""),
            sa.Column("risks_and_dependencies", sa.Text(), nullable=False, server_default=""),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("submitted_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("project_id", "period_end", "version", name="uq_status_report_period_version"),
        )
        op.create_index("ix_status_reports_human_id", "status_reports", ["human_id"])
        op.create_index("ix_status_reports_project_id", "status_reports", ["project_id"])

    # Create default board columns for existing projects.
    if inspect(bind).has_table("board_columns"):
        project_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM projects")).fetchall()]
        defaults = [("Backlog", 0, 0), ("Ready", 1, 8), ("In Progress", 2, 6), ("Review", 3, 4), ("Done", 4, 0)]
        for project_id in project_ids:
            count = bind.execute(sa.text("SELECT COUNT(*) FROM board_columns WHERE project_id=:pid"), {"pid": project_id}).scalar_one()
            if count:
                continue
            for name, position, wip_limit in defaults:
                bind.execute(sa.text(
                    "INSERT INTO board_columns (id, project_id, name, position, wip_limit, entry_criteria, exit_criteria, archived, created_at, updated_at) "
                    "VALUES (:id,:pid,:name,:position,:limit,'','',:archived,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
                ), {"id": str(uuid.uuid4()), "pid": project_id, "name": name, "position": position, "limit": wip_limit, "archived": False})

    # Upgrade RTM evidence without overstating advanced capabilities.
    if inspect(bind).has_table("requirement_trace"):
        updates = [
            ("PRJ-003", "Partially implemented", "0.4.0", "WBS numbering, hierarchy, schedule validation, baseline variance, Gantt, and basic critical path are operational; advanced resource leveling remains planned."),
            ("PRJ-004", "Partially implemented", "0.4.0", "Project boards support configurable columns, WIP limits, criteria, persistent movement, and audit; advanced swimlanes and portfolio boards remain planned."),
            ("PRJ-008", "Partially implemented", "0.4.0", "Task dependency creation rejects circular chains and supports basic schedule impact and critical-path analysis."),
            ("PRJ-012", "Partially implemented", "0.4.0", "Task files support versioning, soft deletion/restoration, integrity hashes, download audit, and safe preview for PDF/images/text/Markdown."),
            ("PRJ-014", "Partially implemented", "0.4.0", "Recurring status reports support draft, submit, approve, reporting periods, source-grounded narratives, and executive roll-up."),
        ]
        statement = sa.text("""
            UPDATE requirement_trace
               SET implementation_status=:status,
                   release=:release,
                   design_reference='docs/USER_GUIDE.md#v040-execution-management',
                   module_reference='app/main.py; app/models.py; app/services/schedule.py; app/templates/project_detail.html',
                   test_case='tests/test_v040.py',
                   uat_result='Automated test passed',
                   acceptance_notes=:notes
             WHERE requirement_id=:requirement_id
        """)
        for requirement_id, status, release, notes in updates:
            bind.execute(statement, {"requirement_id": requirement_id, "status": status, "release": release, "notes": notes})


def downgrade():
    # Data-bearing v0.4 tables are deliberately retained by downgrade guidance.
    # Operators should restore the pre-upgrade backup rather than silently lose
    # status reports, board configuration, note revisions, or file history.
    pass
