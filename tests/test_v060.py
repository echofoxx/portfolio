from conftest import login
from app.config import APP_VERSION


def test_v060_jsj6_dashboard_structure_and_theme(client):
    login(client, "admin")
    response = client.get("/dashboard")
    assert response.status_code == 200
    for marker in [
        "JSJ6",
        "Enterprise Portfolio Management",
        "Portfolio Overview",
        "Active Projects",
        "Total Investment",
        "Health Score",
        "Decisions Pending",
        "Risks High",
        "Benefit Progress",
        "Portfolio Health",
        "Investment Flow",
        "Recent Decisions",
        "My Tasks",
        "Portfolio at a Glance",
    ]:
        assert marker in response.text
    assert 'data-theme="dark"' in response.text
    assert f'/static/app.css?v={APP_VERSION}' in response.text
    assert "/war-room" not in response.text


def test_v060_navigation_uses_requested_enterprise_sections(client):
    login(client, "admin")
    response = client.get("/dashboard")
    assert response.status_code == 200
    # v0.7.9: navigation simplified to ~9 primary destinations with collapsible
    # "More workspaces" and "Administration" groups (all capabilities retained).
    for label in [
        "Home", "My Work", "Strategy", "Demand Intake", "Projects",
        "Resources", "Investments", "Reports &amp; Analytics", "Scenarios",
        "More workspaces", "Administration",
    ]:
        assert label in response.text


def test_v060_legacy_war_route_is_not_registered(client):
    login(client, "admin")
    assert client.get("/war-room").status_code == 404


def test_v061_role_focus_process_guide_and_display_preferences(client):
    login(client, "admin")
    response = client.get("/dashboard")
    assert response.status_code == 200
    for marker in [
        "Your focus · Administrator",
        "Page guide",
        "Use the portfolio overview",
        "Display preferences",
        'data-font-size="standard"',
        'data-font-size-choice',
        "Extra large",
        "Input area",
    ]:
        # Input area is injected client-side, so its source marker lives in the JS asset.
        if marker == "Input area":
            asset = client.get("/static/app.js")
            assert marker in asset.text
        else:
            assert marker in response.text


def test_v061_role_focus_changes_with_user_role(client):
    login(client, "leader")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Your focus · Decision Authority" in response.text
    assert "Review decisions" in response.text
    assert "Open briefings" in response.text


def test_v061_contextual_guides_cover_demand_project_and_import_flows(client):
    login(client, "admin")
    demand = client.get("/demands")
    assert "Demand lifecycle" in demand.text
    assert "Draft" in demand.text and "Execute" in demand.text
    projects = client.get("/projects")
    assert "Project delivery cycle" in projects.text
    assert "Plan" in projects.text and "Report" in projects.text
    imports = client.get("/imports")
    assert "Controlled import flow" in imports.text
    assert "Preview is non-destructive" in imports.text