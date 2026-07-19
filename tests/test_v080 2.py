from __future__ import annotations

import io

from app.config import APP_VERSION
from app.models import (
    DashboardPreference, DivisionProfile, Organization, Project, ProjectPromotionRequest,
    ProjectTemplate, ResourceCapacity, User,
)
from app.services.security import csrf_token
from conftest import login


def test_v080_divisions_are_direct_and_banner_complete(client, db):
    login(client, "admin")
    assert APP_VERSION == "0.8.0"
    page = client.get("/divisions")
    assert page.status_code == 200
    for code, asset in [("FO", "fo.webp"), ("CCD", "ccd.webp"), ("JFID", "jfid.webp")]:
        org = db.query(Organization).filter_by(code=code).one()
        profile = db.query(DivisionProfile).filter_by(org_id=org.id).one()
        assert profile.mission and profile.banner_asset.endswith(asset)
        assert f"/divisions/{code}" in page.text
    assert 'href="/divisions"' in page.text
    assert "division-switcher" in page.text


def test_v080_project_creation_uses_full_page_and_local_classification(client, db):
    login(client, "admin")
    admin = db.query(User).filter_by(username="admin").one()
    org = db.query(Organization).filter_by(code="DSD").one()
    mission = db.query(Project).first()
    template = db.query(ProjectTemplate).filter_by(code="LOCAL", version=1).one()
    source_project = db.query(Project).first()
    page = client.get(f"/projects/new?template={template.id}&division=DSD")
    assert page.status_code == 200
    assert "Create a New Project" in page.text
    response = client.post("/projects", data={
        "csrf": csrf_token(admin.id), "title": "Division local interoperability sprint", "description": "Local improvement",
        "governance_level": "Division Local", "lead_org_id": org.id, "mission_id": source_project.mission_id,
        "sponsor_id": admin.id, "manager_id": admin.id, "template_id": template.id,
        "scope": "Division-owned scope", "desired_end_state": "Accepted local result", "deliverables": "Evidence package",
        "funding_posture": "No Additional Funding", "resource_posture": "Existing Capacity",
        "sensitivity": "Controlled Unclassified",
    }, follow_redirects=False)
    assert response.status_code == 303
    project = db.query(Project).filter_by(title="Division local interoperability sprint").one()
    assert project.governance_level == "Division Local"
    assert project.portfolio_id is None
    assert project.template_code == "LOCAL"
    assert project.promotion_status == "Eligible"


def test_v080_local_project_can_be_promoted_without_duplication(client, db):
    login(client, "admin")
    admin = db.query(User).filter_by(username="admin").one()
    project = db.query(Project).first()
    project.governance_level = "Division Local"; project.portfolio_id = None; project.promotion_status = "Eligible"
    db.commit()
    original_id = project.id
    submitted = client.post(f"/projects/{project.id}/promotion", data={
        "csrf": csrf_token(admin.id), "reason": "Scope now crosses divisions", "scope_change": "Enterprise interface",
        "enterprise_impact": "Shared C2 outcome", "funding_requirement": "FY27 funding needed",
        "resource_requirement": "Two integration engineers", "schedule_risk": "Decision needed this quarter",
    }, follow_redirects=False)
    assert submitted.status_code == 303
    request = db.query(ProjectPromotionRequest).filter_by(project_id=project.id).one()
    decided = client.post(f"/projects/{project.id}/promotion/{request.id}/decision", data={
        "csrf": csrf_token(admin.id), "decision": "Approved", "decision_rationale": "Enterprise value validated", "conditions": "Monthly status",
    }, follow_redirects=False)
    assert decided.status_code == 303
    db.refresh(project)
    assert project.id == original_id
    assert project.governance_level == "Portfolio Managed"
    assert project.promotion_status == "Approved"
    assert db.query(Project).filter_by(id=original_id).count() == 1


def test_v080_resource_admin_preview_commit_and_exports(client, db):
    login(client, "admin")
    admin = db.query(User).filter_by(username="admin").one()
    form = client.get("/resources/requests/new")
    assert form.status_code == 200 and "Submit Resource Request" in form.text
    export = client.get("/exports/resources.csv")
    assert export.status_code == 200 and "division_code" in export.text
    csv_payload = (
        "record_id,division_code,role_name,skill,period,capacity_hours,allocated_hours,actual_hours,minimum_core_coverage\n"
        ",CCD,Capability Analyst,C2 requirements,FY27-Q1,480,240,0,80\n"
    )
    preview = client.post("/resources/import/preview", data={"csrf": csrf_token(admin.id)},
                          files={"file": ("resources.csv", io.BytesIO(csv_payload.encode()), "text/csv")})
    assert preview.status_code == 200 and "Review Resource Import" in preview.text
    batch_id = preview.text.split('/resources/import/')[1].split('/commit')[0]
    commit = client.post(f"/resources/import/{batch_id}/commit", data={"csrf": csrf_token(admin.id)}, follow_redirects=False)
    assert commit.status_code == 303
    ccd = db.query(Organization).filter_by(code="CCD").one()
    assert db.query(ResourceCapacity).filter_by(org_id=ccd.id, role_name="Capability Analyst", period="FY27-Q1").one().capacity_hours == 480


def test_v080_role_dashboard_is_configurable_and_persisted(client, db):
    login(client, "admin")
    admin = db.query(User).filter_by(username="admin").one()
    page = client.get("/dashboard")
    assert "Your role-focused Portfolio Overview" in page.text
    assert 'data-dashboard-layout' in page.text and 'data-dashboard-panel="divisions"' in page.text
    response = client.post("/dashboard/preferences", data={
        "csrf": csrf_token(admin.id), "panel_order": "divisions,changes,kpis", "hidden_panels": "investment",
        "panel_sizes": '{"divisions":"wide","changes":"compact"}',
    }, follow_redirects=False)
    assert response.status_code == 303
    preference = db.query(DashboardPreference).filter_by(user_id=admin.id).one()
    assert preference.panel_order[:2] == ["divisions", "changes"]
    assert preference.hidden_panels == ["investment"]


def test_v080_blueprint_catalog_is_comprehensive(client, db):
    login(client, "admin")
    assert db.query(ProjectTemplate).filter(ProjectTemplate.active.is_(True)).count() >= 14
    page = client.get("/templates")
    for name in ["AI/ML Capability Delivery", "C2 Requirements &amp; Capability Development", "Joint Fires / CJADC2 Integration", "Division Local / Quick Project"]:
        assert name in page.text
    assert "Use this blueprint" in page.text
    assert "template-launch" not in page.text


def test_v080_project_entry_forms_use_focused_pages(client, db):
    login(client, "admin")
    project = db.query(Project).first()
    expectations = {
        "tasks/new": "Create work item",
        "milestones/new": "Create milestone",
        "raid/new": "Create RAID record",
        "status-reports/new": "Prepare status report",
    }
    for path, heading in expectations.items():
        response = client.get(f"/projects/{project.id}/{path}")
        assert response.status_code == 200
        assert heading in response.text
        assert 'class="card form-page-card"' in response.text

    board = client.get(f"/projects/{project.id}?tab=board")
    assert f'/projects/{project.id}/tasks/new' in board.text
    assert "Create Work Item" in board.text
