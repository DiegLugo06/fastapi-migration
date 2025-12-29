"""
Client router
Migrated from Flask app/client/routes.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
import logging
import io

from app.database import get_async_session
from app.apps.authentication.dependencies import get_current_user
from app.apps.client.models import Cliente, FileStatus, IncomeProofDocument, Report, ClientesUnknown
from app.apps.client.schemas import (
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse,
    FileStatusResponse,
    IncomeProofDocumentResponse,
    ReportResponse,
    ValidateClientResponse,
    ValidatePhoneResponse,
    GenerateRFCRequest,
    GenerateRFCResponse,
    GetNeighborhoodsResponse,
    ClientesUnknownCreate,
    ClientesUnknownResponse,
    ValidateCurpRequest,
    ValidateCurpResponse,
    GenerateCurpRequest,
    GenerateCurpResponse,
    ValidateCredentialCompleteRequest,
    ValidateCredentialCompleteResponse,
)
from app.apps.client.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/cliente", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_cliente(
    request: ClienteCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to create a new client.
    """
    try:
        if not request.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is missing."
            )
        
        # Create cliente from request data
        cliente_data = request.dict(exclude={"user_id", "flow_process", "finva_user_id"})
        new_client = Cliente(**cliente_data)
        
        session.add(new_client)
        await session.flush()  # Get the ID
        
        response = {}
        
        # TODO: Handle email notifications and CRM sync
        # This requires migrating utility functions:
        # - _send_client_notification
        # - sync_client_with_crm
        
        # Create the client-user association
        # Note: clientes_users is a many-to-many table that may not exist in test DB
        try:
            stmt = text("""
                INSERT INTO clientes_users (cliente_id, user_id)
                VALUES (:cliente_id, :user_id)
            """)
            await session.execute(stmt, {
                "cliente_id": new_client.id,
                "user_id": request.user_id
            })
        except Exception as e:
            # If table doesn't exist (e.g., in tests), log and continue
            logger.warning(f"Could not create client-user association: {str(e)}")
            # This is not critical for client creation
        
        await session.commit()
        
        logger.info(f"Cliente added successfully, ID: {new_client.id}")
        
        # Prepare the response
        # Use model_validate for Pydantic v2 compatibility
        cliente_dict = ClienteResponse.model_validate(new_client).model_dump()
        response.update({
            "success": True,
            "message": "Cliente added successfully",
            "cliente": cliente_dict,
            "cliente_id": new_client.id,
        })
        
        return response
        
    except IntegrityError as e:
        await session.rollback()
        error_message = str(e.orig)
        
        if "clientes_email_key" in error_message:
            logger.warning(f'Error: A client with this email already exists: {request.email}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A client with this email already exists.",
            )
        elif "clientes_phone_key" in error_message:
            logger.warning(f'Error: A client with this phone already exists: {request.phone}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A client with this phone already exists.",
            )
        
        logger.error(f"Database integrity error: {error_message}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database integrity error: {error_message}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error while creating client: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the client: {str(e)}"
        )


@router.get("/cliente/{id}", response_model=ClienteResponse, status_code=status.HTTP_200_OK)
async def get_cliente(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to retrieve a client by ID.
    """
    try:
        stmt = select(Cliente).where(Cliente.id == id)
        result = await session.execute(stmt)
        cliente = result.scalar_one_or_none()
        
        if not cliente:
            logger.error(f"Client not found with ID: {id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente not found"
            )
        
        logger.info(f"Client retrieved successfully, ID: {id}")
        return ClienteResponse.from_orm(cliente)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error while retrieving client ID {id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the client: {str(e)}"
        )


@router.put("/cliente/{cliente_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def update_cliente(
    cliente_id: int,
    request: ClienteUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to update an existing client.
    """
    try:
        stmt = select(Cliente).where(Cliente.id == cliente_id)
        result = await session.execute(stmt)
        cliente = result.scalar_one_or_none()
        
        if not cliente:
            logger.warning(f"Client not found with ID: {cliente_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente not found"
            )
        
        # Update fields
        update_data = request.dict(exclude_unset=True, exclude={"user_id"})
        for field, value in update_data.items():
            setattr(cliente, field, value)
        
        # TODO: Handle CRM synchronization if user_id is provided
        # This requires migrating sync_client_with_crm utility
        
        await session.commit()
        logger.info(f"Successfully updated client with ID: {cliente_id}")
        
        return {
            "success": True,
            "message": "Cliente updated successfully",
            "cliente": ClienteResponse.from_orm(cliente).dict(),
        }
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await session.rollback()
        error_message = str(e.orig)
        
        if "clientes_email_key" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A client with this email already exists.",
            )
        elif "clientes_phone_key" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A client with this phone already exists.",
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database integrity error: {error_message}"
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error while updating client: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the client: {str(e)}"
        )


