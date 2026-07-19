from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlalchemy import func

from app.models import (
    PortfolioReview,
    TravelApprovalStep,
    TravelEngagement,
    TravelRequest,
    TripReport,
    TripReportItem,
    User,
)
from app.services.briefings import ensure_briefing_sections
from app.services.security import csrf_token
from app.services.travel import validate_travel_request_rows
from app.services.xlsx_reader import read_first_sheet_xlsx
from conftest import login


SOURCE_DIR = Path(__file__).resolve().parents[1] / "docs" / "source" / "travel"


def test_v076_seed_reconciles_supplied_approval_totals_and_reports(db):
    assert db.query(TravelRequest).count() == 385
    assert db.query(func.sum(TravelRequest.estimated_cost)).scalar() == Decimal("1082395.25")
    assert db.query(TripReport).count() == 9
    assert db.query(TravelEngagement).count() > 0
    assert db.query(TripReportItem).count() > 0

    example = db.query(TravelRequest).filter_by(external_id="426").one()
    assert example.estimated_cost == Decimal("11040.00")
    assert example.funding == "J6"
    assert "Direct enablement" in example.exemption_category
    assert db.query(TravelApprovalStep).filter_by(request_id=example.id).count() == 2


def test_v076_power_bi_export_reader_retains_all_source_rows_and_flags_date_anomaly(db):
    rows = read_first_sheet_xlsx((SOURCE_DIR / "Trip data.xlsx").read_bytes())
    results, summary = validate_travel_request_rows(db, rows, db.query(User).filter_by(username="admin").one())
    assert len(rows) == 388
    assert len(results) == 385
    assert summary == {"valid": 384, "errors": 0, "warnings": 1, "skipped": 2}
    anomaly = next(row for row in results if row["record_identifier"] == "303")
    assert anomaly["severity"] == "Warning"
    assert "Return Date precedes Departure Date" in anomaly["message"]


def test_v076_travel_dashboard_drilldown_exports_and_search_render(client, db):
    login(client, "admin")
    request_record = db.query(TravelRequest).filter_by(external_id="426").one()
    report = db.query(TripReport).order_by(TripReport.human_id).first()
    engagement = db.query(TravelEngagement).filter_by(id=request_record.engagement_id).one()

    for url, expected in [
        ("/travel", "Travel &amp; Engagements"),
        (f"/travel/requests/{request_record.id}", "Estimated cost"),
        (f"/travel/reports/{report.id}", "Post-trip report"),
        (f"/travel/engagements/{engagement.id}", "Engagement rollup"),
        ("/divisions/C3OD2", "Travel, forums, and trip reports"),
        ("/my-work", "Action Center"),  # v0.7.9: travel follow-ups moved into the unified queue
        ("/search?q=Bold+Quest", "Trip Report"),
    ]:
        response = client.get(url)
        assert response.status_code == 200
        assert expected in response.text

    travel_csv = client.get("/exports/travel-requests.csv")
    assert travel_csv.status_code == 200
    assert b"TRV-26-" in travel_csv.content
    report_csv = client.get("/exports/trip-reports.csv")
    assert report_csv.status_code == 200
    assert b"TRP-26-" in report_csv.content


def test_v076_trip_report_import_preview_and_traceability(client, db):
    admin = db.query(User).filter_by(username="admin").one()
    login(client, "admin")
    with (SOURCE_DIR / "Trip Report.xlsx").open("rb") as source:
        response = client.post(
            "/imports",
            data={"csrf": csrf_token(admin.id), "template_type": "Trip Reports"},
            files={"file": ("Trip Report.xlsx", source.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            follow_redirects=True,
        )
    assert response.status_code == 200
    assert "Trip Report.xlsx" in response.text
    assert "Ready to commit" in response.text or "Review source values" in response.text


def test_v076_division_briefing_payload_has_travel_section(db):
    review = db.query(PortfolioReview).filter(PortfolioReview.org_id.is_not(None)).first()
    assert review is not None
    sections, payload = ensure_briefing_sections(db, review)
    travel_section = next(section for section in sections if section.section_key == "travel-engagements")
    assert travel_section.title == "Travel, forums, and external engagement outcomes"
    assert "travel_requests" in payload["metrics"]
    assert "trip_reports" in payload
