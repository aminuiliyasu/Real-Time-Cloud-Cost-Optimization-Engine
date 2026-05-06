# Real-Time Cloud Cost Optimization Engine

Real-Time Cloud Cost Optimization Engine is a production-focused FinOps platform that detects cloud waste and applies safe automated cost optimizations across AWS and GCP.

## Problem It Solves

Cloud environments continuously leak money through:

- idle virtual machines
- over-provisioned Kubernetes workloads
- unused storage resources
- expensive configurations that do not match real traffic

This project reduces that waste by turning raw usage and billing data into automated, measurable savings actions.

## What This System Does

The platform:

1. tracks usage and billing signals in real time
2. detects waste patterns
3. recommends or automatically applies optimizations based on policy
4. reports estimated and realized savings

## Core Capabilities

- Integrates with AWS and GCP billing and resource APIs
- Detects:
  - idle VMs
  - over-provisioned Kubernetes pods
  - unused storage
- Executes optimization actions:
  - rightsizing
  - scheduled shutdowns
  - migration to lower-cost configurations
- Provides full audit logs for every recommendation and action

## Advanced Differentiators

### What-If Simulation

Before executing high-impact actions, the simulator evaluates scenarios such as:

`If we reduce instances by 30%, what is the expected monthly savings and utilization risk?`

Each simulation result includes:

- projected monthly savings
- expected post-change utilization
- policy risk classification

### Cost Prediction (ML)

The forecasting module uses historical usage and billing trends to:

- predict short-term spend
- identify overspend risk before it happens
- prioritize optimization opportunities by financial impact

## Example Scenario

An application runs 24/7 but receives low traffic overnight.

1. The engine detects low usage during off-peak hours.
2. It schedules scale-down at night and scale-up before peak traffic.
3. The dashboard records estimated and realized savings.

## Technology Stack

### Cloud + FinOps Integrations

- **AWS:** Cost Explorer API, CloudWatch, Compute Optimizer, EC2/EKS/S3 APIs via `boto3`
- **GCP:** Cloud Billing Export, Cloud Monitoring, Compute Engine/GKE/Cloud Storage APIs
- **Pricing Data:** on-demand pricing catalogs for recommendation cost delta calculations

### Backend + Services

- **Language:** Python 3.11+
- **API Framework:** FastAPI
- **Task Processing:** Celery workers for scheduled analysis and automation jobs
- **Scheduler:** Celery Beat for periodic data collection, anomaly checks, and recommendation refresh
- **API Server:** Uvicorn

### Data + Messaging

- **Primary Database:** PostgreSQL (recommendation history, actions, policy, audit logs)
- **Cache/Queue:** Redis (task queue, short-lived analytics cache, job state)
- **Time-Series Metrics:** Prometheus (resource and platform metrics)
- **Object Storage:** cloud buckets for raw billing exports and historical snapshots

### Frontend + Visualization

- **Frontend:** React
- **Charts:** Recharts (or equivalent React charting package)
- **State/Data Fetching:** TanStack Query
- **UI:** Tailwind CSS + component primitives

### ML + Analytics

- **Data Processing:** Pandas, NumPy
- **Forecasting:** scikit-learn baseline models (linear regression / gradient boosting)
- **Model Tracking:** MLflow for experiment/version tracking
- **Feature Inputs:** usage metrics, billing trend windows, seasonality indicators

### DevOps + Platform

- **Containerization:** Docker
- **Orchestration:** Kubernetes
- **Infrastructure as Code:** Terraform
- **CI/CD:** GitHub Actions
- **Secrets Management:** cloud-native secret managers + Kubernetes secrets references

### Observability + Reliability

- **Metrics:** Prometheus
- **Dashboards:** Grafana
- **Tracing:** OpenTelemetry
- **Logging:** structured JSON logs shipped to centralized log storage
- **Alerting:** Alertmanager and provider-native alert channels

### Security + Compliance

