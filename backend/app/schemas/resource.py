from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ResourceCreate(BaseModel):
    cloud_provider: str
    resource_id: str
    resource_type: str
    region: Optional[str] = None
    account_id: Optional[str] = None
    tags: Optional[str] = None


class ResourceOut(BaseModel):
    id: int
    cloud_provider: str
    resource_id: str
    resource_type: str
    region: Optional[str]
    account_id: Optional[str]
    tags: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True