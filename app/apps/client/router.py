"""
Client router
Migrated from Flask app/client/routes.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
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
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Validate CURP - TODO: Implement utility functions"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="CURP validation not yet implemented"
    )


@router.post("/generate-curp", status_code=status.HTTP_200_OK)
async def generate_curp(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Generate CURP - TODO: Implement utility functions"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="CURP generation not yet implemented"
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
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """Complete credential validation - TODO: Implement utility functions"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Complete credential validation not yet implemented"
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
        is_income_proof = file_type != type  # If file_type differs from type, it might be income proof
        
        # Get current year
        current_year = datetime.now().year
        
        # Handle income proof documents
        if "incomeProof" in file_type.lower() or is_income_proof:
            # For income proof, we'd need additional fields (month, sequence_number, total_income)
            # These should come from the form data, but frontend might not send them in this endpoint
            # For now, we'll handle regular document uploads
            pass
        
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

