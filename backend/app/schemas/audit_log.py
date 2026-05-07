from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class AuditLogOut(BaseModel):
    id: int
    recommendation_id: int
    action: str
    actor: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True