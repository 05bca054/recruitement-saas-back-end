"""Candidate database models."""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId


class CandidateModel(BaseModel):
    """Candidate model."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organization_id: PyObjectId
    pipeline_id: PyObjectId
    current_stage_id: Optional[str] = None
    
    # Personal info
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    
    # Status and scoring
    status: str = "active"           # "active", "rejected", "hired"
    overall_score: float = 0.0
    
    # Airtable sync
    airtable_record_id: Optional[str] = None
    
    # AI Usage Stats
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_ai_cost: float = 0.0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
