from __future__ import annotations

from app.models import FinancialRecord, TravelEngagement, TravelRequest, TripReport, TripReportItem
from app.services.travel import resolve_location, travel_dashboard_payload
from conftest import login
from app.config import APP_VERSION


def test_v077_location_registry_normalizes_source_aliases_and_reports_coverage(db):
    assert resolve_location("Alplena, MI")["canonical"] == "Alpena, MI"
    assert resolve_location("Honoloulu, HI")["canonical"] == "Honolulu / Ford Island, HI"
    requests = db.query(TravelRequest).all()
    reports = db.query(TripReport).all()
    engagements = db.query(TravelEngagement).all()
    items = db.query(TripReportItem).all()
    payload = travel_dashboard_payload(requests, reports, engagements, items)
    alpena = next(row for row in payload["location_rows"] if row["location"] == "Alpena, MI")
    assert alpena["count"] >= 65
    assert payload["mapping_coverage"] >= 95
    assert payload["outcome_funnel"][0]["label"] == "Approved travel"
    assert "division_status" in payload


def test_v077_dashboard_investment_flow_and_briefings_label_render(client, db):
    login(client, "admin")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Investment Flow" in response.text
    assert 'id="investment-flow-data"' in response.text
    assert "Approved investment" in response.text
    assert "not an authoritative accounting statement" in response.text
    assert ">Briefings<" in response.text
    assert f'/static/app.js?v={APP_VERSION}' in response.text
    assert db.query(FinancialRecord).count() > 0


def test_v077_interactive_travel_map_and_fancy_analytics_render(client):
    login(client, "admin")
    response = client.get("/travel")
    assert response.status_code == 200
    for marker in [
        "Interactive geographic footprint",
        'id="travel-map-data"',
        "Places traveled",
        "Monthly travel trend",
        "Determination by division",
        "Outcome pipeline",
        "Report compliance",
        "Top forums and events",
        "world-map-svg",
    ]:
        assert marker in response.text
    filtered = client.get("/travel?location=Alpena%2C+MI")
    assert filtered.status_code == 200
    assert "Geographic footprint:" in filtered.text
    assert "Alpena, MI" in filtered.text
    assert "65 records" in filtered.text or "64 records" in filtered.text


def test_v077_sankey_drillthrough_financial_filters_render(client):
    login(client, "admin")
    response = client.get("/financials?category=Program&view=actual")
    assert response.status_code == 200
    assert "Apply flow filter" in response.text
    assert 'value="Program"' in response.text
    assert 'value="actual" selected' in response.text