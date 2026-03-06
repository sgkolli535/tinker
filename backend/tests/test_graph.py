from tinker.domains.synth_midi.adapter import SynthMidiDomainAdapter
from tinker.graph import run_pipeline
from tinker.llm import HeuristicLLMClient


def test_pipeline_end_to_end() -> None:
    state = {
        "images": [],
        "user_context": None,
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
        "current_node": "",
        "retry_count": 0,
    }
    result = run_pipeline(state, SynthMidiDomainAdapter(), HeuristicLLMClient())
    assert result["final_report"]
    assert result["system_classification"]
    assert isinstance(result["suggestions"], list)
    # Suggestions should be physics-validated
    for s in result["suggestions"]:
        assert s.get("validated") is True
        assert "new_estimated_total_current_mA" in s
        assert "new_usb_headroom_mA" in s
