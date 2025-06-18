from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from sqlalchemy import MetaData
from typing import AsyncGenerator
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Database metadata with naming convention for consistent constraint names
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

# Convert PostgreSQL URL to asyncpg format if needed
def get_asyncpg_url(url: str) -> str:
    """Convert postgresql:// URL to postgresql+asyncpg:// format"""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url

# Create async engine
engine = create_async_engine(
    get_asyncpg_url(settings.database_url),
    poolclass=NullPool,  # Use NullPool for serverless/Lambda compatibility
    echo=False,  # Disable verbose SQL logging
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections every 5 minutes
    connect_args={
        "server_settings": {
            "application_name": f"{settings.project_name}-{settings.environment}",
        }
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Usage in FastAPI:
        @app.get("/users/")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database by creating all tables.
    This should be called on application startup.
    """
    try:
        async with engine.begin() as conn:
            # Import all models here to ensure they are registered with Base
            from app.models import user, email_otp  # noqa: F401
            
            logger.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def close_db() -> None:
    """
    Close database connections.
    This should be called on application shutdown.
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# Database health check
async def check_db_health() -> bool:
    """
    Check if database is accessible and healthy.
    Returns True if healthy, False otherwise.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Simple query to check connection
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# Utility functions for database operations
class DatabaseManager:
    """Database management utilities"""
    
    @staticmethod
    async def create_tables():
        """Create all database tables"""
        await init_db()
    
    @staticmethod
    async def health_check() -> dict:
        """Return detailed health check information"""
        try:
            is_healthy = await check_db_health()
            return {
                "database": {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "hidden",
                    "engine": str(engine.url).split("@")[-1] if "@" in str(engine.url) else "hidden"
                }
            }
        except Exception as e:
            return {
                "database": {
                    "status": "error",
                    "error": str(e)
                }
            }
    
    @staticmethod
    async def get_connection_info() -> dict:
        """Get database connection information (non-sensitive)"""
        return {
            "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else "N/A",
            "pool_checked_in": engine.pool.checkedin() if hasattr(engine.pool, 'checkedin') else "N/A",
            "pool_checked_out": engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else "N/A",
            "echo": engine.echo,
            "dialect": engine.dialect.name,
        }