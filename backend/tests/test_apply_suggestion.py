"""Tests for domain adapter apply_suggestion and the alternative suggester node."""

from tinker.domains.synth_midi.adapter import SynthMidiDomainAdapter


def _make_component(role: str, best_match: str, current: float = 10.0, count: int = 1) -> dict:
    return {
        "role": role,
        "best_match": best_match,
        "estimated_current_mA": current,
        "count": count,
    }


adapter = SynthMidiDomainAdapter()


def test_buck_swap_replaces_ldo():
    components = [
        _make_component("regulator", "ldo_3v3", current=20),
        _make_component("mcu", "rp2040", current=30),
    ]
    result = adapter.apply_suggestion(components, {"change": "Replace LDO with buck converter"})
    reg = next(c for c in result if c["role"] == "regulator")
    assert reg["best_match"] == "buck_5v_1a"
    assert reg["estimated_current_mA"] == 12.0  # 20 * 0.6


def test_led_driver_reduces_pad_current():
    components = [
        _make_component("pads", "pads_rgb_matrix", current=80),
        _make_component("mcu", "rp2040", current=30),
    ]
    result = adapter.apply_suggestion(components, {"change": "Add dedicated LED driver"})
    pad = next(c for c in result if c["role"] == "pads")
    assert pad["estimated_current_mA"] == 40.0  # 80 * 0.5


def test_mcu_swap_uses_new_component():
    components = [
        _make_component("mcu", "stm32f4", current=50),
    ]
    result = adapter.apply_suggestion(components, {"change": "Switch MCU", "new_component": "rp2040"})
    mcu = result[0]
    assert mcu["best_match"] == "rp2040"


def test_codec_swap_uses_new_component():
    components = [
        _make_component("audio codec", "pcm5102", current=15),
    ]
    result = adapter.apply_suggestion(components, {"change": "Upgrade codec", "new_component": "cs4272"})
    assert result[0]["best_match"] == "cs4272"


def test_unmatched_suggestion_returns_unchanged_copy():
    components = [_make_component("mcu", "rp2040", current=30)]
    result = adapter.apply_suggestion(components, {"change": "Add thermal paste"})
    assert result == components
    # Verify it's a copy, not the same object
    assert result is not components
    assert result[0] is not components[0]


def test_apply_suggestion_does_not_mutate_original():
    components = [_make_component("regulator", "ldo_3v3", current=20)]
    original_current = components[0]["estimated_current_mA"]
    adapter.apply_suggestion(components, {"change": "Replace LDO with buck converter"})
    assert components[0]["estimated_current_mA"] == original_current
    assert components[0]["best_match"] == "ldo_3v3"
