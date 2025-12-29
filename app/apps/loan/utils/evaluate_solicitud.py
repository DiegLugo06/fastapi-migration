"""
Main evaluation logic for solicitudes
Migrated from Flask app/loan/utils/_evaluate_solicitud.py
"""
from typing import Dict, List, Optional
import re
import logging
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.apps.loan.models import Solicitud
from app.apps.client.models import Report, Cliente
from app.apps.quote.models import Banco, FinancingOption
from app.apps.loan.utils.evaluation_helpers import (
    fetch_solicitud,
    fetch_reports_by_client_id,
    calculate_amount_to_finance,
)
from app.apps.loan.utils.fetch_bank_offers import fetch_valid_financing_offers
from app.apps.loan.utils.select_best_offers import select_best_offers
from app.apps.loan.utils.extract_credit_data import extract_credit_data
from app.apps.loan.utils.combine_bank_data import combine_bank_data
from app.apps.loan.utils.validate_auto_financing_assignment import validate_auto_financing_assignment

logger = logging.getLogger(__name__)


def process_payments(accounts: List[Dict]) -> str:
    """
    Process payment data from accounts to determine payment status.
    Simplified async-compatible version.
    """
    if not accounts:
        return "No accounts found"
    
    max_status_code = 0
    payment_totals = {"last": 0, "next": 0}
    
    for account in accounts:
        payment_totals["last"] += account.get("montoUltimoPago", 0) or 0
        payment_totals["next"] += account.get("montoPagar", 0) or 0
        
        if payment_history := account.get("historicoPagos"):
            payment_history = payment_history.replace("X", "0").replace("U", "0")[::-1]
            try:
                if (code := int(payment_history[-1])) > max_status_code:
                    max_status_code = code
            except (ValueError, IndexError):
                pass
    
    if max_status_code == 1:
        return "Al corriente"
    elif 1 < max_status_code <= 4:
        return "Atraso 1 a 89 días"
    else:
        return "Más de 90 días o sin recuperar"


