"""Background-job abstraction for local inline execution and future queue workers."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class JobStatus(str, Enum):
    QUEUED = "Queued"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"


@dataclass
class JobRecord:
    id: str
    name: str
    status: JobStatus
    payload: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class InlineJobRunner:
    """Development runner. Replace through this interface with a durable queue."""

    def __init__(self) -> None:
        self.records: dict[str, JobRecord] = {}

    def submit(self, name: str, fn: Callable[..., dict[str, Any]], **payload: Any) -> JobRecord:
        record = JobRecord(id=str(uuid.uuid4()), name=name, status=JobStatus.QUEUED, payload=payload)
        self.records[record.id] = record
        record.status = JobStatus.RUNNING
        record.started_at = datetime.now(timezone.utc)
        try:
            record.result = fn(**payload)
            record.status = JobStatus.SUCCEEDED
        except Exception as exc:  # runner must preserve failure evidence
            record.status = JobStatus.FAILED
            record.error = str(exc)
        finally:
            record.completed_at = datetime.now(timezone.utc)
        return record


job_runner = InlineJobRunner()
