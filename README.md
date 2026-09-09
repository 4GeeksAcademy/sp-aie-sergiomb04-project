# TrackFlow — Unified Logistics & AI Platform

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![Track](https://img.shields.io/badge/Track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![Prefect](https://img.shields.io/badge/Prefect-3.0-024DFD?logo=prefect)](https://www.prefect.io/)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?logo=celery)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-Alpine-DC382D?logo=redis)](https://redis.io/)

TrackFlow is an end-to-end digital logistics and AI platform powering multi-country warehouse operations and last-mile fulfillment across the **United States (Los Angeles)** and **Spain (Zaragoza)** for growing e-commerce brands.

---

## 🚀 Business Overview & Core Capabilities

TrackFlow bridges the gap between physical warehousing operations, multi-carrier shipping networks, executive decision-making, and predictive intelligence:

- **Warehouse & Inventory Intelligence:** Real-time visibility into inbound unit throughput, outbound order fulfillment, and automated discrepancy/stockout tracking.
- **Asynchronous Task Architecture:** Resilient background execution powered by Celery & Redis with automatic retries, exponential backoff, and a Dead Letter Queue (DLQ) for mission-critical jobs.
- **Resilient Data Pipelines:** Production-grade Prefect 3 workflows aggregating multi-tenant KPIs into reporting data marts with atomic UPSERT idempotency.
- **Sales & Revenue Forecasting:** Machine Learning regression pipeline (Random Forest) predicting monthly consolidated revenue with empirical uncertainty intervals (5th–95th percentiles) and strict anti-data leakage split (8 years train / 2 years test).
- **Executive & Operations Dashboards:** Modern Next.js backoffice for monitoring operational telemetry, carrier performance, and real-time business KPIs.

---

## 🏛️ Monorepo Architecture

```text
.
├── services/
│   ├── api/                     # FastAPI backend service (endpoints, routes, ORM models)
│   │   ├── trackflow_api/       # Main API application package
│   │   │   ├── routes/          # REST routes (/telemetry, /reporting, /tasks)
│   │   │   ├── celery_app.py    # Celery producer & worker configuration
│   │   │   ├── tasks.py         # Heavy async background tasks
│   │   │   └── dlq.py           # Dead Letter Queue error management
│   │   └── tests/               # Backend API unit & integration tests
│   ├── telemetry/               # Pure analytics functions for event telemetry
│   └── job_runner.py            # Distributed locking and job execution engine
├── data/
│   ├── pipelines/               # Prefect 3 pipeline flows and CLI entrypoints
│   ├── process/                 # Vectorized data transformation modules
│   └── raw/                     # Raw datasets (sales, telemetry snapshots)
├── src/
│   └── pipelines/               # Machine Learning sales forecasting pipeline
│       ├── data_prep.py         # Temporal split (8/2 yrs) & feature engineering
│       ├── evaluate.py          # Metrics (MSE, PSI, Gini, K2 Score, WAPE)
│       └── train_forecast.py    # Random Forest training & uncertainty visualization
├── uis/
│   └── talent-pipeline-tracker/ # Next.js (App Router) Backoffice UI & dashboards
├── packages/
│   └── shared/                  # Shared TypeScript types and contracts (@repo/shared-types)
├── reports/
│   ├── figures/                 # High-resolution charts (sales forecast, telemetry)
│   └── metrics_report.json      # Evaluated ML model test metrics
├── docs/                        # Architecture proposals, audits, reports, ML docs
├── memory-bank/                 # Project Brief, Technical Context, and Progress tracking
├── scripts/                     # Operational scripts (nightly exports, worker runners)
├── docker-compose.yml           # Redis, Celery worker, and Flower monitoring stack
└── pyproject.toml               # Python workspace configuration managed with uv
```

---

## ⚡ Key Modules & Subsystems

### 1. Asynchronous Task Queue & DLQ (Celery + Redis)
- **FastAPI Producers:** Endpoints (`POST /reporting/pipeline-runs`, `POST /tasks/pipeline-run`) return immediate `202 Accepted` (<200ms) with unique `task_id`.
- **Worker Execution:** Decoupled background processing with exponential backoff retries (`countdown = 2 ** retries * 5`).
- **Dead Letter Queue (DLQ):** Exhausted failures are automatically recorded in the `dead_letter_queue` table with stack traces and payload references for auditing and manual replay.
- **Monitoring:** Live task inspection via Flower dashboard on port `5555`.

### 2. Operational Telemetry & Business Data Pipeline (Prefect 3)
- **Flows:** Modular Prefect subflows (`extract_telemetry_events_flow`, `transform_warehouse_client_metrics_flow`, `load_reporting_metrics_flow`).
- **Idempotency & Integrity:** Atomic PostgreSQL/SQLite UPSERT with unique constraint `(warehouse, client_id, week_start)`.
- **Nightly Snapshot Automation:** Distributed locking (`scripts/nightly_export.py`) preventing duplicate or zombie cron runs.

### 3. Machine Learning Sales Forecasting (Random Forest)
- **Dataset:** 10 years of monthly revenue data (`2016-01` to `2025-12`).
- **Strict Temporal Split:** First 8 years for training (96 months), last 2 years for test verification (24 months) — 100% free of data leakage.
- **Financial Validation Metrics:**
  - **MSE / RMSE:** `115.4K €` (**8.88%** of mean monthly revenue).
  - **WAPE:** **`7.09%`** weighted absolute error across test period.
  - **Normalized Gini:** **`0.6788`** (robust discrimination of holiday peaks vs. low season).
  - **K2 Score:** $p = 0.7436 > 0.05$ (residuals follow normal distribution without systematic bias).
  - **Uncertainty Interval:** Empirical 5th–95th percentile bands across estimator trees.
  - *Detailed documentation available in [`docs/SALES_FORECASTING.md`](./docs/SALES_FORECASTING.md).*

### 4. Backoffice Web Dashboard (Next.js)
- **Pages:** `/telemetry` (event monitoring, latency, error rates), `/reporting` (warehouse throughput, discrepancy rates, client metrics).
- **Stack:** React 19, TypeScript, TailwindCSS, Next.js Server Components, and API Route proxies.

---

## 🛠️ Tech Stack

| Domain | Technologies |
|---|---|
| **Backend & API** | Python 3.13, FastAPI, SQLModel, Pydantic, SQLite / PostgreSQL |
| **Async Tasks & Queue** | Celery 5.4, Redis, Flower |
| **Data Pipelines & ML** | Prefect 3.0, Pandas, NumPy, Scikit-Learn, SciPy, Matplotlib |
| **Frontend & UI** | Next.js 15 (App Router), React 19, TypeScript, TailwindCSS |
| **Package Management** | `uv` (Python), `pnpm` / `npm` (JavaScript / TypeScript) |
| **Containers & Ops** | Docker, Docker Compose |

---

## 🏁 Getting Started

### Prerequisites
- **Python 3.13+** with **`uv`** installed (`curl -LsSf https://astral.sh/uv/install.sh | sh` or via Scoop/Winget).
- **Node.js 20+** with `npm` or `pnpm`.
- **Docker & Docker Compose** (for Redis & Celery worker).

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone https://github.com/4GeeksAcademy/sp-aie-sergiomb04-project.git
cd sp-aie-sergiomb04-project

# Install Python workspace dependencies using uv
uv sync
```

### 2. Start Infrastructure (Redis & Background Workers)

```bash
# Start Redis, Celery Worker, and Flower dashboard
docker-compose up -d

# Verify services:
# - Redis: localhost:6379
# - Flower Dashboard: http://localhost:5555
```

### 3. Run FastAPI Backend

```bash
cd services/api
uv run uvicorn trackflow_api.main:app --reload --port 8000
```
- Interactive Swagger Docs: `http://localhost:8000/docs`

### 4. Run Machine Learning Sales Forecast Pipeline

```bash
# Run training, uncertainty estimation, and chart generation
uv run python -m src.pipelines.train_forecast

# View generated forecast chart in reports/figures/sales_forecast_trackflow.png
```

### 5. Run Next.js Backoffice Frontend

```bash
cd uis/talent-pipeline-tracker
npm install
npm run dev
```
- Access Backoffice UI at: `http://localhost:3000`

---

## 🧪 Testing & Quality Assurance

All modules are protected with comprehensive automated tests:

```bash
# 1. Run Machine Learning Pipeline Unit Tests (Temporal Split & Metrics)
uv run pytest tests/pipelines/test_sales_split.py

# 2. Run Backend API, Celery & Telemetry Tests
uv run pytest services/api/tests/

# 3. Run Data Pipeline Isolation Tests
uv run pytest tests/pipelines/test_pipeline.py

# 4. Run Frontend UI Tests
cd uis/talent-pipeline-tracker
npm test
```

---

## 📚 Project Documentation

- **[Sales Forecasting Technical Deep-Dive](./docs/SALES_FORECASTING.md):** Model rationale, evaluation metrics, and Finance executive guide.
- **[Data Pipeline Design](./data/pipelines/PIPELINE_DESIGN.md):** Architecture and data aggregation specification for warehouse metrics.
- **[Nightly Telemetry & Distributed Locking](./docs/telemetry/):** Specifications for nightly jobs and idempotency.
- **[Memory Bank](./memory-bank/):** Living project memory including [Project Brief](./memory-bank/projectbrief.md), [Technical Context](./memory-bank/techContext.md), and [Progress Report](./memory-bank/progress.md).

---

## 👥 Contributors & Program

Project developed within the **AI Engineering Career Program** at **[4Geeks Academy](https://4geeksacademy.com)**.
