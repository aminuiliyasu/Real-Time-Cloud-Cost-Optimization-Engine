from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric


def run_ecs_underutilized_rule(db: Session) -> dict:
    cpu_threshold = 20.0
    memory_threshold = 30.0
    min_samples = 6
    window_start = datetime.now(timezone.utc) - timedelta(hours=24)

    scanned_services = 0
    created_recommendations = 0
    skipped_existing = 0

    ecs_resources = (
        db.query(Resource)
        .filter(
            Resource.cloud_provider == "aws",
            Resource.resource_type == "ecs_service",
        )
        .all()
    )

    for resource in ecs_resources:
        scanned_services += 1
        avg_cpu = (
            db.query(func.avg(UsageMetric.cpu_utilization))
            .filter(
                UsageMetric.resource_id == resource.id,
                UsageMetric.recorded_at >= window_start,
            )
            .scalar()
        )
        avg_mem = (
            db.query(func.avg(UsageMetric.memory_utilization))
            .filter(
                UsageMetric.resource_id == resource.id,
                UsageMetric.recorded_at >= window_start,
            )
            .scalar()
        )
        sample_count = (
            db.query(func.count(UsageMetric.id))
            .filter(
                UsageMetric.resource_id == resource.id,
                UsageMetric.recorded_at >= window_start,
            )
            .scalar()
        )

        if avg_cpu is None or avg_mem is None or sample_count < min_samples:
            continue

        if float(avg_cpu) < cpu_threshold and float(avg_mem) < memory_threshold:
            exists = (
                db.query(Recommendation)
                .filter(
                    Recommendation.resource_id == resource.id,
                    Recommendation.rule_name == "ecs_underutilized_service",
                    Recommendation.status == "open",
                )
                .first()
            )
            if exists:
                skipped_existing += 1
                continue

            cpu_gap_ratio = max((cpu_threshold - float(avg_cpu)) / cpu_threshold, 0.0)
            mem_gap_ratio = max((memory_threshold - float(avg_mem)) / memory_threshold, 0.0)
            savings_estimate = round(30.0 + (cpu_gap_ratio * 20.0) + (mem_gap_ratio * 20.0), 2)
            confidence = round(min(0.7 + ((cpu_gap_ratio + mem_gap_ratio) / 4.0), 0.95), 2)

            rec = Recommendation(
                resource_id=resource.id,
                rule_name="ecs_underutilized_service",
                severity="medium",
                estimated_monthly_savings=savings_estimate,
                confidence_score=confidence,
                action="reduce_task_size_or_scale_schedule",
                status="open",
            )
            db.add(rec)
            created_recommendations += 1

    db.commit()
    return {
        "scanned_services": scanned_services,
        "created_recommendations": created_recommendations,
        "skipped_existing": skipped_existing,
        "window_hours": 24,
        "thresholds": {
            "cpu_utilization_pct": cpu_threshold,
            "memory_utilization_pct": memory_threshold,
            "min_samples": min_samples,
        },
    }
