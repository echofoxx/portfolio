import pytest

from app.services.workflow import validate_transition


def test_valid_stage_gate_transition():
    validate_transition("Submitted", "Triage", ["PMO"])
    validate_transition("Awaiting Decision", "Approved", ["APPROVAL_AUTHORITY"])


def test_invalid_transition_is_rejected():
    with pytest.raises(ValueError):
        validate_transition("Draft", "Approved", ["ADMIN"])


def test_role_restriction_is_enforced():
    with pytest.raises(PermissionError):
        validate_transition("Awaiting Decision", "Approved", ["REQUESTER"])
