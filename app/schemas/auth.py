"""Authentication request/response schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    """Registration request schema."""
    
    organization_name: str = Field(..., min_length=2, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request schema."""
    
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    
    refresh_token: str


class UserResponse(BaseModel):
    """User response schema."""
    
    id: str
    organization_id: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    role_id: Optional[str] = None
    status: str
    last_login: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class OrganizationResponse(BaseModel):
    """Organization response schema."""
    
    id: str
    name: str
    slug: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_ai_cost: float = 0.0
    
    class Config:
        from_attributes = True

class TelegramConfigUpdate(BaseModel):
    """Telegram configuration update schema."""
    bot_token: str
    bot_username: Optional[str] = None
