# CycloneShield AI — Integrated Prototype

CycloneShield AI is an AI-assisted pre-landfall cyclone impact and vulnerability assessment platform. It combines Google Earth Engine geospatial indicators, mapped infrastructure exposure, meteorological context, hazard-pathway screening, vulnerability scoring, evacuation planning, infrastructure-hardening checklists, illustrative parametric-liquidity scenarios, early-warning advisory generation, and Gemini reasoning.

## Coverage of the challenge

- **GEE satellite/geospatial feeds:** SRTM elevation, Dynamic World land cover and Earth Engine rainfall where available.
- **Meteorological intelligence:** current/forecast context from Open-Meteo plus explicit user-entered cyclone scenarios. The feed is labelled as current/forecast rather than an official warning.
- **Storm surge:** prototype bathtub-style coastal inundation screening using the existing hazard engine.
- **Rainfall damage pathways:** relative flow-path screening using the existing HydroSHEDS/SRTM-based engine.
- **Critical infrastructure:** hospitals, schools, power substations, major roads and mapped shelter-like facilities from OpenStreetMap/Overpass.
- **Evacuation planning:** prioritization, candidate shelter discovery and route-risk screening.
- **Infrastructure hardening:** sector checklists for power, healthcare, roads and schools.
- **Parametric insurance/liquidity:** configurable illustrative trigger/payout scenario; not a real insurance product.
- **Early warning:** advisory generation and simulated authority dispatch workflow. No message is sent externally.
- **Gemini multimodal:** Gemini receives structured scenario information and a generated hazard-map image when a Gemini API key is configured.
- **Resilience:** cached Overpass/weather results, safe missing-data handling and deterministic fallback when Gemini is unavailable.

## Important scientific / operational limitations

This is a decision-support prototype. Storm surge is not a hydrodynamic forecast and does not model tides, waves or detailed bathymetry. Rainfall pathways are screening indicators rather than drainage/runoff forecasts. Infrastructure vulnerability is a transparent potential-impact model, not structural engineering analysis. OSM is a mapped-data source and is not a complete official infrastructure inventory. Parametric insurance outputs are illustrative. Official warnings, evacuation orders and emergency actions must come from authorized agencies.

## Run locally

### Backend

```cmd
cd /d "D:\yash\CycloneShield AI"
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Keep your existing `.env` in the project root. At minimum:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.7-flash
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Earth Engine authentication must already be configured for the Google Cloud project.

### Frontend

```cmd
cd /d "D:\yash\CycloneShield AI\frontend"
npm install
npm run dev
```

The frontend uses `VITE_API_URL` if provided; otherwise it calls `http://127.0.0.1:8000`.

## Full integration smoke test

For a dependency-independent pipeline check, temporarily run the backend with demo mode:

```cmd
set DEMO_MODE=1
python -m uvicorn backend.main:app --reload
```

Then run the complete assessment from the UI. Demo mode bypasses external GEE/Overpass calls while exercising the complete orchestration: meteorology → hazards → vulnerability → decision support → evacuation → hardening → liquidity → advisory → Gemini fallback/multimodal layer.

For the real demonstration, unset `DEMO_MODE` and use the authenticated Google Earth Engine environment.


## Real-data validation
Run the backend with `DEMO_MODE` unset or set to `0` for Earth Engine, Open-Meteo and OpenStreetMap/Overpass retrieval. Overpass and weather results use the built-in cache when a transient upstream failure occurs. Demo mode is intended only for deterministic pipeline smoke tests.



## v2.6.1 infrastructure reliability fix
Infrastructure retrieval is now split by category (hospitals, schools, power substations, shelters and roads). A timeout or rate-limit in one OpenStreetMap/Overpass category no longer clears the other categories. Each category independently uses live retrieval first and its own stale cache as fallback; major roads retain the OpenStreetMap map-API fallback.

## v2.2 resilience behavior
Infrastructure retrieval is split into core assets and major roads. Each group is cached independently. If an Overpass provider times out, a previously cached group may be reused; the API reports `live`, `cache`, or `live+cache` status instead of converting a provider outage into zero infrastructure. If no live or cached data exists, the UI explicitly reports that infrastructure assessment was not performed.

## v2.3 final-validation behavior
Storm-surge coastal proximity now uses the same live → cache → unavailable pattern. Successful Overpass coastline geometry is persisted by location. If Overpass returns a 429/5xx or times out, a cached coastline can be reused. If neither is available, Google Earth Engine JRC Global Surface Water is attempted as a mapped surface-water proximity fallback. The API exposes `screening_status` (`live_coastline`, `cached_coastline`, `surface_water_fallback`, or `unavailable`) so zero screened cells are not misrepresented as a confirmed zero-inundation result.


## v2.3 final validation
The final-validation UI distinguishes a genuine zero-cell storm-surge screening result from an unavailable coastal-data run. Infrastructure totals are explicitly separated from the smaller detailed impact-assessment set and the hazard-affected assessed set. Gemini prompts distinguish user-entered scenario assumptions, retrieved data, modelled screening outputs and contextual AI reasoning; Gemini is instructed not to invent site-specific facilities, waterways, population counts, flood depths, engineering thresholds or official actions.

For a final demo, verify the external data-status labels and run one complete real-data assessment. If an upstream service is unavailable, present the resulting cached/unavailable status rather than interpreting missing data as zero exposure.


## Cloud Run deployment

The repository includes a production deployment layer:

- `Dockerfile` — FastAPI backend container.
- `frontend/Dockerfile` — React/Vite build served by Nginx.
- `frontend/nginx.conf.template` — same-origin `/api` reverse proxy.
- `DEPLOYMENT.md` — Google Cloud Run deployment and Earth Engine runtime setup.

The production frontend does not require a hard-coded backend URL. Nginx receives the backend Cloud Run URL through the `BACKEND_URL` runtime variable.

Never commit `.env`, Gemini API keys, Earth Engine private keys, or service-account JSON files.
