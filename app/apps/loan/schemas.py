"""
Pydantic schemas for loan module
"""
from pydantic import BaseModel, field_serializer, ConfigDict
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from datetime import datetime, date


class SolicitudBase(BaseModel):
    """Base solicitud schema - matches all database columns"""
    # Disable protected namespace warning for model_motorcycle field
    model_config = ConfigDict(protected_namespaces=())
    
    # Foreign keys
    cliente_id: Optional[int] = None
    report_id: Optional[int] = None
    user_id: Optional[int] = None
    finva_user_id: Optional[int] = None
    
    # Motorcycle information
    brand_motorcycle: Optional[str] = None
    model_motorcycle: Optional[str] = None
    year_motorcycle: Optional[int] = None
    first_motorcycle: Optional[str] = None
    use_motorcycle: Optional[str] = None
    invoice_motorcycle_value: Optional[Union[str, Decimal, float, int]] = None
    percentage_down_payment: Optional[Union[str, Decimal, float, int]] = None
    insurance_payment: Optional[str] = None
    finance_term_months: Optional[str] = None
    vin_motorcycle: Optional[str] = None
    invoiced_motorcycle_date: Optional[datetime] = None
    motorcycle_existance: Optional[str] = None
    motorcycle_existance_updated_at: Optional[datetime] = None
    
    # Income and financial
    income_source_type: Optional[List[str]] = None
    income_proof: Optional[List[str]] = None
    monthly_income: Optional[Union[str, Decimal, float, int]] = None
    debt_pay_from_income: Optional[Union[str, Decimal, float, int]] = None
    client_credit_history_description: Optional[str] = None
    clients_banks: Optional[List] = None
    clients_debt_banks: Optional[List] = None
    possible_guarantor: Optional[str] = None
    
    # Job information
    time_current_job: Optional[str] = None
    time_current_business: Optional[str] = None
    time_last_job: Optional[str] = None
    name_current_job: Optional[str] = None
    current_job_business_line: Optional[str] = None
    type_company_current_job: Optional[str] = None
    current_job_position: Optional[str] = None
    current_job_street_address: Optional[str] = None
    current_job_interior_number: Optional[str] = None
    current_job_zip_code: Optional[str] = None
    current_job_suburb_colonia: Optional[str] = None
    current_job_phone: Optional[str] = None
    name_last_job: Optional[str] = None
    last_job_phone: Optional[str] = None
    
    # Business information
    current_business_street_address: Optional[str] = None
    current_business_interior_number: Optional[str] = None
    current_business_zip_code: Optional[str] = None
    current_business_suburb_colonia: Optional[str] = None
    
    # Family reference
    fam_reference_names: Optional[str] = None
    fam_reference_first_last_name: Optional[str] = None
    fam_reference_second_last_name: Optional[str] = None
    fam_reference_street_address: Optional[str] = None
    fam_reference_zip_code: Optional[str] = None
    fam_reference_relation: Optional[str] = None
    fam_reference_suburb_colonia: Optional[str] = None
    fam_reference_phone: Optional[str] = None
    
    # Friend reference
    friend_reference_names: Optional[str] = None
    friend_reference_first_last_name: Optional[str] = None
    friend_reference_second_last_name: Optional[str] = None
    friend_reference_street_address: Optional[str] = None
    friend_reference_zip_code: Optional[str] = None
    friend_reference_suburb_colonia: Optional[str] = None
    friend_reference_phone: Optional[str] = None
    friend_reference_time_knowing: Optional[str] = None
    
    # Beneficiary
    beneficiary_names: Optional[str] = None
    beneficiary_last_names: Optional[str] = None
    
    # Status
    status: Optional[str] = "Nuevo"
    payment_method: Optional[str] = "loan"
    
    # Grant information
    bank_granted: Optional[str] = None
    downpayment_granted: Optional[Union[str, Decimal, float, int]] = None
    amount_to_finance_granted: Optional[Union[str, Decimal, float, int]] = None
    loan_granted_start_date: Optional[date] = None
    commission_by_loan_provider: Optional[bool] = False
    
    # Store
    preferred_store: Optional[str] = None
    preferred_store_id: Optional[int] = None
    time_to_buy_motorcycle: Optional[str] = None
    
    # CRM
    crm_sync_id: Optional[str] = None
    
    # Task tracking
    task_verify_documents: Optional[bool] = False
    task_check_application_data: Optional[bool] = False
    task_verify_signature: Optional[bool] = False
    task_income_source: Optional[str] = None
    task_activity_matches_income: Optional[bool] = None
    task_all_income_verified: Optional[bool] = None
    
    # Registration
    registration_process: Optional[str] = None
    registration_mode: Optional[str] = None
    internal_comment: Optional[str] = None
    credit_preference: Optional[str] = None
    ai_assisted: Optional[bool] = False
    holding_page_url: Optional[str] = None
    fee_paid_to_finva_agent: Optional[bool] = False
    
    # UTM
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    other_url_params: Optional[str] = None
    
    # Legacy fields for backward compatibility (not stored in DB)
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


