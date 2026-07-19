from __future__ import annotations

from bs4 import BeautifulSoup

from app.config import APP_VERSION
from app.models import Organization, PortfolioReview, Project, User
from app.services.security import csrf_token
from conftest import login


def test_v081_release_identity_and_project_overview_layout(client, db):
    login(client, "admin")
    assert APP_VERSION.startswith("0.8.")
    project = db.query(Project).first()
    page = client.get(f"/projects/{project.id}?tab=overview")
    assert page.status_code == 200
    assert "project-overview-grid" in page.text
    assert "project-accountability-list" in page.text
    assert "schedule-date-grid" in page.text
    assert page.text.count("project-signal-card") == 3
    assert 'class="card action-card"' not in page.text


def test_v081_gantt_labels_separate_wbs_title_and_dates(client, db):
    login(client, "admin")
    project = db.query(Project).first()
    page = client.get(f"/projects/{project.id}?tab=schedule")
    assert page.status_code == 200
    soup = BeautifulSoup(page.text, "html.parser")
    label = soup.select_one(".gantt-label")
    assert label is not None
    assert label.select_one(".gantt-wbs") is not None
    assert label.select_one(".gantt-label-copy strong") is not None
    assert "–" in label.select_one(".gantt-label-copy small").get_text()


def test_v081_raid_tables_use_responsive_metadata_layout(client, db):
    login(client, "admin")
    project = db.query(Project).first()
    page = client.get(f"/projects/{project.id}?tab=raid")
    assert page.status_code == 200
    assert "raid-layout" in page.text
    assert "responsive-record-table" in page.text
    assert 'class="meta-cell" data-label="ID"' in page.text
    assert 'class="narrative-cell" data-label="Record"' in page.text
    css = client.get("/static/app.css")
    assert ".raid-panel .meta-cell{white-space:nowrap" in css.text
    assert ".raid-layout{display:grid" in css.text


def test_v081_governance_cycle_uses_dedicated_create_and_cancel_page(client, db):
    login(client, "admin")
    listing = client.get("/portfolio-reviews")
    assert listing.status_code == 200
    assert 'href="/portfolio-reviews/new"' in listing.text
    assert 'action="/portfolio-reviews"' not in listing.text

    form = client.get("/portfolio-reviews/new")
    assert form.status_code == 200
    assert "Create a Briefing or Portfolio Review" in form.text
    assert form.text.count('href="/portfolio-reviews"') >= 2
    assert 'action="/portfolio-reviews"' in form.text

    admin = db.query(User).filter_by(username="admin").one()
    org = db.query(Organization).filter_by(code="JAD").one()
    response = client.post("/portfolio-reviews", data={
        "csrf": csrf_token(admin.id), "title": "v0.8.1 responsive governance test",
        "review_type": "Division Briefing", "portfolio_id": "", "org_id": org.id,
        "period_start": "2026-07-01", "period_end": "2026-09-30", "chair_id": admin.id,
        "participant_ids": [admin.id], "summary": "Validate focused workflow", "decisions_required": "None",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert db.query(PortfolioReview).filter_by(title="v0.8.1 responsive governance test").one()


def test_v081_roadmap_filter_has_stable_action_group(client):
    login(client, "admin")
    page = client.get("/roadmaps")
    assert page.status_code == 200
    assert "roadmap-filter-bar" in page.text
    assert "roadmap-filter-actions" in page.text
    assert 'href="/roadmaps">Reset</a>' in page.text


def test_v081_investment_summary_links_to_dedicated_flow_page(client):
    login(client, "admin")
    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "investment-summary-panel" in dashboard.text
    assert 'href="/financials/flow"' in dashboard.text
    assert "investment-flow-svg" not in dashboard.text
    for label in ("Approved", "Actual to date", "Unspent approved"):
        assert label in dashboard.text

    flow = client.get("/financials/flow")
    assert flow.status_code == 200
    assert "Approved Investment Flow" in flow.text
    assert "investment-flow-page-shell" in flow.text
    assert 'id="investment-flow-data"' in flow.text
    assert "Contributing financial baselines" in flow.text


def test_v081_dashboard_size_tokens_stretch_uniformly(client):
    login(client, "admin")
    css = client.get("/static/app.css").text
    js = client.get("/static/app.js").text
    assert ".dashboard-layout-grid{align-items:stretch" in css
    assert ".dashboard-layout-grid>.panel-size-compact{grid-column:span 4!important" in css
    assert ".dashboard-layout-grid>.panel-size-standard{grid-column:span 6!important" in css
    assert ".dashboard-layout-grid>.panel-size-wide{grid-column:1/-1!important" in css
    assert "panel.dataset.defaultSize" in js
