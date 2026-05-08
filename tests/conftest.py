from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.simulation_run import SimulationRun
from app.models.usage_metric import UsageMetric


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_data(db_session):
    resource = Resource(
        cloud_provider="aws",
        resource_id="ecs:default:svc-a",
        resource_type="ecs_service",
        region="eu-central-1",
        account_id="123",
        tags='{"env":"test"}',
    )
    db_session.add(resource)
    db_session.commit()
    db_session.refresh(resource)

    recommendation = Recommendation(
        resource_id=resource.id,
        rule_name="ecs_underutilized_service",
        severity="medium",
        estimated_monthly_savings=42.5,
        confidence_score=0.9,
        action="reduce_task_size_or_scale_schedule",
        status="open",
    )
    db_session.add(recommendation)
    db_session.commit()
    db_session.refresh(recommendation)

    now = datetime.now(timezone.utc)
    metrics = [
        UsageMetric(
            resource_id=resource.id,
            cpu_utilization=8.0,
            memory_utilization=24.0,
            network_in_mb=1.0,
            network_out_mb=1.0,
            recorded_at=now - timedelta(hours=i),
        )
        for i in range(12)
    ]
    db_session.add_all(metrics)
    db_session.commit()

    return {"resource": resource, "recommendation": recommendation}
