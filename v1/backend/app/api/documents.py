"""Documents API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid
from datetime import datetime
from pathlib import Path
import re
import logging

from app.db.database import get_db
from app.db.models import Document, Event, Case
from app.api.schemas import (
    DocumentResponse,
    DocumentUploadResponse,
    DocumentAnalysisResponse,
    AnalyzeDocumentRequest,
    BulkAnalyzeRequest,
    AnalysisCostEstimate
)
from app.services.s3_service import get_s3_service, S3Service

logger = logging.getLogger(__name__)

router = APIRouter()

# File validation constants
ALLOWED_EXTENSIONS = {
    'pdf': 'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'doc': 'application/msword',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'txt': 'text/plain',
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    # Remove special characters except dots, underscores, hyphens
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    return filename


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """
    Validate uploaded file

    Returns:
        (is_valid, error_message)
    """
    # Check filename
    if not file.filename:
        return False, "No filename provided"

    # Check extension
    extension = file.filename.rsplit('.', 1)[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return False, f"File type '.{extension}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS.keys())}"

    # Check content type (if provided)
    if file.content_type and file.content_type not in ALLOWED_EXTENSIONS.values():
        return False, f"Content type '{file.content_type}' not allowed"

    return True, ""


def generate_s3_key(case_id: UUID, filename: str) -> str:
    """
    Generate unique S3 key for document

    Format: cases/{case_id}/documents/{uuid}_{filename}
    """
    unique_id = uuid.uuid4()
    sanitized_name = sanitize_filename(filename)
    return f"cases/{case_id}/documents/{unique_id}_{sanitized_name}"


@router.post("/", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    case_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    s3_service: S3Service = Depends(get_s3_service)
):
    """Upload a document to a case"""

    # Verify case exists
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found"
        )

    # Validate file
    is_valid, error_msg = validate_file(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({file_size} bytes) exceeds maximum ({MAX_FILE_SIZE} bytes)"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )

    # Generate S3 key
    s3_key = generate_s3_key(case_id, file.filename)

    # Get content type
    extension = file.filename.rsplit('.', 1)[-1].lower()
    content_type = ALLOWED_EXTENSIONS.get(extension, 'application/octet-stream')

    # Upload to S3
    upload_success = s3_service.upload_file(
        file_obj=file.file,
        s3_key=s3_key,
        content_type=content_type,
        metadata={
            'case_id': str(case_id),
            'original_filename': file.filename,
            'uploaded_at': datetime.utcnow().isoformat()
        }
    )

    if not upload_success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage"
        )

    # Create document record (read model)
    document = Document(
        case_id=case_id,
        filename=sanitize_filename(file.filename),
        original_filename=file.filename,
        file_type=content_type,
        file_size=file_size,
        s3_key=s3_key,
        s3_bucket=s3_service.bucket_name,
        status="uploaded",
        document_metadata={}
    )
    db.add(document)
    db.flush()  # CRITICAL: Generate document_id before creating event

    # Create event (event store)
    event = Event(
        aggregate_type="document",
        aggregate_id=document.document_id,
        event_type="DocumentUploaded",
        event_data={
            "case_id": str(case_id),
            "filename": document.filename,
            "original_filename": document.original_filename,
            "file_type": content_type,
            "file_size": file_size,
            "s3_key": s3_key,
        },
        event_metadata={"source": "api", "case_id": str(case_id)}
    )
    db.add(event)

    db.commit()
    db.refresh(document)

    return DocumentUploadResponse(
        document=document,
        message="Document uploaded successfully"
    )


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    case_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all documents for a case"""

    # Verify case exists
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found"
        )

    documents = (
        db.query(Document)
        .filter(Document.case_id == case_id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    case_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific document"""

    document = (
        db.query(Document)
        .filter(Document.document_id == document_id, Document.case_id == case_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found in case {case_id}"
        )

    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    case_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
    s3_service: S3Service = Depends(get_s3_service)
):
    """Delete a document"""

    document = (
        db.query(Document)
        .filter(Document.document_id == document_id, Document.case_id == case_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found in case {case_id}"
        )

    # Delete from S3
    s3_delete_success = s3_service.delete_file(document.s3_key)
    if not s3_delete_success:
        # Log error but continue with database deletion
        # The file might already be deleted or S3 might be temporarily unavailable
        pass

    # Create event before deleting
    event = Event(
        aggregate_type="document",
        aggregate_id=document_id,
        event_type="DocumentDeleted",
        event_data={
            "case_id": str(case_id),
            "filename": document.filename,
            "s3_key": document.s3_key
        },
        event_metadata={"source": "api", "case_id": str(case_id)}
    )
    db.add(event)

    # Delete from database
    db.delete(document)
    db.commit()

    return None


# ============================================================================
# AI Analysis Endpoints
# ============================================================================

async def process_document_background(
    document_id: UUID,
    case_id: UUID,
    db_session: Session
):
    """
    Background task for document AI processing

    Steps:
    1. Download document from S3
    2. Extract text
    3. Quality check
    4. AI analysis (Claude + GPT-4)
    5. Store results in document_metadata
    6. Emit events at each stage
    """
    from app.services import get_s3_service, get_text_extraction_service, get_ai_service
    from app.domain.events import (
        DocumentTextExtractedEvent,
        DocumentAnalyzedEvent,
        DocumentAnalysisFailedEvent
    )
    import tempfile
    import os

    s3_service = get_s3_service()
    text_service = get_text_extraction_service()
    ai_service = get_ai_service()

    tmp_path = None

    try:
        # Get document
        document = db_session.query(Document).filter(
            Document.document_id == document_id
        ).first()

        if not document:
            logger.error(f"Document {document_id} not found")
            return

        # 1. Download from S3 to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(document.filename).suffix) as tmp:
            tmp_path = tmp.name

        download_success = s3_service.download_file(document.s3_key, tmp_path)
        if not download_success:
            raise Exception("Failed to download file from S3")

        # 2. Extract text
        extraction_result = text_service.extract_text(tmp_path, document.file_type)

        # Create extraction event
        event = Event(
            aggregate_type="document",
            aggregate_id=document_id,
            event_type="DocumentTextExtracted",
            event_data={
                "case_id": str(case_id),
                "text_length": extraction_result["text_length"],
                "quality_score": extraction_result["quality_score"],
                "extraction_method": extraction_result["method"]
            },
            event_metadata={"source": "ai_processing"}
        )
        db_session.add(event)
        db_session.commit()

        # 3. Quality check
        if extraction_result["quality_score"] < 0.5:
            document.status = "poor_quality"
            document.document_metadata = {
                "extraction": extraction_result,
                "processing": {
                    "started_at": datetime.utcnow().isoformat(),
                    "completed_at": datetime.utcnow().isoformat(),
                    "error": "Text quality too low for analysis"
                }
            }

            # Create failure event
            event = Event(
                aggregate_type="document",
                aggregate_id=document_id,
                event_type="DocumentAnalysisFailed",
                event_data={
                    "case_id": str(case_id),
                    "error_type": "quality_too_low",
                    "error_message": f"Quality score {extraction_result['quality_score']} below threshold"
                },
                event_metadata={"source": "ai_processing"}
            )
            db_session.add(event)
            db_session.commit()
            return

        # 4. AI Analysis
        started_at = datetime.utcnow()
        analysis_result = await ai_service.process_document(
            extraction_result["text"],
            document.file_type
        )
        completed_at = datetime.utcnow()

        # 5. Store results
        document.document_metadata = {
            "extraction": {
                "text": extraction_result["text"][:10000],  # Store first 10k chars
                "text_length": extraction_result["text_length"],
                "quality_score": extraction_result["quality_score"],
                "extracted_at": extraction_result["extracted_at"],
                "extraction_method": extraction_result["method"],
                "metadata": extraction_result.get("metadata", {})
            },
            "analysis": analysis_result["analysis"],
            "entities": analysis_result["entities"],
            "processing": {
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_ms": int((completed_at - started_at).total_seconds() * 1000),
                "total_cost_usd": analysis_result["total_cost"]
            }
        }
        document.status = "analysis_complete"

        # 6. Emit success event
        event = Event(
            aggregate_type="document",
            aggregate_id=document_id,
            event_type="DocumentAnalyzed",
            event_data={
                "case_id": str(case_id),
                "classification": analysis_result["analysis"]["classification"],
                "confidence": analysis_result["analysis"]["confidence"],
                "total_cost_usd": analysis_result["total_cost"]
            },
            event_metadata={
                "source": "ai_processing",
                "models": analysis_result["model_versions"]
            }
        )
        db_session.add(event)
        db_session.commit()

        logger.info(f"Document {document_id} analysis complete: {analysis_result['analysis']['classification']}")

    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {str(e)}")

        # Update document status
        try:
            document = db_session.query(Document).filter(
                Document.document_id == document_id
            ).first()

            if document:
                document.status = "extraction_failed"
                if not document.document_metadata:
                    document.document_metadata = {}

                document.document_metadata["processing"] = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "failed_at": datetime.utcnow().isoformat()
                }

                # Create failure event
                event = Event(
                    aggregate_type="document",
                    aggregate_id=document_id,
                    event_type="DocumentAnalysisFailed",
                    event_data={
                        "case_id": str(case_id),
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    event_metadata={"source": "ai_processing"}
                )
                db_session.add(event)
                db_session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update error status: {str(db_error)}")

    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to delete temp file {tmp_path}: {str(cleanup_error)}")


@router.post("/{document_id}/analyze", response_model=DocumentAnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_document(
    case_id: UUID,
    document_id: UUID,
    request: AnalyzeDocumentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger AI analysis of a single document

    Returns 202 Accepted immediately and processes in background.
    Use GET /{document_id}/analysis to poll for results.
    """
    from app.domain.events import DocumentAnalysisStartedEvent

    # Verify case exists
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found"
        )

    # Get document
    document = db.query(Document).filter(
        Document.document_id == document_id,
        Document.case_id == case_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found in case {case_id}"
        )

    # Check if already processed
    if document.document_metadata and document.document_metadata.get("analysis") and not request.force_reanalyze:
        return DocumentAnalysisResponse(
            document_id=document_id,
            status=document.status,
            extraction=document.document_metadata.get("extraction"),
            analysis=document.document_metadata.get("analysis"),
            entities=document.document_metadata.get("entities"),
            processing=document.document_metadata.get("processing")
        )

    # Update status to processing
    document.status = "processing"

    # Create start event
    event = Event(
        aggregate_type="document",
        aggregate_id=document_id,
        event_type="DocumentAnalysisStarted",
        event_data={
            "case_id": str(case_id),
            "triggered_by": "user"
        },
        event_metadata={"source": "api"}
    )
    db.add(event)
    db.commit()

    # Schedule background processing
    background_tasks.add_task(process_document_background, document_id, case_id, db)

    return DocumentAnalysisResponse(
        document_id=document_id,
        status="processing",
        extraction=None,
        analysis=None,
        entities=None,
        processing={"started_at": datetime.utcnow().isoformat()}
    )


@router.get("/{document_id}/analysis", response_model=DocumentAnalysisResponse)
async def get_analysis(
    case_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get current analysis status and results

    Use this endpoint to poll for completion after triggering analysis.
    """
    document = db.query(Document).filter(
        Document.document_id == document_id,
        Document.case_id == case_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found in case {case_id}"
        )

    return DocumentAnalysisResponse(
        document_id=document_id,
        status=document.status,
        extraction=document.document_metadata.get("extraction") if document.document_metadata else None,
        analysis=document.document_metadata.get("analysis") if document.document_metadata else None,
        entities=document.document_metadata.get("entities") if document.document_metadata else None,
        processing=document.document_metadata.get("processing") if document.document_metadata else None
    )


@router.post("/analyze-bulk", status_code=status.HTTP_202_ACCEPTED)
async def analyze_bulk(
    case_id: UUID,
    request: BulkAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Analyze multiple documents in sequence

    Processes documents one by one to manage rate limits.
    Returns immediately with count of queued documents.
    """
    # Verify case exists
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found"
        )

    # Get all requested documents
    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.document_id.in_(request.document_ids)
    ).all()

    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found with provided IDs"
        )

    # Filter documents that need analysis
    docs_to_analyze = []
    already_analyzed = 0

    for doc in documents:
        if request.force_reanalyze or not (doc.document_metadata and doc.document_metadata.get("analysis")):
            docs_to_analyze.append(doc)
        else:
            already_analyzed += 1

    # Queue each document for processing
    for doc in docs_to_analyze:
        doc.status = "processing"

        event = Event(
            aggregate_type="document",
            aggregate_id=doc.document_id,
            event_type="DocumentAnalysisStarted",
            event_data={
                "case_id": str(case_id),
                "triggered_by": "bulk"
            },
            event_metadata={"source": "api"}
        )
        db.add(event)

        # Add to background tasks
        background_tasks.add_task(process_document_background, doc.document_id, case_id, db)

    db.commit()

    return {
        "total": len(request.document_ids),
        "queued": len(docs_to_analyze),
        "already_analyzed": already_analyzed,
        "message": f"Queued {len(docs_to_analyze)} documents for analysis"
    }


