from app.models import Demand, Organization, User
from app.services.security import can_access_org, can_access_sensitive, can_edit_business_data


def test_enterprise_and_division_scope(db):
    admin = db.query(User).filter_by(username="admin").one()
    division_user = db.query(User).filter(User.division_id.isnot(None)).first()
    another_org = db.query(Organization).filter(Organization.id != division_user.division_id, Organization.org_type == "Division").first()
    assert can_access_org(admin, another_org.id)
    assert can_access_org(division_user, division_user.division_id)
    assert not can_access_org(division_user, another_org.id)


def test_sensitive_access_is_explicit(db):
    restricted = db.query(Demand).filter_by(sensitivity="Restricted").one()
    ordinary = db.query(User).filter(User.division_id == restricted.lead_org_id, User.sensitive_access.is_(False)).first()
    admin = db.query(User).filter_by(username="admin").one()
    assert not can_access_sensitive(ordinary, restricted.sensitivity)
    assert can_access_sensitive(admin, restricted.sensitivity)


def test_auditor_is_read_only(db):
    auditor = db.query(User).filter_by(username="auditor").one()
    assert not can_edit_business_data(auditor)
