from io import BytesIO

import pytest

from app.services.integrations import FieldOwnershipRule, IntegrationRegistry
from app.services.jobs import InlineJobRunner, JobStatus
from app.services.storage import LocalVolumeStorage


def test_field_ownership_registry_blocks_unapproved_writer():
    registry = IntegrationRegistry()
    rule = FieldOwnershipRule("Project", "status", "ProjectOS", ("ProjectOS",))
    registry.register_ownership(rule)
    registry.assert_write_allowed("Project", "status", "ProjectOS")
    with pytest.raises(PermissionError):
        registry.assert_write_allowed("Project", "status", "DDC5I-PM")
    with pytest.raises(ValueError):
        registry.register_ownership(FieldOwnershipRule("Project", "status", "DDC5I-PM", ("DDC5I-PM",)))
    assert registry.ownership_rules() == [rule]
    with pytest.raises(KeyError):
        registry.adapter("missing")


def test_inline_job_runner_records_success_and_failure():
    runner = InlineJobRunner()
    success = runner.submit("sum", lambda a, b: {"value": a + b}, a=2, b=3)
    assert success.status == JobStatus.SUCCEEDED
    assert success.result == {"value": 5}
    failure = runner.submit("fail", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert failure.status == JobStatus.FAILED
    assert failure.error == "boom"
    assert failure.completed_at is not None


def test_local_storage_validates_and_hashes(tmp_path):
    storage = LocalVolumeStorage(tmp_path, max_mb=1)
    payload = b"portfolio evidence"
    saved = storage.save(BytesIO(payload), "../safe evidence.txt", "text/plain", len(payload))
    assert saved.original_name == "../safe evidence.txt"
    assert saved.storage_key.endswith("safe_evidence.txt")
    assert storage.open(saved.storage_key).read() == payload
    storage.delete(saved.storage_key)
    with pytest.raises(FileNotFoundError):
        storage.open(saved.storage_key)
    with pytest.raises(ValueError):
        storage.save(BytesIO(b"x"), "malware.exe", "application/octet-stream", 1)
    with pytest.raises(ValueError):
        storage.save(BytesIO(b"x"), "too-large.txt", "text/plain", 2 * 1024 * 1024)
