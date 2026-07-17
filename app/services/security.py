from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

PBKDF2_ITERATIONS = 310_000
_serializer = URLSafeTimedSerializer(settings.secret_key, salt="ddc5i-session")

ENTERPRISE_ROLES = {
    "ADMIN",
    "SENIOR_LEADER",
    "ENTERPRISE_PORTFOLIO_OWNER",
    "PMO",
    "AUDITOR",
    "SECURITY_REVIEWER",
}
BUSINESS_EDIT_ROLES = {
    "ADMIN",
    "ENTERPRISE_PORTFOLIO_OWNER",
    "PMO",
    "DIVISION_CHIEF",
    "DIVISION_PORTFOLIO_MANAGER",
    "REQUESTER",
    "ASSESSOR",
    "APPROVAL_AUTHORITY",
    "PROJECT_MANAGER",
    "TEAM_MEMBER",
    "RESOURCE_MANAGER",
    "FINANCIAL_MANAGER",
    "BENEFITS_OWNER",
    "DATA_STEWARD",
}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_session_token(user_id: str) -> str:
    return _serializer.dumps({"user_id": user_id})


def read_session_token(token: str) -> str | None:
    try:
        data = _serializer.loads(token, max_age=settings.session_hours * 3600)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


def has_role(user, *roles: str) -> bool:
    return bool(set(user.roles or []).intersection(roles))


def is_enterprise_user(user) -> bool:
    return bool(set(user.roles or []).intersection(ENTERPRISE_ROLES))


def can_edit_business_data(user) -> bool:
    return bool(set(user.roles or []).intersection(BUSINESS_EDIT_ROLES)) and not (
        set(user.roles or []) == {"AUDITOR"}
    )


def can_access_org(user, org_id: str | None) -> bool:
    if org_id is None or is_enterprise_user(user):
        return True
    return user.division_id == org_id


def can_access_sensitive(user, sensitivity: str) -> bool:
    if sensitivity.lower() not in {"restricted", "sensitive", "limited distribution"}:
        return True
    return bool(user.sensitive_access or has_role(user, "ADMIN", "SECURITY_REVIEWER"))


def csrf_token(user_id: str) -> str:
    return hmac.new(settings.secret_key.encode(), f"csrf:{user_id}".encode(), hashlib.sha256).hexdigest()


def verify_csrf(user_id: str, token: str | None) -> bool:
    return bool(token and hmac.compare_digest(csrf_token(user_id), token))
