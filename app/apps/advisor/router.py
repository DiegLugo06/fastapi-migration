"""
Advisor router
Migrated from Flask app/advisor/routes.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from uuid import UUID
import logging
from typing import Optional, List

from app.database import get_async_session
from app.apps.authentication.models import User
from app.apps.authentication.dependencies import get_current_user
from app.apps.advisor.models import Sucursal, Role
from app.apps.product.models import MotorcycleBrand
from app.apps.quote.models import Banco
from app.apps.advisor.schemas import (
    UserResponse,
    GetStoresResponse,
    StoreData,
    AdvisorResponse,
    UserUpdateRequest,
    AdvisorDetailsResponse,
    CreateSucursalRequest,
)
from app.apps.advisor.utils._format_advisor_response import _format_advisor_response
from app.apps.advisor.utils._get_next_advisor import (
    _get_next_advisor_by_rotation_logic,
    _get_next_advisor_by_holding_logic,
    _get_next_finva_advisor,
)
from app.apps.advisor.utils._fetch_user import _fetch_user
from app.apps.advisor.utils._fetch_store import _fetch_sucursal
from app.apps.advisor.utils._fetch_banks import _fetch_banks_for_sucursal
from app.apps.authentication.utils import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/get_user", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_user(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Endpoint to get the user information from Supabase.
    """
    logger.info("Attempting to get user information")
    try:
        supabase = get_supabase_client()
        
        # Get user from current_user (already authenticated)
        logger.info("User information retrieved successfully")
        return UserResponse(
            status="success",
            user_email=current_user.email,
            user_id=current_user.id,
            role_id=current_user.role_id,
        )
    except Exception as e:
        logger.error(f"Error getting user information: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error: {str(e)}"
        )


@router.get("/get_stores", response_model=GetStoresResponse, status_code=status.HTTP_200_OK)
async def get_stores(
    holding: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    credit_card_payment_method: Optional[str] = Query(None),
    active: Optional[bool] = Query(True),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint to get stores with flexible filtering.
    Query Parameters:
        Any field from Sucursal model can be used as a filter.
        For 'brand' parameter: accepts brand name (converts to brand_id)
        For string fields: performs case-insensitive partial matching
        For boolean fields: accepts 'true'/'false' (case-insensitive)
        For 'holding' parameter: if set to 'ferbel_group', filters stores to only Ferbel Norte SA de CV or Comercializadora Promotodo SA de CV
        Multiple filters are combined with AND logic
    """
    logger.info("Attempting to get stores with filters")
    try:
        # Create mutable copy of query params
        filter_params = {}
        
        # Always filter for active stores only
        query = select(Sucursal).where(Sucursal.active == True)
        
        # Apply holding filter if specified
        if holding in ["Ferbel", "Sfera"]:
            query = query.where(
                Sucursal.razon_social.in_(
                    ["Ferbel Norte SA de CV", "Comercializadora Promotodo SA de CV"]
                )
            )
            filter_params["holding"] = holding
        
        # Handle brand filter
        if brand:
            # Get brand_id from brand name
            brand_stmt = select(MotorcycleBrand).where(
                func.lower(MotorcycleBrand.name) == func.lower(brand.strip())
            )
            brand_result = await session.execute(brand_stmt)
            brand_obj = brand_result.scalar_one_or_none()
            if brand_obj:
                query = query.where(Sucursal.brand_id == brand_obj.id)
                filter_params["brand"] = brand
        
        # Handle credit_card_payment_method filter
        if credit_card_payment_method:
            is_true = credit_card_payment_method.lower() == "true"
            query = query.where(Sucursal.credit_card_payment_method == is_true)
            filter_params["credit_card_payment_method"] = credit_card_payment_method
        
        # Execute query
        result = await session.execute(query)
        stores = result.scalars().all()
        logger.info(f"Query returned {len(stores)} stores")
        
        # Serialize results
        stores_data = []
        for store in stores:
            # Get brand name
            brand_stmt = select(MotorcycleBrand).where(MotorcycleBrand.id == store.brand_id)
            brand_result = await session.execute(brand_stmt)
            brand = brand_result.scalar_one_or_none()
            
            store_data = StoreData(
                id=store.id,
                nombre=store.nombre,
                brand_id=store.brand_id,
                brand_name=brand.name if brand else None,
                ubicacion=store.ubicacion,
                razon_social=store.razon_social,
                credit_card_payment_method=store.credit_card_payment_method,
                crm_sync=store.crm_sync,
                zip_code=store.zip_code,
                active=store.active,
                coordinates=store.coordinates,
            )
            stores_data.append(store_data)
        
        response_data = {
            "status": "success",
            "stores_data": stores_data,
            "filters_applied": filter_params,
            "count": len(stores),
        }
        
        if holding:
            response_data["holding_filter"] = holding
        
        return GetStoresResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Error getting stores: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An error occurred while fetching stores"
        )


@router.put("/update_user", response_model=AdvisorResponse, status_code=status.HTTP_200_OK)
async def update_user(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Endpoint to update an User's information.
    """
    logger.info("Attempting to update User information")
    try:
        # Update user fields
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_user, field, value)
        
        await session.commit()
        
        logger.info(f"User updated successfully, UUID: {current_user.uuid}")
        return AdvisorResponse(
            id=current_user.id,
            uuid=str(current_user.uuid),
            name=current_user.name,
            second_name=current_user.second_name,
            first_last_name=current_user.first_last_name,
            second_last_name=current_user.second_last_name,
            email=current_user.email,
            zona_autoestrena_url=current_user.zona_autoestrena_url,
            selected_at=current_user.last_selected_at.isoformat() if current_user.last_selected_at else None,
            role_id=current_user.role_id,
            phone_number=current_user.phone_number,
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error while updating User: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the User: {str(e)}"
        )


