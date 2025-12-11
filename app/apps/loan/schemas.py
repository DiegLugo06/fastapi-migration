"""
Pydantic schemas for loan module
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class SolicitudBase(BaseModel):
    """Base solicitud schema"""
    cliente_id: int
    motorcycle_id: int
    user_id: Optional[int] = None
    finva_user_id: Optional[int] = None
    bank_offer_id: Optional[int] = None
    status: Optional[str] = None
    loan_term_months: Optional[int] = None
    down_payment_amount: Optional[float] = None
    amount_to_finance: Optional[float] = None
    monthly_payment: Optional[float] = None
    insurance_amount: Optional[float] = None
    insurance_payment_method: Optional[str] = None
    paquete: Optional[str] = None
    solicitud_data: Optional[dict] = None
    bank_data: Optional[dict] = None


class SolicitudCreate(SolicitudBase):
    """Solicitud creation schema"""
    pass


class SolicitudUpdate(BaseModel):
    """Solicitud update schema"""
    status: Optional[str] = None
    bank_offer_id: Optional[int] = None
    loan_term_months: Optional[int] = None
    down_payment_amount: Optional[float] = None
    amount_to_finance: Optional[float] = None
    monthly_payment: Optional[float] = None
    insurance_amount: Optional[float] = None
    insurance_payment_method: Optional[str] = None
    paquete: Optional[str] = None
    solicitud_data: Optional[dict] = None
    bank_data: Optional[dict] = None


class SolicitudResponse(SolicitudBase):
    """Solicitud response schema"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SendNIPRequest(BaseModel):
    """Send NIP request schema"""
    phone: str
    # Additional fields as needed by Kiban API


class ValidateNIPRequest(BaseModel):
    """Validate NIP request schema"""
    phone: str
    nip: str
    # Additional fields as needed by Kiban API


class GetBCKibanRequest(BaseModel):
    """Get BC Kiban request schema"""
    # Fields as needed by Kiban API
    pass


class ApplicationResponse(BaseModel):
    """Application response schema"""
    id: int
    solicitud_id: int
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SolicitudStatusHistoryResponse(BaseModel):
    """Solicitud status history response schema"""
    id: int
    solicitud_id: int
    status: str
    created_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class ContactAttemptResponse(BaseModel):
    """Contact attempt response schema"""
    id: int
    solicitud_id: int
    contact_method: str
    status: str
    created_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True

