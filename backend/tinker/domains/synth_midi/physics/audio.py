import math


def estimate_line_out_headroom_dbu(rail_v: float = 5.0, headroom_margin_v: float = 1.2) -> float:
    max_peak_v = max(0.0, rail_v - headroom_margin_v)
    max_rms_v = max_peak_v / (2 ** 0.5)
    if max_rms_v <= 0:
        return -999.0
    return round(20 * math.log10(max_rms_v / 0.775), 2)