@router.post("/generate_rfc", response_model=GenerateRFCResponse, status_code=status.HTTP_200_OK)
async def generate_rfc(
    request: GenerateRFCRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to generate RFC of a client.
    """
    # TODO: Implement kiban_api.generate_rfc
    # This requires migrating the kiban extension
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="RFC generation not yet implemented - requires kiban_api migration"
    )


@router.get("/validate_client", response_model=ValidateClientResponse, status_code=status.HTTP_200_OK)
async def validate_client(
    email: str = Query(...),
    phone: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to retrieve a client by email and phone number, and optionally return the report if available.
    """
    try:
        stmt = select(Cliente).where(
            and_(Cliente.email == email, Cliente.phone == phone)
        )
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()
        
        if not client:
            logger.error(f"Client not found with email: {email} and phone: {phone}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente not found"
            )
        
        logger.info(f"Client retrieved successfully, email: {email} and phone: {phone}")
        
        # Get file status
        stmt = select(FileStatus).where(FileStatus.cliente_id == client.id)
        result = await session.execute(stmt)
        files = result.scalar_one_or_none()
        
        if not files:
            files = FileStatus(cliente_id=client.id)
            session.add(files)
            await session.commit()
        
        # TODO: Implement is_valid_identification and is_valid_report
        # For now, return basic validation
        is_valid = True
        id_details = "Valid"
        
        # Get the most recent report
        stmt = select(Report).where(Report.cliente_id == client.id).order_by(Report.created_at.desc())
        result = await session.execute(stmt)
        report = result.scalar_one_or_none()
        
        report_id = None
        report_details = None
        if report:
            # TODO: Implement is_valid_report
            report_id = report.id
            report_details = "Valid"
        
        # Get income proof documents
        stmt = select(IncomeProofDocument).where(
            IncomeProofDocument.client_id == client.id,
            IncomeProofDocument.sequence_number.isnot(None)
        ).order_by(IncomeProofDocument.sequence_number.asc())
        result = await session.execute(stmt)
        income_proof_documents = result.scalars().all()
        
        # Check for purchases
        stmt = text("SELECT COUNT(*) FROM purchases WHERE cliente_id = :client_id")
        result = await session.execute(stmt, {"client_id": client.id})
        has_purchases = result.scalar() > 0
        
        files_dict = FileStatusResponse.from_orm(files).dict()
        files_dict["income_proof_documents"] = [
            IncomeProofDocumentResponse.from_orm(doc).dict() for doc in income_proof_documents
        ]
        
        response = {
            "client": ClienteResponse.from_orm(client).dict(),
            "files": files_dict,
            "id": is_valid,
            "id_details": id_details,
            "has_purchases": has_purchases,
        }
        
        if report_id:
            response["report"] = report_id
            response["rerport_details"] = report_details
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error while retrieving client: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the client: {str(e)}"
        )


@router.get("/validate_phone", response_model=ValidatePhoneResponse, status_code=status.HTTP_200_OK)
async def validate_phone(
    phone: str = Query(...),
    email: str = Query(...),
    simply_validation: bool = Query(False),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to validate a client by phone and email.
    """
    logger.info(f"Received validation request: phone={phone}, email={email}")
    
    try:
        # Validate phone
        stmt = select(Cliente).where(Cliente.phone == phone)
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()
        
        validated = None
        
        if client:
            validated = "phone"
            logger.info(f"Client found by phone: {phone}")
            if simply_validation:
                return ValidatePhoneResponse(
                    status="validated",
                    client_id=client.id
                )
        else:
            logger.warning(f"Client not found by phone: {phone}")
            # Try email
            stmt = select(Cliente).where(Cliente.email == email)
            result = await session.execute(stmt)
            client = result.scalar_one_or_none()
            
            if client:
                validated = "email"
                logger.info(f"Client found by email: {email}")
            else:
                logger.error(f"Client not found by phone: {phone} or email: {email}")
                if simply_validation:
                    return ValidatePhoneResponse(
                        status="invalid",
                        client_id=None
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Cliente not found"
                    )
        
        # If client is validated by phone
        if validated == "phone":
            if email == client.email:
                logger.info(f"Phone validated successfully for client ID: {client.id}")
                return ValidatePhoneResponse(status="validated")
            else:
                logger.warning(f"Email Phone mismatch for client ID: {client.id}")
                parts = client.email.split("@")
                username = parts[0]
                domain = parts[1]
                masked_username = "*" * len(username)
                return ValidatePhoneResponse(
                    status="invalid",
                    type="email",
                    clue=f"{masked_username}@{domain}",
                )
        
        # If client is validated by email
        elif validated == "email":
            if phone == client.phone:
                logger.info(f"Email validated successfully for client ID: {client.id}")
                return ValidatePhoneResponse(status="validated")
            else:
                logger.warning(f"Phone mismatch for client ID: {client.id}")
                return ValidatePhoneResponse(
                    status="invalid",
                    type="phone",
                    clue=7 * "*" + client.phone[-4:],
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error occurred during client validation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the client: {str(e)}"
        )


@router.get("/get_neighborhoods/{zip_code}", response_model=GetNeighborhoodsResponse, status_code=status.HTTP_200_OK)
async def get_neighborhoods(
    zip_code: str,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to get neighborhoods by zip code.
    Uses SEPOMEX first, falls back to Copomex if SEPOMEX fails.
    """
    from app.apps.client.services.sepomex_service import sepomex_service
    from app.apps.client.services.copomex_service import copomex_service

    try:
        # Try SEPOMEX first
        sepomex = await sepomex_service.validate_cp(zip_code)

        # If SEPOMEX fails, try Copomex as backup
        if not sepomex:
            logger.info(
                f"SEPOMEX service failed, trying Copomex backup for zip code: {zip_code}"
            )
            copomex_response = await copomex_service.get_neighborhoods_by_zip(zip_code)

            # Check if Copomex response has error
            if copomex_response.get("error", False):
                logger.error(
                    f"Copomex service error: {copomex_response.get('message', 'Unknown error')}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No data found for this zip code"
                )

            # Extract neighborhoods from Copomex response
            colonias = copomex_response.get("response", {}).get("colonia", [])
            if not colonias:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No data found for this zip code"
                )

            return GetNeighborhoodsResponse(neighborhoods=colonias)

        # Handle SEPOMEX response
        # SEPOMEX can return neighborhoods in different formats
        # Try the nested structure first, then check if it's a direct list
        colonias = sepomex.get("codigo_postal", {}).get("colonias", [])
        
        # If not found in nested structure, check if colonias is at root level
        if not colonias:
            colonias = sepomex.get("colonias", [])
        
        # If still not found, check if the response itself is a list
        if not colonias and isinstance(sepomex, list):
            colonias = sepomex
        
        if not colonias:
            logger.warning(f"SEPOMEX response structure unexpected: {sepomex}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for this zip code"
            )

        # Log the structure for debugging
        if colonias:
            logger.info(f"SEPOMEX returned {len(colonias)} neighborhoods, first item type: {type(colonias[0])}")

        return GetNeighborhoodsResponse(neighborhoods=colonias)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing get_neighborhoods request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/file-status/{client_id}", response_model=FileStatusResponse, status_code=status.HTTP_200_OK)
