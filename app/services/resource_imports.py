from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Organization, ResourceCapacity


RESOURCE_COLUMNS = [
    "record_id", "division_code", "role_name", "skill", "period",
    "capacity_hours", "allocated_hours", "actual_hours", "minimum_core_coverage",
]


def _number(value: Any, label: str) -> float:
    try:
        number = float(str(value or "0").replace(",", "").strip())
    except ValueError as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if number < 0:
        raise ValueError(f"{label} cannot be negative")
    return number


def validate_resource_rows(db: Session, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    results: list[dict[str, Any]] = []
    counts = {"create": 0, "update": 0, "unchanged": 0, "errors": 0}
    seen: set[tuple[str, str, str, str]] = set()
    for row_number, raw in enumerate(rows, start=2):
        data = {key: str(raw.get(key, "") or "").strip() for key in RESOURCE_COLUMNS}
        division_code = data["division_code"].upper()
        errors: list[str] = []
        org = db.query(Organization).filter(Organization.code == division_code, Organization.org_type == "Division").first()
        if not org: errors.append(f"Unknown division code: {division_code or 'blank'}")
        if not data["role_name"]: errors.append("role_name is required")
        if not data["skill"]: errors.append("skill is required")
        if not data["period"]: errors.append("period is required")
        numbers: dict[str, float] = {}
        for field in ("capacity_hours", "allocated_hours", "actual_hours", "minimum_core_coverage"):
            try: numbers[field] = _number(data[field], field)
            except ValueError as exc: errors.append(str(exc))
        key = (division_code, data["role_name"].lower(), data["skill"].lower(), data["period"].lower())
        if key in seen: errors.append("Duplicate division/role/skill/period key in upload")
        seen.add(key)
        existing = None
        if data["record_id"]:
            existing = db.get(ResourceCapacity, data["record_id"])
            if not existing: errors.append("record_id does not match an existing resource capacity record")
        if not existing and org:
            existing = db.query(ResourceCapacity).filter(
                ResourceCapacity.org_id == org.id, ResourceCapacity.role_name == data["role_name"],
                ResourceCapacity.skill == data["skill"], ResourceCapacity.period == data["period"],
            ).first()
        normalized = {**data, **numbers, "org_id": org.id if org else "", "existing_id": existing.id if existing else ""}
        if errors:
            action, severity = "Reject", "Error"; counts["errors"] += 1
        elif existing:
            unchanged = all(float(getattr(existing, field) or 0) == numbers[field] for field in numbers)
            action, severity = ("Unchanged", "Info") if unchanged else ("Update", "Warning")
            counts["unchanged" if unchanged else "update"] += 1
        else:
            action, severity = "Create", "Success"; counts["create"] += 1
        results.append({
            "row_number": row_number, "record_identifier": data["record_id"] or "new",
            "action": action, "severity": severity, "message": "; ".join(errors) if errors else f"{action} resource capacity row",
            "data": normalized,
        })
    return results, counts
