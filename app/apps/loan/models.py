"""
Loan models
Basic models for loan module - additional models will be added as needed
"""
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Numeric
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date
from pydantic import ConfigDict
from app.common.fields import handle_postgresql_json


class Solicitud(SQLModel, table=True):
    """
    Loan application (Solicitud) model
    Table: solicitudes
    Complete model matching the original database schema.
    """
    __tablename__ = "solicitudes"
    
    # Disable protected namespace warning for model_motorcycle field
    model_config = ConfigDict(protected_namespaces=())
    
    # Primary key and foreign keys
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: Optional[int] = Field(default=None, foreign_key="clientes.id", index=True)
    report_id: Optional[int] = Field(default=None, foreign_key="reports.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    finva_user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    
    # Motorcycle information
    brand_motorcycle: Optional[str] = Field(default=None)
    model_motorcycle: Optional[str] = Field(default=None)
    year_motorcycle: Optional[int] = Field(default=None)
    first_motorcycle: Optional[str] = Field(default=None)
    use_motorcycle: Optional[str] = Field(default=None)
    invoice_motorcycle_value: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(precision=10, scale=2)))
    percentage_down_payment: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(precision=5, scale=2)))
    insurance_payment: Optional[str] = Field(default=None)
    finance_term_months: Optional[str] = Field(default=None)
    vin_motorcycle: Optional[str] = Field(default=None)
    invoiced_motorcycle_date: Optional[datetime] = Field(default=None)
    motorcycle_existance: Optional[str] = Field(default=None)
    motorcycle_existance_updated_at: Optional[datetime] = Field(default=None)
    
    # Income and financial information
    income_source_type: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))
    income_proof: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))
    monthly_income: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(precision=10, scale=2)))
    debt_pay_from_income: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(precision=10, scale=2)))
    client_credit_history_description: Optional[str] = Field(default=None)
    clients_banks: Optional[List] = Field(default=None, sa_column=Column(JSONB))
    clients_debt_banks: Optional[List] = Field(default=None, sa_column=Column(JSONB))
    possible_guarantor: Optional[str] = Field(default=None)
    
    # Job information
    time_current_job: Optional[str] = Field(default=None)
    time_current_business: Optional[str] = Field(default=None)
    time_last_job: Optional[str] = Field(default=None)
    name_current_job: Optional[str] = Field(default=None)
    current_job_business_line: Optional[str] = Field(default=None)
    type_company_current_job: Optional[str] = Field(default=None)
    current_job_position: Optional[str] = Field(default=None)
    current_job_street_address: Optional[str] = Field(default=None)
    current_job_interior_number: Optional[str] = Field(default=None)
    current_job_zip_code: Optional[str] = Field(default=None)
    current_job_suburb_colonia: Optional[str] = Field(default=None)
    current_job_phone: Optional[str] = Field(default=None)
    name_last_job: Optional[str] = Field(default=None)
    last_job_phone: Optional[str] = Field(default=None)
    
    # Business information
    current_business_street_address: Optional[str] = Field(default=None)
    current_business_interior_number: Optional[str] = Field(default=None)
    current_business_zip_code: Optional[str] = Field(default=None)
    current_business_suburb_colonia: Optional[str] = Field(default=None)
    
    # Family reference
    fam_reference_names: Optional[str] = Field(default=None)
    fam_reference_first_last_name: Optional[str] = Field(default=None)
    fam_reference_second_last_name: Optional[str] = Field(default=None)
    fam_reference_street_address: Optional[str] = Field(default=None)
    fam_reference_zip_code: Optional[str] = Field(default=None)
    fam_reference_relation: Optional[str] = Field(default=None)
    fam_reference_suburb_colonia: Optional[str] = Field(default=None)
    fam_reference_phone: Optional[str] = Field(default=None)
    
    # Friend reference
    friend_reference_names: Optional[str] = Field(default=None)
    friend_reference_first_last_name: Optional[str] = Field(default=None)
    friend_reference_second_last_name: Optional[str] = Field(default=None)
    friend_reference_street_address: Optional[str] = Field(default=None)
    friend_reference_zip_code: Optional[str] = Field(default=None)
    friend_reference_suburb_colonia: Optional[str] = Field(default=None)
    friend_reference_phone: Optional[str] = Field(default=None)
    friend_reference_time_knowing: Optional[str] = Field(default=None)
    
    # Beneficiary
    beneficiary_names: Optional[str] = Field(default=None)
    beneficiary_last_names: Optional[str] = Field(default=None)
    
    # Status and timestamps
    status: Optional[str] = Field(default="Nuevo", max_length=50, index=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.now, index=True)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})
    status_updated_at: Optional[datetime] = Field(default=None)
    
    # Grant information
    bank_granted: Optional[str] = Field(default=None)
    downpayment_granted: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(precision=10, scale=2)))
    amount_to_finance_granted: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(precision=10, scale=2)))
    loan_granted_start_date: Optional[date] = Field(default=None)
    commission_by_loan_provider: Optional[bool] = Field(default=False)
    
    # Store and payment
    payment_method: str = Field(default="loan", max_length=50)  # NOT NULL with default "loan"
    preferred_store: Optional[str] = Field(default=None)
    preferred_store_id: Optional[int] = Field(default=None, foreign_key="sucursales.id")
    time_to_buy_motorcycle: Optional[str] = Field(default=None)
    
    # CRM and tracking
    crm_sync_id: Optional[str] = Field(default=None)
    
    # Task tracking fields
    task_verify_documents: Optional[bool] = Field(default=False)
    task_check_application_data: Optional[bool] = Field(default=False)
    task_verify_signature: Optional[bool] = Field(default=False)
    task_income_source: Optional[str] = Field(default=None)
    task_activity_matches_income: Optional[bool] = Field(default=None)
    task_all_income_verified: Optional[bool] = Field(default=None)
    
    # Registration and tracking
    registration_process: Optional[str] = Field(default=None)
    registration_mode: Optional[str] = Field(default=None)
    internal_comment: Optional[str] = Field(default=None)
    credit_preference: Optional[str] = Field(default=None)
    ai_assisted: Optional[bool] = Field(default=False)
    holding_page_url: Optional[str] = Field(default=None)
    fee_paid_to_finva_agent: Optional[bool] = Field(default=False)
    
    # UTM tracking
    utm_source: Optional[str] = Field(default=None)
    utm_medium: Optional[str] = Field(default=None)
    utm_campaign: Optional[str] = Field(default=None)
    utm_content: Optional[str] = Field(default=None)
    utm_term: Optional[str] = Field(default=None)
    other_url_params: Optional[str] = Field(default=None)
    
    # NOTE: email_notification is NOT a database column
    # It's only included in the response schema for API compatibility


