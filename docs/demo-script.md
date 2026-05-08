# 5-Minute Demo Script

## Goal

Show end-to-end cloud cost optimization flow:

1. ingest data
2. generate recommendation
3. approve/execute
4. show savings and dashboard updates

## Pre-demo Checklist

- Backend API running on `http://127.0.0.1:8000`
- Docker services up (Postgres, Redis)
- Dashboard static server running on `http://127.0.0.1:5500`
- `.env` contains valid `API_KEY`, `AWS_REGION`, `AWS_PROFILE`

## Demo Commands

### 1) Ingest ECS resources + metrics

```bash
curl -X POST "http://127.0.0.1:8000/dev/ingest/aws/ecs/resources" \
  -H "X-API-Key: change_me_strong_key" \
  -H "X-Role: admin"

curl -X POST "http://127.0.0.1:8000/dev/ingest/aws/ecs/metrics?hours=24" \
  -H "X-API-Key: change_me_strong_key" \
  -H "X-Role: admin"
```

### 2) Run optimization rules

```bash
curl -X POST "http://127.0.0.1:8000/dev/recommendations/run-ecs-underutilized-rule" \
  -H "X-API-Key: change_me_strong_key" \
  -H "X-Role: admin"
```

### 3) List recommendations and pick an open id

```bash
curl "http://127.0.0.1:8000/recommendations"
```

### 4) Approve and execute (replace `<OPEN_ID>`)

```bash
curl -X POST "http://127.0.0.1:8000/recommendations/<OPEN_ID>/approve" \
  -H "X-API-Key: change_me_strong_key" \
  -H "X-Role: operator" \
  -H "Content-Type: application/json" \
  -d '{"actor":"demo-user","notes":"approved in demo"}'

curl -X POST "http://127.0.0.1:8000/recommendations/<OPEN_ID>/execute" \
  -H "X-API-Key: change_me_strong_key" \
  -H "X-Role: admin" \
  -H "Content-Type: application/json" \
  -d '{"actor":"demo-user","notes":"executed in demo"}'
```

### 5) Show evidence

```bash
curl "http://127.0.0.1:8000/recommendations/<OPEN_ID>/audit-logs"
curl "http://127.0.0.1:8000/savings/summary"
curl "http://127.0.0.1:8000/dashboard/kpis"
curl "http://127.0.0.1:8000/dashboard/trends?hours=24"
```

## Narration Tips

- Explain that recommendations are generated from live utilization metrics.
- Point out role-based workflow (`operator` approves, `admin` executes).
- Highlight audit logs for governance and accountability.
- End with realized savings from `/savings/summary`.
