"""
Shared pytest fixtures and configuration
"""
import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.sqlite import base as sqlite_base

from app.main import app
from app.database import get_async_session
from app.apps.authentication.models import User
from app.apps.authentication.dependencies import get_current_user


# Patch SQLite dialect to handle JSONB (PostgreSQL-specific type)
# SQLite doesn't support JSONB, so we map it to JSON
def visit_jsonb(self, type_, **kw):
    """Map JSONB to JSON for SQLite compatibility"""
    return self.visit_JSON(type_, **kw)

# Monkey patch the SQLite type compiler to handle JSONB
sqlite_base.SQLiteTypeCompiler.visit_JSONB = visit_jsonb


# Create in-memory SQLite database for testing
# Note: aiosqlite must be installed for async SQLite support
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="function")
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session for each test.
    Cleans up database between tests to avoid UNIQUE constraint violations.
    """
    async with test_engine.begin() as conn:
        # Import all models to create tables
        from app.apps.authentication.models import User
        from app.apps.product.models import Motorcycles, MotorcycleBrand, Discounts
        from app.apps.quote.models import Banco, FinancingOption
        from app.apps.client.models import Cliente, FileStatus, IncomeProofDocument, Report
        from app.apps.advisor.models import Sucursal, Role
        from app.apps.loan.models import Solicitud, Application
        # Import association tables so they're created
        from app.apps.common.association_tables import user_sucursales, clientes_users
        from sqlmodel import SQLModel
        
        # Drop all tables first to ensure clean state
        await conn.run_sync(SQLModel.metadata.drop_all)
        # Create all tables (including association tables)
        await conn.run_sync(SQLModel.metadata.create_all)
    
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            # Clean up after test
            async with test_engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture(scope="function")
def client(test_session: AsyncSession) -> TestClient:
    """
    Create a test client with overridden database dependency.
    """
    async def override_get_async_session():
        yield test_session
    
    app.dependency_overrides[get_async_session] = override_get_async_session
    
    test_client = TestClient(app)
    yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """
    Create a mock user for authentication.
    """
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.uuid = "123e4567-e89b-12d3-a456-426614174000"
    user.role_id = 1
    user.is_active = True
    user.name = "Test"
    user.first_last_name = "User"
    return user


@pytest.fixture
def authenticated_client(client: TestClient, mock_user):
    """
    Create a test client with authentication mocked.
    """
    def override_get_current_user():
        return mock_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    yield client
    
    # Cleanup
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


@pytest.fixture
def api_key_client(client: TestClient):
    """
    Create a test client with API key authentication.
    """
    # API key authentication is handled in get_current_user
    # We can override it to return a minimal user
    def override_get_current_user():
        user = MagicMock(spec=User)
        user.id = 0
        user.email = "api_key_user@example.com"
        user.role_id = 0
        user.is_active = True
        return user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    yield client
    
    # Cleanup
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


# Configure pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