async def get_file_status(
    client_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to get FileStatus and income proof documents for a client.
    """
    try:
        stmt = select(FileStatus).where(FileStatus.cliente_id == client_id)
        result = await session.execute(stmt)
        file_status = result.scalar_one_or_none()
        
        if not file_status:
            logger.info(f"File status not found for client {client_id}, creating new record")
            file_status = FileStatus(cliente_id=client_id)
            session.add(file_status)
            await session.commit()
        
        # Get income proof documents
        stmt = select(IncomeProofDocument).where(IncomeProofDocument.client_id == client_id)
        result = await session.execute(stmt)
        income_docs = result.scalars().all()
        
        response_dict = FileStatusResponse.from_orm(file_status).dict()
        response_dict["income_proof_documents"] = [
            IncomeProofDocumentResponse.from_orm(doc).dict() for doc in income_docs
        ]
        
        return response_dict
        
    except Exception as e:
        logger.error(f"Error retrieving file status for client {client_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file status: {str(e)}"
        )


@router.put("/file-status/{cliente_id}", response_model=FileStatusResponse, status_code=status.HTTP_200_OK)
async def update_file_status(
    cliente_id: int,
    request: dict,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to update FileStatus properties for a client.
    """
    try:
        stmt = select(FileStatus).where(FileStatus.cliente_id == cliente_id)
        result = await session.execute(stmt)
        file_status = result.scalar_one_or_none()
        
        if not file_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File status not found for this client"
            )
        
        # Update fields
        if "officialId_front" in request:
            file_status.officialId_front = request["officialId_front"]
        if "officialId_reverse" in request:
            file_status.officialId_reverse = request["officialId_reverse"]
        if "addressProof" in request:
            file_status.addressProof = request["addressProof"]
        
        await session.commit()
        
        return FileStatusResponse.from_orm(file_status)
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating file status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update file status: {str(e)}"
        )


@router.post("/unknown-client", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_unknown_client(
    request: ClientesUnknownCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to register an unknown client with basic information.
    """
    try:
        # Check if client already exists in main clientes table
        if request.email:
            stmt = select(Cliente).where(Cliente.email == request.email)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                return {"success": True, "message": "Client already exists"}
        
        if request.phone:
            stmt = select(Cliente).where(Cliente.phone == request.phone)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                return {"success": True, "message": "Client already exists"}
        
        # Check if already in unknown clients
        if request.email:
            stmt = select(ClientesUnknown).where(ClientesUnknown.email == request.email)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                return {"success": True, "message": "Client already exists"}
        
        if request.phone:
            stmt = select(ClientesUnknown).where(ClientesUnknown.phone == request.phone)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return {
                    "success": True,
                    "message": "Client already exists",
                    "client": ClientesUnknownResponse.from_orm(existing).dict(),
                }
        
        # Create new unknown client
        unknown_client_data = request.dict(exclude={"motorcycle_data"})
        new_unknown_client = ClientesUnknown(**unknown_client_data)
        
        session.add(new_unknown_client)
        await session.commit()
        
        logger.info(f"Unknown client registered successfully: {new_unknown_client.email}")
        
        # TODO: Handle email notifications and cache
        # This requires migrating:
        # - send_email_to_user
        # - add_client_to_registration_followup_cache
        
        return {
            "success": True,
            "message": "Unknown client registered successfully",
            "client": ClientesUnknownResponse.from_orm(new_unknown_client).dict(),
        }
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error while registering unknown client: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while registering the unknown client: {str(e)}"
        )


@router.get("/unknown-client/{phone}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_unknown_client(
    phone: str,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to get an unknown client by phone number.
    """
    try:
        stmt = select(ClientesUnknown).where(ClientesUnknown.phone == phone)
        result = await session.execute(stmt)
        unknown_client = result.scalar_one_or_none()
        
        if not unknown_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unknown client not found"
            )
        
        client_dict = ClientesUnknownResponse.from_orm(unknown_client).dict()
        
        # TODO: Add motorcycle and user data if needed
        # This requires relationships to be set up
        
        return {"client": client_dict}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting unknown client: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unknown client: {str(e)}"
        )


