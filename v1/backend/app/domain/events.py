from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional, Any


@dataclass
class BaseEvent:
    """Base class for all domain events"""
    aggregate_id: UUID
    event_type: str
    event_data: dict
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None


@dataclass
class CaseCreatedEvent(BaseEvent):
    """Event emitted when a case is created"""
    def __init__(self, case_id: UUID, title: str, case_number: str, metadata: Optional[dict] = None):
        super().__init__(
            aggregate_id=case_id,
            event_type="CaseCreated",
            event_data={
                "title": title,
                "case_number": case_number,
                "metadata": metadata or {}
            }
        )


@dataclass
class CaseUpdatedEvent(BaseEvent):
    """Event emitted when a case is updated"""
    pass


@dataclass
class CaseDeletedEvent(BaseEvent):
    """Event emitted when a case is deleted"""
    pass


@dataclass
class DocumentUploadedEvent(BaseEvent):
    """Event emitted when a document is uploaded"""
    def __init__(self, document_id: UUID, case_id: UUID, filename: str,
                 file_type: str, file_size: int, s3_key: str, metadata: Optional[dict] = None):
        super().__init__(
            aggregate_id=document_id,
            event_type="DocumentUploaded",
            event_data={
                "case_id": str(case_id),
                "filename": filename,
                "file_type": file_type,
                "file_size": file_size,
                "s3_key": s3_key,
                "metadata": metadata or {}
            }
        )


@dataclass
class DocumentDeletedEvent(BaseEvent):
    """Event emitted when a document is deleted"""
    def __init__(self, document_id: UUID, case_id: UUID, s3_key: str):
        super().__init__(
            aggregate_id=document_id,
            event_type="DocumentDeleted",
            event_data={
                "case_id": str(case_id),
                "s3_key": s3_key
            }
        )


@dataclass
class DocumentAnalysisStartedEvent(BaseEvent):
    """Event emitted when document AI analysis begins"""
    def __init__(self, document_id: UUID, case_id: UUID, triggered_by: str):
        super().__init__(
            aggregate_id=document_id,
            event_type="DocumentAnalysisStarted",
            event_data={
                "case_id": str(case_id),
                "triggered_by": triggered_by  # "user" or "bulk"
            }
        )


@dataclass
class DocumentTextExtractedEvent(BaseEvent):
    """Event emitted after text extraction completes"""
    def __init__(self, document_id: UUID, case_id: UUID,
                 text_length: int, quality_score: float, method: str):
        super().__init__(
            aggregate_id=document_id,
            event_type="DocumentTextExtracted",
            event_data={
                "case_id": str(case_id),
                "text_length": text_length,
                "quality_score": quality_score,
                "extraction_method": method
            }
        )


@dataclass
class DocumentAnalyzedEvent(BaseEvent):
    """Event emitted after successful AI analysis"""
    def __init__(self, document_id: UUID, case_id: UUID,
                 classification: str, confidence: float,
                 total_cost: float, model_versions: dict):
        super().__init__(
            aggregate_id=document_id,
            event_type="DocumentAnalyzed",
            event_data={
                "case_id": str(case_id),
                "classification": classification,
                "confidence": confidence,
                "total_cost_usd": total_cost
            },
            metadata={
                "source": "ai_service",
                "models": model_versions,
                "cost_breakdown": {
                    "claude": model_versions.get("claude_cost", 0),
                    "gpt4": model_versions.get("gpt4_cost", 0)
                }
            }
        )


@dataclass
class DocumentAnalysisFailedEvent(BaseEvent):
    """Event emitted when AI analysis fails"""
    def __init__(self, document_id: UUID, case_id: UUID,
                 error_type: str, error_message: str):
        super().__init__(
            aggregate_id=document_id,
            event_type="DocumentAnalysisFailed",
            event_data={
                "case_id": str(case_id),
                "error_type": error_type,  # "extraction_failed", "api_error", "quality_too_low"
                "error_message": error_message
            }
        )
