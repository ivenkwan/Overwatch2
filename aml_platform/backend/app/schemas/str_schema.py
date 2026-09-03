# aml_platform/backend/app/schemas/str_schema.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class STRBase(BaseModel):
    case_id: Optional[UUID] = None
    triggering_factors: Optional[str] = None
    subject_background: Optional[str] = None
    digital_footprints: Optional[str] = None
    transaction_summary: Optional[str] = None

class STRCreate(STRBase):
    pass

class STRUpdate(STRBase):
    pass

class STRResponse(BaseModel):
    str_id: UUID
    tenant_id: UUID
    case_id: Optional[UUID] = None
    status: str
    triggering_factors: Optional[str] = None
    subject_background: Optional[str] = None
    digital_footprints: Optional[str] = None
    transaction_summary: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    submitted_by: Optional[UUID] = None
    submitted_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2
        orm_mode = True         # Pydantic v1
