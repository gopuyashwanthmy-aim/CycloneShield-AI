from __future__ import annotations

import os
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.earth_engine_service import get_geospatial_features
from backend.infrastructure_service import get_infrastructure_exposure
from backend.vulnerability_service import calculate_infrastructure_vulnerability
from backend.decision_support_service import generate_decision_support
from backend.hazard_simulation_service import simulate_hazard_pathways
from backend.meteorology_service import get_meteorological_intelligence
from backend.evacuation_service import generate_evacuation_plan, generate_hardening_plan
from backend.insurance_service import calculate_parametric_liquidity
from backend.advisory_service import generate_advisory, simulate_dispatch
from backend.gemini_service import analyze_cyclone, analyze_multimodal
from backend.multimodal_service import build_hazard_map_png

app = FastAPI(title="CycloneShield AI", version="2.6.1")
app.add_middleware(CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class CycloneRequest(BaseModel):
    cyclone_name: str = Field(min_length=1, max_length=120)
    wind_speed: float = Field(ge=0, le=400)
    rainfall: float = Field(ge=0, le=2000)
    location: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    surge_height_m: float = Field(default=3.0, ge=0, le=20)


def calculate_risk_score(wind_speed: float, rainfall: float) -> int:
    return round(min(wind_speed / 150 * 50, 50) + min(rainfall / 300 * 50, 50))


def demo_geospatial(lat, lon):
    return {"latitude":lat,"longitude":lon,"elevation_meters":8.5,"land_cover":"Built Area","built_probability":0.72,"water_probability":0.06,"land_cover_date":"2026-09-01","recent_precipitation_mm":18.4,"precipitation_date":"2026-09-21","data_status":"demo"}


def demo_infrastructure(lat, lon):
    features=[]
    kinds=[("Hospital",1.1),("School",2.4),("Power Substation",3.1),("Major Road",1.8),("Medical Shelter",4.2)]
    for i,(kind,d) in enumerate(kinds):
        features.append({"id":f"demo-{i}","name":f"Demo {kind} {i+1}","type":kind,"latitude":lat+(i+1)*0.002,"longitude":lon+(i+1)*0.002,"distance_km":d,"exposure":"Very High" if d<=2 else "High" if d<=5 else "Medium","osm_tags":{}})
    return {"status":"success","data_status":"demo","radius_km":10,"total":len(features),"summary":{"hospitals":1,"schools":1,"power_substations":1,"major_roads":1,"medical_shelters":1},"features":features,"note":"Demo mode: external infrastructure feed bypassed."}


def demo_hazard(req, infra):
    affected=infra["features"][:3] if req.surge_height_m >= 3 else infra["features"][:1]
    return {"status":"success","storm_surge":{"scenario_surge_height_m":req.surge_height_m,"inundated_cells":7 if req.surge_height_m>=4 else 3,"coastline_data_available":True,"method":"Demo bathtub-style screening","note":"Demo mode."},"rainfall_pathways":{"scenario_rainfall_mm":req.rainfall,"high_pathway_cells":2 if req.rainfall>=200 else 1,"medium_pathway_cells":4,"method":"Demo relative flow-path screening","note":"Demo mode."},"cells":[],"affected_assets":affected,"affected_asset_count":len(affected),"data_sources":["Demo hazard grid"]}


def safe_geo(req):
    if os.getenv("DEMO_MODE", "0") == "1": return demo_geospatial(req.latitude, req.longitude)
    try: return get_geospatial_features(req.latitude, req.longitude)
    except Exception as exc: return {"latitude":req.latitude,"longitude":req.longitude,"elevation_meters":None,"land_cover":None,"built_probability":None,"water_probability":None,"land_cover_date":None,"recent_precipitation_mm":None,"precipitation_date":None,"data_status":"unavailable","error":str(exc)}


def safe_infra(req):
    if os.getenv("DEMO_MODE", "0") == "1": return demo_infrastructure(req.latitude, req.longitude)
    try: return get_infrastructure_exposure(req.latitude, req.longitude)
    except Exception as exc: return {"status":"unavailable","data_status":"unavailable","radius_km":10,"total":0,"summary":{"hospitals":0,"schools":0,"power_substations":0,"major_roads":0,"medical_shelters":0},"features":[],"error":str(exc)}


def safe_hazard(req, infra):
    if os.getenv("DEMO_MODE", "0") == "1": return demo_hazard(req, infra)
    try: return simulate_hazard_pathways(req.latitude, req.longitude, req.wind_speed, req.rainfall, req.surge_height_m, infra)
    except Exception as exc: return {"status":"unavailable","storm_surge":{"scenario_surge_height_m":req.surge_height_m,"inundated_cells":0,"screening_status":"unavailable","coastline_data_available":False,"method":"Unavailable","note":"Storm-surge screening unavailable because coastal/surface-water proximity data could not be retrieved."},"rainfall_pathways":{"scenario_rainfall_mm":req.rainfall,"high_pathway_cells":0,"medium_pathway_cells":0,"method":"Unavailable","note":"Rainfall pathway screening unavailable."},"cells":[],"affected_assets":[],"affected_asset_count":0,"data_sources":[],"error":str(exc)}


@app.get("/")
def home(): return {"message":"CycloneShield AI backend is running!","version":"2.6.1"}

@app.get("/health")
def health(): return {"status":"healthy","service":"CycloneShield AI","demo_mode":os.getenv("DEMO_MODE","0")=="1"}

@app.post("/advisory/dispatch")
def dispatch(payload: dict):
    advisory=payload.get("advisory")
    if not advisory: raise HTTPException(400,"advisory is required")
    return simulate_dispatch(advisory, payload.get("channel","simulation"), payload.get("recipients",[]))

@app.post("/analyze")
def analyze(request: CycloneRequest):
    risk_score=calculate_risk_score(request.wind_speed, request.rainfall)
    geospatial=safe_geo(request)
    infrastructure=safe_infra(request)
    hazard=safe_hazard(request, infrastructure)
    vulnerability=calculate_infrastructure_vulnerability(infrastructure, request.wind_speed, request.rainfall, geospatial)
    decision=generate_decision_support(request.wind_speed, request.rainfall, geospatial, infrastructure, vulnerability, risk_score)
    meteorology=get_meteorological_intelligence(request.latitude, request.longitude, request.wind_speed, request.rainfall)
    evacuation=generate_evacuation_plan(request.latitude, request.longitude, vulnerability, infrastructure, hazard, meteorology)
    hardening=generate_hardening_plan(infrastructure, vulnerability, hazard)
    insurance=calculate_parametric_liquidity(request.wind_speed, request.rainfall, request.surge_height_m, infrastructure, vulnerability)
    advisory=generate_advisory(request, risk_score, vulnerability, hazard, evacuation, meteorology)

    # Keep the deterministic pipeline independent from Gemini.
    surge = hazard.get("storm_surge", {})
    prompt=(
        f"You are the AI reasoning layer of CycloneShield AI. Analyze this cyclone-impact scenario for {request.location}. "
        f"USER-ENTERED SCENARIO: risk={risk_score}/100; wind={request.wind_speed} km/h; rainfall={request.rainfall} mm; surge={request.surge_height_m} m. "
        f"RETRIEVED/MODELED EVIDENCE: Earth Engine elevation={geospatial.get('elevation_meters')}; "
        f"built probability={geospatial.get('built_probability')}; infrastructure mapped totals={infrastructure.get('summary')}; "
        f"detailed assessed assets={vulnerability.get('total_assessed')}; hazard-affected assessed assets={hazard.get('affected_asset_count')}; "
        f"rainfall high-pathway cells={hazard.get('rainfall_pathways', {}).get('high_pathway_cells')}; "
        f"storm-surge screening status={surge.get('screening_status')}; storm-surge screened cells={surge.get('inundated_cells')}. "
        "IMPORTANT EVIDENCE RULES: Treat user-entered scenario values as scenario assumptions, not observations. "
        "Treat Earth Engine, Open-Meteo and OpenStreetMap values as retrieved data. Treat surge, rainfall pathways, vulnerability, risk and evacuation/hardening/insurance outputs as modelled screening estimates. "
        "If storm-surge screening status is 'unavailable', do not claim that zero cells means zero inundation and do not invent coastal exposure results. "
        "You may provide general contextual mechanisms or planning considerations, but clearly label them as contextual reasoning when they are not directly supported by the supplied data. "
        "Do not invent named facilities, waterways, reservoirs, population counts, flood depths, engineering thresholds or official actions. "
        "Separate evidence, modelled interpretation, uncertainty and contextual planning considerations. Do not issue official warnings or evacuation orders.")
    ai_text=analyze_cyclone(prompt)
    image=build_hazard_map_png(request.latitude, request.longitude, risk_score, hazard, infrastructure)
    multimodal_prompt=(prompt + "\nA generated hazard overview image is attached. Use it as an additional visual input. Distinguish modeled screening from observed/official information.")
    multimodal=analyze_multimodal(multimodal_prompt, image)

    return {
        "cyclone":{"name":request.cyclone_name,"wind_speed":request.wind_speed,"rainfall":request.rainfall,"surge_height_m":request.surge_height_m},
        "location":request.location,"coordinates":{"latitude":request.latitude,"longitude":request.longitude},"risk_score":risk_score,
        "geospatial":geospatial,"meteorology":meteorology,"infrastructure":infrastructure,"vulnerability":vulnerability,
        "hazard_simulation":hazard,"decision_support":decision,"evacuation_planning":evacuation,"infrastructure_hardening":hardening,
        "parametric_insurance":insurance,"early_warning_advisory":advisory,
        "analysis":ai_text,"multimodal_analysis":multimodal,
        "system_metadata":{"architecture_version":"2.6","demo_mode":os.getenv("DEMO_MODE","0")=="1","scenario_source":"user_entered_scenario","meteorology_source":meteorology.get("provider"),"infrastructure_source":infrastructure.get("data_status"),"official_warning_disclaimer":"This platform is a decision-support prototype. Official warnings, evacuation orders and emergency actions must come from authorized agencies."}
    }
