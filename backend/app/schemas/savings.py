from pydantic import BaseModel


class SavingsSummaryOut(BaseModel):
    total_recommendations: int
    open_recommendations: int
    approved_recommendations: int
    executed_recommendations: int
    total_estimated_monthly_savings: float
    realized_monthly_savings: float