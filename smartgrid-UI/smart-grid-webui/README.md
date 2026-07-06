# SmartGrid Insights — Client Interface

> **Service 5 of 5** | CMP404 Spring 2026 · Team 5 | Developed by **Ahmad Bilal** · AUS

## Overview

One of five independently deployed microservices behind SmartGrid Insights, a system that ingests, stores, and analyzes 260K+ smart meter readings end to end. This service is the only user-facing piece: a Flask + Jinja2 web dashboard for registering meters, triggering reading simulations, browsing readings, and viewing analytics (daily averages, peak hours, usage categories).

It stores no data of its own — every action is delegated over HTTP to the Meter Registration, Data Collection, and Data Analysis services. Long-running simulations are dispatched to a background thread and tracked through an in-memory job store the browser polls for status.

Originally deployed on Azure App Service; the backing platform has since moved from Azure SQL to **PostgreSQL** and the whole stack is **dockerized** for local orchestration.

**Stack:** Flask · Jinja2 · Requests · Gunicorn · Docker · GitHub Actions · Azure App Service (deploy-on-demand)

---

## Data Flow

```
Browser ──► this service
              │
              ├──► Meter Registration Service   (create / rename / delete meters)
              ├──► Data Collection Service      (trigger simulation, fetch readings)
              └──► Data Analysis Service        (averages / peaks / categories)
```

---

## Routes

Base URL: `http://localhost:8004` (local dev — the Azure deployment has been decommissioned; see [CI/CD](#cicd))

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Dashboard — meters, readings, and analysis results (filtered via query params) |
| `POST` | `/meters/create` | Register a new meter |
| `POST` | `/meters/update` | Rename a meter |
| `POST` | `/meters/delete` | Delete a meter (and best-effort delete its readings) |
| `POST` | `/simulate` | Start a simulation as a background job |
| `GET` | `/simulate/status/{job_id}` | Poll a simulation job's status (`running` / `done` / `error`) |

Date inputs are validated against the dataset window (**2007-01-01 → 2007-06-30**) before any backend call is made.

---

## Project Structure

```text
.
├── app.py            # Flask routes, date validation, background job store
├── services.py       # HTTP client wrappers for the three backend services
├── config.py         # Service URLs from environment variables
├── templates/index.html
├── static/styles.css
├── Dockerfile
└── requirements.txt
```

---

## Local Setup

```bash
git clone https://github.com/LouayYa/smartgrid-UI.git
cd smartgrid-UI
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file (see [`.env.example`](.env.example)):
```env
METER_SERVICE_URL=http://localhost:8000
COLLECTION_SERVICE_URL=http://localhost:8002
ANALYSIS_SERVICE_URL=http://localhost:8003
SECRET_KEY=change-this-secret-key
```

Run:
```bash
python app.py
# or, matching the production startup command:
gunicorn --bind=0.0.0.0:8004 app:app
```

---

## Run with Docker

The repo ships a multi-stage [`Dockerfile`](Dockerfile) (Python 3.12-slim builder + slim runtime, non-root user, Gunicorn):

```bash
docker build -t smartgrid-ui .
docker run -p 8004:8004 --env-file .env smartgrid-ui
```

To run the **entire five-service stack plus a shared PostgreSQL 16 instance** with one command, use the `docker-compose.yml` in the umbrella repo: [SmartGrid-Insights](https://github.com/LouayYa/SmartGrid-Insights).

---

## CI/CD

**Build** runs automatically via **GitHub Actions** on every push to `main`: dependencies install into a virtual environment to catch build issues early.

**Deploy to Azure App Service** was originally wired through **Azure Deployment Center** (GitHub source → auto-generated workflow), with the service URLs and `SECRET_KEY` configured under App Service → Configuration rather than committed to the repo. The live Azure App Service has since been decommissioned to cut hosting costs, so the `deploy` job is kept in [`.github/workflows/`](.github/workflows/) as a reference implementation and only runs on a manual `workflow_dispatch` trigger — it no longer fires on every push.

---

## Related Services

| Service | Owner | Role |
|---|---|---|
| Data Ingestion Service | Saif | Historical CSV data source |
| Meter Registration Service | Ahmad | Provides `meter_id` values |
| Data Collection Service | Louy | Persists readings tagged with `meter_id` |
| Data Analysis Service | Louy | Queries collected readings for analytics |
| **Client Interface** | **Ahmad** | This repo — web UI |

> Part of **SmartGrid Insights** — CMP404 Spring 2026 · Team 5  
> Saifeldin Hassan · Louy Abbas · Ahmad Bilal · American University of Sharjah
