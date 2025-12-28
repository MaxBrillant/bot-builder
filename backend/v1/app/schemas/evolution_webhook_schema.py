"""
Evolution API Webhook Event Schemas
Pydantic models for validating webhook events from Evolution API v2
"""

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class QRCodeData(BaseModel):
    """QR code data from QRCODE_UPDATED event"""
    qrcode: Optional[str] = Field(None, description="Base64-encoded QR code image")
    code: Optional[str] = Field(None, description="Alternative field for QR code")
    base64: Optional[str] = Field(None, description="Alternative field for QR code")
    pairingCode: Optional[str] = Field(None, description="Pairing code (alternative to QR)")


class ConnectionUpdateData(BaseModel):
    """Connection state data from CONNECTION_UPDATE event"""
    state: str = Field(..., description="Connection state: open, close, connecting")
    instance: Optional[Dict[str, Any]] = Field(None, description="Instance details including phone number")


class MessageData(BaseModel):
    """Message data from MESSAGES_UPSERT event"""
    key: Dict[str, Any] = Field(..., description="Message key with remoteJid, fromMe, id")
    message: Optional[Dict[str, Any]] = Field(None, description="Message content")
    messageTimestamp: Optional[int] = Field(None, description="Unix timestamp")
    pushName: Optional[str] = Field(None, description="Sender name")
    messageType: Optional[str] = Field(None, description="Message type: conversation, imageMessage, etc.")


class BaseWebhookEvent(BaseModel):
    """Base webhook event structure"""
    event: str = Field(..., description="Event type: qrcode.updated, connection.update, etc.")
    instance: str = Field(..., description="Instance name (e.g., bot_uuid_with_underscores)")
    data: Dict[str, Any] = Field(..., description="Event-specific data")
    server_url: Optional[str] = Field(None, description="Evolution API server URL")
    apikey: Optional[str] = Field(None, description="API key used (for verification)")


class QRCodeUpdatedEvent(BaseWebhookEvent):
    """QRCODE_UPDATED webhook event"""
    event: Literal["qrcode.updated"]
    data: QRCodeData


class ConnectionUpdateEvent(BaseWebhookEvent):
    """CONNECTION_UPDATE webhook event"""
    event: Literal["connection.update"]
    data: ConnectionUpdateData


class MessageUpsertEvent(BaseWebhookEvent):
    """MESSAGES_UPSERT webhook event"""
    event: Literal["messages.upsert"]
    data: Dict[str, Any]  # Can contain single message or array


class WebhookResponse(BaseModel):
    """Response returned to Evolution API after webhook processing"""
    status: str = Field("received", description="Processing status")
    message: Optional[str] = Field(None, description="Optional message")
    timestamp: Optional[datetime] = Field(None, description="Processing timestamp")


class QRCodeStorageData(BaseModel):
    """Data structure for storing QR codes in Redis"""
    qr_code: str = Field(..., description="Base64-encoded QR code")
    instance_name: str = Field(..., description="Evolution API instance name")
    timestamp: datetime = Field(..., description="When QR code was received")
    bot_id: Optional[str] = Field(None, description="Associated bot ID")


class QRCodeResponse(BaseModel):
    """Response for GET /whatsapp/qr-code endpoint"""
    qr_code: str = Field(..., description="Base64-encoded QR code image")
    instance_name: str = Field(..., description="Evolution API instance name")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    message: Optional[str] = Field(None, description="Optional message for frontend")
