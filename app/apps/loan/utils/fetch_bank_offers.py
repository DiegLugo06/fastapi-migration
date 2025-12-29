"""
Fetch valid financing offers
Async version migrated from Flask app/loan/utils/_fetch_bank_offers.py
"""
from datetime import date
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import logging

from app.apps.quote.models import FinancingOption, FinanceRestrictionType, BankOffersMotorcycles, BankOffersBrands
from app.apps.product.models import MotorcycleBrand

logger = logging.getLogger(__name__)


def _is_offer_valid_for_financing_amount(
    offer: FinancingOption, 
    invoice_value: float, 
    amount_to_finance: float
) -> bool:
    """Check if an offer is valid based on its financing amount restrictions."""
    
    # If no restriction type is set, use default behavior (invoice value only)
    if offer.amount_to_finance_restriction_type is None:
        return True  # Already filtered by invoice value in main query
    
    # If no min/max values are set, use default behavior
    if offer.min_amount_to_finance is None and offer.max_amount_to_finance is None:
        return True
    
    # Validate min/max values are logical
    if offer.min_amount_to_finance is not None and offer.max_amount_to_finance is not None:
        if offer.min_amount_to_finance > offer.max_amount_to_finance:
            logger.warning(f"Bank Offer {offer.id}: Invalid range min=${offer.min_amount_to_finance:,.0f} > max=${offer.max_amount_to_finance:,.0f}")
            return False
    
    # Apply restrictions based on restriction type
    if offer.amount_to_finance_restriction_type == FinanceRestrictionType.AMOUNT_TO_FINANCE:
        # Check financing amount restrictions
        if offer.min_amount_to_finance and amount_to_finance < offer.min_amount_to_finance:
            logger.info(f"Bank {offer.banco_id}: Finance ${amount_to_finance:,.0f} < min ${offer.min_amount_to_finance:,.0f}")
            return False
        if offer.max_amount_to_finance and amount_to_finance > offer.max_amount_to_finance:
            logger.info(f"Bank {offer.banco_id}: Finance ${amount_to_finance:,.0f} > max ${offer.max_amount_to_finance:,.0f}")
            return False
        
    elif offer.amount_to_finance_restriction_type == FinanceRestrictionType.INVOICE_VALUE:
        # Check invoice value restrictions
        if offer.min_amount_to_finance and invoice_value < offer.min_amount_to_finance:
            logger.info(f"Bank {offer.banco_id}: Invoice ${invoice_value:,.0f} < min ${offer.min_amount_to_finance:,.0f}")
            return False
        if offer.max_amount_to_finance and invoice_value > offer.max_amount_to_finance:
            logger.info(f"Bank {offer.banco_id}: Invoice ${invoice_value:,.0f} > max ${offer.max_amount_to_finance:,.0f}")
            return False
        
    elif offer.amount_to_finance_restriction_type == FinanceRestrictionType.AMOUNT_AND_INVOICE:
        # Check both financing amount and invoice value restrictions
        # Check financing amount
        if offer.min_amount_to_finance and amount_to_finance < offer.min_amount_to_finance:
            logger.info(f"Bank {offer.banco_id}: Finance ${amount_to_finance:,.0f} < min ${offer.min_amount_to_finance:,.0f}")
            return False
        if offer.max_amount_to_finance and amount_to_finance > offer.max_amount_to_finance:
            logger.info(f"Bank {offer.banco_id}: Finance ${amount_to_finance:,.0f} > max ${offer.max_amount_to_finance:,.0f}")
            return False
        # Check invoice value
        if offer.min_amount_to_finance and invoice_value < offer.min_amount_to_finance:
            logger.info(f"Bank {offer.banco_id}: Invoice ${invoice_value:,.0f} < min ${offer.min_amount_to_finance:,.0f}")
            return False
        if offer.max_amount_to_finance and invoice_value > offer.max_amount_to_finance:
            logger.info(f"Bank {offer.banco_id}: Invoice ${invoice_value:,.0f} > max ${offer.max_amount_to_finance:,.0f}")
            return False
    
    return True


