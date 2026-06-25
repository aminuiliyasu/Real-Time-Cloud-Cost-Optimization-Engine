from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    reduction_percent: float = Field(..., gt=0, le=90)  # 1..90


class SimulationOut(BaseModel):
    recommendation_id: int
    current_monthly_cost: float
    projected_monthly_cost: float
    projected_monthly_savings: float
    reduction_percent: float
    risk_score: float
    risk_level: str
    trend_direction: str
    trend_percent: float