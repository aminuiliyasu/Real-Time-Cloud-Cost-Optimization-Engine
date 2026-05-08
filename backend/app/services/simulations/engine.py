from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.simulation_run import SimulationRun
from app.models.usage_metric import UsageMetric
from app.schemas.simulation import SimulationOut, SimulationRequest
from app.services.costs.baseline import compute_metric_based_baseline


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


def run_recommendation_simulation(
    db: Session,
    recommendation: Recommendation,
    payload: SimulationRequest,
) -> SimulationOut:
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