- **Authentication:** JWT for dashboard/API sessions
- **Authorization:** role-based access control for recommendations and execution approvals
- **Cloud Access Model:** least-privilege IAM/service accounts
- **Auditability:** immutable action log with actor, reason, timestamp, and rollback notes

## System Architecture

1. **Ingestion Layer**
  Collects usage, billing, and resource metadata from cloud APIs.
2. **Analysis Engine**
  Detects inefficiencies and generates optimization opportunities.
3. **Simulation + Forecasting Layer**
  Runs what-if scenarios and spend predictions.
4. **Policy + Automation Layer**
  Applies approved actions with safety guardrails.
5. **API + Dashboard Layer**
  Exposes recommendations, actions, and savings metrics.

## API Surface

- `GET /health` - service health and dependency checks
- `GET /recommendations` - list active and historical optimization recommendations
- `POST /recommendations/{id}/simulate` - run what-if simulation for a recommendation
- `POST /recommendations/{id}/approve` - approve optimization action
- `POST /actions/{id}/execute` - execute approved action
- `GET /savings/summary` - estimated vs realized savings by period and account
- `GET /policies` / `PUT /policies/{id}` - policy and automation rule management

## Repository Structure

```text
.
├── backend/
│   ├── app/
│   ├── workers/
│   └── requirements.txt
├── dashboard/
│   ├── src/
│   └── package.json
├── infra/
│   └── terraform/
├── docs/
├── tests/
└── README.md
```

## Setup

### 1) Clone

```bash
git clone <your-repo-url>
cd Real-Time-Cloud-Cost-Optimization-Engine
```

### 2) Create `.env`

```env
APP_ENV=development
API_PORT=8000
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/cost_optimizer
REDIS_URL=redis://localhost:6379/0

AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=replace_me
AWS_SECRET_ACCESS_KEY=replace_me

GCP_PROJECT_ID=replace_me
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/gcp-service-account.json
```

### 3) Start Dependencies

```bash
docker compose up -d postgres redis
```

### 4) Run Backend API

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5) Run Worker

```bash
cd backend
python -m workers.scheduler
```

### 6) Run Dashboard

```bash
cd dashboard
npm install
npm run dev
```

## CI/CD Pipeline

GitHub Actions pipeline stages:

1. lint (`ruff`, `eslint`)
2. unit tests (`pytest`, frontend tests)
3. build backend and dashboard images
4. security scan (`trivy`/dependency checks)
5. deploy to Kubernetes environment

## Infrastructure

Terraform manages:

- VPC/networking
- Kubernetes cluster and node pools
- database and cache services
- IAM roles/service accounts
- monitoring and alerting resources

All infrastructure changes are reviewed through pull requests before apply.

## Detection Rules

- **Idle VM:** CPU and network usage remain below threshold for a defined window
- **Over-provisioned Pod:** requested CPU/memory is consistently above observed usage
- **Unused Storage:** unattached or near-zero read/write activity over time

## Automated Actions

- downsize over-provisioned resources
- apply scheduled shutdown/start policies for non-critical workloads
- move data to lower-cost storage classes
- enforce policy checks before every action

## Testing Strategy

- **Unit tests:** detection rules, simulation logic, policy evaluation, savings calculations
- **Integration tests:** cloud connector clients and billing ingestion workflow
- **End-to-end tests:** recommendation -> approval -> execution -> savings report
- **Load tests:** ingestion and analysis under high metric/cardinality conditions
- **Safety tests:** ensure blocked actions are never executed without policy approval

## Risk Controls

- dry-run mode enabled by default for new environments
- approval gate required for production write actions
- rollback metadata attached to every executable action
- action cooldown windows to prevent repeated oscillating changes
- blast-radius control via per-account and per-cluster policy limits

## Why This Project

- demonstrates business-aware engineering through measurable cost impact
- combines observability, automation, and financial optimization
- solves a real production problem with clear ROI

## Contributing

1. Open an issue describing the problem and expected impact.
2. Create a feature branch.
3. Add tests and documentation for your change.
4. Submit a pull request.

## License

This project is licensed under the MIT License.