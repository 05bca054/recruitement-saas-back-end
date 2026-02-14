"""Airtable integration router."""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

from app.database import get_db
from app.schemas.airtable import AirtableConfigRequest, AirtableConfigResponse
from app.models.user import UserModel
from app.utils.dependencies import get_current_active_user
from app.services.airtable_service import AirtableService


router = APIRouter(prefix="/api/v1/integrations/airtable", tags=["Airtable"])


@router.post("/configure", response_model=AirtableConfigResponse)
async def configure_airtable(
    request: AirtableConfigRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Configure Airtable integration for organization."""
    
    # Get organization
    org = await db.organizations.find_one({"_id": current_user.organization_id})
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Verify the base exists by trying to access it
    try:
        airtable = AirtableService(request.api_key)
        # Try to list tables to verify access
        async with airtable.client() as client:
            response = await client.get(
                f"{airtable.meta_url}/bases/{request.base_id}/tables",
                headers={"Authorization": f"Bearer {request.api_key}"},
                timeout=10.0
            )
            response.raise_for_status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to access Airtable base. Please verify your API key and base ID. Error: {str(e)}"
        )
    
    # Update organization with Airtable config
    await db.organizations.update_one(
        {"_id": current_user.organization_id},
        {"$set": {
            "airtable_config": {
                "api_key": request.api_key,  # TODO: Encrypt this in production
                "base_id": request.base_id,
                "is_configured": True,
                "created_at": datetime.utcnow()
            }
        }}
    )
    
    return AirtableConfigResponse(
        message="Airtable configured successfully",
        base_id=request.base_id
    )


@router.get("/config")
async def get_airtable_config(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get current Airtable configuration."""
    
    org = await db.organizations.find_one({"_id": current_user.organization_id})
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    airtable_config = org.get("airtable_config", {})
    
    # Don't expose API key
    if airtable_config.get("api_key"):
        airtable_config["api_key"] = "***" + airtable_config["api_key"][-4:] if len(airtable_config["api_key"]) > 4 else "***"
    
    return {
        "is_configured": airtable_config.get("is_configured", False),
        "base_id": airtable_config.get("base_id"),
        "base_name": airtable_config.get("base_name"),
        "created_at": airtable_config.get("created_at")
    }
