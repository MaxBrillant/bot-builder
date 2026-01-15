"""
Repository pattern implementation for data access layer

Repositories centralize all database queries and solve N+1 query problems
using SQLAlchemy's relationship loading strategies.
"""

from app.repositories.base import BaseRepository
from app.repositories.user_repository import UserRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.bot_integration_repository import BotIntegrationRepository
from app.repositories.flow_repository import FlowRepository
from app.repositories.session_repository import SessionRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "BotRepository",
    "BotIntegrationRepository",
    "FlowRepository",
    "SessionRepository",
]
