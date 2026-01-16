"""AI Cost Tracking model for monitoring AI service usage and costs"""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSON
from sqlalchemy.orm import relationship

from app.domain.models.base import Base


class AICostTracking(Base):
    """Model for tracking AI service costs and usage"""

    __tablename__ = "ai_cost_tracking"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(PGUUID(as_uuid=True), ForeignKey("documents.document_id", ondelete="SET NULL"), nullable=True)
    case_id = Column(PGUUID(as_uuid=True), ForeignKey("cases.case_id", ondelete="SET NULL"), nullable=True)

    # Service information
    service_type = Column(String, nullable=False)  # 'text_analysis', 'entity_extraction', 'vision_ai'
    model_name = Column(String, nullable=False)  # 'claude-3-5-haiku-20241022', 'gpt-4-turbo-preview', etc.

    # Usage metrics
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(10, 6), nullable=False)
    duration_ms = Column(Integer, nullable=True)

    # Status
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)

    # Additional metadata (can store per-service specific data)
    metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="ai_cost_records")
    case = relationship("Case", back_populates="ai_cost_records")

    def __repr__(self):
        return f"<AICostTracking(id={self.id}, service={self.service_type}, model={self.model_name}, cost=${self.cost_usd})>"
