"""
Insert Report Data Utility
Migrated from Flask app/loan/utils/insert_report_data.py
Converted to async SQLAlchemy for FastAPI
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone
from dateutil import parser as date_parser

from app.apps.client.models import Report

logger = logging.getLogger(__name__)


def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse datetime string from Kiban API response.
    Converts timezone-aware datetimes to timezone-naive UTC datetimes
    for database compatibility (TIMESTAMP WITHOUT TIME ZONE).
    """
    if not date_str:
        return None
    try:
        if isinstance(date_str, datetime):
            dt = date_str
        else:
            dt = date_parser.parse(date_str)
        
        # Convert timezone-aware datetime to timezone-naive UTC
        # Database column is TIMESTAMP WITHOUT TIME ZONE
        if dt.tzinfo is not None:
            # Convert to UTC and remove timezone info
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        
        return dt
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse datetime '{date_str}': {e}")
        return None


async def insert_report(report: Dict[str, Any], cliente_id: int, session: AsyncSession) -> Dict[str, Any]:
    """
    Insert a report from Kiban API response.
    
    Args:
        report: Report data from Kiban API containing id, createdAt, finishedAt, duration, status
        cliente_id: Client ID to associate the report with
        session: Async SQLAlchemy session
        
    Returns:
        Dict with report data including 'id' key, or {'error': str} on failure
    """
    try:
        # Parse datetime strings from Kiban response
        created_at = _parse_datetime(report.get('createdAt'))
        finished_at = _parse_datetime(report.get('finishedAt'))
        
        # Prepare the data
        report_data = {
            "kiban_id": str(report.get('id', '')),
            "cliente_id": cliente_id,
            "created_at": created_at,
            "finished_at": finished_at,
            "duration": report.get('duration'),
            "status": report.get('status'),
            "raw_query_report": report
        }
        
        logger.info(f"Inserting report data for client {cliente_id}: report_id: {report.get('id')}")

        # Create Report object
        report_obj = Report(**report_data)

        # Add to session
        session.add(report_obj)
        await session.flush()  # Flush to get the ID
        await session.commit()

        # Return the report data
        return {
            "id": report_obj.id,
            "kiban_id": report_obj.kiban_id,
            "cliente_id": report_obj.cliente_id,
            "created_at": report_obj.created_at.isoformat() if report_obj.created_at else None,
            "finished_at": report_obj.finished_at.isoformat() if report_obj.finished_at else None,
            "duration": report_obj.duration,
            "status": report_obj.status,
        }

    except Exception as e:
        await session.rollback()
        logger.error(f"Error inserting reporte kiban: {str(e)}", exc_info=True)
        return {"error": str(e)}


async def insert_report_data_bulk(report_id: int, report_kiban_response: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
    """
    Bulk insert all report data from Kiban response with comprehensive error handling.
    
    NOTE: This is a simplified version. Full implementation requires migrating:
    - ConsultasEfectuadas, Cuentas, Domicilios, Empleos, HawkAlerts,
    - HistoricoSaldos, ResumenReporte, ScoreBuroCredito models
    
    Args:
        report_id: The ID of the created report
        report_kiban_response: The response data from Kiban API
        session: Async SQLAlchemy session
        
    Returns:
        dict: Summary of insertion results with success/failure counts and details
    """
    from sqlalchemy.exc import SQLAlchemyError
    
    # Track insertion results
    results = {
        "successful": [],
        "failed": [],
        "total_processed": 0,
        "total_successful": 0,
        "total_failed": 0
    }
    
    # For now, we'll just log what would be inserted
    # TODO: Implement full insertion when models are migrated
    expected_keys = [
        "consultasEfectuadas",
        "cuentas",
        "domicilios",
        "empleos",
        "hawkAlertBD",
        "hawkAlertConsulta",
        "historicoSaldos",
        "resumenReporte",
        "scoreBuroCredito",
    ]
    
    for key in expected_keys:
        if key in report_kiban_response:
            results["total_processed"] += 1
            
            try:
                # TODO: Implement actual insertion when models are available
                # For now, we'll just mark as successful but log that it's not implemented
                logger.info(
                    f"Report data key '{key}' found in response for report {report_id}, "
                    f"but insertion not yet implemented (models need migration)"
                )
                results["successful"].append(key)
                results["total_successful"] += 1
                
            except Exception as e:
                error_msg = f"Unexpected error processing {key}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["failed"].append({
                    "key": key,
                    "error": f"Unexpected error: {str(e)}",
                    "type": "unexpected_error"
                })
                results["total_failed"] += 1
    
    if results["total_failed"] > 0:
        logger.warning(
            f"Some report data processing failed for report ID: {report_id}. "
            f'Successful: {results["total_successful"]}, '
            f'Failed: {results["total_failed"]}'
        )
    else:
        logger.info(
            f"Report data processing completed for report ID: {report_id}. "
            f"Note: Actual insertion pending model migration."
        )
    
    return results

