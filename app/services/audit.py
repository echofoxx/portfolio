from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models import AuditEvent


def _clean(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def snapshot(entity) -> dict:
    mapper = inspect(entity).mapper
    return {column.key: _clean(getattr(entity, column.key)) for column in mapper.column_attrs}


def record_audit(
    db: Session,
    actor_id: str | None,
    entity_type: str,
    entity_id: str,
    action: str,
    before: dict | None = None,
    after: dict | None = None,
    ip_address: str = "",
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=_clean(before),
        after_json=_clean(after),
        ip_address=ip_address,
    )
    db.add(event)
    return event
