from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.database import get_db
from app.db.models import Case, Event
from app.api.schemas import CaseCreate, CaseUpdate, CaseResponse
from app.domain.commands import CreateCaseCommand
from app.domain.events import CaseCreatedEvent

router = APIRouter()


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(case_data: CaseCreate, db: Session = Depends(get_db)):
    """Create a new case"""

    # Check if case number already exists
    existing = db.query(Case).filter(Case.case_number == case_data.case_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Case number '{case_data.case_number}' already exists"
        )

    # Create case (read model)
    new_case = Case(
        title=case_data.title,
        case_number=case_data.case_number,
        status="draft",
        case_metadata=case_data.metadata or {}
    )
    db.add(new_case)
    db.flush()  # Flush to generate case_id from database

    # Create event (event store)
    event = Event(
        aggregate_type="case",
        aggregate_id=new_case.case_id,
        event_type="CaseCreated",
        event_data={
            "title": case_data.title,
            "case_number": case_data.case_number,
            "metadata": case_data.metadata or {}
        },
        event_metadata={"source": "api"}
    )
    db.add(event)

    db.commit()
    db.refresh(new_case)

    return new_case


@router.get("/", response_model=List[CaseResponse])
async def list_cases(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all cases"""
    cases = db.query(Case).order_by(Case.created_at.desc()).offset(skip).limit(limit).all()
    return cases


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: UUID, db: Session = Depends(get_db)):
    """Get a specific case by ID"""
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found"
        )
    return case


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: UUID,
    case_update: CaseUpdate,
    db: Session = Depends(get_db)
):
    """Update a case"""
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found"
        )

    # Update fields
    update_data = case_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    # Create event
    event = Event(
        aggregate_type="case",
        aggregate_id=case_id,
        event_type="CaseUpdated",
        event_data=update_data,
        event_metadata={"source": "api"}
    )
    db.add(event)

    db.commit()
    db.refresh(case)

    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: UUID, db: Session = Depends(get_db)):
    """Delete a case"""
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found"
        )

    # Create event before deleting
    event = Event(
        aggregate_type="case",
        aggregate_id=case_id,
        event_type="CaseDeleted",
        event_data={"case_number": case.case_number},
        event_metadata={"source": "api"}
    )
    db.add(event)

    db.delete(case)
    db.commit()

    return None
