from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from tinker.domain import DomainAdapter
from tinker.domains.synth_midi.adapter import SynthMidiDomainAdapter
from tinker.graph import run_pipeline
from tinker.llm import AnthropicJSONClient, HeuristicLLMClient
from tinker.models import CreateRunResponse, ReportResponse, TraceEvent, new_run_id, now_iso
from tinker.run_store import InMemoryRunStore, RunStore
from tinker.supabase_run_store import SupabaseRunStore

app = FastAPI(title="tinker backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_run_store() -> RunStore:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase_table = os.getenv("SUPABASE_TINKER_RUNS_TABLE", "tinker_runs")

    if supabase_url and supabase_service_key:
        return SupabaseRunStore(
            supabase_url=supabase_url,
            supabase_service_key=supabase_service_key,
            table_name=supabase_table,
        )
    return InMemoryRunStore()


store: RunStore = get_run_store()
upload_root = Path("./.runs/uploads")
upload_root.mkdir(parents=True, exist_ok=True)


DOMAIN_ADAPTERS: dict[str, type[DomainAdapter]] = {
    "synth_midi": SynthMidiDomainAdapter,
}


def get_adapter(domain: str) -> DomainAdapter:
    cls = DOMAIN_ADAPTERS.get(domain)
    if cls is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown domain '{domain}'. Available: {', '.join(sorted(DOMAIN_ADAPTERS))}",
        )
    return cls()


def get_llm_client() -> Any:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        return AnthropicJSONClient(api_key=api_key, model=model)
    return HeuristicLLMClient()


async def _persist_files(run_id: str, files: list[UploadFile]) -> list[str]:
    run_dir = upload_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    for idx, file in enumerate(files):
        ext = Path(file.filename or "image.jpg").suffix or ".jpg"
        target = run_dir / f"img_{idx}{ext}"
        data = await file.read()
        target.write_bytes(data)
        paths.append(str(target))
    return paths


async def _execute_run(run_id: str, images: list[str], user_context: str | None, domain: str = "synth_midi") -> None:
    adapter = get_adapter(domain)
    llm = get_llm_client()
    loop = asyncio.get_running_loop()

    base_state: dict[str, Any] = {
        "images": images,
        "user_context": user_context,
        "system_classification": {},
        "identified_components": [],
        "spatial_estimates": {},
        "matched_components": [],
        "power_estimate_mA": 0.0,
        "cost_estimate_usd": 0.0,
        "physics_validation": {},
        "system_valid": False,
        "bottlenecks": [],
        "tradeoff_analysis": [],
        "suggestions": [],
        "final_report": "",
        "errors": [],
        "current_node": "vision_analysis",
        "retry_count": 0,
    }

    try:
        await store.set_status(run_id, "running", "vision_analysis")
        await store.append_trace(
            run_id,
            TraceEvent(ts=now_iso(), node="run", status="started", payload={"domain": adapter.get_domain_name()}),
        )

        def on_graph_event(node: str, status: str, payload: dict[str, Any]) -> None:
            async def persist() -> None:
                if status == "started":
                    await store.set_status(run_id, "running", node)
                else:
                    await store.merge_state(run_id, payload)
                    await store.set_status(run_id, "running", node)
                await store.append_trace(
                    run_id,
                    TraceEvent(ts=now_iso(), node=node, status=status, payload=payload if status == "failed" else {}),
                )

            asyncio.run_coroutine_threadsafe(persist(), loop)

        result = await asyncio.to_thread(run_pipeline, base_state, adapter, llm, on_graph_event)
        await store.merge_state(run_id, result)
        await store.set_retry_count(run_id, int(result.get("retry_count", 0)))
        await store.append_trace(
            run_id,
            TraceEvent(ts=now_iso(), node="run", status="completed", payload={"system_valid": result.get("system_valid", False)}),
        )
        await store.set_status(run_id, "completed", result.get("current_node"))
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        await store.append_trace(
            run_id,
            TraceEvent(ts=now_iso(), node="run", status="failed", payload={"error": str(exc)}),
        )
        await store.merge_state(run_id, {"errors": [str(exc)]})
        await store.set_status(run_id, "failed", None)


@app.post("/api/v1/runs", response_model=CreateRunResponse)
async def create_run(
    images: list[UploadFile] = File(...),
    user_context: str | None = Form(default=None),
    domain: str = Form(default="synth_midi"),
) -> CreateRunResponse:
    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")

    # Validate domain early so the caller gets a 400, not a silent background failure.
    get_adapter(domain)

    run_id = new_run_id()
    await store.create(run_id)
    paths = await _persist_files(run_id, images)
    asyncio.create_task(_execute_run(run_id=run_id, images=paths, user_context=user_context, domain=domain))
    return CreateRunResponse(run_id=run_id, status="queued")


@app.get("/api/v1/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    snap = await store.get(run_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Run not found")
    return snap.model_dump()


@app.get("/api/v1/runs/{run_id}/trace")
async def get_run_trace(run_id: str) -> list[dict[str, Any]]:
    snap = await store.get(run_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Run not found")
    return snap.trace


@app.get("/api/v1/runs/{run_id}/report", response_model=ReportResponse)
async def get_run_report(run_id: str) -> ReportResponse:
    snap = await store.get(run_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Run not found")
    report = str(snap.state.get("final_report") or "")
    if not report:
        raise HTTPException(status_code=409, detail="Report not ready")
    return ReportResponse(run_id=run_id, report_markdown=report)


@app.get("/api/v1/runs/{run_id}/report.md", response_class=PlainTextResponse)
async def get_run_report_md(run_id: str) -> str:
    snap = await store.get(run_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Run not found")
    report = str(snap.state.get("final_report") or "")
    if not report:
        raise HTTPException(status_code=409, detail="Report not ready")
    return report
