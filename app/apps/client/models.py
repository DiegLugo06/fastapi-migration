"""
Client models
Migrated from Django apps/client/models.py
"""
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional
from datetime import datetime, date
from app.common.fields import handle_postgresql_json


class Cliente(SQLModel, table=True):
    """
    Client model - migrated from Flask/Django
    Table: clientes
    """
    __tablename__ = "clientes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Name fields
    name: str = Field(max_length=50)
    second_name: Optional[str] = Field(default=None, max_length=50)
    first_last_name: Optional[str] = Field(default=None, max_length=50)
    second_last_name: Optional[str] = Field(default=None, max_length=50)
    
    # Contact Information
    phone: str = Field(max_length=15, unique=True, index=True)
    email: str = Field(max_length=100, unique=True, index=True)
    carrier: Optional[str] = Field(default=None, max_length=100)
    
    # Birth Information
    born_state: Optional[str] = Field(default=None, max_length=50)
    birth_date: Optional[date] = Field(default=None)
    
    # Personal Information
    economic_dependants: Optional[int] = Field(default=None)
    sex: Optional[str] = Field(default=None, max_length=1)
    rfc: Optional[str] = Field(default=None, max_length=13, index=True)
    curp: Optional[str] = Field(default=None, max_length=18, index=True)
    
    # Address Information
    street_address: Optional[str] = Field(default=None, max_length=100)
    zip_code: Optional[str] = Field(default=None, max_length=10)
    suburb_colonia: Optional[str] = Field(default=None, max_length=50)
    ciudad: Optional[str] = Field(default=None, max_length=50)
    estado: Optional[str] = Field(default=None, max_length=50)
    time_living_there: Optional[str] = Field(default=None, max_length=50)
    interior_number: Optional[str] = Field(default=None, max_length=10)
    
    # Optional Information
    id_type: Optional[str] = Field(default=None, max_length=50)
    id_number: Optional[str] = Field(default=None, max_length=100)
    id_expiration_date: Optional[date] = Field(default=None)
    marital_status: Optional[str] = Field(default=None, max_length=30)
    level_studies: Optional[str] = Field(default=None, max_length=30)
    profesion: Optional[str] = Field(default=None, max_length=50)
    housing_status: Optional[str] = Field(default=None, max_length=20)
    
    # Metadata
    created_at: Optional[datetime] = Field(default_factory=datetime.now, index=True)
    crm_sync_id: Optional[str] = Field(default=None, max_length=255)


class FileStatus(SQLModel, table=True):
    """
    File status model for client documents
    Table: file_statuses
    """
    __tablename__ = "file_statuses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="clientes.id")
    
    # Status options: 'null', 'validating', 'validated'
    officialId_front: Optional[str] = Field(default="null", max_length=50)
    officialId_reverse: Optional[str] = Field(default="null", max_length=50)
    addressProof: Optional[str] = Field(default="null", max_length=50)


class IncomeProofDocument(SQLModel, table=True):
    """
    Income proof document model
    Table: income_proof_documents
    """
    __tablename__ = "income_proof_documents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="clientes.id")  # Note: Flask uses 'client_id'
    
    document_type: str = Field(max_length=50)  # estado_cuenta, nomina_semanal, etc.
    status: str = Field(default="null", max_length=50)  # null, validating, validated, rejected
    
    sequence_number: Optional[int] = Field(default=None)
    total_income: Optional[float] = Field(default=None)
    month: Optional[int] = Field(default=None)
    year: Optional[int] = Field(default=None)


class Report(SQLModel, table=True):
    """
    Report model - used by client validation
    Table: reports
    """
    __tablename__ = "reports"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    kiban_id: str = Field(max_length=255, unique=True, index=True)
    cliente_id: int = Field(foreign_key="clientes.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.now, index=True)
    finished_at: Optional[datetime] = Field(default=None)
    duration: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None, max_length=50)
    raw_query_report: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    finva_evaluation: Optional[dict] = Field(default=None, sa_column=Column(JSONB))


class ClientesUnknown(SQLModel, table=True):
    """
    Unknown clients model
    Table: clientes_unknown
    """
    __tablename__ = "clientes_unknown"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=15)
    motorcycle_id: Optional[int] = Field(default=None, foreign_key="motorcycles.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    flow_process: Optional[str] = Field(default=None, max_length=50)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)

