"""
Fetch user utility
Migrated from Flask
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.apps.authentication.models import User

logger = logging.getLogger(__name__)


async def _fetch_user(user_id: int, session: AsyncSession) -> User:
    """Fetch user by ID and log errors if not found."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        logger.error(f"User not found for user_id: {user_id}")
    return user

