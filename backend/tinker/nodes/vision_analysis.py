from __future__ import annotations

from typing import Any

from tinker.domain import DomainAdapter


def vision_analysis_node(state: dict[str, Any], adapter: DomainAdapter, llm: Any) -> dict[str, Any]:
    classification = llm.generate_json(adapter.get_classification_prompt(), images=state.get("images", []))

    identified = llm.generate_json(
        adapter.get_component_id_prompt(classification),
        images=state.get("images", []),
    )

    components = identified.get("components", []) if isinstance(identified, dict) else []
    spatial = llm.generate_json(adapter.get_spatial_prompt(components), images=state.get("images", []))

    return {
        "current_node": "vision_analysis",
        "system_classification": classification,
        "identified_components": components,
        "spatial_estimates": spatial,
    }
