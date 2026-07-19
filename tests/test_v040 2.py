from __future__ import annotations

import io
from dataclasses import replace
from datetime import date, timedelta

from starlette.requests import Request

from app import main as main_module
from app.models import (
    AuditEvent,
    BoardColumn,
    Milestone,
    Mission,
    Organization,
    Project,
    ProjectTemplate,
    StatusReport,
    Task,
    TaskAttachment,
    TaskRelationship,
    User,
)
from app.services.schedule import critical_path, gantt_layout, wbs_numbers, would_create_cycle
from app.services.security import csrf_token
from app.services.storage import LocalVolumeStorage
from conftest import login
from app.config import APP_VERSION


def _admin(db) -> User:
    return db.query(User).filter_by(username="admin").one()


def _project(db) -> Project:
    return db.query(Project).filter(Project.status == "Active").order_by(Project.human_id).first()


def _request_with_ip(direct: str, forwarded: str = "") -> Request:
    headers = []
    if forwarded:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers, "client": (direct, 1234), "scheme": "http", "server": ("test", 80), "query_string": b""})


def test_exact_proxy_hops_resolve_client_without_unrestricted_trust(monkeypatch):
    original = main_module.settings
    try:
        monkeypatch.setattr(main_module, "settings", replace(original, trust_proxy_hops=0))
        assert main_module.resolved_client_ip(_request_with_ip("172.18.0.4", "198.51.100.7")) == "172.18.0.4"
        monkeypatch.setattr(main_module, "settings", replace(original, trust_proxy_hops=1))
        assert main_module.resolved_client_ip(_request_with_ip("172.18.0.4", "198.51.100.7")) == "198.51.100.7"
        monkeypatch.setattr(main_module, "settings", replace(original, trust_proxy_hops=2))
        assert main_module.resolved_client_ip(_request_with_ip("172.18.0.4", "198.51.100.7, 10.0.0.8")) == "198.51.100.7"
    finally:
        monkeypatch.setattr(main_module, "settings", original)


def test_runtime_headers_and_v040_navigation_are_present(client):
    login(client, "admin")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.headers["x-ratelimit-limit"]
    assert response.headers["x-resolved-client-ip-source"] == "direct"
    assert '/roadmaps' in response.text
    assert '/templates' in response.text
    assert f'/static/app.js?v={APP_VERSION}' in response.text


