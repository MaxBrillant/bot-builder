"""
API Route Handlers
RESTful API endpoints for the Bot Builder system
"""

from app.api.auth import router as auth_router
from app.api.bots import router as bots_router
from app.api.flows import router as flows_router
from app.api.oauth import router as oauth_router
from app.api.whatsapp import router as whatsapp_router
from app.api.evolution_proxy import router as evolution_proxy_router

# Webhook routers (organized in webhooks/ directory)
from app.api.webhooks import (
    core_router as core_webhook_router,
    whatsapp_router as whatsapp_webhook_router
)

__all__ = [
    "auth_router",
    "bots_router",
    "flows_router",
    "core_webhook_router",
    "oauth_router",
    "whatsapp_router",
    "whatsapp_webhook_router",
    "evolution_proxy_router"
]