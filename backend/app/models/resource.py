from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base import Base


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    cloud_provider = Column(String(20), nullable=False)  # aws | gcp
    resource_id = Column(String(255), nullable=False, unique=True, index=True)
    resource_type = Column(String(100), nullable=False)  # ec2 | ebs | gke_node etc
    region = Column(String(100), nullable=True)
    account_id = Column(String(100), nullable=True)
    tags = Column(String, nullable=True)  # JSON string for now
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)