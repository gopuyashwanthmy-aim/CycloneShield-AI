from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from backend.resilience_service import cached_call

# Multiple public Overpass instances are used.  Infrastructure groups are
# queried independently so a timeout in one category cannot zero-out the
# entire inventory.
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
SEARCH_RADIUS_METERS = 10000
OVERPASS_TIMEOUT_SECONDS = 45
USER_AGENT = "CycloneShieldAI/2.6"


def calculate_distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lat2 - lat1)
    dn = math.radians(lon2 - lon1)
    a = math.sin(dl / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dn / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_element_coordinates(element):
    if element.get("type") == "node":
        return element.get("lat"), element.get("lon")
    center = element.get("center") or {}
    return center.get("lat"), center.get("lon")


def classify_infrastructure(tags):
    amenity = tags.get("amenity")
    power = tags.get("power")
    highway = tags.get("highway")

    if amenity == "hospital":
        return "Hospital"
    if amenity in {"school", "college", "university"}:
        return "School"
    if amenity in {"clinic", "doctors"}:
        return "Medical Facility"
    if (
        amenity in {"shelter", "social_facility"}
        or tags.get("emergency") in {"shelter", "assembly_point"}
    ):
        return "Medical Shelter"
    if power == "substation":
        return "Power Substation"
    if highway in {
        "motorway", "motorway_link", "trunk", "trunk_link",
        "primary", "primary_link", "secondary", "secondary_link",
    }:
        return "Major Road"
    return None


def _around(tag_clause: str, latitude: float, longitude: float) -> str:
    return f'{tag_clause}(around:{SEARCH_RADIUS_METERS},{latitude},{longitude});'


def build_overpass_query(latitude, longitude, kind="all"):
    """Build small, independently retrievable Overpass queries.

    The previous implementation bundled hospitals, schools, substations and
    shelters into one large query. A transient timeout then removed every
    non-road category. Splitting them makes the pipeline resilient while
    keeping the data entirely live OpenStreetMap/Overpass data.
    """
    clauses = {
        "hospitals": _around('nwr["amenity"="hospital"]', latitude, longitude),
        "schools": _around('nwr["amenity"~"school|college|university"]', latitude, longitude),
        "power": _around('nwr["power"="substation"]', latitude, longitude),
        "shelters": (
            _around('nwr["amenity"~"shelter|social_facility"]', latitude, longitude)
            + _around('nwr["emergency"~"shelter|assembly_point"]', latitude, longitude)
        ),
        "roads": _around(
            'way["highway"~"motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link"]',
            latitude,
            longitude,
        ),
    }

    if kind == "roads":
        body = clauses["roads"]
    elif kind in clauses:
        body = clauses[kind]
    else:
        body = "".join(clauses[k] for k in ("hospitals", "schools", "power", "shelters"))

    return f"[out:json][timeout:{OVERPASS_TIMEOUT_SECONDS}];\n{body}\nout center;"


def _query_overpass_once(server, query, method="POST"):
    headers = {"User-Agent": USER_AGENT}
    if method == "POST":
        encoded = urllib.parse.urlencode({"data": query}).encode()
        req = urllib.request.Request(
            server,
            data=encoded,
            method="POST",
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
        )
    else:
        url = server + "?" + urllib.parse.urlencode({"data": query})
        req = urllib.request.Request(url, method="GET", headers=headers)

    with urllib.request.urlopen(req, timeout=OVERPASS_TIMEOUT_SECONDS + 10) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def query_overpass(query):
    """Try POST and GET across all configured Overpass instances."""
    errors = []
    for server in OVERPASS_SERVERS:
        for method in ("POST", "GET"):
            try:
                data = _query_overpass_once(server, query, method)
                if isinstance(data, dict) and isinstance(data.get("elements"), list):
                    return data
                raise RuntimeError("Overpass returned an invalid response")
            except Exception as exc:
                errors.append(f"{server} {method}: {exc}")
                print("Overpass attempt failed:", errors[-1])
    raise RuntimeError("All Overpass servers failed: " + " | ".join(errors[-8:]))


def _fetch_roads_from_osm_map(latitude: float, longitude: float):
    """Live OSM fallback for major roads using small map tiles."""
    allowed = {
        "motorway", "motorway_link", "trunk", "trunk_link",
        "primary", "primary_link", "secondary", "secondary_link",
    }
    offsets = [(-0.045, -0.045), (-0.045, 0.045), (0.045, -0.045), (0.045, 0.045)]
    elements_by_id = {}
    errors = []

    for dlat, dlon in offsets:
        half_lat, half_lon = 0.045, 0.050
        center_lat = latitude + dlat
        center_lon = longitude + dlon
        left, bottom = center_lon - half_lon, center_lat - half_lat
        right, top = center_lon + half_lon, center_lat + half_lat
        bbox = f"{left:.6f},{bottom:.6f},{right:.6f},{top:.6f}"
        url = "https://api.openstreetmap.org/api/0.6/map?bbox=" + urllib.parse.quote(bbox, safe=",.-")
        try:
            req = urllib.request.Request(
                url,
                method="GET",
                headers={"User-Agent": USER_AGENT + " (road-exposure-fallback)"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"OSM map HTTP {response.status}")
                root = ET.fromstring(response.read())

            nodes = {}
            for node in root.findall("node"):
                try:
                    nodes[int(node.attrib["id"])] = (
                        float(node.attrib["lat"]),
                        float(node.attrib["lon"]),
                    )
                except (KeyError, ValueError):
                    continue

            for way in root.findall("way"):
                tags = {t.attrib.get("k"): t.attrib.get("v") for t in way.findall("tag")}
                if tags.get("highway") not in allowed:
                    continue
                coords = []
                for nd in way.findall("nd"):
                    ref = nd.attrib.get("ref")
                    if ref is not None and int(ref) in nodes:
                        coords.append(nodes[int(ref)])
                if not coords:
                    continue
                lat = sum(c[0] for c in coords) / len(coords)
                lon = sum(c[1] for c in coords) / len(coords)
                wid = int(way.attrib.get("id", 0))
                elements_by_id[wid] = {
                    "type": "way",
                    "id": wid,
                    "center": {"lat": lat, "lon": lon},
                    "tags": tags,
                }
            print(f"OSM road tile succeeded: bbox={bbox}, roads_so_far={len(elements_by_id)}")
        except Exception as exc:
            errors.append(f"bbox={bbox}: {exc}")
            print("OSM road tile failed:", bbox, exc)

    if not elements_by_id:
        raise RuntimeError("Live OSM road fallback returned no major roads; " + " | ".join(errors))

    return {
        "elements": list(elements_by_id.values()),
        "_cycloneshield_source": "osm_map_fallback",
        "_road_fallback_tiles": len(offsets),
    }


def _load_group(latitude, longitude, kind):
    payload = {
        "lat": round(latitude, 4),
        "lon": round(longitude, 4),
        "radius": SEARCH_RADIUS_METERS,
        "group": kind,
    }

    if kind == "roads":
        def loader():
            try:
                return query_overpass(build_overpass_query(latitude, longitude, kind))
            except Exception as overpass_exc:
                print("Road Overpass failed; trying live OSM map fallback:", overpass_exc)
                return _fetch_roads_from_osm_map(latitude, longitude)

        data, meta = cached_call("roads", payload, loader)
        if isinstance(data, dict) and data.get("_cycloneshield_source") == "osm_map_fallback":
            meta = dict(meta)
            meta["source"] = "live"
            meta["provider"] = "OpenStreetMap map API fallback"
        return data, meta

    return cached_call(
        f"overpass_{kind}",
        payload,
        lambda: query_overpass(build_overpass_query(latitude, longitude, kind)),
    )


def get_infrastructure_exposure(latitude: float, longitude: float):
    """Retrieve each infrastructure category independently.

    A failure in hospitals must not make roads, schools, substations or
    shelters disappear. Cached data is used only for the category that failed.
    """
    groups = ("hospitals", "schools", "power", "shelters", "roads")
    results = {}
    errors = []
    sources = []

    for kind in groups:
        try:
            data, meta = _load_group(latitude, longitude, kind)
            results[kind] = data
            sources.append({"group": kind, **meta})
        except Exception as exc:
            results[kind] = {"elements": []}
            errors.append(f"{kind}: {exc}")
            print(f"Infrastructure group unavailable: {kind}: {exc}")

    elements = []
    for data in results.values():
        elements.extend(data.get("elements", []))

    features = []
    seen = set()
    for element in elements:
        eid = f"{element.get('type')}-{element.get('id')}"
        if eid in seen:
            continue
        seen.add(eid)

        tags = element.get("tags", {})
        category = classify_infrastructure(tags)
        lat, lon = get_element_coordinates(element)
        if not category or lat is None or lon is None:
            continue

        dist = calculate_distance_km(latitude, longitude, float(lat), float(lon))
        exposure = (
            "Very High" if dist <= 2 else
            "High" if dist <= 5 else
            "Medium" if dist <= 8 else
            "Low"
        )
        defaults = {
            "Hospital": "Unnamed Hospital",
            "School": "Unnamed School",
            "Power Substation": "Unnamed Power Substation",
            "Major Road": "Unnamed Major Road",
            "Medical Shelter": "Unnamed Medical Shelter",
            "Medical Facility": "Unnamed Medical Facility",
        }
        features.append({
            "id": eid,
            "name": tags.get("name") or defaults.get(category, "Unnamed Infrastructure"),
            "type": category,
            "latitude": round(float(lat), 6),
            "longitude": round(float(lon), 6),
            "distance_km": round(dist, 2),
            "exposure": exposure,
            "osm_tags": tags,
        })

    limits = {
        "Hospital": 20,
        "School": 20,
        "Power Substation": 20,
        "Medical Shelter": 20,
        "Medical Facility": 20,
        "Major Road": 40,
    }
    grouped = {
        k: sorted(
            [x for x in features if x["type"] == k],
            key=lambda x: x["distance_km"],
        )
        for k in limits
    }

    selected = []
    for k, limit in limits.items():
        selected.extend(grouped[k][:limit])
    selected.sort(key=lambda x: x["distance_km"])

    summary = {
        "hospitals": len(grouped["Hospital"]),
        "schools": len(grouped["School"]),
        "power_substations": len(grouped["Power Substation"]),
        "major_roads": len(grouped["Major Road"]),
        "medical_shelters": len(grouped["Medical Shelter"]),
    }

    live_count = sum(1 for m in sources if m.get("source") == "live")
    cache_count = sum(1 for m in sources if m.get("source") == "cache")
    unavailable_groups = [
        group for group in groups
        if not results.get(group, {}).get("elements")
    ]

    if live_count and not cache_count and not unavailable_groups:
        source = "live"
    elif live_count or cache_count:
        source = "live+cache" if live_count else "cache"
    else:
        source = "partial" if features else "unavailable"

    note = "Counts are mapped OpenStreetMap features, not a complete official inventory."
    if cache_count:
        note += " One or more categories used stale cached data because live retrieval failed."
    if unavailable_groups:
        note += " Unavailable categories: " + ", ".join(unavailable_groups) + "."
    if errors:
        note += " Provider errors were isolated by category so available groups remain usable."

    status = "success" if features else "unavailable"
    return {
        "status": status,
        "data_status": source,
        "radius_km": 10.0,
        "total": len(selected),
        "summary": summary,
        "features": selected,
        "mapped_feature_counts": summary,
        "note": note,
        "group_status": {
            group: ("available" if results.get(group, {}).get("elements") else "unavailable")
            for group in groups
        },
        "sources": sources,
        "errors": errors,
    }
