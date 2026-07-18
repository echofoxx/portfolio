from __future__ import annotations

import io
from pathlib import Path

from bs4 import BeautifulSoup

from app.models import AuditEvent, Notification, Project, Task, TaskAttachment, TaskComment, TaskRelationship, User
from app.services.security import csrf_token
from conftest import login


def _admin(db):
    return db.query(User).filter_by(username="admin").one()


def _task_and_project(db):
    task = db.query(Task).order_by(Task.human_id).first()
    return task, db.get(Project, task.project_id)


def test_global_search_finds_task_content_and_suggestions(client, db):
    task, project = _task_and_project(db)
    task.description = "Unique orbital interoperability acceptance phrase"
    db.commit()
    login(client, "admin")

    response = client.get("/search", params={"q": "orbital interoperability"})
    assert response.status_code == 200
    assert task.human_id in response.text
    assert "Task" in response.text
    assert f"task={task.id}" in response.text

    suggestions = client.get("/api/search/suggest", params={"q": task.human_id})
    assert suggestions.status_code == 200
    payload = suggestions.json()["results"]
    assert payload[0]["identifier"] == task.human_id
    assert payload[0]["url"].endswith(f"task={task.id}")


def test_search_box_has_intentional_keyboard_hint_and_csp_safe_controls(client):
    login(client, "admin")
    response = client.get("/dashboard")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    search = soup.find("form", {"class": "search-form"})
    assert search is not None
    assert search.find("kbd").get_text(strip=True) == "⌘K"
    assert "onclick=" not in response.text
    assert search.find("button", {"class": "search-submit"}) is not None


def test_task_drawer_loads_full_workspace(client, db):
    task, project = _task_and_project(db)
    login(client, "admin")
    response = client.get(f"/projects/{project.id}/tasks/{task.id}/panel")
    assert response.status_code == 200
    for expected in ["Task Details", "Working notes", "Attachments", "Notes and comments", "Task Dependencies", "Applicable requirements"]:
        assert expected in response.text


