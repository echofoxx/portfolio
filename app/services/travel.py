from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models import (
    Organization,
    TravelEngagement,
    TravelRequest,
    TripReport,
    TripReportItem,
    User,
)

TRAVEL_REQUEST_HEADERS = [
    "ID",
    "Traveler Full Name",
    "Division",
    "Location",
    "Travel Event or Forum Name",
    "DDS Determination",
    "Departure Date",
    "Return Date",
    "Cost Estimate",
]
TRIP_REPORT_HEADERS = [
    "Event Name/Title",
    "Traveler Name",
    "Division",
    "Start Date",
    "Return Date",
    "Location (City, State or Country)",
    "Purpose/Objectives",
    "Discussion",
    "Key Findings",
    "Recommendations",
    "Action Items (Specific to J6 DDC5I)",
]

DIVISION_ALIASES = {
    "front": "FO",
    "front office": "FO",
    "ddc5i front office": "FO",
    "ddc5i ccd": "CCD",
}


LOCATION_GEO_REGISTRY = [
    {"canonical": "Alpena, MI", "lat": 45.0617, "lon": -83.4328, "country": "USA", "region": "North America", "aliases": ["alpena", "alplena"]},
    {"canonical": "Arlington / Pentagon, VA", "lat": 38.8719, "lon": -77.0563, "country": "USA", "region": "North America", "aliases": ["arlington", "arlingtron", "pentagon", "pnt", "crystal city", "rosslyn", "washington arlington"]},
    {"canonical": "Washington, DC", "lat": 38.9072, "lon": -77.0369, "country": "USA", "region": "North America", "aliases": ["washington dc", "washington d c", "washington, dc"]},
    {"canonical": "Columbia, MD", "lat": 39.2037, "lon": -76.8610, "country": "USA", "region": "North America", "aliases": ["columbia md"]},
    {"canonical": "Honolulu / Ford Island, HI", "lat": 21.3099, "lon": -157.8581, "country": "USA", "region": "North America", "aliases": ["honolulu", "honlulu", "honoloulu", "ford island", "pearl harbor", "kaneohe bay"]},
    {"canonical": "Brussels, Belgium", "lat": 50.8503, "lon": 4.3517, "country": "BEL", "region": "Europe", "aliases": ["brussels", "belgium"]},
    {"canonical": "Linthicum Heights, MD", "lat": 39.2051, "lon": -76.6527, "country": "USA", "region": "North America", "aliases": ["linthicum heights", "lithicum"]},
    {"canonical": "Suffolk, VA", "lat": 36.7282, "lon": -76.5836, "country": "USA", "region": "North America", "aliases": ["suffolk"]},
    {"canonical": "Miami / Doral, FL", "lat": 25.7617, "lon": -80.1918, "country": "USA", "region": "North America", "aliases": ["miami", "doral"]},
    {"canonical": "Annapolis Junction, MD", "lat": 39.1204, "lon": -76.7766, "country": "USA", "region": "North America", "aliases": ["annapolis junction"]},
    {"canonical": "San Diego, CA", "lat": 32.7157, "lon": -117.1611, "country": "USA", "region": "North America", "aliases": ["san diego", "oceanside"]},
    {"canonical": "Huntsville, AL", "lat": 34.7304, "lon": -86.5861, "country": "USA", "region": "North America", "aliases": ["huntsville"]},
    {"canonical": "Sagami Depot / Yokota, Japan", "lat": 35.5715, "lon": 139.3730, "country": "JPN", "region": "Asia-Pacific", "aliases": ["sagami depot", "yokota"]},
    {"canonical": "Fort Meade, MD", "lat": 39.1082, "lon": -76.7432, "country": "USA", "region": "North America", "aliases": ["fort meade", "ft meade"]},
    {"canonical": "Fort Walton Beach / Hurlburt, FL", "lat": 30.4201, "lon": -86.6170, "country": "USA", "region": "North America", "aliases": ["fort walton beach", "hurlburt"]},
    {"canonical": "Quantico, VA", "lat": 38.5229, "lon": -77.2901, "country": "USA", "region": "North America", "aliases": ["quantico"]},
    {"canonical": "McLean / Tysons, VA", "lat": 38.9339, "lon": -77.1773, "country": "USA", "region": "North America", "aliases": ["mclean", "tysons corner"]},
    {"canonical": "Alexandria, VA", "lat": 38.8048, "lon": -77.0469, "country": "USA", "region": "North America", "aliases": ["alexandria"]},
    {"canonical": "Orlando, FL", "lat": 28.5383, "lon": -81.3792, "country": "USA", "region": "North America", "aliases": ["orlando"]},
    {"canonical": "Colorado Springs, CO", "lat": 38.8339, "lon": -104.8214, "country": "USA", "region": "North America", "aliases": ["colorado springs", "colorado spring"]},
    {"canonical": "The Hague, Netherlands", "lat": 52.0705, "lon": 4.3007, "country": "NLD", "region": "Europe", "aliases": ["the hague"]},
    {"canonical": "Luxembourg City, Luxembourg", "lat": 49.6116, "lon": 6.1319, "country": "LUX", "region": "Europe", "aliases": ["luxembourg city"]},
    {"canonical": "Maastricht, Netherlands", "lat": 50.8514, "lon": 5.6910, "country": "NLD", "region": "Europe", "aliases": ["maastricht"]},
    {"canonical": "Bydgoszcz, Poland", "lat": 53.1235, "lon": 18.0084, "country": "POL", "region": "Europe", "aliases": ["bydgoszcz", "bydgoscz"]},
    {"canonical": "Chantilly, VA", "lat": 38.8943, "lon": -77.4311, "country": "USA", "region": "North America", "aliases": ["chantilly"]},
    {"canonical": "Yuma, AZ", "lat": 32.6927, "lon": -114.6277, "country": "USA", "region": "North America", "aliases": ["yuma"]},
    {"canonical": "Wellington, New Zealand", "lat": -41.2866, "lon": 174.7756, "country": "NZL", "region": "Asia-Pacific", "aliases": ["wellington"]},
    {"canonical": "Richmond, VA", "lat": 37.5407, "lon": -77.4360, "country": "USA", "region": "North America", "aliases": ["richmond"]},
    {"canonical": "Fort Lauderdale, FL", "lat": 26.1224, "lon": -80.1373, "country": "USA", "region": "North America", "aliases": ["fort lauderdale", "ft lauderdale"]},
    {"canonical": "Reston, VA", "lat": 38.9586, "lon": -77.3570, "country": "USA", "region": "North America", "aliases": ["reston"]},
    {"canonical": "Stockholm, Sweden", "lat": 59.3293, "lon": 18.0686, "country": "SWE", "region": "Europe", "aliases": ["stockholm"]},
    {"canonical": "London, United Kingdom", "lat": 51.5074, "lon": -0.1278, "country": "GBR", "region": "Europe", "aliases": ["london"]},
    {"canonical": "Newcastle, Australia", "lat": -32.9283, "lon": 151.7817, "country": "AUS", "region": "Asia-Pacific", "aliases": ["newcastle nsw", "newcastle, nsw"]},
    {"canonical": "Idar-Oberstein, Germany", "lat": 49.7144, "lon": 7.3078, "country": "DEU", "region": "Europe", "aliases": ["idar oberstein"]},
    {"canonical": "Palmerston North, New Zealand", "lat": -40.3523, "lon": 175.6082, "country": "NZL", "region": "Asia-Pacific", "aliases": ["palmerston north"]},
    {"canonical": "Oslo, Norway", "lat": 59.9139, "lon": 10.7522, "country": "NOR", "region": "Europe", "aliases": ["oslo"]},
    {"canonical": "Tampa, FL", "lat": 27.9506, "lon": -82.4572, "country": "USA", "region": "North America", "aliases": ["tampa"]},
    {"canonical": "Fort Bragg, NC", "lat": 35.1415, "lon": -79.0060, "country": "USA", "region": "North America", "aliases": ["fort bragg"]},
    {"canonical": "Edinburgh, United Kingdom", "lat": 55.9533, "lon": -3.1883, "country": "GBR", "region": "Europe", "aliases": ["edinburgh"]},
    {"canonical": "Farnborough, United Kingdom", "lat": 51.2869, "lon": -0.7526, "country": "GBR", "region": "Europe", "aliases": ["farmborough", "farnborough"]},
    {"canonical": "Lexington, MA", "lat": 42.4473, "lon": -71.2245, "country": "USA", "region": "North America", "aliases": ["lexington"]},
    {"canonical": "Bristol, United Kingdom", "lat": 51.4545, "lon": -2.5879, "country": "GBR", "region": "Europe", "aliases": ["bristol"]},
    {"canonical": "Bern, Switzerland", "lat": 46.9480, "lon": 7.4474, "country": "CHE", "region": "Europe", "aliases": ["bern"]},
    {"canonical": "Fort Leavenworth, KS", "lat": 39.3556, "lon": -94.9216, "country": "USA", "region": "North America", "aliases": ["fort leavenworth"]},
    {"canonical": "College Park, MD", "lat": 38.9807, "lon": -76.9369, "country": "USA", "region": "North America", "aliases": ["college park"]},
    {"canonical": "St. Augustine, FL", "lat": 29.9012, "lon": -81.3124, "country": "USA", "region": "North America", "aliases": ["st augustine"]},
    {"canonical": "Vienna, Austria", "lat": 48.2082, "lon": 16.3738, "country": "AUT", "region": "Europe", "aliases": ["vienna"]},
    {"canonical": "Dresden, Germany", "lat": 51.0504, "lon": 13.7373, "country": "DEU", "region": "Europe", "aliases": ["dresden"]},
    {"canonical": "Las Vegas, NV", "lat": 36.1699, "lon": -115.1398, "country": "USA", "region": "North America", "aliases": ["las vegas"]},
    {"canonical": "Nancy, France", "lat": 48.6921, "lon": 6.1844, "country": "FRA", "region": "Europe", "aliases": ["nancy"]},
    {"canonical": "Lyon, France", "lat": 45.7640, "lon": 4.8357, "country": "FRA", "region": "Europe", "aliases": ["lyon"]},
    {"canonical": "Bucharest, Romania", "lat": 44.4268, "lon": 26.1025, "country": "ROU", "region": "Europe", "aliases": ["bucharest"]},
    {"canonical": "Charleston, SC", "lat": 32.7765, "lon": -79.9311, "country": "USA", "region": "North America", "aliases": ["charleston"]},
    {"canonical": "Aberdeen Proving Ground, MD", "lat": 39.4735, "lon": -76.1408, "country": "USA", "region": "North America", "aliases": ["aberdeen proving ground"]},
    {"canonical": "Split, Croatia", "lat": 43.5081, "lon": 16.4402, "country": "HRV", "region": "Europe", "aliases": ["split"]},
    {"canonical": "Livermore, CA", "lat": 37.6819, "lon": -121.7680, "country": "USA", "region": "North America", "aliases": ["livermore"]},
    {"canonical": "Reno, NV", "lat": 39.5296, "lon": -119.8138, "country": "USA", "region": "North America", "aliases": ["reno"]},
    {"canonical": "Tallinn, Estonia", "lat": 59.4370, "lon": 24.7536, "country": "EST", "region": "Europe", "aliases": ["tallinn"]},
    {"canonical": "Paris, France", "lat": 48.8566, "lon": 2.3522, "country": "FRA", "region": "Europe", "aliases": ["paris"]},
    {"canonical": "Munich, Germany", "lat": 48.1351, "lon": 11.5820, "country": "DEU", "region": "Europe", "aliases": ["munich"]},
    {"canonical": "Ottawa, Canada", "lat": 45.4215, "lon": -75.6972, "country": "CAN", "region": "North America", "aliases": ["ottawa"]},
    {"canonical": "Stuttgart, Germany", "lat": 48.7758, "lon": 9.1829, "country": "DEU", "region": "Europe", "aliases": ["stuttgart"]},
    {"canonical": "Stavanger, Norway", "lat": 58.9700, "lon": 5.7331, "country": "NOR", "region": "Europe", "aliases": ["stavanger"]},
    {"canonical": "Charlottesville, VA", "lat": 38.0293, "lon": -78.4767, "country": "USA", "region": "North America", "aliases": ["charlottesville"]},
    {"canonical": "Pittsburgh, PA", "lat": 40.4406, "lon": -79.9959, "country": "USA", "region": "North America", "aliases": ["pittsburgh"]},
    {"canonical": "Koblenz, Germany", "lat": 50.3569, "lon": 7.5889, "country": "DEU", "region": "Europe", "aliases": ["koblenz"]},
    {"canonical": "Springfield, VA", "lat": 38.7893, "lon": -77.1872, "country": "USA", "region": "North America", "aliases": ["springfield"]},
    {"canonical": "West Bethesda, MD", "lat": 39.0026, "lon": -77.1174, "country": "USA", "region": "North America", "aliases": ["west bethesda"]},
    {"canonical": "Bournemouth, United Kingdom", "lat": 50.7192, "lon": -1.8808, "country": "GBR", "region": "Europe", "aliases": ["bournemouth"]},
    {"canonical": "Baltimore, MD", "lat": 39.2904, "lon": -76.6122, "country": "USA", "region": "North America", "aliases": ["baltimore"]},
]


