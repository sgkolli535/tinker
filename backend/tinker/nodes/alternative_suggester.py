from __future__ import annotations

from typing import Any

from tinker.domain import DomainAdapter


def alternative_suggester_node(state: dict[str, Any], adapter: DomainAdapter, llm: Any) -> dict[str, Any]:
    components = state.get("matched_components", [])
    validation = state.get("physics_validation", {})
    spatial = state.get("spatial_estimates", {})

    # Baseline metrics for comparison
    baseline_current = float(validation.get("estimated_total_current_mA", 0))
    baseline_latency = float(validation.get("estimated_control_latency_ms", 99))
    baseline_headroom_dbu = float(validation.get("estimated_line_out_headroom_dBu", 0))
    baseline_usb_headroom = 500.0 - baseline_current

    # 1. LLM proposes modifications
    prompt = adapter.get_alternatives_prompt(components, validation)
    payload = llm.generate_json(prompt)
    llm_suggestions = payload.get("suggestions", [])

    # 2. Deterministic domain-level suggestions
    domain_suggestions = adapter.suggest_alternatives(components, validation)

    # 3. Re-validate each suggestion through the physics engine
    all_candidates = domain_suggestions + llm_suggestions
    validated: list[dict[str, Any]] = []
    seen_changes: set[str] = set()

    for suggestion in all_candidates:
        change = suggestion.get("change", "")
        if change in seen_changes:
            continue
        seen_changes.add(change)

        # Apply the suggested modification to a copy of the components
        modified_components = adapter.apply_suggestion(components, suggestion)

        # Re-run physics validation with the modified components
        new_validation = adapter.validate_physics(modified_components, spatial)

        new_current = float(new_validation.get("estimated_total_current_mA", 0))
        new_latency = float(new_validation.get("estimated_control_latency_ms", 99))
        new_headroom_dbu = float(new_validation.get("estimated_line_out_headroom_dBu", 0))
        new_usb_headroom = 500.0 - new_current

        # Check if the suggestion actually improves something
        improved = (
            new_current < baseline_current
            or new_usb_headroom > baseline_usb_headroom + 10
            or new_latency < baseline_latency - 0.5
            or new_headroom_dbu > baseline_headroom_dbu + 0.5
        )

        suggestion_out = {
            "change": change,
            "improves": suggestion.get("improves", ""),
            "improvement": suggestion.get("improvement", ""),
            "cost": suggestion.get("cost", ""),
            "validated": improved,
            "new_estimated_total_current_mA": round(new_current, 2),
            "new_usb_headroom_mA": round(new_usb_headroom, 2),
        }

        # Only surface validated improvements (per spec)
        if improved:
            validated.append(suggestion_out)

    return {
        "current_node": "alternative_suggester",
        "suggestions": validated,
    }
