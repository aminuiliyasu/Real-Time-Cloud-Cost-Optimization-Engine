from pydantic import BaseModel


class AccountSummaryOut(BaseModel):
    cloud_provider: str
    account_id: str
    resource_count: int
    open_recommendations: int
    monthly_savings_potential: float


class OptimizationBreakdownOut(BaseModel):
    rightsizing: int
    scheduled_shutdown: int
    migration: int
    other: int


class PortfolioSummaryOut(BaseModel):
    accounts_monitored: int
    cloud_providers: list[str]
    total_resources: int
    total_recommendations: int
    open_recommendations: int
    monthly_waste_identified: float
    annual_waste_identified: float
    realized_monthly_savings: float
    manual_review_reduction_pct: int
    optimization_breakdown: OptimizationBreakdownOut
    accounts: list[AccountSummaryOut]
    last_sync_at: str | None
