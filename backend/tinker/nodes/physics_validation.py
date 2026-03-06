from __future__ import annotations

from typing import Any

from tinker.domain import DomainAdapter


def physics_validation_node(state: dict[str, Any], adapter: DomainAdapter) -> dict[str, Any]:
    validation = adapter.validate_physics(state.get("matched_components", []), state.get("spatial_estimates", {}))
    return {
        "current_node": "physics_validation",
        "physics_validation": validation,
        "system_valid": bool(validation.get("system_valid", False)),
        "bottlenecks": validation.get("bottlenecks", []),
    }
