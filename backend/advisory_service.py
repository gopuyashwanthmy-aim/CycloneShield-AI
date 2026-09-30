"""Early-warning advisory generation and simulated authority dispatch log."""
from __future__ import annotations
from datetime import datetime, timezone
import uuid


def generate_advisory(request, risk_score, vulnerability, hazard, evacuation, meteorology):
    highest = vulnerability.get("overall_level", "Low")
    surge = hazard.get("storm_surge", {})
    rain = hazard.get("rainfall_pathways", {})
    severity = "VERY HIGH" if risk_score >= 75 or highest == "Very High" else "HIGH" if risk_score >= 55 or highest == "High" else "MODERATE" if risk_score >= 35 else "LOW"
    headline = f"CycloneShield AI preparedness advisory: {severity} scenario assessment for {request.location}"
    body = (
        f"Scenario: {request.cyclone_name}. Wind {request.wind_speed:g} km/h, rainfall {request.rainfall:g} mm, "
        f"surge {request.surge_height_m:g} m. Risk score {risk_score}/100. "
        f"The model identified {hazard.get('affected_asset_count', 0)} mapped assets intersecting simulated hazard zones. "
        "Authorities should validate all conditions against official meteorological and disaster-management information before action."
    )
    return {
        "status": "success",
        "advisory_id": f"ADV-{uuid.uuid4().hex[:10].upper()}",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "severity": severity,
        "headline": headline,
        "message": body,
        "recommended_actions": evacuation.get("evacuation_actions", [])[:5],
        "hazard_indicators": {
            "storm_surge_cells": surge.get("inundated_cells", 0),
            "rainfall_high_pathways": rain.get("high_pathway_cells", 0),
            "affected_assets": hazard.get("affected_asset_count", 0),
        },
        "targeting": ["Municipal disaster management", "Emergency operations", "Critical infrastructure coordinators"],
        "dispatch_mode": "simulation_only",
        "dispatch_log": [],
        "note": "No external message is sent by this prototype. Dispatch is simulated until an authorized messaging connector is configured.",
    }


def simulate_dispatch(advisory, channel, recipients):
    event = {
        "dispatch_id": f"DSP-{uuid.uuid4().hex[:10].upper()}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "channel": channel,
        "recipients": recipients,
        "status": "simulated",
    }
    advisory = dict(advisory)
    advisory["dispatch_log"] = list(advisory.get("dispatch_log", [])) + [event]
    return advisory
