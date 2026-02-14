"""Interview session models."""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Literal
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId

class InterviewSession(BaseModel):
    """Tracks an active interview conversation."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    candidate_id: PyObjectId = Field(..., description="The candidate being interviewed")
    pipeline_id: PyObjectId = Field(..., description="The context pipeline")
    
    # Platform context
    platform: Literal["telegram", "web_simulator"] = "web_simulator"
    telegram_chat_id: Optional[str] = None
    
    # Conversation handling
    messages: List[Dict] = Field(default_factory=list, description="OpenAI message history")
    status: Literal["active", "completed"] = "active"
    
    # Metadata for process tracking
    current_question_index: int = 0
    metadata: Dict = Field(default_factory=dict)
    
    # Scoring results
    scores: List[Dict] = Field(default_factory=list, description="List of component scores")
    total_score: int = Field(0, description="Total score calculated from answers")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
