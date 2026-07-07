from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.db.session import get_db
from app.schemas.contracts import IngestionMetricsOut, IngestionResourcesOut
from app.services.ingestion.gcp_ingestion import ingest_gcp_metrics, ingest_gcp_resources

router = APIRouter(prefix="/dev/ingest/gcp", tags=["ingestion"])


@router.post("/resources", response_model=IngestionResourcesOut)
def ingest_resources(
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    try:
        result = ingest_gcp_resources(db)
        return {"provider": "gcp", **result}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"gcp resource ingestion failed: {exc}")


@router.post("/metrics", response_model=IngestionMetricsOut)
def ingest_metrics(
    hours: int = 24,
    _authz: None = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    if hours <= 0:
        raise HTTPException(status_code=400, detail="hours must be > 0")

    try:
        result = ingest_gcp_metrics(db, hours=hours)
        return {"provider": "gcp", "hours": hours, **result}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"gcp metric ingestion failed: {exc}")
