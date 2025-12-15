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
if settings.debug:
    engine = create_async_engine(
        settings.database.url,
        echo=settings.database.echo,
        poolclass=NullPool,
        pool_pre_ping=True
    )
else:
    engine = create_async_engine(
        settings.database.url,
        echo=settings.database.echo,
        pool_pre_ping=True,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow
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
    FastAPI dependency for database session

    IMPORTANT: This function does NOT auto-commit. Services must explicitly
    call `await session.commit()` when they're ready to persist changes.
    This provides explicit transaction control and prevents double-commit issues.

    Transaction Management Pattern:
        @app.post("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Perform database operations
            entity = MyModel(...)
            db.add(entity)

            # Explicitly commit when ready
            await db.commit()

            # Refresh if you need updated fields (e.g., server defaults)
            await db.refresh(entity)

            return entity

    Error Handling:
        - On exception: automatically rolls back the transaction
        - On success: NO auto-commit (service controls when to commit)

    Yields:
        AsyncSession: Database session without auto-commit
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # NO auto-commit - services must call session.commit() explicitly


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