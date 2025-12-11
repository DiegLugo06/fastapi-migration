"""
Fetch store utility
Migrated from Flask
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.apps.advisor.models import Sucursal

logger = logging.getLogger(__name__)


async def _fetch_sucursal(user_id: int, session: AsyncSession) -> Sucursal:
    """Fetch sucursal ID for a given user and log errors if not found."""
    # Query user_sucursales association table
    stmt = text("""
        SELECT sucursal_id 
        FROM user_sucursales 
        WHERE user_id = :user_id 
        LIMIT 1
    """)
    result = await session.execute(stmt, {"user_id": user_id})
    row = result.fetchone()
    
    if not row:
        logger.error(f"No sucursal_id found for user_id: {user_id}")
        return None
    
    sucursal_id = row[0]
    
    # Get sucursal
    stmt = select(Sucursal).where(Sucursal.id == sucursal_id)
    result = await session.execute(stmt)
    sucursal = result.scalar_one_or_none()
    
    if not sucursal:
        logger.error(f"No sucursal found for sucursal_id: {sucursal_id}")
        return None
    
    return sucursal

