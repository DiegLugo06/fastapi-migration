"""
Pydantic schemas for product module
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MotorcycleBrandResponse(BaseModel):
    """Motorcycle brand response schema"""
    id: int
    name: str
    
    class Config:
        from_attributes = True


class MotorcycleResponse(BaseModel):
    """Motorcycle response schema"""
    id: int
    brand: Optional[str] = None
    brand_id: int
    model: str
    inner_brand_model: Optional[str] = None
    year: int
    price: float
    color: Optional[str] = None
    active: Optional[bool] = True
    review_video_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class DiscountCreate(BaseModel):
    """Discount creation schema"""
    description: str
    discount_type: str  # 'percentage' or 'fixed'
    discount_value: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    motorcycle_id: int
    user_id: int


class DiscountResponse(BaseModel):
    """Discount response schema"""
    id: int
    description: str
    type: str
    value: float
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str
    sucursal_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GetMotorcycleModelsResponse(BaseModel):
    """Get motorcycle models response schema"""
    models: List[MotorcycleResponse]


class CreateDiscountResponse(BaseModel):
    """Create discount response schema"""
    message: str
    discount_id: int
    motorcycle_id: int
    hash: str