def _location_match_text(value: str | None) -> str:
    text = (value or "").lower().replace("/", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def resolve_location(value: str | None) -> dict[str, Any]:
    raw = " ".join((value or "").split()).strip(" ,")
    searchable = _location_match_text(raw)
    if not searchable or searchable.startswith("tbd"):
        return {"canonical": raw or "Not provided", "lat": None, "lon": None, "country": "", "region": "Unmapped", "mapped": False, "confidence": 0.0}
    for entry in LOCATION_GEO_REGISTRY:
        for alias in entry["aliases"]:
            alias_text = _location_match_text(alias)
            if searchable.startswith(alias_text) or f" {alias_text} " in f" {searchable} ":
                return {
                    "canonical": entry["canonical"], "lat": entry["lat"], "lon": entry["lon"],
                    "country": entry["country"], "region": entry["region"], "mapped": True,
                    "confidence": 1.0 if searchable.startswith(alias_text) else 0.9,
                }
    return {"canonical": raw or "Not provided", "lat": None, "lon": None, "country": "", "region": "Unmapped", "mapped": False, "confidence": 0.0}


def excel_serial_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        raise ValueError("Date is required")
    try:
        return (datetime(1899, 12, 30) + timedelta(days=float(text))).date()
    except ValueError:
        pass
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date value: {text}")


def normalize_text(value: str | None) -> str:
    text = (value or "").lower().replace("&", " and ")
    text = re.sub(r"\b(working group|work group|meeting|conference|wg|mtg)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def division_code(value: str | None) -> str:
    text = " ".join((value or "").strip().split())
    lowered = text.lower()
    if lowered in DIVISION_ALIASES:
        return DIVISION_ALIASES[lowered]
    match = re.search(r"(?:DDC5I\s+)?([A-Z0-9]+)$", text, flags=re.I)
    return match.group(1).upper() if match else text.upper()


def _row_dict(headers: list[str], row: list[str]) -> dict[str, str]:
    padded = row + [""] * max(0, len(headers) - len(row))
    return {headers[i]: str(padded[i] or "").strip() for i in range(len(headers))}


def _org(db: Session, source_division: str) -> Organization | None:
    return db.query(Organization).filter(Organization.code == division_code(source_division)).first()


def _money(value: Any) -> Decimal:
    text = str(value or "0").replace("$", "").replace(",", "").strip()
    try:
        return Decimal(text or "0").quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError("Cost Estimate must be numeric") from exc


def validate_travel_request_rows(db: Session, rows: list[list[str]], user: User) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not rows:
        return [], {"valid": 0, "errors": 1, "warnings": 0, "skipped": 0}
    headers = [str(v).strip() for v in rows[0]]
    missing = [h for h in TRAVEL_REQUEST_HEADERS if h not in headers]
    if missing:
        result = {"row_number": 1, "record_identifier": "Workbook", "action": "Reject", "severity": "Error", "message": f"Missing columns: {', '.join(missing)}", "guidance": "Use the Travel Requests template or Power BI export.", "data": {}}
        return [result], {"valid": 0, "errors": 1, "warnings": 0, "skipped": 0}
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    skipped = 0
    for row_number, row in enumerate(rows[1:], 2):
        data = _row_dict(headers, row)
        external_id = data.get("ID", "")
        if external_id.lower() in {"", "total"} or (len(row) == 1 and row[0].startswith("Applied filters:")):
            skipped += 1
            continue
        errors: list[str] = []
        warnings: list[str] = []
        if external_id in seen:
            errors.append("Duplicate ID in workbook")
        seen.add(external_id)
        org = _org(db, data.get("Division"))
        if not org:
            errors.append(f"Unknown division: {data.get('Division') or 'blank'}")
        if not data.get("Traveler Full Name"):
            errors.append("Traveler Full Name is required")
        if not data.get("Travel Event or Forum Name"):
            errors.append("Travel Event or Forum Name is required")
        try:
            departure = excel_serial_date(data.get("Departure Date"))
            returned = excel_serial_date(data.get("Return Date"))
            if returned < departure:
                warnings.append("Return Date precedes Departure Date; source value retained for traceability")
        except ValueError as exc:
            errors.append(str(exc)); departure = returned = None
        try:
            cost = _money(data.get("Cost Estimate"))
            if cost < 0:
                errors.append("Cost Estimate cannot be negative")
        except ValueError as exc:
            errors.append(str(exc)); cost = Decimal("0")
        existing = db.query(TravelRequest).filter_by(source_system="Travel Approval Export", external_id=external_id).first()
        action = "Update" if existing else "Create"
        if data.get("DDS Determination") not in {"Approved", "Pending", "Canceled", "Cancelled", "Disapproved"}:
            warnings.append("Determination is outside the standard controlled values")
        data.update({"_org_id": org.id if org else None, "_departure": departure.isoformat() if departure else None, "_return": returned.isoformat() if returned else None, "_cost": str(cost)})
        severity = "Error" if errors else "Warning" if warnings else "Valid"
        results.append({
            "row_number": row_number,
            "record_identifier": external_id,
            "action": action if not errors else "Reject",
            "severity": severity,
            "message": "; ".join(errors or warnings) or "Ready to commit",
            "guidance": "Correct the source row and re-upload." if errors else "Review source values before commit." if warnings else "",
            "data": data,
        })
    summary = {
        "valid": sum(r["severity"] == "Valid" for r in results),
        "errors": sum(r["severity"] == "Error" for r in results),
        "warnings": sum(r["severity"] == "Warning" for r in results),
        "skipped": skipped,
    }
    return results, summary


def infer_sensitivity(*texts: str) -> str:
    joined = " ".join(texts).upper()
    if "(CUI)" in joined or "CONTROLLED UNCLASSIFIED" in joined:
        return "Controlled Unclassified"
    if "LIMITED DISTRIBUTION" in joined or "RESTRICTED" in joined:
        return "Restricted"
    return "Controlled Unclassified"


def validate_trip_report_rows(db: Session, rows: list[list[str]], user: User) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not rows:
        return [], {"valid": 0, "errors": 1, "warnings": 0, "skipped": 0}
    headers = [str(v).strip() for v in rows[0]]
    missing = [h for h in TRIP_REPORT_HEADERS if h not in headers]
    if missing:
        result = {"row_number": 1, "record_identifier": "Workbook", "action": "Reject", "severity": "Error", "message": f"Missing columns: {', '.join(missing)}", "guidance": "Use the Trip Reports template/export.", "data": {}}
        return [result], {"valid": 0, "errors": 1, "warnings": 0, "skipped": 0}
    results: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows[1:], 2):
        data = _row_dict(headers, row)
        if not any(data.values()):
            continue
        errors: list[str] = []
        warnings: list[str] = []
        org = _org(db, data.get("Division"))
        if not org:
            errors.append(f"Unknown division: {data.get('Division') or 'blank'}")
        if not data.get("Event Name/Title"):
            errors.append("Event Name/Title is required")
        if not data.get("Traveler Name"):
            errors.append("Traveler Name is required")
        try:
            start = excel_serial_date(data.get("Start Date"))
            returned = excel_serial_date(data.get("Return Date"))
            if returned < start:
                errors.append("Return Date precedes Start Date")
        except ValueError as exc:
            errors.append(str(exc)); start = returned = None
        if not data.get("Key Findings") and not data.get("Recommendations") and not data.get("Action Items (Specific to J6 DDC5I)"):
            warnings.append("No structured outcomes were supplied")
        source_record = f"{data.get('Path', '').strip()}:{row_number}"
        existing = db.query(TripReport).filter_by(source_system="Trip Reports SharePoint", source_record=source_record).first()
        data.update({
            "_org_id": org.id if org else None,
            "_start": start.isoformat() if start else None,
            "_return": returned.isoformat() if returned else None,
            "_sensitivity": infer_sensitivity(*data.values()),
            "_source_record": source_record,
        })
        severity = "Error" if errors else "Warning" if warnings else "Valid"
        results.append({
            "row_number": row_number,
            "record_identifier": data.get("Event Name/Title") or f"row-{row_number}",
            "action": ("Update" if existing else "Create") if not errors else "Reject",
            "severity": severity,
            "message": "; ".join(errors or warnings) or "Ready to commit",
            "guidance": "Correct the source row and re-upload." if errors else "Review the outcome fields before commit." if warnings else "",
            "data": data,
        })
    summary = {
        "valid": sum(r["severity"] == "Valid" for r in results),
        "errors": sum(r["severity"] == "Error" for r in results),
        "warnings": sum(r["severity"] == "Warning" for r in results),
        "skipped": 0,
    }
    return results, summary


def next_travel_id(db: Session, model: type, prefix: str) -> str:
    number = db.query(model).count() + 1
    candidate = f"{prefix}-26-{number:04d}"
    while db.query(model).filter(model.human_id == candidate).first():
        number += 1
        candidate = f"{prefix}-26-{number:04d}"
    return candidate


def find_or_create_engagement(
    db: Session,
    *,
    title: str,
    location: str,
    start_date: date,
    end_date: date,
    org_id: str | None,
    source_filename: str,
    source_row: int,
    raw_payload: dict[str, Any],
) -> TravelEngagement:
    normalized = normalize_text(title)
    candidates = db.query(TravelEngagement).filter(TravelEngagement.normalized_title == normalized).all()
    engagement = next((e for e in candidates if e.start_date == start_date and e.end_date == end_date), None)
    if not engagement:
        engagement = TravelEngagement(
            human_id=next_travel_id(db, TravelEngagement, "ENG"),
            title=title,
            normalized_title=normalized,
            location=location,
            start_date=start_date,
            end_date=end_date,
            status="Completed" if end_date < date.today() else "Planned",
            lead_org_id=org_id,
            source_record=f"{source_filename}:{source_row}",
            source_filename=source_filename,
            source_row=source_row,
            raw_payload=raw_payload,
        )
        db.add(engagement)
        db.flush()
    return engagement


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def match_candidates(db: Session, report: TripReport, limit: int = 5) -> list[dict[str, Any]]:
    query = db.query(TravelRequest).filter(TravelRequest.org_id == report.org_id)
    requests = query.all()
    results: list[dict[str, Any]] = []
    for request in requests:
        engagement = db.get(TravelEngagement, request.engagement_id) if request.engagement_id else None
        title_score = _similarity(report.title, engagement.title if engagement else "")
        traveler_score = _similarity(report.traveler_name, request.traveler_name)
        location_score = _similarity(report.location, request.location)
        overlap_days = max(0, (min(report.return_date, request.return_date) - max(report.start_date, request.departure_date)).days + 1)
        union_days = max(1, (max(report.return_date, request.return_date) - min(report.start_date, request.departure_date)).days + 1)
        date_score = overlap_days / union_days
        score = 0.35 * traveler_score + 0.30 * title_score + 0.20 * date_score + 0.10 + 0.05 * location_score
        results.append({
            "request": request,
            "engagement": engagement,
            "score": round(score, 4),
            "components": {
                "traveler": round(traveler_score, 3),
                "title": round(title_score, 3),
                "dates": round(date_score, 3),
                "location": round(location_score, 3),
            },
        })
    return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]


def apply_best_match(db: Session, report: TripReport, actor_id: str | None = None) -> list[dict[str, Any]]:
    candidates = match_candidates(db, report, limit=5)
    if not candidates:
        report.match_status = "Needs Reconciliation"
        report.match_rationale = "No travel requests were available in the report division."
        return candidates
    best = candidates[0]
    margin = best["score"] - (candidates[1]["score"] if len(candidates) > 1 else 0)
    report.match_confidence = best["score"]
    report.match_rationale = (
        f"Traveler {best['components']['traveler']:.2f}; title {best['components']['title']:.2f}; "
        f"dates {best['components']['dates']:.2f}; location {best['components']['location']:.2f}; margin {margin:.2f}."
    )
    if best["score"] >= 0.88 and margin >= 0.08:
        report.request_id = best["request"].id
        report.engagement_id = best["request"].engagement_id
        report.match_status = "Auto Matched"
        report.matched_by_id = actor_id
        report.matched_at = datetime.now(timezone.utc)
    elif best["score"] >= 0.72:
        report.match_status = "Suggested Match"
    else:
        report.match_status = "Needs Reconciliation"
    return candidates


def _split_outcomes(text: str) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    items: list[str] = []
    buffer = ""
    for line in lines:
        is_new = bool(re.match(r"^(?:[-•–]|\d+[\.)]|[a-z][\.)])\s*", line, flags=re.I))
        stripped = re.sub(r"^(?:[-•–]|\d+[\.)]|[a-z][\.)])\s*", "", line, flags=re.I).strip()
        if is_new and buffer:
            items.append(buffer.strip())
            buffer = stripped
        else:
            buffer = f"{buffer} {stripped}".strip()
    if buffer:
        items.append(buffer.strip())
    return items or [cleaned]


def ensure_report_items(db: Session, report: TripReport) -> list[TripReportItem]:
    existing = db.query(TripReportItem).filter(TripReportItem.report_id == report.id).all()
    if existing:
        return existing
    sequence = 1
    created: list[TripReportItem] = []
    for item_type, text in [
        ("Finding", report.key_findings),
        ("Recommendation", report.recommendations),
        ("Action Candidate", report.action_items),
    ]:
        for body in _split_outcomes(text):
            title = body.split(".", 1)[0][:240] or item_type
            item = TripReportItem(
                human_id=next_travel_id(db, TripReportItem, "TRI"),
                report_id=report.id,
                item_type=item_type,
                sequence=sequence,
                title=title,
                body=body,
                source_excerpt=body[:1000],
            )
            db.add(item); db.flush()
            created.append(item); sequence += 1
    return created


def refresh_engagement_rollups(db: Session) -> None:
    engagements = db.query(TravelEngagement).all()
    for engagement in engagements:
        requests = db.query(TravelRequest).filter(TravelRequest.engagement_id == engagement.id).all()
        org_ids = {r.org_id for r in requests}
        engagement.cross_division = len(org_ids) > 1
        if requests and not engagement.lead_org_id:
            engagement.lead_org_id = requests[0].org_id


def travel_dashboard_payload(
    requests: Iterable[TravelRequest],
    reports: Iterable[TripReport],
    engagements: Iterable[TravelEngagement],
    report_items: Iterable[TripReportItem] = (),
) -> dict[str, Any]:
    request_rows = list(requests)
    report_rows = list(reports)
    engagement_rows = list(engagements)
    item_rows = list(report_items)
    status_costs: dict[str, float] = defaultdict(float)
    status_counts = Counter()
    division_costs: dict[str, float] = defaultdict(float)
    division_status: dict[str, Counter] = defaultdict(Counter)
    month_costs: dict[str, float] = defaultdict(float)
    month_counts = Counter()
    location_rollup: dict[str, dict[str, Any]] = {}
    request_location: dict[str, str] = {}
    for item in request_rows:
        cost = float(item.estimated_cost or 0)
        status_costs[item.determination] += cost
        status_counts[item.determination] += 1
        division_costs[item.org_id] += cost
        division_status[item.org_id][item.determination] += 1
        month_key = item.departure_date.strftime("%Y-%m")
        month_costs[month_key] += cost
        month_counts[month_key] += 1
        geo = resolve_location(item.location)
        request_location[item.id] = geo["canonical"]
        row = location_rollup.setdefault(geo["canonical"], {
            **geo, "cost": 0.0, "count": 0, "approved_count": 0, "request_ids": set(),
            "engagement_ids": set(), "division_ids": set(), "report_ids": set(),
        })
        row["cost"] += cost
        row["count"] += 1
        row["approved_count"] += int(item.determination == "Approved")
        row["request_ids"].add(item.id)
        if item.engagement_id:
            row["engagement_ids"].add(item.engagement_id)
        row["division_ids"].add(item.org_id)
    for report in report_rows:
        canonical = request_location.get(report.request_id or "")
        if not canonical:
            canonical = resolve_location(report.location)["canonical"]
        if canonical in location_rollup:
            location_rollup[canonical]["report_ids"].add(report.id)
    location_rows = []
    for row in sorted(location_rollup.values(), key=lambda item: item["cost"], reverse=True):
        location_rows.append({
            "location": row["canonical"], "lat": row["lat"], "lon": row["lon"],
            "country": row["country"], "region": row["region"], "mapped": row["mapped"],
            "confidence": row["confidence"], "cost": round(row["cost"], 2), "count": row["count"],
            "approved_count": row["approved_count"], "report_count": len(row["report_ids"]),
            "engagement_count": len(row["engagement_ids"]), "division_count": len(row["division_ids"]),
        })
    matched_request_ids = {r.request_id for r in report_rows if r.request_id}
    completed_requests = [item for item in request_rows if item.return_date < date.today() and item.determination == "Approved"]
    completed_without_report = sum(1 for item in completed_requests if item.report_required and item.id not in matched_request_ids)
    reviewed_reports = sum(r.review_status in {"Reviewed", "Closed"} for r in report_rows)
    promoted_items = sum(bool(item.promoted_entity_type) for item in item_rows)
    mapped_requests = sum(row["count"] for row in location_rows if row["mapped"])
    compliance: dict[str, dict[str, int]] = defaultdict(lambda: {"approved_completed": 0, "linked_reports": 0, "reviewed_reports": 0, "overdue": 0})
    request_org = {item.id: item.org_id for item in request_rows}
    for item in completed_requests:
        compliance[item.org_id]["approved_completed"] += 1
        if item.id not in matched_request_ids and item.report_required:
            compliance[item.org_id]["overdue"] += 1
    for report in report_rows:
        org_id = request_org.get(report.request_id or "", report.org_id)
        if report.request_id:
            compliance[org_id]["linked_reports"] += 1
        if report.review_status in {"Reviewed", "Closed"}:
            compliance[org_id]["reviewed_reports"] += 1
    return {
        "total_estimated": round(sum(status_costs.values()), 2),
        "status_costs": dict(status_costs),
        "status_counts": dict(status_counts),
        "division_costs": dict(sorted(division_costs.items(), key=lambda kv: kv[1], reverse=True)),
        "division_status": {key: dict(value) for key, value in division_status.items()},
        "month_costs": dict(sorted(month_costs.items())),
        "month_counts": dict(sorted(month_counts.items())),
        "month_rows": [{"month": key, "cost": round(value, 2), "count": month_counts[key]} for key, value in sorted(month_costs.items())],
        "locations": {row["location"]: row["cost"] for row in location_rows[:20]},
        "location_rows": location_rows,
        "mapped_location_rows": [row for row in location_rows if row["mapped"]],
        "unmapped_location_rows": [row for row in location_rows if not row["mapped"]],
        "mapping_coverage": round(mapped_requests / len(request_rows) * 100, 1) if request_rows else 100.0,
        "request_count": len(request_rows),
        "engagement_count": len(engagement_rows),
        "report_count": len(report_rows),
        "matched_reports": sum(r.request_id is not None for r in report_rows),
        "reports_awaiting_review": sum(r.review_status not in {"Reviewed", "Closed"} for r in report_rows),
        "reconciliation_count": sum(r.match_status in {"Suggested Match", "Needs Reconciliation", "Unmatched"} for r in report_rows),
        "completed_without_report": completed_without_report,
        "cross_division_engagements": sum(bool(e.cross_division) for e in engagement_rows),
        "outcome_funnel": [
            {"key": "approved", "label": "Approved travel", "count": status_counts.get("Approved", 0)},
            {"key": "completed", "label": "Travel completed", "count": len(completed_requests)},
            {"key": "reported", "label": "Reports linked", "count": sum(r.request_id is not None for r in report_rows)},
            {"key": "reviewed", "label": "Reports reviewed", "count": reviewed_reports},
            {"key": "promoted", "label": "Outcomes promoted", "count": promoted_items},
        ],
        "compliance": dict(compliance),
    }


