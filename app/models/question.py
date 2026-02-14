"""Question models for pipeline questionnaires."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class QuestionOption(BaseModel):
    """Option for multiple choice questions."""
    option_id: str = Field(..., description="Unique identifier for this option")
    text: str = Field(..., description="Option text")
    score: int = Field(0, description="Points awarded for selecting this option")


class FollowUpQuestion(BaseModel):
    """Conditional follow-up question."""
    text: str = Field(..., description="The follow-up question text")
    condition: str = Field(..., description="Trigger condition (e.g., 'yes', 'no', or option_id)")
    scoring_rubric: str = Field("", description="Instructions for LLM scoring follow-up")
    max_score: int = Field(5, description="Maximum points for follow-up")


class Question(BaseModel):
    """Question in a pipeline stage."""
    question_id: str = Field(..., description="Unique identifier")
    text: str = Field(..., description="Question text")
    type: str = Field(..., description="Question type: multiple_choice, rating, yes_no, text, conversational")
    max_score: int = Field(10, description="Maximum points for this question")
    weight: float = Field(1.0, description="Weight/importance multiplier")
    required: bool = Field(True, description="Whether this question is required")
    options: List[QuestionOption] = Field(default_factory=list, description="Options for multiple choice")
    follow_up: Optional[FollowUpQuestion] = Field(None, description="Conditional follow-up question")
    scoring_rubric: str = Field("", description="Instructions for LLM scoring")
    order: int = Field(0, description="Display order")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question_id": "q1",
                "text": "¿Has trabajado antes como despachador de gasolina?",
                "type": "yes_no",
                "max_score": 20,
                "weight": 2.0,
                "required": True,
                "options": [
                    {"option_id": "yes", "text": "Sí", "score": 20},
                    {"option_id": "no", "text": "No", "score": 0}
                ],
                "scoring_rubric": "Award full points if candidate has relevant experience",
                "order": 1
            }
        }


class InterviewAgent(BaseModel):
    """AI agent configuration for conducting interviews."""
    enabled: bool = Field(False, description="Whether AI interviewer is enabled")
    agent_name: str = Field("Laura", description="Agent's name/personality")
    agent_prompt: str = Field("", description="System prompt defining behavior")
    llm_provider: str = Field("openai", description="LLM provider: openai, anthropic, gemini")
    llm_model: str = Field("gpt-4", description="Model to use")
    temperature: float = Field(0.7, description="Temperature for responses")
    language: str = Field("es", description="Interview language")
    api_key: Optional[str] = Field(None, description="API key for LLM provider")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "agent_name": "Laura",
                "agent_prompt": "You are Laura, a friendly HR agent...",
                "llm_provider": "openai",
                "llm_model": "gpt-4",
                "temperature": 0.7,
                "language": "es"
            }
        }
