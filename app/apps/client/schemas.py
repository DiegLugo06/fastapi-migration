"""
Pydantic schemas for client module
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Any, Union
from datetime import datetime, date


class ClienteBase(BaseModel):
    """Base cliente schema"""
    name: str = Field(max_length=50)
    second_name: Optional[str] = Field(None, max_length=50)
    first_last_name: Optional[str] = Field(None, max_length=50)
    second_last_name: Optional[str] = Field(None, max_length=50)
    phone: str = Field(max_length=15)
    email: EmailStr = Field(max_length=100)
    carrier: Optional[str] = Field(None, max_length=100)
    born_state: Optional[str] = Field(None, max_length=50)
    birth_date: Optional[date] = None
    economic_dependants: Optional[int] = None
    sex: Optional[str] = Field(None, max_length=1)
    rfc: Optional[str] = Field(None, max_length=13)
    curp: Optional[str] = Field(None, max_length=18)
    street_address: Optional[str] = Field(None, max_length=100)
    zip_code: Optional[str] = Field(None, max_length=10)
    suburb_colonia: Optional[str] = Field(None, max_length=50)
    ciudad: Optional[str] = Field(None, max_length=50)
    estado: Optional[str] = Field(None, max_length=50)
    time_living_there: Optional[str] = Field(None, max_length=50)
    interior_number: Optional[str] = Field(None, max_length=10)
    id_type: Optional[str] = Field(None, max_length=50)
    id_number: Optional[str] = Field(None, max_length=100)
    id_expiration_date: Optional[date] = None
    marital_status: Optional[str] = Field(None, max_length=30)
    level_studies: Optional[str] = Field(None, max_length=30)
    profesion: Optional[str] = Field(None, max_length=50)
    housing_status: Optional[str] = Field(None, max_length=20)
    crm_sync_id: Optional[str] = Field(None, max_length=255)


class ClienteCreate(ClienteBase):
    """Cliente creation schema"""
    user_id: int
    flow_process: str
    finva_user_id: Optional[int] = None


class ClienteUpdate(BaseModel):
    """Cliente update schema - all fields optional"""
    name: Optional[str] = Field(None, max_length=50)
    second_name: Optional[str] = Field(None, max_length=50)
    first_last_name: Optional[str] = Field(None, max_length=50)
    second_last_name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = Field(None, max_length=100)
    carrier: Optional[str] = Field(None, max_length=100)
    born_state: Optional[str] = Field(None, max_length=50)
    birth_date: Optional[date] = None
    economic_dependants: Optional[int] = None
    sex: Optional[str] = Field(None, max_length=1)
    rfc: Optional[str] = Field(None, max_length=13)
    curp: Optional[str] = Field(None, max_length=18)
    street_address: Optional[str] = Field(None, max_length=100)
    zip_code: Optional[str] = Field(None, max_length=10)
    suburb_colonia: Optional[str] = Field(None, max_length=50)
    ciudad: Optional[str] = Field(None, max_length=50)
    estado: Optional[str] = Field(None, max_length=50)
    time_living_there: Optional[str] = Field(None, max_length=50)
    interior_number: Optional[str] = Field(None, max_length=10)
    id_type: Optional[str] = Field(None, max_length=50)
    id_number: Optional[str] = Field(None, max_length=100)
    id_expiration_date: Optional[date] = None
    marital_status: Optional[str] = Field(None, max_length=30)
    level_studies: Optional[str] = Field(None, max_length=30)
    profesion: Optional[str] = Field(None, max_length=50)
    housing_status: Optional[str] = Field(None, max_length=20)
    user_id: Optional[int] = None


class ClienteResponse(ClienteBase):
    """Cliente response schema"""
    id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class FileStatusResponse(BaseModel):
    """File status response schema"""
    id: Optional[int] = None
    cliente_id: int
    officialId_front: Optional[str] = "null"
    officialId_reverse: Optional[str] = "null"
    addressProof: Optional[str] = "null"
    income_proof_documents: Optional[List[dict]] = []
    
    class Config:
        from_attributes = True


class IncomeProofDocumentResponse(BaseModel):
    """Income proof document response schema"""
    id: int
    client_id: int
    document_type: str
    status: str
    sequence_number: Optional[int] = None
    total_income: Optional[float] = None
    month: Optional[int] = None
    year: Optional[int] = None
    
    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    """Report response schema"""
    id: int
    kiban_id: str
    cliente_id: int
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration: Optional[int] = None
    status: Optional[str] = None
    raw_query_report: Optional[dict] = None
    finva_evaluation: Optional[dict] = None
    
    class Config:
        from_attributes = True


class ValidateClientResponse(BaseModel):
    """Validate client response schema"""
    client: dict
    files: dict
    id: bool
    id_details: str
    report: Optional[int] = None
    rerport_details: Optional[str] = None
    has_purchases: bool


class ValidatePhoneResponse(BaseModel):
    """Validate phone response schema"""
    status: str
    type: Optional[str] = None
    clue: Optional[str] = None
    client_id: Optional[int] = None


class GenerateRFCRequest(BaseModel):
    """Generate RFC request schema"""
    # Add fields based on kiban_api.generate_rfc requirements
    pass


class GenerateRFCResponse(BaseModel):
    """Generate RFC response schema"""
    status: str
    rfc: str


class GetNeighborhoodsResponse(BaseModel):
    """Get neighborhoods response schema"""
    # Neighborhoods can be strings (from SEPOMEX) or dicts (from Copomex)
    neighborhoods: List[Union[str, dict]]


class ClientesUnknownCreate(BaseModel):
    """Unknown client creation schema"""
    email: Optional[str] = None
    phone: Optional[str] = None
    motorcycle_id: Optional[int] = None
    user_id: Optional[int] = None
    flow_process: Optional[str] = None
    motorcycle_data: Optional[dict] = None


class ClientesUnknownResponse(BaseModel):
    """Unknown client response schema"""
    id: int
    email: Optional[str] = None
    phone: Optional[str] = None
    motorcycle_id: Optional[int] = None
    user_id: Optional[int] = None
    flow_process: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