@router.post("/estimate-cost", response_model=AnalysisCostEstimate)
async def estimate_cost(
    case_id: UUID,
    request: BulkAnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    Estimate cost before processing documents

    Calculates based on document file sizes and current daily budget.
    """
    from app.services import get_ai_service

    ai_service = get_ai_service()

    # Verify case exists
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found"
        )

    # Get documents
    documents = db.query(Document).filter(
        Document.case_id == case_id,
        Document.document_id.in_(request.document_ids)
    ).all()

    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found with provided IDs"
        )

    # Estimate cost for each document
    total_cost = 0.0
    for doc in documents:
        # Skip already analyzed unless force reanalyze
        if not request.force_reanalyze and doc.document_metadata and doc.document_metadata.get("analysis"):
            continue

        # Rough estimate: PDF/DOCX ~500 chars per page, ~10 pages avg
        # Images ~2000 chars per page
        if 'pdf' in doc.file_type.lower() or 'word' in doc.file_type.lower():
            estimated_text_length = min(doc.file_size // 100, 50000)  # Conservative estimate
        else:
            estimated_text_length = min(doc.file_size // 50, 20000)

        cost = ai_service.estimate_cost(estimated_text_length)
        total_cost += cost

    # Check budget
    within_budget, remaining = ai_service.check_daily_budget()

    # Estimate time (rough: 30 seconds per document)
    estimated_time = len(documents) * 30

    return AnalysisCostEstimate(
        total_documents=len(documents),
        estimated_cost_usd=round(total_cost, 3),
        estimated_time_seconds=estimated_time,
        within_budget=total_cost <= remaining,
        remaining_budget_usd=remaining
    )
