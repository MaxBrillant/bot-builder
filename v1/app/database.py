"""
Database Connection and Session Management
Async SQLAlchemy setup with PostgreSQL
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create async engine
# Note: NullPool is incompatible with pool_size/max_overflow
if settings.DEBUG:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
        pool_pre_ping=True
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for ORM models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session
    
    Yields:
        AsyncSession: Database session
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            # Only commit if no exception occurred
            await session.commit()
        finally:
            await session.close()


async def init_db():
    """
    Initialize database connection
    
    Note: Tables are created by Alembic migrations, not by SQLAlchemy create_all()
    """
    # Just verify connection - tables created by Alembic
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database initialized")


async def close_db():
    """
    Close database connections
    Called on application shutdown
    """
    await engine.dispose()
    logger.info("Database connections closed")


async def check_database() -> bool:
    """
    Check database connectivity
    
    Returns:
        True if database is accessible, False otherwise
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False