def commit_travel_request_result(
    db: Session,
    result: dict[str, Any],
    *,
    source_filename: str,
    import_batch_id: str | None = None,
) -> tuple[TravelRequest, str]:
    data = result["data"]
    external_id = data["ID"]
    existing = db.query(TravelRequest).filter_by(source_system="Travel Approval Export", external_id=external_id).first()
    action = "IMPORT_UPDATE" if existing else "IMPORT_CREATE"
    departure = date.fromisoformat(data["_departure"])
    returned = date.fromisoformat(data["_return"])
    engagement = find_or_create_engagement(
        db,
        title=data["Travel Event or Forum Name"],
        location=data.get("Location", ""),
        start_date=departure,
        end_date=returned,
        org_id=data["_org_id"],
        source_filename=source_filename,
        source_row=result["row_number"],
        raw_payload=data,
    )
    request = existing or TravelRequest(
        human_id=next_travel_id(db, TravelRequest, "TRV"),
        external_id=external_id,
        traveler_name=data["Traveler Full Name"],
        org_id=data["_org_id"],
        departure_date=departure,
        return_date=returned,
    )
    if not existing:
        db.add(request)
    request.engagement_id = engagement.id
    request.traveler_name = data["Traveler Full Name"]
    request.org_id = data["_org_id"]
    request.location = data.get("Location", "")
    request.determination = data.get("DDS Determination") or "Pending"
    request.departure_date = departure
    request.return_date = returned
    request.estimated_cost = Decimal(data["_cost"])
    request.report_due_date = returned + timedelta(days=10)
    request.source_record = external_id
    request.source_filename = source_filename
    request.source_row = result["row_number"]
    request.import_batch_id = import_batch_id
    request.raw_payload = data
    db.flush()
    return request, action


