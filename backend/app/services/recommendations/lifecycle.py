from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.simulation_run import SimulationRun
from app.models.usage_metric import UsageMetric
from app.schemas.recommendation_actions import (
    ApproveRecommendationRequest,
    ExecuteRecommendationRequest,
)
from app.schemas.savings import SavingsSummaryOut


def get_resource_or_404(db: Session, resource_id: int) -> Resource:
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource


def get_recommendation_or_404(db: Session, recommendation_id: int) -> Recommendation:
    recommendation = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not recommendation:
        raise HTTPException(status_code=404, detail="recommendation not found")
    return recommendation


def list_recommendations(db: Session) -> list[Recommendation]:
    return db.query(Recommendation).order_by(Recommendation.id.desc()).all()


def approve_recommendation(
    db: Session,
    recommendation_id: int,
    payload: ApproveRecommendationRequest,
) -> Recommendation:
    recommendation = get_recommendation_or_404(db, recommendation_id)
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


def execute_recommendation(
    db: Session,
    recommendation_id: int,
    payload: ExecuteRecommendationRequest,
) -> Recommendation:
    recommendation = get_recommendation_or_404(db, recommendation_id)
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


def list_audit_logs(db: Session, recommendation_id: int) -> list[AuditLog]:
    _ = get_recommendation_or_404(db, recommendation_id)
    return (
        db.query(AuditLog)
        .filter(AuditLog.recommendation_id == recommendation_id)
        .order_by(AuditLog.id.desc())
        .all()
    )


def list_simulation_runs(db: Session, recommendation_id: int) -> list[SimulationRun]:
    _ = get_recommendation_or_404(db, recommendation_id)
    return (
        db.query(SimulationRun)
        .filter(SimulationRun.recommendation_id == recommendation_id)
        .order_by(SimulationRun.id.desc())
        .all()
    )


def get_metrics_range(db: Session, resource_id: int) -> dict:
    _ = get_resource_or_404(db, resource_id)
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


def get_savings_summary(db: Session) -> SavingsSummaryOut:
    total = db.query(func.count(Recommendation.id)).scalar() or 0
    open_count = db.query(func.count(Recommendation.id)).filter(Recommendation.status == "open").scalar() or 0
    approved_count = (
        db.query(func.count(Recommendation.id)).filter(Recommendation.status == "approved").scalar() or 0
    )
    executed_count = (
        db.query(func.count(Recommendation.id)).filter(Recommendation.status == "executed").scalar() or 0
    )
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
