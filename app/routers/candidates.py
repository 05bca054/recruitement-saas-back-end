"""Candidate router."""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import List

from app.database import get_db
from app.schemas.candidate import (
    CreateCandidateRequest,
    CandidateResponse,
    UpdateCandidateRequest
)
from app.models.candidate import CandidateModel
from app.models.user import UserModel
from app.utils.dependencies import get_current_active_user
from app.services.airtable_service import AirtableService


router = APIRouter(prefix="/api/v1/candidates", tags=["Candidates"])


@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    request: CreateCandidateRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Create a candidate and sync to Airtable."""
    
    # Get pipeline
    pipeline = await db.pipelines.find_one({
        "_id": ObjectId(request.pipeline_id),
        "organization_id": current_user.organization_id
    })
    
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    # Get first stage if pipeline has stages
    first_stage_id = None
    first_stage_name = ""
    if pipeline.get("stages"):
        first_stage_id = pipeline["stages"][0]["stage_id"]
        first_stage_name = pipeline["stages"][0]["name"]
    
    # Create candidate
    candidate = CandidateModel(
        organization_id=current_user.organization_id,
        pipeline_id=ObjectId(request.pipeline_id),
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        phone=request.phone,
        resume_url=request.resume_url,
        current_stage_id=first_stage_id
    )
    
    result = await db.candidates.insert_one(candidate.model_dump(by_alias=True, exclude={"id"}))
    candidate_id = result.inserted_id
    
    # Sync to Airtable if pipeline is synced
    airtable_record_id = None
    if pipeline.get("airtable_synced") and pipeline.get("airtable_table_id"):
        try:
            org = await db.organizations.find_one({"_id": current_user.organization_id})
            airtable_config = org.get("airtable_config", {})
            
            if airtable_config.get("is_configured"):
                airtable = AirtableService(airtable_config["api_key"])
                
                airtable_record = await airtable.create_record(
                    airtable_config["base_id"],
                    pipeline["airtable_table_id"],
                    {
                        "Name": f"{request.first_name} {request.last_name}",
                        "Email": request.email,
                        "Phone": request.phone or "",
                        "Current Stage": first_stage_name,
                        "Status": "Active",
                        "Overall Score": 0,
                        "Created At": datetime.utcnow().isoformat()
                    }
                )
                
                airtable_record_id = airtable_record["id"]
                
                # Update candidate with Airtable record ID
                await db.candidates.update_one(
                    {"_id": candidate_id},
                    {"$set": {"airtable_record_id": airtable_record_id}}
                )
        except Exception as e:
            print(f"Failed to sync candidate to Airtable: {str(e)}")
    
    return CandidateResponse(
        id=str(candidate_id),
        organization_id=str(current_user.organization_id),
        pipeline_id=str(request.pipeline_id),
        current_stage_id=first_stage_id,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        phone=request.phone,
        resume_url=request.resume_url,
        status="active",
        overall_score=0.0,
        airtable_record_id=airtable_record_id,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at
    )


@router.get("/", response_model=List[CandidateResponse])
async def list_candidates(
    pipeline_id: str = None,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """List all candidates for the organization."""
    
    query = {"organization_id": current_user.organization_id}
    if pipeline_id:
        query["pipeline_id"] = ObjectId(pipeline_id)
    
    candidates = await db.candidates.find(query).to_list(length=100)
    
    return [
        CandidateResponse(
            id=str(c["_id"]),
            organization_id=str(c["organization_id"]),
            pipeline_id=str(c["pipeline_id"]),
            current_stage_id=c.get("current_stage_id"),
            first_name=c["first_name"],
            last_name=c["last_name"],
            email=c["email"],
            phone=c.get("phone"),
            resume_url=c.get("resume_url"),
            status=c.get("status", "active"),
            overall_score=c.get("overall_score", 0.0),
            airtable_record_id=c.get("airtable_record_id"),
            created_at=c["created_at"],
            updated_at=c["updated_at"]
        )
        for c in candidates
    ]


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get a specific candidate."""
    
    candidate = await db.candidates.find_one({
        "_id": ObjectId(candidate_id),
        "organization_id": current_user.organization_id
    })
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    return CandidateResponse(
        id=str(candidate["_id"]),
        organization_id=str(candidate["organization_id"]),
        pipeline_id=str(candidate["pipeline_id"]),
        current_stage_id=candidate.get("current_stage_id"),
        first_name=candidate["first_name"],
        last_name=candidate["last_name"],
        email=candidate["email"],
        phone=candidate.get("phone"),
        resume_url=candidate.get("resume_url"),
        status=candidate.get("status", "active"),
        overall_score=candidate.get("overall_score", 0.0),
        airtable_record_id=candidate.get("airtable_record_id"),
        created_at=candidate["created_at"],
        updated_at=candidate["updated_at"]
    )
