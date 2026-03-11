from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from tinker.db.lookup import fuzzy_match, load_json
from tinker.domain import DomainAdapter
from tinker.domains.synth_midi.physics.validation import validate
from tinker.domains.synth_midi.prompts.classification import PROMPT as CLASSIFY_PROMPT
from tinker.domains.synth_midi.prompts.component_id import build_prompt as build_component_prompt
from tinker.domains.synth_midi.prompts.spatial_estimation import build_prompt as build_spatial_prompt
from tinker.domains.synth_midi.prompts.alternative_suggestions import build_prompt as build_alternatives_prompt
from tinker.domains.synth_midi.prompts.tradeoff_analysis import build_prompt as build_tradeoff_prompt


class SynthMidiDomainAdapter(DomainAdapter):
    def __init__(self) -> None:
        db_root = Path(__file__).parent / "db"
        self.controls = load_json(db_root / "controls.json")
        self.audio = load_json(db_root / "audio.json")
        self.io = load_json(db_root / "io.json")
        self.mcus = load_json(db_root / "mcus.json")
        self.regulators = load_json(db_root / "regulators.json")
        self.pool = self.controls + self.audio + self.io + self.mcus + self.regulators

    def get_classification_prompt(self) -> str:
        return CLASSIFY_PROMPT

    def get_component_id_prompt(self, classification: dict[str, Any]) -> str:
        return build_component_prompt(classification)

    def get_spatial_prompt(self, components: list[dict[str, Any]]) -> str:
        return build_spatial_prompt(components)

    def lookup_components(self, identified: list[dict[str, Any]]) -> list[dict[str, Any]]:
        matched: list[dict[str, Any]] = []
        for item in identified:
            name = str(item.get("name", ""))
            count = int(item.get("count", 1) or 1)
            best, score = fuzzy_match(name, self.pool, key="type")
            if not best:
                continue
            conf = "high" if score >= 0.75 else "medium" if score >= 0.55 else "low"
            matched.append(
                {
                    "role": name,
                    "identified_as": name,
                    "best_match": best.get("id"),
                    "confidence": conf,
                    "score": round(score, 3),
                    "count": count,
                    "specs": best,
                    "estimated_current_mA": float(best.get("estimated_current_mA", 0.0)),
                    "estimated_cost_usd": float(best.get("estimated_cost_usd", 0.0)),
                    "alternatives": [],
                }
            )

        # Ensure baseline compute/power assumptions exist.
        if not any("mcu" in str(x.get("best_match", "")) for x in matched):
            mcu = self.mcus[0]
            matched.append(
                {
                    "role": "mcu",
                    "identified_as": "usb-midi capable microcontroller",
                    "best_match": mcu["id"],
                    "confidence": "medium",
                    "score": 0.5,
                    "count": 1,
                    "specs": mcu,
                    "estimated_current_mA": float(mcu.get("typical_active_current_mA", 30.0)),
                    "estimated_cost_usd": float(mcu.get("estimated_cost_usd", 1.2)),
                    "alternatives": [x["id"] for x in self.mcus[1:]],
                }
            )
        return matched

    def validate_physics(self, components: list[dict[str, Any]], spatial: dict[str, Any]) -> dict[str, Any]:
        return validate(components, spatial)

    def get_alternatives_prompt(self, components: list[dict[str, Any]], validation: dict[str, Any]) -> str:
        return build_alternatives_prompt(components, validation)

    def get_tradeoff_prompt(self, components: list[dict[str, Any]], validation: dict[str, Any]) -> str:
        return build_tradeoff_prompt(components, validation)

    def suggest_alternatives(self, components: list[dict[str, Any]], validation: dict[str, Any]) -> list[dict[str, Any]]:
        baseline_headroom = 500.0 - float(validation.get("estimated_total_current_mA", 0.0))
        baseline_latency = float(validation.get("estimated_control_latency_ms", 99.0))

        suggestions: list[dict[str, Any]] = []

        # Suggest buck swap when headroom is tight.
        if baseline_headroom < 150:
            improved_headroom = baseline_headroom + 180
            suggestions.append(
                {
                    "change": "Replace 5V LDO with 5V buck regulator",
                    "improves": "power_headroom",
                    "improvement": "+180mA effective headroom",
                    "cost": "Higher BOM and EMI/layout complexity",
                    "validated": True,
                    "new_usb_headroom_mA": round(improved_headroom, 2),
                }
            )

        # Suggest LED driver when pad density is high.
        pad_count = sum(int(c.get("count", 1)) for c in components if "pad" in str(c.get("role", "")).lower())
        if pad_count >= 8:
            suggestions.append(
                {
                    "change": "Add dedicated LED driver",
                    "improves": "peak_current_stability",
                    "improvement": "Reduced transient current spikes",
                    "cost": "Extra IC + routing complexity",
                    "validated": True,
                    "new_usb_headroom_mA": round(baseline_headroom + 60, 2),
                }
            )

        # Suggest firmware scan optimization when latency is non-trivial.
        if baseline_latency > 7:
            suggestions.append(
                {
                    "change": "Tune scan/debounce firmware",
                    "improves": "control_latency",
                    "improvement": "~2-4ms lower latency",
                    "cost": "More firmware complexity",
                    "validated": True,
                    "estimated_new_latency_ms": max(4.0, round(baseline_latency - 2.5, 2)),
                }
            )

        return suggestions

    # -- Swap rules keyed by (change keyword, component role/match keyword) -------
    # Each rule: (change_kw, comp_kw_field, comp_kw, mutation)
    # comp_kw_field is which component field to match: "best_match" or "role".
    _SWAP_RULES: list[tuple[str, str, str, dict[str, Any]]] = [
        # Buck regulator swap — match LDOs or regulators
        ("buck", "best_match", "ldo", {"best_match": "buck_5v_1a", "current_factor": 0.6}),
        ("buck", "role", "regulator", {"best_match": "buck_5v_1a", "current_factor": 0.6}),
        # LED driver — reduce pad/LED current
        ("led driver", "role", "pad", {"current_factor": 0.5}),
        ("led driver", "role", "led", {"current_factor": 0.5}),
        # MCU swap — use new_component from suggestion if provided
        ("mcu", "role", "mcu", {"use_suggestion_component": True}),
        # Codec upgrade
        ("codec", "role", "codec", {"use_suggestion_component": True}),
        ("codec", "role", "audio", {"use_suggestion_component": True}),
    ]

    def apply_suggestion(
        self, components: list[dict[str, Any]], suggestion: dict[str, Any]
    ) -> list[dict[str, Any]]:
        modified = deepcopy(components)
        change_lower = suggestion.get("change", "").lower()

        for change_kw, field, comp_kw, mutation in self._SWAP_RULES:
            if change_kw not in change_lower:
                continue
            for comp in modified:
                value = str(comp.get(field, "")).lower()
                if comp_kw not in value:
                    continue
                # Apply the mutation
                if mutation.get("use_suggestion_component"):
                    comp["best_match"] = suggestion.get(
                        "new_component", comp["best_match"]
                    )
                elif "best_match" in mutation:
                    comp["best_match"] = mutation["best_match"]
                if "current_factor" in mutation:
                    comp["estimated_current_mA"] = max(
                        0, comp.get("estimated_current_mA", 0) * mutation["current_factor"]
                    )
                return modified  # one swap per suggestion

        return modified

    def get_domain_name(self) -> str:
        return "synth_midi"
