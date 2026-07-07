from datetime import datetime

import boto3

from app.core.config import settings
from app.services.providers.base import CloudProvider


class AwsProvider(CloudProvider):
    def __init__(self, profile_name: str | None = None, region_name: str | None = None) -> None:
        session_kwargs: dict[str, str] = {"profile_name": profile_name or settings.aws_profile}
        if region_name:
            session_kwargs["region_name"] = region_name
        session = boto3.Session(**session_kwargs)
        self._profile = profile_name or settings.aws_profile
        self._region = region_name or session.region_name or settings.aws_region
        self._ec2 = session.client("ec2", region_name=self._region)
        self._ecs = session.client("ecs", region_name=self._region)
        self._cw = session.client("cloudwatch", region_name=self._region)
        self._sts = session.client("sts", region_name=self._region)

    def list_resources(self) -> list[dict]:
        account_id = self._sts.get_caller_identity().get("Account", "")
        response = self._ec2.describe_instances()
        resources: list[dict] = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                resources.append(
                    {
                        "cloud_provider": "aws",
                        "resource_id": instance.get("InstanceId", ""),
                        "resource_type": "ec2",
                        "region": self._region,
                        "account_id": account_id,
                        "source_profile": self._profile,
                        "tags": instance.get("Tags", []),
                    }
                )
        return [r for r in resources if r["resource_id"]]

    def fetch_cpu_metrics(self, resource_id: str, start: datetime, end: datetime) -> list[dict]:
        response = self._cw.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": resource_id}],
            StartTime=start,
            EndTime=end,
            Period=3600,
            Statistics=["Average"],
        )
        datapoints = response.get("Datapoints", [])
        datapoints.sort(key=lambda d: d["Timestamp"])
        return [
            {
                "recorded_at": d["Timestamp"],
                "cpu_utilization": float(d.get("Average", 0.0)),
            }
            for d in datapoints
        ]

    def list_ecs_services(self) -> list[dict]:
        account_id = self._sts.get_caller_identity().get("Account", "")
        resources: list[dict] = []

        clusters = self._ecs.list_clusters().get("clusterArns", [])
        for cluster_arn in clusters:
            cluster_name = cluster_arn.split("/")[-1]
            service_arns = self._ecs.list_services(cluster=cluster_arn).get("serviceArns", [])
            if not service_arns:
                continue

            described = self._ecs.describe_services(cluster=cluster_arn, services=service_arns).get("services", [])
            for svc in described:
                service_name = svc.get("serviceName", "")
                if not service_name:
                    continue
                resources.append(
                    {
                        "cloud_provider": "aws",
                        "resource_id": f"ecs:{cluster_name}:{service_name}",
                        "resource_type": "ecs_service",
                        "region": self._region,
                        "account_id": account_id,
                        "source_profile": self._profile,
                        "tags": {
                            "cluster_name": cluster_name,
                            "service_name": service_name,
                            "desired_count": svc.get("desiredCount"),
                            "running_count": svc.get("runningCount"),
                        },
                    }
                )
        return resources

    def fetch_ecs_metrics(self, cluster_name: str, service_name: str, start: datetime, end: datetime) -> list[dict]:
        cpu_response = self._cw.get_metric_statistics(
            Namespace="AWS/ECS",
            MetricName="CPUUtilization",
            Dimensions=[
                {"Name": "ClusterName", "Value": cluster_name},
                {"Name": "ServiceName", "Value": service_name},
            ],
            StartTime=start,
            EndTime=end,
            Period=3600,
            Statistics=["Average"],
        )
        mem_response = self._cw.get_metric_statistics(
            Namespace="AWS/ECS",
            MetricName="MemoryUtilization",
            Dimensions=[
                {"Name": "ClusterName", "Value": cluster_name},
                {"Name": "ServiceName", "Value": service_name},
            ],
            StartTime=start,
            EndTime=end,
            Period=3600,
            Statistics=["Average"],
        )

        cpu_datapoints = {d["Timestamp"]: float(d.get("Average", 0.0)) for d in cpu_response.get("Datapoints", [])}
        mem_datapoints = {d["Timestamp"]: float(d.get("Average", 0.0)) for d in mem_response.get("Datapoints", [])}
        timestamps = sorted(set(cpu_datapoints.keys()) | set(mem_datapoints.keys()))

        return [
            {
                "recorded_at": ts,
                "cpu_utilization": cpu_datapoints.get(ts, 0.0),
                "memory_utilization": mem_datapoints.get(ts),
            }
            for ts in timestamps
        ]
