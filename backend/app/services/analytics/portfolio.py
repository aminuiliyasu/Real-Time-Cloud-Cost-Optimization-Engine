from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric
from app.schemas.portfolio import (
    AccountSummaryOut,
    OptimizationBreakdownOut,
    PortfolioSummaryOut,
)


def _action_category(action: str | None) -> str:
    action_lower = (action or "").lower()
    if "shutdown" in action_lower or "schedule" in action_lower:
        return "scheduled_shutdown"
    if "migrate" in action_lower or "migration" in action_lower:
        return "migration"
    if "downsize" in action_lower or "rightsiz" in action_lower or "reduce" in action_lower:
        return "rightsizing"
    return "other"


def get_portfolio_summary(db: Session) -> PortfolioSummaryOut:
    total_resources = int(db.query(func.count(Resource.id)).scalar() or 0)
    total_recommendations = int(db.query(func.count(Recommendation.id)).scalar() or 0)
    open_recommendations = int(
        db.query(func.count(Recommendation.id)).filter(Recommendation.status == "open").scalar() or 0
    )
    monthly_waste = float(
        db.query(func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0.0)).scalar() or 0.0
    )
    realized_monthly = float(
        db.query(func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0.0))
        .filter(Recommendation.status == "executed")
        .scalar()
        or 0.0
    )

    providers = [
        row[0]
        for row in db.query(Resource.cloud_provider).distinct().order_by(Resource.cloud_provider).all()
        if row[0]
    ]

    account_rows = (
        db.query(
            Resource.cloud_provider,
            Resource.account_id,
            func.count(Resource.id).label("resource_count"),
        )
        .filter(Resource.account_id.isnot(None))
        .group_by(Resource.cloud_provider, Resource.account_id)
        .order_by(Resource.cloud_provider, Resource.account_id)
        .all()
    )

    accounts: list[AccountSummaryOut] = []
    for row in account_rows:
        open_count = (
            db.query(func.count(Recommendation.id))
            .join(Resource, Recommendation.resource_id == Resource.id)
            .filter(
                Resource.account_id == row.account_id,
                Resource.cloud_provider == row.cloud_provider,
                Recommendation.status == "open",
            )
            .scalar()
            or 0
        )
        monthly_for_account = (
            db.query(func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0.0))
            .join(Resource, Recommendation.resource_id == Resource.id)
            .filter(
                Resource.account_id == row.account_id,
                Resource.cloud_provider == row.cloud_provider,
            )
            .scalar()
            or 0.0
        )
        accounts.append(
            AccountSummaryOut(
                cloud_provider=row.cloud_provider,
                account_id=row.account_id,
                resource_count=int(row.resource_count),
                open_recommendations=int(open_count),
                monthly_savings_potential=float(monthly_for_account),
            )
        )

    breakdown = OptimizationBreakdownOut(rightsizing=0, scheduled_shutdown=0, migration=0, other=0)
    for rec in db.query(Recommendation).all():
        category = _action_category(rec.action)
        setattr(breakdown, category, getattr(breakdown, category) + 1)

    last_metric_at = db.query(func.max(UsageMetric.recorded_at)).scalar()
    if total_resources > 0:
        automated_coverage_pct = min(100, int(round((total_recommendations / total_resources) * 100)))
    else:
        automated_coverage_pct = 0

    return PortfolioSummaryOut(
        accounts_monitored=len(accounts),
        cloud_providers=providers,
        total_resources=total_resources,
        total_recommendations=total_recommendations,
        open_recommendations=open_recommendations,
        monthly_waste_identified=round(monthly_waste, 2),
        annual_waste_identified=round(monthly_waste * 12, 2),
        realized_monthly_savings=round(realized_monthly, 2),
        automated_coverage_pct=automated_coverage_pct,
        optimization_breakdown=breakdown,
        accounts=accounts,
        last_sync_at=last_metric_at.isoformat() if last_metric_at else None,
    )
