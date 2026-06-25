from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric


def run_migration_candidate_rule(db: Session) -> dict[str, int]:
    """Suggest lower-cost instance families when sustained utilization is low."""
    cpu_threshold = 15.0
    min_samples = 6
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

        cpu = float(avg_cpu)
        if cpu >= cpu_threshold or cpu < 5.0:
            continue

        exists = (
            db.query(Recommendation)
            .filter(
                Recommendation.resource_id == resource.id,
                Recommendation.rule_name == "migration_candidate",
                Recommendation.status == "open",
            )
            .first()
        )
        if exists:
            continue

        gap = (cpu_threshold - cpu) / cpu_threshold
        savings = round(45.0 + gap * 55.0, 2)
        db.add(
            Recommendation(
                resource_id=resource.id,
                rule_name="migration_candidate",
                severity="medium",
                estimated_monthly_savings=savings,
                confidence_score=round(min(0.75 + gap * 0.2, 0.93), 2),
                action="migrate_to_smaller_instance_family",
                status="open",
            )
        )
        created += 1

    db.commit()
    return {"created_recommendations": created}
