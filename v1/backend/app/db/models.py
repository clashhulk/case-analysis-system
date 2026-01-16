from sqlalchemy import Column, String, DateTime, BigInteger, Text, Integer, ForeignKey, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.db.database import Base


class Event(Base):
    """Event store - immutable log of all system events"""
    __tablename__ = "events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_type = Column(String(50), nullable=False, index=True)  # 'case', 'document', etc.
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)  # 'CaseCreated', 'DocumentUploaded', etc.
    event_data = Column(JSONB, nullable=False)  # Event payload
    event_metadata = Column(JSONB)  # user_id, timestamp, ai_model_version, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    sequence_number = Column(BigInteger, primary_key=True, autoincrement=True)


class Case(Base):
    """Cases - read model"""
    __tablename__ = "cases"

    case_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    case_number = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(50), default="draft")  # draft, active, archived
    case_metadata = Column(JSONB)  # Additional flexible data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Document(Base):
    """Documents - read model"""
    __tablename__ = "documents"

    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    s3_key = Column(String(1000), nullable=False, unique=True)
    s3_bucket = Column(String(255), nullable=False)
    status = Column(String(50), default="uploaded")  # uploaded, processing, failed
    document_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AICostTracking(Base):
    """AI Cost Tracking - tracks all AI service usage and costs"""
    __tablename__ = "ai_cost_tracking"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id", ondelete="SET NULL"), nullable=True, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id", ondelete="SET NULL"), nullable=True, index=True)
    service_type = Column(String(50), nullable=False, index=True)  # 'text_analysis', 'entity_extraction', 'vision_ai'
    model_name = Column(String(100), nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(10, 6), nullable=False)
    duration_ms = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
