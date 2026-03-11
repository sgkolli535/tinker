"""Tests for physics validation — especially the MIDI isolation check branches."""

from tinker.domains.synth_midi.physics.validation import validate


def _make_component(role: str, best_match: str, current: float = 5.0, count: int = 1, identified_as: str = "") -> dict:
    return {
        "role": role,
        "best_match": best_match,
        "estimated_current_mA": current,
        "count": count,
        "identified_as": identified_as or role,
    }


def test_midi_isolation_pass_when_no_din_midi():
    """USB-only device — no DIN MIDI port means isolation check is N/A."""
    components = [
        _make_component("mcu", "rp2040", current=30),
        _make_component("usb-c", "usb_c_device_port", current=0),
    ]
    result = validate(components, {})
    midi_check = next(c for c in result["checks"] if c["name"] == "MIDI IN isolation")
    assert midi_check["status"] == "pass"
    assert midi_check["value"] == "N/A"


def test_midi_isolation_pass_when_optocoupler_present():
    """DIN MIDI port with optocoupler confirmed should pass."""
    components = [
        _make_component("mcu", "rp2040", current=30),
        _make_component("midi_port", "din5_midi_in_out", current=5),
        _make_component("optocoupler", "6n138_optocoupler", current=2),
    ]
    result = validate(components, {})
    midi_check = next(c for c in result["checks"] if c["name"] == "MIDI IN isolation")
    assert midi_check["status"] == "pass"
    assert midi_check["value"] == "Confirmed"


def test_midi_isolation_warn_when_din_midi_without_optocoupler():
    """DIN MIDI port without optocoupler should warn."""
    components = [
        _make_component("mcu", "rp2040", current=30),
        _make_component("midi_port", "din5_midi_in_out", current=5),
    ]
    result = validate(components, {})
    midi_check = next(c for c in result["checks"] if c["name"] == "MIDI IN isolation")
    assert midi_check["status"] == "warn"
    assert midi_check["value"] == "Missing"


def test_midi_isolation_detects_opto_in_identified_as():
    """Optocoupler mentioned in identified_as field should be detected."""
    components = [
        _make_component("mcu", "rp2040", current=30),
        _make_component("midi_port", "din5_midi_in_out", current=5),
        _make_component("isolator", "6n137", current=2, identified_as="optocoupler for MIDI input"),
    ]
    result = validate(components, {})
    midi_check = next(c for c in result["checks"] if c["name"] == "MIDI IN isolation")
    assert midi_check["status"] == "pass"


def test_validation_system_valid_when_no_fails():
    """System should be valid when all checks pass or warn (no fails)."""
    components = [
        _make_component("mcu", "rp2040", current=30),
        _make_component("rotary encoder", "encoder_24det_push", current=1, count=4),
    ]
    result = validate(components, {})
    assert result["system_valid"] is True
    assert result["route"] == "valid"


def test_validation_invalid_when_over_power_budget():
    """Exceeding 500mA USB budget should fail."""
    components = [
        _make_component("mcu", "rp2040", current=300),
        _make_component("pads", "pads_rgb_matrix", current=250, count=1),
    ]
    result = validate(components, {})
    assert result["system_valid"] is False
    assert result["route"] == "invalid_fixable"
    assert any(b["type"] == "power_budget" for b in result["bottlenecks"])
