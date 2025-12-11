"""
Loan models
Basic models for loan module - additional models will be added as needed
"""
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List
from datetime import datetime, date
from app.common.fields import handle_postgresql_json


class Solicitud(SQLModel, table=True):
    """
    Loan application (Solicitud) model
    Table: solicitudes
    """
    __tablename__ = "solicitudes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="clientes.id", index=True)
    motorcycle_id: int = Field(foreign_key="motorcycles.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    finva_user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    bank_offer_id: Optional[int] = Field(default=None, foreign_key="banks_offers.id")
    status: Optional[str] = Field(default=None, max_length=50, index=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.now, index=True)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})
    
    # Additional fields as needed
    loan_term_months: Optional[int] = Field(default=None)
    down_payment_amount: Optional[float] = Field(default=None)
    amount_to_finance: Optional[float] = Field(default=None)
    monthly_payment: Optional[float] = Field(default=None)
    insurance_amount: Optional[float] = Field(default=None)
    insurance_payment_method: Optional[str] = Field(default=None, max_length=50)
    paquete: Optional[str] = Field(default=None, max_length=50)
    
    # JSON fields
    solicitud_data: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    bank_data: Optional[dict] = Field(default=None, sa_column=Column(JSONB))


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
    solicitud_id: int = Field(foreign_key="solicitudes.id", index=True)
    status: str = Field(max_length=50)
    created_at: Optional[datetime] = Field(default_factory=datetime.now, index=True)
    notes: Optional[str] = Field(default=None, max_length=500)


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

