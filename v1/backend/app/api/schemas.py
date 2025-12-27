from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class CaseCreate(BaseModel):
    """Schema for creating a new case"""
    title: str = Field(..., min_length=1, max_length=500, description="Case title")
    case_number: str = Field(..., min_length=1, max_length=100, description="Unique case number")
    metadata: Optional[dict] = Field(default=None, description="Additional case metadata")


class CaseUpdate(BaseModel):
    """Schema for updating a case"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[str] = Field(None, pattern="^(draft|active|archived)$")
    metadata: Optional[dict] = None


class CaseResponse(BaseModel):
    """Schema for case response"""
    case_id: UUID
    title: str
    case_number: str
    status: str
    case_metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Schema for document response"""
    document_id: UUID
    case_id: UUID
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    s3_key: str
    s3_bucket: str
    status: str
    document_metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response"""
    document: DocumentResponse
    message: str = "Document uploaded successfully"
