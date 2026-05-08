from datetime import datetime

from pydantic import BaseModel


class ResourceOperationOut(BaseModel):
    inserted: int
    updated: int


class IngestionResourcesOut(BaseModel):
    provider: str
    inserted: int
    updated: int


class IngestionMetricsOut(BaseModel):
    provider: str
    hours: int
    resources_scanned: int
    metrics_written: int


class IngestionEcsResourcesOut(BaseModel):
    provider: str
    resource_type: str
    inserted: int
    updated: int


class IngestionEcsMetricsOut(BaseModel):
    provider: str
    resource_type: str
    hours: int
    resources_scanned: int
    metrics_written: int


class UsageMetricsWriteOut(BaseModel):
    inserted: int
    resource_id: int


class UsageMetricsRangeOut(BaseModel):
    resource_id: int
    count: int
    min_recorded_at: datetime | None
    max_recorded_at: datetime | None


class IdleVmRuleRunOut(BaseModel):
    created_recommendations: int


class EcsRuleThresholdsOut(BaseModel):
    cpu_utilization_pct: float
    memory_utilization_pct: float
    min_samples: int


class EcsUnderutilizedRuleRunOut(BaseModel):
    scanned_services: int
    created_recommendations: int
    skipped_existing: int
    window_hours: int
    thresholds: EcsRuleThresholdsOut
