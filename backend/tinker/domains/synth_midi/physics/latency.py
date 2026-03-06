def estimate_control_latency_ms(num_controls: int, scan_rate_Hz: float = 200.0, debounce_ms: float = 4.5) -> float:
    if scan_rate_Hz <= 0:
        return 999.0
    worst_scan = (1.0 / scan_rate_Hz) * 1000.0
    # Add slight scaling with control count for matrix complexity.
    scaling = max(0.0, (num_controls - 16) * 0.03)
    return round(worst_scan + debounce_ms + scaling, 2)
