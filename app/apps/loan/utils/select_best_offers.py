"""
Select best offers per bank
Async-compatible version migrated from Flask app/loan/utils/_select_best_offers.py
"""
from typing import Dict, List, Optional, Union
import json
import logging

from app.apps.quote.models import FinancingOption

logger = logging.getLogger(__name__)


def calculate_interest_rate(offer: FinancingOption, loan_term_months: Optional[int] = None) -> float:
    """
    Calculate the appropriate interest rate for an offer based on its type and loan term.
    
    Enhanced logic that supports:
    - Term-based interest rates (INTEREST_PER_TERM)
    - Average interest rates (AVG_INTEREST) 
    - Fallback to original calculation
    """
    # Check if offer has the new interest type system
    if hasattr(offer, 'interest_type') and offer.interest_type:
        # Handle term-based interest rates
        if (offer.interest_type.value == 'interest_per_term' if hasattr(offer.interest_type, 'value') else offer.interest_type == 'INTEREST_PER_TERM') and offer.interest_term and loan_term_months:
            try:
                # Parse JSON if it's stored as string
                if isinstance(offer.interest_term, str):
                    term_rates = json.loads(offer.interest_term)
                else:
                    term_rates = offer.interest_term
                
                # Look for exact match first
                if str(loan_term_months) in term_rates:
                    rate = float(term_rates[str(loan_term_months)])
                    logger.info(f"Term-based rate: {loan_term_months}mo = {rate}%")
                    return rate
                
                # If no exact match, find the closest term
                available_terms = [int(term) for term in term_rates.keys()]
                closest_term = min(available_terms, key=lambda x: abs(x - loan_term_months))
                rate = float(term_rates[str(closest_term)])
                logger.info(f"Term-based rate: {closest_term}mo (closest) = {rate}%")
                return rate
                
            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                # Fallback to original calculation if JSON parsing fails
                logger.error(f"Term-based rate failed: {e}")
                return calculate_fallback_interest_rate(offer)
        
        # Handle average interest rate calculation
        elif (offer.interest_type.value == 'avg_interest' if hasattr(offer.interest_type, 'value') else offer.interest_type == 'AVG_INTEREST'):
            return calculate_fallback_interest_rate(offer)
    
    # Fallback to original calculation for backward compatibility
    return calculate_fallback_interest_rate(offer)


def calculate_fallback_interest_rate(offer: FinancingOption) -> float:
    """
    Fallback calculation using the original method.
    
    This maintains backward compatibility with existing offers that don't have
    the new interest type system.
    """
    rate = (offer.lowest_interest_rate + offer.highest_interest_rate) / 2
    logger.info(f"Fallback rate: {rate}%")
    return rate


def select_best_offers(
    valid_offers: List[FinancingOption], 
    income_proof: Optional[List[str]], 
    simulation: Optional[bool] = False, 
    loan_term_months: Optional[int] = None
) -> Dict[int, Dict[str, Union[float, bool]]]:
    """
    Select the best offer for each bank based on interest rate.
    
    Enhanced to support term-based interest rates while maintaining backward compatibility.
    
    Args:
        valid_offers: List of valid financing options
        income_proof: List of income proof documents provided
        simulation: Whether this is a simulation (bypasses income proof requirements)
        loan_term_months: Loan term in months (used for term-based rate calculation)
    
    Returns:
        Dictionary with bank_id as key and offer details as value
    """
    logger.info(f"[SELECT_BEST_OFFERS] Evaluating {len(valid_offers)} offers for {loan_term_months} months")
    
    best_offers = {}
    for i, offer in enumerate(valid_offers):
        banco_id = offer.banco_id
        
        # Calculate interest rate using enhanced logic
        interest_rate = calculate_interest_rate(offer, loan_term_months)
        logger.info(f"Offer {i+1} (Bank {banco_id}): Rate {interest_rate}%")

        if banco_id not in best_offers or best_offers[banco_id]['avg_interest_rate'] > interest_rate:
            best_offers[banco_id] = {
                'avg_interest_rate': interest_rate,
                'opening_fee': offer.opening_fee,
            }
    
    logger.info(f"Selected {len(best_offers)} banks")
    
    return best_offers


