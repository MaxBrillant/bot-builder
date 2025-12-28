"""
Bot Management Schemas
Pydantic models for bot CRUD operations
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class BotCreate(BaseModel):
    """Schema for creating a new bot"""
    name: str = Field(..., min_length=1, max_length=255, description="Bot display name")
    description: Optional[str] = Field(None, max_length=1024, description="Bot description")


class BotUpdate(BaseModel):
    """Schema for updating bot details"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Bot display name")
    description: Optional[str] = Field(None, max_length=1024, description="Bot description")
    status: Optional[str] = Field(None, pattern="^(active|inactive)$", description="Bot status")


class BotResponse(BaseModel):
    """Schema for bot response"""
    bot_id: UUID
    owner_user_id: UUID
    name: str
    description: Optional[str]
    webhook_url: str  # Computed field
    webhook_secret: Optional[str] = None  # Only included when explicitly requested
    status: str
    created_at: datetime
    updated_at: datetime
    flow_count: Optional[int] = None  # Optional aggregation

    # WhatsApp connection info
    whatsapp_connected: bool = False  # Computed from evolution_instance_status
    whatsapp_phone_number: Optional[str] = None
    whatsapp_status: Optional[str] = None  # disconnected/pending/connected/error

    class Config:
        from_attributes = True


class BotListResponse(BaseModel):
    """Schema for listing bots"""
    bots: list[BotResponse]
    total: int


class WebhookSecretResponse(BaseModel):
    """Schema for webhook secret regeneration"""
    bot_id: UUID
    webhook_secret: str
    message: str = "Webhook secret regenerated successfully"