from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.services.ingestion.aws_ingestion import ingest_aws_ecs_metrics, ingest_aws_ecs_resources
from app.services.rules.ecs_underutilized import run_ecs_underutilized_rule
from app.services.rules.idle_vm import run_idle_vm_rule


def run_ingestion_cycle(hours: int = 24) -> dict:
    db = SessionLocal()
    try:
        resources_result = ingest_aws_ecs_resources(db)
        metrics_result = ingest_aws_ecs_metrics(db, hours=hours)
        return {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "hours": hours,
            "resources": resources_result,
            "metrics": metrics_result,
        }
    finally:
        db.close()


def run_rule_evaluation_cycle() -> dict:
    db = SessionLocal()
    try:
        ecs_result = run_ecs_underutilized_rule(db)
        idle_vm_result = run_idle_vm_rule(db)
        return {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ecs_underutilized": ecs_result,
            "idle_vm": idle_vm_result,
        }
    finally:
        db.close()
