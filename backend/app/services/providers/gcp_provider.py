from datetime import datetime, timezone

from app.core.config import settings
from app.services.providers.base import CloudProvider


class GcpProvider(CloudProvider):
    """Read-only GCE discovery and Monitoring metrics for a single GCP project."""

    def __init__(self, project_id: str, zone: str | None = None) -> None:
        self._project_id = project_id
        self._zone = zone or settings.gcp_default_zone
        self._compute = None
        self._monitoring = None
        self._zones = None

    def _ensure_clients(self):
        if self._compute is not None:
            return
        try:
            from google.cloud import compute_v1, monitoring_v3
        except ImportError as exc:
            raise RuntimeError(
                "Install google-cloud-compute and google-cloud-monitoring to use GCP ingestion"
            ) from exc
        self._compute = compute_v1.InstancesClient()
        self._monitoring = monitoring_v3.MetricServiceClient()
        self._zones = compute_v1.ZonesClient()

    def list_resources(self) -> list[dict]:
        self._ensure_clients()
        resources: list[dict] = []
        zones = [self._zone] if self._zone else [zone.name for zone in self._zones.list(project=self._project_id)]

        for zone in zones:
            for instance in self._compute.list(project=self._project_id, zone=zone):
                resources.append(
                    {
                        "cloud_provider": "gcp",
                        "resource_id": f"gce:{zone}:{instance.name}",
                        "resource_type": "gce_instance",
                        "region": zone.rsplit("-", 1)[0],
                        "account_id": self._project_id,
                        "source_profile": self._project_id,
                        "tags": {"zone": zone, "machine_type": instance.machine_type.split("/")[-1]},
                    }
                )
        return resources

    def fetch_cpu_metrics(self, resource_id: str, start: datetime, end: datetime) -> list[dict]:
        self._ensure_clients()
        from google.cloud import monitoring_v3

        try:
            _, zone, instance_name = resource_id.split(":", 2)
        except ValueError:
            return []

        interval = monitoring_v3.TimeInterval(
            {
                "end_time": {"seconds": int(end.timestamp())},
                "start_time": {"seconds": int(start.timestamp())},
            }
        )
        filter_str = (
            'metric.type="compute.googleapis.com/instance/cpu/utilization" '
            f'AND resource.labels.instance_id="{instance_name}" '
            f'AND resource.labels.zone="{zone}"'
        )
        request = monitoring_v3.ListTimeSeriesRequest(
            name=f"projects/{self._project_id}",
            filter=filter_str,
            interval=interval,
            view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        )

        points: list[dict] = []
        for series in self._monitoring.list_time_series(request=request):
            for point in series.points:
                recorded_at = point.interval.end_time
                if recorded_at.tzinfo is None:
                    recorded_at = recorded_at.replace(tzinfo=timezone.utc)
                cpu_pct = float(point.value.double_value) * 100.0
                points.append({"recorded_at": recorded_at, "cpu_utilization": round(cpu_pct, 2)})

        points.sort(key=lambda item: item["recorded_at"])
        return points