def commit_trip_report_result(
    db: Session,
    result: dict[str, Any],
    *,
    source_filename: str,
    import_batch_id: str | None = None,
    actor_id: str | None = None,
) -> tuple[TripReport, str, list[dict[str, Any]]]:
    data = result["data"]
    source_record = data["_source_record"]
    existing = db.query(TripReport).filter_by(source_system="Trip Reports SharePoint", source_record=source_record).first()
    action = "IMPORT_UPDATE" if existing else "IMPORT_CREATE"
    report = existing or TripReport(
        human_id=next_travel_id(db, TripReport, "TRP"),
        traveler_name=data["Traveler Name"],
        org_id=data["_org_id"],
        title=data["Event Name/Title"],
        start_date=date.fromisoformat(data["_start"]),
        return_date=date.fromisoformat(data["_return"]),
    )
    if not existing:
        db.add(report)
    report.traveler_name = data["Traveler Name"]
    report.org_id = data["_org_id"]
    report.title = data["Event Name/Title"]
    report.start_date = date.fromisoformat(data["_start"])
    report.return_date = date.fromisoformat(data["_return"])
    report.location = data.get("Location (City, State or Country)", "")
    report.purpose_objectives = data.get("Purpose/Objectives", "")
    report.discussion = data.get("Discussion", "")
    report.key_findings = data.get("Key Findings", "")
    report.recommendations = data.get("Recommendations", "")
    report.action_items = data.get("Action Items (Specific to J6 DDC5I)", "")
    report.sensitivity = data.get("_sensitivity", "Controlled Unclassified")
    report.source_record = source_record
    report.source_filename = source_filename
    report.source_row = result["row_number"]
    report.import_batch_id = import_batch_id
    report.raw_payload = data
    db.flush()
    candidates = apply_best_match(db, report, actor_id)
    if not existing:
        ensure_report_items(db, report)
    db.flush()
    return report, action, candidates
