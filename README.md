# 🌪️ CycloneShield AI

### AI-Powered Pre-Landfall Cyclone Risk, Vulnerability & Anticipatory-Action Intelligence

[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run-blue?logo=googlecloud)](https://cloud.google.com/run)
[![Google Earth Engine](https://img.shields.io/badge/Google-Earth%20Engine-green)](https://earthengine.google.com/)
[![Gemini](https://img.shields.io/badge/Google-Gemini%20AI-purple)](https://ai.google.dev/)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react)](https://react.dev/)

> **Prepare before the impact.**

CycloneShield AI is an AI-powered **pre-landfall decision-support platform** designed to help communities and disaster-management stakeholders assess cyclone risk, infrastructure exposure, hazard pathways and potential impacts before severe weather reaches affected areas.

The platform combines **Google Earth Engine, Gemini AI, meteorological data, terrain information and OpenStreetMap infrastructure data** to transform a cyclone scenario into a structured workflow:

**Scenario → Geospatial Intelligence → Hazard Screening → Infrastructure Exposure → Impact Assessment → Anticipatory Action**

---

## 🚀 Live Demo

🌐 **Live Application**

https://cycloneshield-frontend-298560693045.asia-south1.run.app

💻 **Source Code**

https://github.com/gopuyashwanthmy-aim/CycloneShield-AI

---

## 🎯 Problem

Cyclones can cause cascading impacts across:

- 🏥 Healthcare facilities
- ⚡ Power infrastructure
- 🛣️ Roads and transportation
- 🏫 Schools
- 🏠 Communities and shelters
- 🌧️ Flood-prone areas
- 💰 Local economic systems

Traditional disaster response often becomes heavily reactive after severe weather impacts an area.

CycloneShield AI explores how AI and geospatial intelligence can support **pre-landfall preparedness**, helping identify potentially affected infrastructure and translate risk information into anticipatory planning actions.

---

# 💡 Solution

CycloneShield AI provides an integrated decision-support workflow that combines:

### 🌍 Geospatial Intelligence

Google Earth Engine is used to retrieve location-specific environmental context such as:

- Elevation
- Dynamic World land-cover information
- Built-area probability
- Water probability

### 🌦️ Meteorological Intelligence

The platform combines:

- Current meteorological observations
- Rainfall information
- Wind information
- User-defined cyclone scenario parameters

### 🏥 Infrastructure Exposure

OpenStreetMap data is used to identify mapped infrastructure such as:

- Hospitals
- Schools
- Power substations
- Major roads
- Medical shelters

### 🌊 Hazard Screening

The platform performs prototype screening for:

- Storm-surge exposure
- Rainfall/runoff pathways
- Terrain-related exposure
- Infrastructure-hazard intersections

### ⚠️ Risk & Impact Assessment

A deterministic risk engine combines scenario hazards, spatial exposure and environmental context to generate:

- Overall risk score
- Asset impact scores
- Impact levels
- Hazard intersections
- Sector-specific planning priorities

### 🚨 Anticipatory Action

The results are translated into:

- Evacuation-planning support
- Infrastructure-hardening recommendations
- Early-warning preparedness advisories
- Monitoring points
- Illustrative financial-resilience calculations

### 🤖 Gemini AI

Gemini provides an additional contextual reasoning layer over the structured CycloneShield assessment.

The AI layer is designed to help contextualize:

- Scenario conditions
- Retrieved data
- Infrastructure exposure
- Risk indicators
- Recommended preparedness actions

---

# 🧠 System Architecture

```text
                   Cyclone Scenario
                         │
                         ▼
              ┌──────────────────────┐
              │ Meteorological Data  │
              │ Wind / Rainfall      │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Google Earth Engine  │
              │ Elevation / Land     │
              │ Cover / Water        │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Infrastructure Data  │
              │ OSM / GIS            │
              │ Hospitals / Roads     │
              │ Schools / Power       │
              │ Shelters              │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Hazard Screening     │
              │ Surge / Rainfall     │
              │ Pathways / Terrain   │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Risk & Impact Engine │
              │ Exposure / Impact    │
              │ Vulnerability        │
              └──────────┬───────────┘
                         │
                         ▼
        ┌─────────────────────────────────┐
        │      Anticipatory Actions       │
        ├─────────────────────────────────┤
        │ Evacuation Planning              │
        │ Infrastructure Hardening         │
        │ Early-Warning Advisory           │
        │ Financial Resilience             │
        └────────────────┬────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Gemini AI Reasoning  │
              │ Contextual Analysis  │
              └──────────────────────┘
