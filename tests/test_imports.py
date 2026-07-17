from app.models import Mission, Organization, User
from app.services.imports import DEMAND_COLUMNS, validate_demand_rows


def test_excel_import_returns_success_warning_duplicate_and_error(db):
    admin = db.query(User).filter_by(username="admin").one()
    org = db.query(Organization).filter_by(code="DSD").one()
    mission = db.query(Mission).filter_by(code="M-DATA").one()
    rows = [DEMAND_COLUMNS]
    rows += [
        ["DMD-NEW-001", "Valid imported demand", "Idea", "Draft", org.code, mission.code, "Purpose", "Problem", "End state", "Normal", "125000", "Benefit", "Controlled Unclassified"],
        ["", "Joint Assessment Evidence Repository", "Idea", "Draft", org.code, mission.code, "Purpose", "Problem", "End state", "Normal", "1000", "Benefit", "Controlled Unclassified"],
        ["DMD-NEW-001", "Duplicate upload id", "Idea", "Draft", org.code, mission.code, "Purpose", "Problem", "End state", "Normal", "1000", "Benefit", "Controlled Unclassified"],
        ["DMD-BAD-001", "Invalid imported demand", "Idea", "Draft", "BAD", "BAD", "Purpose", "Problem", "End state", "Normal", "not-a-number", "Benefit", "Controlled Unclassified"],
    ]
    results, summary = validate_demand_rows(db, rows, admin)
    assert len(results) == 4
    assert summary["new"] >= 1
    assert summary["duplicates"] >= 1
    assert summary["warnings"] >= 1
    assert summary["errors"] >= 2
    assert any(row["severity"] == "Success" for row in results)
    assert any(row["severity"] == "Warning" for row in results)
    assert any(row["severity"] == "Error" for row in results)


def test_artifact_tool_workbook_can_be_read():
    from pathlib import Path
    from app.services.xlsx_reader import read_first_sheet_xlsx
    path = Path(__file__).resolve().parents[1] / "sample-imports" / "DDC5I_Demand_Import_Demo_v1.0.xlsx"
    rows = read_first_sheet_xlsx(path.read_bytes())
    assert rows[0][0] == "Human ID"
    assert rows[1][1] == "Validated Data Standards Intake"
