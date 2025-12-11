"""
Get next advisor utility
Migrated from Flask
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from app.apps.authentication.models import User
from app.apps.advisor.models import Role

logger = logging.getLogger(__name__)


async def _get_next_finva_advisor(
    client_id: Optional[int],
    session: AsyncSession
) -> Tuple[Optional[User], Optional[str]]:
    """
    Get the next available finva advisor based on rotation logic.
    Only considers users with the finva_agent role.
    """
    if client_id:
        # Get most recent application within 6 months
        # Note: Solicitud model needs to be imported when available
        stmt = text("""
            SELECT finva_user_id 
            FROM solicitudes 
            WHERE cliente_id = :client_id 
            AND created_at > NOW() - INTERVAL '180 days'
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        result = await session.execute(stmt, {"client_id": client_id})
        row = result.fetchone()
        
        if row and row[0]:
            finva_user_id = row[0]
            logger.info(f"Already has a finva advisor assigned in a solicitud: {finva_user_id}")
            stmt = select(User).where(User.id == finva_user_id)
            result = await session.execute(stmt)
            finva_user = result.scalar_one_or_none()
            if finva_user:
                return finva_user, None
    
    # Get finva agent role id
    stmt = select(Role).where(Role.name == "finva_agent")
    result = await session.execute(stmt)
    role = result.scalar_one_or_none()
    
    if not role:
        return None, "Finva agent role not found"
    
    finva_agent_role_id = role.id
    logger.info(f"Finva agent role ID: {finva_agent_role_id}")
    
    # Get finva agent query
    finva_query = select(User).where(
        User.is_active == True,
        User.role_id == finva_agent_role_id
    )
    
    return await _get_next_advisor_by_rotation_logic(finva_query, "finva", None, session)


async def _get_next_advisor_by_rotation_logic(
    query,
    advisor_type: str = "store",
    store_id: Optional[int] = None,
    session: AsyncSession = None
) -> Tuple[Optional[User], Optional[str]]:
    """
    Helper function to get the next available advisor based on rotation logic.
    
    Args:
        query: SQLAlchemy select statement for advisors
        advisor_type: String indicating type of advisor ("store" or "finva")
        store_id: Optional store ID to validate advisor relationship with store
        session: Async database session
    
    Returns:
        tuple: (advisor object, error message if any)
    """
    try:
        # Add is_active filter
        query = query.where(User.is_active == True)
        
        # Get all active advisors first to get their IDs
        result = await session.execute(query)
        all_advisors = result.scalars().all()
        advisor_ids = [adv.id for adv in all_advisors]
        
        if not advisor_ids:
            return None, f"No active {advisor_type} advisors available"
        
        # First, clear any existing selections to ensure fair rotation
        update_stmt = text("""
            UPDATE users 
            SET is_selected = FALSE 
            WHERE id = ANY(:advisor_ids) AND is_selected = TRUE
        """)
        await session.execute(update_stmt, {"advisor_ids": advisor_ids})
        await session.commit()
        
        # Now get active advisors ordered by last_selected_at (NULL first), then by ID
        query = query.order_by(
            User.last_selected_at.asc().nullsfirst(),
            User.id.asc()
        )
        result = await session.execute(query)
        advisors = result.scalars().all()
        
        # Validate store relationship if store_id is provided and advisor_type is "store"
        next_advisor = None
        if advisor_type == "store" and store_id is not None:
            logger.info(f"[ROTATION LOGIC] Validating advisors relationship with store {store_id}")
            for advisor in advisors:
                # Check if advisor has relationship with the store
                stmt = text("""
                    SELECT sucursal_id 
                    FROM user_sucursales 
                    WHERE user_id = :user_id AND sucursal_id = :store_id
                """)
                result = await session.execute(stmt, {"user_id": advisor.id, "store_id": store_id})
                row = result.fetchone()
                
                if row:
                    next_advisor = advisor
                    logger.info(
                        f"[ROTATION LOGIC] Found advisor {next_advisor.id} with verified relationship to store {store_id}"
                    )
                    break
            
            if not next_advisor:
                # Fallback to default advisor (user_id=117)
                stmt = select(User).where(User.id == 117)
                result = await session.execute(stmt)
                fallback_advisor = result.scalar_one_or_none()
                if fallback_advisor:
                    next_advisor = fallback_advisor
                    logger.info(
                        f"[ROTATION LOGIC] No advisor found with relationship to store {store_id}, using fallback advisor {next_advisor.id}"
                    )
                else:
                    return None, f"No active {advisor_type} advisors available with relationship to store {store_id} and fallback advisor (117) not found"
        else:
            # For finva advisors or when store_id is not provided, use first advisor
            if advisors:
                next_advisor = advisors[0]
            else:
                return None, f"No active {advisor_type} advisors available"
        
        # Update selection status
        logger.info(f"Updating {advisor_type} advisor selection status")
        update_stmt = text("""
            UPDATE users 
            SET is_selected = TRUE, last_selected_at = :now
            WHERE id = :advisor_id
        """)
        await session.execute(update_stmt, {
            "advisor_id": next_advisor.id,
            "now": datetime.now()
        })
        await session.commit()
        
        logger.info(f"Successfully updated selected {advisor_type} advisor to {next_advisor.id}")
        return next_advisor, None
        
    except Exception as e:
        logger.error(f"Error in get_next_{advisor_type}_user: {str(e)}", exc_info=True)
        await session.rollback()
        return None, str(e)


async def _get_next_advisor_by_holding_logic(
    holding: str,
    session: AsyncSession
) -> Tuple[Optional[User], Optional[str]]:
    """
    Helper function to get the next available advisor based on holding logic.
    For Sfera holding, gets all users with role_id=9 and applies rotation logic.
    
    Args:
        holding: String indicating the holding (e.g., "Sfera")
        session: Async database session
    
    Returns:
        tuple: (advisor object, error message if any)
    """
    try:
        logger.info(f"[HOLDING LOGIC] Getting next advisor for holding: {holding}")
        
        # Build query based on holding
        if holding == "Sfera":
            # Get all users with role_id=9 for Sfera holding
            holding_query = select(User).where(User.role_id == 9)
            advisor_type = "holding_sfera"
        else:
            return None, f"Unsupported holding: {holding}"
        
        # Use the existing rotation logic function
        return await _get_next_advisor_by_rotation_logic(holding_query, advisor_type, None, session)
        
    except Exception as e:
        logger.error(f"Error in _get_next_advisor_by_holding_logic: {str(e)}", exc_info=True)
        await session.rollback()
        return None, str(e)