def test_task_details_notes_tags_and_assignment_are_persistent(client, db):
    task, project = _task_and_project(db)
    admin = _admin(db)
    new_owner = db.query(User).filter(User.id != task.owner_id, User.is_active.is_(True)).first()
    login(client, "admin")
    response = client.post(
        f"/projects/{project.id}/tasks/{task.id}/update",
        data={
            "csrf": csrf_token(admin.id),
            "title": task.title,
            "description": "Expanded task description and acceptance criteria.",
            "priority": "Critical",
            "status": "In Progress",
            "board_column": "In Progress",
            "owner_id": new_owner.id,
            "contributor_ids": [admin.id, new_owner.id],
            "start_date": "2026-07-01",
            "due_date": "2026-08-15",
            "baseline_due_date": "2026-08-01",
            "estimated_effort": "48",
            "actual_effort": "12.5",
            "percent_complete": "35",
            "tags": "integration, evidence, integration",
            "notes": "Detailed working notes retained with the authoritative task.",
            "acceptance_evidence": "Signed review memo and validation workbook.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    updated = db.get(Task, task.id)
    assert updated.description.startswith("Expanded")
    assert updated.priority == "Critical"
    assert updated.notes.startswith("Detailed")
    assert updated.tags == ["integration", "evidence"]
    assert updated.contributor_ids == [admin.id, new_owner.id]
    assert db.query(Notification).filter_by(user_id=new_owner.id).filter(Notification.title.contains(updated.human_id)).count() >= 1
    assert db.query(AuditEvent).filter_by(entity_id=updated.id, action="UPDATE").count() >= 1


def test_task_comment_mentions_and_checklist_workflow(client, db):
    task, project = _task_and_project(db)
    admin = _admin(db)
    mentioned = db.query(User).filter_by(username="pmo").one()
    login(client, "admin")

    comment = client.post(
        f"/projects/{project.id}/tasks/{task.id}/comments",
        data={"csrf": csrf_token(admin.id), "body": "@pmo please review the attached evidence and due date."},
        follow_redirects=False,
    )
    assert comment.status_code == 303
    assert db.query(TaskComment).filter_by(task_id=task.id).filter(TaskComment.body.contains("attached evidence")).count() == 1
    assert db.query(Notification).filter_by(user_id=mentioned.id, notification_type="Mention").count() >= 1

    add = client.post(
        f"/projects/{project.id}/tasks/{task.id}/checklist",
        data={"csrf": csrf_token(admin.id), "text": "Complete security review"},
        follow_redirects=False,
    )
    assert add.status_code == 303
    db.expire_all()
    updated = db.get(Task, task.id)
    item = next(x for x in updated.checklist if x["text"] == "Complete security review")
    toggle = client.post(
        f"/projects/{project.id}/tasks/{task.id}/checklist/{item['id']}/toggle",
        data={"csrf": csrf_token(admin.id)},
        follow_redirects=False,
    )
    assert toggle.status_code == 303
    db.expire_all()
    assert next(x for x in db.get(Task, task.id).checklist if x["id"] == item["id"])["done"] is True


def test_task_attachment_upload_download_and_delete(client, db, tmp_path, monkeypatch):
    task, project = _task_and_project(db)
    admin = _admin(db)
    login(client, "admin")

    # Settings are immutable, so patch the storage constructor used by the route.
    from app import main as main_module
    from app.services.storage import LocalVolumeStorage

    monkeypatch.setattr(main_module, "LocalVolumeStorage", lambda: LocalVolumeStorage(root=tmp_path, max_mb=2))
    payload = b"# Task Evidence\n\nValidated offline evidence package.\n"
    response = client.post(
        f"/projects/{project.id}/tasks/{task.id}/attachments",
        data={"csrf": csrf_token(admin.id), "description": "Validation evidence", "sensitivity": "Controlled Unclassified"},
        files={"attachment": ("evidence.md", io.BytesIO(payload), "text/markdown")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db.expire_all()
    attachment = db.query(TaskAttachment).filter_by(task_id=task.id, original_name="evidence.md").one()
    assert attachment.sha256
    assert (tmp_path / attachment.storage_key).exists()

    download = client.get(f"/projects/{project.id}/tasks/{task.id}/attachments/{attachment.id}")
    assert download.status_code == 200
    assert download.content == payload
    assert "attachment" in download.headers["content-disposition"]

    attachment_id = attachment.id
    storage_key = attachment.storage_key
    delete = client.post(
        f"/projects/{project.id}/tasks/{task.id}/attachments/{attachment_id}/delete",
        data={"csrf": csrf_token(admin.id)},
        follow_redirects=False,
    )
    assert delete.status_code == 303
    db.expire_all()
    removed = db.get(TaskAttachment, attachment_id)
    assert removed is not None
    assert removed.deleted_at is not None
    assert removed.is_current is False
    assert (tmp_path / storage_key).exists()


def test_invalid_binary_signature_is_rejected(client, db, tmp_path, monkeypatch):
    task, project = _task_and_project(db)
    admin = _admin(db)
    login(client, "admin")
    from app import main as main_module
    from app.services.storage import LocalVolumeStorage
    monkeypatch.setattr(main_module, "LocalVolumeStorage", lambda: LocalVolumeStorage(root=tmp_path, max_mb=2))

    response = client.post(
        f"/projects/{project.id}/tasks/{task.id}/attachments",
        data={"csrf": csrf_token(admin.id), "description": "Fake PDF", "sensitivity": "Controlled Unclassified"},
        files={"attachment": ("fake.pdf", io.BytesIO(b"not actually a pdf"), "application/pdf")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error" in response.headers["location"]
    assert db.query(TaskAttachment).filter_by(task_id=task.id, original_name="fake.pdf").count() == 0


def test_task_relationship_and_wbs_actions_are_persistent(client, db):
    task, project = _task_and_project(db)
    target = db.query(Task).filter(Task.project_id == project.id, Task.id != task.id).order_by(Task.sequence).first()
    admin = _admin(db)
    login(client, "admin")

    relation = client.post(
        f"/projects/{project.id}/tasks/{task.id}/relationships",
        data={"csrf": csrf_token(admin.id), "target_task_id": target.id, "relationship_type": "Finish-to-start"},
        follow_redirects=False,
    )
    assert relation.status_code == 303
    assert db.query(TaskRelationship).filter_by(source_task_id=task.id, target_task_id=target.id).count() == 1

    baseline = client.post(
        f"/projects/{project.id}/tasks/{task.id}/wbs-action",
        data={"csrf": csrf_token(admin.id), "action": "baseline"},
        follow_redirects=False,
    )
    assert baseline.status_code == 303
    db.expire_all()
    assert db.get(Task, task.id).baseline_due_date == db.get(Task, task.id).due_date


def test_search_does_not_leak_restricted_project_task_to_unapproved_user(client, db):
    restricted = db.query(Project).first()
    restricted.sensitivity = "Restricted"
    hidden_task = db.query(Task).filter(Task.project_id == restricted.id).first()
    hidden_task.title = "Needleword restricted task"
    db.commit()

    # `jamie.jad` is division-scoped and does not have sensitive access.
    login(client, "jamie.jad")
    response = client.get("/search", params={"q": "Needleword"})
    assert response.status_code == 200
    assert "Needleword restricted task" not in response.text

    suggestions = client.get("/api/search/suggest", params={"q": "Needleword"})
    assert suggestions.status_code == 200
    assert all(item["identifier"] != hidden_task.human_id for item in suggestions.json()["results"])
