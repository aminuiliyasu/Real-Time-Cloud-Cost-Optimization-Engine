from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.pipeline import run_full_analysis_pipeline


def run_ingestion_cycle(hours: int = 24) -> dict:
    db = SessionLocal()
    try:
        result = run_full_analysis_pipeline(db, hours=hours)
        return {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "hours": hours,
            "ingestion": result["ingestion"],
            "rules": result["rules"],
            "portfolio": result["portfolio"],
        }
    finally:
        db.close()


def run_rule_evaluation_cycle() -> dict:
    """Kept for backwards compatibility with the scheduler CLI."""
    return run_ingestion_cycle(hours=24)["rules"]
