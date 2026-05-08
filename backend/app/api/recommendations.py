from datetime import datetime, timedelta, timezone
import random
from app.schemas.savings import SavingsSummaryOut
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.schemas.simulation import SimulationRequest, SimulationOut

from app.db.session import get_db
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.simulation_run import SimulationRun
from app.models.usage_metric import UsageMetric
from app.schemas.audit_log import AuditLogOut
from app.schemas.recommendation_actions import (
    ApproveRecommendationRequest,
    ExecuteRecommendationRequest,
)
from app.schemas.recommendation import RecommendationOut
from app.schemas.simulation_run import SimulationRunOut
from app.models.audit_log import AuditLog
from app.core.config import settings
from app.core.auth import require_roles

router = APIRouter(tags=["recommendations"])


def compute_metric_based_baseline(avg_cpu: float, avg_mem: float | None) -> float:
    """
    Simple cost heuristic:
    - base floor cost = 40
    - cpu contributes up to 60
    - memory contributes up to 40 (if present)
    """
    cpu_component = min(max(avg_cpu, 0.0), 100.0) * 0.6
    mem_component = (min(max(avg_mem or 0.0, 0.0), 100.0) * 0.4) if avg_mem is not None else 10.0
    return round(40.0 + cpu_component + mem_component, 2)


def compute_trend_percent(current_avg: float | None, previous_avg: float | None) -> tuple[str, float]:
    if current_avg is None or previous_avg is None or previous_avg == 0:
        return "insufficient_data", 0.0

    change = ((current_avg - previous_avg) / previous_avg) * 100
    if change > 5:
        direction = "up"
    elif change < -5:
        direction = "down"
    else:
        direction = "flat"
    return direction, round(change, 2)


def ensure_dev_mode() -> None:
    if settings.app_env.lower() != "development":
        raise HTTPException(status_code=403, detail="dev endpoint disabled outside development")


@router.post("/dev/usage-metrics/mock/{resource_id}")
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


@router.post("/dev/usage-metrics/backfill/{resource_id}")
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


@router.get("/usage-metrics/range/{resource_id}")
def metrics_range(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="resource not found")

    min_ts = (
        db.query(func.min(UsageMetric.recorded_at))
        .filter(UsageMetric.resource_id == resource_id)
        .scalar()
    )
    max_ts = (
        db.query(func.max(UsageMetric.recorded_at))
        .filter(UsageMetric.resource_id == resource_id)
        .scalar()
    )
    count = (
        db.query(func.count(UsageMetric.id))
        .filter(UsageMetric.resource_id == resource_id)
        .scalar()
    )

    return {
        "resource_id": resource_id,
        "count": int(count or 0),
        "min_recorded_at": min_ts,
        "max_recorded_at": max_ts,
    }


