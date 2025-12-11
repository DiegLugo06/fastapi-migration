"""
Quote router
Migrated from Flask app/quote/routes.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional, List
import logging
import asyncio
import xml.etree.ElementTree as ET
from datetime import date

from app.database import get_async_session
from app.apps.authentication.dependencies import get_current_user
from app.apps.quote.models import Banco, FinancingOption
from app.apps.quote.schemas import (
    GenerateQuoteRequest,
    GenerateQuoteResponse,
    BankQuote,
    QuoteDetail,
)
from app.apps.product.models import Motorcycles, MotorcycleBrand, MotorcycleQualitasAmis
from app.apps.advisor.utils._fetch_user import _fetch_user
from app.apps.advisor.utils._fetch_store import _fetch_sucursal
from app.apps.advisor.utils._fetch_banks import _fetch_banks_for_sucursal
from app.apps.quote.services.qualitas_service import get_qualitas_service
from app.config import FRONTEND_URL

logger = logging.getLogger(__name__)

router = APIRouter()

BANK_DOMAINS = {
    "Santander": "santander.com",
    "Bbva": "bbva.com",
    "Hey": "heybanco.com",
    "Scotiabank": "scotiabank.com",
    "HSBC": "hsbc.com",
    "Banorte": "banorte.com",
    "Inbursa": "inbursa.com",
    "Afirme": "afirme.com",
    "Banregio": "banregio.com",
    "Maxikash": "maxikash.com",
    "Galgo": "galgo.com",
    "Creditogo": "creditogo.mx",
}


def calculate_loan_payment(principal: float, annual_rate: float, months: int) -> float:
    """
    Calculate monthly loan payment using standard amortization formula.
    """
    if months == 0 or annual_rate == 0:
        return principal / months if months > 0 else 0
    
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        return principal / months
    
    payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    return round(payment, 2)


async def _fetch_valid_financing_offers(
    invoice_value: float,
    request_date: date,
    bank_ids: List[int],
    loan_term_months: int,
    down_payment_amount: float,
    motorcycle_id: Optional[int],
    brand_name: Optional[str],
    session: AsyncSession,
) -> dict:
    """
    Fetch valid financing offers with optional motorcycle and brand filters.
    TODO: Implement full logic from loan/utils/_fetch_bank_offers.py
    """
    # Simplified version - will need full implementation
    amount_to_finance = invoice_value * (1 - down_payment_amount)
    
    # Base query for active offers
    stmt = select(FinancingOption).where(
        FinancingOption.start_date <= request_date,
        FinancingOption.end_date >= request_date,
        FinancingOption.is_active == True,
        FinancingOption.banco_id.in_(bank_ids),
        FinancingOption.min_loan_term_months <= loan_term_months,
        FinancingOption.max_loan_term_months >= loan_term_months,
        FinancingOption.min_downpayment <= down_payment_amount,
        FinancingOption.max_downpayment >= down_payment_amount,
        FinancingOption.min_invoice_value <= invoice_value,
        FinancingOption.max_invoice_value >= invoice_value,
    )
    
    result = await session.execute(stmt)
    offers = result.scalars().all()
    
    # TODO: Apply motorcycle and brand filters
    # TODO: Apply financing amount restrictions
    
    valid_offers = []
    for offer in offers:
        valid_offers.append({
            "id": offer.id,
            "banco_id": offer.banco_id,
            "avg_interest_rate": (offer.lowest_interest_rate + offer.highest_interest_rate) / 2,
            "opening_fee": offer.opening_fee,
            "bank_offer_name": offer.bank_offer_name,
        })
    
    return {"valid_offers": valid_offers}


def _select_best_offers(valid_offers: List[dict], income_proof: List[str], has_income_proof: bool, loan_term_months: int) -> dict:
    """
    Select the best offer for each bank.
    TODO: Implement full logic from loan/utils/_select_best_offers.py
    """
    # Simplified version - select first offer per bank
    best_offers = {}
    for offer in valid_offers:
        bank_id = offer["banco_id"]
        if bank_id not in best_offers:
            best_offers[bank_id] = offer
    
    return best_offers


@router.post("/quote", response_model=GenerateQuoteResponse, status_code=status.HTTP_200_OK)
async def generate_bank_quotes(
    request: GenerateQuoteRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
):
    """
    Generate bank quotes for a motorcycle financing request.
    """
    try:
        logger.info("Received request to generate bank quotes")
        
        # Validate notification parameters if notification is True
        if request.send_notification:
            if not request.client_email and not request.client_phone:
                logger.warning(
                    "Notification requested but no contact method provided"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Notification requested but missing contact information",
                        "details": "Either client_email or client_phone must be provided",
                    }
                )
        
        # Handle Sfera holding
        if request.holding == "Sfera":
            # TODO: Implement get_sferea_quote
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Sfera quote not yet implemented"
            )
        
        # OPTIMIZATION: Fetch motorcycle and brand in parallel
        async def fetch_motorcycle():
            stmt = select(Motorcycles).where(Motorcycles.id == request.motorcycle_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        
        # Start fetching motorcycle
        motorcycle_task = asyncio.create_task(fetch_motorcycle())
        
        # Wait for motorcycle first (we need brand_id)
        motorcycle = await motorcycle_task
        
        if not motorcycle:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid motorcycle_id provided, motorcycle not found: {request.motorcycle_id}"
            )
        
        # Now fetch brand in parallel with other queries
        async def fetch_brand():
            stmt = select(MotorcycleBrand).where(MotorcycleBrand.id == motorcycle.brand_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        
        brand_task = asyncio.create_task(fetch_brand())
        brand = await brand_task
        
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid brand_name provided, brand not found"
            )
        
        brand_name = brand.name
        model_value = motorcycle.year
        invoice_motorcycle_value = motorcycle.price
        
        # OPTIMIZATION: Run independent queries in parallel
        # Prepare tasks for parallel execution
        tasks = {}
        
        # Task 1: Fetch banks (conditional)
        if request.user_id:
            async def fetch_banks_task():
                user = await _fetch_user(request.user_id, session)
                if not user:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
                
                sucursal = await _fetch_sucursal(user.id, session)
                if not sucursal:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal not found for the user")
                
                banks = await _fetch_banks_for_sucursal(sucursal.id, session)
                if not banks:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Banks not found for the sucursal {sucursal.nombre}"
                    )
                return banks
            tasks["banks"] = fetch_banks_task()
        else:
            async def fetch_all_banks_task():
                stmt = select(Banco)
                result = await session.execute(stmt)
                return result.scalars().all()
            tasks["banks"] = fetch_all_banks_task()
        
        # Task 2: Fetch Qualitas AMIS key
        async def fetch_qualitas_task():
            stmt = select(MotorcycleQualitasAmis).where(
                MotorcycleQualitasAmis.motorcycle_id == request.motorcycle_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        tasks["qualitas"] = fetch_qualitas_task()
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Extract results
        banks = None
        clave_ami = None
        for task_name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                if isinstance(result, HTTPException):
                    raise result
                logger.error(f"Error in {task_name} task: {result}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(result))
            
            if task_name == "banks":
                banks = result
            elif task_name == "qualitas":
                clave_ami = result
        
        bank_ids = [bank.id for bank in banks] if banks else []
        logger.info(f"Found {len(bank_ids)} banks associated")
        
        # Get insurance amount (placeholder - requires Qualitas service)
        insurance_amount = 0
        coverage_names = []
        
        if clave_ami:
            try:
                clave_amis = clave_ami.clave_amis_qualitas
                # OPTIMIZATION: Run Qualitas API call in background to avoid blocking
                # Use asyncio.to_thread for CPU-bound or blocking I/O operations
                service = get_qualitas_service()
                
                # If service.get_quote is blocking, run it in a thread pool
                if hasattr(asyncio, 'to_thread'):
                    # Python 3.9+
                    insurance_response = await asyncio.to_thread(
                        service.get_quote,
                        clave_amis=clave_amis,
                        paquete=request.paquete,
                        vehicle_cost=invoice_motorcycle_value,
                        model=model_value,
                        postal_code="53100",
                    )
                else:
                    # Fallback for older Python versions
                    loop = asyncio.get_event_loop()
                    insurance_response = await loop.run_in_executor(
                        None,
                        lambda: service.get_quote(
                            clave_amis=clave_amis,
                            paquete=request.paquete,
                            vehicle_cost=invoice_motorcycle_value,
                            model=model_value,
                            postal_code="53100",
                        )
                    )
                
                if insurance_response.get("success"):
                    insurance_data = insurance_response.get("data", {})
                    insurance_amount = insurance_data.get("prima_total", 0)
                    coverage_names = insurance_data.get("coverage_names", [])
                    logger.info(f"Got insurance quote: {insurance_amount}")
                else:
                    logger.warning(
                        f"Failed to get insurance quote: {insurance_response.get('error')}"
                    )
            except Exception as e:
                logger.error(f"Error getting insurance quote: {str(e)}")
        
        # Fetch valid financing offers
        today_date = date.today()
        offers_data = await _fetch_valid_financing_offers(
            invoice_motorcycle_value,
            today_date,
            bank_ids,
            request.loan_term_months,
            request.down_payment_amount,
            request.motorcycle_id,
            brand_name,
            session,
        )
        valid_offers = offers_data.get("valid_offers", [])
        logger.info(f"Found {len(valid_offers)} valid offers to evaluate")
        
        # Select the best offer for each bank
        income_proof = ["Simulation"]
        best_offers = _select_best_offers(valid_offers, income_proof, True, request.loan_term_months)
        logger.info(f"Selected best offers for {len(best_offers)} banks")
        
        quotes = []
        down_payment = invoice_motorcycle_value * request.down_payment_amount
        
        for bank_id, best_offer in best_offers.items():
            bank = next((bank for bank in banks if bank.id == bank_id), None)
            if not bank:
                continue
            
            bank_name = bank.name.title()
            bank_name_upper = bank_name.upper()
            interest_rate = best_offer.get("avg_interest_rate", 0)
            opening_fee = best_offer.get("opening_fee", 0)
            
            insurance_payment_method_normalized = request.insurance_payment_method.lower() if request.insurance_payment_method else ""
            
            # Calculate life and unemployment insurance amount
            life_unemployment_insurance_amount = invoice_motorcycle_value * 0.015
            amount_to_finance = invoice_motorcycle_value * (1 - request.down_payment_amount)
            opening_fee_payment = amount_to_finance * opening_fee
            bank_logo = BANK_DOMAINS.get(bank_name, "")
            
            # Create base quote data
            base_quote_data = {
                **best_offer,
                "bank": bank_name,
                "bank_logo": bank_logo if bank_logo else None,
            }
            
            # Generate quote without insurance
            quote_without_insurance = {
                **base_quote_data,
                "quote": {
                    "initial_payment": down_payment + opening_fee_payment,
                    "down_payment": down_payment,
                    "opening_fee_payment": opening_fee_payment,
                    "loan_term_months": request.loan_term_months,
                    "monthly_payment": calculate_loan_payment(
                        amount_to_finance, interest_rate, request.loan_term_months
                    ),
                    "total_loan_amount": (
                        (
                            calculate_loan_payment(
                                amount_to_finance, interest_rate, request.loan_term_months
                            )
                            * request.loan_term_months
                        )
                        + opening_fee_payment
                        + down_payment
                    ),
                    "amount_to_finance": amount_to_finance,
                    "insurance_amount": 0,
                    "life_unemployment_insurance_amount": 0,
                    "coverage_names": [],
                    "insurance_applied": False,
                    "insurance_method": "Sin Seguro",
                },
            }
            
            # Always add quote without insurance first (matching Flask behavior)
            quotes.append(BankQuote(**quote_without_insurance))
            
            # Generate quote with insurance (only if insurance_amount > 0)
            if insurance_amount > 0:
                special_banks = ["HEY", "BBVA", "SANTANDER", "BANREGIO", "CREDITOGO"]
                is_special_bank = bank_name_upper in special_banks
                
                if insurance_payment_method_normalized == "financiado":
                    if not is_special_bank:
                        amount_to_finance_with_insurance = amount_to_finance + insurance_amount
                    else:
                        amount_to_finance_with_insurance = amount_to_finance + insurance_amount + life_unemployment_insurance_amount
                else:
                    amount_to_finance_with_insurance = amount_to_finance

                if insurance_payment_method_normalized == "contado":
                    if not is_special_bank:
                        initial_payment = down_payment + opening_fee_payment + insurance_amount
                    else:
                        initial_payment = down_payment + opening_fee_payment + insurance_amount + life_unemployment_insurance_amount
                else:
                    initial_payment = down_payment + opening_fee_payment

                monthly_payment_with_insurance = calculate_loan_payment(
                    amount_to_finance_with_insurance, interest_rate, request.loan_term_months
                )
                total_loan_amount_with_insurance = (
                    monthly_payment_with_insurance * request.loan_term_months
                ) + initial_payment

                quote_with_insurance = {
                    **base_quote_data,
                    "quote": {
                        "initial_payment": initial_payment,
                        "down_payment": down_payment,
                        "opening_fee_payment": opening_fee_payment,
                        "loan_term_months": request.loan_term_months,
                        "monthly_payment": monthly_payment_with_insurance,
                        "total_loan_amount": total_loan_amount_with_insurance,
                        "amount_to_finance": amount_to_finance_with_insurance,
                        "insurance_amount": insurance_amount,
                        "life_unemployment_insurance_amount": life_unemployment_insurance_amount,
                        "coverage_names": coverage_names,
                        "insurance_applied": True,
                        "insurance_method": request.insurance_payment_method,
                    },
                }
                
                # Add quote with insurance only if insurance amount is available
                quotes.append(BankQuote(**quote_with_insurance))
        
        # TODO: Send notification if requested
        # This requires migrating _send_financing_quotes_email
        
        return GenerateQuoteResponse(
            quotes=quotes,
            motorcycle_id=request.motorcycle_id,
            invoice_motorcycle_value=invoice_motorcycle_value,
            down_payment_amount=request.down_payment_amount,
            loan_term_months=request.loan_term_months,
            insurance_amount=insurance_amount,
            coverage_names=coverage_names,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating bank quotes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating quotes: {str(e)}"
        )


@router.post("/qualitas-emision", status_code=status.HTTP_200_OK)
async def obtener_emision(
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Qualitas emision endpoint.
    Receives XML data and processes it through Qualitas service.
    """
    try:
        # Get raw XML data from request body
        xml_data = await request.body()
        xml_data = xml_data.decode("utf-8")

        if not xml_data or xml_data.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="XML data is required"
            )

        logger.info(f"Sending XML data to Qualitas: {xml_data}")

        service = get_qualitas_service()
        response = service.obtener_nueva_emision(xml_data)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in emision endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/lista-tarifas", status_code=status.HTTP_200_OK)
