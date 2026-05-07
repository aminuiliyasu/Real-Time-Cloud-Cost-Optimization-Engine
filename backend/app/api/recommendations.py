from datetime import datetime, timedelta, timezone
import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric
from app.schemas.recommendation import RecommendationOut

router = APIRouter(tags=["recommendations"])


@router.post("/usage-metrics/mock/{resource_id}")
def seed_mock_metrics(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="resource not found")

    now = datetime.now(timezone.utc)
    rows = []
    for i in range(12):
        recorded_at = now - timedelta(hours=i)
        rows.append(
            UsageMetric(
                resource_id=resource_id,
                cpu_utilization=round(random.uniform(1.0, 4.5), 2),  # intentionally low
                memory_utilization=round(random.uniform(20.0, 35.0), 2),
                network_in_mb=round(random.uniform(1.0, 8.0), 2),
                network_out_mb=round(random.uniform(1.0, 6.0), 2),
                recorded_at=recorded_at,
            )
        )

    db.add_all(rows)
    db.commit()
    return {"inserted": len(rows), "resource_id": resource_id}


@router.post("/recommendations/run-idle-vm-rule")
def run_idle_vm_rule(db: Session = Depends(get_db)):
    cpu_threshold = 5.0
    min_samples = 6
    created = 0

    resources = db.query(Resource).all()
    for resource in resources:
        avg_cpu = (
            db.query(func.avg(UsageMetric.cpu_utilization))
            .filter(UsageMetric.resource_id == resource.id)
            .scalar()
        )
        sample_count = (
            db.query(func.count(UsageMetric.id))
            .filter(UsageMetric.resource_id == resource.id)
            .scalar()
        )

        if avg_cpu is None or sample_count < min_samples:
            continue

        if float(avg_cpu) < cpu_threshold:
            exists = (
                db.query(Recommendation)
                .filter(
                    Recommendation.resource_id == resource.id,
                    Recommendation.rule_name == "idle_vm",
                    Recommendation.status == "open",
                )
                .first()
            )
            if exists:
                continue

            rec = Recommendation(
                resource_id=resource.id,
                rule_name="idle_vm",
                severity="medium",
                estimated_monthly_savings=25.0,
                confidence_score=0.82,
                action="downsize_instance",
                status="open",
            )
            db.add(rec)
            created += 1

    db.commit()
    return {"created_recommendations": created}


@router.get("/recommendations", response_model=list[RecommendationOut])
def list_recommendations(db: Session = Depends(get_db)):
    return db.query(Recommendation).order_by(Recommendation.id.desc()).all()