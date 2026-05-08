from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric
from app.schemas.dashboard import DashboardKpisOut, DashboardTrendPointOut, DashboardTrendsOut

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/kpis", response_model=DashboardKpisOut)
def dashboard_kpis(db: Session = Depends(get_db)):
    total_resources = db.query(func.count(Resource.id)).scalar() or 0
    total_recommendations = db.query(func.count(Recommendation.id)).scalar() or 0
    open_recommendations = (
        db.query(func.count(Recommendation.id)).filter(Recommendation.status == "open").scalar() or 0
    )
    approved_recommendations = (
        db.query(func.count(Recommendation.id)).filter(Recommendation.status == "approved").scalar() or 0
    )
    executed_recommendations = (
        db.query(func.count(Recommendation.id)).filter(Recommendation.status == "executed").scalar() or 0
    )
    total_estimated_monthly_savings = (
        db.query(func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0.0)).scalar() or 0.0
    )
    realized_monthly_savings = (
        db.query(func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0.0))
        .filter(Recommendation.status == "executed")
        .scalar()
        or 0.0
    )
    last_metric_at = db.query(func.max(UsageMetric.recorded_at)).scalar()

    return DashboardKpisOut(
        total_resources=int(total_resources),
        total_recommendations=int(total_recommendations),
        open_recommendations=int(open_recommendations),
        approved_recommendations=int(approved_recommendations),
        executed_recommendations=int(executed_recommendations),
        total_estimated_monthly_savings=float(total_estimated_monthly_savings),
        realized_monthly_savings=float(realized_monthly_savings),
        last_metric_at=last_metric_at,
    )


@router.get("/dashboard/trends", response_model=DashboardTrendsOut)
def dashboard_trends(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    window_start = datetime.now(timezone.utc) - timedelta(hours=hours)

    trend_rows = (
        db.query(
            func.date_trunc("hour", UsageMetric.recorded_at).label("bucket_start"),
            func.avg(UsageMetric.cpu_utilization).label("avg_cpu"),
            func.avg(UsageMetric.memory_utilization).label("avg_memory"),
        )
        .filter(UsageMetric.recorded_at >= window_start)
        .group_by(func.date_trunc("hour", UsageMetric.recorded_at))
        .order_by(func.date_trunc("hour", UsageMetric.recorded_at).asc())
        .all()
    )

    open_monthly_savings = (
        db.query(func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0.0))
        .filter(Recommendation.status == "open")
        .scalar()
        or 0.0
    )
    estimated_hourly_savings_potential = float(open_monthly_savings) / 730.0

    points = [
        DashboardTrendPointOut(
            bucket_start=row.bucket_start,
            avg_cpu_utilization=float(row.avg_cpu or 0.0),
            avg_memory_utilization=float(row.avg_memory or 0.0),
            estimated_hourly_savings_potential=round(estimated_hourly_savings_potential, 4),
        )
        for row in trend_rows
    ]

    return DashboardTrendsOut(hours=hours, points=points)