@router.options("/lista-tarifas", status_code=status.HTTP_200_OK)
async def lista_tarifas(
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Qualitas lista tarifas endpoint.
    Receives XML data and processes it through Qualitas service.
    """
    if request.method == "OPTIONS":
        return Response("", status_code=status.HTTP_200_OK)

    try:
        # Get raw XML data from request body
        xml_data = await request.body()
        xml_data = xml_data.decode("utf-8")

        # Parse XML data into required format
        try:
            root = ET.fromstring(xml_data)
            data = {
                "cUsuario": root.findtext(".//cUsuario", ""),
                "cTarifa": root.findtext(".//cTarifa", ""),
                "cMarca": root.findtext(".//cMarca", ""),
                "cTipo": root.findtext(".//cTipo", ""),
                "cVersion": root.findtext(".//cVersion", ""),
                "cModelo": root.findtext(".//cModelo", ""),
                "cCAMIS": root.findtext(".//cCAMIS", ""),
                "cCategoria": root.findtext(".//cCategoria", ""),
                "cNvaAMIS": root.findtext(".//cNvaAMIS", ""),
            }
        except ET.ParseError as e:
            logger.error(f"Error parsing XML: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid XML format: {str(e)}"
            )

        service = get_qualitas_service()
        response = service.get_listTarifas(data)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in lista-tarifas endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/get_qualitas_quote", status_code=status.HTTP_200_OK)
async def get_qualitas_quote(
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Get Qualitas insurance quote.
    
    Expected JSON body:
    {
        "clave_amis": "string",
        "paquete": "string",
        "vehicle_cost": float (optional),
        "model": int (optional)
    }
    """
    try:
        data = await request.json()

        # Extract required parameters
        clave_amis = data.get("clave_amis")
        paquete = data.get("paquete")
        vehicle_cost = data.get("vehicle_cost")
        model = data.get("model")

        # Validate required parameters
        if not clave_amis or not paquete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="clave_amis and paquete are required"
            )

        service = get_qualitas_service()
        response = service.get_quote(
            clave_amis=clave_amis,
            paquete=paquete,
            vehicle_cost=vehicle_cost,
            model=model,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_qualitas_quote endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

