from datetime import datetime
from pydantic import BaseModel


class RecommendationOut(BaseModel):
    id: int
    resource_id: int
    rule_name: str
    severity: str
    estimated_monthly_savings: float
    confidence_score: float
    action: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True