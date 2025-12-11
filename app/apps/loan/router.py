"""
Loan router
Migrated from Flask app/loan/routes.py
Basic structure with essential endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import logging

from app.database import get_async_session
from app.apps.authentication.dependencies import get_current_user
from app.apps.loan.models import Solicitud, Application, SolicitudStatusHistory, ContactAttempt
from app.apps.loan.schemas import (
    SolicitudCreate,
    SolicitudUpdate,
    SolicitudResponse,
    SendNIPRequest,
    ValidateNIPRequest,
    GetBCKibanRequest,
    ApplicationResponse,
    SolicitudStatusHistoryResponse,
    ContactAttemptResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/send_nip_kiban", status_code=status.HTTP_200_OK)
async def send_nip_kiban(
    request: SendNIPRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to send NIP to phone number by Kiban Service.
    TODO: Implement kiban_api.send_nip_kiban
    """
    logger.info("Sending NIP to Kiban service")
    try:
        # TODO: Implement kiban_api integration
        # response = kiban_api.send_nip_kiban(data)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Kiban NIP sending not yet implemented - requires kiban_api migration"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_nip_kiban: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/validate_nip_kiban", status_code=status.HTTP_200_OK)
async def validate_nip_kiban(
    request: ValidateNIPRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to validate NIP of phone number by Kiban Service.
    TODO: Implement kiban_api.verify_nip_kiban
    """
    logger.info(f"Validating NIP with Kiban service")
    try:
        # TODO: Implement kiban_api integration
        # response = kiban_api.verify_nip_kiban(data)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Kiban NIP validation not yet implemented - requires kiban_api migration"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in validate_nip_kiban: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/get_bc_kiban/{cliente_id}", status_code=status.HTTP_200_OK)
async def get_bc_kiban(
    cliente_id: int,
    request: GetBCKibanRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to retrieve and insert BC report from Kiban Service.
    TODO: Implement kiban_api.query_bc_pf_by_kiban and report insertion
    """
    logger.info(f"Retrieving BC report for client {cliente_id} from Kiban service")
    try:
        # TODO: Implement kiban_api integration and report insertion
        # report_kiban = kiban_api.query_bc_pf_by_kiban(data)
        # insert_report(report_kiban, cliente_id)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="BC Kiban retrieval not yet implemented - requires kiban_api and report insertion migration"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_bc_kiban: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/solicitud", response_model=SolicitudResponse, status_code=status.HTTP_201_CREATED)
async def create_solicitud(
    request: SolicitudCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to create a new solicitud (loan application).
    """
    try:
        solicitud = Solicitud(**request.dict())
        session.add(solicitud)
        await session.flush()
        
        # Create initial status history
        status_history = SolicitudStatusHistory(
            solicitud_id=solicitud.id,
            status=solicitud.status or "created",
            notes="Solicitud created"
        )
        session.add(status_history)
        
        await session.commit()
        
        logger.info(f"Solicitud created successfully, ID: {solicitud.id}")
        return SolicitudResponse.from_orm(solicitud)
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating solicitud: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the solicitud: {str(e)}"
        )


@router.get("/solicitud/{solicitud_id}", response_model=SolicitudResponse, status_code=status.HTTP_200_OK)
async def get_solicitud(
    solicitud_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to retrieve a solicitud by ID.
    """
    try:
        stmt = select(Solicitud).where(Solicitud.id == solicitud_id)
        result = await session.execute(stmt)
        solicitud = result.scalar_one_or_none()
        
        if not solicitud:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitud not found"
            )
        
        return SolicitudResponse.from_orm(solicitud)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving solicitud: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the solicitud: {str(e)}"
        )


@router.put("/solicitud/{solicitud_id}", response_model=SolicitudResponse, status_code=status.HTTP_200_OK)
async def update_solicitud(
    solicitud_id: int,
    request: SolicitudUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to update an existing solicitud.
    """
    try:
        stmt = select(Solicitud).where(Solicitud.id == solicitud_id)
        result = await session.execute(stmt)
        solicitud = result.scalar_one_or_none()
        
        if not solicitud:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitud not found"
            )
        
        # Update fields
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(solicitud, field, value)
        
        # Create status history if status changed
        if "status" in update_data and update_data["status"] != solicitud.status:
            status_history = SolicitudStatusHistory(
                solicitud_id=solicitud.id,
                status=update_data["status"],
                notes=f"Status updated to {update_data['status']}"
            )
            session.add(status_history)
        
        await session.commit()
        
        logger.info(f"Solicitud updated successfully, ID: {solicitud_id}")
        return SolicitudResponse.from_orm(solicitud)
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating solicitud: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the solicitud: {str(e)}"
        )


@router.get("/solicitud/{solicitud_id}/status-history", response_model=List[SolicitudStatusHistoryResponse], status_code=status.HTTP_200_OK)
async def get_solicitud_status_history(
    solicitud_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to retrieve status history for a solicitud.
    """
    try:
        stmt = select(SolicitudStatusHistory).where(
            SolicitudStatusHistory.solicitud_id == solicitud_id
        ).order_by(SolicitudStatusHistory.created_at.desc())
        
        result = await session.execute(stmt)
        history = result.scalars().all()
        
        return [SolicitudStatusHistoryResponse.from_orm(h) for h in history]
        
    except Exception as e:
        logger.error(f"Error retrieving status history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving status history: {str(e)}"
        )


@router.post("/solicitud/{solicitud_id}/contact-attempt", response_model=ContactAttemptResponse, status_code=status.HTTP_201_CREATED)
async def create_contact_attempt(
    solicitud_id: int,
    request: dict,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to create a contact attempt for a solicitud.
    """
    try:
        contact_attempt = ContactAttempt(
            solicitud_id=solicitud_id,
            contact_method=request.get("contact_method", "phone"),
            status=request.get("status", "pending"),
            notes=request.get("notes")
        )
        
        session.add(contact_attempt)
        await session.commit()
        
        logger.info(f"Contact attempt created for solicitud {solicitud_id}")
        return ContactAttemptResponse.from_orm(contact_attempt)
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating contact attempt: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating contact attempt: {str(e)}"
        )

