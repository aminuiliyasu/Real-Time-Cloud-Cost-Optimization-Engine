from pydantic import BaseModel
from typing import Optional


class ApproveRecommendationRequest(BaseModel):
    actor: str = "operator"
    notes: Optional[str] = None


class ExecuteRecommendationRequest(BaseModel):
    actor: str = "system"
    notes: Optional[str] = None