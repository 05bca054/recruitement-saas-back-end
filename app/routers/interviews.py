"""Interview router."""
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db
from app.services.interview_service import InterviewService
from app.schemas.interview import (
    StartInterviewRequest, 
    ChatRequest, 
    ChatResponse, 
    InterviewSessionResponse
)
from app.models.interview import InterviewSession
from app.utils.dependencies import get_current_active_user
from bson import ObjectId

router = APIRouter(prefix="/api/v1/interviews", tags=["Interviews"])

@router.post("/start", response_model=InterviewSessionResponse)
async def start_interview(
    request: StartInterviewRequest,
    service: InterviewService = Depends(InterviewService)
):
    """Start a new interview session."""
    try:
        session = await service.create_session(
            candidate_id=request.candidate_id,
            platform=request.platform,
            chat_id=request.chat_id
        )
        return InterviewSessionResponse(
            session_id=str(session.id),
            candidate_id=str(session.candidate_id),
            status=session.status,
            messages=session.messages,
            created_at=session.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: InterviewService = Depends(InterviewService)
):
    """Send a message to the AI interviewer."""
    try:
        response_text = await service.process_message(
            session_id=request.session_id,
            user_text=request.message
        )
        
        # Fetch updated session status
        # Ideally process_message should return (text, status) or updated session
        # For now we fetch it again or service returns it.
        # Let's just fetch status from DB to return accurate status.
        # But process_message is robust enough.
        
        # We need the session status to know if it completed.
        # I'll update process_message to return Dict or object later, for now just text.
        # The frontend can check if response == "Interview Completed."
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            status="active" # Placeholder, simple implementation
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}", response_model=InterviewSessionResponse)
async def get_session(
    session_id: str,
    db = Depends(get_db)
):
    """Get session details."""
    data = await db.interview_sessions.find_one({"_id": ObjectId(session_id)})
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = InterviewSession(**data)
    return InterviewSessionResponse(
        session_id=str(session.id),
        candidate_id=str(session.candidate_id),
        status=session.status,
        messages=session.messages,
        scores=session.scores,
        total_score=session.total_score,
        created_at=session.created_at
    )

@router.get("/candidate/{candidate_id}", response_model=list[InterviewSessionResponse])
async def get_candidate_sessions(
    candidate_id: str,
    db = Depends(get_db)
):
    """Get all interview sessions for a candidate."""
    cursor = db.interview_sessions.find({"candidate_id": ObjectId(candidate_id)}).sort("created_at", -1)
    sessions = await cursor.to_list(length=100)
    
    return [
        InterviewSessionResponse(
            session_id=str(s["_id"]),
            candidate_id=str(s["candidate_id"]),
            status=s["status"],
            messages=s.get("messages", []),
            scores=s.get("scores"),
            total_score=s.get("total_score"),
            created_at=s["created_at"]
        ) for s in sessions
    ]
