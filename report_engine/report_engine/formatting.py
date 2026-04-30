from __future__ import annotations

import math


def format_metric_value(value, unit: str) -> str:
    if value == "" or value is None:
        return ""
    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)
    if math.isnan(num):
        return ""
    if unit == "USD":
        return f"${num:,.2f}"
    if unit == "%":
        return f"{num:g}%"
    if num == int(num):
        return f"{int(num):,}"
    return f"{num:,}"
