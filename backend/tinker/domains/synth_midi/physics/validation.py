from __future__ import annotations

from typing import Any

from tinker.domains.synth_midi.physics.audio import estimate_line_out_headroom_dbu
from tinker.domains.synth_midi.physics.latency import estimate_control_latency_ms
from tinker.domains.synth_midi.physics.power import check_usb_budget


def validate(matched_components: list[dict[str, Any]], spatial: dict[str, Any]) -> dict[str, Any]:
    total_current_mA = sum(float(c.get("estimated_current_mA", 0.0)) * max(1, int(c.get("count", 1))) for c in matched_components)
    num_controls = sum(
        int(c.get("count", 1))
        for c in matched_components
        if str(c.get("role", "")).lower() in {"rotary encoder", "fader", "pads", "buttons", "potentiometer"}
    )

    power_check = check_usb_budget(total_current_mA)
    latency_ms = estimate_control_latency_ms(num_controls=max(num_controls, 12))
    audio_headroom = estimate_line_out_headroom_dbu()

    # Determine MIDI IN isolation status from matched components.
    has_din_midi = any(
        "din" in str(c.get("best_match", "")).lower() or "midi" in str(c.get("best_match", "")).lower()
        for c in matched_components
        if str(c.get("role", "")).lower() not in {"mcu", "usb", "usb-c"}
    )
    has_optocoupler = any(
        "opto" in str(c.get("best_match", "")).lower()
        or "opto" in str(c.get("role", "")).lower()
        or "opto" in str(c.get("identified_as", "")).lower()
        for c in matched_components
    )

    if not has_din_midi:
        midi_check = {
            "name": "MIDI IN isolation",
            "value": "N/A",
            "status": "pass",
            "note": "No DIN MIDI port detected; USB-only device",
        }
    elif has_optocoupler:
        midi_check = {
            "name": "MIDI IN isolation",
            "value": "Confirmed",
            "status": "pass",
            "note": "Optocoupler detected for MIDI IN galvanic isolation",
        }
    else:
        midi_check = {
            "name": "MIDI IN isolation",
            "value": "Missing",
            "status": "warn",
            "note": "DIN MIDI port detected but no optocoupler confirmed from photos",
        }

    checks = [
        power_check,
        {
            "name": "Control latency",
            "value": f"{latency_ms}ms",
            "status": "pass" if latency_ms <= 15 else "warn",
            "note": "Good for performance" if latency_ms <= 15 else "May feel sluggish for live control",
        },
        {
            "name": "Line out headroom",
            "value": f"+{audio_headroom} dBu",
            "status": "pass" if audio_headroom >= 10 else "warn",
            "note": "Meets pro-ish target" if audio_headroom >= 10 else "Limited headroom on low rails",
        },
        midi_check,
    ]

    bottlenecks = []
    for check in checks:
        if check["status"] in {"warn", "fail"}:
            bottlenecks.append(
                {
                    "type": check["name"].lower().replace(" ", "_"),
                    "detail": check["note"],
                    "severity": "warning" if check["status"] == "warn" else "error",
                }
            )

    has_fail = any(c["status"] == "fail" for c in checks)
    has_warn = any(c["status"] == "warn" for c in checks)
    route = "valid"
    if has_fail:
        route = "invalid_fixable"

    return {
        "system_valid": not has_fail,
        "estimated_total_current_mA": round(total_current_mA, 2),
        "estimated_control_latency_ms": latency_ms,
        "estimated_line_out_headroom_dBu": audio_headroom,
        "checks": checks,
        "bottlenecks": bottlenecks,
        "physics_consistency": {
            "power_budget": "ok" if power_check["status"] == "pass" else "warning",
            "control_latency": "good" if latency_ms <= 15 else "warning",
            "audio_headroom": "ok" if audio_headroom >= 10 else "warning",
            "midi_io": "likely_ok" if not has_warn else "review",
        },
        "route": route if has_fail else ("valid" if not has_warn else "valid"),
    }
