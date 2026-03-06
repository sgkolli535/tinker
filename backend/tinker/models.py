from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class RunStatus(BaseModel):
    run_id: str
    status: Literal["queued", "running", "completed", "failed"]
    current_node: Optional[str] = None
    retry_count: int = 0
    created_at: str
    updated_at: str


class RunSnapshot(BaseModel):
    status: RunStatus
    state: dict[str, Any] = Field(default_factory=dict)
    trace: list[dict[str, Any]] = Field(default_factory=list)


class CreateRunResponse(BaseModel):
    run_id: str
    status: Literal["queued", "running"]


class CreateRunRequest(BaseModel):
    user_context: Optional[str] = None


class TraceEvent(BaseModel):
    ts: str
    node: str
    status: Literal["started", "completed", "failed"]
    payload: dict[str, Any] = Field(default_factory=dict)


class ReportResponse(BaseModel):
    run_id: str
    report_markdown: str


class ErrorResponse(BaseModel):
    detail: str


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def new_run_id() -> str:
    return f"run_{uuid4().hex[:10]}"