@router.get("/get_advisor_details/{advisor_id}", response_model=AdvisorDetailsResponse, status_code=status.HTTP_200_OK)
async def get_advisor_details(
    advisor_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint to get the user information from Supabase.
    Returns stores with brand_name instead of brand_id.
    """
    logger.info("Attempting to get user information")
    try:
        stmt = select(User).where(User.id == advisor_id)
        result = await session.execute(stmt)
        advisor = result.scalar_one_or_none()
        
        if not advisor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Advisor not found"
            )
        
        # Get all razon_social values for sucursales assigned to this advisor
        stmt = text("""
            SELECT s.razon_social
            FROM sucursales s
            INNER JOIN user_sucursales us ON s.id = us.sucursal_id
            WHERE us.user_id = :user_id
        """)
        result = await session.execute(stmt, {"user_id": advisor.id})
        razon_socials = [row[0] for row in result.fetchall()]
        
        # Condition for advisor to see both razon_social stores if one of them is in the list
        if (
            "Ferbel Norte SA de CV" in razon_socials
            or "Comercializadora Promotodo SA de CV" in razon_socials
        ):
            # Get all stores from both companies
            stmt = text("""
                SELECT id FROM sucursales
                WHERE razon_social IN ('Ferbel Norte SA de CV', 'Comercializadora Promotodo SA de CV')
            """)
            result = await session.execute(stmt)
            sucursal_ids = [row[0] for row in result.fetchall()]
        else:
            # Get stores assigned to this advisor
            stmt = text("""
                SELECT s.id
                FROM sucursales s
                INNER JOIN user_sucursales us ON s.id = us.sucursal_id
                WHERE us.user_id = :user_id
            """)
            result = await session.execute(stmt, {"user_id": advisor.id})
            sucursal_ids = [row[0] for row in result.fetchall()]
        
        # Query stores with brand information
        if sucursal_ids:
            stmt = text("""
                SELECT s.id, s.nombre, mb.name as brand_name, s.ubicacion, 
                       s.razon_social, s.credit_card_payment_method, s.crm_sync, s.zip_code
                FROM sucursales s
                INNER JOIN motorcycle_brands mb ON s.brand_id = mb.id
                WHERE s.id = ANY(:sucursal_ids)
            """)
            result = await session.execute(stmt, {"sucursal_ids": sucursal_ids})
            stores_rows = result.fetchall()
        else:
            stores_rows = []
        
        # Convert to dictionary format
        stores_data = [
            StoreData(
                id=store[0],
                nombre=store[1],
                brand_id=0,  # Not available in query
                brand_name=store[2],
                ubicacion=store[3],
                razon_social=store[4],
                credit_card_payment_method=store[5],
                crm_sync=store[6],
                zip_code=store[7],
                active=True,  # Default
                coordinates=None,
            )
            for store in stores_rows
        ]
        
        # Format advisor data
        advisor_data = {
            "id": advisor.id,
            "uuid": str(advisor.uuid),
            "name": advisor.name,
            "second_name": advisor.second_name,
            "first_last_name": advisor.first_last_name,
            "second_last_name": advisor.second_last_name,
            "email": advisor.email,
            "phone_number": advisor.phone_number,
            "role_id": advisor.role_id,
            "is_active": advisor.is_active,
            "zona_autoestrena_url": advisor.zona_autoestrena_url,
        }
        
        return AdvisorDetailsResponse(
            status="success",
            advisor=advisor_data,
            stores=stores_data,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user information: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An error occurred while fetching advisor details: {str(e)}"
        )


@router.post("/sucursales", status_code=status.HTTP_201_CREATED)
async def create_sucursal(
    request: CreateSucursalRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint to create a new Sucursal and associate it with Banco entities.
    """
    try:
        logger.info("Starting creation of a new Sucursal.")
        
        # Create the Sucursal object
        sucursal = Sucursal(
            nombre=request.nombre,
            ubicacion=request.ubicacion,
            razon_social=request.razon_social,
            credit_card_payment_method=request.credit_card_payment_method,
            crm_sync=request.crm_sync,
            zip_code=request.zip_code,
            brand_id=1,  # Default, should be set from marca if provided
            active=True,
        )
        
        session.add(sucursal)
        await session.flush()  # Get the ID
        
        logger.info("Sucursal object created and added to the session.")
        
        # Associate the Sucursal with Bancos
        if request.banco_ids:
            for banco_id in request.banco_ids:
                stmt = select(Banco).where(Banco.id == banco_id)
                result = await session.execute(stmt)
                banco = result.scalar_one_or_none()
                if banco:
                    # Insert into association table
                    stmt = text("""
                        INSERT INTO bancos_sucursal (banco_id, sucursal_id)
                        VALUES (:banco_id, :sucursal_id)
                        ON CONFLICT DO NOTHING
                    """)
                    await session.execute(stmt, {
                        "banco_id": banco_id,
                        "sucursal_id": sucursal.id
                    })
                    logger.info(f"Associated Sucursal with Banco ID: {banco_id}")
        
        await session.commit()
        logger.info("Sucursal and Banco associations successfully committed to the database.")
        
        # Return sucursal data
        return {
            "id": sucursal.id,
            "nombre": sucursal.nombre,
            "ubicacion": sucursal.ubicacion,
            "razon_social": sucursal.razon_social,
            "credit_card_payment_method": sucursal.credit_card_payment_method,
            "crm_sync": sucursal.crm_sync,
            "zip_code": sucursal.zip_code,
            "active": sucursal.active,
        }
        
    except Exception as e:
        await session.rollback()
        logger.error(f"An error occurred while creating the Sucursal: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while creating the Sucursal."
        )


@router.get("/get_next_user", response_model=AdvisorResponse, status_code=status.HTTP_200_OK)
async def get_next_user(
    store_id: int = Query(...),
    client_email: str = Query(...),
    client_phone: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get the next available advisor for a store based on rotation logic.
    If a client has a recent application (within 6 months), returns their previous advisor.
    
    Query Parameters:
        store_id (int): ID of the store to get advisor for
        client_email (str): Email of the client
        client_phone (str): Phone number of the client
    
    Returns:
        JSON response with advisor details or error message
    """
    try:
        logger.info("Starting get_next_user request processing")
        
        # Check for existing client and recent application
        logger.info(f"Searching for client with email: {client_email} and phone: {client_phone}")
        stmt = text("""
            SELECT id FROM clientes 
            WHERE email = :email AND phone = :phone
            LIMIT 1
        """)
        result = await session.execute(stmt, {"email": client_email, "phone": client_phone})
        row = result.fetchone()
        
        if row:
            client_id = row[0]
            logger.info(f"Found existing client with ID: {client_id}")
            # Get most recent application within 6 months
            stmt = text("""
                SELECT user_id FROM solicitudes
                WHERE cliente_id = :client_id
                AND created_at > NOW() - INTERVAL '180 days'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = await session.execute(stmt, {"client_id": client_id})
            row = result.fetchone()
            
            if row and row[0]:
                advisor_id = row[0]
                logger.info(f"Found recent solicitud with advisor ID: {advisor_id}")
                stmt = select(User).where(User.id == advisor_id)
                result = await session.execute(stmt)
                advisor = result.scalar_one_or_none()
                
                if advisor:
                    # Validate that the advisor has a relationship with the requested store
                    stmt = text("""
                        SELECT sucursal_id FROM user_sucursales
                        WHERE user_id = :user_id AND sucursal_id = :store_id
                    """)
                    result = await session.execute(stmt, {"user_id": advisor.id, "store_id": store_id})
                    row = result.fetchone()
                    
                    if row:
                        logger.info(
                            f"Returning previous advisor (ID: {advisor.id}) for existing client. "
                            f"Verified relationship with store {store_id}"
                        )
                        return _format_advisor_response(advisor)
                    else:
                        logger.warning(
                            f"Previous advisor (ID: {advisor.id}) does not have relationship with store {store_id}. "
                            f"Proceeding with rotation logic"
                        )
        
        # Get store advisors and current selection
        logger.info(f"Fetching advisors for store ID: {store_id}")
        
        # Get the role id of salesman
        stmt = select(Role).where(Role.name == "salesman")
        result = await session.execute(stmt)
        role = result.scalar_one_or_none()
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salesman role not found"
            )
        
        salesman_role = role.id
        logger.info(f"Salesman role ID: {salesman_role}")
        
        # Build query for store advisors using raw SQL
        # Note: We'll use the rotation logic function which handles the query properly
        # For now, create a base query that will be filtered in the utility function
        store_query = select(User).where(User.role_id == salesman_role)
        
        # Get advisors for this store
        # First get user IDs for this store
        stmt = text("""
            SELECT user_id FROM user_sucursales
            WHERE sucursal_id = :store_id
        """)
        result = await session.execute(stmt, {"store_id": store_id})
        user_ids = [row[0] for row in result.fetchall()]
        
        if not user_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No advisors found for store {store_id}"
            )
        
        # Filter query by user IDs and role
        store_query = select(User).where(
            User.id.in_(user_ids),
            User.role_id == salesman_role
        )
        
        # Pass store_id to validate advisor relationship with store
        next_advisor, error = await _get_next_advisor_by_rotation_logic(
            store_query, "store", store_id, session
        )
        if error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        
        return _format_advisor_response(next_advisor)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_next_user: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )


