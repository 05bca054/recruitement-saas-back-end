"""Question-related schemas for API requests/responses."""
from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.question import Question, QuestionOption, InterviewAgent, FollowUpQuestion


class AddQuestionRequest(BaseModel):
    """Request to add a question to a pipeline stage."""
    text: str = Field(..., description="Question text")
    type: str = Field(..., description="Question type: multiple_choice, rating, yes_no, text")
    max_score: int = Field(10, description="Maximum points")
    weight: float = Field(1.0, description="Weight multiplier")
    required: bool = Field(True, description="Is required")
    options: List[QuestionOption] = Field(default_factory=list)
    follow_up: Optional[FollowUpQuestion] = Field(None, description="Conditional follow-up question")
    scoring_rubric: str = Field("", description="LLM scoring instructions")
    order: int = Field(0, description="Display order")


class UpdateQuestionRequest(BaseModel):
    """Request to update a question."""
    text: Optional[str] = None
    type: Optional[str] = None
    max_score: Optional[int] = None
    weight: Optional[float] = None
    required: Optional[bool] = None
    options: Optional[List[QuestionOption]] = None
    follow_up: Optional[FollowUpQuestion] = None
    scoring_rubric: Optional[str] = None
    order: Optional[int] = None


class QuestionResponse(BaseModel):
    """Response with question details."""
    question_id: str
    text: str
    type: str
    max_score: int
    weight: float
    required: bool
    options: List[QuestionOption]
    follow_up: Optional[FollowUpQuestion]
    scoring_rubric: str
    order: int


class ConfigureInterviewAgentRequest(BaseModel):
    """Request to configure AI interview agent."""
    enabled: bool
    agent_name: str = "Laura"
    agent_prompt: str
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    temperature: float = 0.7
    language: str = "es"
    api_key: Optional[str] = None


class InterviewAgentResponse(BaseModel):
    """Response with interview agent configuration."""
    enabled: bool
    agent_name: str
    agent_prompt: str
    llm_provider: str
    llm_model: str
    temperature: float
    language: str
