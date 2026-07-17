"""Server-rendered end-to-end acceptance test for project status roll-up."""
from app.models import Project, User
from app.services.security import csrf_token
from conftest import login


def test_project_status_update_rolls_to_dashboard(client, db):
    admin = db.query(User).filter_by(username="admin").one()
    project = db.query(Project).filter_by(status="Active").first()
    login(client, "admin")
    response = client.post(
        f"/projects/{project.id}/status",
        data={
            "csrf": csrf_token(admin.id),
            "health_owner": "Off Track",
            "percent_complete": "44",
            "status_narrative": "Critical external dependency requires leadership action.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert project.title in dashboard.text
    assert "Projects at risk" in dashboard.text
