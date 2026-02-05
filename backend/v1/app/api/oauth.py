"""
Google OAuth2 Authentication API
Endpoints for Google Sign-In integration
"""

from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth, OAuthError
from authlib.integrations.base_client import OAuthError as BaseOAuthError
from datetime import timedelta

from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.security import create_access_token
from app.config import settings
from app.utils.logger import get_logger
from app.utils.constants import OAuthProvider

logger = get_logger(__name__)

router = APIRouter(prefix="/auth/google", tags=["OAuth"])

# Initialize OAuth client with validation
def get_oauth_client():
    """Initialize and return OAuth client"""
    if not settings.google.client_id or not settings.google.client_secret:
        raise ValueError("Google OAuth credentials not configured")

    oauth = OAuth()
    oauth.register(
        name='google',
        client_id=settings.google.client_id,
        client_secret=settings.google.client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email'
            # Removed 'prompt' to let Google handle consent intelligently
            # Google will show consent only on first login, then just account picker
        }
    )
    return oauth

# Create OAuth client instance
try:
    oauth = get_oauth_client()
    logger.info("OAuth client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OAuth client: {e}")
    oauth = None


@router.get("/login")
async def google_login(request: Request, redirect: str = None):
    """
    Initiate Google OAuth flow

    Redirects the user to Google's OAuth consent screen

    Args:
        request: FastAPI request object (required for OAuth)
        redirect: Optional redirect URL to return to after successful login

    Returns:
        Redirect response to Google OAuth
    """
    if oauth is None:
        logger.error("OAuth client not initialized - check Google OAuth credentials")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured. Please contact administrator."
        )

    try:
        # Log configuration for debugging
        logger.info(f"Initiating Google OAuth with redirect_uri: {settings.google.redirect_uri}")
        logger.info(f"Google Client ID configured: {settings.google.client_id[:20]}..." if settings.google.client_id else "No Client ID")

        redirect_uri = settings.google.redirect_uri

        # Store redirect URL in session to preserve it through OAuth flow
        if redirect:
            request.session['oauth_redirect'] = redirect

        return await oauth.google.authorize_redirect(
            request,
            redirect_uri
        )
    except Exception as e:
        logger.error(f"Failed to initiate Google OAuth: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google login: {str(e)}"
        )


@router.get("/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth callback

    Processes the OAuth callback from Google, exchanges authorization code
    for tokens, retrieves user info, and creates/updates user account.
    Auto-links accounts by email if user already exists.

    Args:
        request: FastAPI request object (contains auth code)
        db: Database session

    Returns:
        Redirect to frontend with JWT token

    Raises:
        HTTPException: If OAuth exchange fails or email not provided
    """
    if oauth is None:
        logger.error("OAuth client not initialized in callback")
        error_url = f"{settings.frontend_url.rstrip('/')}/login?error=oauth_not_configured"
        return RedirectResponse(url=error_url)

    try:
        # 1. Exchange authorization code for tokens
        token = await oauth.google.authorize_access_token(request)

        # 2. Extract user info from ID token
        user_info = token.get('userinfo')
        if not user_info:
            logger.error("No userinfo in OAuth token response")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from Google"
            )

        email = user_info.get('email')
        google_user_id = user_info.get('sub')  # Google's unique user ID

        if not email:
            logger.error("Email not provided by Google")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )

        if not google_user_id:
            logger.error("Google user ID (sub) not provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID not provided by Google"
            )

        # 3. Find or create user (auto-link by email)
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(email)

        if user:
            # Check if user account is active
            if not user.is_active:
                logger.warning(f"OAuth login attempt by inactive user", email=email, user_id=str(user.user_id))
                error_url = f"{settings.frontend_url.rstrip('/')}/login?error=account_inactive"
                return RedirectResponse(url=error_url)

            # User exists - update OAuth fields if not set
            if not user.oauth_provider:
                logger.info(f"Linking existing user to Google OAuth", email=email)
                user.oauth_provider = OAuthProvider.GOOGLE.value
                user.oauth_id = google_user_id
                await db.commit()
                await db.refresh(user)
            else:
                logger.info(f"User logged in via Google OAuth", email=email)
        else:
            # Create new OAuth user
            logger.info(f"Creating new user via Google OAuth", email=email)
            user = User(
                email=email,
                password_hash=None,  # OAuth users don't have passwords
                oauth_provider=OAuthProvider.GOOGLE.value,
                oauth_id=google_user_id,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            # Create example bot with flows for new user
            from app.services.bot_service import BotService
            bot_service = BotService(db)
            await bot_service.create_example_bot_for_user(user.user_id)

        # 4. Generate JWT token (same as password login)
        access_token = create_access_token(
            data={"sub": str(user.user_id)},
            expires_delta=timedelta(minutes=settings.security.access_token_expire_minutes)
        )

        # 5. Extract redirect URL from session if present
        redirect_url = request.session.pop('oauth_redirect', None)

        # 6. Redirect to frontend with token in URL query parameter
        frontend_base_url = settings.frontend_url.rstrip('/')
        frontend_callback_url = f"{frontend_base_url}/auth/callback?token={access_token}"

        # Add redirect parameter if present
        if redirect_url:
            from urllib.parse import quote
            frontend_callback_url += f"&redirect={quote(redirect_url)}"

        return RedirectResponse(url=frontend_callback_url)

    except OAuthError as e:
        logger.error(f"OAuth error during callback: {e.error} - {e.description}")
        # Redirect to login with error
        frontend_base_url = settings.frontend_url.rstrip('/')
        error_url = f"{frontend_base_url}/login?error=oauth_failed"
        return RedirectResponse(url=error_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {e}", exc_info=True)
        frontend_base_url = settings.frontend_url.rstrip('/')
        error_url = f"{frontend_base_url}/login?error=oauth_failed"
        return RedirectResponse(url=error_url)
