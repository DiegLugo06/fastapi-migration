"""
Helper functions for solicitud evaluation
Async versions migrated from Flask backend
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.apps.loan.models import Solicitud
from app.apps.client.models import Report
import logging

logger = logging.getLogger(__name__)


async def fetch_solicitud(solicitud_id: int, session: AsyncSession) -> Optional[Solicitud]:
    """Fetch solicitud by ID (async version)."""
    try:
        stmt = select(Solicitud).where(Solicitud.id == solicitud_id)
        result = await session.execute(stmt)
        solicitud = result.scalar_one_or_none()
        if not solicitud:
            logger.error(f"Solicitud not found for id: {solicitud_id}")
        return solicitud
    except Exception as e:
        logger.error(f"Error fetching solicitud {solicitud_id}: {str(e)}", exc_info=True)
        return None


async def fetch_reports_by_client_id(client_id: int, session: AsyncSession) -> List[Report]:
    """Fetch reports for a given client ID (async version)."""
    try:
        stmt = select(Report).where(Report.cliente_id == client_id)
        result = await session.execute(stmt)
        reports = result.scalars().all()
        if not reports:
            logger.error(f'No reports found for client: {client_id}')
        return reports
    except Exception as e:
        logger.error(f"Error fetching reports for client {client_id}: {str(e)}", exc_info=True)
        return []


def calculate_amount_to_finance(solicitud: Solicitud) -> float:
    """Calculate the amount to finance based on solicitud data."""
    if (
        solicitud.invoice_motorcycle_value is None
        or solicitud.percentage_down_payment is None
    ):
        return 0.0

    try:
        invoice_value = float(solicitud.invoice_motorcycle_value) if solicitud.invoice_motorcycle_value else 0.0
        percentage_down = float(solicitud.percentage_down_payment) if solicitud.percentage_down_payment else 0.0
        return invoice_value * (1 - percentage_down)
    except (ValueError, TypeError) as e:
        logger.error(f"Error calculating amount to finance: {str(e)}")
        return 0.0


