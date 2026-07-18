from conftest import login


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
        "Benefits Realized",
        "Portfolio Health",
        "Investment by Category",
        "Recent Decisions",
        "My Tasks",
        "Portfolio at a Glance",
    ]:
        assert marker in response.text
    assert 'data-theme="dark"' in response.text
    assert '/static/app.css?v=0.6.0' in response.text
    assert "/war-room" not in response.text


def test_v060_navigation_uses_requested_enterprise_sections(client):
    login(client, "admin")
    response = client.get("/dashboard")
    assert response.status_code == 200
    for label in [
        "Overview", "Strategy", "Demand Intake", "Portfolio", "Projects",
        "Resources", "Investments", "Reports &amp; Analytics", "Scenarios",
        "Quick Access", "Administration",
    ]:
        assert label in response.text


def test_v060_legacy_war_route_is_not_registered(client):
    login(client, "admin")
    assert client.get("/war-room").status_code == 404
