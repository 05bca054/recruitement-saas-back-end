"""User database models."""
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, Annotated
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic v2."""
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate),
            ])
        ])
    
    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")


class UserModel(BaseModel):
    """User database model."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organization_id: PyObjectId
    email: EmailStr
    password_hash: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    role_id: Optional[PyObjectId] = None
    status: str = "active"  # active, inactive, invited
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OrganizationModel(BaseModel):
    """Organization database model."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    slug: str
    domain: Optional[str] = None
    subscription: dict = {
        "plan": "free",
        "status": "active",
        "started_at": None,
        "expires_at": None
    }
    settings: dict = {
        "timezone": "UTC",
        "language": "en",
        "branding": {
            "logo_url": None,
            "primary_color": "#4F46E5",
            "secondary_color": "#10B981"
        }
    }
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[PyObjectId] = None
    
    # Airtable configuration
    airtable_config: Optional[dict] = {
        "api_key": None,              # Encrypted Airtable API key
        "base_id": None,              # Airtable base ID (created automatically)
        "base_name": None,            # Base name (e.g., "Acme Corp Recruitment")
        "is_configured": False,
        "created_at": None
    }
    
    # AI Usage Stats
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_ai_cost: float = 0.0


class RefreshTokenModel(BaseModel):
    """Refresh token database model."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: PyObjectId
    token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

