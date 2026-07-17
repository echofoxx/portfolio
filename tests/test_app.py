from bs4 import BeautifulSoup

from app.models import AuditEvent, Demand, Mission, Organization, Project, User
from app.services.security import csrf_token
from conftest import login


def test_health_and_primary_routes(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
    login(client, "leader")
    for path in [
        "/dashboard", "/divisions", "/strategy", "/demands", "/assessments",
        "/decisions", "/projects", "/risks", "/resources", "/financials",
        "/benefits", "/reports", "/notifications", "/requirements", "/api/docs",
    ]:
        response = client.get(path)
        assert response.status_code == 200, path


def test_critical_pages_have_accessible_landmarks(client):
    login(client, "leader")
    for path in ["/dashboard", "/demands", "/projects"]:
        soup = BeautifulSoup(client.get(path).text, "html.parser")
        assert soup.find("main") is not None
        assert soup.find("nav") is not None
        assert soup.find("h2") is not None
        assert soup.find("input", {"aria-label": "Global search"}) is not None


def test_division_scoped_user_cannot_read_other_division(client, db):
    user = db.query(User).filter(User.username.like("avery.%")).one()
    other = db.query(Demand).filter(Demand.lead_org_id != user.division_id).first()
    login(client, user.username)
    response = client.get(f"/demands/{other.id}")
    assert response.status_code == 404


def test_auditor_cannot_modify_business_data(client, db):
    auditor = db.query(User).filter_by(username="auditor").one()
    demand = db.query(Demand).filter_by(status="Submitted").first()
    login(client, "auditor")
    response = client.post(
        f"/demands/{demand.id}/transition",
        data={"csrf": csrf_token(auditor.id), "target_status": "Triage", "comment": "Attempt"},
    )
    assert response.status_code == 403


def test_end_to_end_demand_to_project_without_rekeying(client, db):
    admin = db.query(User).filter_by(username="admin").one()
    org = db.query(Organization).filter_by(code="DSD").one()
    mission = db.query(Mission).filter_by(code="M-DATA").one()
    manager = db.query(User).filter(User.roles.contains("PROJECT_MANAGER")).first()
    token = csrf_token(admin.id)
    login(client, "admin")

    created = client.post(
        "/demands/new",
        data={
            "csrf": token, "title": "Acceptance Workflow Demand", "category": "Modernization effort",
            "lead_org_id": org.id, "mission_id": mission.id, "sponsor_id": admin.id,
            "purpose": "Validate the end-to-end acceptance workflow.",
            "problem": "Approved work must move into execution without rekeying.",
            "desired_end_state": "A linked execution project retains approved demand data.",
            "beneficiaries": "DDC5I portfolio stakeholders", "urgency": "High",
            "rom_cost": "250000", "expected_benefits": "Faster governed initiation",
            "confidence": "High", "sensitivity": "Controlled Unclassified", "action": "submit",
        },
        follow_redirects=False,
    )
    assert created.status_code == 303
    demand_url = created.headers["location"].split("?", 1)[0]
    demand_id = demand_url.rsplit("/", 1)[-1]

    for target in ["Triage", "Assessment"]:
        response = client.post(
            f"/demands/{demand_id}/transition",
            data={"csrf": token, "target_status": target, "comment": f"Move to {target}"},
            follow_redirects=False,
        )
        assert response.status_code == 303

    score_data = {key: "4" for key in [
        "mission_criticality", "strategic_alignment", "operational_impact", "urgency",
        "risk_reduction", "readiness_interoperability", "feasibility", "expected_value",
    ]}
    score_data.update({"csrf": token, "rationale": "Evidence supports a high-priority pilot.", "confidence": "High"})
    assert client.post(f"/demands/{demand_id}/assess", data=score_data, follow_redirects=False).status_code == 303

    for target in ["Awaiting Portfolio Recommendation", "Awaiting Decision"]:
        assert client.post(
            f"/demands/{demand_id}/transition",
            data={"csrf": token, "target_status": target, "comment": f"Gate complete: {target}"},
            follow_redirects=False,
        ).status_code == 303

    assert client.post(
        f"/demands/{demand_id}/decision",
        data={"csrf": token, "decision": "Approve", "rationale": "Mission value supports approval.",
              "conditions": "Provide monthly status", "resource_implications": "Use planned DSD capacity",
              "financial_implications": "$250,000 ROM"},
        follow_redirects=False,
    ).status_code == 303

    converted = client.post(
        f"/demands/{demand_id}/convert",
        data={"csrf": token, "manager_id": manager.id},
        follow_redirects=False,
    )
    assert converted.status_code == 303
    with db.no_autoflush:
        db.expire_all()
        demand = db.get(Demand, demand_id)
        project = db.query(Project).filter_by(demand_id=demand_id).one()
        assert demand.status == "Converted to Execution"
        assert project.title == demand.title
        assert project.mission_id == demand.mission_id
        assert float(project.budget) == float(demand.rom_cost)
        assert db.query(AuditEvent).filter_by(entity_id=project.id, action="CREATE_FROM_DEMAND").count() == 1


def test_login_redirect_rejects_scheme_relative_url(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "Demo123!", "next": "//example.invalid"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


def test_csv_export_escapes_spreadsheet_formulas():
    from app.main import csv_safe
    assert csv_safe("=2+2") == "'=2+2"
    assert csv_safe("@SUM(A1:A2)") == "'@SUM(A1:A2)"
    assert csv_safe("Normal title") == "Normal title"
