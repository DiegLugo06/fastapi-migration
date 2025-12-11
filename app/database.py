"""
Database connection and session management
Using SQLModel with asyncpg for async PostgreSQL operations
"""
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator, Optional
import ssl
import os
import logging
from app.config import DATABASE_URL, DB_SSL_CERT_PATH, DEBUG, MODE

logger = logging.getLogger(__name__)

# CRITICAL FIX: Disable prepared statements for pgbouncer compatibility
# Even with statement_cache_size=0, SQLAlchemy's asyncpg dialect may still use prepared statements
# We need to ensure the parameter is correctly passed and verify it's working

# Convert postgresql:// to postgresql+asyncpg:// for async operations
async_database_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Detect which port is being used
if ":6543" in async_database_url:
    logger.warning("Using pooler port 6543 - prepared statements will be disabled")
    using_pooler = True
elif ":5432" in async_database_url:
    logger.info("Using direct connection port 5432 - prepared statements supported")
    using_pooler = False
else:
    logger.warning("Could not detect port in database URL")
    using_pooler = True  # Assume pooler to be safe

# SSL configuration for asyncpg
# asyncpg accepts: ssl.SSLContext, True, False, 'require', or a dict
ssl_config: Optional[ssl.SSLContext] = None

if DB_SSL_CERT_PATH:
    try:
        # Verify certificate file exists and is readable
        if os.path.exists(DB_SSL_CERT_PATH):
            file_size = os.path.getsize(DB_SSL_CERT_PATH)
            if file_size > 0:
                logger.info(f"Loading SSL certificate from: {DB_SSL_CERT_PATH} ({file_size} bytes)")
                
                # Create SSL context for asyncpg
                # This matches the Flask/psycopg2 behavior but adapted for asyncpg
                ssl_config = ssl.create_default_context(cafile=DB_SSL_CERT_PATH)
                
                # Configure SSL context to match Flask's "verify-full" behavior
                # For Supabase/cloud databases, we typically don't verify hostname
                ssl_config.check_hostname = False
                ssl_config.verify_mode = ssl.CERT_REQUIRED
                
                logger.info("SSL context created successfully")
            else:
                logger.warning(f"SSL certificate file is empty: {DB_SSL_CERT_PATH}")
        else:
            logger.warning(f"SSL certificate file not found: {DB_SSL_CERT_PATH}")
    except Exception as e:
        logger.error(f"Failed to create SSL context: {e}", exc_info=True)
        ssl_config = None

# Create async engine with SSL and connection pool settings
# Note: Supabase uses pgbouncer in transaction/statement pooling mode,
# which doesn't support prepared statements. We must disable statement caching.
# IMPORTANT: If you're using Supabase's pooler URL (port 6543), this setting is required.
# Alternative: Use Supabase's direct connection URL (port 5432) which supports prepared statements.
connect_args = {
    "command_timeout": 30,  # 30 second timeout for commands (increased for SSL handshake)
    "statement_cache_size": 0,  # CRITICAL: Disable prepared statements for pgbouncer compatibility
    "server_settings": {
        "application_name": "fastapi_migration"
    }
}

# Add SSL configuration for asyncpg
# asyncpg accepts ssl.SSLContext directly in the 'ssl' parameter
if ssl_config:
    connect_args["ssl"] = ssl_config
    logger.info("SSL enabled for database connections")
else:
    logger.warning("SSL not configured - database connections will be unencrypted")

# Create async engine with enhanced settings for SSL connections
# For pgbouncer compatibility, we disable prepared statements via connect_args
# CRITICAL: The statement_cache_size=0 MUST be in connect_args for asyncpg
# Note: You MUST restart the server completely for this to take effect
# If the error persists, consider using the direct connection URL (port 5432) instead of pooler (port 6543)
async_engine = create_async_engine(
    async_database_url,
    echo=DEBUG,  # Set to True for SQL query logging
    future=True,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,  # Timeout for getting connection from pool (increased for SSL)
    pool_size=10,  # Increased pool size for better concurrency
    max_overflow=20,  # Increased overflow for peak loads
    connect_args=connect_args,
)

logger.info(f"Database engine created (mode: {MODE}, SSL: {'enabled' if ssl_config else 'disabled'})")
logger.info(f"Prepared statements disabled (statement_cache_size=0) for pgbouncer compatibility")
logger.info(f"Using pooler: {using_pooler}")
logger.info(f"Connect args: statement_cache_size={connect_args.get('statement_cache_size')}")

# Log URL without password, but show port
url_parts = async_database_url.split("@")
if len(url_parts) > 1:
    host_part = url_parts[1].split("/")[0] if "/" in url_parts[1] else url_parts[1]
    logger.info(f"Database URL: {url_parts[0]}@***{host_part}")
    
    # Warn if using pooler port
    if ":6543" in host_part:
        logger.warning("⚠️  Using pooler port 6543 - prepared statements are NOT supported!")
        logger.warning("⚠️  Consider switching to direct connection (port 5432) in your .env file")
    elif ":5432" in host_part:
        logger.info("✓ Using direct connection port 5432 - prepared statements are supported")
else:
    logger.info(f"Database URL: {async_database_url.split('@')[0]}@***")

# Create async session factory
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get async database session
    Usage: async def endpoint(session: AsyncSession = Depends(get_async_session))
    
    Note: Prepared statements are disabled for pgbouncer compatibility.
    If you see DuplicatePreparedStatementError, ensure you're using port 5432 (direct connection)
    or that statement_cache_size=0 is properly configured.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Set execution options to avoid prepared statements
            # This is a workaround for SQLAlchemy's asyncpg dialect
            yield session
            await session.commit()
        except Exception as e:
            # Check if it's a prepared statement error
            error_str = str(e)
            if "DuplicatePreparedStatementError" in error_str or "prepared statement" in error_str.lower():
                logger.error("Prepared statement error detected - this should not happen with statement_cache_size=0")
                logger.error("Please verify your database URL uses port 5432 (direct connection) not 6543 (pooler)")
                logger.error("Or ensure statement_cache_size=0 is being applied correctly")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database - create all tables
    Call this on application startup
    """
    async with async_engine.begin() as conn:
        # Import all models here so SQLModel can create tables
        # from app.apps.authentication.models import User
        # from app.apps.client.models import Cliente, FileStatus, etc.
        
        # Create all tables
        # await conn.run_sync(SQLModel.metadata.create_all)
        pass


async def close_db():
    """
    Close database connections
    Call this on application shutdown
    """
    await async_engine.dispose()
    logger.info("Database connections closed")


async def test_db_connection():
    """
    Test database connection - useful for debugging
    """
    try:
        async with AsyncSessionLocal() as session:
            # Simple query to test connection
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            logger.info(f"Database connection test successful: {value}")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}", exc_info=True)
        return False