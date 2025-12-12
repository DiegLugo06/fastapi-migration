"""
CMS router for content management
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional, List
import logging
import json
import re
from datetime import datetime
from pathlib import Path

from app.database import get_async_session
from app.apps.authentication.dependencies import get_current_user
from app.apps.authentication.models import User
from app.apps.authentication.utils import get_supabase_client
from app.apps.cms.models import PageContent
from app.apps.cms.schemas import (
    PageContentCreate,
    PageContentUpdate,
    PageContentResponse,
    MarketplaceLandingResponse,
    MarketplaceLandingContent,
    SlideItem,
    MotorcycleCardItem,
    BankItem,
    ImageUploadResponse,
    MultipleImageUploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Image bucket name
IMAGE_BUCKET = "marketplace-assets"


def normalize_model_name_for_filename(model_name: str) -> str:
    """
    Normalize motorcycle model name to a safe filename.
    
    Examples:
    - "FZ-S 3.0" -> "fz-s-3.0"
    - "MT-07" -> "mt-07"
    - "CBR 650R" -> "cbr-650r"
    - "Ninja 650" -> "ninja-650"
    """
    if not model_name:
        return "unknown"
    
    # Convert to lowercase
    normalized = model_name.lower()
    
    # Replace spaces with hyphens
    normalized = normalized.replace(" ", "-")
    
    # Remove or replace special characters (keep alphanumeric, hyphens, dots, underscores)
    normalized = re.sub(r'[^a-z0-9\-\._]', '', normalized)
    
    # Replace multiple consecutive hyphens with single hyphen
    normalized = re.sub(r'-+', '-', normalized)
    
    # Remove leading/trailing hyphens or dots
    normalized = normalized.strip('-.')
    
    # If empty after normalization, use a fallback
    if not normalized:
        normalized = "unknown"
    
    return normalized


@router.get("/marketplace/content", response_model=MarketplaceLandingResponse, status_code=status.HTTP_200_OK)
async def get_marketplace_content_dynamic(
    brand_name: str = Query("Yamaha", description="Brand name for motorcycles"),
    motorcycle_limit: int = Query(6, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get complete marketplace landing page content with dynamic data from database.
    Combines CMS slides with database-fetched motorcycles and banks.
    """
    try:
        # Get slides from CMS (if they exist)
        stmt = select(PageContent).where(
            PageContent.page_key == "marketplace_landing",
            PageContent.is_active == True
        )
        result = await session.execute(stmt)
        page_content = result.scalar_one_or_none()
        
        slides = []
        if page_content:
            if isinstance(page_content.content, str):
                content_dict = json.loads(page_content.content)
            else:
                content_dict = page_content.content
            
            slides_data = content_dict.get("slides", [])
            slides = [SlideItem(**slide) for slide in slides_data]
        
        # If no slides in CMS, use defaults with Supabase URLs
        if not slides:
            from app.config import get_supabase_url
            supabase_url = get_supabase_url()
            url_without_protocol = supabase_url.replace("https://", "").replace("http://", "")
            project_id = url_without_protocol.split(".supabase.co")[0] if ".supabase.co" in url_without_protocol else url_without_protocol.split("/")[0]
            base_image_url = f"https://{project_id}.supabase.co/storage/v1/object/public/{IMAGE_BUCKET}"
            
            slides = [
                SlideItem(
                    title="Potencia en cada kilómetro",
                    image=f"{base_image_url}/landing1.webp"
                ),
                SlideItem(
                    title="Finva Motors",
                    image=f"{base_image_url}/her21.webp"
                )
            ]
        
        # Fetch motorcycles from database
        motorcycles_stmt = text("""
            SELECT m.id, m.model, m.price, m.color, m.year,
                   mb.name as brand_name
            FROM motorcycles m
            INNER JOIN motorcycle_brands mb ON m.brand_id = mb.id
            WHERE mb.name = :brand_name
            AND m.active = TRUE
            ORDER BY m.id
            LIMIT :limit
        """)
        
        motorcycles_result = await session.execute(motorcycles_stmt, {
            "brand_name": brand_name,
            "limit": motorcycle_limit
        })
        motorcycles_rows = motorcycles_result.fetchall()
        
        motorcycles = []
        for row in motorcycles_rows:
            # Get model name from database (row[1] is the model field)
            model_name = row[1]  # m.model
            
            # Normalize model name for filename
            normalized_model = normalize_model_name_for_filename(model_name)
            image_filename = f"{normalized_model}.jpg"
            
            # Get Supabase URL from config
            from app.config import get_supabase_url
            supabase_url = get_supabase_url()
            # Extract project ID from URL (format: https://xxxxx.supabase.co)
            # Remove protocol and extract project ID
            url_without_protocol = supabase_url.replace("https://", "").replace("http://", "")
            project_id = url_without_protocol.split(".supabase.co")[0] if ".supabase.co" in url_without_protocol else url_without_protocol.split("/")[0]
            image_url = f"https://{project_id}.supabase.co/storage/v1/object/public/{IMAGE_BUCKET}/assets/{image_filename}"
            
            # Handle color - split by comma if multiple colors, or use single color
            colors = []
            if row[3]:  # color field
                if ',' in row[3]:
                    colors = [c.strip() for c in row[3].split(',')]
                else:
                    colors = [row[3]]
            else:
                colors = ["Negro", "Blanco"]
            
            # Format price with currency
            price_str = f"${row[2]:,.0f}" if row[2] else "$0"
            
            # Technical specs - these are not in the database, so we'll use defaults
            technical = {
                "engine": "N/A",
                "power": "N/A",
                "torque": "N/A",
                "weight": "N/A",
                "fuelCapacity": "N/A"
            }
            
            motorcycles.append(MotorcycleCardItem(
                id=row[0],
                image=image_url,
                name=f"{row[5]} {row[1]}",  # brand_name + model
                price=price_str,
                colors=colors,
                technical=technical
            ))
        
        # Fetch banks from database - only specific bank IDs
        banks_stmt = text("""
            SELECT id, name
            FROM bancos
            WHERE id IN (1, 2, 3, 4, 8, 9)
            ORDER BY id
        """)
        
        banks_result = await session.execute(banks_stmt)
        banks_rows = banks_result.fetchall()
        
        banks = []
        for row in banks_rows:
            bank_id, bank_name = row[0], row[1]
            
            # Normalize bank name for filename (similar to motorcycle models)
            normalized_bank_name = normalize_model_name_for_filename(bank_name)
            bank_logo_filename = f"{normalized_bank_name}.jpg"
            
            # Get Supabase URL from config
            from app.config import get_supabase_url
            supabase_url = get_supabase_url()
            url_without_protocol = supabase_url.replace("https://", "").replace("http://", "")
            project_id = url_without_protocol.split(".supabase.co")[0] if ".supabase.co" in url_without_protocol else url_without_protocol.split("/")[0]
            bank_logo_url = f"https://{project_id}.supabase.co/storage/v1/object/public/{IMAGE_BUCKET}/banks/{bank_logo_filename}"
            
            banks.append(BankItem(
                id=bank_id,
                name=bank_name,
                image=bank_logo_url
            ))
        
        # Build response
        landing_content = MarketplaceLandingContent(
            slides=slides,
            motorcycles=motorcycles,
            banks=banks
        )
        
        return MarketplaceLandingResponse(
            page_key="marketplace_landing",
            content=landing_content,
            version=page_content.version if page_content else 1,
            updated_at=page_content.updated_at if page_content else datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching marketplace content: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching marketplace content: {str(e)}"
        )


