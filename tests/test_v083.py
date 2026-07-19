from __future__ import annotations

from datetime import date, timedelta

from bs4 import BeautifulSoup

from app.config import APP_VERSION
from app.models import TravelEngagement, TravelRequest, TripReport
from app.services.travel import travel_dashboard_payload
from conftest import login


def test_v083_release_theme_catalog_and_clean_forms(client):
    assert APP_VERSION == "0.8.3.1"
    login(client, "admin")
    page = client.get("/dashboard")
    soup = BeautifulSoup(page.text, "html.parser")
    theme = soup.select_one("[data-theme-choice]")
    assert theme is not None
    assert {option.get("value") for option in theme.select("option")} == {
        "light", "dusk", "black", "forest", "navy", "teal", "plum", "steel", "stone"
    }
    js = client.get("/static/app.js").text
    css = client.get("/static/app.css").text
    assert "Input area" not in js
    assert "input-zone-banner" not in css
    assert "storedTheme === 'dark' ? 'dusk'" in js
    for token in ("[data-theme=black]", "[data-theme=forest]", "[data-theme=navy]", "[data-theme=teal]", "[data-theme=plum]", "[data-theme=steel]", "[data-theme=stone]"):
        assert token in css


def test_v083_blueprint_catalog_button_is_concise_and_aligned(client):
    login(client, "admin")
    page = client.get("/projects/new")
    soup = BeautifulSoup(page.text, "html.parser")
    link = soup.select_one("a.blueprint-catalog-link[href='/templates']")
    assert link is not None and link.get_text(strip=True) == "Blueprint Catalog"
    assert "Review full blueprint catalog" not in page.text


def test_v083_location_compliance_is_request_accurate(db):
    engagement = db.query(TravelEngagement).first()
    org_id = engagement.lead_org_id
    completed = TravelRequest(
        human_id="TRV-V083-001", external_id="V083-COMPLIANT", traveler_name="Map Test", org_id=org_id,
        location="Brussels, Belgium", departure_date=date.today() - timedelta(days=8),
        return_date=date.today() - timedelta(days=4), determination="Approved",
        report_required=True, estimated_cost=1000, engagement_id=engagement.id,
    )
    overdue = TravelRequest(
        human_id="TRV-V083-002", external_id="V083-OVERDUE", traveler_name="Map Test", org_id=org_id,
        location="Brussels, Belgium", departure_date=date.today() - timedelta(days=7),
        return_date=date.today() - timedelta(days=3), determination="Approved",
        report_required=True, estimated_cost=2000, engagement_id=engagement.id,
    )
    db.add_all([completed, overdue]); db.flush()
    db.add(TripReport(
        human_id="TR-V083", request_id=completed.id, org_id=org_id, title="Linked map test",
        traveler_name="Map Test", location="Brussels, Belgium",
        start_date=completed.departure_date, return_date=completed.return_date,
        match_status="Matched", match_confidence=1.0, review_status="Submitted",
    ))
    db.commit()
    payload = travel_dashboard_payload(
        db.query(TravelRequest).all(), db.query(TripReport).all(), db.query(TravelEngagement).all()
    )
    row = next(item for item in payload["location_rows"] if item["location"] == "Brussels, Belgium")
    assert row["report_required_completed"] >= 2
    assert row["linked_completed"] >= 1
    assert row["overdue_count"] >= 1
    assert row["compliance_pct"] is not None
    assert payload["unmapped_cost"] >= 0


def test_v083_travel_map_is_one_linked_direct_manipulation_system(client):
    login(client, "admin")
    page = client.get("/travel")
    soup = BeautifulSoup(page.text, "html.parser")
    system = soup.select_one(".travel-map-system[data-travel-map]")
    assert system is not None
    assert system.select_one(".travel-map-canvas[tabindex='0']") is not None
    assert system.select_one(".travel-location-card .top-location-list") is not None
    assert system.select_one("[data-map-detail][hidden]") is not None
    assert system.select_one("[data-map-chip-gap]") is not None
    assert system.select_one("[data-map-chip-unmapped]") is not None
    assert not system.select("[data-map-zoom-in], [data-map-zoom-out], [data-map-fit]")
    assert "Linked required report" in page.text and "Missing required report" in page.text
    js = client.get("/static/app.js").text
    for capability in ("zoomAt", "fitVisible", "pointerdown", "pointermove", "dblclick", "scrollIntoView", "report_required_completed"):
        assert capability in js
    css = client.get("/static/app.css").text
    assert "[hidden]{display:none!important}" in css
    assert "conic-gradient(#2e90fa" in css