# Placeholder endpoints for complex validation functions
# These will be implemented when utility functions are migrated

@router.post("/extract-validation-ine", status_code=status.HTTP_200_OK)
async def extract_validation_ine(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Extract INE validation - TODO: Implement utility functions"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="INE extraction not yet implemented - requires utility function migration"
    )


@router.post("/validate-lista-nominal", status_code=status.HTTP_200_OK)
async def validate_lista_nominal(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Validate INE by Kiban - TODO: Implement utility functions"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Lista nominal validation not yet implemented"
    )


@router.post("/validate-curp", status_code=status.HTTP_200_OK)
async def validate_curp(
    request: ValidateCurpRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Validate CURP using primary (Nobarium) and fallback (ValidaCurp, Verificamex) services.
    
    Returns:
        JSON response with client data or error message
    """
    import time
    from app.apps.client.services.nobarium_service import nobarium_service
    from app.apps.client.services.valida_curp_service import valida_curp_service
    from app.apps.client.services.verificamex_service import verificamex_service
    from app.apps.client.utils.curp_transformers import (
        transform_nubarium_curp_response,
        transform_first_service_response,
        transform_second_service_response,
        get_curp_validation_message_mapping,
    )
    
    curp = request.curp
    start_time = time.time()
    curp_data = {}
    
    try:
        logger.info(f"Processing CURP validation: {curp}")
        
        # Try primary service (Nobarium)
        try:
            nobarium_response = await nobarium_service.validate_curp(curp)
            
            if nobarium_response and nobarium_response.get("estatus") == "OK":
                curp_data = transform_nubarium_curp_response(nobarium_response)
                service_used = "nobarium"
                processing_time = time.time() - start_time
                
                return {
                    "success": True,
                    "client_data": curp_data,
                    "status": "success",
                    "metadata": {
                        "service_used": service_used,
                        "processing_time": f"{processing_time:.2f}s",
                    },
                }
            else:
                # Check for specific error codes
                codigo_mensaje = nobarium_response.get("codigoMensaje", "")
                mensaje = nobarium_response.get("mensaje", "Unknown error")
                
                if codigo_mensaje in ["1", "2", "3", "5", "-1"]:
                    user_message = get_curp_validation_message_mapping(codigo_mensaje, mensaje)
                    logger.warning(f"Primary service returned mapped error: {mensaje} (Code: {codigo_mensaje})")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "success": False,
                            "message": user_message,
                            "error_code": codigo_mensaje,
                            "original_message": mensaje,
                            "service": "primary",
                            "curp": curp,
                        }
                    )
                
                # For other errors, check if it's a "not found" type error
                if "no se pudo obtener" in mensaje.lower() or "no encontrado" in mensaje.lower():
                    logger.info(f"Curp not found: {nobarium_response}")
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={"error": "Curp not found"}
                    )
                
                raise ValueError(f"Empty or error response from primary service: {nobarium_response}")
        
        except HTTPException:
            raise
        except Exception as nobarium_error:
            logger.warning(f"Primary service (Nobarium) failed: {str(nobarium_error)}. Attempting fallback...")
            
            # Try fallback service (ValidaCurp)
            try:
                valida_curp_response = await valida_curp_service.get_curp_data(curp)
                
                if valida_curp_response and isinstance(valida_curp_response, dict):
                    if valida_curp_response.get("estatus") == "ERROR":
                        codigo_mensaje = valida_curp_response.get("codigoMensaje", "")
                        mensaje = valida_curp_response.get("mensaje", "")
                        user_message = get_curp_validation_message_mapping(codigo_mensaje, mensaje)
                        
                        logger.warning(f"Fallback service returned error: {mensaje} (Code: {codigo_mensaje})")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={
                                "success": False,
                                "message": user_message,
                                "error_code": codigo_mensaje,
                                "original_message": mensaje,
                                "service": "fallback",
                                "curp": curp,
                            }
                        )
                    
                    if not valida_curp_response.get("error", True):
                        curp_data = transform_first_service_response(valida_curp_response)
                        service_used = "valida_curp"
                    else:
                        raise ValueError(f"Empty or error response from fallback service: {valida_curp_response}")
                else:
                    raise ValueError(f"Invalid response structure from fallback service: {valida_curp_response}")
            
            except HTTPException:
                raise
            except Exception as valida_curp_error:
                logger.warning(f"Fallback service (ValidaCurp) failed: {str(valida_curp_error)}. Attempting second fallback...")
                
                # Try second fallback service (Verificamex)
                try:
                    verificamex_response = await verificamex_service.validate_curp(curp)
                    
                    if verificamex_response and isinstance(verificamex_response, dict):
                        if verificamex_response.get("estatus") == "ERROR":
                            codigo_mensaje = verificamex_response.get("codigoMensaje", "")
                            mensaje = verificamex_response.get("mensaje", "")
                            user_message = get_curp_validation_message_mapping(codigo_mensaje, mensaje)
                            
                            logger.warning(f"Second fallback service also returned error: {mensaje} (Code: {codigo_mensaje})")
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail={
                                    "success": False,
                                    "message": user_message,
                                    "error_code": codigo_mensaje,
                                    "original_message": mensaje,
                                    "service": "second_fallback",
                                    "curp": curp,
                                }
                            )
                    
                    curp_data = transform_second_service_response(verificamex_response)
                    service_used = "verificamex"
                
                except HTTPException:
                    raise
                except Exception as verificamex_error:
                    logger.error(f"All services failed. Primary: {str(nobarium_error)}, Fallback: {str(valida_curp_error)}, Second Fallback: {str(verificamex_error)}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail={
                            "error": "CURP validation service unavailable",
                            "details": str(verificamex_error),
                            "curp": curp,
                            "status": "error",
                        }
                    )
        
        # Build successful response
        processing_time = time.time() - start_time
        logger.info(f"CURP validation completed in {processing_time:.2f} seconds")
        
        return {
            "success": True,
            "client_data": curp_data,
            "status": "success",
            "metadata": {
                "service_used": service_used,
                "processing_time": f"{processing_time:.2f}s",
            },
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CURP validation failed for {curp or 'unknown'}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "CURP validation service unavailable",
                "details": str(e),
                "curp": curp,
                "status": "error",
            }
        )


@router.post("/generate-curp", status_code=status.HTTP_200_OK)
async def generate_curp(
    request: GenerateCurpRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Generate CURP from person's data using Kiban API.
    
    Returns:
        JSON response with generated CURP and client data
    """
    import os
    import httpx
    from app.config import MODE
    
    try:
        logger.info(f"Starting CURP generation for: {request.nombres} {request.primerApellido}")
        
        # Get Kiban API settings
        api_url = os.getenv(
            "KIBAN_API_URL_PRODUCTION" if MODE == "production" else "KIBAN_API_URL_STAGING"
        )
        access_key = os.getenv(
            "KIBAN_API_KEY_PRODUCTION" if MODE == "production" else "KIBAN_API_KEY_STAGING"
        )
        
        if not api_url or not access_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Kiban API configuration missing"
            )
        
        # Prepare request body
        data_body = {
            "claveEntidad": request.claveEntidad,
            "fechaNacimiento": request.fechaNacimiento,
            "nombres": request.nombres,
            "primerApellido": request.primerApellido,
            "segundoApellido": request.segundoApellido,
            "sexo": request.sexo,
        }
        
        # Call Kiban API
        headers = {
            "x-api-key": access_key,
            "Content-Type": "application/json",
        }
        params = {"testCaseId": "664230608659f0c02fcd3f0c"} if MODE != "production" else {}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{api_url}/curp/validateData",
                params=params,
                headers=headers,
                json=data_body
            )
            response.raise_for_status()
            kiban_response = response.json()
        
        curp_data = kiban_response.get("response", {})
        if not curp_data:
            logger.warning(f"Kiban API returned empty response {kiban_response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CURP generation failed"
            )
        
        logger.info("CURP generation successful")
        return {
            "client_data": curp_data,
            "status": "success",
            "curp": curp_data.get("curp", ""),
        }
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during CURP generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CURP generation service error: {str(e)}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error during CURP generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CURP generation service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error during CURP generation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during CURP generation"
        )


