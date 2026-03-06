from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

from supabase import Client, create_client

from tinker.models import RunSnapshot, RunStatus, TraceEvent, now_iso


class SupabaseRunStore:
    """Supabase-backed run store for persistent run state and trace history."""

    def __init__(self, supabase_url: str, supabase_service_key: str, table_name: str = "tinker_runs") -> None:
        self._client: Client = create_client(supabase_url, supabase_service_key)
        self._table = table_name
        self._lock = asyncio.Lock()

    async def create(self, run_id: str) -> None:
        now = now_iso()
        payload = {
            "run_id": run_id,
            "status": "queued",
            "current_node": None,
            "retry_count": 0,
            "created_at": now,
            "updated_at": now,
            "state": {},
            "trace": [],
        }
        await asyncio.to_thread(self._upsert, payload)

    async def get(self, run_id: str) -> RunSnapshot | None:
        row = await asyncio.to_thread(self._select_one, run_id)
        if not row:
            return None
        return self._to_snapshot(row)

    async def set_status(self, run_id: str, status: str, current_node: str | None = None) -> None:
        await asyncio.to_thread(
            self._update,
            run_id,
            {"status": status, "current_node": current_node, "updated_at": now_iso()},
        )

    async def set_retry_count(self, run_id: str, retry_count: int) -> None:
        await asyncio.to_thread(
            self._update,
            run_id,
            {"retry_count": retry_count, "updated_at": now_iso()},
        )

    async def merge_state(self, run_id: str, state_updates: dict[str, Any]) -> None:
        async with self._lock:
            row = await asyncio.to_thread(self._select_one, run_id)
            if not row:
                return
            state = deepcopy(row.get("state") or {})
            state.update(state_updates)
            await asyncio.to_thread(
                self._update,
                run_id,
                {"state": state, "updated_at": now_iso()},
            )

    async def append_trace(self, run_id: str, event: TraceEvent) -> None:
        async with self._lock:
            row = await asyncio.to_thread(self._select_one, run_id)
            if not row:
                return
            trace = list(row.get("trace") or [])
            trace.append(event.model_dump())
            await asyncio.to_thread(
                self._update,
                run_id,
                {"trace": trace, "updated_at": now_iso()},
            )

    def _upsert(self, payload: dict[str, Any]) -> None:
        self._client.table(self._table).upsert(payload, on_conflict="run_id").execute()

    def _update(self, run_id: str, payload: dict[str, Any]) -> None:
        self._client.table(self._table).update(payload).eq("run_id", run_id).execute()

    def _select_one(self, run_id: str) -> dict[str, Any] | None:
        res = self._client.table(self._table).select("*").eq("run_id", run_id).limit(1).execute()
        rows = res.data or []
        return rows[0] if rows else None

    def _to_snapshot(self, row: dict[str, Any]) -> RunSnapshot:
        return RunSnapshot(
            status=RunStatus(
                run_id=row["run_id"],
                status=row.get("status", "queued"),
                current_node=row.get("current_node"),
                retry_count=int(row.get("retry_count", 0)),
                created_at=row.get("created_at", now_iso()),
                updated_at=row.get("updated_at", now_iso()),
            ),
            state=row.get("state") or {},
            trace=row.get("trace") or [],
        )
