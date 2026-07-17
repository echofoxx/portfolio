from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Demand, Mission, Organization, User

DEMAND_COLUMNS = [
    "Human ID",
    "Title",
    "Category",
    "Status",
    "Lead Division",
    "Mission Code",
    "Purpose",
    "Problem or Opportunity",
    "Desired End State",
    "Urgency",
    "ROM Cost",
    "Expected Benefits",
    "Sensitivity",
]


def validate_demand_rows(db: Session, rows: list[list[str]], user: User) -> tuple[list[dict], dict]:
    if not rows:
        return [], {"new": 0, "updated": 0, "duplicates": 0, "warnings": 0, "errors": 1}
    headers = [h.strip() for h in rows[0]]
    missing = [h for h in DEMAND_COLUMNS if h not in headers]
    if missing:
        return [
            {
                "row_number": 1,
                "record_identifier": "",
                "action": "Excluded",
                "severity": "Error",
                "message": f"Missing required columns: {', '.join(missing)}",
                "guidance": "Use the versioned demand template.",
                "data": {},
            }
        ], {"new": 0, "updated": 0, "duplicates": 0, "warnings": 0, "errors": 1}
    idx = {h: headers.index(h) for h in headers}
    results = []
    summary = {"new": 0, "updated": 0, "duplicates": 0, "warnings": 0, "errors": 0}
    seen = set()
    orgs = {o.code: o for o in db.query(Organization).all()}
    missions = {m.code: m for m in db.query(Mission).all()}
    for row_number, row in enumerate(rows[1:], start=2):
        row = row + [""] * (len(headers) - len(row))
        data = {h: row[idx[h]].strip() for h in headers}
        rid = data.get("Human ID", "")
        title = data.get("Title", "")
        errors, warnings = [], []
        if not title:
            errors.append("Title is required")
        if rid and rid in seen:
            errors.append("Duplicate identifier in upload")
        if rid:
            seen.add(rid)
        org = orgs.get(data.get("Lead Division", ""))
        if not org:
            errors.append("Lead Division must match an organization code")
        elif user.division_id and user.division_id != org.id and "ADMIN" not in (user.roles or []) and "PMO" not in (user.roles or []):
            errors.append("Permission exclusion: record is outside your division scope")
        mission = missions.get(data.get("Mission Code", ""))
        if not mission:
            errors.append("Mission Code is not valid")
        if data.get("Sensitivity", "").lower() == "restricted" and not user.sensitive_access:
            errors.append("Permission exclusion: restricted record")
        try:
            rom = float(data.get("ROM Cost") or 0)
            if rom < 0:
                errors.append("ROM Cost cannot be negative")
        except ValueError:
            errors.append("ROM Cost must be numeric")
            rom = 0
        existing = db.query(Demand).filter(Demand.human_id == rid).first() if rid else None
        same_title = db.query(Demand).filter(Demand.title.ilike(title)).first() if title else None
        if same_title and (not existing or same_title.id != existing.id):
            warnings.append(f"Possible duplicate of {same_title.human_id}")
        if errors:
            action, severity = "Excluded", "Error"
            summary["errors"] += 1
        elif existing:
            action, severity = "Update", "Warning" if warnings else "Success"
            summary["updated"] += 1
            summary["warnings"] += bool(warnings)
        else:
            action, severity = "Create", "Warning" if warnings else "Success"
            summary["new"] += 1
            summary["warnings"] += bool(warnings)
        if same_title and not existing:
            summary["duplicates"] += 1
        results.append(
            {
                "row_number": row_number,
                "record_identifier": rid or "AUTO",
                "action": action,
                "severity": severity,
                "message": "; ".join(errors or warnings) or "Validated",
                "guidance": "Correct the highlighted values and re-import." if errors else "Review before commit." if warnings else "Ready to commit.",
                "data": {**data, "_rom": rom, "_org_id": org.id if org else None, "_mission_id": mission.id if mission else None},
            }
        )
    return results, summary
