# Real-Time Cloud Cost Optimization Engine

A FinOps platform that ingests **live AWS usage**, flags waste, and walks through an approve → simulate → apply workflow with a simple dashboard.

**Stack:** Python · FastAPI · SQLAlchemy · PostgreSQL · Redis · AWS APIs · Docker · Terraform

**Repo:** https://github.com/aminuiliyasu/Real-Time-Cloud-Cost-Optimization-Engine

---

## What it does

1. **Discovers** EC2 instances and ECS services from your AWS accounts (multi-profile, multi-region).
2. **Pulls** CloudWatch CPU/memory metrics on a schedule or on demand.
3. **Runs rules** for rightsizing, scheduled shutdowns, idle VMs, and migration candidates.
4. **Shows savings** per account in a portfolio view (monthly and annual estimates).
5. **What-if simulations** let you model a % reduction before approving a change.
6. **Workflow** — open → approved → executed, with audit logs.

Savings numbers are **estimates from utilization rules**, not pulled from AWS Cost Explorer or billing APIs.

“Execute” updates status and audit logs in the database. It does **not** resize or stop AWS resources automatically.

---

## What is not included

| Area | Status |
|------|--------|
| GCP | Not implemented (AWS only) |
| Billing / Cost Explorer API | Not implemented |
| Automatic AWS changes on execute | Not implemented |
| CI/CD pipeline | Not implemented |
| Kubernetes | ECS only (no EKS) |
| Storage waste rules | Not implemented |

---

## Project layout

```
.
├── backend/          # FastAPI app, rules, ingestion, workers
├── dashboard/src/    # Static demo UI (HTML/CSS/JS)
├── infra/terraform/  # Minimal AWS VPC + EC2 skeleton
├── tests/
├── docker-compose.yml
└── .env.example
```

---

## Quick start

### 1. Clone and configure

```bash
git clone https://github.com/aminuiliyasu/Real-Time-Cloud-Cost-Optimization-Engine.git
cd Real-Time-Cloud-Cost-Optimization-Engine
cp .env.example .env
git config core.hooksPath .githooks
```

The git hook strips accidental AI co-author trailers from commit messages.

Edit `.env` and add a database credential and API key (generate random strings — do not commit `.env`).

```env
AWS_PROFILES=default:af-south-1,rhentify-aws:us-east-1
```

The dashboard reads your API key from the header field or `?api_key=` in the URL.

### 2. Start database and cache

```bash
docker compose up -d postgres redis
```

### 3. Run the API

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 4. Run the dashboard

In a second terminal:

```bash
cd dashboard/src
python3 -m http.server 5500
```

Open **http://127.0.0.1:5500** and click **Run full analysis** to ingest AWS data and run all rules.

---

## Demo flow (for screen recording)

1. Open the dashboard.
2. Click **Run full analysis (AWS → rules → savings)**.
3. Show account cards and annual waste identified.
4. Scroll to the utilization chart (CloudWatch metrics).
5. Open a recommendation → **What-if** → adjust slider → run simulation.
6. **Approve** → **Apply** → refresh to see realized savings update.

---

## API overview

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check |
| `GET /dashboard/portfolio` | Multi-account waste summary |
| `GET /dashboard/kpis` | KPI cards |
| `GET /dashboard/trends?hours=24` | Utilization chart data |
| `GET /recommendations` | List recommendations |
| `POST /recommendations/{id}/simulate` | What-if simulation |
| `POST /recommendations/{id}/approve` | Approve (operator/admin) |
| `POST /recommendations/{id}/execute` | Mark executed (admin) |
| `POST /dev/pipeline/run-full-analysis` | Ingest + run all rules (dev only) |

Dev ingestion endpoints require `APP_ENV=development`, `X-API-Key`, and `X-Role: admin`.

Interactive docs: **http://127.0.0.1:8000/docs**

---

## Detection rules

| Rule | Trigger | Action type |
|------|---------|---------------|
| `idle_vm` | EC2 avg CPU &lt; 5% | Rightsizing |
| `ecs_underutilized_service` | ECS CPU &lt; 20% and memory &lt; 30% | Rightsizing |
| `scheduled_shutdown` | EC2 avg CPU &lt; 8% | Scheduled shutdown |
| `migration_candidate` | EC2 CPU between 5–15% | Migration |

---

## Background worker (optional)

```bash
cd backend
python -m app.workers.scheduler --run-once --hours 24
```

Loop every 15 minutes:

```bash
python -m app.workers.scheduler --hours 24 --interval-seconds 900
```

---

## Docker (all services)

```bash
docker compose up -d --build
```

API on port 8000, dashboard on port 5500. Mount `~/.aws` for AWS credentials (see `docker-compose.yml`).

---

## Terraform (minimal EC2 host)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

Provisions a VPC, public subnet, security group (SSH + port 8000), and one EC2 instance. Extend this for production (HTTPS, RDS, IAM role, etc.).

---

## Tests

```bash
source backend/.venv/bin/activate
pytest -q
```

---

## Author

**Aminu Iliyasu** — [GitHub](https://github.com/aminuiliyasu)
