from app.models import AuditEvent, Demand, User
from app.services.audit import record_audit, snapshot


def test_material_change_has_before_and_after(db):
    actor = db.query(User).filter_by(username="admin").one()
    demand = db.query(Demand).first()
    before = snapshot(demand)
    demand.title = demand.title + " (test)"
    after = snapshot(demand)
    event = record_audit(db, actor.id, "Demand", demand.id, "UPDATE", before=before, after=after)
    db.flush()
    assert event.before_json["title"] != event.after_json["title"]
    assert db.query(AuditEvent).filter_by(id=event.id).one().action == "UPDATE"
