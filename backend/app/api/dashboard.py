import json

import redis
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.dashboard import DashboardKpisOut, DashboardTrendsOut
from app.schemas.portfolio import PortfolioSummaryOut
from app.services.analytics.dashboard import get_dashboard_kpis, get_dashboard_trends
from app.services.analytics.portfolio import get_portfolio_summary

router = APIRouter(tags=["dashboard"])

PORTFOLIO_CACHE_KEY = "dashboard:portfolio"
PORTFOLIO_CACHE_TTL = 60


def _redis_client():
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@router.get("/dashboard/kpis", response_model=DashboardKpisOut)
def dashboard_kpis(db: Session = Depends(get_db)):
    return get_dashboard_kpis(db)


@router.get("/dashboard/trends", response_model=DashboardTrendsOut)
def dashboard_trends(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    return get_dashboard_trends(db, hours=hours)


@router.get("/dashboard/portfolio", response_model=PortfolioSummaryOut)
def dashboard_portfolio(db: Session = Depends(get_db)):
    try:
        client = _redis_client()
        cached = client.get(PORTFOLIO_CACHE_KEY)
        if cached:
            return PortfolioSummaryOut.model_validate_json(cached)
    except Exception:
        pass

    summary = get_portfolio_summary(db)
    try:
        client = _redis_client()
        client.setex(PORTFOLIO_CACHE_KEY, PORTFOLIO_CACHE_TTL, summary.model_dump_json())
    except Exception:
        pass
    return summary
