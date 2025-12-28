"""
API Route Handlers
RESTful API endpoints for the Bot Builder system
"""

from app.api.auth import router as auth_router
from app.api.bots import router as bots_router
from app.api.flows import router as flows_router
from app.api.webhooks import router as webhooks_router
from app.api.oauth import router as oauth_router
from app.api.whatsapp import router as whatsapp_router
from app.api.evolution_webhooks import router as evolution_webhooks_router

__all__ = [
    "auth_router",
    "bots_router",
    "flows_router",
    "webhooks_router",
    "oauth_router",
    "whatsapp_router",
    "evolution_webhooks_router"
]