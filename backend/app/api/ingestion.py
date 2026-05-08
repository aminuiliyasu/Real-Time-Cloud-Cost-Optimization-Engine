from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.db.session import get_db
from app.services.ingestion.aws_ingestion import (
    ingest_aws_ecs_metrics,
    ingest_aws_ecs_resources,
    ingest_aws_metrics,
    ingest_aws_resources,
)

router = APIRouter(prefix="/dev/ingest/aws", tags=["ingestion"])


@router.post("/resources")
def ingest_resources(
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    try:
        result = ingest_aws_resources(db)
        return {"provider": "aws", **result}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"aws resource ingestion failed: {exc}")


@router.post("/metrics")
def ingest_metrics(
    hours: int = 24,
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    if hours <= 0:
        raise HTTPException(status_code=400, detail="hours must be > 0")

    try:
        result = ingest_aws_metrics(db, hours=hours)
        return {"provider": "aws", "hours": hours, **result}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"aws metric ingestion failed: {exc}")


@router.post("/ecs/resources")
def ingest_ecs_resources(
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    try:
        result = ingest_aws_ecs_resources(db)
        return {"provider": "aws", "resource_type": "ecs_service", **result}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"aws ecs resource ingestion failed: {exc}")


@router.post("/ecs/metrics")
def ingest_ecs_metrics(
    hours: int = 24,
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    if hours <= 0:
        raise HTTPException(status_code=400, detail="hours must be > 0")

    try:
        result = ingest_aws_ecs_metrics(db, hours=hours)
        return {"provider": "aws", "resource_type": "ecs_service", "hours": hours, **result}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"aws ecs metric ingestion failed: {exc}")
