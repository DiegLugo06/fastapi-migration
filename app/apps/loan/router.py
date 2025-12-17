"""
Loan router
Migrated from Flask app/loan/routes.py
Basic structure with essential endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
    AddClientWithoutReportRequest,
    AddClientWithoutReportResponse,
)
from app.apps.client.models import Cliente, Report
from app.apps.product.models import Motorcycles, MotorcycleBrand
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError
import hashlib

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


@router.post("/add_client_without_report", response_model=AddClientWithoutReportResponse, status_code=status.HTTP_201_CREATED)
async def add_client_without_report(
    request: AddClientWithoutReportRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Adds a new client without a report.
    
    Steps:
    - Receives phone, email, CURP (optional), and motorcycle ID.
    - If CURP provided: fetches CURP data from Kiban API (TODO: implement Kiban integration)
    - If CURP not provided: uses provided client information directly
    - Creates/updates Cliente record
    - Creates associated Report and Solicitud records
    - Returns the newly created client and solicitud data.
    """
    try:
        logger.info("Received request to add client without report")
        
        # Check if motorcycle exists
        stmt = select(Motorcycles).where(Motorcycles.id == request.id_motorcycle)
        result = await session.execute(stmt)
        motorcycle = result.scalar_one_or_none()
        
        if not motorcycle:
            logger.error(f"Motorcycle ID {request.id_motorcycle} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Motorcycle not found"
            )
        
        # Handle client data based on whether CURP is provided
        if request.curp:
            # TODO: Implement CURP data fetching from Kiban API
            # For now, use provided client information
            logger.warning("CURP provided but Kiban integration not yet implemented, using provided client data")
            valid_cliente_data = {
                "name": request.name,
                "second_name": request.second_name,
                "first_last_name": request.first_last_name,
                "second_last_name": request.second_last_name,
            }
        else:
            # Use provided client information directly
            if not request.name or not request.first_last_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required fields: name and first_last_name are required when CURP is not provided"
                )
            valid_cliente_data = {
                "name": request.name,
                "second_name": request.second_name,
                "first_last_name": request.first_last_name,
                "second_last_name": request.second_last_name,
            }
        
        # Add contact information
        valid_cliente_data.update({
            "phone": request.phone,
            "email": request.email
        })
        
        # Check if client already exists
        stmt = select(Cliente).where(
            or_(Cliente.phone == request.phone, Cliente.email == request.email)
        )
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()
        
        if not client:
            # Create new client
            client = Cliente(**valid_cliente_data)
            session.add(client)
            await session.flush()  # Get the ID
            logger.info(f"Created client {client.id}")
        else:
            # Update existing client with new data if needed
            for key, value in valid_cliente_data.items():
                if value and hasattr(client, key):
                    setattr(client, key, value)
            await session.flush()
            logger.info(f"Using existing client {client.id}")
        
        # Generate kiban_id and check for existing report
        kiban_id = hashlib.md5(str(client.id).encode()).hexdigest()
        stmt = select(Report).where(Report.kiban_id == kiban_id)
        result = await session.execute(stmt)
        existing_report = result.scalar_one_or_none()
        
        if existing_report:
            logger.info(f"Using existing report {existing_report.id} for client {client.id}")
            report_id = existing_report.id
        else:
            # Create new Report
            new_report = Report(
                kiban_id=kiban_id,
                cliente_id=client.id
            )
            session.add(new_report)
            await session.flush()
            logger.info(f"Created report {new_report.id}")
            report_id = new_report.id
        
        # Fetch Brand Name
        stmt = select(MotorcycleBrand).where(MotorcycleBrand.id == motorcycle.brand_id)
        result = await session.execute(stmt)
        brand = result.scalar_one_or_none()
        
        if not brand or not brand.name:
            logger.warning(f"Error processing Motorcycle data: Brand id not valid : {motorcycle.brand_id}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to process Motorcycle data: Brand id not valid : {motorcycle.brand_id}"
            )
        
        # Create Solicitud
        # Note: The Solicitud model in fastapi-migration may have different fields
        # We'll use solicitud_data JSON field to store additional data
        solicitud_data = {
            "cliente_id": client.id,
            "motorcycle_id": request.id_motorcycle,
            "user_id": request.user_id,
        }
        
        # Store additional data in solicitud_data JSON field
        solicitud_json_data = {
            "brand_motorcycle": brand.name,
            "model_motorcycle": motorcycle.model,
            "year_motorcycle": motorcycle.year,
            "invoice_motorcycle_value": motorcycle.price,
            "payment_method": request.payment_method,
            "preferred_store_id": request.preferred_store_id,
            "time_to_buy_motorcycle": request.time_to_buy_motorcycle,
            "registration_process": request.registration_process or "manualRegistration",
            "registration_mode": request.registration_mode,
        }
        
        new_solicitud = Solicitud(
            **solicitud_data,
            solicitud_data=solicitud_json_data
        )
        session.add(new_solicitud)
        await session.commit()
        
        logger.info(f"Created solicitud {new_solicitud.id}")
        
        # TODO: Send email notifications
        # This requires migrating email utility functions
        
        logger.info(
            f"New client: {client.id}, report: {report_id}, and solicitud: {new_solicitud.id} added successfully"
        )
        
        return AddClientWithoutReportResponse(
            message="Client and solicitud created successfully",
            client_id=client.id,
            solicitud_id=new_solicitud.id
        )
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await session.rollback()
        error_message = str(e.orig)
        
        if "clientes_email_key" in error_message:
            logger.warning(f"Error: A client with this email already exists: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A client with this email already exists: {request.email}"
            )
        elif "clientes_phone_key" in error_message:
            logger.warning(f"Error: A client with this phone already exists: {request.phone}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A client with this phone already exists: {request.phone}"
            )
        
        logger.error(f"Database integrity error: {error_message}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database integrity error: {error_message}"
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error processing data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

