# Architecture Overview

## System Components

- **API layer (`backend/app/api`)**: HTTP endpoints, auth guards, request validation, response models.
- **Service layer (`backend/app/services`)**: business logic for rules, simulation, analytics, ingestion, and lifecycle operations.
- **Worker layer (`backend/app/workers`)**: scheduled ingestion and rule evaluation cycles.
- **Data layer (`backend/app/models`, `backend/app/db`)**: SQLAlchemy models and DB session management.
- **Dashboard (`dashboard/src`)**: static frontend that consumes KPI, trend, and recommendation endpoints.

## Request and Data Flow

1. Cloud metrics/resources are ingested through ingestion services or worker jobs.
2. Ingested resource/metric data is stored in `resources` and `usage_metrics`.
3. Rule services evaluate utilization and create recommendation records.
4. Recommendation lifecycle services handle approval/execution and write audit logs.
5. Simulation service computes projected savings/risk and persists simulation history.
6. Dashboard analytics service aggregates KPI and trend data for frontend visualization.

## Key Runtime Paths

- **Ingestion path**
  - `POST /dev/ingest/aws/ecs/resources`
  - `POST /dev/ingest/aws/ecs/metrics`
  - worker equivalent: `python -m app.workers.scheduler --run-once --hours 24`

- **Optimization path**
  - `POST /dev/recommendations/run-ecs-underutilized-rule`
  - `POST /dev/recommendations/run-idle-vm-rule`

- **Lifecycle path**
  - `POST /recommendations/{id}/approve`
  - `POST /recommendations/{id}/execute`
  - `GET /recommendations/{id}/audit-logs`

- **Dashboard path**
  - `GET /dashboard/kpis`
  - `GET /dashboard/trends?hours=24`

## Boundary Rules

- API routes should remain thin (auth, input checks, service calls).
- Business logic should stay in services, not route handlers.
- Workers call service functions directly and do not duplicate core logic.
- Contracts are enforced through explicit response models in schema files.
