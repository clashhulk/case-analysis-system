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
    """Schema for document response

    Status values:
    - uploaded: Successfully uploaded and stored (default)
    - pending: Upload in progress
    - failed: Upload failed
    - processing: Being analyzed by AI (Phase 3)
    - extracted: Text extraction complete (Phase 3)
    - analysis_complete: Full AI analysis done (Phase 3)
    - extraction_failed: AI processing failed (Phase 3)
    - poor_quality: Low quality scan/image
    - pending_review: Needs manual review
    - approved: Reviewed and approved
    - rejected: Rejected/invalid
    """
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


class DocumentAnalysisResponse(BaseModel):
    """Schema for document analysis results"""
    document_id: UUID
    status: str  # "processing", "analysis_complete", "extraction_failed", "poor_quality"
    extraction: Optional[dict] = Field(
        None,
        description="Text extraction results with text, quality_score, method, etc."
    )
    analysis: Optional[dict] = Field(
        None,
        description="Claude analysis results with summary, classification, key_points"
    )
    entities: Optional[dict] = Field(
        None,
        description="GPT-4 entity extraction with people, dates, locations, case_numbers"
    )
    processing: Optional[dict] = Field(
        None,
        description="Processing metadata with timestamps and costs"
    )

    class Config:
        from_attributes = True


class AnalyzeDocumentRequest(BaseModel):
    """Schema for triggering document analysis"""
    force_reanalyze: bool = Field(
        default=False,
        description="Re-analyze even if already processed"
    )


class BulkAnalyzeRequest(BaseModel):
    """Schema for bulk document analysis"""
    document_ids: list[UUID] = Field(
        ...,
        description="List of document IDs to analyze"
    )
    force_reanalyze: bool = Field(
        default=False,
        description="Re-analyze documents even if already processed"
    )


class AnalysisCostEstimate(BaseModel):
    """Schema for cost estimation before processing"""
    total_documents: int = Field(..., description="Number of documents to process")
    estimated_cost_usd: float = Field(..., description="Estimated total cost in USD")
    estimated_time_seconds: int = Field(..., description="Estimated processing time")
    within_budget: bool = Field(..., description="Whether operation is within daily budget")
    remaining_budget_usd: float = Field(..., description="Remaining daily budget in USD")