class SolicitudUpdate(SolicitudBase):
    """Solicitud update schema - accepts all fields from SolicitudBase"""
    # All fields from SolicitudBase are inherited and optional
    pass


class SolicitudResponse(SolicitudBase):
    """Solicitud response schema - includes all fields from database"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status_updated_at: Optional[datetime] = None
    email_notification: Optional[bool] = True  # Not in DB, but included in response for compatibility
    
    @field_serializer('invoice_motorcycle_value', 'percentage_down_payment', 'monthly_income', 
                     'debt_pay_from_income', 'downpayment_granted', 'amount_to_finance_granted')
    def serialize_decimal_fields(self, value, _info) -> Optional[str]:
        """Convert Decimal/numeric values to string for API response"""
        if value is None:
            return None
        if isinstance(value, Decimal):
            # Convert Decimal to string, removing trailing zeros
            return str(value.normalize())
        if isinstance(value, (int, float)):
            return str(value)
        # Already a string
        return str(value) if value is not None else None
    
    class Config:
        from_attributes = True


class SendNIPRequest(BaseModel):
    """Send NIP request schema"""
    method: str = "whatsapp"
    countryCode: str = "+52"
    to: str


class ValidateNIPRequest(BaseModel):
    """Validate NIP request schema"""
    id: str  # Changed from int to str - Kiban API returns string IDs (MongoDB ObjectId format)
    nip: str


class GetBCKibanRequest(BaseModel):
    """Get BC Kiban request schema"""
    # Accept flexible JSON structure for Kiban API
    # The body contains: parameters_bc_pf_by_kiban, nombre, domicilio, authorization
    parameters_bc_pf_by_kiban: Optional[Dict[str, Any]] = None
    nombre: Optional[Dict[str, Any]] = None
    domicilio: Optional[Dict[str, Any]] = None
    authorization: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"  # Allow additional fields


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
    previous_status: Optional[str] = None
    new_status: str
    changed_by_user_id: Optional[int] = None
    comment: Optional[str] = None
    time_in_previous_status_minutes: Optional[int] = None
    process_type_id: Optional[int] = None
    created_at: Optional[datetime] = None
    
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


class AddClientWithoutReportRequest(BaseModel):
    """Add client without report request schema"""
    phone: str
    email: str
    id_motorcycle: int
    user_id: int
    payment_method: str
    preferred_store_id: Optional[int] = None
    time_to_buy_motorcycle: Optional[str] = None
    registration_process: Optional[str] = "manualRegistration"
    registration_mode: Optional[str] = None
    curp: Optional[str] = None
    name: Optional[str] = None
    first_last_name: Optional[str] = None
    second_last_name: Optional[str] = None
    second_name: Optional[str] = None


class AddClientWithoutReportResponse(BaseModel):
    """Add client without report response schema"""
    message: str
    client_id: int
    solicitud_id: int


class ProcessTypeResponse(BaseModel):
    """Process type response schema"""
    id: int
    name: str
    description: Optional[str] = None
    payment_method: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProcessStepResponse(BaseModel):
    """Process step response schema"""
    id: int
    process_type_id: int
    step_order: int
    step_name: str
    
    class Config:
        from_attributes = True


class ProcessStepsResponse(BaseModel):
    """Process steps response schema"""
    process_type: str
    payment_method: str
    steps: List[ProcessStepResponse]


class SolicitudCreateResponse(BaseModel):
    """Solicitud create response schema - matches original Flask response format"""
    email_notification: bool = True
    message: str = "Solicitud added successfully"
    solicitud: SolicitudResponse
    success: bool = True
