"""Candidate schemas."""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class CreateCandidateRequest(BaseModel):
    """Request to create a candidate."""
    pipeline_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    resume_url: Optional[str] = None


class CandidateResponse(BaseModel):
    """Response schema for candidate."""
    id: str
    organization_id: str
    pipeline_id: str
    current_stage_id: Optional[str]
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    resume_url: Optional[str]
    status: str
    overall_score: float
    airtable_record_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class UpdateCandidateRequest(BaseModel):
    """Request to update a candidate."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    current_stage_id: Optional[str] = None
    status: Optional[str] = None
    overall_score: Optional[float] = None
