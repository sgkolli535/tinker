def check_usb_budget(total_current_mA: float, usb_budget_mA: float = 500.0) -> dict:
    headroom = usb_budget_mA - total_current_mA
    severity = "pass"
    if headroom < 0:
        severity = "fail"
    elif headroom < 100:
        severity = "warn"
    return {
        "name": "Power budget",
        "value": f"{total_current_mA:.0f}mA / {usb_budget_mA:.0f}mA",
        "status": severity,
        "headroom_mA": round(headroom, 2),
        "note": "Low headroom for LED peaks" if severity == "warn" else "Within conservative USB budget",
    }
