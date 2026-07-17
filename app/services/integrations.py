"""Integration contracts and synchronization registry.

The MVP does not require live enterprise integrations. These contracts make field
ownership, canonical identifiers, retries, lineage, and reconciliation explicit
before any connector is enabled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol


class SyncDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class Authority(str, Enum):
    LOCAL = "DDC5I-PM"
    REMOTE = "remote-system"
    GOVERNED = "governance-required"


@dataclass(frozen=True)
class FieldOwnershipRule:
    entity_type: str
    field_name: str
    authoritative_system: str
    allowed_writers: tuple[str, ...]
    conflict_policy: str = "reject-and-reconcile"


@dataclass
class SyncEnvelope:
    event_id: str
    event_type: str
    entity_type: str
    canonical_id: str
    source_system: str
    source_record_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"
    correlation_id: str | None = None


@dataclass
class SyncResult:
    success: bool
    canonical_id: str
    remote_id: str | None = None
    retryable: bool = False
    message: str = ""
    lineage: dict[str, Any] = field(default_factory=dict)


class IntegrationAdapter(Protocol):
    name: str

    def health(self) -> dict[str, Any]: ...
    def publish(self, envelope: SyncEnvelope) -> SyncResult: ...
    def pull(self, cursor: str | None = None) -> tuple[list[SyncEnvelope], str | None]: ...
    def reconcile(self, canonical_id: str) -> SyncResult: ...


class ProjectOSAdapter(IntegrationAdapter, Protocol):
    """Contract for task, schedule, document, and delivery-status exchange."""


class ServiceNowSPMAdapter(IntegrationAdapter, Protocol):
    """Contract for demand, investment, portfolio, and governance exchange."""


class MicrosoftGraphAdapter(IntegrationAdapter, Protocol):
    """Contract for minimal email, calendar, and actionable approval links."""


class IntegrationRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, IntegrationAdapter] = {}
        self._ownership: dict[tuple[str, str], FieldOwnershipRule] = {}

    def register_adapter(self, adapter: IntegrationAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def register_ownership(self, rule: FieldOwnershipRule) -> None:
        key = (rule.entity_type, rule.field_name)
        if key in self._ownership and self._ownership[key] != rule:
            raise ValueError(f"Field ownership already defined for {key}")
        self._ownership[key] = rule

    def assert_write_allowed(self, entity_type: str, field_name: str, writer: str) -> None:
        rule = self._ownership.get((entity_type, field_name))
        if rule and writer not in rule.allowed_writers:
            raise PermissionError(
                f"{writer} cannot write {entity_type}.{field_name}; authority is "
                f"{rule.authoritative_system}"
            )

    def adapter(self, name: str) -> IntegrationAdapter:
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise KeyError(f"Integration adapter '{name}' is not configured") from exc

    def ownership_rules(self) -> list[FieldOwnershipRule]:
        return list(self._ownership.values())


registry = IntegrationRegistry()
for rule in (
    FieldOwnershipRule("Demand", "status", "DDC5I-PM", ("DDC5I-PM",)),
    FieldOwnershipRule("Project", "portfolio_id", "DDC5I-PM", ("DDC5I-PM",)),
    FieldOwnershipRule("Task", "percent_complete", "governance-required", ("DDC5I-PM", "ProjectOS")),
    FieldOwnershipRule("FinancialRecord", "actual_cost", "financial-system", ("financial-system",)),
    FieldOwnershipRule("User", "employment_status", "workforce-system", ("workforce-system",)),
):
    registry.register_ownership(rule)
