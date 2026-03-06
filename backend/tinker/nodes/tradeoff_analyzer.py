from __future__ import annotations

from typing import Any

from tinker.domain import DomainAdapter


def tradeoff_analyzer_node(state: dict[str, Any], adapter: DomainAdapter, llm: Any) -> dict[str, Any]:
    prompt = adapter.get_tradeoff_prompt(state.get("matched_components", []), state.get("physics_validation", {}))
    payload = llm.generate_json(prompt)
    return {
        "current_node": "tradeoff_analyzer",
        "tradeoff_analysis": payload.get("tradeoffs", []),
    }
