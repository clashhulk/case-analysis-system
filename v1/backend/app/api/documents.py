"""Documents API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid
from datetime import datetime
import re

from app.db.database import get_db
from app.db.models import Document, Event, Case
from app.api.schemas import DocumentResponse, DocumentUploadResponse
from app.services.s3_service import get_s3_service, S3Service

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
