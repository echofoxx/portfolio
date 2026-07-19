from __future__ import annotations

from datetime import date, timedelta

from app.models import (
    BriefingSection,
    BriefingSnapshot,
    Organization,
    PortfolioReview,
    Project,
    ReviewChangeRequest,
    ReviewQuestion,
    User,
)
from app.services.briefings import division_briefing_payload
from app.services.security import csrf_token
from conftest import login
from app.config import APP_VERSION


def admin(db):
    return db.query(User).filter_by(username="admin").one()


def create_briefing(client, db, title: str) -> PortfolioReview:
    owner = admin(db)
    division = db.query(Organization).filter_by(org_type="Division").order_by(Organization.code).first()
    response = client.post(
        "/portfolio-reviews",
        data={
            "csrf": csrf_token(owner.id),
            "title": title,
            "review_type": "Division Briefing",
            "portfolio_id": "",
            "org_id": division.id,
            "period_start": (date.today() - timedelta(days=30)).isoformat(),
            "period_end": date.today().isoformat(),
            "chair_id": owner.id,
            "participant_ids": [owner.id],
            "summary": "Acceptance-test division briefing.",
            "decisions_required": "Confirm recovery and cross-division support.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].endswith("/brief")
    db.expire_all()
    return db.query(PortfolioReview).filter_by(title=title).one()


def test_v070_navigation_and_seeded_briefing_render(client, db):
    login(client, "admin")
    response = client.get("/portfolio-reviews")
    assert response.status_code == 200
    assert "Briefings" in response.text
    assert "Division Briefing" in response.text
    seeded = db.query(PortfolioReview).filter_by(review_type="Division Briefing").first()
    assert seeded is not None
    detail = client.get(f"/portfolio-reviews/{seeded.id}/brief")
    assert detail.status_code == 200
    for marker in [
        "Division summary",
        "Source-backed evidence",
        "Questions &amp; follow-up",
        "Presentation mode",
        "Mission and operating context",
        "Previous-review action status",
    ]:
        assert marker in detail.text


def test_v070_create_generates_standard_sections_and_source_summary(client, db):
    owner = admin(db)
    login(client, "admin")
    review = create_briefing(client, db, "v0.7 Standard Section Acceptance")
    sections = db.query(BriefingSection).filter_by(review_id=review.id).order_by(BriefingSection.sort_order).all()
    assert len(sections) == 16
    assert sections[0].section_key == "mission-context"
    assert sections[-1].section_key == "prior-actions"
    assert all(section.source_summary is not None for section in sections)
    response = client.get(f"/portfolio-reviews/{review.id}/brief")
    assert response.status_code == 200
    assert f'/static/app.css?v={APP_VERSION}' in response.text
    assert "0%" in response.text
    assert csrf_token(owner.id) in response.text


def test_v070_lifecycle_snapshot_questions_changes_and_my_work(client, db):
    owner = admin(db)
    login(client, "admin")
    review = create_briefing(client, db, "v0.7 Lifecycle Acceptance")
    sections = db.query(BriefingSection).filter_by(review_id=review.id).order_by(BriefingSection.sort_order).all()

    for section in sections:
        response = client.post(
            f"/portfolio-reviews/{review.id}/briefing/sections/{section.id}",
            data={
                "csrf": csrf_token(owner.id),
                "narrative": f"Leadership narrative for {section.title}.",
                "owner_id": owner.id,
                "status": "Ready for Division Review",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    response = client.post(
        f"/portfolio-reviews/{review.id}/briefing/lifecycle",
        data={"csrf": csrf_token(owner.id), "action": "submit"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    assert db.get(PortfolioReview, review.id).status == "Ready for Division Review"

    project = db.query(Project).filter_by(lead_org_id=review.org_id).first()
    original_health = project.health_owner if project else None
    response = client.post(
        f"/portfolio-reviews/{review.id}/briefing/lifecycle",
        data={"csrf": csrf_token(owner.id), "action": "approve"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    approved = db.get(PortfolioReview, review.id)
    snapshot = db.query(BriefingSnapshot).filter_by(review_id=review.id).one()
    assert approved.status == "Ready to Brief"
    assert len(snapshot.payload["sections"]) == 16
    frozen_narrative = snapshot.payload["sections"][0]["narrative"]
    response = client.post(
        f"/portfolio-reviews/{review.id}/briefing/sections/{sections[0].id}",
        data={"csrf": csrf_token(owner.id), "narrative": "Unauthorized post-approval edit", "owner_id": owner.id, "status": "Ready to Brief"},
        follow_redirects=False,
    )
    assert response.status_code == 404
    db.expire_all()
    assert db.query(BriefingSnapshot).filter_by(review_id=review.id).one().payload["sections"][0]["narrative"] == frozen_narrative
    if project:
        frozen = next(item for item in snapshot.payload["projects"] if item["id"] == project.id)
        project.health_owner = "Blocked" if original_health != "Blocked" else "On Track"
        db.commit()
        db.refresh(snapshot)
        assert next(item for item in snapshot.payload["projects"] if item["id"] == project.id)["health"] == frozen["health"]

    response = client.post(
        f"/portfolio-reviews/{review.id}/briefing/lifecycle",
        data={"csrf": csrf_token(owner.id), "action": "start"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    assert db.get(PortfolioReview, review.id).status == "In Review"

    section = sections[0]
    response = client.post(
        f"/portfolio-reviews/{review.id}/briefing/questions",
        data={
            "csrf": csrf_token(owner.id),
            "section_id": section.id,
            "question": "What changed since the prior review?",
            "assigned_to_id": owner.id,
            "priority": "High",
            "due_date": (date.today() + timedelta(days=2)).isoformat(),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    response = client.post(
        f"/portfolio-reviews/{review.id}/briefing/change-requests",
        data={
            "csrf": csrf_token(owner.id),
            "section_id": section.id,
            "field_name": "health_owner",
            "current_value": original_health or "On Track",
            "proposed_value": "At Risk",
            "rationale": "Leadership requested source validation.",
            "owner_id": owner.id,
            "due_date": (date.today() + timedelta(days=3)).isoformat(),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    question = db.query(ReviewQuestion).filter_by(review_id=review.id, question="What changed since the prior review?").one()
    change = db.query(ReviewChangeRequest).filter_by(review_id=review.id, field_name="health_owner").one()

    my_work = client.get("/my-work")
    assert my_work.status_code == 200
    assert question.human_id in my_work.text
    assert change.human_id in my_work.text
    # v0.7.9: briefing follow-ups now surface in the unified Action Center queue
    assert "Awaiting me" in my_work.text

    response = client.post(
        f"/portfolio-reviews/{review.id}/briefing/questions/{question.id}/respond",
        data={"csrf": csrf_token(owner.id), "response": "The status changed after the latest dependency review.", "status": "Closed"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    response = client.post(
        f"/portfolio-reviews/{review.id}/briefing/change-requests/{change.id}/resolve",
        data={"csrf": csrf_token(owner.id), "status": "Accepted", "resolution": "Owner will update the authoritative project record."},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    assert db.get(ReviewQuestion, question.id).status == "Closed"
    assert db.get(ReviewChangeRequest, change.id).status == "Accepted"


def test_v070_closeout_requires_open_followup_acknowledgement(client, db):
    owner = admin(db)
    login(client, "admin")
    review = create_briefing(client, db, "v0.7 Closeout Acceptance")
    review.status = "In Review"
    db.commit()
    question = ReviewQuestion(
        human_id="QUE-V070-CLOSE",
        review_id=review.id,
        question="Provide the final evidence after the meeting.",
        asked_by_id=owner.id,
        assigned_to_id=owner.id,
        status="Open",
    )
    db.add(question)
    db.commit()

    response = client.post(
        f"/portfolio-reviews/{review.id}/complete",
        data={"csrf": csrf_token(owner.id), "summary": "Review completed with follow-up."},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "acknowledge" in response.headers["location"].lower()
    db.expire_all()
    assert db.get(PortfolioReview, review.id).status == "In Review"

    response = client.post(
        f"/portfolio-reviews/{review.id}/complete",
        data={"csrf": csrf_token(owner.id), "summary": "Review completed with follow-up.", "acknowledge_open_items": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    assert db.get(PortfolioReview, review.id).status == "Completed"


def test_v070_standard_payload_excludes_restricted_records_and_auditor_is_read_only(client, db):
    owner = admin(db)
    division = db.query(Organization).filter_by(org_type="Division").order_by(Organization.code).first()
    restricted_project = db.query(Project).filter_by(lead_org_id=division.id).first()
    assert restricted_project is not None
    original_sensitivity = restricted_project.sensitivity
    restricted_project.sensitivity = "Restricted"
    review = PortfolioReview(
        human_id="REV-V070-SEC",
        title="Restricted boundary acceptance",
        review_type="Division Briefing",
        org_id=division.id,
        period_start=date.today() - timedelta(days=30),
        period_end=date.today(),
        chair_id=owner.id,
        participant_ids=[owner.id],
        status="In Review",
    )
    db.add(review)
    db.commit()
    payload = division_briefing_payload(db, review)
    assert restricted_project.id not in {project["id"] for project in payload["projects"]}
    assert payload["metrics"]["excluded_sensitive_projects"] >= 1

    auditor = db.query(User).filter_by(username="auditor").one()
    client.cookies.clear()
    login(client, "auditor")
    response = client.get(f"/portfolio-reviews/{review.id}/brief")
    assert response.status_code == 200
    assert "Ask a question" not in response.text
    response = client.post(
        f"/portfolio-reviews/{review.id}/briefing/questions",
        data={"csrf": csrf_token(auditor.id), "question": "Auditor mutation should fail."},
        follow_redirects=False,
    )
    assert response.status_code == 403

    restricted_project.sensitivity = original_sensitivity
    db.commit()