@router.get("/get_next_finva_user", response_model=AdvisorResponse, status_code=status.HTTP_200_OK)
async def get_next_finva_user(
    client_id: Optional[int] = Query(None),
    holdingStore: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get the next available finva advisor based on rotation logic.
    Only considers users with the finva_agent role.
    If holdingStore is provided and equals "Sfera", uses holding-based logic with role 9.
    
    Query Parameters:
        client_id (int): Optional client ID to check for previous finva advisor assignment
        holdingStore (str): Optional holding name (e.g., "Sfera") to use holding-based logic
    
    Returns:
        JSON response with advisor details or error message
    """
    try:
        logger.info("Starting get_next_finva_user request processing")
        
        # If holdingStore is "Sfera", use holding-based logic
        if holdingStore == "Sfera":
            logger.info(f"Using holding-based logic for finva user with holding: {holdingStore}")
            
            # Check for existing client and recent application with Sfera finva_user_id
            if client_id:
                logger.info(f"Checking for recent solicitud with client_id: {client_id}")
                stmt = text("""
                    SELECT finva_user_id FROM solicitudes
                    WHERE cliente_id = :client_id
                    AND created_at > NOW() - INTERVAL '180 days'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = await session.execute(stmt, {"client_id": client_id})
                row = result.fetchone()
                
                if row and row[0]:
                    finva_user_id = row[0]
                    logger.info(f"Found recent solicitud with finva_user_id: {finva_user_id}")
                    stmt = select(User).where(
                        User.id == finva_user_id,
                        User.role_id == 9  # Verify it's a Sfera user
                    )
                    result = await session.execute(stmt)
                    finva_user = result.scalar_one_or_none()
                    
                    if finva_user:
                        logger.info(
                            f"Returning previous Sfera finva user (ID: {finva_user.id}) for existing client"
                        )
                        return _format_advisor_response(finva_user)
            
            # Get next Sfera advisor using holding-based logic
            next_advisor, error = await _get_next_advisor_by_holding_logic(holdingStore, session)
            if error:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error
                )
            return _format_advisor_response(next_advisor)
        
        # Get next finva advisor using standard finva_agent role logic
        next_advisor, error = await _get_next_finva_advisor(client_id, session)
        
        if error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        
        return _format_advisor_response(next_advisor)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_next_finva_user: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )


@router.get("/get_next_finva_agent_zae", response_model=AdvisorResponse, status_code=status.HTTP_200_OK)
async def get_next_finva_agent_zae(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get the next available finva agent zae based on rotation logic.
    """
    try:
        # Get finva agent zae role id
        stmt = select(Role).where(Role.name == "finva_agent_zae")
        result = await session.execute(stmt)
        role = result.scalar_one_or_none()
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finva agent zae role not found"
            )
        
        query = select(User).where(User.role_id == role.id)
        next_advisor, error = await _get_next_advisor_by_rotation_logic(
            query, "finva_agent_zae", None, session
        )
        if error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        
        return _format_advisor_response(next_advisor)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_next_finva_agent_zae: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )

