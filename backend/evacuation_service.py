"""Pre-landfall evacuation planning and infrastructure hardening recommendations."""
from __future__ import annotations
from typing import Any


def _nearby_assets(features, asset_types, max_km=8):
    return [a for a in features if a.get("type") in asset_types and float(a.get("distance_km", 999)) <= max_km]


def generate_evacuation_plan(latitude, longitude, vulnerability, infrastructure, hazard, meteorology):
    features = infrastructure.get("features", [])
    high_assets = [a for a in vulnerability.get("assets", []) if a.get("impact_level") in {"Very High", "High"}]
    affected = hazard.get("affected_assets", [])
    shelters = _nearby_assets(features, {"Medical Shelter", "School"}, 10)
    roads = _nearby_assets(features, {"Major Road"}, 10)
    blocked = {a.get("id") for a in affected}
    route_risks = [r for r in roads if r.get("id") in blocked]
    priority = "Very High" if len(high_assets) >= 20 or hazard.get("affected_asset_count", 0) >= 20 else "High" if high_assets else "Medium"
    actions = [
        "Identify people and facilities in the highest-impact assessment areas before landfall.",
        "Pre-position transport, medical support and communications for priority areas.",
        "Use multiple access corridors and verify road status before movement.",
        "Confirm shelter capacity and accessibility with local authorities before issuing evacuation orders.",
    ]
    if route_risks:
        actions.insert(0, f"Review {len(route_risks)} mapped road features intersecting simulated hazard zones.")
    return {
        "status": "success",
        "planning_priority": priority,
        "assessment_center": {"latitude": latitude, "longitude": longitude},
        "high_priority_assets": len(high_assets),
        "hazard_affected_assets": hazard.get("affected_asset_count", 0),
        "candidate_shelters": shelters[:20],
        "route_risk_features": route_risks[:30],
        "evacuation_actions": actions,
        "planning_sequence": [
            "Validate official warning and local authority guidance.",
            "Confirm vulnerable-population and facility lists.",
            "Validate shelter capacity and accessibility.",
            "Validate road status and alternate routes.",
            "Issue or coordinate official instructions through authorized channels.",
        ],
        "note": "This is a planning aid, not an evacuation order or official route plan.",
    }


def generate_hardening_plan(infrastructure, vulnerability, hazard):
    summary = infrastructure.get("summary", {})
    actions = []
    if summary.get("power_substations", 0):
        actions.append({"sector": "Power", "actions": ["Review flood protection and equipment elevation.", "Verify backup control/communications and access arrangements.", "Pre-stage restoration resources and alternate access routes."]})
    if summary.get("hospitals", 0):
        actions.append({"sector": "Healthcare", "actions": ["Review backup power, water and communications continuity.", "Protect critical equipment and records from flood exposure.", "Confirm emergency access and patient transfer arrangements."]})
    if summary.get("major_roads", 0):
        actions.append({"sector": "Roads", "actions": ["Inspect drainage and known low points.", "Pre-position debris-clearance resources.", "Identify alternate corridors for emergency access."]})
    if summary.get("schools", 0):
        actions.append({"sector": "Schools", "actions": ["Review roof, window and utility vulnerabilities.", "Protect equipment and records from water ingress.", "Coordinate closure/shelter decisions with authorities."]})
    return {"status": "success", "sector_plans": actions, "note": "Prototype hardening checklist; engineering design requires qualified assessment."}
