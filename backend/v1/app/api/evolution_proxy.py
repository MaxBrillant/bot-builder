"""
Evolution API Mirror Proxy
Provides transparent proxy to Evolution API with automatic credential injection
"""

from fastapi import APIRouter, HTTPException, Header, Request, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import httpx

from app.database import get_db
from app.repositories.bot_repository import BotRepository
from app.core.engine import get_http_client
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/integrations/whatsapp", tags=["WhatsApp Integration"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def evolution_mirror_proxy(
    path: str,
    request: Request,
    bot_id: UUID = Header(..., alias="X-Bot-ID"),
    db: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client)
):
    """
    WhatsApp messaging proxy with automatic credential injection.

    This endpoint provides WhatsApp messaging capabilities for flows, automatically:
    - Injecting WhatsApp credentials from environment
    - Injecting instance configuration from bot setup
    - Validating bot ownership and configuration

    Usage in flows:
    1. Follow Evolution API documentation for endpoint paths and request bodies
    2. Use base URL: https://your-domain/api/integrations/whatsapp/...
    3. Remove {instanceName} from paths (injected automatically)
    4. Add header: X-Bot-ID with your bot ID
    5. Authentication handled automatically

    Example:
        Evolution API docs: POST /message/sendText/{instanceName}
        Flow usage:         POST /api/integrations/whatsapp/message/sendText

    Args:
        path: Evolution API endpoint path (e.g., "message/sendText", "instance/connectionState")
        request: FastAPI request object (contains body, query params, etc.)
        bot_id: Bot ID from X-Bot-ID header
        db: Database session
        http_client: Shared HTTP client

    Returns:
        JSON response from Evolution API

    Raises:
        HTTPException 400: Bot not found or has no Evolution instance configured
        HTTPException 4xx/5xx: Evolution API errors (status code passed through)
    """
    # Get bot and validate WhatsApp integration
    bot_repo = BotRepository(db)
    bot = await bot_repo.get_by_id(bot_id)

    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot {bot_id} not found"
        )

    # Get WhatsApp integration
    whatsapp_integration = bot.get_integration(IntegrationPlatform.WHATSAPP)

    if not whatsapp_integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bot {bot_id} has no WhatsApp integration configured"
        )

    # Get instance name from integration config
    instance_name = whatsapp_integration.config.get("instance_name")

    if not instance_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bot {bot_id} WhatsApp integration has no instance_name configured"
        )

    # Block dangerous instance and proxy operations
    # These operations should be done through Bot Builder UI, not flows
    # Allow: message/* and settings/* operations (safe operations)
    blocked_prefixes = [
        "instance/",    # All instance management operations (create, delete, restart, logout, connect)
        "proxy/"        # All proxy configuration operations
    ]

    if any(path.startswith(blocked) for blocked in blocked_prefixes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation '{path}' is not allowed from flows. Instance and proxy operations must be done through Bot Builder UI."
        )

    # Always append instance name to path
    # Evolution API expects paths like: /message/sendText/{instanceName}
    evolved_path = f"{path}/{instance_name}"

    # Build full Evolution API URL
    evolution_url = f"{settings.evolution_api.url}/{evolved_path}"

    # Get request body if present
    body = None
    if await request.body():
        try:
            body = await request.json()
        except Exception:
            # Non-JSON body, pass as-is
            pass

    # Prepare headers with injected API key
    headers = {"apikey": settings.evolution_api.api_key}

    # Forward request to Evolution API
    try:
        logger.info(
            f"Proxying Evolution API request",
            bot_id=str(bot_id),
            instance=instance_name,
            method=request.method,
            path=evolved_path
        )

        response = await http_client.request(
            method=request.method,
            url=evolution_url,
            headers=headers,
            json=body,
            params=dict(request.query_params),
            timeout=settings.http_client.timeout
        )
        response.raise_for_status()

        # Return JSON response
        return response.json()

    except httpx.HTTPStatusError as e:
        # Pass through Evolution API errors with original status code
        logger.warning(
            f"Evolution API error",
            bot_id=str(bot_id),
            status_code=e.response.status_code,
            error=e.response.text
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Evolution API error: {e.response.text}"
        )
    except httpx.TimeoutException:
        logger.error(
            f"Evolution API timeout",
            bot_id=str(bot_id),
            url=evolution_url
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Evolution API request timed out"
        )
    except httpx.RequestError as e:
        logger.error(
            f"Evolution API request error",
            bot_id=str(bot_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Evolution API: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected proxy error",
            bot_id=str(bot_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal proxy error: {str(e)}"
        )
