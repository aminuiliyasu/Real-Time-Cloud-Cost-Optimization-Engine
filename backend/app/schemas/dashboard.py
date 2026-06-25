from datetime import datetime

from pydantic import BaseModel


class DashboardKpisOut(BaseModel):
    total_resources: int
    total_recommendations: int
    open_recommendations: int
    approved_recommendations: int
    executed_recommendations: int
    total_estimated_monthly_savings: float
    realized_monthly_savings: float
    last_metric_at: datetime | None


class DashboardTrendPointOut(BaseModel):
    bucket_start: datetime
    avg_cpu_utilization: float
    avg_memory_utilization: float
    estimated_hourly_savings_potential: float


class DashboardTrendsOut(BaseModel):
    hours: int
    points: list[DashboardTrendPointOut]
