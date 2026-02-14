"""Airtable integration schemas."""
from pydantic import BaseModel
from typing import Optional


class AirtableConfigRequest(BaseModel):
    """Request to configure Airtable."""
    api_key: str
    base_id: str  # User provides existing base ID instead of creating one


class AirtableConfigResponse(BaseModel):
    """Response after configuring Airtable."""
    message: str
    base_id: str
