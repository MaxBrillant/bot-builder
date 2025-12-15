"""
Flow Management API
Endpoints for creating, reading, updating, and deleting flows
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.bot import Bot
from app.schemas.flow_schema import (
    FlowCreate,
    FlowUpdate,
    FlowResponse,
    FlowListResponse,
    FlowValidationResponse,
    FlowValidationError
)
from app.services.flow_service import FlowService
from app.services.bot_service import BotService
from app.dependencies import get_current_user
from app.utils.logger import get_logger
from app.utils.exceptions import ValidationError, NotFoundError

logger = get_logger(__name__)

router = APIRouter(prefix="/bots/{bot_id}/flows", tags=["Flow Management"])


def flow_to_response(flow) -> FlowResponse:
    """Convert Flow model to FlowResponse schema"""
    return FlowResponse(
        flow_id=str(flow.id),
        flow_name=flow.name,
        bot_id=str(flow.bot_id),
        trigger_keywords=flow.trigger_keywords,
        flow_definition=flow.flow_definition,
        created_at=flow.created_at,
        updated_at=flow.updated_at
    )


@router.post("", response_model=FlowValidationResponse, status_code=status.HTTP_201_CREATED)
async def create_flow(
    bot_id: UUID = Path(..., description="Bot ID"),
    flow_data: FlowCreate = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new flow for a bot
    
    Args:
        bot_id: Bot ID that will own the flow
        flow_data: Flow definition
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Validation result with flow_id (UUID) and flow_name if successful
    
    Note:
        - Validates bot ownership
        - Validates flow structure before storage
        - System generates UUID for flow.id
        - Checks name uniqueness per bot (not globally)
        - Trigger keywords unique per bot
    """
    # Verify bot ownership
    bot_service = BotService(db)
    bot = await bot_service.get_bot(bot_id, current_user.user_id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot '{bot_id}' not found"
        )
    
    flow_service = FlowService(db)
    
    try:
        flow = await flow_service.create_flow(
            flow_data.model_dump(),
            bot_id
        )
        
        return FlowValidationResponse(
            status="success",
            flow_id=str(flow.id),
            flow_name=flow.name,
            bot_id=str(bot_id),
            message="Flow validated and stored successfully"
        )
    
    except ValidationError as e:
        logger.warning(
            f"Flow validation failed",
            flow_name=flow_data.name,
            errors=str(e.errors)
        )
        
        return FlowValidationResponse(
            status="error",
            errors=[
                FlowValidationError(
                    type="validation_error",
                    message=str(e)
                )
            ]
        )


@router.get("", response_model=FlowListResponse)
async def list_flows(
    bot_id: UUID = Path(..., description="Bot ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of flows to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of flows to return")
):
    """
    List bot's flows with pagination
    
    Args:
        bot_id: Bot ID to list flows for
        current_user: Current authenticated user
        db: Database session
        skip: Number of flows to skip (for pagination)
        limit: Maximum number of flows to return (1-100)
    
    Returns:
        Paginated list of flows with total count
        
    Example:
        GET /bots/{bot_id}/flows?skip=0&limit=20  # First page (20 items)
        GET /bots/{bot_id}/flows?skip=20&limit=20 # Second page
    """
    # Verify bot ownership
    bot_service = BotService(db)
    bot = await bot_service.get_bot(bot_id, current_user.user_id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot '{bot_id}' not found"
        )
    
    flow_service = FlowService(db)
    
    # Get paginated flows
    flows = await flow_service.list_flows(
        bot_id,
        skip=skip,
        limit=limit
    )
    
    # Get total count efficiently
    total = await flow_service.count_flows(bot_id)
    
    return FlowListResponse(
        flows=[flow_to_response(flow) for flow in flows],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{flow_id}", response_model=FlowResponse)
async def get_flow(
    bot_id: UUID = Path(..., description="Bot ID"),
    flow_id: UUID = Path(..., description="Flow UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific flow by UUID
    
    Args:
        bot_id: Bot ID
        flow_id: Flow UUID identifier
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Flow definition with both flow_id (UUID) and flow_name
    
    Raises:
        HTTPException: If bot or flow not found or not owned by user
    """
    # Verify bot ownership
    bot_service = BotService(db)
    bot = await bot_service.get_bot(bot_id, current_user.user_id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot '{bot_id}' not found"
        )
    
    flow_service = FlowService(db)
    flow = await flow_service.get_flow(flow_id, bot_id)
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow '{flow_id}' not found"
        )
    
    return flow_to_response(flow)


@router.put("/{flow_id}", response_model=FlowValidationResponse)
async def update_flow(
    bot_id: UUID = Path(..., description="Bot ID"),
    flow_id: UUID = Path(..., description="Flow UUID"),
    flow_data: FlowCreate = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update existing flow
    
    Args:
        bot_id: Bot ID
        flow_id: Flow identifier
        flow_data: Updated flow definition
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Validation result
    
    Note:
        - Validates bot ownership
        - Validates new flow structure
        - Active sessions continue with old version
        - New sessions use updated version
    
    Raises:
        HTTPException: If bot or flow not found or not owned by user
    """
    # Verify bot ownership
    bot_service = BotService(db)
    bot = await bot_service.get_bot(bot_id, current_user.user_id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot '{bot_id}' not found"
        )
    
    flow_service = FlowService(db)
    
    try:
        flow = await flow_service.update_flow(
            flow_id,
            bot_id,
            flow_data.model_dump()
        )
        
        return FlowValidationResponse(
            status="success",
            flow_id=str(flow.id),
            flow_name=flow.name,
            bot_id=str(bot_id),
            message="Flow updated successfully"
        )
    
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow '{flow_id}' not found"
        )
    
    except ValidationError as e:
        logger.warning(
            f"Flow update validation failed",
            flow_id=str(flow_id),
            errors=str(e.errors)
        )
        
        return FlowValidationResponse(
            status="error",
            errors=[
                FlowValidationError(
                    type="validation_error",
                    message=str(e)
                )
            ]
        )


@router.delete("/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flow(
    bot_id: UUID = Path(..., description="Bot ID"),
    flow_id: UUID = Path(..., description="Flow UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete flow
    
    Args:
        bot_id: Bot ID
        flow_id: Flow UUID identifier
        current_user: Current authenticated user
        db: Database session
    
    Note:
        - Validates bot ownership
        - Active sessions continue until completion
        - No new sessions can be created
    
    Raises:
        HTTPException: If bot or flow not found or not owned by user
    """
    # Verify bot ownership
    bot_service = BotService(db)
    bot = await bot_service.get_bot(bot_id, current_user.user_id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot '{bot_id}' not found"
        )
    
    flow_service = FlowService(db)
    deleted = await flow_service.delete_flow(flow_id, bot_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow '{flow_id}' not found"
        )
    
    return None