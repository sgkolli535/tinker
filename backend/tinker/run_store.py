from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any, Protocol

from tinker.models import RunSnapshot, RunStatus, TraceEvent, now_iso


class RunStore(Protocol):
    async def create(self, run_id: str) -> None:
        ...

    async def get(self, run_id: str) -> RunSnapshot | None:
        ...

    async def set_status(self, run_id: str, status: str, current_node: str | None = None) -> None:
        ...

    async def set_retry_count(self, run_id: str, retry_count: int) -> None:
        ...

    async def merge_state(self, run_id: str, state_updates: dict[str, Any]) -> None:
        ...

    async def append_trace(self, run_id: str, event: TraceEvent) -> None:
        ...


class InMemoryRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunSnapshot] = {}
        self._lock = asyncio.Lock()

    async def create(self, run_id: str) -> None:
        async with self._lock:
            now = now_iso()
            self._runs[run_id] = RunSnapshot(
                status=RunStatus(
                    run_id=run_id,
                    status="queued",
                    current_node=None,
                    retry_count=0,
                    created_at=now,
                    updated_at=now,
                ),
                state={},
                trace=[],
            )

    async def get(self, run_id: str) -> RunSnapshot | None:
        async with self._lock:
            snap = self._runs.get(run_id)
            return deepcopy(snap) if snap else None

    async def set_status(self, run_id: str, status: str, current_node: str | None = None) -> None:
        async with self._lock:
            run = self._runs[run_id]
            run.status.status = status
            run.status.current_node = current_node
            run.status.updated_at = now_iso()

    async def set_retry_count(self, run_id: str, retry_count: int) -> None:
        async with self._lock:
            run = self._runs[run_id]
            run.status.retry_count = retry_count
            run.status.updated_at = now_iso()

    async def merge_state(self, run_id: str, state_updates: dict[str, Any]) -> None:
        async with self._lock:
            run = self._runs[run_id]
            run.state.update(state_updates)
            run.status.updated_at = now_iso()

    async def append_trace(self, run_id: str, event: TraceEvent) -> None:
        async with self._lock:
            run = self._runs[run_id]
            run.trace.append(event.model_dump())
            run.status.updated_at = now_iso()
