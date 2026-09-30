from typing import Any, Dict, List


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _impact_level(score: float) -> str:
    if score >= 75:
        return "Very High"
    if score >= 55:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def _add_action(
    actions: List[Dict[str, Any]],
    priority: str,
    category: str,
    title: str,
    action: str,
    reason: str,
):
    actions.append(
        {
            "priority": priority,
            "category": category,
            "title": title,
            "action": action,
            "reason": reason,
        }
    )


def generate_decision_support(
    wind_speed: float,
    rainfall: float,
    geospatial_data: Dict[str, Any],
    infrastructure_data: Dict[str, Any],
    vulnerability_data: Dict[str, Any],
    risk_score: float,
) -> Dict[str, Any]:

    wind_speed = _safe_float(wind_speed)
    rainfall = _safe_float(rainfall)
    risk_score = _safe_float(risk_score)

    elevation = geospatial_data.get("elevation_meters")
    built_probability = geospatial_data.get("built_probability")
    water_probability = geospatial_data.get("water_probability")

    elevation = (
        None
        if elevation is None
        else _safe_float(elevation)
    )

    built_probability = (
        None
        if built_probability is None
        else _safe_float(built_probability)
    )

    water_probability = (
        None
        if water_probability is None
        else _safe_float(water_probability)
    )

    summary = infrastructure_data.get(
        "summary",
        {}
    )

    hospitals = _safe_int(
        summary.get("hospitals")
    )

    schools = _safe_int(
        summary.get("schools")
    )

    power_substations = _safe_int(
        summary.get("power_substations")
    )

    major_roads = _safe_int(
        summary.get("major_roads")
    )

    vulnerability_level_counts = (
        vulnerability_data.get(
            "level_counts",
            {}
        )
    )

    high_assets = _safe_int(
        vulnerability_level_counts.get(
            "High"
        )
    )

    very_high_assets = _safe_int(
        vulnerability_level_counts.get(
            "Very High"
        )
    )

    total_assessed = _safe_int(
        vulnerability_data.get(
            "total_assessed"
        )
    )

    average_score = _safe_float(
        vulnerability_data.get(
            "overall_score"
        )
    )

    actions: List[Dict[str, Any]] = []
    monitoring_points: List[str] = []
    data_gaps: List[str] = []

    # ==========================================================
    # OVERALL PLANNING PRIORITY
    # ==========================================================

    if risk_score >= 75 or very_high_assets > 0:
        planning_priority = "Very High"
    elif risk_score >= 55 or high_assets >= 10:
        planning_priority = "High"
    elif risk_score >= 35:
        planning_priority = "Medium"
    else:
        planning_priority = "Low"

    # ==========================================================
    # HEALTHCARE
    # ==========================================================

    if hospitals > 0:
        if hospitals >= 10 or very_high_assets > 0:
            priority = "High"
        else:
            priority = "Medium"

        _add_action(
            actions,
            priority,
            "Healthcare",
            "Review healthcare continuity",
            (
                "Review emergency access, backup power, "
                "staffing continuity and essential-service "
                "plans for mapped healthcare facilities "
                "within the assessment area."
            ),
            (
                f"{hospitals} mapped hospitals were identified "
                "within the infrastructure search area."
            ),
        )

        monitoring_points.append(
            "Monitor accessibility and continuity of mapped healthcare facilities."
        )

    # ==========================================================
    # POWER
    # ==========================================================

    if power_substations > 0:
        priority = (
            "High"
            if power_substations >= 5
            or risk_score >= 55
            else "Medium"
        )

        _add_action(
            actions,
            priority,
            "Power",
            "Review power continuity",
            (
                "Review backup-power arrangements, access "
                "plans and continuity procedures for mapped "
                "power substations."
            ),
            (
                f"{power_substations} mapped power substations "
                "were identified in the assessment area."
            ),
        )

        monitoring_points.append(
            "Monitor access and operational status of mapped power infrastructure."
        )

    # ==========================================================
    # TRANSPORT
    # ==========================================================

    if major_roads > 0:
        priority = (
            "High"
            if risk_score >= 55
            else "Medium"
        )

        _add_action(
            actions,
            priority,
            "Transport",
            "Review critical road access",
            (
                "Identify important road corridors that may "
                "need access monitoring and contingency planning "
                "during severe weather conditions."
            ),
            (
                f"{major_roads} mapped major-road features "
                "were identified."
            ),
        )

        monitoring_points.append(
            "Monitor key road corridors for access restrictions, flooding or debris."
        )

    # ==========================================================
    # EDUCATION
    # ==========================================================

    if schools > 0:
        priority = (
            "High"
            if risk_score >= 55
            else "Medium"
        )

        _add_action(
            actions,
            priority,
            "Education",
            "Review school continuity",
            (
                "Review continuity procedures for mapped schools, "
                "including communication, access and temporary "
                "closure arrangements if conditions deteriorate."
            ),
            (
                f"{schools} mapped schools were identified "
                "within the search area."
            ),
        )

        monitoring_points.append(
            "Monitor access and operational status of mapped schools."
        )

    # ==========================================================
    # FLOOD / LOW-ELEVATION CONTEXT
    # ==========================================================

    if elevation is not None and elevation <= 15:
        _add_action(
            actions,
            "High" if risk_score >= 55 else "Medium",
            "Flood & Drainage",
            "Review low-elevation exposure",
            (
                "Review local drainage, water accumulation and "
                "access-continuity considerations for low-elevation "
                "areas."
            ),
            (
                f"Earth Engine elevation at the assessment point "
                f"is approximately {elevation:.1f} m."
            ),
        )

        monitoring_points.append(
            "Monitor local drainage and surface-water accumulation."
        )

    # ==========================================================
    # BUILT ENVIRONMENT
    # ==========================================================

    if (
        built_probability is not None
        and built_probability >= 0.70
    ):
        _add_action(
            actions,
            "High" if risk_score >= 55 else "Medium",
            "Built Environment",
            "Review dense built-area exposure",
            (
                "Prioritize situational monitoring and continuity "
                "planning in highly built-up areas."
            ),
            (
                f"Dynamic World reports approximately "
                f"{built_probability * 100:.1f}% built probability "
                "at the assessment point."
            ),
        )

    # ==========================================================
    # WATER CONTEXT
    # ==========================================================

    if (
        water_probability is not None
        and water_probability >= 0.20
    ):
        _add_action(
            actions,
            "High" if risk_score >= 55 else "Medium",
            "Water Context",
            "Review nearby water-related exposure",
            (
                "Review local water bodies, drainage pathways "
                "and potential access constraints using local "
                "authoritative information."
            ),
            (
                f"Dynamic World reports approximately "
                f"{water_probability * 100:.1f}% water probability "
                "at the assessment point."
            ),
        )

    # ==========================================================
    # HIGH-IMPACT ASSETS
    # ==========================================================

    highest_assets = vulnerability_data.get(
        "highest_impact_assets",
        []
    )

    if highest_assets:
        asset_names = []

        for asset in highest_assets[:5]:
            name = asset.get("name")

            if name:
                asset_names.append(name)

        if asset_names:
            _add_action(
                actions,
                "High",
                "Infrastructure",
                "Review highest-impact mapped assets",
                (
                    "Use the infrastructure impact list to "
                    "identify mapped assets that warrant closer "
                    "local verification and continuity planning."
                ),
                (
                    "Highest-impact mapped assets include: "
                    + ", ".join(asset_names)
                    + "."
                ),
            )

    # ==========================================================
    # GENERAL RISK RESPONSE
    # ==========================================================

    if risk_score >= 75:
        _add_action(
            actions,
            "Very High",
            "Overall Assessment",
            "Escalate planning attention",
            (
                "Use the assessment as an input to preparedness "
                "and continuity planning, while checking official "
                "meteorological and disaster-management information "
                "for current conditions and instructions."
            ),
            (
                f"The prototype cyclone scenario risk indicator "
                f"is {risk_score:.0f}/100."
            ),
        )

    elif risk_score >= 55:
        _add_action(
            actions,
            "High",
            "Overall Assessment",
            "Increase preparedness attention",
            (
                "Review sector-specific continuity plans and "
                "continue monitoring official weather and "
                "disaster-management information."
            ),
            (
                f"The prototype cyclone scenario risk indicator "
                f"is {risk_score:.0f}/100."
            ),
        )

    elif risk_score >= 35:
        _add_action(
            actions,
            "Medium",
            "Overall Assessment",
            "Maintain preparedness monitoring",
            (
                "Maintain situational awareness and review "
                "relevant continuity procedures."
            ),
            (
                f"The prototype cyclone scenario risk indicator "
                f"is {risk_score:.0f}/100."
            ),
        )

    else:
        _add_action(
            actions,
            "Low",
            "Overall Assessment",
            "Continue routine monitoring",
            (
                "Continue monitoring official information and "
                "review local preparedness procedures as needed."
            ),
            (
                f"The prototype cyclone scenario risk indicator "
                f"is {risk_score:.0f}/100."
            ),
        )

    # ==========================================================
    # DATA QUALITY / LIMITATIONS
    # ==========================================================

    if (
        geospatial_data.get(
            "recent_precipitation_mm"
        )
        is None
    ):
        data_gaps.append(
            "Earth Engine recent precipitation value is unavailable."
        )

    if infrastructure_data.get("status") != "success":
        data_gaps.append(
            "Infrastructure retrieval did not complete successfully."
        )

    if total_assessed == 0:
        data_gaps.append(
            "No infrastructure assets were available for impact assessment."
        )

    data_gaps.extend(
        [
            (
                "OpenStreetMap infrastructure represents mapped assets "
                "and is not a complete infrastructure inventory."
            ),
            (
                "The prototype impact score does not establish the "
                "structural condition of an individual asset."
            ),
            (
                "Rainfall duration and local drainage conditions are "
                "not fully represented by the supplied scenario."
            ),
        ]
    )

    # ==========================================================
    # OFFICIAL INFORMATION
    # ==========================================================

    official_sources_note = (
        "CycloneShield AI provides prototype impact-assessment "
        "and planning information. Official weather warnings, "
        "evacuation instructions and emergency directions should "
        "be obtained from the relevant meteorological and "
        "disaster-management authorities."
    )

    # ==========================================================
    # SORT ACTIONS
    # ==========================================================

    priority_order = {
        "Very High": 0,
        "High": 1,
        "Medium": 2,
        "Low": 3,
    }

    actions.sort(
        key=lambda item: priority_order.get(
            item.get("priority"),
            99
        )
    )

    return {
        "status": "success",
        "planning_priority": planning_priority,
        "risk_score": round(risk_score, 1),
        "average_impact_score": round(
            average_score,
            1
        ),
        "assets_assessed": total_assessed,
        "priority_actions": actions,
        "monitoring_points": monitoring_points,
        "data_gaps": data_gaps,
        "official_sources_note": official_sources_note,
        "methodology": (
            "Decision support is generated from the supplied "
            "cyclone scenario, Earth Engine environmental "
            "context, OpenStreetMap infrastructure exposure "
            "and prototype infrastructure impact indicators. "
            "It is intended for planning support and is not "
            "an official emergency command system."
        ),
    }