from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime

class StartInterviewRequest(BaseModel):
    candidate_id: str
    platform: Literal["telegram", "web_simulator"] = "web_simulator"
    chat_id: Optional[str] = None

class ChatRequest(BaseModel):
    session_id: str
    message: str

class InterviewSessionResponse(BaseModel):
    session_id: str
    candidate_id: str
    status: str
    messages: List[Dict]
    scores: Optional[List[Dict]] = None
    total_score: Optional[float] = None  # Float because it might be avg or customized
    created_at: datetime

class ChatResponse(BaseModel):
    response: str
    session_id: str
    status: str
