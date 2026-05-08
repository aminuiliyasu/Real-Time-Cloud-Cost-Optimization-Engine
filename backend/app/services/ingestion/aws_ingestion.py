from datetime import datetime, timedelta, timezone
import json

from sqlalchemy.orm import Session

from app.models.resource import Resource
from app.models.usage_metric import UsageMetric
from app.services.providers.aws_provider import AwsProvider


def ingest_aws_resources(db: Session) -> dict:
    provider = AwsProvider()
    payload = provider.list_resources()

    inserted = 0
    updated = 0
    for item in payload:
        existing = db.query(Resource).filter(Resource.resource_id == item["resource_id"]).first()
        tag_str = json.dumps(item.get("tags", []))
        if existing:
            existing.cloud_provider = item["cloud_provider"]
            existing.resource_type = item["resource_type"]
            existing.region = item["region"]
            existing.account_id = item["account_id"]
            existing.tags = tag_str
            updated += 1
        else:
            db.add(
                Resource(
                    cloud_provider=item["cloud_provider"],
                    resource_id=item["resource_id"],
                    resource_type=item["resource_type"],
                    region=item["region"],
                    account_id=item["account_id"],
                    tags=tag_str,
                )
            )
            inserted += 1

    db.commit()
    return {"inserted": inserted, "updated": updated}


def ingest_aws_metrics(db: Session, hours: int = 24) -> dict:
    provider = AwsProvider()
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)

    resources = db.query(Resource).filter(Resource.cloud_provider == "aws").all()
    written = 0
    for resource in resources:
        metrics = provider.fetch_cpu_metrics(resource.resource_id, start, end)
        for metric in metrics:
            exists = (
                db.query(UsageMetric)
                .filter(
                    UsageMetric.resource_id == resource.id,
                    UsageMetric.recorded_at == metric["recorded_at"],
                )
                .first()
            )
            if exists:
                continue
            db.add(
                UsageMetric(
                    resource_id=resource.id,
                    cpu_utilization=metric["cpu_utilization"],
                    memory_utilization=None,
                    network_in_mb=None,
                    network_out_mb=None,
                    recorded_at=metric["recorded_at"],
                )
            )
            written += 1

    db.commit()
    return {"resources_scanned": len(resources), "metrics_written": written}


def ingest_aws_ecs_resources(db: Session) -> dict:
    provider = AwsProvider()
    payload = provider.list_ecs_services()

    inserted = 0
    updated = 0
    for item in payload:
        existing = db.query(Resource).filter(Resource.resource_id == item["resource_id"]).first()
        tag_str = json.dumps(item.get("tags", {}))
        if existing:
            existing.cloud_provider = item["cloud_provider"]
            existing.resource_type = item["resource_type"]
            existing.region = item["region"]
            existing.account_id = item["account_id"]
            existing.tags = tag_str
            updated += 1
        else:
            db.add(
                Resource(
                    cloud_provider=item["cloud_provider"],
                    resource_id=item["resource_id"],
                    resource_type=item["resource_type"],
                    region=item["region"],
                    account_id=item["account_id"],
                    tags=tag_str,
                )
            )
            inserted += 1

    db.commit()
    return {"inserted": inserted, "updated": updated}


def ingest_aws_ecs_metrics(db: Session, hours: int = 24) -> dict:
    provider = AwsProvider()
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)

    resources = db.query(Resource).filter(Resource.cloud_provider == "aws", Resource.resource_type == "ecs_service").all()
    written = 0

    for resource in resources:
        try:
            _, cluster_name, service_name = resource.resource_id.split(":", 2)
        except ValueError:
            continue

        metrics = provider.fetch_ecs_metrics(cluster_name, service_name, start, end)
        for metric in metrics:
            exists = (
                db.query(UsageMetric)
                .filter(
                    UsageMetric.resource_id == resource.id,
                    UsageMetric.recorded_at == metric["recorded_at"],
                )
                .first()
            )
            if exists:
                continue

            db.add(
                UsageMetric(
                    resource_id=resource.id,
                    cpu_utilization=metric["cpu_utilization"],
                    memory_utilization=metric["memory_utilization"],
                    network_in_mb=None,
                    network_out_mb=None,
                    recorded_at=metric["recorded_at"],
                )
            )
            written += 1

    db.commit()
    return {"resources_scanned": len(resources), "metrics_written": written}
