"""
Bot Builder - Main Application
FastAPI application entry point
"""

import asyncio
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db, close_db, check_database, AsyncSessionLocal
from app.core.redis_manager import redis_manager
from app.core.engine import init_http_client, close_http_client
from app.api import (
    auth_router,
    bots_router,
    flows_router,
    webhooks_router,
    oauth_router,
    whatsapp_router,
    evolution_webhooks_router
)
from app.api.middleware import register_exception_handlers
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Background task handle
cleanup_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    
    Startup:
    - Initialize database connection
    - Initialize Redis (if enabled)
    - Log application start
    
    Shutdown:
    - Close database connections
    - Close Redis connections
    - Cleanup resources
    """
    # Startup
    logger.info("Starting Bot Builder application", version=settings.app_version)

    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

    # Initialize Redis
    if settings.redis.enabled:
        try:
            await redis_manager.connect()
            logger.info("Redis initialized")
        except Exception as e:
            logger.warning(f"Redis initialization failed: {str(e)} - continuing without Redis")
    
    # Initialize shared HTTP client
    try:
        await init_http_client()
        logger.info("HTTP client initialized")
    except Exception as e:
        logger.error(f"HTTP client initialization failed: {str(e)}")
        raise
    
    # Start background cleanup task using asyncio
    async def cleanup_loop():
        """Background loop to cleanup expired sessions every 10 minutes"""
        consecutive_failures = 0
        max_failures = 5
        
        while True:
            try:
                await asyncio.sleep(600)  # 10 minutes
                async with AsyncSessionLocal() as db:
                    from app.core.session_manager import SessionManager
                    session_mgr = SessionManager(db)
                    count = await session_mgr.cleanup_expired_sessions()
                    if count > 0:
                        logger.info(f"Background cleanup: {count} expired sessions cleaned")
                
                # Reset failure counter on success
                consecutive_failures = 0
                
            except asyncio.CancelledError:
                logger.info("Background cleanup task cancelled")
                break
            except Exception as e:
                consecutive_failures += 1
                logger.error(
                    f"Session cleanup task failed (attempt {consecutive_failures}/{max_failures}): {str(e)}"
                )
                
                # Stop task after too many consecutive failures
                if consecutive_failures >= max_failures:
                    logger.critical(
                        f"Background cleanup task stopping after {max_failures} consecutive failures"
                    )
                    break
    
    global cleanup_task
    cleanup_task = asyncio.create_task(cleanup_loop())
    logger.info("Background cleanup task started (runs every 10 minutes)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Bot Builder application")
    
    # Stop background cleanup task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info("Background cleanup task stopped")
    
    # Close HTTP client
    await close_http_client()
    logger.info("HTTP client closed")

    # Close Redis
    if settings.redis.enabled:
        await redis_manager.disconnect()
        logger.info("Redis connection closed")

    # Close database
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Conversational bot framework with multi-tenant support",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)


# Session middleware - Required for OAuth flows
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.security.secret_key,
    session_cookie="session",
    max_age=1800,  # 30 minutes
    same_site="lax",
    https_only=settings.is_production
)


# CORS - Restrictive configuration for security (10 MB request limit handled by Uvicorn)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Specific methods only
    allow_headers=["Authorization", "Content-Type", "X-Webhook-Secret"],  # Specific headers only
    max_age=3600,  # Cache preflight requests for 1 hour
)


# Exception handlers - Register structured exception handling from middleware
register_exception_handlers(app)


# Catch-all for unexpected exceptions (not BotBuilderException subclasses)
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions not caught by BotBuilderException handlers"""
    logger.error(
        f"Unexpected error: {str(exc)}",
        path=request.url.path,
        exc_info=True
    )

    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"}
    )


# Register routers
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(bots_router)
app.include_router(flows_router)  # Nested under /bots/{bot_id}/flows
app.include_router(webhooks_router)
app.include_router(whatsapp_router)  # WhatsApp/Evolution API integration
app.include_router(evolution_webhooks_router)  # Evolution API webhook receiver


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Application health status
    """
    db_healthy = await check_database()
    redis_health = await redis_manager.health_check() if settings.redis.enabled else {"status": "disabled"}

    overall_healthy = db_healthy and (not settings.redis.enabled or redis_health["status"] == "healthy")

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "connected" if db_healthy else "disconnected",
        "redis": redis_health
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint

    Returns:
        API information
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else None,
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )