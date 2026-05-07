from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_name = Column(String(100), nullable=False)  # e.g. idle_vm
    severity = Column(String(20), nullable=False)    # low | medium | high
    estimated_monthly_savings = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.0)
    action = Column(String(120), nullable=False)     # e.g. downsize_instance
    status = Column(String(30), nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    resource = relationship("Resource", back_populates="recommendations")
    audit_logs = relationship("AuditLog", back_populates="recommendation", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="recommendation", cascade="all, delete-orphan")