@router.get("/marketplace/motorcycles", response_model=List[MotorcycleCardItem], status_code=status.HTTP_200_OK)
async def get_marketplace_motorcycles(
    brand_name: str = Query("Yamaha", description="Brand name to filter motorcycles"),
    limit: int = Query(6, ge=1, le=50, description="Maximum number of motorcycles to return"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get motorcycles for marketplace landing page from database.
    Filters by brand and returns formatted data for CMS.
    """
    try:
        # Query motorcycles with brand filter
        stmt = text("""
            SELECT m.id, m.model, m.price, m.color, m.year,
                   mb.name as brand_name
            FROM motorcycles m
            INNER JOIN motorcycle_brands mb ON m.brand_id = mb.id
            WHERE mb.name = :brand_name
            AND m.active = TRUE
            ORDER BY m.id
            LIMIT :limit
        """)
        
        result = await session.execute(stmt, {
            "brand_name": brand_name,
            "limit": limit
        })
        rows = result.fetchall()
        
        if not rows:
            logger.warning(f"No motorcycles found for brand: {brand_name}")
            return []
        
        # Format motorcycles for CMS structure
        motorcycles = []
        for row in rows:
            # Get model name from database (row[1] is the model field)
            model_name = row[1]  # m.model
            
            # Normalize model name for filename
            normalized_model = normalize_model_name_for_filename(model_name)
            image_filename = f"{normalized_model}.jpg"
            
            from app.config import get_supabase_url
            supabase_url = get_supabase_url()
            # Extract project ID from URL
            url_without_protocol = supabase_url.replace("https://", "").replace("http://", "")
            project_id = url_without_protocol.split(".supabase.co")[0] if ".supabase.co" in url_without_protocol else url_without_protocol.split("/")[0]
            image_url = f"https://{project_id}.supabase.co/storage/v1/object/public/{IMAGE_BUCKET}/assets/{image_filename}"
            
            # Handle color
            colors = []
            if row[3]:
                if ',' in row[3]:
                    colors = [c.strip() for c in row[3].split(',')]
                else:
                    colors = [row[3]]
            else:
                colors = ["Negro", "Blanco"]
            
            # Format price
            price_str = f"${row[2]:,.0f}" if row[2] else "$0"
            
            # Technical specs defaults
            technical = {
                "engine": "N/A",
                "power": "N/A",
                "torque": "N/A",
                "weight": "N/A",
                "fuelCapacity": "N/A"
            }
            
            motorcycles.append(MotorcycleCardItem(
                id=row[0],
                image=image_url,
                name=f"{row[5]} {row[1]}",
                price=price_str,
                colors=colors,
                technical=technical
            ))
        
        return motorcycles
        
    except Exception as e:
        logger.error(f"Error fetching marketplace motorcycles: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching motorcycles: {str(e)}"
        )


@router.get("/marketplace/banks", response_model=List[BankItem], status_code=status.HTTP_200_OK)
async def get_marketplace_banks(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get banks for marketplace landing page from database.
    Returns bank logos from Supabase storage bucket.
    """
    try:
        # Query banks - only specific bank IDs
        stmt = text("""
            SELECT id, name
            FROM bancos
            WHERE id IN (1, 2, 3, 4, 8, 9)
            ORDER BY id
        """)
        
        result = await session.execute(stmt)
        rows = result.fetchall()
        
        if not rows:
            logger.warning("No banks found in database")
            return []
        
        # Get Supabase URL from config
        from app.config import get_supabase_url
        supabase_url = get_supabase_url()
        url_without_protocol = supabase_url.replace("https://", "").replace("http://", "")
        project_id = url_without_protocol.split(".supabase.co")[0] if ".supabase.co" in url_without_protocol else url_without_protocol.split("/")[0]
        
        # Format banks for CMS structure
        banks = []
        for row in rows:
            bank_id, bank_name = row[0], row[1]
            
            # Normalize bank name for filename
            normalized_bank_name = normalize_model_name_for_filename(bank_name)
            bank_logo_filename = f"{normalized_bank_name}.jpg"
            
            # Construct Supabase URL for bank logo
            bank_logo_url = f"https://{project_id}.supabase.co/storage/v1/object/public/{IMAGE_BUCKET}/banks/{bank_logo_filename}"
            
            banks.append(BankItem(
                id=bank_id,
                name=bank_name,
                image=bank_logo_url
            ))
        
        return banks
        
    except Exception as e:
        logger.error(f"Error fetching marketplace banks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching banks: {str(e)}"
        )


@router.post("/upload-image", response_model=ImageUploadResponse, status_code=status.HTTP_200_OK)
async def upload_image(
    file: UploadFile = File(...),
    folder: str = Query("images", description="Folder path within the bucket"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an image to Supabase storage (requires authentication)
    
    Args:
        file: The image file to upload
        folder: Folder path within the bucket (e.g., "hero", "gallery", "logos")
    
    Returns:
        Public URL of the uploaded image
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Generate file path
        file_extension = Path(file.filename).suffix
        file_path = f"{folder}/{file.filename}"
        
        # Upload to Supabase
        supabase = get_supabase_client()
        
        # Upload file
        response = supabase.storage.from_(IMAGE_BUCKET).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type, "upsert": "true"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(IMAGE_BUCKET).get_public_url(file_path)
        
        logger.info(f"Image uploaded successfully: {file_path}")
        
        return ImageUploadResponse(
            success=True,
            url=public_url,
            path=file_path,
            filename=file.filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )


@router.post("/upload-multiple-images", response_model=MultipleImageUploadResponse, status_code=status.HTTP_200_OK)
async def upload_multiple_images(
    files: List[UploadFile] = File(...),
    folder: str = Query("images", description="Folder path within the bucket"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """
    Upload multiple images to Supabase storage (requires authentication)
    """
    results = []
    errors = []
    
    supabase = get_supabase_client()
    
    for file in files:
        try:
            # Validate file type
            allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
            if file.content_type not in allowed_types:
                errors.append({
                    "filename": file.filename,
                    "error": f"Invalid file type: {file.content_type}"
                })
                continue
            
            # Read file content
            file_content = await file.read()
            
            # Generate file path
            file_path = f"{folder}/{file.filename}"
            
            # Upload to Supabase
            response = supabase.storage.from_(IMAGE_BUCKET).upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": file.content_type, "upsert": "true"}
            )
            
            # Get public URL
            public_url = supabase.storage.from_(IMAGE_BUCKET).get_public_url(file_path)
            
            results.append(ImageUploadResponse(
                success=True,
                url=public_url,
                path=file_path,
                filename=file.filename
            ))
            
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
            logger.error(f"Error uploading {file.filename}: {str(e)}")
    
    return MultipleImageUploadResponse(
        success=len(errors) == 0,
        uploaded=results,
        errors=errors
    )


@router.get("/page/{page_key}", response_model=PageContentResponse, status_code=status.HTTP_200_OK)
async def get_page_content(
    page_key: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Get page content by page_key (public endpoint, no auth required)
    """
    try:
        stmt = select(PageContent).where(
            PageContent.page_key == page_key,
            PageContent.is_active == True
        )
        result = await session.execute(stmt)
        page_content = result.scalar_one_or_none()
        
        if not page_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page content not found for key: {page_key}"
            )
        
        # Parse JSON content
        if isinstance(page_content.content, str):
            content_dict = json.loads(page_content.content)
        else:
            content_dict = page_content.content
        
        return PageContentResponse(
            id=page_content.id,
            page_key=page_content.page_key,
            content=content_dict,
            version=page_content.version,
            is_active=page_content.is_active,
            created_at=page_content.created_at,
            updated_at=page_content.updated_at,
            created_by=page_content.created_by,
            updated_by=page_content.updated_by,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page content: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving page content: {str(e)}"
        )


@router.post("/page", response_model=PageContentResponse, status_code=status.HTTP_201_CREATED)
async def create_page_content(
    request: PageContentCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create new page content (requires authentication)
    """
    try:
        # Check if page_key already exists
        stmt = select(PageContent).where(PageContent.page_key == request.page_key)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Page content with key '{request.page_key}' already exists"
            )
        
        # Create new page content
        page_content = PageContent(
            page_key=request.page_key,
            content=request.content,
            is_active=request.is_active,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        
        session.add(page_content)
        await session.flush()
        await session.commit()
        
        # Parse content for response
        if isinstance(page_content.content, str):
            content_dict = json.loads(page_content.content)
        else:
            content_dict = page_content.content
        
        return PageContentResponse(
            id=page_content.id,
            page_key=page_content.page_key,
            content=content_dict,
            version=page_content.version,
            is_active=page_content.is_active,
            created_at=page_content.created_at,
            updated_at=page_content.updated_at,
            created_by=page_content.created_by,
            updated_by=page_content.updated_by,
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating page content: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating page content: {str(e)}"
        )


@router.put("/page/{page_key}", response_model=PageContentResponse, status_code=status.HTTP_200_OK)
async def update_page_content(
    page_key: str,
    request: PageContentUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update existing page content (requires authentication)
    """
    try:
        stmt = select(PageContent).where(PageContent.page_key == page_key)
        result = await session.execute(stmt)
        page_content = result.scalar_one_or_none()
        
        if not page_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page content not found for key: {page_key}"
            )
        
        # Update fields
        if request.content is not None:
            page_content.content = request.content
        if request.is_active is not None:
            page_content.is_active = request.is_active
        
        page_content.updated_by = current_user.id
        page_content.updated_at = datetime.now()
        page_content.version += 1
        
        await session.commit()
        await session.refresh(page_content)
        
        # Parse content for response
        if isinstance(page_content.content, str):
            content_dict = json.loads(page_content.content)
        else:
            content_dict = page_content.content
        
        return PageContentResponse(
            id=page_content.id,
            page_key=page_content.page_key,
            content=content_dict,
            version=page_content.version,
            is_active=page_content.is_active,
            created_at=page_content.created_at,
            updated_at=page_content.updated_at,
            created_by=page_content.created_by,
            updated_by=page_content.updated_by,
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating page content: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating page content: {str(e)}"
        )


@router.get("/pages", response_model=List[PageContentResponse], status_code=status.HTTP_200_OK)
async def list_all_pages(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all page content (requires authentication)
    """
    try:
        stmt = select(PageContent).order_by(PageContent.updated_at.desc())
        result = await session.execute(stmt)
        pages = result.scalars().all()
        
        response = []
        for page in pages:
            if isinstance(page.content, str):
                content_dict = json.loads(page.content)
            else:
                content_dict = page.content
            
            response.append(PageContentResponse(
                id=page.id,
                page_key=page.page_key,
                content=content_dict,
                version=page.version,
                is_active=page.is_active,
                created_at=page.created_at,
                updated_at=page.updated_at,
                created_by=page.created_by,
                updated_by=page.updated_by,
            ))
        
        return response
    except Exception as e:
        logger.error(f"Error listing pages: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing pages: {str(e)}"
        )

