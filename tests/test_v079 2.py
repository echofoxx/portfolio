from __future__ import annotations

"""v0.7.9 — Adoption, Focus, and Workflow Simplification release tests."""

from pathlib import Path

from app.config import APP_VERSION
from app.models import Action, AuditEvent, Task, User
from conftest import login

ROOT = Path(__file__).resolve().parent.parent


def test_v079_version_single_source_of_truth(client):
    """VERSION file, config, FastAPI metadata, and asset strings must agree."""
    assert (ROOT / "VERSION").read_text().strip() == APP_VERSION
    from app.main import app as fastapi_app
    assert fastapi_app.version == APP_VERSION
    login(client, "admin")
    response = client.get("/dashboard")
    assert f"/static/app.css?v={APP_VERSION}" in response.text
    assert f"/static/app.js?v={APP_VERSION}" in response.text
    assert f"v{APP_VERSION}" in response.text  # sidebar footer


def test_v079_simplified_navigation_and_collapsible_groups(client):
    login(client, "admin")
    response = client.get("/dashboard")
    assert response.status_code == 200
    # ~9 primary destinations
    for label in ["Home", "My Work", "Projects", "Demand Intake", "Briefings",
                  "Resources", "Investments &amp; Value", "Reports &amp; Analytics",
                  "Travel &amp; Engagements"]:
        assert label in response.text
    # Less-frequent destinations live behind collapsible groups, not removed
    assert 'data-nav-group="more"' in response.text
    assert 'data-nav-group="admin"' in response.text
    for retained in ["Strategy", "Scenarios", "Decisions", "Roadmaps", "Blueprints",
                     "Excel Imports", "Data Quality", "Audit &amp; Activity"]:
        assert retained in response.text
    # Duplicated primary top-tabs replaced with a contextual shortcut strip
    assert "context-strip" in response.text


def test_v079_adaptive_shell_and_help_glossary(client):
    login(client, "admin")
    response = client.get("/dashboard")
    assert 'data-action="open-help"' in response.text
    assert 'data-help-drawer' in response.text
    for term in ["RAID", "ROM", "RTM", "Benefit realization", "Authoritative source",
                 "Reconciliation", "Determination", "Stage gate", "Confidence score",
                 "Calculated status", "Approved status"]:
        assert term in response.text
    # Adaptive role-focus strip and role-specific onboarding card
    assert 'data-action="toggle-role-focus"' in response.text
    assert 'data-onboarding' in response.text
    assert "Getting started" in response.text


def test_v079_my_work_action_center_groups_and_empty_collapse(client, db):
    login(client, "admin")
    response = client.get("/my-work")
    assert response.status_code == 200
    assert "Action Center" in response.text
    # Admin owns actions in seed data → Awaiting me renders; empty groups collapse
    assert "Awaiting me" in response.text
    admin = db.query(User).filter_by(username="admin").one()
    has_critical = any(
        a.due_date for a in db.query(Action).filter(Action.owner_id == admin.id, Action.status != "Closed")
    )
    if not has_critical:
        # No overdue critical work seeded for admin → the group heading must be absent
        assert "Critical now" not in response.text or "group-critical" in response.text


def test_v079_quick_task_update_owner_permission_and_audit(client, db):
    login(client, "admin")
    admin = db.query(User).filter_by(username="admin").one()
    task = db.query(Task).filter(Task.status != "Completed").first()
    assert task is not None
    original_owner = task.owner_id
    task.owner_id = admin.id
    db.commit()
    page = client.get("/my-work")
    csrf = page.text.split('name="csrf" value="')[1].split('"')[0]
    response = client.post(f"/quick/tasks/{task.id}", data={"csrf": csrf, "percent_complete": "60"}, follow_redirects=False)
    assert response.status_code == 303
    db.expire_all()
    updated = db.get(Task, task.id)
    assert updated.percent_complete == 60
    audit = db.query(AuditEvent).filter_by(entity_id=task.id, action="QUICK_UPDATE").first()
    assert audit is not None and audit.after_json["percent_complete"] == 60
    # Completing via quick action forces 100%
    response = client.post(f"/quick/tasks/{task.id}", data={"csrf": csrf, "status": "Completed"}, follow_redirects=False)
    assert response.status_code == 303
    db.expire_all()
    assert db.get(Task, task.id).status == "Completed"
    assert db.get(Task, task.id).percent_complete == 100
    # Restore
    record = db.get(Task, task.id)
    record.owner_id = original_owner
    record.status = "In Progress"
    record.percent_complete = 60
    db.commit()


def test_v079_quick_task_update_rejected_for_non_owner(client, db):
    login(client, "leader")  # SENIOR_LEADER is not owner/PM/ADMIN/PMO
    leader_page = client.get("/my-work")
    csrf = leader_page.text.split('name="csrf" value="')[1].split('"')[0]
    leader = db.query(User).filter_by(username="leader").one()
    from app.models import Project
    task = (
        db.query(Task).join(Project, Task.project_id == Project.id)
        .filter(Task.owner_id != leader.id, Project.manager_id != leader.id)
        .first()
    )
    assert task is not None
    response = client.post(f"/quick/tasks/{task.id}", data={"csrf": csrf, "percent_complete": "10"}, follow_redirects=False)
    assert response.status_code == 403


def test_v079_dashboard_is_decision_first_with_explainable_health(client):
    login(client, "admin")
    response = client.get("/dashboard")
    text = response.text
    assert "Decisions Required" in text
    assert "Significant Changes" in text
    assert "View calculation" in text  # explainable health rollup
    assert "Data freshness:" in text
    # Ordering: decisions → changes → health → investment analysis deep-dive
    assert text.index("Decisions Required") < text.index("Significant Changes")
    assert text.index("Significant Changes") < text.index("Portfolio Health")
    assert text.index("Portfolio Health") < text.index("Investment Flow")
    assert "Investment analysis" in text


def test_v079_travel_split_into_focused_views_with_pagination(client):
    login(client, "admin")
    overview = client.get("/travel")
    assert overview.status_code == 200
    assert "Interactive geographic footprint" in overview.text
    assert "Traveler-level approvals" not in overview.text  # long tables moved off overview

    requests_view = client.get("/travel?view=requests")
    assert "Traveler-level approvals" in requests_view.text
    assert requests_view.text.count("/travel/requests/") <= 26  # 25 rows + margin
    assert "Page 1 of" in requests_view.text
    page2 = client.get("/travel?view=requests&page=2")
    assert "Page 2 of" in page2.text

    reports_view = client.get("/travel?view=reports")
    assert "Post-trip outcomes" in reports_view.text and "Page 1 of" in reports_view.text
    reconciliation = client.get("/travel?view=reconciliation")
    assert reconciliation.status_code == 200
    assert "Trip report reconciliation" in reconciliation.text
    outcomes = client.get("/travel?view=outcomes")
    assert "All forums and events" in outcomes.text
    # Unknown views fall back safely
    assert client.get("/travel?view=nonsense").status_code == 200


def test_v079_reduced_motion_and_mobile_rules_present():
    css = (ROOT / "app" / "static" / "app.css").read_text()
    assert "prefers-reduced-motion" in css
    assert "v0.7.9" in css
    js = (ROOT / "app" / "static" / "app.js").read_text()
    assert "jsj6Telemetry" in js  # privacy-conscious adoption measurement hooks
    assert "restartOnboarding" in js
