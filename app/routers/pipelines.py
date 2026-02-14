"""Pipeline router."""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import List

from app.database import get_db
from app.schemas.pipeline import (
    CreatePipelineRequest,
    PipelineResponse,
    UpdatePipelineRequest
)
from app.models.pipeline import RecruitmentPipelineModel, PipelineStage
from app.models.user import UserModel
from app.utils.dependencies import get_current_active_user
from app.services.airtable_service import AirtableService


router = APIRouter(prefix="/api/v1/pipelines", tags=["Pipelines"])


@router.post("/", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    request: CreatePipelineRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Create a new recruitment pipeline and optionally sync to Airtable."""
    
    # Get organization Airtable config (optional)
    org = await db.organizations.find_one({"_id": current_user.organization_id})
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Convert request stages to model stages
    stages = [PipelineStage(**stage.model_dump()) for stage in request.stages]
    
    # Create pipeline
    pipeline = RecruitmentPipelineModel(
        organization_id=current_user.organization_id,
        name=request.name,
        description=request.description,
        stages=stages,
        created_by=current_user.id
    )
    
    result = await db.pipelines.insert_one(pipeline.model_dump(by_alias=True, exclude={"id"}))
    pipeline_id = result.inserted_id
    
    # Try to sync to Airtable if configured
    airtable_table_id = None
    airtable_table_name = None
    airtable_synced = False
    
    airtable_config = org.get("airtable_config", {})
    if airtable_config.get("is_configured"):
        try:
            airtable = AirtableService(airtable_config["api_key"])
            table_name = f"{request.name}"
            table_response = await airtable.create_table(airtable_config["base_id"], table_name)
            
            # Update pipeline with Airtable table info
            await db.pipelines.update_one(
                {"_id": pipeline_id},
                {"$set": {
                    "airtable_table_id": table_response["id"],
                    "airtable_table_name": table_name,
                    "airtable_synced": True
                }}
            )
            
            airtable_table_id = table_response["id"]
            airtable_table_name = table_name
            airtable_synced = True
            print(f"✅ Airtable table created: {table_name}")
        except Exception as e:
            print(f"⚠️  Airtable sync failed (pipeline still created): {str(e)}")
            # Pipeline is still created successfully, just without Airtable sync
    
    return PipelineResponse(
        id=str(pipeline_id),
        organization_id=str(current_user.organization_id),
        name=pipeline.name,
        description=pipeline.description,
        status=pipeline.status,
        stages=[stage.model_dump() for stage in pipeline.stages],
        airtable_table_id=airtable_table_id,
        airtable_table_name=airtable_table_name,
        airtable_synced=airtable_synced,
        created_at=pipeline.created_at,
        updated_at=pipeline.updated_at,
        created_by=str(current_user.id)
    )


@router.get("/", response_model=List[PipelineResponse])
async def list_pipelines(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """List all pipelines for the organization."""
    
    pipelines = await db.pipelines.find({
        "organization_id": current_user.organization_id,
        "status": {"$ne": "archived"}
    }).to_list(length=100)
    
    return [
        PipelineResponse(
            id=str(p["_id"]),
            organization_id=str(p["organization_id"]),
            name=p["name"],
            description=p.get("description"),
            status=p["status"],
            stages=p.get("stages", []),
            airtable_table_id=p.get("airtable_table_id"),
            airtable_table_name=p.get("airtable_table_name"),
            airtable_synced=p.get("airtable_synced", False),
            created_at=p["created_at"],
            updated_at=p["updated_at"],
            created_by=str(p["created_by"])
        )
        for p in pipelines
    ]


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get a specific pipeline."""
    
    pipeline = await db.pipelines.find_one({
        "_id": ObjectId(pipeline_id),
        "organization_id": current_user.organization_id
    })
    
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    return PipelineResponse(
        id=str(pipeline["_id"]),
        organization_id=str(pipeline["organization_id"]),
        name=pipeline["name"],
        description=pipeline.get("description"),
        status=pipeline["status"],
        stages=pipeline.get("stages", []),
        airtable_table_id=pipeline.get("airtable_table_id"),
        airtable_table_name=pipeline.get("airtable_table_name"),
        airtable_synced=pipeline.get("airtable_synced", False),
        created_at=pipeline["created_at"],
        updated_at=pipeline["updated_at"],
        created_by=str(pipeline["created_by"])
    )


@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: str,
    request: UpdatePipelineRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Update a pipeline."""
    
    # Check if pipeline exists
    pipeline = await db.pipelines.find_one({
        "_id": ObjectId(pipeline_id),
        "organization_id": current_user.organization_id
    })
    
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    # Prepare update data
    update_data = request.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    # If stages are updated, we need to convert them to dicts
    if "stages" in update_data:
        # We need to preserve existing questions if not provided in request
        # But UpdatePipelineRequest typically replaces the list.
        # Here we assume the client sends the full stages list if updating stages.
        # However, StageRequest doesn't have 'questions' field in schema?
        # Let's check schema. StageRequest has config but no questions field definition.
        # Wait, if we use StageRequest, we lose questions!
        # Implementation issue: UpdatePipelineRequest.stages is List[StageRequest]
        # StageRequest definition in schema: name, order, type, config. No questions.
        
        # We must be careful not to overwrite questions with empty list.
        # Approach: Merge questions from existing pipeline into new stages based on stage_id
        
        current_stages_map = {s["stage_id"]: s for s in pipeline.get("stages", [])}
        new_stages = []
        
        for stage_req in update_data["stages"]: # These are dicts now
            # stage_req is a dict from model_dump
            stage_id = stage_req.get("stage_id")
            if stage_id in current_stages_map:
                # Preserve questions
                existing = current_stages_map[stage_id]
                if "questions" in existing:
                    stage_req["questions"] = existing["questions"]
            
            new_stages.append(stage_req)
        
        update_data["stages"] = new_stages

    await db.pipelines.update_one(
        {"_id": ObjectId(pipeline_id)},
        {"$set": update_data}
    )
    
    # Get updated pipeline
    updated_pipeline = await db.pipelines.find_one({"_id": ObjectId(pipeline_id)})
    
    return PipelineResponse(
        id=str(updated_pipeline["_id"]),
        organization_id=str(updated_pipeline["organization_id"]),
        name=updated_pipeline["name"],
        description=updated_pipeline.get("description"),
        status=updated_pipeline["status"],
        stages=updated_pipeline.get("stages", []),
        airtable_table_id=updated_pipeline.get("airtable_table_id"),
        airtable_table_name=updated_pipeline.get("airtable_table_name"),
        airtable_synced=updated_pipeline.get("airtable_synced", False),
        created_at=updated_pipeline["created_at"],
        updated_at=updated_pipeline["updated_at"],
        created_by=str(updated_pipeline["created_by"])
    )


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(
    pipeline_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Delete (archive) a pipeline."""
    
    result = await db.pipelines.update_one(
        {
            "_id": ObjectId(pipeline_id),
            "organization_id": current_user.organization_id
        },
        {"$set": {"status": "archived"}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )
    
    return None
