"""
Webhook Message Schemas
Pydantic models for bot webhook message processing
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class WebhookMessageRequest(BaseModel):
    """
    Schema for incoming webhook messages
    
    This is the standardized format that integration layers (Evolution API, etc.)
    must send to the bot webhook endpoint.
    """
    channel: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Communication channel (e.g., 'WHATSAPP', 'TELEGRAM', 'SLACK')",
        examples=["WHATSAPP", "TELEGRAM", "SLACK"]
    )
    channel_user_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Platform-specific user identifier (e.g., phone number for WhatsApp, user ID for Slack)",
        examples=["+254712345678", "U012345", "@username"]
    )
    message_text: str = Field(
        ...,
        max_length=1024,
        description="The text message content from the user"
    )


class WebhookMessageResponse(BaseModel):
    """Schema for webhook message response"""
    status: str = Field(..., description="Response status: 'success' or 'error'")
    messages: List[str] = Field(default_factory=list, description="List of messages to send back to user (each rendered as separate message)")
    session_id: Optional[str] = Field(None, description="Session identifier")
    error: Optional[str] = Field(None, description="Error message if status is 'error'")

    class Config:
        from_attributes = True