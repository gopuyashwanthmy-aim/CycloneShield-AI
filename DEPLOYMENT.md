# CycloneShield AI v2.6.1 — Cloud Run Deployment

This deployment layer keeps the validated v2.6 application logic intact, with category-isolated infrastructure retrieval hardening.

## Architecture

Browser
→ Cloud Run frontend (React/Vite + Nginx)
→ `/api/*` reverse proxy
→ Cloud Run backend (FastAPI)
→ Gemini + Earth Engine + Open-Meteo + OpenStreetMap

The frontend uses a same-origin `/api` path in production, reverse-proxied by Nginx to the deployed backend, so browser CORS is not required between the public frontend and backend.

## 0. Project

Google Cloud project:

```text
gen-lang-client-0849641374
```

Recommended region:

```text
asia-south1
```

Use another region if your hackathon/account setup requires it.

## 1. Enable APIs

From the project root:

```cmd
gcloud config set project gen-lang-client-0849641374

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

## 2. Backend deployment

From the project root:

```cmd
gcloud run deploy cycloneshield-backend ^
  --source . ^
  --region asia-south1 ^
  --allow-unauthenticated ^
  --memory 2Gi ^
  --cpu 2 ^
  --timeout 300 ^
  --min 0 ^
  --max 3 ^
  --set-env-vars "DEMO_MODE=0,GEMINI_MODEL=gemini-3.7-flash,GEMINI_MAX_ATTEMPTS=2,CYCLONESHIELD_CACHE_TTL=21600"
```

### Gemini secret

Do NOT commit `.env` or the Gemini key.

For the first deployment, set the Gemini key through Cloud Run's environment-variable/Secret Manager configuration rather than placing it in source control.

Preferred production approach:

1. Create a Secret Manager secret containing the Gemini API key.
2. Grant the Cloud Run runtime service account access to that secret.
3. Attach the secret to the backend as `GEMINI_API_KEY`.

If Gemini is temporarily unavailable, the deterministic CycloneShield pipeline remains independent of Gemini; the UI already reports Gemini availability limitations.

## 3. Earth Engine runtime identity

Cloud Run uses Application Default Credentials (ADC) for unattended Google API access.

The Cloud Run runtime service account must have Earth Engine access on the registered Earth Engine project. At minimum, Google documents the combination of:

```text
roles/earthengine.viewer
roles/serviceusage.serviceUsageConsumer
```

Grant these to the Cloud Run runtime service account if needed.

Then verify the backend logs for:

```text
SRTM result:
Dynamic World
FINAL GEOSPATIAL RESULT:
```

Do NOT upload an Earth Engine private-key JSON file into the repository.

## 4. Capture the backend URL

After backend deployment:

```cmd
gcloud run services describe cycloneshield-backend ^
  --region asia-south1 ^
  --format="value(status.url)"
```

Copy the returned URL.

Example shape:

```text
https://cycloneshield-backend-xxxxx-xx.a.run.app
```

## 5. Frontend deployment

The checked-in `frontend/nginx.conf.template` contains the validated backend Cloud Run URL and the Dockerfile installs it as the deterministic Nginx configuration. This avoids runtime `BACKEND_URL`/`envsubst` issues.

Deploy from the `frontend` directory:

```cmd
cd frontend

gcloud run deploy cycloneshield-frontend ^
  --source . ^
  --region asia-south1 ^
  --allow-unauthenticated ^
  --memory 512Mi ^
  --cpu 1
```

## 6. Get the public frontend URL

```cmd
gcloud run services describe cycloneshield-frontend ^
  --region asia-south1 ^
  --format="value(status.url)"
```

That frontend URL is the submission/demo URL.

## 7. Production smoke test

Open:

```text
https://YOUR-FRONTEND-URL/
```

Then:

1. Confirm the dashboard loads.
2. Run the default Chennai scenario.
3. Confirm `/api/analyze` returns the assessment.
4. Confirm Earth Engine data is shown as live/unavailable rather than fabricated.
5. Confirm infrastructure data status is visible.
6. Confirm Gemini text/multimodal output when quota/service is available.
7. Click **Simulate Authority Dispatch**.
8. Confirm the dispatch log appears.
9. Refresh the browser and run the assessment again.

Backend health endpoint:

```text
https://YOUR-BACKEND-URL/health
```

Expected shape:

```json
{
  "status": "healthy",
  "service": "CycloneShield AI",
  "demo_mode": false
}
```

## Important

This is a deployment configuration for the validated v2.6 prototype. It does not change the scientific positioning:

- storm surge = prototype screening, not hydrodynamic forecasting
- rainfall pathways = relative screening
- infrastructure = mapped OSM inventory, not complete official inventory
- vulnerability = transparent potential-impact model, not structural engineering
- insurance = illustrative liquidity scenario, not an insurance policy
- advisory/dispatch = simulated workflow, not an official emergency alert

For the hackathon, present the deployed URL as a working decision-support prototype.
