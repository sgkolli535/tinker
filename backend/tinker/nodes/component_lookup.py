from __future__ import annotations

from typing import Any

from tinker.domain import DomainAdapter


def component_lookup_node(state: dict[str, Any], adapter: DomainAdapter) -> dict[str, Any]:
    matched = adapter.lookup_components(state.get("identified_components", []))
    total_mA = sum(float(x.get("estimated_current_mA", 0.0)) for x in matched)
    total_cost = sum(float(x.get("estimated_cost_usd", 0.0)) for x in matched)
    return {
        "current_node": "component_lookup",
        "matched_components": matched,
        "power_estimate_mA": round(total_mA, 2),
        "cost_estimate_usd": round(total_cost, 2),
    }
