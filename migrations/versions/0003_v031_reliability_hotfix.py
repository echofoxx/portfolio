"""Task-detail reliability and governed submitted-demand editing evidence.

Revision ID: 0003_v031_reliability_hotfix
Revises: 0002_task_workspace_v030
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0003_v031_reliability_hotfix"
down_revision = "0002_task_workspace_v030"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not inspect(bind).has_table("requirement_trace"):
        return
    updates = [
        {
            "requirement_id": "DMD-008",
            "release": "0.3.1",
            "design_reference": "docs/USER_GUIDE.md#editing-a-submitted-demand",
            "module_reference": "app/main.py; app/templates/demand_form.html; app/templates/demand_detail.html",
            "test_case": "tests/test_v031.py::test_requester_can_edit_a_submitted_demand_with_revision_and_audit",
            "uat_result": "Automated test passed",
            "acceptance_notes": "Requesters and authorized portfolio roles can edit Draft, Submitted, Clarification Required, and authorized Triage records before assessment. Saves use optimistic version checks, create revision and audit evidence, and notify accountable users; later assessment and decision baselines remain locked.",
        },
        {
            "requirement_id": "PRJ-007",
            "release": "0.3.1",
            "design_reference": "docs/USER_GUIDE.md#task-workspace",
            "module_reference": "app/main.py; app/static/app.js; app/templates/project_detail.html; app/templates/task_detail.html; app/templates/_task_drawer.html; app/services/storage.py",
            "test_case": "tests/test_v030.py; tests/test_v031.py::test_task_controls_have_drawer_and_reliable_full_page_fallback",
            "uat_result": "Automated test passed",
            "acceptance_notes": "Task detail supports the complete task workspace and now opens through a versioned JavaScript drawer with a shareable full-page fallback, preventing stale-bundle or JavaScript failures from leaving task controls nonfunctional.",
        },
    ]
    statement = sa.text(
        """
        UPDATE requirement_trace
           SET release = :release,
               design_reference = :design_reference,
               module_reference = :module_reference,
               test_case = :test_case,
               uat_result = :uat_result,
               acceptance_notes = :acceptance_notes
         WHERE requirement_id = :requirement_id
        """
    )
    for values in updates:
        bind.execute(statement, values)


def downgrade():
    # Evidence-only migration. Business data and schema are unchanged; retaining
    # the newer evidence is safer than fabricating a historical rollback state.
    pass
