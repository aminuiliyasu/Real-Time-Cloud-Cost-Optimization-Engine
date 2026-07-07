from datetime import datetime, timedelta, timezone
import json

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resource import Resource
from app.models.usage_metric import UsageMetric
from app.services.ingestion.aws_ingestion import _merge_resource
from app.services.providers.gcp_provider import GcpProvider


def _gcp_project_zones() -> list[tuple[str, str | None]]:
    if not settings.gcp_projects.strip():
        return []
    entries: list[tuple[str, str | None]] = []
    for raw in settings.gcp_projects.split(","):
        part = raw.strip()
        if not part:
            continue
        if ":" in part:
            project, zone = part.split(":", 1)
            entries.append((project.strip(), zone.strip() or None))
        else:
            entries.append((part, None))
    return entries


def ingest_gcp_resources(db: Session) -> dict:
    inserted = 0
    updated = 0
    projects_scanned: list[str] = []
    skipped: list[str] = []

    for project_id, zone in _gcp_project_zones():
        label = f"{project_id}@{zone or 'all-zones'}"
        projects_scanned.append(label)
        try:
            provider = GcpProvider(project_id=project_id, zone=zone)
            for item in provider.list_resources():
                result = _merge_resource(db, item)
                if result == "inserted":
                    inserted += 1
                else:
                    updated += 1
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"{label}: {exc}")

    db.commit()
    return {
        "inserted": inserted,
        "updated": updated,
        "projects_scanned": projects_scanned,
        "skipped": skipped,
    }


def ingest_gcp_metrics(db: Session, hours: int = 24) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    resources = db.query(Resource).filter(Resource.cloud_provider == "gcp", Resource.resource_type == "gce_instance").all()
    written = 0
    skipped: list[str] = []

    for resource in resources:
        project_id = resource.account_id or ""
        zone = None
        if resource.tags:
            try:
                tags = json.loads(resource.tags)
                if isinstance(tags, dict):
                    zone = tags.get("zone")
            except json.JSONDecodeError:
                pass
        try:
            provider = GcpProvider(project_id=project_id, zone=zone)
            metrics = provider.fetch_cpu_metrics(resource.resource_id, start, end)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"{resource.resource_id}: {exc}")
            continue

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
    return {"resources_scanned": len(resources), "metrics_written": written, "skipped": skipped}
