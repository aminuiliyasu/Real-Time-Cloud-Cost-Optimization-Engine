from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric
from app.services.costs.savings import estimate_rightsizing_savings


def run_idle_vm_rule(db: Session) -> dict[str, int]:
    cpu_threshold = 5.0
    min_samples = 6
    created = 0

    resources = (
        db.query(Resource)
        .filter(Resource.resource_type.in_(["ec2", "gce_instance"]))
        .all()
    )
    for resource in resources:
        avg_cpu = (
            db.query(func.avg(UsageMetric.cpu_utilization))
            .filter(UsageMetric.resource_id == resource.id)
            .scalar()
        )
        avg_mem = (
            db.query(func.avg(UsageMetric.memory_utilization))
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

            savings = estimate_rightsizing_savings(float(avg_cpu), float(avg_mem) if avg_mem else None)
            rec = Recommendation(
                resource_id=resource.id,
                rule_name="idle_vm",
                severity="medium",
                estimated_monthly_savings=savings,
                confidence_score=0.82,
                action="rightsizing_downsize_instance",
                status="open",
            )
            db.add(rec)
            created += 1

    db.commit()
    return {"created_recommendations": created}
