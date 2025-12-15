"""
Bot Management API
Endpoints for creating and managing bots
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.bot_service import BotService
from app.schemas.bot_schema import (
    BotCreate,
    BotUpdate,
    BotResponse,
    BotListResponse,
    WebhookSecretResponse
)
from app.utils.exceptions import NotFoundError, UnauthorizedError
from app.config import settings

router = APIRouter(prefix="/bots", tags=["bots"])


def bot_to_response(bot, include_secret: bool = False) -> BotResponse:
    """Convert Bot model to BotResponse schema"""
    return BotResponse(
        bot_id=bot.bot_id,
        owner_user_id=bot.owner_user_id,
        name=bot.name,
        description=bot.description,
        webhook_url=f"{settings.base_url}/webhook/{bot.bot_id}",
        webhook_secret=bot.webhook_secret if include_secret else None,
        status=bot.status,
        created_at=bot.created_at,
        updated_at=bot.updated_at
    )


@router.post("", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    bot_data: BotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new bot
    
    - **name**: Bot display name (required)
    - **description**: Optional bot description
    
    Returns the created bot with webhook_secret (save this - it's only shown once!)
    """
    bot_service = BotService(db)
    
    bot = await bot_service.create_bot(
        name=bot_data.name,
        owner_user_id=current_user.user_id,
        description=bot_data.description
    )
    
    # Include secret in response (only time it's shown)
    return bot_to_response(bot, include_secret=True)


@router.get("", response_model=BotListResponse)
async def list_bots(
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all bots owned by the current user (includes webhook_secret for authenticated owner)
    
    - **status**: Optional filter by status ('active' or 'inactive')
    """
    bot_service = BotService(db)
    
    bots = await bot_service.list_bots(
        owner_user_id=current_user.user_id,
        status=status
    )
    
    # Include secrets since user owns these bots and needs them for webhook configuration
    return BotListResponse(
        bots=[bot_to_response(bot, include_secret=True) for bot in bots],
        total=len(bots)
    )


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get bot details by ID (includes webhook_secret for authenticated owner)"""
    bot_service = BotService(db)
    
    try:
        bot = await bot_service.get_bot(
            bot_id=bot_id,
            owner_user_id=current_user.user_id,
            check_ownership=True
        )
        # Include secret since user owns the bot and needs it for webhook configuration
        return bot_to_response(bot, include_secret=True)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: UUID,
    bot_data: BotUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update bot details
    
    - **name**: New bot name (optional)
    - **description**: New description (optional)
    - **status**: New status - 'active' or 'inactive' (optional)
    """
    bot_service = BotService(db)
    
    try:
        bot = await bot_service.update_bot(
            bot_id=bot_id,
            owner_user_id=current_user.user_id,
            name=bot_data.name,
            description=bot_data.description,
            status=bot_data.status
        )
        # Include secret since user owns the bot and needs it for webhook configuration
        return bot_to_response(bot, include_secret=True)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a bot
    
    **Warning**: This will cascade delete all flows and active sessions for this bot!
    """
    bot_service = BotService(db)
    
    try:
        await bot_service.delete_bot(
            bot_id=bot_id,
            owner_user_id=current_user.user_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{bot_id}/regenerate-secret", response_model=WebhookSecretResponse)
async def regenerate_webhook_secret(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate webhook secret for security
    
    **Important**: 
    - Save the new secret immediately!
    - Update your integration layer with the new secret
    - Old secret will stop working immediately
    """
    bot_service = BotService(db)
    
    try:
        bot = await bot_service.regenerate_webhook_secret(
            bot_id=bot_id,
            owner_user_id=current_user.user_id
        )
        return WebhookSecretResponse(
            bot_id=bot.bot_id,
            webhook_secret=bot.webhook_secret
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{bot_id}/activate", response_model=BotResponse)
async def activate_bot(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Activate a bot (sets status to 'active')"""
    bot_service = BotService(db)
    
    try:
        bot = await bot_service.set_bot_status(
            bot_id=bot_id,
            owner_user_id=current_user.user_id,
            status='active'
        )
        # Include secret since user owns the bot and needs it for webhook configuration
        return bot_to_response(bot, include_secret=True)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{bot_id}/deactivate", response_model=BotResponse)
async def deactivate_bot(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a bot (sets status to 'inactive')"""
    bot_service = BotService(db)
    
    try:
        bot = await bot_service.set_bot_status(
            bot_id=bot_id,
            owner_user_id=current_user.user_id,
            status='inactive'
        )
        # Include secret since user owns the bot and needs it for webhook configuration
        return bot_to_response(bot, include_secret=True)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))