class Application(SQLModel, table=True):
    """
    Application model
    Table: applications
    """
    __tablename__ = "applications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: int = Field(foreign_key="solicitudes.id", index=True)
    status: Optional[str] = Field(default=None, max_length=50)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})


class SolicitudStatusHistory(SQLModel, table=True):
    """
    Solicitud status history model
    Table: solicitud_status_history
    """
    __tablename__ = "solicitud_status_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: int = Field(foreign_key="solicitudes.id", index=True, nullable=False)
    previous_status: Optional[str] = Field(default=None, max_length=50)  # Can be null for first status
    new_status: str = Field(max_length=50, nullable=False)  # NOT NULL - the new status
    changed_by_user_id: Optional[int] = Field(default=None, foreign_key="users.id", nullable=True)
    comment: Optional[str] = Field(default=None)  # Text field, not notes
    time_in_previous_status_minutes: Optional[int] = Field(default=None, nullable=True)
    process_type_id: Optional[int] = Field(default=None, foreign_key="process_types.id", nullable=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.now, index=True, nullable=False)


class ProcessType(SQLModel, table=True):
    """
    Process type model
    Table: process_types
    Represents different payment/process types (loan, cash, credit_card, auto_financing)
    """
    __tablename__ = "process_types"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, nullable=False)
    description: Optional[str] = Field(default=None)
    payment_method: Optional[str] = Field(default=None, max_length=50)  # 'loan', 'cash', 'credit_card', 'auto_financing'


class ProcessStep(SQLModel, table=True):
    """
    Process step model
    Table: process_steps
    Represents individual steps in a process type workflow
    """
    __tablename__ = "process_steps"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    process_type_id: int = Field(foreign_key="process_types.id", nullable=False)
    step_order: int = Field(nullable=False)
    step_name: str = Field(max_length=200, nullable=False)


class ContactAttempt(SQLModel, table=True):
    """
    Contact attempt model
    Table: contact_attempts
    """
    __tablename__ = "contact_attempts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: int = Field(foreign_key="solicitudes.id", index=True)
    contact_method: str = Field(max_length=50)  # phone, email, etc.
    status: str = Field(max_length=50)  # success, failed, no_answer
    created_at: Optional[datetime] = Field(default_factory=datetime.now, index=True)
    notes: Optional[str] = Field(default=None, max_length=500)

