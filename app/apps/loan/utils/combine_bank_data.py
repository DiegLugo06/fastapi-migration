"""
Combine bank evaluation data
Async version migrated from Flask app/loan/utils/_combine_bank_data.py
"""
import datetime
from typing import Dict, List, Optional, Union
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.apps.quote.models import Banco
from app.apps.client.models import Report, Domicilios
from app.apps.loan.utils.estudio import (
    age_evaluation,
    calculate_debt_income_rate,
    calcular_capacidad_pago_creditogo,
    calcular_capacidad_pago_hey,
    calcular_cuentas_quebranto,
    calcular_monto_maximo_cc,
    calcular_saldo_actual_ca,
    evaluar_antiguedad_historial,
    evaluar_arraigo_domiciliar,
    evaluar_buro,
    evaluar_comportamiento_mop1,
    evaluar_comportamiento_mop1_hey,
    evaluar_consultas_buro,
    evaluar_porcentaje_ingresos,
    evaluar_quitas,
    evaluar_score_crediticio,
    evaluar_capacidad_pago_bc,
    _evaluate_zone_eligibility,
)

logger = logging.getLogger(__name__)


async def combine_bank_data(
    banks: List[Banco],
    best_offers: Dict[int, Dict[str, Union[float, bool]]],
    credit_data: Optional[Dict[str, Union[str, int, date]]],
    reports: List[Report],
    addresses: Optional[List[Domicilios]],
    accounts_from_bc: List[Dict],
    scores_bc_from_bc: List[Dict],
    invoice_motorcycle_value: int,
    percentage_down_payment: float,
    birth_date: datetime.date,
    income_type: str,
    session: AsyncSession,
    client_estado: Optional[str] = None,
    client_ciudad: Optional[str] = None,
    client_zip_code: Optional[str] = None,
) -> List[Dict[str, Union[int, str, Dict[str, Union[float, bool]]]]]:
    """Combine credit evaluation and financing offers into a single list of banks (async version)."""

    combined_banks = []

    for bank in banks:
        bank_data = {
            "bank_id": bank.id,
            "bank_name": bank.name.title() if bank.name else f"Bank {bank.id}",
            "pre_aprovado": evaluar_buro(reports[0] if reports else None, bank.name),
            "age_evaluation": age_evaluation(birth_date, income_type, bank.name),
        }
        
        # Zone eligibility (async)
        zone_eligibility = await _evaluate_zone_eligibility(
            client_estado or "",
            client_ciudad or "",
            client_zip_code or "",
            bank,
            session
        )
        bank_data["zone_eligibility"] = zone_eligibility

        # Try to get Score BC from different sources
        score_bc_numeric = None
        if credit_data and credit_data.get("scoreBC"):
            score_bc_numeric = credit_data["scoreBC"]
        elif scores_bc_from_bc:
            # Try to get from scores_bc_from_bc if available
            for score in scores_bc_from_bc:
                if score.get("codigoScore") == "007":
                    score_bc_numeric = score.get("valorScore")
                    break

        if credit_data:
            # Calculate payment capacity for AFIRME and HEY
            payment_capacity = credit_data.get("payment_capacity_by_bc")

            # For AFIRME, calculate specific payment capacity
            if bank.name == "AFIRME":
                # Handle income_type - it might be an empty array, None, or a string
                income_source_type = "PF"  # Default
                if income_type:
                    if isinstance(income_type, list):
                        if len(income_type) > 0:
                            income_source_type = income_type[0]  # Take first element
                        else:
                            income_source_type = "PF"  # Default if empty list
                    else:
                        income_source_type = str(income_type)  # Convert to string

                # Create mock solicitud object for AFIRME calculation
                mock_solicitud = {"income_source_type": income_source_type}
                try:
                    # For AFIRME, we need to pass the total payments, not the calculated capacity
                    total_payments = 0
                    if accounts_from_bc:
                        for account in accounts_from_bc:
                            try:
                                monto_pagar = float(account.get("montoPagar", 0)) or 0
                                total_payments += monto_pagar
                            except (ValueError, TypeError):
                                continue

                    payment_capacity = evaluar_capacidad_pago_bc(
                        total_payments,
                        bank.name,
                        mock_solicitud,
                        accounts_from_bc,
                        scores_bc_from_bc,
                    )
                except Exception as e:
                    logger.error(f"Error calculating AFIRME payment capacity: {str(e)}")
                    payment_capacity = "N/A"

            # For Hey Banco, calculate specific payment capacity
            elif bank.name == "HEY":
                # Handle income_type
                income_source_type = None
                if income_type:
                    if isinstance(income_type, list):
                        if len(income_type) > 0:
                            income_source_type = income_type[0]
                        else:
                            income_source_type = None
                    else:
                        income_source_type = str(income_type)

                # Create mock solicitud object for Hey Banco calculation
                mock_solicitud = {"income_source_type": income_source_type}
                try:
                    payment_capacity = calcular_capacidad_pago_hey(
                        mock_solicitud, accounts_from_bc, scores_bc_from_bc
                    )
                except Exception as e:
                    logger.error(f"Error calculating Hey Banco payment capacity: {str(e)}")
                    payment_capacity = "N/A"

            # For SFERA, calculate specific payment capacity
            elif bank.name == "SFERA":
                try:
                    total_payments = 0
                    if accounts_from_bc:
                        for account in accounts_from_bc:
                            try:
                                monto_pagar = float(account.get("montoPagar", 0)) or 0
                                total_payments += monto_pagar
                            except (ValueError, TypeError):
                                continue

                    payment_capacity = evaluar_capacidad_pago_bc(
                        total_payments,
                        bank.name,
                        None,
                        accounts_from_bc,
                        scores_bc_from_bc,
                    )
                except Exception as e:
                    logger.error(f"Error calculating SFERA payment capacity: {str(e)}")
                    payment_capacity = "N/A"

            # For CREDITOGO, calculate specific payment capacity
            elif bank.name == "CREDITOGO":
                try:
                    total_payments = 0
                    if accounts_from_bc:
                        for account in accounts_from_bc:
                            try:
                                monto_pagar = float(account.get("montoPagar", 0)) or 0
                                total_payments += monto_pagar
                            except (ValueError, TypeError):
                                continue

                    payment_capacity = evaluar_capacidad_pago_bc(
                        total_payments,
                        bank.name,
                        None,
                        accounts_from_bc,
                        scores_bc_from_bc,
                    )
                except Exception as e:
                    logger.error(f"Error calculating CREDITOGO payment capacity: {str(e)}")
                    payment_capacity = "N/A"

            monto_maximo_cc = "N/A"
            saldo_actual_ca = "N/A"
            cuentas_quebranto = "N/A"
            if bank.name == "SFERA":
                monto_maximo_cc = calcular_monto_maximo_cc(accounts_from_bc)
                saldo_actual_ca = calcular_saldo_actual_ca(accounts_from_bc)
                cuentas_quebranto = calcular_cuentas_quebranto(accounts_from_bc)

            # Calculate MOP1 behavior
            comportamiento_mop1 = "N/A"
            if bank.name == "HEY":
                try:
                    comportamiento_mop1 = evaluar_comportamiento_mop1_hey(
                        accounts_from_bc
                    )
                except Exception as e:
                    logger.error(f"Error in Hey Banco MOP1 evaluation: {str(e)}")
                    comportamiento_mop1 = "N/A"
            else:
                try:
                    comportamiento_mop1 = evaluar_comportamiento_mop1(
                        historic_payments=credit_data.get("historic_payments", []),
                        bank=bank.name,
                        forma_pago_actual=credit_data.get("forma_pago_actual"),
                        quita=credit_data.get("quita"),
                        monto_pagar=credit_data.get("monto_pagar"),
                    )
                except Exception as e:
                    logger.error(f"Error in {bank.name} MOP1 evaluation: {str(e)}")
                    comportamiento_mop1 = "N/A"

            bank_data.update(
                {
                    "comportamiento_mop1": comportamiento_mop1,
                    "porcentaje_ingresos": calculate_debt_income_rate(
                        accounts_from_bc,
                        scores_bc_from_bc,
                        bank.id,
                        invoice_motorcycle_value,
                        percentage_down_payment,
                    ),
                    "score_crediticio": (
                        evaluar_score_crediticio(score_bc_numeric, bank.name)
                        if score_bc_numeric
                        else "N/A"
                    ),
                    "score_bc_numeric": score_bc_numeric,
                    "consultas_buro": evaluar_consultas_buro(
                        credit_data.get("consultas_buro"), bank.name
                    ),
                    "antiguedad_historial": evaluar_antiguedad_historial(
                        credit_data.get("antiguedad_historial"), bank.name
                    ),
                    "quitas": evaluar_quitas(credit_data.get("quita"), bank.name, accounts_from_bc),
                    "capacidad_pago_mensual_bc": payment_capacity if bank.name in ["AFIRME", "HEY", "CREDITOGO", "SFERA"] else "N/A",
                    "monto_maximo_cc": monto_maximo_cc,
                    "saldo_actual_ca": saldo_actual_ca,
                    "cuentas_quebranto": cuentas_quebranto,
                    "age_evaluation": age_evaluation(
                        birth_date,
                        income_type,
                        bank.name,
                    ),
                }
            )
        else:
            # If no credit_data, still try to provide basic evaluation
            bank_data.update(
                {
                    "score_crediticio": (
                        evaluar_score_crediticio(score_bc_numeric, bank.name)
                        if score_bc_numeric
                        else "N/A"
                    ),
                    "score_bc_numeric": score_bc_numeric,
                }
            )

        if addresses:
            bank_data["arraigo_domiciliar"] = evaluar_arraigo_domiciliar(
                addresses, bank.name
            )

        if bank.id in best_offers:
            bank_data["best_offer"] = best_offers[bank.id]

        combined_banks.append(bank_data)

    return combined_banks


