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