async def evaluate_solicitud_logic(
    solicitud_id: int, 
    session: AsyncSession
) -> Dict:
    """
    Core logic for evaluating financing options and creditworthiness for a given solicitud.
    Returns evaluation results as a dictionary.
    Async version migrated from Flask.
    """
    try:
        logger.info(f"Starting evaluation for solicitud_id: {solicitud_id}")

        # Fetch solicitud and validate existence
        solicitud = await fetch_solicitud(solicitud_id, session)
        if not solicitud:
            return {"error": "Solicitud not found", "status_code": 404}
        
        # Fetch cliente for evaluation
        stmt_cliente = select(Cliente).where(Cliente.id == solicitud.cliente_id)
        result_cliente = await session.execute(stmt_cliente)
        cliente = result_cliente.scalar_one_or_none()
        if not cliente:
            return {"error": "Cliente not found for solicitud", "status_code": 404}

        # Fetch all banks
        stmt_banks = select(Banco)
        result_banks = await session.execute(stmt_banks)
        banks = result_banks.scalars().all()
        bank_ids = [bank.id for bank in banks]

        # Calculate amount to finance
        amount_to_finance = calculate_amount_to_finance(solicitud)
        logger.info(f"Amount to finance calculated: {amount_to_finance}")

        # Get loan term months from solicitud data
        loan_term_months = 0
        if solicitud.finance_term_months:
            if str(solicitud.finance_term_months).isdigit():
                loan_term_months = int(solicitud.finance_term_months)
            else:
                # Extract numeric value if it contains text like "36 Meses (3 años)"
                match = re.search(r"\d+", str(solicitud.finance_term_months))
                if match:
                    loan_term_months = int(match.group())

        # Fetch valid financing offers and select best offers
        best_offers = {}
        
        if not loan_term_months or loan_term_months == 0:
            logger.warning(
                f"finance_term_months is missing or invalid in solicitud {solicitud_id}. Value: {solicitud.finance_term_months}"
            )
        else:
            logger.info(f"Loan term months: {loan_term_months}")
            # Convert datetime to date if needed
            request_date = solicitud.created_at.date() if hasattr(solicitud.created_at, 'date') else solicitud.created_at
            
            # Handle null values and convert to float
            invoice_value = float(solicitud.invoice_motorcycle_value) if solicitud.invoice_motorcycle_value is not None else 0.0
            percentage_down_payment = float(solicitud.percentage_down_payment) if solicitud.percentage_down_payment is not None else 0.0
            
            if invoice_value == 0.0:
                logger.warning(f"Invoice value is null or zero for solicitud {solicitud_id}")
            else:
                offers_data = await fetch_valid_financing_offers(
                    invoice_value,
                    request_date,
                    bank_ids,
                    loan_term_months,
                    percentage_down_payment,
                    session,
                )
                # Extract valid_offers from the returned dictionary
                valid_offers = offers_data.get("valid_offers", [])
                logger.info(f"Found {len(valid_offers)} valid offers to evaluate")

                # Select the best offer for each bank
                best_offers = select_best_offers(
                    valid_offers, 
                    solicitud.income_proof if solicitud.income_proof else [], 
                    False,  # simulation=False for real solicitud evaluation
                    loan_term_months
                )
                logger.info(f"Selected best offers for {len(best_offers)} banks")

        # Evaluate creditworthiness
        logger.info(f"Fetching reports for client ID: {solicitud.cliente_id}")
        reports = await fetch_reports_by_client_id(solicitud.cliente_id, session)

        # Check if any reports exist for the client
        if not reports:
            logger.warning(f"No reports found for client ID: {solicitud.cliente_id}")
            return {
                "error": f"No reports found for client: {solicitud.cliente_id}",
                "status_code": 400,
            }

        # Extract raw query report if available
        response_bc: Optional[Dict] = None
        for report in reports:
            if hasattr(report, 'raw_query_report') and report.raw_query_report:
                response_bc = report.raw_query_report
                break

        if response_bc is None:
            logger.warning("No raw query report found in the reports list.")

        # Extract account details from response_bc safely
        accounts_from_bc: List[Dict] = (
            response_bc.get("response", {}).get("cuentas", []) if response_bc else []
        )

        # Extract score BC details from response_bc safely
        scores_bc_from_bc: List[Dict] = (
            response_bc.get("response", {}).get("scoreBuroCredito", [])
            if response_bc
            else []
        )

        logger.info(f"Extracted {len(accounts_from_bc)} accounts from response_bc.")

        # Process payment status if accounts are found
        payment_status = None
        if accounts_from_bc:
            logger.info("Processing payment status for extracted accounts.")
            payment_status = process_payments(accounts_from_bc)
            logger.info("Payment status processing completed.")
        else:
            logger.info("No accounts found, skipping payment status processing.")

        # Extract credit data and addresses from reports
        logger.info(f"Extracting credit data for client ID: {solicitud.cliente_id}")
        credit_data, addresses = await extract_credit_data(reports, session)

        if not credit_data:
            logger.warning(
                f"Credit report data is incomplete or missing for solicitud: {solicitud.cliente_id}"
            )

        # Generate combined bank offers
        logger.info(f"Generating combined bank offers for client ID: {solicitud.cliente_id}")

        birth_date = cliente.birth_date
        income_type = solicitud.income_source_type

        # Combine credit evaluation and financing offers into a single list of banks
        combined_banks = await combine_bank_data(
            banks=banks,
            best_offers=best_offers,
            credit_data=credit_data,
            reports=reports,
            addresses=addresses,
            accounts_from_bc=accounts_from_bc,
            scores_bc_from_bc=scores_bc_from_bc,
            invoice_motorcycle_value=solicitud.invoice_motorcycle_value,
            percentage_down_payment=solicitud.percentage_down_payment,
            birth_date=birth_date,
            income_type=income_type,
            session=session,
            client_estado=cliente.estado,
            client_ciudad=cliente.ciudad,
            client_zip_code=cliente.zip_code,
        )

        # Validate if solicitud should be assigned to auto financing due to bad credit
        auto_financing_result = await validate_auto_financing_assignment(
            solicitud, combined_banks, session
        )
        logger.info(
            f"Auto financing validation result for solicitud {solicitud_id}: {auto_financing_result}"
        )

        logger.info(f"Solicitud evaluated successfully for solicitud ID: {solicitud_id}")

        # Return the evaluation results
        return {
            "banks": combined_banks,
            "income_estimate": (
                credit_data.get("income_estimate", "N/A") if credit_data else "N/A"
            ),
            "payment_capacity_by_bc": (
                credit_data.get("payment_capacity_by_bc", "N/A")
                if credit_data
                else "N/A"
            ),
            "income_proof": (
                solicitud.income_proof[0]
                if solicitud.income_proof and len(solicitud.income_proof) > 0
                else None
            ),
            "success": True,
            "payment_status": payment_status or "No accounts found",
            "payment_capacity_by_client": (
                float(solicitud.monthly_income) - float(solicitud.debt_pay_from_income)
                if solicitud.monthly_income and solicitud.debt_pay_from_income
                else None
            ),
            "auto_financing_assignment": auto_financing_result,
            "status_code": 200,
        }

    except Exception as e:
        logger.error(
            f"Unexpected error evaluating solicitud: {str(e)}", exc_info=True
        )
        return {"error": str(e), "status_code": 500}

