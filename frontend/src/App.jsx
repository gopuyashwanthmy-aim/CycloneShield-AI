import { useMemo, useState } from 'react'
import {
  Circle,
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  useMap,
} from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

/*
 * Production:
 * Always use the same-origin /api proxy configured in nginx.
 *
 * Development:
 * Use VITE_API_URL if provided, otherwise localhost backend.
 */
const API_URL = import.meta.env.PROD
  ? '/api'
  : (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000')

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })

  const contentType = response.headers.get('content-type') || ''

  let body

  if (contentType.includes('application/json')) {
    body = await response.json()
  } else {
    body = await response.text()
  }

  if (!response.ok) {
    const message =
      typeof body === 'object' && body?.detail
        ? body.detail
        : typeof body === 'string' && body
          ? body
          : `Request failed with HTTP ${response.status}`

    throw new Error(message)
  }

  return body
}

function FitMap({ center }) {
  const map = useMap()
  map.setView(center, 11)
  return null
}

function Card({ title, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      <h2>{title}</h2>
      {children}
    </section>
  )
}

function Metric({ label, value, sub }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {sub && <small>{sub}</small>}
    </div>
  )
}

function List({ items = [] }) {
  return (
    <ul className="list">
      {items.map((x, i) => (
        <li key={i}>
          {typeof x === 'string' ? (
            x
          ) : (
            <>
              <b>{x.title || x.sector || x.category || 'Action'}</b>
              {x.action && <> — {x.action}</>}
              {x.reason && <small>{x.reason}</small>}
            </>
          )}
        </li>
      ))}
    </ul>
  )
}