@router.post("/dev/recommendations/run-idle-vm-rule")
def run_idle_vm_rule(
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    ensure_dev_mode()
    cpu_threshold = 5.0
    min_samples = 6
    created = 0

    resources = db.query(Resource).all()
    for resource in resources:
        avg_cpu = (
            db.query(func.avg(UsageMetric.cpu_utilization))
            .filter(UsageMetric.resource_id == resource.id)
            .scalar()
        )
        sample_count = (
            db.query(func.count(UsageMetric.id))
            .filter(UsageMetric.resource_id == resource.id)
            .scalar()
        )

        if avg_cpu is None or sample_count < min_samples:
            continue

        if float(avg_cpu) < cpu_threshold:
            exists = (
                db.query(Recommendation)
                .filter(
                    Recommendation.resource_id == resource.id,
                    Recommendation.rule_name == "idle_vm",
                    Recommendation.status == "open",
                )
                .first()
            )
            if exists:
                continue

            rec = Recommendation(
                resource_id=resource.id,
                rule_name="idle_vm",
                severity="medium",
                estimated_monthly_savings=25.0,
                confidence_score=0.82,
                action="downsize_instance",
                status="open",
            )
            db.add(rec)
            created += 1

    db.commit()
    return {"created_recommendations": created}


@router.get("/recommendations", response_model=list[RecommendationOut])
def list_recommendations(db: Session = Depends(get_db)):
    return db.query(Recommendation).order_by(Recommendation.id.desc()).all()


@router.post("/recommendations/{recommendation_id}/approve", response_model=RecommendationOut)
def approve_recommendation(
    recommendation_id: int,
    payload: ApproveRecommendationRequest,
    _authz: None = Depends(require_roles(["operator", "admin"])),
    db: Session = Depends(get_db),
):
    recommendation = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not recommendation:
        raise HTTPException(status_code=404, detail="recommendation not found")

    if recommendation.status != "open":
        raise HTTPException(status_code=400, detail="only open recommendations can be approved")

    recommendation.status = "approved"
    db.add(
        AuditLog(
            recommendation_id=recommendation.id,
            action="approved",
            actor=payload.actor,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.post("/recommendations/{recommendation_id}/execute", response_model=RecommendationOut)
def execute_recommendation(
    recommendation_id: int,
    payload: ExecuteRecommendationRequest,
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    recommendation = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not recommendation:
        raise HTTPException(status_code=404, detail="recommendation not found")

    if recommendation.status != "approved":
        raise HTTPException(status_code=400, detail="only approved recommendations can be executed")

    recommendation.status = "executed"
    db.add(
        AuditLog(
            recommendation_id=recommendation.id,
            action="executed",
            actor=payload.actor,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.get("/recommendations/{recommendation_id}/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(recommendation_id: int, db: Session = Depends(get_db)):
    recommendation = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not recommendation:
        raise HTTPException(status_code=404, detail="recommendation not found")

    return (
        db.query(AuditLog)
        .filter(AuditLog.recommendation_id == recommendation_id)
        .order_by(AuditLog.id.desc())
        .all()
    )



@router.get("/savings/summary", response_model=SavingsSummaryOut)
def savings_summary(db: Session = Depends(get_db)):
    total = db.query(func.count(Recommendation.id)).scalar() or 0
    open_count = db.query(func.count(Recommendation.id)).filter(Recommendation.status == "open").scalar() or 0
    approved_count = db.query(func.count(Recommendation.id)).filter(Recommendation.status == "approved").scalar() or 0
    executed_count = db.query(func.count(Recommendation.id)).filter(Recommendation.status == "executed").scalar() or 0

    total_estimated = (
        db.query(func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0.0)).scalar() or 0.0
    )
    realized = (
        db.query(func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0.0))
        .filter(Recommendation.status == "executed")
        .scalar()
        or 0.0
    )

    return SavingsSummaryOut(
        total_recommendations=int(total),
        open_recommendations=int(open_count),
        approved_recommendations=int(approved_count),
        executed_recommendations=int(executed_count),
        total_estimated_monthly_savings=float(total_estimated),
        realized_monthly_savings=float(realized),
    )


@router.post("/recommendations/{recommendation_id}/simulate", response_model=SimulationOut)
def simulate_recommendation(
    recommendation_id: int,
    payload: SimulationRequest,
    db: Session = Depends(get_db),
):
    recommendation = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not recommendation:
        raise HTTPException(status_code=404, detail="recommendation not found")

    avg_cpu = (
        db.query(func.avg(UsageMetric.cpu_utilization))
        .filter(UsageMetric.resource_id == recommendation.resource_id)
        .scalar()
    )
    avg_mem = (
        db.query(func.avg(UsageMetric.memory_utilization))
        .filter(UsageMetric.resource_id == recommendation.resource_id)
        .scalar()
    )
    now = datetime.now(timezone.utc)
    current_window_start = now - timedelta(hours=24)
    previous_window_start = now - timedelta(hours=48)

    current_avg_cpu = (
        db.query(func.avg(UsageMetric.cpu_utilization))
        .filter(
            UsageMetric.resource_id == recommendation.resource_id,
            UsageMetric.recorded_at >= current_window_start,
            UsageMetric.recorded_at <= now,
        )
        .scalar()
    )
    previous_avg_cpu = (
        db.query(func.avg(UsageMetric.cpu_utilization))
        .filter(
            UsageMetric.resource_id == recommendation.resource_id,
            UsageMetric.recorded_at >= previous_window_start,
            UsageMetric.recorded_at < current_window_start,
        )
        .scalar()
    )
    trend_direction, trend_percent = compute_trend_percent(
        float(current_avg_cpu) if current_avg_cpu is not None else None,
        float(previous_avg_cpu) if previous_avg_cpu is not None else None,
    )

    if avg_cpu is None:
        current_monthly_cost = max(recommendation.estimated_monthly_savings * 4, 1.0)
    else:
        current_monthly_cost = compute_metric_based_baseline(
            float(avg_cpu),
            float(avg_mem) if avg_mem is not None else None,
        )

    projected_monthly_cost = current_monthly_cost * (1 - payload.reduction_percent / 100)
    projected_monthly_savings = current_monthly_cost - projected_monthly_cost

    base_risk = payload.reduction_percent / 100.0
    utilization_pressure = 0.0
    if avg_cpu is not None:
        utilization_pressure += min(float(avg_cpu) / 100.0, 1.0) * 0.5
    if avg_mem is not None:
        utilization_pressure += min(float(avg_mem) / 100.0, 1.0) * 0.3

    risk_score = min(base_risk + utilization_pressure, 0.95)
    if trend_direction == "up" and trend_percent > 10:
        risk_score = min(risk_score + 0.1, 0.95)
    elif trend_direction == "down" and trend_percent < -10:
        risk_score = max(risk_score - 0.05, 0.0)

    if risk_score < 0.30:
        risk_level = "low"
    elif risk_score < 0.60:
        risk_level = "medium"
    else:
        risk_level = "high"

    simulation = SimulationRun(
        recommendation_id=recommendation.id,
        reduction_percent=payload.reduction_percent,
        current_monthly_cost=round(current_monthly_cost, 2),
        projected_monthly_cost=round(projected_monthly_cost, 2),
        projected_monthly_savings=round(projected_monthly_savings, 2),
        risk_score=round(risk_score, 2),
        risk_level=risk_level,
    )
    db.add(simulation)
    db.commit()

    return SimulationOut(
        recommendation_id=recommendation.id,
        current_monthly_cost=round(current_monthly_cost, 2),
        projected_monthly_cost=round(projected_monthly_cost, 2),
        projected_monthly_savings=round(projected_monthly_savings, 2),
        reduction_percent=payload.reduction_percent,
        risk_score=round(risk_score, 2),
        risk_level=risk_level,
        trend_direction=trend_direction,
        trend_percent=trend_percent,
    )


@router.get("/recommendations/{recommendation_id}/simulations", response_model=list[SimulationRunOut])
def list_simulation_runs(recommendation_id: int, db: Session = Depends(get_db)):
    recommendation = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not recommendation:
        raise HTTPException(status_code=404, detail="recommendation not found")

    return (
        db.query(SimulationRun)
        .filter(SimulationRun.recommendation_id == recommendation_id)
        .order_by(SimulationRun.id.desc())
        .all()
    )