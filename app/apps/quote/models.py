"""
Quote models
Migrated from Django apps/quote/models.py
"""
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List
from datetime import date, datetime
from app.common.fields import handle_postgresql_json
from enum import Enum


class FinanceRestrictionType(str, Enum):
    """Enum for finance restriction types"""
    AMOUNT_TO_FINANCE = "amount_to_finance"
    INVOICE_VALUE = "invoice_value"
    AMOUNT_AND_INVOICE = "amount_and_invoice"


class InterestType(str, Enum):
    """Enum for interest types"""
    AVG_INTEREST = "avg_interest"
    INTEREST_PER_TERM = "interest_per_term"


class RequirementType(str, Enum):
    """Enum for requirement types"""
    FIELD = "field"
    DOCUMENT = "document"


class RequirementStatus(str, Enum):
    """Enum for requirement status"""
    REQUIRED = "required"
    SUGGESTED = "suggested"


class Banco(SQLModel, table=True):
    """
    Bank model
    Table: bancos
    """
    __tablename__ = "bancos"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    valor_factura: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    minimo_financiar: Optional[int] = Field(default=None)


class FinancingOption(SQLModel, table=True):
    """
    Bank financing option model
    Table: banks_offers
    """
    __tablename__ = "banks_offers"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    banco_id: int = Field(foreign_key="bancos.id", index=True)
    bank_offer_name: Optional[str] = Field(default=None, max_length=255)
    lowest_interest_rate: float = Field(ge=0)
    highest_interest_rate: float = Field(ge=0)
    opening_fee: float = Field(ge=0)
    min_invoice_value: int = Field(ge=0)
    max_invoice_value: int = Field(ge=0)
    min_downpayment: float = Field(ge=0)
    max_downpayment: float = Field(ge=0)
    min_loan_term_months: int = Field(ge=1)
    max_loan_term_months: int = Field(ge=1)
    income_proof: Optional[bool] = Field(default=None)
    start_date: date
    end_date: date
    is_active: bool = Field(default=True, index=True)
    min_amount_to_finance: Optional[float] = Field(default=None, ge=0)
    max_amount_to_finance: Optional[float] = Field(default=None, ge=0)
    amount_to_finance_restriction_type: Optional[FinanceRestrictionType] = Field(default=None, max_length=50)
    interest_type: Optional[InterestType] = Field(default=None, max_length=50)
    interest_term: Optional[dict] = Field(default=None, sa_column=Column(JSONB))


class BankOffersMotorcycles(SQLModel, table=True):
    """
    Through model for FinancingOption <-> Motorcycles relationship
    Table: bank_offers_motorcycles
    """
    __tablename__ = "bank_offers_motorcycles"
    
    bank_offer_id: int = Field(foreign_key="banks_offers.id", primary_key=True)
    motorcycle_id: int = Field(foreign_key="motorcycles.id", primary_key=True)


class BankOffersBrands(SQLModel, table=True):
    """
    Through model for FinancingOption <-> MotorcycleBrand relationship
    Table: bank_offers_brands
    """
    __tablename__ = "bank_offers_brands"
    
    bank_offer_id: int = Field(foreign_key="banks_offers.id", primary_key=True)
    brand_id: int = Field(foreign_key="motorcycle_brands.id", primary_key=True)


class BankOfferRequirement(SQLModel, table=True):
    """
    Bank offer requirement model
    Table: banks_offers_requirements
    """
    __tablename__ = "banks_offers_requirements"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    bank_offer_id: int = Field(foreign_key="banks_offers.id", index=True)
    type_requirement: RequirementType
    requirement_key: Optional[str] = Field(default=None, max_length=255)
    requirement_status: RequirementStatus
    validation_rule: str = Field(max_length=255)
    conditional_requirement_group: Optional[str] = Field(default=None, max_length=100)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})

