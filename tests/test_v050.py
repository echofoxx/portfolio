from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.models import (
    DataQualityIssue,
    Delegation,
    FinancialRecord,
    FinancialTransaction,
    IntegrationConnection,
    JobRun,
    PortfolioReview,
    PortfolioReviewItem,
    Project,
    ReportPack,
    ResourceRequest,
    Scenario,
    ScenarioChange,
    ScenarioResult,
    SyncRun,
    User,
)
from app.services.security import csrf_token
from conftest import login


def admin(db):
    return db.query(User).filter_by(username="admin").one()


def test_v050_navigation_and_governance_pages_render(client):
    login(client, "admin")
    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert '/static/app.js?v=0.6.0' in dashboard.text
    for path, marker in [
        ("/portfolio-reviews", "Portfolio Reviews"),
        ("/scenarios", "Portfolio Scenarios"),
        ("/integrations", "Synchronization & Field Authority"),
        ("/data-quality", "Data Quality & Reconciliation"),
        ("/operations", "Jobs, Report Packs"),
        ("/administration", "Administration, Access"),
    ]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert marker in response.text


def test_admin_creates_user_and_auditable_delegation(client, db):
    owner = admin(db)
    login(client, "admin")
    username = "v050.user"
    response = client.post(
        "/administration/users",
        data={
            "csrf": csrf_token(owner.id),
            "username": username,
            "full_name": "V050 Test User",
            "email": "v050.user@demo.ddc5i.local",
            "password": "LongDemoPass!2026",
            "roles": ["TEAM_MEMBER", "REQUESTER"],
            "division_id": "",
            "sensitive_access": "1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    created = db.query(User).filter_by(username=username).one()
    assert set(created.roles) == {"TEAM_MEMBER", "REQUESTER"}
    delegate = db.query(User).filter(User.id != created.id).first()
    response = client.post(
        "/administration/delegations",
        data={
            "csrf": csrf_token(owner.id),
            "delegator_id": delegate.id,
            "delegate_id": created.id,
            "roles": ["PROJECT_MANAGER"],
            "org_scope_id": "",
            "starts_at": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "expires_at": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M"),
            "reason": "Acceptance-test acting role",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    delegation = db.query(Delegation).filter_by(delegate_id=created.id).one()
    assert delegation.active and delegation.roles == ["PROJECT_MANAGER"]


def test_projectos_dry_run_retains_payload_and_no_remote_write(client, db):
    owner = admin(db)
    connection = db.query(IntegrationConnection).filter_by(code="PROJECTOS-MOCK").one()
    project = db.query(Project).filter(Project.status == "Active").first()
    login(client, "admin")
    response = client.post(
        f"/integrations/{connection.id}/sync",
        data={"csrf": csrf_token(owner.id), "project_id": project.id, "direction": "Outbound", "dry_run": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    run = db.query(SyncRun).filter_by(connection_id=connection.id, canonical_id=project.id).order_by(SyncRun.started_at.desc()).first()
    assert run.status == "Succeeded" and run.dry_run is True
    assert run.payload["canonical_id"] == project.id
    assert run.result["records"]["projects"] == 1


def test_portfolio_review_decision_creates_decision_and_action(client, db):
    owner = admin(db)
    review = db.query(PortfolioReview).first()
    project = db.query(Project).filter(Project.status == "Active").first()
    login(client, "admin")
    response = client.post(
        f"/portfolio-reviews/{review.id}/items",
        data={
            "csrf": csrf_token(owner.id), "item_type": "Decision", "entity_type": "Project", "entity_id": project.id,
            "title": "v0.5 review acceptance decision", "recommendation": "Continue", "rationale": "Validate governed decision capture.", "owner_id": project.manager_id,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    item = db.query(PortfolioReviewItem).filter_by(title="v0.5 review acceptance decision").one()
    response = client.post(
        f"/portfolio-reviews/{review.id}/items/{item.id}/decide",
        data={
            "csrf": csrf_token(owner.id), "decision": "Continue", "rationale": "Approved with evidence.",
            "conditions": "Refresh status in 14 days.", "action_title": "Refresh source evidence", "action_due_date": (date.today()+timedelta(days=14)).isoformat(), "action_owner_id": project.manager_id,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    item = db.get(PortfolioReviewItem, item.id)
    assert item.status == "Decided" and item.decision_id and item.action_id


def test_scenario_compare_is_non_destructive_until_apply(client, db):
    owner = admin(db)
    project = db.query(Project).filter(Project.status == "Active").first()
    baseline = float(project.budget)
    scenario = Scenario(human_id="SCN-TEST-050", name="Acceptance Scenario", scenario_type="Budget Change", baseline_date=date.today(), assumptions="Test non-destructive behavior", created_by_id=owner.id)
    db.add(scenario); db.commit()
    login(client, "admin")
    proposed = baseline + 1000
    response = client.post(
        f"/scenarios/{scenario.id}/changes",
        data={"csrf": csrf_token(owner.id), "entity_type": "Project", "entity_id": project.id, "field_name": "budget", "proposed_value": str(proposed), "rationale": "Acceptance change"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    response = client.post(f"/scenarios/{scenario.id}/calculate", data={"csrf": csrf_token(owner.id)}, follow_redirects=False)
    assert response.status_code == 303
    db.expire_all()
    assert float(db.get(Project, project.id).budget) == baseline
    assert db.query(ScenarioResult).filter_by(scenario_id=scenario.id, metric_key="portfolio_budget").one().delta == 1000
    response = client.post(f"/scenarios/{scenario.id}/approve", data={"csrf": csrf_token(owner.id)}, follow_redirects=False)
    assert response.status_code == 303
    response = client.post(f"/scenarios/{scenario.id}/apply", data={"csrf": csrf_token(owner.id)}, follow_redirects=False)
    assert response.status_code == 303
    db.expire_all()
    assert float(db.get(Project, project.id).budget) == proposed


def test_resource_and_financial_governance_workflows(client, db):
    owner = admin(db)
    project = db.query(Project).filter(Project.status == "Active").first()
    login(client, "admin")
    response = client.post(
        "/resources/requests",
        data={
            "csrf": csrf_token(owner.id), "org_id": project.lead_org_id, "project_id": project.id, "role_name": "Integration Engineer",
            "skill": "ProjectOS synchronization", "requested_hours": "160", "period_start": date.today().isoformat(),
            "period_end": (date.today()+timedelta(days=60)).isoformat(), "priority": "High", "rationale": "Acceptance workflow",
        }, follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    request = db.query(ResourceRequest).filter_by(role_name="Integration Engineer", skill="ProjectOS synchronization").one()
    response = client.post(f"/resources/requests/{request.id}/decision", data={"csrf": csrf_token(owner.id), "decision": "Approved", "resolution": "Approved from available role capacity."}, follow_redirects=False)
    assert response.status_code == 303
    financial = db.query(FinancialRecord).filter_by(project_id=project.id).first()
    response = client.post(
        "/financials/transactions",
        data={"csrf": csrf_token(owner.id), "financial_record_id": financial.id, "transaction_type": "Commitment", "amount": "1234.50", "transaction_date": date.today().isoformat(), "reference": "V050-TEST", "source_system": "DDC5I-PM", "notes": "Acceptance evidence"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    assert db.query(ResourceRequest).filter_by(id=request.id).one().status == "Approved"
    assert db.query(FinancialTransaction).filter_by(reference="V050-TEST").one().amount == 1234.50


def test_quality_scan_and_report_pack_operations(client, db):
    owner = admin(db)
    login(client, "admin")
    response = client.post("/data-quality/scan", data={"csrf": csrf_token(owner.id)}, follow_redirects=False)
    assert response.status_code == 303
    db.expire_all()
    assert db.query(JobRun).filter_by(job_type="Data Quality Scan", status="Succeeded").count() >= 1
    assert db.query(DataQualityIssue).count() >= 1
    response = client.post(
        "/operations/report-packs",
        data={"csrf": csrf_token(owner.id), "name": "v0.5 Acceptance Pack", "pack_type": "Executive Portfolio Summary", "org_id": "", "period_start": (date.today()-timedelta(days=30)).isoformat(), "period_end": date.today().isoformat()},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    pack = db.query(ReportPack).filter_by(name="v0.5 Acceptance Pack").one()
    assert pack.status == "Generated" and len(pack.sections) >= 4
    response = client.post(f"/operations/report-packs/{pack.id}/approve", data={"csrf": csrf_token(owner.id)}, follow_redirects=False)
    assert response.status_code == 303
    db.expire_all()
    assert db.get(ReportPack, pack.id).status == "Approved"