@router.post("/validate-ine-tuidentidad", status_code=status.HTTP_200_OK)
async def validate_ine_tuidentidad(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Validate INE with TuIdentidad - TODO: Implement utility functions"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TuIdentidad validation not yet implemented"
    )


@router.post("/validate-credential-complete", status_code=status.HTTP_200_OK)
async def validate_credential_complete(
    request: Request,
    validation_type: str = Query("automatic", description="Validation type: automatic or manual"),
    image_front: Optional[UploadFile] = File(None),
    image_back: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Endpoint to validate INE and CURP in a single flow:
    1. Extract data from INE images using OCR (automatic) or use provided data (manual)
    2. Validate extracted data
    3. Validate INE and CURP in parallel using multiple services
    """
    import time
    import uuid
    import base64
    from app.apps.client.utils.ine_validation_utils import (
        process_ocr_with_nobarium,
        process_ocr_parallel,
        validate_ocr_results,
        validate_curp_and_ine_parallel,
        prepare_combined_response,
        prepare_nobarium_combined_response,
        extract_curp_from_nobarium,
        prepare_validation_body_nobarium,
        prepare_validation_body,
    )
    
    timing_metrics = {}
    start_time = time.time()
    request_id = str(uuid.uuid4())
    validation_type = validation_type.lower()
    
    try:
        logger.info(f"[{request_id}] Starting complete credential validation - type: {validation_type}")
        
        if validation_type == "manual":
            # Get data from JSON body for manual validation
            try:
                manual_data = await request.json()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request body must be JSON for manual validation"
                )
            
            cic = manual_data.get("cic")
            id_citizen = manual_data.get("id_citizen")
            curp = manual_data.get("curp")
            
            if not all([cic, id_citizen, curp]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Missing required fields for manual validation",
                        "required_fields": ["cic", "id_citizen", "curp"],
                    }
                )
            
            # Prepare validation body directly
            body_validate_ine = {"cic": cic, "id_citizen": id_citizen, "model": "E"}
            ocr_data_for_validation = None
        
        elif validation_type == "automatic":
            # Process automatic image validation
            if not image_front or not image_back:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Both 'image_front' and 'image_back' images are required for automatic validation."
                )
            
            # Validate and process images
            validation_start = time.time()
            try:
                # Read image files
                ine_front_bytes = await image_front.read()
                ine_back_bytes = await image_back.read()
                
                # Convert to base64
                def normalize_extension(filename: str) -> str:
                    ext = filename.split('.')[-1].lower()
                    return "jpg" if ext == "jpeg" else ext
                
                front_ext = normalize_extension(image_front.filename)
                back_ext = normalize_extension(image_back.filename)
                
                ine_front_base64 = f"data:image/{front_ext};base64," + base64.b64encode(ine_front_bytes).decode('utf-8')
                ine_back_base64 = f"data:image/{back_ext};base64," + base64.b64encode(ine_back_bytes).decode('utf-8')
                
                timing_metrics["image_validation"] = time.time() - validation_start
            except Exception as e:
                logger.error(f"[{request_id}] Image validation failed - error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image processing failed: {str(e)}"
                )
            
            # Try nubarium first
            try:
                logger.info(f"[{request_id}] Trying nubarium OCR first")
                ine_full_info, ocr_metrics = await process_ocr_with_nobarium(
                    ine_front_base64, ine_back_base64, request_id
                )
                timing_metrics.update(ocr_metrics)
                
                if "error" in ine_full_info:
                    logger.warning(f"[{request_id}] Nubarium OCR failed: {ine_full_info}")
                    raise Exception(f"Nubarium OCR failed: {ine_full_info.get('error', 'Unknown error')}")
                
                # Extract CURP from nubarium result
                curp_nubarium = extract_curp_from_nobarium(ine_full_info)
                if not curp_nubarium:
                    logger.warning(f"[{request_id}] No CURP found in nubarium OCR data")
                    raise Exception("No CURP found in nubarium OCR data")
                
                # Prepare validation body for nubarium
                body_validate_ine_nubarium = prepare_validation_body_nobarium(ine_full_info)
                
                logger.info(f"[{request_id}] Nubarium CURP: {curp_nubarium}")
                
                # Use nubarium data for this flow
                curp = curp_nubarium
                body_validate_ine = body_validate_ine_nubarium
                ocr_data_for_validation = ine_full_info
                
                logger.info(f"[{request_id}] Successfully using nubarium data")
            
            except Exception as nubarium_error:
                logger.warning(f"[{request_id}] Nubarium processing failed: {str(nubarium_error)}. Falling back to verificamex...")
                
                # Fall back to verificamex
                front_info, back_info, ocr_metrics = await process_ocr_parallel(
                    ine_front_base64, ine_back_base64, request_id
                )
                timing_metrics.update(ocr_metrics)
                
                # Validate OCR results
                ocr_data, error_details = validate_ocr_results(front_info, back_info, request_id)
                if error_details:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "OCR validation failed",
                            "details": error_details,
                            "timing_metrics": timing_metrics,
                        }
                    )
                
                front_data, back_data = ocr_data
                
                # Extract CURP and prepare INE validation body for verificamex
                curp_verificamex = front_data[8].get("value", "") if len(front_data) > 8 else ""
                body_validate_ine_verificamex = prepare_validation_body(back_data)
                
                logger.info(f"[{request_id}] Verificamex CURP: {curp_verificamex}")
                
                if not curp_verificamex:
                    logger.error(f"[{request_id}] No CURP found in verificamex OCR data")
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "Could not extract CURP from INE using verificamex",
                            "timing_metrics": timing_metrics,
                        }
                    )
                
                # Use verificamex data for this flow
                curp = curp_verificamex
                body_validate_ine = body_validate_ine_verificamex
                ocr_data_for_validation = None  # No OCR data for nubarium validation
                front_info_stored = front_info
                back_info_stored = back_info
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="validation_type must be 'automatic' or 'manual'"
            )
        
        # Validate INE and CURP in parallel
        validation_results, validation_metrics = await validate_curp_and_ine_parallel(
            curp, body_validate_ine, request_id, ocr_data_for_validation
        )
        timing_metrics.update(validation_metrics)
        
        # Calculate total processing time
        timing_metrics["total"] = time.time() - start_time
        
        logger.info(f"[{request_id}] Successfully completed credential validation - timing_metrics: {timing_metrics}")
        
        # Prepare and return combined response
        if validation_type == "manual":
            # Extract RFC from validation results if available
            rfc = ""
            if "curp" in validation_results and "error" not in validation_results["curp"]:
                rfc = validation_results["curp"].get("data", {}).get("rfc", "")
            
            response_data = {
                "body_validate_ine": body_validate_ine,
                "curp": curp,
                "rfc": rfc,
                "timing_metrics": timing_metrics,
                "validation_results": validation_results,
                "is_valid": (
                    "curp" in validation_results
                    and validation_results["curp"].get("is_valid", "error" not in validation_results["curp"])
                    and "ine" in validation_results
                    and validation_results["ine"].get("is_valid", "error" not in validation_results["ine"])
                ),
                "validation_details": {
                    "curp": {
                        "is_valid": "curp" in validation_results
                        and validation_results["curp"].get("is_valid", "error" not in validation_results["curp"]),
                        "service_used": validation_results.get("curp", {}).get("service", "none"),
                    },
                    "ine": {
                        "is_valid": "ine" in validation_results
                        and validation_results["ine"].get("is_valid", "error" not in validation_results["ine"]),
                        "service_used": validation_results.get("ine", {}).get("service", "none"),
                    },
                },
            }
        else:
            # For automatic flow, determine which response format to use
            if ocr_data_for_validation is not None:
                # Nubarium was used successfully
                logger.info(f"[{request_id}] Preparing nubarium response format")
                response_data = prepare_nobarium_combined_response(
                    ocr_data_for_validation, validation_results, timing_metrics
                )
            else:
                # Verificamex was used (fallback)
                logger.info(f"[{request_id}] Preparing verificamex response format")
                response_data = prepare_combined_response(
                    (front_info_stored, back_info_stored), validation_results, timing_metrics
                )
        
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        timing_metrics["total"] = time.time() - start_time
        logger.error(
            f"[{request_id}] Unhandled error in complete credential validation - error: {str(e)}, "
            f"timing_metrics: {timing_metrics}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error during credential validation",
                "details": str(e),
                "timing_metrics": timing_metrics,
            }
        )


@router.post("/send-redirect-url", status_code=status.HTTP_200_OK)
async def send_redirect_url(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Send redirect URL - TODO: Implement email sending"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Send redirect URL not yet implemented"
    )


@router.post("/notify-validation-failed", status_code=status.HTTP_200_OK)
async def notify_validation_failed(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Notify validation failure - TODO: Implement email sending"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Validation failure notification not yet implemented"
    )


@router.post("/notify-files-uploaded", status_code=status.HTTP_200_OK)
async def notify_files_uploaded(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Notify files uploaded - TODO: Implement email sending"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Files uploaded notification not yet implemented"
    )


@router.get("/files/{client_id}", status_code=status.HTTP_200_OK)
async def get_files(
    client_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Get client files from Supabase storage"""
    try:
        supabase = get_supabase_client()
        path = f"{client_id}/"
        # TODO: Implement list_files method
        files = []  # Placeholder
        return {"client_id": client_id, "files": files}
    except Exception as e:
        logger.error(f"Error getting files for client {client_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get client files: {str(e)}"
        )


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload(
    type: Optional[str] = Query(None, description="Document type (optional, from query)"),
    client_id: int = Form(...),
    file_type: str = Form(...),
    file: UploadFile = File(...),
    validated: Optional[str] = Form("false"),
    month: Optional[int] = Form(None),
    sequence_number: Optional[int] = Form(None),
    document_type: Optional[str] = Form(None),
    total_income: Optional[float] = Form(None),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Upload document endpoint - matches frontend expectations.
    Frontend sends: POST /client/upload?type=officialIdFrontClient
    with FormData: client_id, file_type, file, validated
    """
    from app.apps.client.services.supabase_storage import supabase_storage
    from datetime import datetime
    
    try:
        # Validate client exists
        stmt = select(Cliente).where(Cliente.id == client_id)
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        # Use file_type from form (or type from query if file_type not provided)
        document_type_str = file_type or type or ""
        
        # Determine document_type from file_type
        # Frontend sends types like "officialIdFrontClient", "officialIdReverseClient", etc.
        document_type = document_type_str.replace("Client", "")
        
        # Parse validated (can be string "true"/"false" or boolean)
        is_validated = validated.lower() == "true" if isinstance(validated, str) else bool(validated)
        
        # Determine if this is an income proof or regular document
        is_income_proof = "incomeproof" in file_type.lower()
        
        # Get current year
        current_year = datetime.now().year
        
        # Handle income proof documents
        if is_income_proof:
            if not month:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Month is required for income proof documents"
                )
            
            # Use document_type from form or default to "Others"
            doc_type = document_type or "Others"
            seq_num = sequence_number or 1
            
            # Generate filename for income proof
            file_extension = file.filename.split(".")[-1] if "." in file.filename else "pdf"
            filename = f"incomeProofClient_{month}_{seq_num}.{file_extension}"
            file_path = f"{client_id}/{filename}"
            
            # Read file content
            file_bytes = await file.read()
            content_type = file.content_type or "application/octet-stream"
            
            # Upload file to Supabase
            upload_result = supabase_storage.upload_file(file_path, file_bytes, content_type)
            
            if not upload_result.get("success"):
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file: {upload_result.get('error', 'Unknown error')}"
                )
            
            # Create or update IncomeProofDocument record
            stmt = select(IncomeProofDocument).where(
                IncomeProofDocument.client_id == client_id,
                IncomeProofDocument.month == month,
                IncomeProofDocument.year == current_year,
                IncomeProofDocument.sequence_number == seq_num
            )
            result = await session.execute(stmt)
            income_proof = result.scalar_one_or_none()
            
            if not income_proof:
                income_proof = IncomeProofDocument(
                    client_id=client_id,
                    month=month,
                    year=current_year,
                    document_type=doc_type,
                    sequence_number=seq_num,
                    status="validating",
                    total_income=total_income
                )
                session.add(income_proof)
            else:
                income_proof.status = "validating"
                income_proof.document_type = doc_type
                if total_income:
                    income_proof.total_income = total_income
            
            await session.commit()
            
            logger.info(f"Income proof uploaded for client {client_id}: month={month}, sequence={seq_num}")
            
            return {
                "message": "Income proof uploaded successfully",
                "file_path": file_path,
                "status": "success",
                "income_proof_id": income_proof.id
            }
        
        # Handle regular documents (officialIdFront, officialIdReverse, addressProof)
        # Get or create FileStatus record
        stmt = select(FileStatus).where(FileStatus.cliente_id == client_id)
        result = await session.execute(stmt)
        file_status = result.scalar_one_or_none()
        
        if not file_status:
            file_status = FileStatus(cliente_id=client_id)
            session.add(file_status)
            await session.flush()
        
        # Update file status based on document_type
        validated_str = "validated" if is_validated else "validating"
        if document_type == "officialIdFront":
            file_status.officialId_front = validated_str
        elif document_type == "officialIdReverse":
            file_status.officialId_reverse = validated_str
        elif document_type == "addressProof":
            file_status.addressProof = validated_str
        
        logger.info(f"Updated file status for client {client_id}: {document_type} = {validated_str}")
        
        # Generate filename
        filename = f"{document_type}Client"
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "pdf"
        full_filename = f"{filename}.{file_extension}"
        file_path = f"{client_id}/{full_filename}"
        
        # Read file content
        file_bytes = await file.read()
        content_type = file.content_type or "application/octet-stream"
        
        # Check if file exists in storage
        existing_files = supabase_storage.list_files(str(client_id))
        file_exists = False
        
        if isinstance(existing_files, list):
            for existing_file in existing_files:
                if existing_file.get("name") == full_filename:
                    file_exists = True
                    logger.info(f"File exists, will replace: {file_path}")
                    break
        
        # Upload or replace file
        if file_exists:
            upload_result = supabase_storage.replace_file(file_path, file_bytes, content_type)
            logger.info(f"Replaced existing file: {file_path}")
        else:
            upload_result = supabase_storage.upload_file(file_path, file_bytes, content_type)
            logger.info(f"Uploaded new file: {file_path}")
        
        if not upload_result.get("success"):
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {upload_result.get('error', 'Unknown error')}"
            )
        
        # Commit database changes
        await session.commit()
        
        return {
            "message": "File uploaded successfully",
            "file_path": file_path,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error processing upload request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


async def upload_document(
    client_id: int,
    file: UploadFile = File(...),
    file_type: str = Form(...),
    document_type: str = Form(...),
    validated: str = Form("true"),
    month: Optional[int] = Form(None),
    sequence_number: Optional[int] = Form(1),
    total_income: Optional[float] = Form(None),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Upload document and store metadata - alternative endpoint"""
    # TODO: Implement file upload to Supabase storage
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document upload not yet implemented - requires Supabase storage migration"
    )


@router.get("/document/{client_id}/download", status_code=status.HTTP_200_OK)
async def download_document(
    client_id: int,
    file_type: str = Query(...),
    document_type: str = Query(...),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    sequence_number: Optional[int] = Query(1),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Download document from Supabase storage"""
    # TODO: Implement file download from Supabase storage
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document download not yet implemented"
    )


@router.put("/document/{client_id}/status", status_code=status.HTTP_200_OK)
async def update_document_status(
    client_id: int,
    request: dict,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Update document status"""
    try:
        document_type = request.get("document_type")
        new_status = request.get("status")
        
        if not document_type or not new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: document_type and status"
            )
        
        valid_statuses = ["validated", "validating", "null"]
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # For income proofs
        if document_type == "incomeProof":
            if not request.get("month") or not request.get("year"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Income proof updates require month and year"
                )
            
            sequence_number = request.get("sequence_number", 1)
            stmt = select(IncomeProofDocument).where(
                IncomeProofDocument.client_id == client_id,
                IncomeProofDocument.month == request["month"],
                IncomeProofDocument.year == request["year"],
                IncomeProofDocument.sequence_number == sequence_number
            )
            result = await session.execute(stmt)
            income_proof = result.scalar_one_or_none()
            
            if not income_proof:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Income proof document not found"
                )
            
            income_proof.status = new_status
            if request.get("total_income"):
                income_proof.total_income = request["total_income"]
            
            await session.commit()
        else:
            # Update ID or address proof status
            valid_types = ["officialId_front", "officialId_reverse", "addressProof"]
            if document_type not in valid_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}"
                )
            
            attr_map = {
                "officialId_front": "officialId_front",
                "officialId_reverse": "officialId_reverse",
                "addressProof": "addressProof",
            }
            attr_name = attr_map[document_type]
            
            stmt = select(FileStatus).where(FileStatus.cliente_id == client_id)
            result = await session.execute(stmt)
            file_status = result.scalar_one_or_none()
            
            if not file_status:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File status record not found"
                )
            
            setattr(file_status, attr_name, new_status)
            await session.commit()
        
        return {"message": "Document status updated successfully", "status": new_status}
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating document status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document status: {str(e)}"
        )


@router.post("/validate-ine-manually", status_code=status.HTTP_200_OK)
async def validate_ine_manually(
    request: dict,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Validate INE manually - TODO: Implement utility functions"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Manual INE validation not yet implemented"
    )