export default function App() {
  const [form, setForm] = useState({
    cyclone_name: 'CycloneShield Scenario',
    wind_speed: 160,
    rainfall: 220,
    location: 'Chennai, India',
    latitude: 13.0837,
    longitude: 80.2702,
    surge_height_m: 4,
  })

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [dispatch, setDispatch] = useState(null)

  const set = (key, value) => {
    setForm((current) => ({
      ...current,
      [key]: value,
    }))
  }

  const analyze = async () => {
    if (loading) return

    setLoading(true)
    setError('')
    setDispatch(null)

    try {
      const payload = {
        ...form,
        wind_speed: Number(form.wind_speed),
        rainfall: Number(form.rainfall),
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        surge_height_m: Number(form.surge_height_m),
      }

      const result = await apiRequest('/analyze', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      setData(result)
    } catch (e) {
      console.error('CycloneShield analysis error:', e)

      if (e instanceof TypeError) {
        setError(
          'Unable to connect to the CycloneShield API. Please refresh the page and try again.'
        )
      } else {
        setError(e?.message || 'Analysis failed')
      }
    } finally {
      setLoading(false)
    }
  }

  const sendDispatch = async () => {
    if (!data) return

    setError('')

    try {
      const result = await apiRequest('/advisory/dispatch', {
        method: 'POST',
        body: JSON.stringify({
          advisory: data.early_warning_advisory,
          channel: 'simulation',
          recipients: [
            'Municipal disaster management',
            'Emergency operations',
          ],
        }),
      })

      setDispatch(result)
    } catch (e) {
      console.error('CycloneShield dispatch error:', e)

      if (e instanceof TypeError) {
        setError(
          'Unable to connect to the dispatch API. Please try again.'
        )
      } else {
        setError(e?.message || 'Dispatch simulation failed')
      }
    }
  }

  const center = useMemo(
    () =>
      data
        ? [data.coordinates.latitude, data.coordinates.longitude]
        : [Number(form.latitude), Number(form.longitude)],
    [data, form.latitude, form.longitude]
  )

  const risk = data?.risk_score ?? 0

  const baseRadius = 20000 + risk * 800

  const zones = [
    {
      n: 'Outer',
      r: baseRadius,
    },
    {
      n: 'Medium',
      r: Math.min(50000, baseRadius * 0.7),
    },
    {
      n: 'High',
      r: Math.min(35000, baseRadius * 0.45),
    },
    {
      n: 'Very High',
      r: Math.min(18000, baseRadius * 0.2),
    },
  ]

  const vuln = data?.vulnerability
  const infra = data?.infrastructure
  const hazard = data?.hazard_simulation
  const decision = data?.decision_support

  return (
    <div className="app">
      <header>
        <div>
          <div className="eyebrow">
            GOOGLE CLOUD • EARTH ENGINE • GEMINI
          </div>

          <h1>🌪️ CycloneShield AI</h1>

          <p>
            Pre-landfall risk, vulnerability, hazard pathway and
            anticipatory-action intelligence.
          </p>
        </div>

        <div className="badge">
          Decision-support prototype
        </div>
      </header>

      <main>
        <Card title="Scenario Input" className="input-card">
          <div className="form-grid">
            <label>
              Cyclone name
              <input
                value={form.cyclone_name}
                onChange={(e) =>
                  set('cyclone_name', e.target.value)
                }
              />
            </label>

            <label>
              Location
              <input
                value={form.location}
                onChange={(e) =>
                  set('location', e.target.value)
                }
              />
            </label>

            <label>
              Wind speed (km/h)
              <input
                type="number"
                value={form.wind_speed}
                onChange={(e) =>
                  set('wind_speed', e.target.value)
                }
              />
            </label>

            <label>
              Rainfall (mm)
              <input
                type="number"
                value={form.rainfall}
                onChange={(e) =>
                  set('rainfall', e.target.value)
                }
              />
            </label>

            <label>
              Latitude
              <input
                type="number"
                step="any"
                value={form.latitude}
                onChange={(e) =>
                  set('latitude', e.target.value)
                }
              />
            </label>

            <label>
              Longitude
              <input
                type="number"
                step="any"
                value={form.longitude}
                onChange={(e) =>
                  set('longitude', e.target.value)
                }
              />
            </label>

            <label>
              Scenario surge (m)
              <input
                type="number"
                step="0.1"
                value={form.surge_height_m}
                onChange={(e) =>
                  set('surge_height_m', e.target.value)
                }
              />
            </label>
          </div>

          <button
            onClick={analyze}
            disabled={loading}
          >
            {loading
              ? 'Running complete assessment…'
              : 'Run Complete Cyclone Assessment'}
          </button>

          {error && (
            <div className="error">
              {error}
            </div>
          )}
        </Card>

        {data && (
          <>
            <div className="metrics">
              <Metric
                label="Risk score"
                value={`${risk}/100`}
                sub={
                  risk >= 75
                    ? 'Very High'
                    : risk >= 55
                      ? 'High'
                      : risk >= 35
                        ? 'Medium'
                        : 'Low'
                }
              />

              <Metric
                label="Assets assessed"
                value={vuln?.total_assessed ?? 0}
              />

              <Metric
                label="Average impact"
                value={`${vuln?.overall_score ?? 0}/100`}
                sub={vuln?.overall_level}
              />

              <Metric
                label="Hazard-affected assets"
                value={hazard?.affected_asset_count ?? 0}
              />

              <Metric
                label="Surge screening"
                value={
                  hazard?.storm_surge?.screening_status ===
                  'unavailable'
                    ? 'Unavailable'
                    : (
                        hazard?.storm_surge?.inundated_cells ??
                        0
                      )
                }
              />

              <Metric
                label="Rainfall pathways"
                value={
                  hazard?.rainfall_pathways
                    ?.high_pathway_cells ?? 0
                }
              />
            </div>

            <Card title="Scenario Used">
              <div className="mini-grid">
                <Metric
                  label="Cyclone"
                  value={data.cyclone?.name}
                />

                <Metric
                  label="Wind"
                  value={`${data.cyclone?.wind_speed} km/h`}
                />

                <Metric
                  label="Rainfall"
                  value={`${data.cyclone?.rainfall} mm`}
                />

                <Metric
                  label="Surge"
                  value={`${data.cyclone?.surge_height_m} m`}
                />
              </div>

              <p className="note">
                These are the exact user-entered scenario values
                used by the risk, hazard, advisory and insurance
                calculations.
              </p>
            </Card>

            <div className="two">
              <Card title="Meteorological Intelligence">
                <div className="mini-grid">
                  <Metric
                    label="Current wind"
                    value={
                      data.meteorology?.current
                        ?.wind_speed_kmh ?? 'Unavailable'
                    }
                    sub="km/h"
                  />

                  <Metric
                    label="Current rain"
                    value={
                      data.meteorology?.current
                        ?.precipitation_mm ?? 'Unavailable'
                    }
                    sub="mm"
                  />

                  <Metric
                    label="Feed"
                    value={
                      data.meteorology?.data_status ||
                      'Unavailable'
                    }
                    sub={
                      data.meteorology?.provider || ''
                    }
                  />

                  <Metric
                    label="Scenario wind/current"
                    value={
                      data.meteorology?.scenario
                        ?.wind_vs_current_ratio
                        ? `${data.meteorology.scenario.wind_vs_current_ratio}×`
                        : '—'
                    }
                  />
                </div>

                <p className="note">
                  Observed/current and forecast feed data are
                  separated from the user-entered scenario. This
                  is not an official cyclone warning.
                </p>
              </Card>

              <Card title="Earth Engine Geospatial">
                <div className="mini-grid">
                  <Metric
                    label="Elevation"
                    value={
                      data.geospatial?.elevation_meters ??
                      'Unavailable'
                    }
                    sub="m"
                  />

                  <Metric
                    label="Built probability"
                    value={
                      data.geospatial?.built_probability != null
                        ? `${(
                            data.geospatial.built_probability *
                            100
                          ).toFixed(1)}%`
                        : 'Unavailable'
                    }
                  />

                  <Metric
                    label="Water probability"
                    value={
                      data.geospatial?.water_probability != null
                        ? `${(
                            data.geospatial.water_probability *
                            100
                          ).toFixed(1)}%`
                        : 'Unavailable'
                    }
                  />

                  <Metric
                    label="Land cover"
                    value={
                      data.geospatial?.land_cover ||
                      'Unavailable'
                    }
                  />
                </div>
              </Card>
            </div>

            <Card title="Storm Surge & Rainfall Damage Pathways">
              <div className="two">
                <div>
                  <h3>Storm surge</h3>

                  <p>
                    <b>
                      {
                        hazard?.storm_surge
                          ?.scenario_surge_height_m
                      }{' '}
                      m
                    </b>{' '}
                    scenario •{' '}
                    <b>
                      {hazard?.storm_surge
                        ?.screening_status ===
                      'unavailable'
                        ? 'Spatial screening unavailable'
                        : `${hazard?.storm_surge?.inundated_cells ?? 0} screened cells`}
                    </b>
                  </p>

                  <p>
                    {hazard?.storm_surge?.method}
                  </p>

                  <p>
                    <b>Screening status:</b>{' '}
                    {hazard?.storm_surge?.screening_status ||
                      'unknown'}
                  </p>

                  <small>
                    {hazard?.storm_surge?.note}
                  </small>
                </div>

                <div>
                  <h3>Rainfall pathways</h3>

                  <p>
                    <b>
                      {
                        hazard?.rainfall_pathways
                          ?.scenario_rainfall_mm
                      }{' '}
                      mm
                    </b>{' '}
                    scenario •{' '}
                    <b>
                      {
                        hazard?.rainfall_pathways
                          ?.high_pathway_cells
                      }
                    </b>{' '}
                    high pathways
                  </p>

                  <p>
                    {hazard?.rainfall_pathways?.method}
                  </p>

                  <small>
                    {hazard?.rainfall_pathways?.note}
                  </small>
                </div>
              </div>
            </Card>

            <Card title="Infrastructure Exposure">
              <div className="metrics">
                <Metric
                  label="Hospitals"
                  value={infra?.summary?.hospitals ?? 0}
                />

                <Metric
                  label="Schools"
                  value={infra?.summary?.schools ?? 0}
                />

                <Metric
                  label="Power substations"
                  value={
                    infra?.summary?.power_substations ?? 0
                  }
                />

                <Metric
                  label="Major roads"
                  value={
                    infra?.summary?.major_roads ?? 0
                  }
                />

                <Metric
                  label="Medical shelters"
                  value={
                    infra?.summary?.medical_shelters ?? 0
                  }
                />
              </div>

              <p className="note">
                {infra?.note} Data status:{' '}
                <b>
                  {infra?.data_status || 'unknown'}
                </b>.
              </p>

              <p className="note">
                Mapped infrastructure totals are the live/cached
                inventory in the search area.{' '}
                <b>{vuln?.total_assessed ?? 0}</b> assets are
                selected for detailed impact assessment, and{' '}
                <b>{hazard?.affected_asset_count ?? 0}</b>{' '}
                assessed assets intersect simulated hazard
                screening. These counts are different by design.
              </p>
            </Card>

            <div className="two">
              <Card title="Evacuation Planning">
                <Metric
                  label="Planning priority"
                  value={
                    data.evacuation_planning
                      ?.planning_priority
                  }
                />

                <p>
                  High-priority assets:{' '}
                  <b>
                    {
                      data.evacuation_planning
                        ?.high_priority_assets
                    }
                  </b>
                </p>

                <p>
                  Candidate shelters:{' '}
                  <b>
                    {
                      data.evacuation_planning
                        ?.candidate_shelters?.length ?? 0
                    }
                  </b>
                </p>

                <List
                  items={
                    data.evacuation_planning
                      ?.evacuation_actions
                  }
                />
              </Card>

              <Card title="Infrastructure Hardening">
                <List
                  items={data.infrastructure_hardening?.sector_plans?.flatMap(
                    (x) =>
                      x.actions.map((a) => ({
                        sector: x.sector,
                        action: a,
                      }))
                  )}
                />

                <p className="note">
                  {data.infrastructure_hardening?.note}
                </p>
              </Card>
            </div>

            <div className="two">
              <Card title="Parametric Insurance & Liquidity">
                <div className="mini-grid">
                  <Metric
                    label="Trigger"
                    value={
                      data.parametric_insurance?.triggered
                        ? 'YES'
                        : 'NO'
                    }
                  />

                  <Metric
                    label="Illustrative payout"
                    value={`${(data.parametric_insurance?.illustrative_payout_rate ?? 0) * 100}%`}
                  />

                  <Metric
                    label="Illustrative liquidity"
                    value={`₹${Number(
                      data.parametric_insurance
                        ?.illustrative_liquidity_inr || 0
                    ).toLocaleString('en-IN')}`}
                  />

                  <Metric
                    label="Exposed value"
                    value={`₹${Number(
                      data.parametric_insurance
                        ?.estimated_exposed_value_inr || 0
                    ).toLocaleString('en-IN')}`}
                  />
                </div>

                <p className="note">
                  {data.parametric_insurance?.disclaimer}
                </p>
              </Card>

              <Card title="Early-Warning Advisory">
                <span
                  className={`severity ${data.early_warning_advisory?.severity}`}
                >
                  {data.early_warning_advisory?.severity}
                </span>

                <h3>
                  {data.early_warning_advisory?.headline}
                </h3>

                <p>
                  {data.early_warning_advisory?.message}
                </p>

                <List
                  items={
                    data.early_warning_advisory
                      ?.recommended_actions
                  }
                />

                <button
                  className="secondary"
                  onClick={sendDispatch}
                >
                  Simulate Authority Dispatch
                </button>

                {dispatch && (
                  <div className="success">
                    Dispatch simulated:{' '}
                    {
                      dispatch.dispatch_log?.at(-1)
                        ?.dispatch_id
                    }
                  </div>
                )}
              </Card>
            </div>

            <Card title="Risk Zones & Infrastructure Map">
              <div className="map-wrap">
                <MapContainer
                  center={center}
                  zoom={11}
                  scrollWheelZoom
                >
                  <FitMap center={center} />

                  <TileLayer
                    attribution="© OpenStreetMap contributors"
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  {zones.map((z, i) => (
                    <Circle
                      key={z.n}
                      center={center}
                      radius={z.r}
                      pathOptions={{
                        fillOpacity: 0.04 + i * 0.02,
                        weight: 2,
                      }}
                    />
                  ))}

                  <CircleMarker
                    center={center}
                    radius={9}
                  >
                    <Popup>
                      Assessment center
                      <br />
                      Risk {risk}/100
                    </Popup>
                  </CircleMarker>

                  {(vuln?.assets || []).map((a) => (
                    <CircleMarker
                      key={a.id}
                      center={[
                        a.latitude,
                        a.longitude,
                      ]}
                      radius={6}
                    >
                      <Popup>
                        <b>{a.name}</b>
                        <br />
                        {a.type}
                        <br />
                        Impact: {a.impact_score}/100 (
                        {a.impact_level})
                        <br />
                        Distance: {a.distance_km} km
                      </Popup>
                    </CircleMarker>
                  ))}
                </MapContainer>
              </div>

              <div className="legend">
                Visualization only: circles are prototype
                assessment zones, not official warning boundaries.
              </div>
            </Card>

            <div className="two">
              <Card title="Gemini AI Analysis">
                <p className="ai">
                  {data.analysis}
                </p>

                <p className="note">
                  AI text reasoning is supplemental to the
                  deterministic assessment and may be unavailable
                  when Gemini quota/service limits are reached.
                </p>
              </Card>

              <Card title="Gemini Multimodal Analysis">
                <p className="ai">
                  {data.multimodal_analysis}
                </p>

                <p className="note">
                  Gemini is given the generated hazard overview
                  plus structured CycloneShield outputs.
                  AI-generated contextual reasoning is not an
                  official observation, forecast, engineering
                  assessment, or emergency directive.
                </p>
              </Card>
            </div>

            <Card title="Decision Support">
              <div className="metrics">
                <Metric
                  label="Planning priority"
                  value={decision?.planning_priority}
                />

                <Metric
                  label="Average impact"
                  value={
                    decision?.average_impact_score
                  }
                />

                <Metric
                  label="Data gaps"
                  value={
                    decision?.data_gaps?.length ?? 0
                  }
                />
              </div>

              <List
                items={decision?.priority_actions}
              />

              <h3>Monitoring points</h3>

              <List
                items={decision?.monitoring_points}
              />
            </Card>

            <div className="disclaimer">
              CycloneShield AI is a decision-support prototype.
              Simulated surge, rainfall pathways, vulnerability,
              evacuation, hardening and parametric-liquidity
              outputs are modelled estimates. Verify conditions
              and official instructions with authorized
              meteorological and disaster-management agencies.
            </div>
          </>
        )}
      </main>
    </div>
  )
}