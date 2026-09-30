"""Parametric insurance/liquidity scenario calculator.

This is a transparent scenario model, not an insurance contract, quote, or underwriting decision.
"""
from __future__ import annotations


def calculate_parametric_liquidity(wind_speed, rainfall, surge_height_m, infrastructure, vulnerability):
    exposed_value = (
        infrastructure.get("summary", {}).get("hospitals", 0) * 2_000_000
        + infrastructure.get("summary", {}).get("power_substations", 0) * 1_500_000
        + infrastructure.get("summary", {}).get("major_roads", 0) * 750_000
        + infrastructure.get("summary", {}).get("schools", 0) * 500_000
    )
    trigger_wind = 120.0
    trigger_rain = 200.0
    trigger_surge = 2.5
    wind_ratio = min(max((wind_speed - trigger_wind) / 80.0, 0), 1)
    rain_ratio = min(max((rainfall - trigger_rain) / 300.0, 0), 1)
    surge_ratio = min(max((surge_height_m - trigger_surge) / 4.5, 0), 1)
    trigger_components = {"wind": wind_speed >= trigger_wind, "rainfall": rainfall >= trigger_rain, "surge": surge_height_m >= trigger_surge}
    triggered = any(trigger_components.values())
    intensity = round(max(wind_ratio, rain_ratio, surge_ratio), 3)
    payout_rate = round(0.15 + 0.60 * intensity, 3) if triggered else 0.0
    liquidity = round(exposed_value * payout_rate, 2)
    return {
        "status": "success",
        "triggered": triggered,
        "trigger_components": trigger_components,
        "triggers": {"wind_kmh": trigger_wind, "rainfall_mm": trigger_rain, "surge_m": trigger_surge},
        "scenario": {"wind_kmh": wind_speed, "rainfall_mm": rainfall, "surge_m": surge_height_m},
        "estimated_exposed_value_inr": round(exposed_value, 2),
        "illustrative_payout_rate": payout_rate,
        "illustrative_liquidity_inr": liquidity,
        "method": "Illustrative index trigger and payout scenario using mapped asset-category values.",
        "disclaimer": "Not an insurance quote, policy, underwriting decision, or guaranteed payout. Real parametric products require actuarial, legal and regulatory design.",
    }
