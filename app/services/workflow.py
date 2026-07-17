from __future__ import annotations

ALLOWED_TRANSITIONS = {
    "Draft": {"Submitted"},
    "Submitted": {"Triage", "Withdrawn"},
    "Triage": {"Clarification Required", "Assessment", "Withdrawn"},
    "Clarification Required": {"Submitted", "Withdrawn"},
    "Assessment": {"Awaiting Portfolio Recommendation", "Clarification Required"},
    "Awaiting Portfolio Recommendation": {"Awaiting Decision", "Assessment"},
    "Awaiting Decision": {"Approved", "Deferred", "Declined", "Assessment"},
    "Approved": {"Converted to Execution", "Deferred"},
    "Deferred": {"Assessment", "Closed"},
    "Declined": {"Closed"},
    "Withdrawn": {"Draft", "Closed"},
    "Converted to Execution": {"Closed"},
    "Closed": set(),
}

ROLE_TRANSITION_RULES = {
    "Submitted": {"REQUESTER", "ADMIN"},
    "Triage": {"PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN"},
    "Clarification Required": {"PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN"},
    "Assessment": {"PMO", "DIVISION_PORTFOLIO_MANAGER", "ASSESSOR", "ADMIN"},
    "Awaiting Portfolio Recommendation": {"ASSESSOR", "PMO", "DIVISION_PORTFOLIO_MANAGER", "ADMIN"},
    "Awaiting Decision": {"PMO", "ENTERPRISE_PORTFOLIO_OWNER", "DIVISION_PORTFOLIO_MANAGER", "ADMIN"},
    "Approved": {"APPROVAL_AUTHORITY", "SENIOR_LEADER", "ADMIN"},
    "Deferred": {"APPROVAL_AUTHORITY", "SENIOR_LEADER", "ADMIN"},
    "Declined": {"APPROVAL_AUTHORITY", "SENIOR_LEADER", "ADMIN"},
    "Converted to Execution": {"PMO", "PROJECT_MANAGER", "ADMIN"},
    "Withdrawn": {"REQUESTER", "ADMIN"},
    "Closed": {"PMO", "PROJECT_MANAGER", "ADMIN"},
    "Draft": {"REQUESTER", "ADMIN"},
}


def validate_transition(current: str, target: str, user_roles: list[str]) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"Transition from {current} to {target} is not allowed")
    allowed_roles = ROLE_TRANSITION_RULES.get(target, {"ADMIN"})
    if not set(user_roles).intersection(allowed_roles):
        raise PermissionError(f"Your role cannot move a demand to {target}")
