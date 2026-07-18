"""Task workspace, comments, attachments, relationships, and search expansion.

Revision ID: 0002_task_workspace_v030
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_task_workspace_v030"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _columns(bind, table: str) -> set[str]:
    inspector = inspect(bind)
    if not inspector.has_table(table):
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    task_columns = _columns(bind, "tasks")
    with op.batch_alter_table("tasks") as batch:
        if "description" not in task_columns:
            batch.add_column(sa.Column("description", sa.Text(), nullable=False, server_default=""))
        if "priority" not in task_columns:
            batch.add_column(sa.Column("priority", sa.String(length=30), nullable=False, server_default="Medium"))
        if "tags" not in task_columns:
            batch.add_column(sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))

    inspector = inspect(bind)
    if not inspector.has_table("task_comments"):
        op.create_table(
            "task_comments",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id"), nullable=False),
            sa.Column("author_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("mentions", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"])
        op.create_index("ix_task_comments_author_id", "task_comments", ["author_id"])

    inspector = inspect(bind)
    if not inspector.has_table("task_attachments"):
        op.create_table(
            "task_attachments",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id"), nullable=False),
            sa.Column("uploaded_by_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("original_name", sa.String(length=300), nullable=False),
            sa.Column("storage_key", sa.String(length=500), nullable=False, unique=True),
            sa.Column("media_type", sa.String(length=160), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("sensitivity", sa.String(length=60), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_task_attachments_task_id", "task_attachments", ["task_id"])
        op.create_index("ix_task_attachments_uploaded_by_id", "task_attachments", ["uploaded_by_id"])
        op.create_index("ix_task_attachments_sha256", "task_attachments", ["sha256"])

    inspector = inspect(bind)
    if not inspector.has_table("task_relationships"):
        op.create_table(
            "task_relationships",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("source_task_id", sa.String(length=36), sa.ForeignKey("tasks.id"), nullable=False),
            sa.Column("target_task_id", sa.String(length=36), sa.ForeignKey("tasks.id"), nullable=False),
            sa.Column("relationship_type", sa.String(length=40), nullable=False),
            sa.Column("created_by_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("source_task_id", "target_task_id", "relationship_type", name="uq_task_relationship"),
        )
        op.create_index("ix_task_relationships_source_task_id", "task_relationships", ["source_task_id"])
        op.create_index("ix_task_relationships_target_task_id", "task_relationships", ["target_task_id"])

    # Existing v0.2.0 databases already contain the RTM and the seed process is
    # intentionally idempotent. Update the requirements affected by this
    # release in the migration so upgrade installs receive the same evidence
    # and status values as clean v0.3.0 installs.
    inspector = inspect(bind)
    if inspector.has_table("requirement_trace"):
        requirement_updates = [
            {
                "requirement_id": "PRJ-001",
                "implementation_status": "Partially implemented",
                "release": "0.3.0",
                "design_reference": "docs/USER_GUIDE.md#task-workspace",
                "module_reference": "app/main.py; app/models.py; app/templates/project_detail.html; app/templates/_task_drawer.html",
                "test_case": "tests/test_v030.py",
                "uat_result": "Automated test passed",
                "acceptance_notes": "Project workspace now includes an operational task drawer, notes, evidence, files, comments, checklist, task relationships, WBS actions, and audit. Advanced schedule/document lifecycle remains roadmap.",
            },
            {
                "requirement_id": "PRJ-003",
                "implementation_status": "Partially implemented",
                "release": "0.3.0",
                "design_reference": "docs/USER_GUIDE.md#task-workspace",
                "module_reference": "app/main.py; app/templates/project_detail.html",
                "test_case": "tests/test_v030.py::test_task_relationship_and_wbs_actions_are_persistent",
                "uat_result": "Automated test passed",
                "acceptance_notes": "WBS items can be sequenced, moved, indented/outdented, baselined, and opened in place. Import, aggregate roll-up, and full baseline/version management remain planned.",
            },
            {
                "requirement_id": "PRJ-004",
                "implementation_status": "Partially implemented",
                "release": "0.3.0",
                "design_reference": "docs/USER_GUIDE.md#task-workspace",
                "module_reference": "app/main.py; app/static/app.js; app/templates/project_detail.html",
                "test_case": "tests/test_app.py; tests/test_v030.py",
                "uat_result": "Automated test passed",
                "acceptance_notes": "Kanban drag-and-drop persists authorized board-column changes and task cards open the detailed task workspace. WIP limits, configurable board administration, and keyboard reordering remain planned.",
            },
            {
                "requirement_id": "PRJ-007",
                "implementation_status": "Implemented",
                "release": "0.3.0",
                "design_reference": "docs/USER_GUIDE.md#task-workspace",
                "module_reference": "app/main.py; app/models.py; app/templates/_task_drawer.html; app/services/storage.py",
                "test_case": "tests/test_v030.py",
                "uat_result": "Automated test passed",
                "acceptance_notes": "Task detail supports owner, contributors, status, priority, dates, effort, percent complete, relationships, checklist, persistent notes, secure attachments, comments/mentions, tags, and acceptance evidence with audit.",
            },
            {
                "requirement_id": "PRJ-008",
                "implementation_status": "Partially implemented",
                "release": "0.3.0",
                "design_reference": "docs/USER_GUIDE.md#task-workspace",
                "module_reference": "app/main.py; app/models.py; app/templates/_task_drawer.html",
                "test_case": "tests/test_v030.py::test_task_relationship_and_wbs_actions_are_persistent",
                "uat_result": "Automated test passed",
                "acceptance_notes": "Task relationships support finish-to-start, start-to-start, finish-to-finish, and related links. Schedule-logic validation and broken-relationship warnings remain planned.",
            },
            {
                "requirement_id": "PRJ-012",
                "implementation_status": "Partially implemented",
                "release": "0.3.0",
                "design_reference": "docs/USER_GUIDE.md#task-files-and-evidence",
                "module_reference": "app/main.py; app/models.py; app/services/storage.py; app/templates/_task_drawer.html",
                "test_case": "tests/test_v030.py::test_task_attachment_upload_download_and_delete; tests/test_v030.py::test_invalid_binary_signature_is_rejected",
                "uat_result": "Automated test passed",
                "acceptance_notes": "Authorized users can upload, describe, download, hash, and delete task files with extension, size, filename, and signature validation. Versioning, preview, full-text search, malware scanning, records metadata, and project-wide repository lifecycle remain planned.",
            },
            {
                "requirement_id": "PRJ-014",
                "implementation_status": "Partially implemented",
                "release": "0.3.0",
                "design_reference": "docs/USER_GUIDE.md#project-manager",
                "module_reference": "app/main.py; app/models.py",
                "test_case": "e2e/test_status_rollup.py; tests/test_app.py",
                "uat_result": "Automated test passed",
                "acceptance_notes": "Project status, health, milestones, RAID, dependencies, financials, and benefits roll into division and executive views from canonical records. Full task/resource/financial actual aggregation requires expansion.",
            },
        ]
        update_statement = sa.text(
            """
            UPDATE requirement_trace
               SET implementation_status = :implementation_status,
                   release = :release,
                   design_reference = :design_reference,
                   module_reference = :module_reference,
                   test_case = :test_case,
                   uat_result = :uat_result,
                   acceptance_notes = :acceptance_notes
             WHERE requirement_id = :requirement_id
            """
        )
        for values in requirement_updates:
            bind.execute(update_statement, values)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    for table in ["task_relationships", "task_attachments", "task_comments"]:
        if inspector.has_table(table):
            op.drop_table(table)
    task_columns = _columns(bind, "tasks")
    with op.batch_alter_table("tasks") as batch:
        for column in ["tags", "priority", "description"]:
            if column in task_columns:
                batch.drop_column(column)
