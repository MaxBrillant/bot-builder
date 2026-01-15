"""
Webhooks Package

All webhook endpoints organized by purpose:
- core: Platform-agnostic core webhook (receives normalized messages)
- whatsapp: WhatsApp integration (messages + system events via Evolution API)

Future integrations: telegram.py, slack.py, etc.
"""

from app.api.webhooks.core import router as core_router
from app.api.webhooks.whatsapp import router as whatsapp_router

__all__ = [
    'core_router',
    'whatsapp_router',
]
