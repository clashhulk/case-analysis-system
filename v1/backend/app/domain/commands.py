from dataclasses import dataclass
from uuid import UUID
from typing import Optional


@dataclass
class CreateCaseCommand:
    """Command to create a new case"""
    title: str
    case_number: str
    metadata: Optional[dict] = None


@dataclass
class UpdateCaseCommand:
    """Command to update an existing case"""
    case_id: UUID
    title: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class DeleteCaseCommand:
    """Command to delete a case"""
    case_id: UUID
