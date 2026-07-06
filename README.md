# SmartGrid Insights

> CMP404 Spring 2026 · Team 5 · American University of Sharjah  
> Saifeldin Hassan · Louy Abbas · Ahmad Bilal

A cloud-based platform for analyzing household electricity consumption patterns, built as five independently deployed microservices. Administrators can register smart meters, simulate data collection from a historical dataset, and run consumption analytics — all from a single web interface.

Originally deployed on **Azure App Service** with **Azure SQL** databases (since decommissioned to cut hosting costs); the database layer has been migrated to **PostgreSQL**, every service is **dockerized**, and the readings write path is **event-driven through Kafka** — so the whole stack now runs anywhere with one `docker compose up`.

---

## Repositories

| # | Service | Owner | Stack | Repo |
|---|---------|-------|-------|------|
| 1 | **Data Ingestion** | Saif | FastAPI · SQLAlchemy · PostgreSQL | [smartgrid-data-ingestion](https://github.com/LouayYa/smartgrid-data-ingestion) |
| 2 | **Meter Registration** | Ahmad | Flask · SQLAlchemy · PostgreSQL | [meter-registration-service](https://github.com/LouayYa/meter-registration-service) |
| 3 | **Data Collection** | Louy | FastAPI · Kafka · SQLAlchemy · PostgreSQL | [smartgrid-data-collection](https://github.com/LouayYa/smartgrid-data-collection) |
| 4 | **Data Analysis** | Louy | FastAPI · Requests | [smartgrid-data-analysis](https://github.com/LouayYa/smartgrid-data-analysis) |
| 5 | **Client Interface** | Ahmad | Flask · Jinja2 | [smartgrid-ui](https://github.com/LouayYa/smartgrid-ui) |

This repository also contains a full snapshot of every service plus the Docker Compose orchestration, so the entire system can be cloned and run from one place:

```
.
├── docker-compose.yml                  # One-command local orchestration
├── .env.example                        # Template for required secrets (copy to .env)
├── db/init/                            # Creates the per-service Postgres databases
├── smart-data-ingestion/               # Data Ingestion (FastAPI, port 8001)
├── smartgrid-meter-registration/       # Meter Registration (Flask, port 8000)
├── smartgrid-data-collection/          # Data Collection (FastAPI, port 8002)
├── smartgrid-data-analysis/            # Data Analysis (FastAPI, port 8003)
└── smartgrid-UI/                       # Client Interface (Flask, port 8004)
```

---

## Quick Start (Docker Compose)

Run the whole platform locally — five services, a Kafka broker (KRaft, no ZooKeeper), a readings consumer worker, and a shared Postgres 16 instance — with one command.

```bash
git clone https://github.com/LouayYa/SmartGrid-Insights.git
cd SmartGrid-Insights

# Secrets are NOT hardcoded — copy the template and set your own values.
cp .env.example .env      # then edit .env and set POSTGRES_PASSWORD

docker compose up --build
```

Then open the UI at **http://localhost:8004**. To seed the dataset, call `POST http://localhost:8001/api/v1/load` once, register a meter in the UI, and trigger a simulation.

The database password is injected everywhere from the `POSTGRES_PASSWORD` variable in `.env` (which is gitignored) — nothing secret lives in `docker-compose.yml`.

---

## System Architecture (original Azure deployment)

The diagrams below document the original Azure PaaS deployment: five microservices and three databases, with the Client UI as the only public-facing service — all backend services and databases VNet-private. The same topology now runs locally on the compose network (`smartgrid`), with the three Azure SQL databases replaced by per-service databases on a shared Postgres instance.

<p align="center">
  <img src="./diagrams/system-architecture.svg" width="90%" />
</p>

---

## Network Topology (original Azure deployment)

The VNet (`smartgrid-vnet`, `10.0.0.0/16`) was split into an app-subnet for App Service VNet integration and a db-private-subnet for private endpoints to each Azure SQL database. Only the Client UI had a public inbound endpoint.

<p align="center">
  <img src="./diagrams/Network-Topology.svg" width="90%" />
</p>

---

## End-to-End Data Flow

<p align="center">
  <img src="./diagrams/data-flow-sequence.svg" width="90%" />
</p>

1. **Register a meter** — Client UI → `POST /meters` → Meter Registration Service → Meter Registration DB
2. **Trigger simulation** — Client UI → `POST /simulate/{meter_id}` → Data Collection Service
3. **Publish readings** — Data Collection Service fetches the historical window via `GET /consumption` on the Data Ingestion Service and publishes each reading as a JSON event to the **`meter-readings` Kafka topic**, keyed by `meter_id` (a standalone simulator client in `smartgrid-data-collection/simulator/` plays a real smart meter and produces to the same topic directly)
4. **Store readings** — the **readings consumer worker** (`collection-consumer` in compose) is the single DB writer: it validates each event, batch-inserts into the Data Collection DB, and commits Kafka offsets only after the database transaction succeeds (at-least-once delivery)
5. **Analyze** — Client UI → Data Analysis Service (`/analysis/averages`, `/analysis/peaks`, `/analysis/categories`) → queries Data Collection DB → returns computed results

```mermaid
sequenceDiagram
    participant UI as Client UI
    participant DC as Data Collection API
    participant DI as Data Ingestion
    participant K as Kafka (meter-readings)
    participant CW as Consumer Worker
    participant DB as Collection DB (Postgres)

    UI->>DC: POST /simulate/{meter_id}
    DC->>DI: GET /consumption?start&end
    DI-->>DC: historical records
    DC->>K: produce reading events (key = meter_id)
    K-->>DC: acks (idempotent producer)
    DC-->>UI: 202 { records_published }
    K->>CW: consume batch
    CW->>DB: validated batch INSERT
    CW->>K: commit offsets (after DB commit)
```

---

## Databases

| Database | Owned By | Table | Key Columns |
|----------|----------|-------|-------------|
| Ingestion DB | Data Ingestion | `household_power_consumption` | `ID`, `Date`, `Time`, `Global_active_power`, `Voltage`, `Sub_metering_1/2/3` |
| Meter Registration DB | Meter Registration | `meters` | `meter_id`, `name`, `created_at` |
| Data Collection DB | Data Collection | `readings` | `reading_id`, `meter_id`, `timestamp`, `global_active_power`, `voltage`, `sub_metering_1/2/3` |

---

## CI/CD

Every push to `main` triggers **GitHub Actions** in each service repo: dependencies install and the service's pytest suite runs, blocking the pipeline on failure. The deploy-to-Azure jobs (originally wired through Azure Deployment Center) are kept as reference implementations but only run on a manual `workflow_dispatch` trigger, since the Azure hosting was decommissioned.

| Service | Workflow Status |
|---------|----------------|
| Data Ingestion | ![CI](https://github.com/LouayYa/smartgrid-data-ingestion/actions/workflows/main_smartgrid-data-ingestion.yml/badge.svg) |
| Meter Registration | ![CI](https://github.com/LouayYa/meter-registration-service/actions/workflows/main_meter-registration-service.yml/badge.svg) |
| Data Collection | ![CI](https://github.com/LouayYa/smartgrid-data-collection/actions/workflows/main_smartgrid-data-collection.yml/badge.svg) |
| Data Analysis | ![CI](https://github.com/LouayYa/smartgrid-data-analysis/actions/workflows/main_smartgrid-data-analysis.yml/badge.svg) |
| Client Interface | ![CI](https://github.com/LouayYa/smartgrid-ui/actions/workflows/main_smartgrid-ui.yml/badge.svg) |

---

## Local Development

Each service has its own `.env` — refer to the `.env.example` in each repo. The inter-service URLs you'll need:

```env
# Data Collection Service
DATA_INGESTION_URL=http://localhost:8001

# Data Analysis Service
DATA_COLLECTION_URL=http://localhost:8002

# Client Interface
METER_SERVICE_URL=http://localhost:8000
COLLECTION_SERVICE_URL=http://localhost:8002
ANALYSIS_SERVICE_URL=http://localhost:8003
```

Default ports: Meter Registration `8000` · Data Ingestion `8001` · Data Collection `8002` · Data Analysis `8003` · Client UI `8004`

---

## Dataset

[UCI Household Power Consumption](https://archive.ics.uci.edu/ml/datasets/Individual+household+electric+power+consumption) — 260,640 minute-level readings, January 1 – June 30, 2007. Loaded into the Ingestion DB via `POST /api/v1/load`.

---

> Part of **SmartGrid Insights** — CMP404 Spring 2026 · Team 5
