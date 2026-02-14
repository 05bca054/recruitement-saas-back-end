"""Authentication router."""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from bson import ObjectId
import re

from app.database import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    OrganizationResponse
)
from app.models.user import UserModel, OrganizationModel, RefreshTokenModel
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.utils.dependencies import get_current_active_user
from app.config import settings


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def create_slug(name: str) -> str:
    """Create URL-friendly slug from organization name."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Register a new organization with admin user."""
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create organization
    org_slug = create_slug(request.organization_name)
    
    # Check if slug already exists
    existing_org = await db.organizations.find_one({"slug": org_slug})
    if existing_org:
        # Append random suffix
        import random
        org_slug = f"{org_slug}-{random.randint(1000, 9999)}"
    
    organization = OrganizationModel(
        name=request.organization_name,
        slug=org_slug
    )
    
    org_result = await db.organizations.insert_one(organization.model_dump(by_alias=True, exclude={"id"}))
    org_id = org_result.inserted_id
    
    # Update organization with created_by
    await db.organizations.update_one(
        {"_id": org_id},
        {"$set": {"created_by": org_id}}  # Will update after user creation
    )
    
    # Create admin user
    user = UserModel(
        organization_id=org_id,
        email=request.email,
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        status="active"
    )
    
    user_result = await db.users.insert_one(user.model_dump(by_alias=True, exclude={"id"}))
    user_id = user_result.inserted_id
    
    # Update organization created_by
    await db.organizations.update_one(
        {"_id": org_id},
        {"$set": {"created_by": user_id}}
    )
    
    # Create tokens
    access_token = create_access_token({"sub": str(user_id), "org_id": str(org_id)})
    refresh_token_str = create_refresh_token({"sub": str(user_id), "org_id": str(org_id)})
    
    # Store refresh token
    refresh_token = RefreshTokenModel(
        user_id=user_id,
        token=refresh_token_str,
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    )
    await db.refresh_tokens.insert_one(refresh_token.model_dump(by_alias=True, exclude={"id"}))
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Login with email and password."""
    
    # Find user by email
    user_data = await db.users.find_one({"email": request.email})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    user = UserModel(**user_data)
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    await db.users.update_one(
        {"_id": user.id},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create tokens
    access_token = create_access_token({"sub": str(user.id), "org_id": str(user.organization_id)})
    refresh_token_str = create_refresh_token({"sub": str(user.id), "org_id": str(user.organization_id)})
    
    # Store refresh token
    refresh_token = RefreshTokenModel(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    )
    await db.refresh_tokens.insert_one(refresh_token.model_dump(by_alias=True, exclude={"id"}))
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Refresh access token using refresh token."""
    
    # Decode refresh token
    payload = decode_token(request.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    org_id = payload.get("org_id")
    
    # Verify refresh token exists in database
    token_data = await db.refresh_tokens.find_one({
        "user_id": ObjectId(user_id),
        "token": request.refresh_token
    })
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    token = RefreshTokenModel(**token_data)
    
    # Check if token is expired
    if token.expires_at < datetime.utcnow():
        # Delete expired token
        await db.refresh_tokens.delete_one({"_id": token.id})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
    
    # Create new access token
    access_token = create_access_token({"sub": user_id, "org_id": org_id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/logout")
async def logout(
    request: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Logout by invalidating refresh token."""
    
    # Delete refresh token
    result = await db.refresh_tokens.delete_one({"token": request.refresh_token})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token not found"
        )
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get current user information."""
    
    return UserResponse(
        id=str(current_user.id),
        organization_id=str(current_user.organization_id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        avatar_url=current_user.avatar_url,
        role_id=str(current_user.role_id) if current_user.role_id else None,
        status=current_user.status,
        last_login=current_user.last_login,
        created_at=current_user.created_at
    )

@router.get("/organization", response_model=OrganizationResponse)
async def get_current_organization(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get current user's organization with usage stats."""
    org = await db.organizations.find_one({"_id": current_user.organization_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return OrganizationResponse(
        id=str(org["_id"]),
        name=org["name"],
        slug=org["slug"],
        total_input_tokens=org.get("total_input_tokens", 0),
        total_output_tokens=org.get("total_output_tokens", 0),
        total_ai_cost=org.get("total_ai_cost", 0.0)
    )
