from sqlalchemy.orm import Session

from app.services.analytics.portfolio import get_portfolio_summary
from app.services.ingestion.aws_ingestion import (
    ingest_aws_ecs_metrics,
    ingest_aws_ecs_resources,
    ingest_aws_metrics,
    ingest_aws_resources,
)
from app.services.rules.ecs_underutilized import run_ecs_underutilized_rule
from app.services.rules.idle_vm import run_idle_vm_rule
from app.services.rules.migration_candidate import run_migration_candidate_rule
from app.services.rules.scheduled_shutdown import run_scheduled_shutdown_rule


def run_full_analysis_pipeline(db: Session, hours: int = 24) -> dict:
    ec2_resources = ingest_aws_resources(db)
    ecs_resources = ingest_aws_ecs_resources(db)
    ec2_metrics = ingest_aws_metrics(db, hours=hours)
    ecs_metrics = ingest_aws_ecs_metrics(db, hours=hours)

    ecs_rule = run_ecs_underutilized_rule(db)
    idle_rule = run_idle_vm_rule(db)
    shutdown_rule = run_scheduled_shutdown_rule(db)
    migration_rule = run_migration_candidate_rule(db)

    portfolio = get_portfolio_summary(db)

    return {
        "hours": hours,
        "ingestion": {
            "ec2_resources": ec2_resources,
            "ecs_resources": ecs_resources,
            "ec2_metrics": ec2_metrics,
            "ecs_metrics": ecs_metrics,
        },
        "rules": {
            "ecs_underutilized": ecs_rule,
            "idle_vm": idle_rule,
            "scheduled_shutdown": shutdown_rule,
            "migration_candidate": migration_rule,
        },
        "portfolio": portfolio.model_dump(),
    }
