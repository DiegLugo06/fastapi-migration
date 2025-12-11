"""
Product router
Migrated from Flask app/product/routes.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional, List
import logging
import asyncio
from datetime import datetime

from app.database import get_async_session
from app.apps.authentication.dependencies import get_current_user
from app.apps.product.models import Motorcycles, MotorcycleBrand, Discounts
from app.apps.product.schemas import (
    MotorcycleResponse,
    GetMotorcycleModelsResponse,
    DiscountCreate,
    DiscountResponse,
    CreateDiscountResponse,
)
from app.apps.product.utils.decryption_functions import generate_hash
from app.config import MODE

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/motorcycle_models", response_model=GetMotorcycleModelsResponse, status_code=status.HTTP_200_OK)
async def get_motorcycle_models(
    user_id: Optional[int] = Query(None),
    holding: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)  # Require API key or JWT token for security
):
    """
    Get motorcycle models with optional filtering by user and holding.
    """
    try:
        # Determine allowed motorcycle IDs for Sfera holding
        allowed_motorcycle_ids = None
        if holding == "Sfera":
            is_development = MODE == "development"
            
            if is_development:
                allowed_motorcycle_ids = [2]
            else:
                allowed_motorcycle_ids = [2]
            
            logger.info(f"Filtering motorcycles for Sfera holding: {allowed_motorcycle_ids}")
        
        # Initialize variables
        rows = None
        motorcycles = []
        
        # If user_id is provided, filter by user's available brands
        if user_id and user_id != 6:
            try:
                # Query to get motorcycles filtered by user's sucursal brands
                stmt = text("""
                    SELECT DISTINCT m.id, m.brand_id, m.model, m.inner_brand_model, 
                           m.year, m.price, m.color, m.active, m.review_video_url,
                           mb.name as brand_name
                    FROM motorcycles m
                    INNER JOIN motorcycle_brands mb ON m.brand_id = mb.id
                    INNER JOIN sucursales s ON m.brand_id = s.brand_id
                    INNER JOIN user_sucursales us ON s.id = us.sucursal_id
                    WHERE us.user_id = :user_id
                    AND m.active = TRUE
                """)
                
                if allowed_motorcycle_ids:
                    stmt = text("""
                        SELECT DISTINCT m.id, m.brand_id, m.model, m.inner_brand_model, 
                               m.year, m.price, m.color, m.active, m.review_video_url,
                               mb.name as brand_name
                        FROM motorcycles m
                        INNER JOIN motorcycle_brands mb ON m.brand_id = mb.id
                        INNER JOIN sucursales s ON m.brand_id = s.brand_id
                        INNER JOIN user_sucursales us ON s.id = us.sucursal_id
                        WHERE us.user_id = :user_id
                        AND m.active = TRUE
                        AND m.id = ANY(:allowed_ids)
                    """)
                    result = await session.execute(stmt, {
                        "user_id": user_id,
                        "allowed_ids": allowed_motorcycle_ids
                    })
                else:
                    result = await session.execute(stmt, {"user_id": user_id})
                
                rows = result.fetchall()
                
            except Exception as filter_error:
                logger.warning(f"Error filtering models by user stores (table may not exist in test DB): {str(filter_error)}")
                # OPTIMIZATION: Fallback with JOIN to avoid N+1 queries
                if allowed_motorcycle_ids:
                    stmt = text("""
                        SELECT DISTINCT m.id, m.brand_id, m.model, m.inner_brand_model, 
                               m.year, m.price, m.color, m.active, m.review_video_url,
                               mb.name as brand_name
                        FROM motorcycles m
                        INNER JOIN motorcycle_brands mb ON m.brand_id = mb.id
                        WHERE m.active = TRUE
                        AND m.id = ANY(:allowed_ids)
                    """)
                    result = await session.execute(stmt, {"allowed_ids": allowed_motorcycle_ids})
                    rows = result.fetchall()
                else:
                    stmt = text("""
                        SELECT DISTINCT m.id, m.brand_id, m.model, m.inner_brand_model, 
                               m.year, m.price, m.color, m.active, m.review_video_url,
                               mb.name as brand_name
                        FROM motorcycles m
                        INNER JOIN motorcycle_brands mb ON m.brand_id = mb.id
                        WHERE m.active = TRUE
                    """)
                    result = await session.execute(stmt)
                    rows = result.fetchall()
        else:
            # OPTIMIZATION: Use JOIN to get brands in one query instead of N+1
            # No user_id provided, apply holding filter if needed
            if allowed_motorcycle_ids:
                # Use JOIN query to get motorcycles with brands in one go
                stmt = text("""
                    SELECT DISTINCT m.id, m.brand_id, m.model, m.inner_brand_model, 
                           m.year, m.price, m.color, m.active, m.review_video_url,
                           mb.name as brand_name
                    FROM motorcycles m
                    INNER JOIN motorcycle_brands mb ON m.brand_id = mb.id
                    WHERE m.active = TRUE
                    AND m.id = ANY(:allowed_ids)
                """)
                result = await session.execute(stmt, {"allowed_ids": allowed_motorcycle_ids})
                rows = result.fetchall()
            else:
                # Use JOIN query to get motorcycles with brands in one go
                stmt = text("""
                    SELECT DISTINCT m.id, m.brand_id, m.model, m.inner_brand_model, 
                           m.year, m.price, m.color, m.active, m.review_video_url,
                           mb.name as brand_name
                    FROM motorcycles m
                    INNER JOIN motorcycle_brands mb ON m.brand_id = mb.id
                    WHERE m.active = TRUE
                """)
                result = await session.execute(stmt)
                rows = result.fetchall()
        
        # OPTIMIZATION: Serialize models from rows (all data already fetched)
        if rows:
            models_data = [
                MotorcycleResponse(
                    id=row[0],
                    brand_id=row[1],
                    brand=row[9],  # brand_name from JOIN
                    model=row[2],
                    inner_brand_model=row[3],
                    year=row[4],
                    price=row[5],
                    color=row[6],
                    active=row[7],
                    review_video_url=row[8],
                )
                for row in rows
            ]
        else:
            # Fallback: if rows is None (shouldn't happen with optimized queries)
            # Batch fetch all brands at once instead of N+1 queries
            if motorcycles:
                # Get all unique brand_ids
                brand_ids = list(set(m.brand_id for m in motorcycles))
                
                # Fetch all brands in one query
                stmt = select(MotorcycleBrand).where(MotorcycleBrand.id.in_(brand_ids))
                result = await session.execute(stmt)
                brands = {brand.id: brand for brand in result.scalars().all()}
                
                # Build response using brand lookup
                models_data = [
                    MotorcycleResponse(
                        id=motorcycle.id,
                        brand_id=motorcycle.brand_id,
                        brand=brands.get(motorcycle.brand_id).name if brands.get(motorcycle.brand_id) else None,
                        model=motorcycle.model,
                        inner_brand_model=motorcycle.inner_brand_model,
                        year=motorcycle.year,
                        price=motorcycle.price,
                        color=motorcycle.color,
                        active=motorcycle.active,
                        review_video_url=motorcycle.review_video_url,
                    )
                    for motorcycle in motorcycles
                ]
            else:
                models_data = []
        
        if models_data:
            return GetMotorcycleModelsResponse(models=models_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Models not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error in get_motorcycle_models: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error. Please try again later."
        )


@router.post("/create_discount", response_model=CreateDiscountResponse, status_code=status.HTTP_201_CREATED)
async def create_discount(
    request: DiscountCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Create a discount for a motorcycle.
    """
    try:
        # Validate request data
        if not request.motorcycle_id or not request.user_id:
            missing_fields = []
            if not request.motorcycle_id:
                missing_fields.append("motorcycle_id")
            if not request.user_id:
                missing_fields.append("user_id")
            
            logger.warning(f"Missing required fields: {missing_fields}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {missing_fields}"
            )
        
        # Ensure motorcycle exists
        stmt = select(Motorcycles).where(Motorcycles.id == request.motorcycle_id)
        result = await session.execute(stmt)
        motorcycle = result.scalar_one_or_none()
        
        if not motorcycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Motorcycle not found"
            )
        
        # Ensure user exists
        from app.apps.authentication.models import User
        stmt = select(User).where(User.id == request.user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate required fields
        if not all([request.description, request.discount_type, request.discount_value, request.motorcycle_id]):
            discount_hash = generate_hash(request.motorcycle_id, 0, request.user_id)
            return CreateDiscountResponse(
                message="Hash generated",
                discount_id=0,
                motorcycle_id=request.motorcycle_id,
                hash=discount_hash
            )
        
        # Create the discount record
        discount = Discounts(
            description=request.description,
            type=request.discount_type,
            value=request.discount_value,
            start_date=request.start_date or datetime.now(),
            end_date=request.end_date,
        )
        session.add(discount)
        await session.flush()  # Get the ID
        
        # Generate a hash combining motorcycle_id and discount_id
        discount_hash = generate_hash(request.motorcycle_id, discount.id, request.user_id)
        
        await session.commit()
        
        return CreateDiscountResponse(
            message="Discount created successfully",
            discount_id=discount.id,
            motorcycle_id=request.motorcycle_id,
            hash=discount_hash
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating discount: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the discount: {str(e)}"
        )

