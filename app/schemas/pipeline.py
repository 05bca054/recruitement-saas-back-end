"""Pipeline schemas."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class StageRequest(BaseModel):
    """Request schema for pipeline stage."""
    stage_id: str
    name: str
    order: int
    type: str = "manual"
    config: dict = {
        "auto_advance": False,
        "required_score": 0,
        "telegram_interview": False
    }


class CreatePipelineRequest(BaseModel):
    """Request to create a pipeline."""
    name: str
    description: Optional[str] = None
    stages: List[StageRequest]


class PipelineResponse(BaseModel):
    """Response schema for pipeline."""
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    status: str
    stages: List[dict]
    airtable_table_id: Optional[str]
    airtable_table_name: Optional[str]
    airtable_synced: bool
    created_at: datetime
    updated_at: datetime
    created_by: str


class UpdatePipelineRequest(BaseModel):
    """Request to update a pipeline."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    stages: Optional[List[StageRequest]] = None
