from __future__ import annotations

from typing import Any

from tinker.domain import DomainAdapter


def _render_tradeoffs(items: list[dict[str, Any]]) -> str:
    if not items:
        return "- No trade-off analysis available."
    return "\n".join(
        f"- **{x.get('choice', 'Unknown choice')}**: optimized {x.get('optimized', 'n/a')}; "
        f"sacrificed {x.get('sacrificed', 'n/a')}. {x.get('verdict', '')}" for x in items
    )


def _render_suggestions(items: list[dict[str, Any]]) -> str:
    if not items:
        return "- No validated alternatives found."
    rows = []
    for x in items:
        rows.append(
            f"- **{x.get('change', 'Change')}** -> improves {x.get('improves', 'n/a')} "
            f"by {x.get('improvement', 'n/a')} (cost: {x.get('cost', 'n/a')})"
        )
    return "\n".join(rows)


def report_generator_node(state: dict[str, Any], adapter: DomainAdapter) -> dict[str, Any]:
    classification = state.get("system_classification", {})
    validation = state.get("physics_validation", {})

    report = f"""# tinker Engineering Teardown

## 1. System Overview
- Domain: `{adapter.get_domain_name()}`
- Category: `{classification.get('category', 'unknown')}`
- Form factor: `{classification.get('form_factor', 'unknown')}`
- Power input: `{classification.get('power_input', 'unknown')}`
- Apparently optimized for: `{classification.get('apparent_use_case', 'unknown')}`

## 2. Component BOM (Estimated)
- Matched components: {len(state.get('matched_components', []))}
- Estimated total current: {state.get('power_estimate_mA', 0.0)} mA
- Estimated total cost: ${state.get('cost_estimate_usd', 0.0)}

## 3. Physics Validation Summary
- System valid: `{validation.get('system_valid', False)}`
- Control latency: `{validation.get('estimated_control_latency_ms', 'n/a')} ms`
- Line out headroom: `{validation.get('estimated_line_out_headroom_dBu', 'n/a')} dBu`
- Bottlenecks: `{len(validation.get('bottlenecks', []))}`

## 4. Design Trade-offs
{_render_tradeoffs(state.get('tradeoff_analysis', []))}

## 5. Alternative Configurations
{_render_suggestions(state.get('suggestions', []))}
"""

    return {"current_node": "report_generator", "final_report": report}
