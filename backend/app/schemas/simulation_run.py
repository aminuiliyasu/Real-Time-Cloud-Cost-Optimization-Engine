from datetime import datetime

from pydantic import BaseModel


class SimulationRunOut(BaseModel):
    id: int
    recommendation_id: int
    reduction_percent: float
    current_monthly_cost: float
    projected_monthly_cost: float
    projected_monthly_savings: float
    risk_score: float
    risk_level: str
    created_at: datetime

    class Config:
        from_attributes = True
