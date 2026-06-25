from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric


def run_scheduled_shutdown_rule(db: Session) -> dict[str, int]:
    """Flag idle non-production workloads for nights/weekends shutdown schedules."""
    cpu_threshold = 8.0
    min_samples = 4
    created = 0

    resources = (
        db.query(Resource)
        .filter(Resource.cloud_provider == "aws", Resource.resource_type == "ec2")
        .all()
    )

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

        if float(avg_cpu) >= cpu_threshold:
            continue

        exists = (
            db.query(Recommendation)
            .filter(
                Recommendation.resource_id == resource.id,
                Recommendation.rule_name == "scheduled_shutdown",
                Recommendation.status == "open",
            )
            .first()
        )
        if exists:
            continue

        savings = round(35.0 + max(0.0, (cpu_threshold - float(avg_cpu)) * 3.0), 2)
        db.add(
            Recommendation(
                resource_id=resource.id,
                rule_name="scheduled_shutdown",
                severity="low",
                estimated_monthly_savings=savings,
                confidence_score=0.88,
                action="schedule_shutdown_weeknights",
                status="open",
            )
        )
        created += 1

    db.commit()
    return {"created_recommendations": created}
