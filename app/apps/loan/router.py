"""
Loan router
Migrated from Flask app/loan/routes.py
Basic structure with essential endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from decimal import Decimal, InvalidOperation
import logging

from app.database import get_async_session
from app.apps.authentication.dependencies import get_current_user
from app.apps.loan.models import Solicitud, Application, SolicitudStatusHistory, ContactAttempt, ProcessType, ProcessStep
from app.apps.loan.schemas import (
    SolicitudCreate,
    SolicitudUpdate,
    SolicitudResponse,
    SolicitudCreateResponse,
    SendNIPRequest,
    ValidateNIPRequest,
    GetBCKibanRequest,
    ApplicationResponse,
    SolicitudStatusHistoryResponse,
    ContactAttemptResponse,
    AddClientWithoutReportRequest,
    AddClientWithoutReportResponse,
    ProcessTypeResponse,
    ProcessStepResponse,
    ProcessStepsResponse,
)
from app.apps.client.models import Cliente, Report
from app.apps.product.models import Motorcycles, MotorcycleBrand
from app.apps.quote.models import Banco
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
    Returns: { status: "success", response: { id: <nip_request_id> } }
    """
    from app.apps.loan.utils.kiban_service import kiban_api
    
    logger.info(f"Sending NIP to Kiban service for phone: {request.to}")
    try:
        # Convert request to dict for Kiban API
        data = request.model_dump()
        response = await kiban_api.send_nip_kiban(data)
        
        if response is None or "error" in response:
            logger.error(
                f"Error consulting KIBAN API for sending NIP: {response.get('error', 'Unknown error') if response else 'None response'}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Error al consultar KIBAN API",
                    "data": response
                }
            )
        
        logger.info(f"NIP sent successfully, response: {response}")
        return {"status": "success", "response": response}
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
    Returns: { status: "success", response: { id: <validated_id> } }
    """
    from app.apps.loan.utils.kiban_service import kiban_api
    
    logger.info(f"Validating NIP with Kiban service for id: {request.id}")
    try:
        # Convert request to dict for Kiban API
        data = request.model_dump()
        response = await kiban_api.verify_nip_kiban(data)
        
        if response is None or "error" in response:
            logger.error(
                f"Error consulting KIBAN API for validating NIP: {response.get('error', 'Unknown error') if response else 'None response'}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Error al consultar KIBAN API",
                    "data": response
                }
            )
        
        logger.info(f"NIP validated successfully, response: {response}")
        return {"status": "success", "response": response}
    except Exception as e:
        logger.error(f"Error in validate_nip_kiban: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/solicitud", response_model=SolicitudCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_solicitud(
    request: SolicitudCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to create a new solicitud (loan application).
    """
    try:
        # Get request data and filter out fields that don't exist in the database
        request_data = request.model_dump(exclude_unset=True)
        
        logger.info(f"Received solicitud creation request with keys: {list(request_data.keys())}")
        if 'solicitud_data' in request_data:
            logger.info(f"solicitud_data contains: {list(request_data['solicitud_data'].keys()) if isinstance(request_data.get('solicitud_data'), dict) else 'not a dict'}")
        
        # Extract data from nested solicitud_data if it exists
        # The frontend sends data nested in solicitud_data, but we need it at the top level
        if 'solicitud_data' in request_data and isinstance(request_data['solicitud_data'], dict):
            solicitud_data_nested = request_data.pop('solicitud_data')
            # Merge nested data into main request_data
            # Nested data takes precedence if there are conflicts (overwrites top-level values)
            for key, value in solicitud_data_nested.items():
                # Merge all values, we'll convert empty strings to None later
                request_data[key] = value
        
        # Extract data from nested bank_data if it exists (for future use)
        if 'bank_data' in request_data and isinstance(request_data['bank_data'], dict):
            bank_data_nested = request_data.pop('bank_data')
            # Merge bank_data fields if needed (currently not used but keeping for compatibility)
            for key, value in bank_data_nested.items():
                # Merge all values, we'll convert empty strings to None later
                request_data[key] = value
        
        # Handle field name mappings from frontend to database
        # Map old field names to new ones if they exist
        field_mappings = {
            'loan_term_months': 'finance_term_months',  # Map loan_term_months to finance_term_months
            'down_payment_amount': None,  # Will be converted to percentage_down_payment if invoice_motorcycle_value exists
            'amount_to_finance': None,  # Not used directly, but invoice_motorcycle_value should be set
            'insurance_amount': 'insurance_payment',  # Map insurance_amount to insurance_payment
        }
        
        # Apply field mappings
        for old_field, new_field in field_mappings.items():
            if old_field in request_data and request_data[old_field] is not None:
                if new_field:
                    # Map to new field name
                    if new_field not in request_data or request_data[new_field] is None:
                        request_data[new_field] = request_data[old_field]
                # Remove old field after mapping
                request_data.pop(old_field, None)
        
        # Remove fields that don't exist in the database model
        # These fields are accepted in the request but the database uses different column names or doesn't have them
        non_existent_fields = [
            'motorcycle_id',  # Not a column, but used for lookup
            'bank_offer_id',
            'monthly_payment',  # Doesn't exist
            'insurance_payment_method',  # Doesn't exist
            'paquete',  # Doesn't exist
            'email_notification',  # Not stored in DB, only in response
            'flow_process',  # Not stored in DB
        ]
        
        for field in non_existent_fields:
            request_data.pop(field, None)
        
        # Convert empty strings to None for optional fields
        for key, value in list(request_data.items()):
            if value == "":
                request_data[key] = None
        
        # Convert string numeric fields to Decimal if they are strings
        numeric_fields = [
            'invoice_motorcycle_value',
            'percentage_down_payment',
            'monthly_income',
            'debt_pay_from_income',
            'downpayment_granted',
            'amount_to_finance_granted'
        ]
        
        for field in numeric_fields:
            if field in request_data and request_data[field] is not None:
                value = request_data[field]
                if isinstance(value, str):
                    try:
                        # Remove any whitespace and convert to Decimal
                        request_data[field] = Decimal(str(value).strip())
                    except (InvalidOperation, ValueError):
                        # If conversion fails, set to None or keep as is
                        logger.warning(f"Could not convert {field} value '{value}' to Decimal, setting to None")
                        request_data[field] = None
                elif isinstance(value, (int, float)):
                    # Convert int/float to Decimal
                    request_data[field] = Decimal(str(value))
        
        # Convert integer fields (year_motorcycle, cliente_id, report_id, user_id, etc.)
        integer_fields = [
            'year_motorcycle',
            'cliente_id',
            'report_id',
            'user_id',
            'finva_user_id',
            'preferred_store_id'
        ]
        
        for field in integer_fields:
            if field in request_data and request_data[field] is not None:
                value = request_data[field]
                if isinstance(value, str):
                    try:
                        # Remove any whitespace and convert to int
                        request_data[field] = int(str(value).strip())
                    except (ValueError, TypeError):
                        # If conversion fails, set to None
                        logger.warning(f"Could not convert {field} value '{value}' to int, setting to None")
                        request_data[field] = None
                elif isinstance(value, float):
                    # Convert float to int
                    request_data[field] = int(value)
        
        # Ensure payment_method is set (required field with NOT NULL constraint)
        payment_method = request_data.get('payment_method', 'loan')
        if not payment_method:
            payment_method = 'loan'  # Default value from original model
        request_data['payment_method'] = payment_method
        
        # Get process_type_id from payment_method
        process_type_id = None
        try:
            stmt = select(ProcessType).where(ProcessType.payment_method == payment_method)
            result = await session.execute(stmt)
            process_type = result.scalar_one_or_none()
            if process_type:
                process_type_id = process_type.id
        except Exception as e:
            logger.warning(f"Could not find process_type for payment_method '{payment_method}': {str(e)}")
        
        # Log key fields before creating solicitud for debugging
        logger.info(f"Creating solicitud with key fields: cliente_id={request_data.get('cliente_id')}, "
                   f"report_id={request_data.get('report_id')}, "
                   f"brand_motorcycle={request_data.get('brand_motorcycle')}, "
                   f"model_motorcycle={request_data.get('model_motorcycle')}, "
                   f"year_motorcycle={request_data.get('year_motorcycle')}, "
                   f"invoice_motorcycle_value={request_data.get('invoice_motorcycle_value')}")
        
        solicitud = Solicitud(**request_data)
        session.add(solicitud)
        await session.flush()
        
        # Create initial status history
        # For the first status entry, previous_status is None and new_status is the initial status
        status_history = SolicitudStatusHistory(
            solicitud_id=solicitud.id,
            previous_status=None,  # No previous status for initial entry
            new_status=solicitud.status or "pending",  # Use new_status, not status
            comment="Solicitud created",  # Use comment, not notes
            process_type_id=process_type_id  # Set process_type_id if found
        )
        session.add(status_history)
        
        await session.commit()
        
        logger.info(f"Solicitud created successfully, ID: {solicitud.id}")
        
        # Refresh to get all fields from database
        await session.refresh(solicitud)
        
        # Use model_validate for Pydantic v2 (from_orm is deprecated)
        solicitud_response = SolicitudResponse.model_validate(solicitud)
        
        # Return in the same format as original Flask implementation
        return SolicitudCreateResponse(
            email_notification=True,
            message="Solicitud added successfully",
            solicitud=solicitud_response,
            success=True
        )
        
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
        
        # Get request data and filter out fields that don't exist in the database
        update_data = request.model_dump(exclude_unset=True)
        
        logger.info(f"Received solicitud update request for ID {solicitud_id} with keys: {list(update_data.keys())}")
        if 'solicitud_data' in update_data:
            logger.info(f"solicitud_data contains: {list(update_data['solicitud_data'].keys()) if isinstance(update_data.get('solicitud_data'), dict) else 'not a dict'}")
        
        # Extract data from nested solicitud_data if it exists
        # The frontend sends data nested in solicitud_data, but we need it at the top level
        if 'solicitud_data' in update_data and isinstance(update_data['solicitud_data'], dict):
            solicitud_data_nested = update_data.pop('solicitud_data')
            # Merge nested data into main update_data
            # Nested data takes precedence if there are conflicts (overwrites top-level values)
            for key, value in solicitud_data_nested.items():
                # Merge all values, we'll convert empty strings to None later
                update_data[key] = value
        
        # Extract data from nested bank_data if it exists (for future use)
        if 'bank_data' in update_data and isinstance(update_data['bank_data'], dict):
            bank_data_nested = update_data.pop('bank_data')
            # Merge bank_data fields if needed (currently not used but keeping for compatibility)
            for key, value in bank_data_nested.items():
                # Merge all values, we'll convert empty strings to None later
                update_data[key] = value
        
        # Handle field name mappings from frontend to database
        # Map old field names to new ones if they exist
        field_mappings = {
            'loan_term_months': 'finance_term_months',  # Map loan_term_months to finance_term_months
            'down_payment_amount': None,  # Will be converted to percentage_down_payment if invoice_motorcycle_value exists
            'amount_to_finance': None,  # Not used directly, but invoice_motorcycle_value should be set
            'insurance_amount': 'insurance_payment',  # Map insurance_amount to insurance_payment
        }
        
        # Apply field mappings
        for old_field, new_field in field_mappings.items():
            if old_field in update_data and update_data[old_field] is not None:
                if new_field:
                    # Map to new field name
                    if new_field not in update_data or update_data[new_field] is None:
                        update_data[new_field] = update_data[old_field]
                # Remove old field after mapping
                update_data.pop(old_field, None)
        
        # Remove fields that don't exist in the database model
        # These fields are accepted in the request but the database uses different column names or doesn't have them
        non_existent_fields = [
            'motorcycle_id',  # Not a column, but used for lookup
            'bank_offer_id',
            'monthly_payment',  # Doesn't exist
            'insurance_payment_method',  # Doesn't exist
            'paquete',  # Doesn't exist
            'email_notification',  # Not stored in DB, only in response
            'flow_process',  # Not stored in DB
        ]
        
        for field in non_existent_fields:
            update_data.pop(field, None)
        
        # Convert empty strings to None for optional fields
        for key, value in list(update_data.items()):
            if value == "":
                update_data[key] = None
        
        # Convert string numeric fields to Decimal if they are strings
        numeric_fields = [
            'invoice_motorcycle_value',
            'percentage_down_payment',
            'monthly_income',
            'debt_pay_from_income',
            'downpayment_granted',
            'amount_to_finance_granted'
        ]
        
        for field in numeric_fields:
            if field in update_data and update_data[field] is not None:
                value = update_data[field]
                if isinstance(value, str):
                    try:
                        # Remove any whitespace and convert to Decimal
                        update_data[field] = Decimal(str(value).strip())
                    except (InvalidOperation, ValueError):
                        # If conversion fails, set to None
                        logger.warning(f"Could not convert {field} value '{value}' to Decimal, setting to None")
                        update_data[field] = None
                elif isinstance(value, (int, float)):
                    # Convert int/float to Decimal
                    update_data[field] = Decimal(str(value))
        
        # Convert integer fields (year_motorcycle, cliente_id, report_id, user_id, etc.)
        integer_fields = [
            'year_motorcycle',
            'cliente_id',
            'report_id',
            'user_id',
            'finva_user_id',
            'preferred_store_id'
        ]
        
        for field in integer_fields:
            if field in update_data and update_data[field] is not None:
                value = update_data[field]
                if isinstance(value, str):
                    try:
                        # Remove any whitespace and convert to int
                        update_data[field] = int(str(value).strip())
                    except (ValueError, TypeError):
                        # If conversion fails, set to None
                        logger.warning(f"Could not convert {field} value '{value}' to int, setting to None")
                        update_data[field] = None
                elif isinstance(value, float):
                    # Convert float to int
                    update_data[field] = int(value)
        
        # Get previous status before updating (for status history)
        previous_status = solicitud.status if "status" in update_data else None
        
        # Log key fields before updating for debugging
        logger.info(f"Updating solicitud {solicitud_id} with key fields: "
                   f"brand_motorcycle={update_data.get('brand_motorcycle')}, "
                   f"model_motorcycle={update_data.get('model_motorcycle')}, "
                   f"year_motorcycle={update_data.get('year_motorcycle')}, "
                   f"invoice_motorcycle_value={update_data.get('invoice_motorcycle_value')}")
        
        # Update fields
        for field, value in update_data.items():
            # Only update fields that exist on the model
            if hasattr(solicitud, field):
                setattr(solicitud, field, value)
            else:
                logger.warning(f"Skipping field '{field}' as it doesn't exist on Solicitud model")
        
        # Create status history if status changed
        if "status" in update_data and update_data["status"] != previous_status:
            new_status = update_data["status"]
            
            # Get process_type_id from payment_method if available
            process_type_id = None
            if hasattr(solicitud, 'payment_method') and solicitud.payment_method:
                try:
                    stmt = select(ProcessType).where(ProcessType.payment_method == solicitud.payment_method)
                    result = await session.execute(stmt)
                    process_type = result.scalar_one_or_none()
                    if process_type:
                        process_type_id = process_type.id
                except Exception as e:
                    logger.warning(f"Could not find process_type for payment_method '{solicitud.payment_method}': {str(e)}")
            
            status_history = SolicitudStatusHistory(
                solicitud_id=solicitud.id,
                previous_status=previous_status,  # Previous status (before update)
                new_status=new_status,  # New status (from update_data)
                comment=f"Status updated to {new_status}",  # Use comment, not notes
                process_type_id=process_type_id  # Set process_type_id if found
            )
            session.add(status_history)
        
        await session.commit()
        
        logger.info(f"Solicitud updated successfully, ID: {solicitud_id}")
        
        # Refresh to get all fields from database
        await session.refresh(solicitud)
        
        # Use model_validate for Pydantic v2 (from_orm is deprecated)
        return SolicitudResponse.model_validate(solicitud)
        
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
        
        return [SolicitudStatusHistoryResponse.model_validate(h) for h in history]
        
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


