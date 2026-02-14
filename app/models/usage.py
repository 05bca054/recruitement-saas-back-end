from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TokenUsageLog(BaseModel):
    organization_id: str
    candidate_id: str
    interaction_type: str  # 'chat', 'scoring', 'greeting'
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
