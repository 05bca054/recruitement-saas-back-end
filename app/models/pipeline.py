"""Pipeline database models."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId
from app.models.question import Question, InterviewAgent


class PipelineStage(BaseModel):
    """Pipeline stage configuration."""
    stage_id: str                    # UUID for stage
    name: str                        # "Application Review", "Phone Screen"
    order: int                       # Sequential order (1, 2, 3...)
    type: str = "manual"             # "manual", "automated_interview"
    questions: List[Question] = []   # Questions for this stage
    min_passing_score: int = 0       # Minimum score to pass this stage
    use_ai_interview: bool = False   # Enable conversational AI interview
    config: dict = {
        "auto_advance": False,
        "required_score": 0,
        "telegram_interview": False
    }


class RecruitmentPipelineModel(BaseModel):
    """Recruitment pipeline model."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organization_id: PyObjectId
    name: str                        # "Software Engineer Hiring"
    description: Optional[str] = None
    status: str = "active"           # "active", "draft", "archived"
    stages: List[PipelineStage] = []
    
    # Scoring configuration
    overall_min_score: int = 70      # Overall minimum score for hire decision
    auto_calculate_scores: bool = True
    
    # AI Interview Agent
    interview_agent: Optional[InterviewAgent] = None
    
    # Airtable sync configuration
    airtable_table_id: Optional[str] = None    # Airtable table ID
    airtable_table_name: Optional[str] = None  # Table name in Airtable
    airtable_synced: bool = False
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: PyObjectId
