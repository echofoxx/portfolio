import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Demand


def test_stable_human_identifier_is_unique(db):
    existing = db.query(Demand).first()
    clone = Demand(
        human_id=existing.human_id,
        title="Duplicate identifier",
        sponsor_id=existing.sponsor_id,
        requester_id=existing.requester_id,
        requesting_org_id=existing.requesting_org_id,
        lead_org_id=existing.lead_org_id,
    )
    db.add(clone)
    with pytest.raises(IntegrityError):
        db.flush()
