from app.models import Task, RequirementTrace
from conftest import login


def test_legacy_war_room_is_removed_and_dashboard_is_available(client):
    login(client, "leader")
    response = client.get("/war-room")
    assert response.status_code == 404
    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "Portfolio Overview" in dashboard.text
    assert "War Room" not in dashboard.text


def test_record_drilldown_and_reverse_traceability(client, db):
    login(client, "admin")
    task = db.query(Task).first()
    response = client.get(f"/records/task/{task.id}")
    assert response.status_code == 200
    assert task.human_id in response.text
    assert "Bidirectional Traceability" in response.text


def test_requirement_has_evidence_detail(client, db):
    login(client, "admin")
    requirement = db.query(RequirementTrace).first()
    response = client.get(f"/requirements/{requirement.requirement_id}")
    assert response.status_code == 200
    assert requirement.requirement_id in response.text
    assert "Reverse Traceability" in response.text
