from datetime import datetime, timedelta, timezone
import random
from app.schemas.savings import SavingsSummaryOut
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.simulation import SimulationRequest, SimulationOut

from app.db.session import get_db
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric
from app.schemas.audit_log import AuditLogOut
from app.schemas.recommendation_actions import (
    ApproveRecommendationRequest,
    ExecuteRecommendationRequest,
)
from app.schemas.recommendation import RecommendationOut
from app.schemas.simulation_run import SimulationRunOut
from app.core.config import settings
from app.core.auth import require_roles
from app.schemas.contracts import (
    EcsUnderutilizedRuleRunOut,
    FullAnalysisPipelineOut,
    IdleVmRuleRunOut,
    MigrationCandidateRuleRunOut,
    ScheduledShutdownRuleRunOut,
    UsageMetricsRangeOut,
    UsageMetricsWriteOut,
)
from app.services.rules.idle_vm import run_idle_vm_rule as run_idle_vm_rule_service
from app.services.rules.ecs_underutilized import (
    run_ecs_underutilized_rule as run_ecs_underutilized_rule_service,
)
from app.services.rules.migration_candidate import run_migration_candidate_rule
from app.services.rules.scheduled_shutdown import run_scheduled_shutdown_rule
from app.services.pipeline import run_full_analysis_pipeline
from app.services.simulations.engine import run_recommendation_simulation
from app.services.recommendations.lifecycle import (
    approve_recommendation as approve_recommendation_service,
    execute_recommendation as execute_recommendation_service,
    get_metrics_range,
    get_recommendation_or_404,
    get_savings_summary,
    list_audit_logs as list_audit_logs_service,
    list_recommendations as list_recommendations_service,
    list_simulation_runs as list_simulation_runs_service,
)

router = APIRouter(tags=["recommendations"])

def ensure_dev_mode() -> None:
    if settings.app_env.lower() != "development":
        raise HTTPException(status_code=403, detail="dev endpoint disabled outside development")


@router.post("/dev/usage-metrics/mock/{resource_id}", response_model=UsageMetricsWriteOut)
def seed_mock_metrics(
    resource_id: int,
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    ensure_dev_mode()
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="resource not found")

    now = datetime.now(timezone.utc)
    rows = []
    for i in range(12):
        recorded_at = now - timedelta(hours=i)
        rows.append(
            UsageMetric(
                resource_id=resource_id,
                cpu_utilization=round(random.uniform(1.0, 4.5), 2),  # intentionally low
                memory_utilization=round(random.uniform(20.0, 35.0), 2),
                network_in_mb=round(random.uniform(1.0, 8.0), 2),
                network_out_mb=round(random.uniform(1.0, 6.0), 2),
                recorded_at=recorded_at,
            )
        )

    db.add_all(rows)
    db.commit()
    return {"inserted": len(rows), "resource_id": resource_id}


@router.post("/dev/usage-metrics/backfill/{resource_id}", response_model=UsageMetricsWriteOut)
def backfill_metrics(
    resource_id: int,
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    ensure_dev_mode()
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="resource not found")

    now = datetime.now(timezone.utc)
    rows = []
    # 72 hourly samples: enough for current 24h + previous 24h windows
    for i in range(72):
        recorded_at = now - timedelta(hours=i)

        # synthetic trend: older half lower load, recent half higher load
        if i >= 36:
            cpu = round(random.uniform(2.0, 6.0), 2)
            mem = round(random.uniform(20.0, 35.0), 2)
        else:
            cpu = round(random.uniform(6.0, 14.0), 2)
            mem = round(random.uniform(30.0, 50.0), 2)

        rows.append(
            UsageMetric(
                resource_id=resource_id,
                cpu_utilization=cpu,
                memory_utilization=mem,
                network_in_mb=round(random.uniform(2.0, 15.0), 2),
                network_out_mb=round(random.uniform(2.0, 12.0), 2),
                recorded_at=recorded_at,
            )
        )

    db.add_all(rows)
    db.commit()
    return {"inserted": len(rows), "resource_id": resource_id}


@router.get("/usage-metrics/range/{resource_id}", response_model=UsageMetricsRangeOut)
def metrics_range(resource_id: int, db: Session = Depends(get_db)):
    return get_metrics_range(db, resource_id)


@router.post("/dev/recommendations/run-idle-vm-rule", response_model=IdleVmRuleRunOut)
def run_idle_vm_rule(
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    ensure_dev_mode()
    return run_idle_vm_rule_service(db)


@router.post(
    "/dev/recommendations/run-ecs-underutilized-rule",
    response_model=EcsUnderutilizedRuleRunOut,
)
def run_ecs_underutilized_rule(
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    ensure_dev_mode()
    return run_ecs_underutilized_rule_service(db)


@router.post("/dev/recommendations/run-scheduled-shutdown-rule", response_model=ScheduledShutdownRuleRunOut)
def run_scheduled_shutdown_rule_endpoint(
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    ensure_dev_mode()
    return run_scheduled_shutdown_rule(db)


@router.post("/dev/recommendations/run-migration-candidate-rule", response_model=MigrationCandidateRuleRunOut)
def run_migration_candidate_rule_endpoint(
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    ensure_dev_mode()
    return run_migration_candidate_rule(db)


@router.post("/dev/pipeline/run-full-analysis", response_model=FullAnalysisPipelineOut)
def run_full_analysis(
    hours: int = 24,
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    ensure_dev_mode()
    if hours <= 0:
        raise HTTPException(status_code=400, detail="hours must be > 0")
    return run_full_analysis_pipeline(db, hours=hours)


@router.get("/recommendations", response_model=list[RecommendationOut])
def list_recommendations(db: Session = Depends(get_db)):
    return list_recommendations_service(db)


@router.post("/recommendations/{recommendation_id}/approve", response_model=RecommendationOut)
def approve_recommendation(
    recommendation_id: int,
    payload: ApproveRecommendationRequest,
    _authz: None = Depends(require_roles(["operator", "admin"])),
    db: Session = Depends(get_db),
):
    return approve_recommendation_service(db, recommendation_id, payload)


@router.post("/recommendations/{recommendation_id}/execute", response_model=RecommendationOut)
def execute_recommendation(
    recommendation_id: int,
    payload: ExecuteRecommendationRequest,
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    return execute_recommendation_service(db, recommendation_id, payload)


@router.get("/recommendations/{recommendation_id}/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(recommendation_id: int, db: Session = Depends(get_db)):
    return list_audit_logs_service(db, recommendation_id)



@router.get("/savings/summary", response_model=SavingsSummaryOut)
def savings_summary(db: Session = Depends(get_db)):
    return get_savings_summary(db)


@router.post("/recommendations/{recommendation_id}/simulate", response_model=SimulationOut)
def simulate_recommendation(
    recommendation_id: int,
    payload: SimulationRequest,
    db: Session = Depends(get_db),
):
    recommendation = get_recommendation_or_404(db, recommendation_id)
    return run_recommendation_simulation(db, recommendation, payload)


@router.get("/recommendations/{recommendation_id}/simulations", response_model=list[SimulationRunOut])
def list_simulation_runs(recommendation_id: int, db: Session = Depends(get_db)):
    return list_simulation_runs_service(db, recommendation_id)