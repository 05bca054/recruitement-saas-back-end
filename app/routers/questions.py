"""Question management router."""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
import uuid

from app.database import get_db
from app.schemas.question import (
    AddQuestionRequest,
    UpdateQuestionRequest,
    QuestionResponse,
    ConfigureInterviewAgentRequest,
    InterviewAgentResponse
)
from app.models.user import UserModel
from app.models.question import Question, QuestionOption
from app.utils.dependencies import get_current_active_user


router = APIRouter(prefix="/api/v1/pipelines", tags=["Questions"])


@router.post("/{pipeline_id}/stages/{stage_id}/questions", response_model=QuestionResponse)
async def add_question(
    pipeline_id: str,
    stage_id: str,
    request: AddQuestionRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Add a question to a pipeline stage."""
    
    # Get pipeline
    pipeline = await db.pipelines.find_one({
        "_id": ObjectId(pipeline_id),
        "organization_id": current_user.organization_id
    })
    
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    # Find the stage
    stage_found = False
    for stage in pipeline.get("stages", []):
        if stage["stage_id"] == stage_id:
            stage_found = True
            
            # Create new question
            question_id = str(uuid.uuid4())
            new_question = Question(
                question_id=question_id,
                text=request.text,
                type=request.type,
                max_score=request.max_score,
                weight=request.weight,
                required=request.required,
                options=request.options,
                follow_up=request.follow_up,
                scoring_rubric=request.scoring_rubric,
                order=request.order
            )
            
            # Add question to stage
            if "questions" not in stage:
                stage["questions"] = []
            stage["questions"].append(new_question.model_dump())
            break
    
    if not stage_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stage not found"
        )
    
    # Update pipeline
    await db.pipelines.update_one(
        {"_id": ObjectId(pipeline_id)},
        {"$set": {"stages": pipeline["stages"]}}
    )
    
    return QuestionResponse(**new_question.model_dump())


@router.put("/{pipeline_id}/stages/{stage_id}/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    pipeline_id: str,
    stage_id: str,
    question_id: str,
    request: UpdateQuestionRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Update a question."""
    
    # Get pipeline
    pipeline = await db.pipelines.find_one({
        "_id": ObjectId(pipeline_id),
        "organization_id": current_user.organization_id
    })
    
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    # Find and update the question
    question_found = False
    updated_question = None
    
    for stage in pipeline.get("stages", []):
        if stage["stage_id"] == stage_id:
            for i, question in enumerate(stage.get("questions", [])):
                if question["question_id"] == question_id:
                    # Update fields
                    update_data = request.model_dump(exclude_unset=True)
                    for key, value in update_data.items():
                        question[key] = value
                    
                    stage["questions"][i] = question
                    updated_question = question
                    question_found = True
                    break
            break
    
    if not question_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Update pipeline
    await db.pipelines.update_one(
        {"_id": ObjectId(pipeline_id)},
        {"$set": {"stages": pipeline["stages"]}}
    )
    
    return QuestionResponse(**updated_question)


@router.delete("/{pipeline_id}/stages/{stage_id}/questions/{question_id}")
async def delete_question(
    pipeline_id: str,
    stage_id: str,
    question_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Delete a question."""
    
    # Get pipeline
    pipeline = await db.pipelines.find_one({
        "_id": ObjectId(pipeline_id),
        "organization_id": current_user.organization_id
    })
    
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    # Find and delete the question
    question_found = False
    
    for stage in pipeline.get("stages", []):
        if stage["stage_id"] == stage_id:
            questions = stage.get("questions", [])
            for i, question in enumerate(questions):
                if question["question_id"] == question_id:
                    questions.pop(i)
                    stage["questions"] = questions
                    question_found = True
                    break
            break
    
    if not question_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Update pipeline
    await db.pipelines.update_one(
        {"_id": ObjectId(pipeline_id)},
        {"$set": {"stages": pipeline["stages"]}}
    )
    
    return {"message": "Question deleted successfully"}


@router.get("/{pipeline_id}/stages/{stage_id}/questions", response_model=List[QuestionResponse])
async def list_questions(
    pipeline_id: str,
    stage_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """List all questions for a stage."""
    
    # Get pipeline
    pipeline = await db.pipelines.find_one({
        "_id": ObjectId(pipeline_id),
        "organization_id": current_user.organization_id
    })
    
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    # Find the stage
    for stage in pipeline.get("stages", []):
        if stage["stage_id"] == stage_id:
            questions = stage.get("questions", [])
            return [QuestionResponse(**q) for q in questions]
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Stage not found"
    )


@router.post("/{pipeline_id}/interview-agent", response_model=InterviewAgentResponse)
async def configure_interview_agent(
    pipeline_id: str,
    request: ConfigureInterviewAgentRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Configure AI interview agent for a pipeline."""
    
    # Get pipeline
    pipeline = await db.pipelines.find_one({
        "_id": ObjectId(pipeline_id),
        "organization_id": current_user.organization_id
    })
    
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    # Update interview agent
    agent_data = request.model_dump()
    await db.pipelines.update_one(
        {"_id": ObjectId(pipeline_id)},
        {"$set": {"interview_agent": agent_data}}
    )
    
    return InterviewAgentResponse(**agent_data)


@router.get("/{pipeline_id}/interview-agent", response_model=InterviewAgentResponse)
async def get_interview_agent(
    pipeline_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get AI interview agent configuration."""
    
    # Get pipeline
    pipeline = await db.pipelines.find_one({
        "_id": ObjectId(pipeline_id),
        "organization_id": current_user.organization_id
    })
    
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    agent = pipeline.get("interview_agent")
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview agent not configured"
        )
    
    return InterviewAgentResponse(**agent)


@router.post("/{pipeline_id}/interview-agent/auto-configure", response_model=InterviewAgentResponse)
async def auto_configure_interview_agent(
    pipeline_id: str,
    target_stage_id: str = None,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Auto-configure AI interview agent prompt based on pipeline questions."""
    
    # Get pipeline
    pipeline = await db.pipelines.find_one({
        "_id": ObjectId(pipeline_id),
        "organization_id": current_user.organization_id
    })
    
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    # 1. Gather questions
    questions = []
    
    if target_stage_id:
        # Get questions from specific stage
        for stage in pipeline.get("stages", []):
            if stage["stage_id"] == target_stage_id:
                questions = [Question(**q) for q in stage.get("questions", [])]
                break
        if not questions:
             # Fallback or error? For now, if stage empty, empty prompt.
             pass
    else:
        # Default: Get questions from first stage that has questions
        # OR aggregate all questions? 
        # Assuming single-stage interview for now based on user prompt '1-23'
        for stage in pipeline.get("stages", []):
            if stage.get("questions"):
                questions = [Question(**q) for q in stage.get("questions", [])]
                break
    
    if not questions:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No questions found in pipeline stages to generate prompt."
        )

    # 2. Generate Prompt
    from app.utils.prompt_generator import generate_system_prompt
    system_prompt = generate_system_prompt(questions)
    
    # 3. Update Interview Agent
    agent_data = pipeline.get("interview_agent", {})
    if not agent_data:
        agent_data = {
            "enabled": True,
            "agent_name": "Laura",
            "llm_provider": "openai",
            "llm_model": "gpt-4",
            "temperature": 0.7,
            "language": "es"
        }
    
    # Force update the prompt
    agent_data["agent_prompt"] = system_prompt
    agent_data["enabled"] = True # Enable it if we're auto-configuring
    
    await db.pipelines.update_one(
        {"_id": ObjectId(pipeline_id)},
        {"$set": {"interview_agent": agent_data}}
    )
    
    return InterviewAgentResponse(**agent_data)
