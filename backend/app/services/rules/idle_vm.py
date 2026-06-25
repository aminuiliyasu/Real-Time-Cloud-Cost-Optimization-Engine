from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric


def run_idle_vm_rule(db: Session) -> dict[str, int]:
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
                action="rightsizing_downsize_instance",
                status="open",
            )
            db.add(rec)
            created += 1

    db.commit()
    return {"created_recommendations": created}
