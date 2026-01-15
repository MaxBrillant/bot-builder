"""
WhatsApp Management Schemas
Pydantic models for WhatsApp/Evolution API integration
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WhatsAppStatusResponse(BaseModel):
    """
    WhatsApp connection status response

    Returned by status, connect, disconnect, and reconnect endpoints
    """
    status: str = Field(
        ...,
        description="Connection status: DISCONNECTED, CONNECTING, CONNECTED, or ERROR",
        pattern="^(DISCONNECTED|CONNECTING|CONNECTED|ERROR)$"
    )
    instance_name: Optional[str] = Field(
        None,
        description="Evolution API instance name"
    )
    phone_number: Optional[str] = Field(
        None,
        description="Connected WhatsApp phone number (when status=CONNECTED)"
    )
    connected_at: Optional[datetime] = Field(
        None,
        description="Timestamp when WhatsApp was connected"
    )
    qr_code: Optional[str] = Field(
        None,
        description="Base64-encoded QR code image (only when status=CONNECTING)"
    )
    message: Optional[str] = Field(
        None,
        description="Additional status message or error details"
    )

    class Config:
        from_attributes = True


class EvolutionWebhookData(BaseModel):
    """
    Evolution API webhook payload structure (simplified)

    Evolution API sends various event types. The most common structure includes:
    - event: Event type (e.g., "messages.upsert")
    - instance: Instance name that received the event
    - data: Event-specific data (varies by event type)
    """
    event: str = Field(
        ...,
        description="Event type from Evolution API"
    )
    instance: str = Field(
        ...,
        description="Instance name"
    )
    data: dict = Field(
        ...,
        description="Event-specific data payload"
    )

    class Config:
        extra = "allow"  # Allow additional fields from Evolution API
