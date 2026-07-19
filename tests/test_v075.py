from __future__ import annotations

import io
import json
import zipfile

from app.models import AuditEvent, DivisionProfile, Organization, User
from app.services.security import csrf_token
from conftest import login
from app.config import APP_VERSION


def test_v075_division_identity_profiles_and_banners_render(client, db):
    login(client, "admin")
    expected_names = {
        "CID": "Coalition Interoperability Division",
        "JFID": "Joint Fires Integration Division",
        "C3OD2": "Cyber & C2 Operational Development Division",
    }
    for code, name in expected_names.items():
        org = db.query(Organization).filter_by(code=code).one()
        assert org.name == name
        profile = db.query(DivisionProfile).filter_by(org_id=org.id).one()
        assert profile.mission
        assert profile.banner_asset == f"/static/division-banners/{code.lower()}.webp"
        assert profile.banner_alt

    response = client.get("/divisions")
    assert response.status_code == 200
    for code in ["JFID", "JAD", "DSD", "CID", "C3OD2", "AID"]:
        assert f"/static/division-banners/{code.lower()}.webp" in response.text

    detail = client.get("/divisions/CID")
    assert detail.status_code == 200
    assert "Coalition Interoperability Division" in detail.text
    assert "Current view" in detail.text
    assert "Briefing view" in detail.text
    assert "About this division" in detail.text
    assert "Export" in detail.text
    assert f'/static/app.css?v={APP_VERSION}' in detail.text


def test_v075_division_json_and_csv_package_exports(client, db):
    login(client, "admin")
    response = client.get("/divisions/DSD/export/json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    payload = response.json()
    assert payload["schema_version"] == APP_VERSION
    assert payload["division"]["division_code"] == "DSD"
    assert payload["division"]["official_name"] == "Data and Standards Division"
    assert isinstance(payload["projects"], list)
    assert isinstance(payload["demands"], list)

    response = client.get("/divisions/DSD/export/csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(response.content)) as package:
        names = set(package.namelist())
        assert {"division_profile.csv", "projects.csv", "demands.csv", "financials.csv", "README.txt"}.issubset(names)
        profile_csv = package.read("division_profile.csv").decode("utf-8")
        assert "division_code" in profile_csv
        assert "DSD" in profile_csv


def test_v075_profile_edit_and_json_import_are_previewed_and_audited(client, db):
    admin = db.query(User).filter_by(username="admin").one()
    login(client, "admin")
    org = db.query(Organization).filter_by(code="AID").one()
    profile = db.query(DivisionProfile).filter_by(org_id=org.id).one()

    edit = client.post(
        "/divisions/AID/profile/edit",
        data={
            "csrf": csrf_token(admin.id),
            "mission": profile.mission,
            "vision": profile.vision,
            "focus_areas": "C5 Architecture\nMission Threads\nMission Analysis\nIntegrated Capability",
            "responsibilities": "Develop architecture baselines.\nValidate mission-thread integration.",
            "branches": "Architecture Branch | Reference architecture and design",
            "initiatives": "CJADC2 Chief Architect\nJCSFL",
            "relationships": "DoD CIO | Enterprise architecture coordination | OSD",
            "forums": "EASB | Support / Advise | Enterprise architecture governance",
            "doctrine": "WMA Architecture Standards | Chief architect | Maintain standards",
            "banner_asset": profile.banner_asset,
            "banner_alt": profile.banner_alt,
            "focal_x": "50",
            "focal_y": "50",
            "status": "Published",
            "source_documents": "AID Division Outline.docx",
            "source_notes": "Acceptance test update.",
        },
        follow_redirects=False,
    )
    assert edit.status_code == 303
    db.expire_all()
    assert "Integrated Capability" in db.query(DivisionProfile).filter_by(org_id=org.id).one().focus_areas

    imported = {
        "mission": profile.mission,
        "vision": "An imported, validated architecture vision.",
        "focus_areas": ["Architecture", "Mission Threads"],
        "responsibilities": ["Integrate architecture evidence."],
        "branches": [{"name": "Integration Branch", "focus": "Cross-domain integration"}],
        "initiatives": ["CJADC2 Reference Architecture"],
        "relationships": [{"name": "DoD CIO", "role": "Coordinate", "category": "OSD"}],
        "forums": [{"name": "EASB", "role": "Support", "purpose": "Governance"}],
        "doctrine": [],
        "banner_asset": "/static/division-banners/aid.webp",
        "banner_alt": profile.banner_alt,
        "focal_x": 52,
        "focal_y": 48,
        "status": "Published",
        "source_documents": ["AID Division Outline.docx"],
        "source_notes": "Imported in acceptance test.",
    }
    preview = client.post(
        "/divisions/AID/profile/import/preview",
        data={"csrf": csrf_token(admin.id)},
        files={"file": ("aid-profile.json", json.dumps(imported), "application/json")},
    )
    assert preview.status_code == 200
    assert "Review AID profile import" in preview.text
    assert "An imported, validated architecture vision." in preview.text

    commit = client.post(
        "/divisions/AID/profile/import/commit",
        data={"csrf": csrf_token(admin.id), "payload_json": json.dumps(imported)},
        follow_redirects=False,
    )
    assert commit.status_code == 303
    db.expire_all()
    updated = db.query(DivisionProfile).filter_by(org_id=org.id).one()
    assert updated.vision == "An imported, validated architecture vision."
    assert updated.focal_x == 52
    assert db.query(AuditEvent).filter_by(entity_type="DivisionProfile", entity_id=updated.id, action="IMPORT").count() >= 1


def test_v075_read_only_auditor_cannot_edit_profile(client):
    login(client, "auditor")
    response = client.get("/divisions/CID/profile/edit")
    assert response.status_code == 403