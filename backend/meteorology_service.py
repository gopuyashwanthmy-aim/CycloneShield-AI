"""Meteorological intelligence using a public current/forecast weather feed.

The service deliberately labels observations, forecasts and user-entered scenarios
separately. It does not present a weather feed as an official cyclone warning.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from backend.resilience_service import cached_call


def _fetch_open_meteo(latitude: float, longitude: float) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,precipitation,rain",
        "hourly": "precipitation_probability,precipitation,wind_speed_10m,wind_gusts_10m",
        "forecast_days": 2,
        "timezone": "auto",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "CycloneShieldAI/1.0"})
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def get_meteorological_intelligence(latitude: float, longitude: float, scenario_wind: float, scenario_rainfall: float) -> dict[str, Any]:
    payload = {"lat": round(latitude, 4), "lon": round(longitude, 4)}
    try:
        raw, meta = cached_call("weather", payload, lambda: _fetch_open_meteo(latitude, longitude))
        current = raw.get("current", {})
        hourly = raw.get("hourly", {})
        times = hourly.get("time", [])
        wind = hourly.get("wind_speed_10m", [])
        gusts = hourly.get("wind_gusts_10m", [])
        rain = hourly.get("precipitation", [])
        rain_prob = hourly.get("precipitation_probability", [])
        horizon = []
        for i in range(min(len(times), 24)):
            horizon.append({
                "time": times[i],
                "wind_speed_kmh": wind[i] if i < len(wind) else None,
                "wind_gust_kmh": gusts[i] if i < len(gusts) else None,
                "precipitation_mm": rain[i] if i < len(rain) else None,
                "precipitation_probability_pct": rain_prob[i] if i < len(rain_prob) else None,
            })
        return {
            "status": "success",
            "provider": "Open-Meteo",
            "feed_type": "current_and_forecast",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "data_status": meta["source"],
            "current": {
                "temperature_c": current.get("temperature_2m"),
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "wind_direction_deg": current.get("wind_direction_10m"),
                "precipitation_mm": current.get("precipitation"),
                "rain_mm": current.get("rain"),
            },
            "next_24_hours": horizon,
            "scenario": {
                "wind_speed_kmh": scenario_wind,
                "rainfall_mm": scenario_rainfall,
                "wind_vs_current_ratio": round(scenario_wind / max(float(current.get("wind_speed_10m") or 1), 1), 2),
                "rainfall_scenario_vs_current_hour": round(scenario_rainfall / max(float(current.get("precipitation") or 0.1), 0.1), 2),
            },
            "uncertainty": [
                "Public forecast feeds are not a substitute for official cyclone warnings.",
                "Scenario wind/rainfall values are user inputs and may represent a synthetic event.",
            ],
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "provider": "Open-Meteo",
            "feed_type": "current_and_forecast",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "data_status": "unavailable",
            "current": {},
            "next_24_hours": [],
            "scenario": {"wind_speed_kmh": scenario_wind, "rainfall_mm": scenario_rainfall},
            "error": str(exc),
            "uncertainty": ["Meteorological external feed was unavailable; scenario inputs remain available."],
        }
