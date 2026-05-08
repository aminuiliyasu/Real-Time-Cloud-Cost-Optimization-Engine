from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric
from app.schemas.dashboard import DashboardKpisOut

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