@router.get("/applications", response_model=dict, status_code=status.HTTP_200_OK)
async def get_applications(
    client_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to retrieve all solicitudes (applications) for a client.
    Returns applications in the format expected by the frontend.
    """
    try:
        # Use raw SQL to select only columns that exist in the database
        # The original database has individual columns, not solicitud_data JSONB
        stmt = text("""
            SELECT 
                id, 
                cliente_id, 
                status, 
                created_at,
                brand_motorcycle,
                model_motorcycle,
                year_motorcycle,
                invoice_motorcycle_value
            FROM solicitudes
            WHERE cliente_id = :client_id
            ORDER BY created_at DESC
        """)
        
        result = await session.execute(stmt, {"client_id": client_id})
        rows = result.fetchall()
        
        # Format response to match frontend expectations
        applications = []
        for row in rows:
            application = {
                "id": row.id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "brand_motorcycle": row.brand_motorcycle or "",
                "model_motorcycle": row.model_motorcycle or "",
                "year_motorcycle": row.year_motorcycle if row.year_motorcycle else None,
                "invoice_motorcycle_value": float(row.invoice_motorcycle_value) if row.invoice_motorcycle_value else None,
                "status": row.status or "pending",
            }
            applications.append(application)
        
        return {"applications": applications}
        
    except Exception as e:
        logger.error(f"Error retrieving applications: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving applications: {str(e)}"
        )
        
@router.get("/evaluar/{solicitud_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def evaluate_solicitud(
    solicitud_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to evaluate a solicitud and return bank offers.
    TODO: Implement actual evaluation logic with bank scoring/offers
    """
    try:
        # Use the migrated evaluation logic
        from app.apps.loan.utils.evaluate_solicitud import evaluate_solicitud_logic
        
        result = await evaluate_solicitud_logic(solicitud_id, session)
        
        # Check for errors in result
        if "error" in result:
            status_code = result.pop("status_code", 500)
            raise HTTPException(
                status_code=status_code,
                detail=result.get("error", "Error evaluating solicitud")
            )
        
        # Remove status_code from response (it's for internal use)
        result.pop("status_code", None)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating solicitud: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while evaluating the solicitud: {str(e)}"
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
    Returns: { report_id: <report_id>, cliente_id: <cliente_id> }
    """
    from app.apps.loan.utils.kiban_service import kiban_api
    from app.apps.loan.utils.insert_report_data import insert_report, insert_report_data_bulk
    
    logger.info(f"Retrieving BC report for client {cliente_id} from Kiban service")
    try:
        # Convert request to dict for Kiban API
        data = request.model_dump()
        
        # Query BC report from Kiban API
        report_kiban = await kiban_api.query_bc_pf_by_kiban(data)
        
        if report_kiban is None or "error" in report_kiban:
            logger.error(
                f"Error retrieving BC report from Kiban for client {cliente_id}, {report_kiban}, body: {data}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Error al consultar KIBAN API",
                    "data": report_kiban
                }
            )
        
        # Insert the report
        report = await insert_report(report_kiban, cliente_id, session)
        
        if report is None or "error" in report:
            logger.error(
                f'Error creating report for client {cliente_id}: {report.get("error", "Unknown error") if report else "None response"}'
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Error al crear reporte",
                    "data": report
                }
            )
        
        logger.info(
            f'Report created successfully for client {cliente_id}, report ID: {report["id"]}'
        )
        
        # Insert all report data using the utility function
        if "response" in report_kiban:
            insert_results = await insert_report_data_bulk(report["id"], report_kiban["response"], session)
            
            # Log the results
            if insert_results["total_failed"] > 0:
                logger.warning(
                    f'Some insert functions failed for report ID: {report["id"]}. '
                    f'Successful: {insert_results["total_successful"]}, '
                    f'Failed: {insert_results["total_failed"]}, '
                    f'Failures: {insert_results["failed"]}'
                )
            else:
                logger.info(
                    f'All insert functions completed successfully for report ID: {report["id"]}'
                )
        
        response = {
            "success": True,
            "message": "Report/ConsultaBC added and client data updated successfully",
            "report_id": report["id"],
            "cliente_id": cliente_id,
        }
        
        logger.info(
            f'Report and associated data inserted successfully for client {cliente_id}, report ID: {report["id"]}'
        )
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_bc_kiban: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving BC report: {str(e)}"
        )


@router.get("/process-steps/{payment_method}", response_model=ProcessStepsResponse, status_code=status.HTTP_200_OK)
async def get_process_steps(
    payment_method: str,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Get all process steps for a given payment method.
    Migrated from Flask app/loan/routes.py
    """
    try:
        # Get process type based on payment method
        stmt = select(ProcessType).where(ProcessType.payment_method == payment_method)
        result = await session.execute(stmt)
        process_type = result.scalar_one_or_none()
        
        if not process_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No process type found for payment method: {payment_method}"
            )
        
        # Get all process steps for this process type
        stmt = select(ProcessStep).where(
            ProcessStep.process_type_id == process_type.id
        ).order_by(ProcessStep.step_order)
        result = await session.execute(stmt)
        process_steps = result.scalars().all()
        
        steps_data = [
            ProcessStepResponse(
                id=step.id,
                process_type_id=step.process_type_id,
                step_order=step.step_order,
                step_name=step.step_name
            )
            for step in process_steps
        ]
        
        return ProcessStepsResponse(
            process_type=process_type.name,
            payment_method=payment_method,
            steps=steps_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_process_steps: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving process steps: {str(e)}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_bc_kiban: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )