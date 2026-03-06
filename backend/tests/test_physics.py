from tinker.domains.synth_midi.physics.latency import estimate_control_latency_ms
from tinker.domains.synth_midi.physics.power import check_usb_budget


def test_usb_budget_warn_threshold() -> None:
    result = check_usb_budget(total_current_mA=450)
    assert result["status"] == "warn"
    assert result["headroom_mA"] == 50


def test_latency_estimation() -> None:
    latency = estimate_control_latency_ms(num_controls=20, scan_rate_Hz=200, debounce_ms=4.5)
    assert 9 <= latency <= 11
