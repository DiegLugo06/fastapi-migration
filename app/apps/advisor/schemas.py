"""
Pydantic schemas for advisor module
"""
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class UserResponse(BaseModel):
    """User response schema"""
    status: str
    user_email: str
    user_id: int
    role_id: int


class StoreData(BaseModel):
    """Store data schema"""
    id: int
    nombre: str
    brand_id: int
    brand_name: Optional[str] = None
    ubicacion: str
    razon_social: Optional[str] = None
    credit_card_payment_method: Optional[bool] = None
    crm_sync: Optional[str] = None
    zip_code: Optional[str] = None
    active: bool
    coordinates: Optional[dict] = None


class GetStoresResponse(BaseModel):
    """Get stores response schema"""
    status: str
    stores_data: List[StoreData]
    filters_applied: dict
    count: int
    holding_filter: Optional[str] = None


class AdvisorResponse(BaseModel):
    """Advisor response schema"""
    id: int
    uuid: str
    name: Optional[str] = None
    second_name: Optional[str] = None
    first_last_name: Optional[str] = None
    second_last_name: Optional[str] = None
    email: str
    zona_autoestrena_url: Optional[str] = None
    selected_at: Optional[str] = None
    role_id: int
    phone_number: Optional[str] = None


class UserUpdateRequest(BaseModel):
    """User update request schema"""
    name: Optional[str] = None
    second_name: Optional[str] = None
    first_last_name: Optional[str] = None
    second_last_name: Optional[str] = None
    phone_number: Optional[str] = None
    zona_autoestrena_url: Optional[str] = None


class AdvisorDetailsResponse(BaseModel):
    """Advisor details response schema"""
    status: str
    advisor: dict
    stores: List[StoreData]


class CreateSucursalRequest(BaseModel):
    """Create sucursal request schema"""
    nombre: str
    marca: Optional[str] = None
    ubicacion: str
    razon_social: Optional[str] = None
    credit_card_payment_method: Optional[bool] = None
    crm_sync: Optional[str] = None
    zip_code: Optional[str] = None
    banco_ids: Optional[List[int]] = []


class GetNextUserRequest(BaseModel):
    """Get next user request schema (query params)"""
    store_id: int
    client_email: str
    client_phone: str


class GetNextFinvaUserRequest(BaseModel):
    """Get next finva user request schema (query params)"""
    client_id: Optional[int] = None
    holdingStore: Optional[str] = None

