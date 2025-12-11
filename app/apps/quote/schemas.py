"""
Pydantic schemas for quote module
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date


class GenerateQuoteRequest(BaseModel):
    """Generate quote request schema"""
    loan_term_months: int
    down_payment_amount: float
    motorcycle_id: int
    paquete: str
    insurance_payment_method: str
    holding: Optional[str] = None
    send_notification: bool = False
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    user_id: Optional[int] = None


class QuoteDetail(BaseModel):
    """Quote detail schema"""
    initial_payment: float
    down_payment: float
    opening_fee_payment: float
    loan_term_months: int
    monthly_payment: float
    total_loan_amount: float
    amount_to_finance: float
    insurance_amount: float
    life_unemployment_insurance_amount: float
    coverage_names: List[str]
    insurance_applied: bool
    insurance_method: str


class BankQuote(BaseModel):
    """Bank quote schema"""
    bank: str
    bank_logo: Optional[str] = None
    quote: QuoteDetail
    # Additional fields from best_offer
    avg_interest_rate: Optional[float] = None
    opening_fee: Optional[float] = None
    bank_offer_id: Optional[int] = None


class GenerateQuoteResponse(BaseModel):
    """Generate quote response schema"""
    quotes: List[BankQuote]
    motorcycle_id: int
    invoice_motorcycle_value: float
    down_payment_amount: float
    loan_term_months: int
    insurance_amount: float
    coverage_names: List[str]


class FinancingOptionResponse(BaseModel):
    """Financing option response schema"""
    id: int
    banco_id: int
    bank_offer_name: Optional[str] = None
    lowest_interest_rate: float
    highest_interest_rate: float
    opening_fee: float
    min_invoice_value: int
    max_invoice_value: int
    min_downpayment: float
    max_downpayment: float
    min_loan_term_months: int
    max_loan_term_months: int
    income_proof: Optional[bool] = None
    start_date: date
    end_date: date
    is_active: bool
    min_amount_to_finance: Optional[float] = None
    max_amount_to_finance: Optional[float] = None
    amount_to_finance_restriction_type: Optional[str] = None
    interest_type: Optional[str] = None
    interest_term: Optional[dict] = None
    
    class Config:
        from_attributes = True

