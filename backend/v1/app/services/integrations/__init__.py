"""
Integration services package
Platform-specific integrations isolated from core bot logic
"""

from app.services.integrations.base import IntegrationService
from app.services.integrations.manager import IntegrationManager
from app.services.integrations.whatsapp import WhatsAppIntegration

__all__ = [
    'IntegrationService',
    'IntegrationManager',
    'WhatsAppIntegration',
]
