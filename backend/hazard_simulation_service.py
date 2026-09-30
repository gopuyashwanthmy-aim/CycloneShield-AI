"""
CycloneShield AI - Module 8
Storm-surge and rainfall-damage-pathway simulation.

This module intentionally implements a transparent prototype simulation,
not a calibrated coastal flood model or official forecast.

Storm surge:
- Uses SRTM elevation from Google Earth Engine.
- Uses OSM coastline geometry when available.
- Applies a simple bathtub-style screening rule: low terrain within a
  configurable coastal-influence distance is flagged when elevation is
  at or below the supplied surge-height scenario.

Rainfall pathways:
- Uses rainfall scenario intensity together with HydroSHEDS flow
  accumulation and terrain elevation.
- Produces a relative pathway-pressure score for screening locations
  that may concentrate runoff.
"""

import math
from typing import Any

import ee
import requests

from backend.earth_engine_service import initialize_earth_engine
from backend.resilience_service import cached_call

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

GRID_SIZE = 13
GRID_SPACING_KM = 1.0
COAST_QUERY_RADIUS_M = 60000


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return radius * 2 * math.asin(math.sqrt(a))


def point_to_segment_distance_km(
    lat: float,
    lon: float,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Approximate point-to-segment distance using a local equirectangular plane."""
    lat_ref = math.radians((lat + lat1 + lat2) / 3.0)
    scale_x = 111.32 * math.cos(lat_ref)
    scale_y = 111.32

    px = lon * scale_x
    py = lat * scale_y
    x1 = lon1 * scale_x
    y1 = lat1 * scale_y
    x2 = lon2 * scale_x
    y2 = lat2 * scale_y

    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)

    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    nearest_x = x1 + t * dx
    nearest_y = y1 + t * dy
    return math.hypot(px - nearest_x, py - nearest_y)


def _fetch_coastline_live(latitude: float, longitude: float) -> list[tuple[float, float, float, float]]:
    query = f"""
    [out:json][timeout:30];
    way[\"natural\"=\"coastline\"](around:{COAST_QUERY_RADIUS_M},{latitude},{longitude});
    out geom;
    """

    for server in OVERPASS_SERVERS:
        try:
            print("Trying coastline server:", server)
            response = requests.post(
                server,
                data={"data": query},
                timeout=45,
                headers={"User-Agent": "CycloneShield-AI/1.0"},
            )
            print("Coastline response:", response.status_code)
            if response.status_code != 200:
                continue

            payload = response.json()
            segments = []
            for element in payload.get("elements", []):
                geometry = element.get("geometry") or []
                for first, second in zip(geometry, geometry[1:]):
                    segments.append(
                        (
                            float(first["lat"]),
                            float(first["lon"]),
                            float(second["lat"]),
                            float(second["lon"]),
                        )
                    )
            if segments:
                print("Coastline segments received:", len(segments))
                return segments
        except Exception as exc:
            print("Coastline server error:", exc)

    raise RuntimeError("All coastline Overpass servers failed")


def fetch_coastline_segments(latitude: float, longitude: float) -> tuple[list[tuple[float, float, float, float]], dict]:
    payload = {
        "lat": round(latitude, 4),
        "lon": round(longitude, 4),
        "radius_m": COAST_QUERY_RADIUS_M,
    }
    try:
        segments, meta = cached_call(
            "coastline_segments",
            payload,
            lambda: _fetch_coastline_live(latitude, longitude),
        )
        return segments or [], meta
    except Exception as exc:
        return [], {"source": "unavailable", "error": str(exc)}


def nearest_coast_distance_km(
    latitude: float,
    longitude: float,
    segments: list[tuple[float, float, float, float]],
) -> float | None:
    if not segments:
        return None
    # Fast bounding prefilter followed by local segment distance.
    best = float("inf")
    for lat1, lon1, lat2, lon2 in segments:
        if abs(latitude - (lat1 + lat2) / 2) > 1.0:
            continue
        if abs(longitude - (lon1 + lon2) / 2) > 1.5:
            continue
        distance = point_to_segment_distance_km(
            latitude, longitude, lat1, lon1, lat2, lon2
        )
        if distance < best:
            best = distance
    return None if math.isinf(best) else round(best, 3)


def build_grid(latitude: float, longitude: float) -> list[dict[str, Any]]:
    cells = []
    half = GRID_SIZE // 2
    cos_lat = max(math.cos(math.radians(latitude)), 0.2)
    lat_step = GRID_SPACING_KM / 111.32
    lon_step = GRID_SPACING_KM / (111.32 * cos_lat)

    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            lat = latitude + (row - half) * lat_step
            lon = longitude + (col - half) * lon_step
            cells.append({
                "row": row,
                "col": col,
                "latitude": lat,
                "longitude": lon,
            })
    return cells


def sample_surface_water_distance_grid(cells: list[dict[str, Any]]) -> dict[tuple[int, int], float]:
    """Estimate distance to mapped surface water with Earth Engine.

    This is a fallback when Overpass coastline geometry is unavailable. It is
    deliberately described as surface-water proximity rather than a precise
    coastline, because inland water bodies can also be present.
    """
    initialize_earth_engine()
    features = [
        ee.Feature(
            ee.Geometry.Point([cell["longitude"], cell["latitude"]]),
            {"row": cell["row"], "col": cell["col"]},
        )
        for cell in cells
    ]
    collection = ee.FeatureCollection(features)
    water = (
        ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        .select("occurrence")
        .gte(50)
        .unmask(0)
    )
    # SRTM/HydroSHEDS screening grid is ~464 m; distance is returned in
    # pixels and converted approximately to kilometres.
    distance_pixels = water.fastDistanceTransform(256, "pixels", "squared_euclidean").sqrt()
    distance_km = distance_pixels.multiply(463.83).divide(1000).rename("water_distance_km")
    sampled = distance_km.reduceRegions(
        collection=collection,
        reducer=ee.Reducer.first(),
        scale=463.83,
        tileScale=2,
    ).getInfo()
    result = {}
    for feature in sampled.get("features", []):
        props = feature.get("properties", {})
        value = _number_or_none(props.get("water_distance_km"))
        if value is not None:
            result[(props.get("row"), props.get("col"))] = value
    return result


def sample_earth_engine_grid(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    initialize_earth_engine()

    features = [
        ee.Feature(
            ee.Geometry.Point([cell["longitude"], cell["latitude"]]),
            {"row": cell["row"], "col": cell["col"]},
        )
        for cell in cells
    ]
    collection = ee.FeatureCollection(features)

    srtm = ee.Image("USGS/SRTMGL1_003").select("elevation")
    slope = ee.Terrain.slope(srtm).rename("slope")
    flow = ee.Image("WWF/HydroSHEDS/15ACC").select("b1").rename("flow_accumulation")
    water = (
        ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        .select("occurrence")
        .rename("water_occurrence")
    )

    composite = srtm.addBands(slope).addBands(flow).addBands(water)
    sampled = composite.reduceRegions(
        collection=collection,
        reducer=ee.Reducer.first(),
        scale=463.83,
        tileScale=2,
    ).getInfo()

    values = {}
    for feature in sampled.get("features", []):
        props = feature.get("properties", {})
        key = (props.get("row"), props.get("col"))
        values[key] = props

    output = []
    for cell in cells:
        props = values.get((cell["row"], cell["col"]), {})
        output.append({
            **cell,
            "elevation_m": _number_or_none(props.get("elevation")),
            "slope_deg": _number_or_none(props.get("slope")),
            "flow_accumulation": _number_or_none(props.get("flow_accumulation")),
            "water_occurrence_pct": _number_or_none(props.get("water_occurrence")),
        })
    return output


def _number_or_none(value):
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def level_from_score(score: float) -> str:
    if score >= 75:
        return "Very High"
    if score >= 55:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def simulate_hazard_pathways(
    latitude: float,
    longitude: float,
    wind_speed: float,
    rainfall: float,
    surge_height_m: float,
    infrastructure_data: dict,
) -> dict:
    """Generate the Module 8 hazard simulation and exposure summary."""

    cells = build_grid(latitude, longitude)
    coastline_segments, coastline_meta = fetch_coastline_segments(latitude, longitude)

    try:
        sampled_cells = sample_earth_engine_grid(cells)
    except Exception as exc:
        print("Hazard grid Earth Engine error:", exc)
        raise

    # Overpass coastline data is preferred. If it is unavailable, use
    # Earth Engine surface-water proximity so a transient Overpass outage
    # does not disable the surge screening entirely.
    surface_water_distance = {}
    if not coastline_segments:
        try:
            surface_water_distance = sample_surface_water_distance_grid(cells)
            print("Earth Engine surface-water fallback cells:", len(surface_water_distance))
        except Exception as exc:
            print("Surface-water fallback error:", exc)

    coast_distances = []
    for cell in sampled_cells:
        distance = nearest_coast_distance_km(
            cell["latitude"], cell["longitude"], coastline_segments
        )
        if distance is None:
            distance = surface_water_distance.get((cell["row"], cell["col"]))
            cell["coast_distance_source"] = "Earth Engine mapped surface-water proximity" if distance is not None else None
        else:
            cell["coast_distance_source"] = "OpenStreetMap coastline"
        cell["coast_distance_km"] = distance
        if distance is not None:
            coast_distances.append(distance)

    valid_elevations = [c["elevation_m"] for c in sampled_cells if c["elevation_m"] is not None]
    valid_flows = [c["flow_accumulation"] for c in sampled_cells if c["flow_accumulation"] is not None]

    min_elev = min(valid_elevations) if valid_elevations else None
    max_elev = max(valid_elevations) if valid_elevations else None
    log_flows = [math.log10(max(v, 1.0)) for v in valid_flows]
    min_log_flow = min(log_flows) if log_flows else None
    max_log_flow = max(log_flows) if log_flows else None

    # Scenario-derived coastal influence distance. This is deliberately a
    # screening radius, not a hydrodynamic surge propagation result.
    coastal_influence_km = max(5.0, min(20.0, surge_height_m * 5.0 + wind_speed / 100.0))

    rainfall_intensity = clamp((rainfall / 300.0) * 100.0)
    surge_exposed = 0
    pathway_high = 0
    pathway_medium = 0

    for cell in sampled_cells:
        elevation = cell["elevation_m"]
        coast_distance = cell["coast_distance_km"]

        water_occurrence = cell.get("water_occurrence_pct")

        # Missing optional water-occurrence data must never abort the
        # simulation. Treat it as unknown rather than as a numeric value.
        water_clear_or_unknown = (
            water_occurrence is None
            or water_occurrence < 80
        )

        surge_candidate = (
            elevation is not None
            and coast_distance is not None
            and coast_distance <= coastal_influence_km
            and elevation <= surge_height_m
            and water_clear_or_unknown
        )
        cell["storm_surge_exposed"] = bool(surge_candidate)
        cell["storm_surge_level"] = (
            "High" if surge_candidate and elevation <= surge_height_m * 0.5
            else "Medium" if surge_candidate
            else "None"
        )
        if surge_candidate:
            surge_exposed += 1

        low_elevation_score = 0.0
        if elevation is not None and min_elev is not None and max_elev is not None and max_elev > min_elev:
            low_elevation_score = clamp(
                (max_elev - elevation) / (max_elev - min_elev) * 100
            )

        flow_score = 0.0
        if cell.get("flow_accumulation") is not None and min_log_flow is not None and max_log_flow is not None and max_log_flow > min_log_flow:
            log_flow = math.log10(max(cell["flow_accumulation"], 1.0))
            flow_score = clamp(
                (log_flow - min_log_flow) / (max_log_flow - min_log_flow) * 100
            )

        slope = cell.get("slope_deg")
        slope_factor = 100.0 if slope is None else clamp(100.0 - min(float(slope), 45.0) / 45.0 * 100.0)

        pathway_score = round(
            rainfall_intensity * 0.45
            + flow_score * 0.35
            + low_elevation_score * 0.15
            + slope_factor * 0.05,
            1,
        )
        cell["rainfall_pathway_score"] = pathway_score
        cell["rainfall_pathway_level"] = level_from_score(pathway_score)
        cell["runoff_screening_factors"] = [
            "Rainfall scenario",
            "HydroSHEDS flow accumulation",
            "Relative terrain elevation",
        ]

        if pathway_score >= 75:
            pathway_high += 1
        elif pathway_score >= 55:
            pathway_medium += 1

    assets = infrastructure_data.get("features", [])
    affected_assets = []
    for asset in assets:
        try:
            asset_lat = float(asset["latitude"])
            asset_lon = float(asset["longitude"])
        except (KeyError, TypeError, ValueError):
            continue

        nearest = min(
            sampled_cells,
            key=lambda cell: haversine_km(
                asset_lat, asset_lon, cell["latitude"], cell["longitude"]
            ),
        )
        if nearest.get("storm_surge_exposed") or nearest.get("rainfall_pathway_score", 0) >= 55:
            affected_assets.append({
                "id": asset.get("id"),
                "name": asset.get("name") or "Unnamed asset",
                "type": asset.get("type", "Infrastructure"),
                "distance_km": asset.get("distance_km"),
                "storm_surge_exposed": nearest.get("storm_surge_exposed", False),
                "rainfall_pathway_score": nearest.get("rainfall_pathway_score", 0),
                "rainfall_pathway_level": nearest.get("rainfall_pathway_level", "Low"),
            })

    affected_assets.sort(
        key=lambda item: (
            item["storm_surge_exposed"],
            item["rainfall_pathway_score"],
        ),
        reverse=True,
    )

    return {
        "status": "success",
        "grid": {
            "rows": GRID_SIZE,
            "columns": GRID_SIZE,
            "cell_spacing_km": GRID_SPACING_KM,
        },
        "storm_surge": {
            "scenario_surge_height_m": round(float(surge_height_m), 2),
            "coastal_influence_radius_km": round(coastal_influence_km, 2),
            "inundated_cells": surge_exposed,
            "screening_status": (
                "live_coastline" if coastline_meta.get("source") == "live" else
                "cached_coastline" if coastline_meta.get("source") == "cache" else
                "surface_water_fallback" if surface_water_distance else
                "unavailable"
            ),
            "coastline_data_available": bool(coastline_segments),
            "coastline_data_source": coastline_meta.get("source"),
            "coastline_cache_age_seconds": coastline_meta.get("cache_age_seconds"),
            "surface_water_fallback_available": bool(surface_water_distance),
            "method": "Prototype bathtub-style screening using SRTM elevation and mapped coastal/surface-water proximity.",
            "note": (
                "This is a screening simulation, not a hydrodynamic storm-surge forecast or official inundation boundary."
                if (coastline_segments or surface_water_distance) else
                "Storm-surge screening unavailable for this run because coastal/surface-water proximity data could not be retrieved."
            ),
        },
        "rainfall_pathways": {
            "scenario_rainfall_mm": round(float(rainfall), 2),
            "rainfall_intensity_score": round(rainfall_intensity, 1),
            "high_pathway_cells": pathway_high,
            "medium_pathway_cells": pathway_medium,
            "method": "Relative runoff-pathway screening using rainfall scenario, HydroSHEDS flow accumulation and terrain context.",
            "note": "Rainfall duration, soil infiltration and detailed drainage networks are not modeled; scores are relative screening indicators.",
        },
        "cells": sampled_cells,
        "affected_assets": affected_assets[:50],
        "affected_asset_count": len(affected_assets),
        "data_sources": [
            "USGS SRTMGL1 elevation via Google Earth Engine",
            "WWF HydroSHEDS 15 arc-second flow accumulation via Google Earth Engine",
            "JRC Global Surface Water occurrence via Google Earth Engine",
            "OpenStreetMap coastline via Overpass when available or cached",
            "JRC Global Surface Water occurrence via Google Earth Engine for coastline-proximity fallback",
        ],
    }