async def fetch_valid_financing_offers(
    invoice_value: float,
    request_date: date,
    bank_ids: List[int],
    loan_term_months: int,
    down_payment_amount: float,
    session: AsyncSession,
    motorcycle_id: Optional[int] = None,
    brand_name: Optional[str] = None,
    validation_offers_only: bool = False,
) -> Dict:
    """Fetch valid financing offers with optional motorcycle and brand filters (async version)."""
    
    # Calculate amount to finance for debugging
    invoice_float = float(invoice_value) if invoice_value is not None else 0.0
    down_payment_float = float(down_payment_amount) if down_payment_amount is not None else 0.0
    amount_to_finance = invoice_float * (1 - down_payment_float)
    
    logger.info(f"[FETCH] Invoice=${invoice_float:,.0f}, Down={down_payment_float:.0%}, Finance=${amount_to_finance:,.0f}, Term={loan_term_months}mo, Banks={bank_ids}")
    
    # Start with empty set for valid offer IDs
    valid_offer_ids = set()

    # If motorcycle_id is provided, get bank offer IDs from motorcycle association
    if motorcycle_id:
        stmt_moto = select(BankOffersMotorcycles.bank_offer_id).where(
            BankOffersMotorcycles.motorcycle_id == motorcycle_id
        )
        result_moto = await session.execute(stmt_moto)
        motorcycle_offer_ids = {row[0] for row in result_moto.all()}
        valid_offer_ids.update(motorcycle_offer_ids)

    # If brand_name is provided, get bank offer IDs from brand association
    if brand_name:
        # First check if brand exists and get its ID
        stmt_brand = select(MotorcycleBrand).where(MotorcycleBrand.name == brand_name)
        result_brand = await session.execute(stmt_brand)
        brand = result_brand.scalar_one_or_none()
        
        if brand:
            stmt_brand_offers = select(BankOffersBrands.bank_offer_id).where(
                BankOffersBrands.brand_id == brand.id
            )
            result_brand_offers = await session.execute(stmt_brand_offers)
            brand_offer_ids = {row[0] for row in result_brand_offers.all()}
            valid_offer_ids.update(brand_offer_ids)
    
    # Build base query filters
    base_filters = [
        FinancingOption.start_date <= request_date,
        FinancingOption.end_date >= request_date,
        FinancingOption.is_active == True,
        FinancingOption.banco_id.in_(bank_ids),
        FinancingOption.min_invoice_value <= invoice_float,
        FinancingOption.max_invoice_value >= invoice_float,
    ]
    
    if not validation_offers_only:
        # Apply down payment and finance term filters
        base_filters.extend([
            FinancingOption.min_loan_term_months <= loan_term_months,
            FinancingOption.max_loan_term_months >= loan_term_months,
            FinancingOption.min_downpayment <= down_payment_float,
            FinancingOption.max_downpayment >= down_payment_float,
        ])
    
    # Apply ID filter if we have any valid offer IDs
    if motorcycle_id or brand_name:
        if valid_offer_ids:
            base_filters.append(FinancingOption.id.in_(valid_offer_ids))
        else:
            # No matching offers found
            logger.info(f"[FILTER] No offers found for motorcycle_id={motorcycle_id}, brand_name={brand_name}")
            return {"valid_offers": [], "optional_offers": []}
    
    # Get all offers matching base filters
    stmt = select(FinancingOption).where(and_(*base_filters))
    result = await session.execute(stmt)
    all_offers = result.scalars().all()
    
    logger.info(f"[FILTER] Found {len(all_offers)} offers after base filtering")
    
    # Separate offers into valid and optional based on down payment and finance term filters
    valid_offers = []
    optional_offers = []
    restriction_types_found = set()
    
    for offer in all_offers:
        # Track restriction type
        if offer.amount_to_finance_restriction_type:
            restriction_types_found.add(offer.amount_to_finance_restriction_type.value)
        
        # Check if offer passes financing amount restrictions
        is_financing_valid = _is_offer_valid_for_financing_amount(offer, invoice_float, amount_to_finance)
        
        if validation_offers_only:
            # When validation_offers_only is True, separate offers based on down payment and finance term filters
            passes_down_payment = (offer.min_downpayment <= down_payment_float and 
                                  offer.max_downpayment >= down_payment_float)
            passes_finance_term = (offer.min_loan_term_months <= loan_term_months and 
                                  offer.max_loan_term_months >= loan_term_months)
            
            if is_financing_valid and passes_down_payment and passes_finance_term:
                # Valid offer - passes all filters
                valid_offers.append(offer)
            elif is_financing_valid and (not passes_down_payment or not passes_finance_term):
                # Optional offer - passes basic filters but fails down payment or finance term
                optional_offers.append(offer)
        else:
            # When validation_offers_only is False, all offers already passed down payment and finance term filters
            # Only need to check financing amount restrictions
            if is_financing_valid:
                valid_offers.append(offer)
    
    # Summary of restriction types found
    if restriction_types_found:
        logger.info(f"[RESTRICTIONS] Types: {', '.join(restriction_types_found)}")
    else:
        logger.info(f"[RESTRICTIONS] No financing restrictions (using defaults)")
    
    if validation_offers_only:
        logger.info(f"[RESULT] {len(valid_offers)} valid offers, {len(optional_offers)} optional offers")
    else:
        logger.info(f"[RESULT] {len(valid_offers)} valid offers")
    
    return {
        "valid_offers": valid_offers,
        "optional_offers": optional_offers
    }


