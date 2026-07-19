from __future__ import annotations

from bs4 import BeautifulSoup

from app.config import APP_VERSION
from app.models import Project, RaidItem
from conftest import login


def test_v082_release_identity(client):
    assert APP_VERSION == "0.8.3.1"
    login(client, "admin")
    assert "v0.8.3.1" in client.get("/dashboard").text


def test_v082_raid_identifiers_are_full_and_non_wrapping(client, db):
    login(client, "admin")
    project = db.query(Project).first()
    raid = db.query(RaidItem).filter_by(project_id=project.id).first()
    page = client.get(f"/projects/{project.id}?tab=raid")
    assert page.status_code == 200
    if raid:
        assert raid.human_id in page.text
    css = client.get("/static/app.css").text
    assert ".project-raid-table th:nth-child(1){width:104px}" in css
    assert ".project-raid-table td:nth-child(1){white-space:nowrap!important" in css


def test_v082_board_governance_remains_structured_without_injected_guidance(client, db):
    login(client, "admin")
    project = db.query(Project).first()
    page = client.get(f"/projects/{project.id}?tab=board-settings")
    assert page.status_code == 200
    soup = BeautifulSoup(page.text, "html.parser")
    panel = soup.select_one(".board-governance-panel[data-input-zone-group]")
    assert panel is not None
    assert len(panel.select("form.board-config-update")) >= 2
    js = client.get("/static/app.js").text
    css = client.get("/static/app.css").text
    assert "Input area" not in js
    assert ".input-zone-banner" not in css


def test_v082_dashboard_kpis_and_divisions_use_uniform_compact_grids(client):
    login(client, "admin")
    page = client.get("/dashboard")
    soup = BeautifulSoup(page.text, "html.parser")
    assert len(soup.select(".kpi-grid-6 > .card")) == 6
    assert len(soup.select(".division-dashboard-grid > a")) == 8
    css = client.get("/static/app.css").text
    assert "grid-template-columns:repeat(6,minmax(0,1fr))" in css
    assert ".dashboard-layout-grid>.division-dashboard-panel .division-dashboard-grid{grid-template-columns:repeat(4,minmax(0,1fr))" in css


def test_v082_task_breadcrumbs_are_semantic_and_every_link_is_navigable(client, db):
    login(client, "admin")
    project = db.query(Project).first()
    page = client.get(f"/projects/{project.id}/tasks/new")
    assert page.status_code == 200
    soup = BeautifulSoup(page.text, "html.parser")
    breadcrumb = soup.select_one(".global-breadcrumbs")
    assert breadcrumb is not None
    assert [item.get_text(strip=True) for item in breadcrumb.select("a, span[aria-current=page]")] == [
        "Home", "Projects", project.human_id, "Board", "New Task"
    ]
    for link in breadcrumb.select("a[href]"):
        response = client.get(link["href"], follow_redirects=True)
        assert response.status_code == 200
        assert "Method Not Allowed" not in response.text
    collection = client.get(f"/projects/{project.id}/tasks", follow_redirects=False)
    assert collection.status_code == 303
    assert collection.headers["location"].endswith(f"/projects/{project.id}?tab=board")


def test_v082_icon_role_focus_and_sidebar_signout_are_always_available(client):
    login(client, "admin")
    page = client.get("/dashboard")
    soup = BeautifulSoup(page.text, "html.parser")
    toggle = soup.select_one('[data-action="toggle-role-focus"]')
    assert toggle is not None and toggle.get_text(strip=True) == "⌃"
    assert toggle.get("aria-label") == "Compact role focus"
    signout = soup.select_one(".sidebar-signout-form[action='/logout']")
    assert signout is not None and signout.select_one("input[name=csrf]") is not None
    css = client.get("/static/app.css").text
    assert ".app.collapsed .sidebar-signout-form{display:block}" in css


def test_v082_travel_has_full_width_guidance_and_executive_map_lenses(client):
    login(client, "admin")
    page = client.get("/travel")
    assert page.status_code == 200
    soup = BeautifulSoup(page.text, "html.parser")
    assert soup.select_one("form.travel-filter-bar") is not None
    assert soup.select_one("[data-map-region]") is not None
    assert soup.select_one("[data-map-measure]") is not None
    assert soup.select_one("[data-map-zoom-in]") is None
    assert soup.select_one("[data-map-zoom-out]") is None
    assert soup.select_one("[data-map-fit]") is None
    assert soup.select_one("[data-map-stage]") is not None
    assert soup.select_one("[data-map-detail][hidden]") is not None
    assert "City-level planning view" in page.text
    js = client.get("/static/app.js").text
    for capability in ("displayRegion", "measureLabels", "map-cluster", "map_region", "map_measure"):
        assert capability in js
