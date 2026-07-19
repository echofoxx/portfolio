from __future__ import annotations

from bs4 import BeautifulSoup

from app.models import AuditEvent, Demand, DemandRevision, Mission, Organization, Project, Task, User
from app.services.security import csrf_token
from conftest import login
from app.config import APP_VERSION


def _task_and_project(db):
    task = db.query(Task).order_by(Task.human_id).first()
    return task, db.get(Project, task.project_id)


def test_task_controls_have_drawer_and_reliable_full_page_fallback(client, db):
    task, project = _task_and_project(db)
    login(client, "admin")

    project_page = client.get(f"/projects/{project.id}?tab=board")
    assert project_page.status_code == 200
    soup = BeautifulSoup(project_page.text, "html.parser")
    task_link = soup.find(attrs={"data-task-open": task.id})
    assert task_link is not None
    assert task_link.name == "a"
    assert task_link["href"] == f"/projects/{project.id}/tasks/{task.id}"
    assert task_link["data-task-panel-url"] == f"/projects/{project.id}/tasks/{task.id}/panel"

    full_page = client.get(task_link["href"])
    assert full_page.status_code == 200
    for expected in [task.human_id, "Authoritative Task Workspace", "Working notes", "Attachments", "Notes and comments"]:
        assert expected in full_page.text


def test_static_assets_are_versioned_to_prevent_stale_task_javascript(client):
    login(client, "admin")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert f'/static/app.js?v={APP_VERSION}' in response.text
    assert f'/static/app.css?v={APP_VERSION}' in response.text


def test_requester_can_edit_a_submitted_demand_with_revision_and_audit(client, db):
    requester = db.query(User).filter_by(username="avery.jad").one()
    org = db.get(Organization, requester.division_id)
    mission = db.query(Mission).filter_by(owner_org_id=org.id).first() or db.query(Mission).first()
    login(client, requester.username)
    token = csrf_token(requester.id)

    created = client.post(
        "/demands/new",
        data={
            "csrf": token,
            "title": "Submitted Demand Edit Hotfix Test",
            "category": "Capability Gap",
            "lead_org_id": org.id,
            "mission_id": mission.id,
            "sponsor_id": requester.id,
            "purpose": "Demonstrate governed editing after submission.",
            "problem": "Submitted demand details require correction before triage.",
            "desired_end_state": "Requester updates the authoritative demand without losing history.",
            "beneficiaries": "JAD portfolio staff",
            "urgency": "High",
            "rom_cost": "125000",
            "expected_benefits": "Improved intake quality",
            "confidence": "Medium",
            "sensitivity": "Controlled Unclassified",
            "action": "submit",
        },
        follow_redirects=False,
    )
    assert created.status_code == 303
    demand_id = created.headers["location"].split("?", 1)[0].rsplit("/", 1)[-1]

    edit_page = client.get(f"/demands/{demand_id}/edit")
    assert edit_page.status_code == 200
    assert "Governed post-submission editing" in edit_page.text
    assert "Submitted Demand Edit Hotfix Test" in edit_page.text

    demand = db.get(Demand, demand_id)
    updated = client.post(
        f"/demands/{demand_id}/edit",
        data={
            "csrf": token,
            "expected_version": str(demand.version),
            "title": "Submitted Demand Edit Hotfix Test — Updated",
            "category": demand.category,
            "lead_org_id": demand.lead_org_id,
            "mission_id": demand.mission_id,
            "sponsor_id": demand.sponsor_id,
            "purpose": "Demonstrate governed editing after submission with revision history.",
            "problem": demand.problem,
            "desired_end_state": demand.desired_end_state,
            "beneficiaries": demand.beneficiaries,
            "required_date": demand.required_date.isoformat() if demand.required_date else "",
            "urgency": demand.urgency,
            "consequence_of_inaction": demand.consequence_of_inaction,
            "preliminary_scope": demand.preliminary_scope,
            "deliverables": demand.deliverables,
            "assumptions": demand.assumptions,
            "dependencies_text": demand.dependencies_text,
            "required_skills": demand.required_skills,
            "rom_cost": str(demand.rom_cost),
            "expected_benefits": demand.expected_benefits,
            "confidence": demand.confidence,
            "sensitivity": demand.sensitivity,
            "change_summary": "Corrected the title and clarified the purpose before triage.",
            "action": "save",
        },
        follow_redirects=False,
    )
    assert updated.status_code == 303
    db.expire_all()
    saved = db.get(Demand, demand_id)
    assert saved.status == "Submitted"
    assert saved.title.endswith("Updated")
    assert saved.version == 2
    assert db.query(DemandRevision).filter_by(demand_id=demand_id, revision=2).count() == 1
    assert db.query(AuditEvent).filter_by(entity_id=demand_id, action="UPDATE_AFTER_SUBMISSION").count() == 1

    detail = client.get(f"/demands/{demand_id}")
    assert detail.status_code == 200
    assert f'/demands/{demand_id}/edit' in detail.text
    assert "Version-controlled editing available" in detail.text


def test_assessment_stage_demand_is_locked_for_direct_requester_edit(client, db):
    requester = db.query(User).filter_by(username="avery.jad").one()
    demand = db.query(Demand).filter_by(requester_id=requester.id).first()
    original_status = demand.status
    demand.status = "Assessment"
    db.commit()
    try:
        login(client, requester.username)
        response = client.get(f"/demands/{demand.id}/edit")
        assert response.status_code == 403
    finally:
        demand.status = original_status
        db.commit()