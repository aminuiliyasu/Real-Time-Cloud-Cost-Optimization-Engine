from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardKpisOut, DashboardTrendsOut
from app.services.analytics.dashboard import get_dashboard_kpis, get_dashboard_trends

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/kpis", response_model=DashboardKpisOut)
def dashboard_kpis(db: Session = Depends(get_db)):
    return get_dashboard_kpis(db)


@router.get("/dashboard/trends", response_model=DashboardTrendsOut)
def dashboard_trends(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    return get_dashboard_trends(db, hours=hours)