def test_blueprint_instantiates_governed_project(client, db):
    admin = _admin(db)
    template = db.query(ProjectTemplate).filter(ProjectTemplate.active.is_(True)).first()
    org = db.query(Organization).filter_by(org_type="Division").first()
    mission = db.query(Mission).first()
    assert template and org and mission
    login(client, "admin")
    title = "v0.4 Template Acceptance Project"
    response = client.post(
        f"/templates/{template.id}/instantiate",
        data={
            "csrf": csrf_token(admin.id),
            "title": title,
            "lead_org_id": org.id,
            "mission_id": mission.id,
            "sponsor_id": admin.id,
            "manager_id": admin.id,
            "start_date": "2027-01-04",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    project = db.query(Project).filter_by(title=title).one()
    assert db.query(BoardColumn).filter_by(project_id=project.id, archived=False).count() >= 3
    assert db.query(Task).filter_by(project_id=project.id).count() == len(template.blueprint.get("tasks", []))
    assert db.query(Milestone).filter_by(project_id=project.id).count() == len(template.blueprint.get("milestones", []))
    assert project.template_code == template.code
    assert project.template_version == template.version
    assert db.query(AuditEvent).filter_by(entity_id=project.id, action="CREATE_FROM_TEMPLATE").count() == 1


def test_configurable_board_enforces_wip_limit(client, db):
    admin = _admin(db)
    project = _project(db)
    login(client, "admin")
    name = "Acceptance WIP"
    column = db.query(BoardColumn).filter_by(project_id=project.id, name=name).first()
    if not column:
        column = BoardColumn(project_id=project.id, name=name, position=99, wip_limit=1)
        db.add(column)
        db.commit()
    first = db.query(Task).filter_by(project_id=project.id, board_column=name).first()
    if not first:
        first = Task(human_id="TSK-WIP-040", project_id=project.id, title="Existing WIP task", board_column=name, status="In Progress", owner_id=admin.id, sequence=999)
        db.add(first)
        db.commit()
    before = db.query(Task).filter_by(project_id=project.id).count()
    response = client.post(
        f"/projects/{project.id}/tasks",
        data={
            "csrf": csrf_token(admin.id),
            "title": "Task that exceeds WIP",
            "task_type": "Task",
            "priority": "Medium",
            "owner_id": admin.id,
            "board_column": name,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "WIP" in response.headers["location"] or "capacity" in response.headers["location"].lower()
    db.expire_all()
    assert db.query(Task).filter_by(project_id=project.id).count() == before


def test_schedule_service_numbers_wbs_rejects_cycle_and_marks_critical_path(db):
    project = _project(db)
    tasks = db.query(Task).filter_by(project_id=project.id).order_by(Task.sequence).limit(4).all()
    assert len(tasks) >= 3
    numbers = wbs_numbers(tasks)
    assert all(task.id in numbers for task in tasks)
    relationships = [
        TaskRelationship(source_task_id=tasks[1].id, target_task_id=tasks[0].id, relationship_type="Finish-to-start", created_by_id=_admin(db).id),
        TaskRelationship(source_task_id=tasks[2].id, target_task_id=tasks[1].id, relationship_type="Finish-to-start", created_by_id=_admin(db).id),
    ]
    assert would_create_cycle(tasks, relationships, tasks[0].id, tasks[2].id) is True
    path = critical_path(tasks, relationships)
    assert tasks[0].id in path["task_ids"] and tasks[2].id in path["task_ids"]
    gantt = gantt_layout(tasks, project.start_date or date.today(), project.current_end_date or date.today() + timedelta(days=90))
    assert len(gantt["rows"]) == len(tasks)
    assert all("left" in row and "width" in row for row in gantt["rows"])


def test_status_report_submit_approve_and_reporting_baseline(client, db):
    admin = _admin(db)
    project = _project(db)
    login(client, "admin")
    period_end = date(2027, 2, 28)
    existing = db.query(StatusReport).filter_by(project_id=project.id, period_end=period_end).count()
    response = client.post(
        f"/projects/{project.id}/status-reports",
        data={
            "csrf": csrf_token(admin.id),
            "period_start": "2027-02-15",
            "period_end": period_end.isoformat(),
            "health": "At Risk",
            "percent_complete": "47",
            "accomplishments": "Completed interface discovery and evidence review.",
            "planned_work": "Resolve the external dependency and complete validation.",
            "decisions_required": "Approve two-week schedule recovery action.",
            "risks_and_dependencies": "External validation environment is constrained.",
            "summary": "Delivery remains at risk pending leadership action.",
            "action": "submit",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    report = db.query(StatusReport).filter_by(project_id=project.id, period_end=period_end).order_by(StatusReport.version.desc()).first()
    assert report and report.status == "Submitted" and report.version == existing + 1
    approval = client.post(f"/projects/{project.id}/status-reports/{report.id}/approve", data={"csrf": csrf_token(admin.id)}, follow_redirects=False)
    assert approval.status_code == 303
    db.expire_all()
    report = db.get(StatusReport, report.id)
    assert report.status == "Approved"
    detail = client.get(f"/status-reports/{report.id}")
    assert detail.status_code == 200 and report.human_id in detail.text
    legacy = client.get("/war-room")
    assert legacy.status_code == 404



def test_draft_status_report_can_be_updated_and_submitted(client, db):
    admin = _admin(db)
    project = _project(db)
    login(client, "admin")
    response = client.post(
        f"/projects/{project.id}/status-reports",
        data={
            "csrf": csrf_token(admin.id),
            "period_start": "2027-03-01",
            "period_end": "2027-03-14",
            "health": "On Track",
            "percent_complete": "50",
            "accomplishments": "Initial draft.",
            "planned_work": "Initial plan.",
            "action": "draft",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    report = db.query(StatusReport).filter_by(project_id=project.id, period_end=date(2027, 3, 14)).order_by(StatusReport.version.desc()).first()
    assert report and report.status == "Draft"
    detail = client.get(f"/status-reports/{report.id}")
    assert detail.status_code == 200 and "Editable Reporting Draft" in detail.text
    updated = client.post(
        f"/projects/{project.id}/status-reports/{report.id}/update",
        data={
            "csrf": csrf_token(admin.id),
            "health": "At Risk",
            "percent_complete": "55",
            "accomplishments": "Updated evidence complete.",
            "planned_work": "Recover schedule.",
            "decisions_required": "Approve recovery plan.",
            "risks_and_dependencies": "External dependency.",
            "summary": "Updated and ready for review.",
            "action": "submit",
        },
        follow_redirects=False,
    )
    assert updated.status_code == 303
    db.expire_all()
    saved = db.get(StatusReport, report.id)
    assert saved.status == "Submitted" and saved.health == "At Risk" and saved.percent_complete == 55
    assert db.query(AuditEvent).filter_by(entity_id=report.id, action="RESUBMITTED").count() == 1

def test_attachment_version_preview_soft_delete_and_restore(client, db, tmp_path, monkeypatch):
    admin = _admin(db)
    task = db.query(Task).order_by(Task.human_id).first()
    project = db.get(Project, task.project_id)
    login(client, "admin")
    monkeypatch.setattr(main_module, "LocalVolumeStorage", lambda: LocalVolumeStorage(root=tmp_path, max_mb=2))
    first = client.post(
        f"/projects/{project.id}/tasks/{task.id}/attachments",
        data={"csrf": csrf_token(admin.id), "description": "v1", "category": "Acceptance Evidence", "sensitivity": "Controlled Unclassified"},
        files={"attachment": ("v040-evidence.md", io.BytesIO(b"# Version 1\n"), "text/markdown")},
        follow_redirects=False,
    )
    assert first.status_code == 303
    db.expire_all()
    v1 = db.query(TaskAttachment).filter_by(task_id=task.id, original_name="v040-evidence.md").order_by(TaskAttachment.version_number).first()
    second = client.post(
        f"/projects/{project.id}/tasks/{task.id}/attachments",
        data={"csrf": csrf_token(admin.id), "description": "v2", "category": "Acceptance Evidence", "sensitivity": "Controlled Unclassified", "replace_attachment_id": v1.id},
        files={"attachment": ("v040-evidence.md", io.BytesIO(b"# Version 2\n"), "text/markdown")},
        follow_redirects=False,
    )
    assert second.status_code == 303
    db.expire_all()
    versions = db.query(TaskAttachment).filter_by(logical_file_id=v1.logical_file_id).order_by(TaskAttachment.version_number).all()
    assert [item.version_number for item in versions] == [1, 2]
    assert versions[0].is_current is False and versions[1].is_current is True
    preview = client.get(f"/projects/{project.id}/tasks/{task.id}/attachments/{versions[1].id}/preview")
    assert preview.status_code == 200 and b"Version 2" in preview.content
    removed = client.post(f"/projects/{project.id}/tasks/{task.id}/attachments/{versions[1].id}/delete", data={"csrf": csrf_token(admin.id)}, follow_redirects=False)
    assert removed.status_code == 303
    restored = client.post(f"/projects/{project.id}/tasks/{task.id}/attachments/{versions[1].id}/restore", data={"csrf": csrf_token(admin.id)}, follow_redirects=False)
    assert restored.status_code == 303
    db.expire_all()
    assert db.get(TaskAttachment, versions[1].id).deleted_at is None
    assert db.get(TaskAttachment, versions[1].id).is_current is True


def test_roadmap_templates_admin_and_schedule_pages_render(client, db):
    project = _project(db)
    login(client, "admin")
    checks = {
        "/roadmaps": "Enterprise Roadmap",
        "/templates": "Project Blueprint Catalog",
        "/administration": "Deployment and runtime controls",
        f"/projects/{project.id}?tab=schedule": "Critical Path",
        f"/projects/{project.id}?tab=board-settings": "Board Configuration",
        f"/projects/{project.id}?tab=status": "Status Reporting",
    }
    for url, text in checks.items():
        response = client.get(url)
        assert response.status_code == 200, url
        assert text in response.text, url