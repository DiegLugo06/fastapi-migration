"""
Pydantic schemas for CMS module
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# Landing page specific schemas
class SlideItem(BaseModel):
    title: str
    image: str


class MotorcycleCardItem(BaseModel):
    id: int
    image: str
    name: str
    price: str
    colors: List[str]
    technical: Dict[str, str]
    hero_image: Optional[str] = None
    images: Optional[List[str]] = None


class BankItem(BaseModel):
    id: int
    name: str
    image: str  # Supabase URL for bank logo


class MarketplaceLandingContent(BaseModel):
    """Schema for marketplace landing page content"""
    slides: List[SlideItem]
    motorcycles: List[MotorcycleCardItem]
    banks: List[BankItem]


# Generic CMS schemas
class PageContentCreate(BaseModel):
    """Create page content schema"""
    page_key: str = Field(..., max_length=100)
    content: Dict[str, Any]  # Flexible JSON content
    is_active: bool = True


class PageContentUpdate(BaseModel):
    """Update page content schema"""
    content: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PageContentResponse(BaseModel):
    """Page content response schema"""
    id: int
    page_key: str
    content: Dict[str, Any]
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    
    class Config:
        from_attributes = True


class MarketplaceLandingResponse(BaseModel):
    """Marketplace landing page response"""
    page_key: str
    content: MarketplaceLandingContent
    version: int
    updated_at: datetime


class ImageUploadResponse(BaseModel):
    """Image upload response"""
    success: bool
    url: str
    path: str
    filename: str


class MultipleImageUploadResponse(BaseModel):
    """Multiple image upload response"""
    success: bool
    uploaded: List[ImageUploadResponse]
    errors: List[Dict[str, str]]

