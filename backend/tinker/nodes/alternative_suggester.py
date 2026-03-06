from __future__ import annotations

from copy import deepcopy
from typing import Any

from tinker.domain import DomainAdapter


def _apply_suggestion(components: list[dict[str, Any]], suggestion: dict[str, Any]) -> list[dict[str, Any]]:
    """Apply a suggested component swap to a copy of the component list.

    Uses a simple heuristic: if the suggestion mentions a component role or
    match id, substitute or adjust it. Falls back to returning the original
    list unchanged so we can still compare before/after physics.
    """
    modified = deepcopy(components)
    change_lower = suggestion.get("change", "").lower()

    for comp in modified:
        role = str(comp.get("role", "")).lower()
        best = str(comp.get("best_match", "")).lower()

        # Buck regulator swap
        if "buck" in change_lower and ("ldo" in best or "regulator" in role):
            comp["best_match"] = "buck_5v_1a"
            comp["estimated_current_mA"] = max(0, comp.get("estimated_current_mA", 0) * 0.6)
            break

        # LED driver addition — reduce pad/LED current draw
        if "led driver" in change_lower and ("pad" in role or "led" in role):
            comp["estimated_current_mA"] = max(0, comp.get("estimated_current_mA", 0) * 0.5)
            break

        # MCU swap
        if "mcu" in change_lower and "mcu" in role:
            comp["best_match"] = suggestion.get("new_component", comp["best_match"])
            break

        # Codec upgrade
        if "codec" in change_lower and ("codec" in role or "audio" in role):
            comp["best_match"] = suggestion.get("new_component", comp["best_match"])
            break

    return modified


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
        modified_components = _apply_suggestion(components, suggestion)

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
