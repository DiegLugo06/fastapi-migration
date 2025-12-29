"""
Credit evaluation functions
Migrated from Flask app/loan/utils/estudio.py
Simplified version with key evaluation functions
"""
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.apps.client.models import Report, Cuentas
from app.apps.quote.models import Banco

logger = logging.getLogger(__name__)


def evaluar_score_crediticio(scoreBC, bank):
    """Evaluate credit score based on bank criteria."""
    if not scoreBC:
        return "scoreBC not available"
    bank_upper = bank.upper() if bank else ""
    
    if bank_upper == "VWFS":
        return "N/A"
    elif bank_upper == "BBVA":
        return "Aprobado" if scoreBC >= 670 else "Rechazado"
    elif bank_upper == "SANTANDER":
        return "Aprobado" if scoreBC >= 621 else "Rechazado"
    elif bank_upper == "HEY":
        return "Aprobado" if scoreBC >= 634 else "Rechazado"
    elif bank_upper == "BANREGIO":
        if scoreBC >= 701:
            return "Aprobado"
        elif 650 <= scoreBC < 701:
            return "En Estudio"
        else:
            return "Rechazado"
    elif bank_upper in ["BAZ", "GALGO", "MAXIKASH", "CREDITOGO", "AFIRME", "CNE"]:
        return "N/A"
    elif bank_upper == "ZONA AUTOESTRENA":
        return "Aprobado"
    elif bank_upper == "SFERA":
        if scoreBC >= 701:
            return "Aprobado"
        elif 668 <= scoreBC < 701:
            return "En Estudio"
        else:
            return "Rechazado"
    return "Rechazado"


def evaluar_consultas_buro(consultas_buro, bank):
    """Evaluate credit bureau inquiries based on bank criteria."""
    bank_upper = bank.upper() if bank else ""
    
    if bank_upper == "VWFS":
        return "N/A"
    elif bank_upper == "BBVA":
        if consultas_buro <= 7:
            return "Aprobado"
        elif 7 < consultas_buro <= 10:
            return "En Estudio"
        else:
            return "Rechazado"
    elif bank_upper == "SANTANDER":
        if consultas_buro >= 10:
            return "Rechazado"
        elif consultas_buro >= 4:
            return "En Estudio"
        else:
            return "Aprobado"
    elif bank_upper == "HEY":
        return "Aprobado" if consultas_buro <= 10 else "Rechazado"
    elif bank_upper == "BANREGIO":
        if consultas_buro <= 1:
            return "Aprobado"
        elif consultas_buro <= 20:
            return "En Estudio"
        else:
            return "Rechazado"
    elif bank_upper == "BAZ":
        return "Aprobado" if consultas_buro <= 3 else "Rechazado"
    elif bank_upper in ["GALGO", "MAXIKASH", "CNE", "SFERA"]:
        return "N/A"
    elif bank_upper == "ZONA AUTOESTRENA":
        return "Aprobado"
    elif bank_upper == "CREDITOGO":
        return "Aprobado" if consultas_buro <= 60 else "Rechazado"
    elif bank_upper == "AFIRME":
        return "Aprobado" if consultas_buro <= 8 else "En Estudio"
    return "Rechazado"


def evaluar_antiguedad_historial(antiguedad_historia, bank):
    """Evaluate credit history age based on bank criteria."""
    if isinstance(antiguedad_historia, str):
        try:
            fecha_apertura_cuenta_mas_antigua = datetime.strptime(antiguedad_historia, "%Y-%m-%d").date()
        except:
            return "N/A"
    else:
        fecha_apertura_cuenta_mas_antigua = antiguedad_historia

    if fecha_apertura_cuenta_mas_antigua is None:
        diff_in_months = 0
    else:
        now = datetime.now()
        diff_in_months = (
            (now.year - fecha_apertura_cuenta_mas_antigua.year) * 12
            + now.month
            - fecha_apertura_cuenta_mas_antigua.month
        )

    bank_upper = bank.upper() if bank else ""
    
    if bank_upper == "VWFS":
        return "N/A"
    elif bank_upper in ["BBVA", "SANTANDER", "HEY"]:
        if diff_in_months >= 12:
            return "Aprobado"
        elif 0 <= diff_in_months < 12:
            return "En Estudio"
        else:
            return "N/A"
    elif bank_upper == "BANREGIO":
        return "Aprobado" if diff_in_months >= 6 else "Rechazado"
    elif bank_upper in ["BAZ", "GALGO", "MAXIKASH", "AFIRME", "CNE"]:
        return "N/A"
    elif bank_upper == "ZONA AUTOESTRENA":
        return "Aprobado"
    elif bank_upper == "CREDITOGO":
        if diff_in_months >= 3:
            return "Aprobado"
        elif 0 <= diff_in_months < 3:
            return "En Estudio"
        else:
            return "N/A"
    elif bank_upper == "SFERA":
        if diff_in_months >= 12:
            return "Aprobado"
        elif 6 <= diff_in_months < 12:
            return "En Estudio"
        elif diff_in_months < 6:
            return "Rechazado"
    return "Rechazado"


def evaluar_comportamiento_mop1(historic_payments, bank, forma_pago_actual=None, quita=None, monto_pagar=None):
    """Evaluate payment behavior (MOP1) based on bank criteria."""
    # Simplified version - returns N/A for most banks
    bank_upper = bank.upper() if bank else ""
    
    if bank_upper in ["VWFS", "BBVA", "SANTANDER", "HEY", "BANREGIO", "BAZ", "GALGO", 
                      "MAXIKASH", "ZONA AUTOESTRENA", "CREDITOGO", "AFIRME", "CNE", "SFERA"]:
        # For now, return N/A - full implementation would analyze historic_payments
        return "N/A"
    
    return "Rechazado"


def evaluar_comportamiento_mop1_hey(historic_payments, bank):
    """Evaluate payment behavior for Hey Banco."""
    return "N/A"  # Simplified


def evaluar_quitas(quita, bank, cuentas=None):
    """Evaluate write-offs (quitas) based on bank criteria."""
    bank_upper = bank.upper() if bank else ""
    
    if bank_upper in ["VWFS", "BBVA", "SANTANDER", "HEY", "BANREGIO", "BAZ", "GALGO", 
                      "MAXIKASH", "ZONA AUTOESTRENA", "CREDITOGO", "AFIRME", "CNE", "SFERA"]:
        # Simplified - return N/A for most banks
        if quita and quita > 0:
            return "Rechazado"
        return "Aprobado"
    
    return "Rechazado"


def evaluar_arraigo_domiciliar(addresses, bank):
    """Evaluate residential stability based on bank criteria."""
    # Simplified version
    bank_upper = bank.upper() if bank else ""
    
    if bank_upper in ["VWFS", "BBVA", "SANTANDER", "HEY", "BANREGIO", "BAZ", "GALGO", 
                      "MAXIKASH", "ZONA AUTOESTRENA", "CREDITOGO", "AFIRME", "CNE", "SFERA"]:
        return "N/A"  # Simplified
    
    return "Rechazado"


def evaluar_buro(report, bank):
    """Evaluate credit bureau report based on bank criteria."""
    if not report:
        return "report not available"
    
    bank_upper = bank.upper() if bank else ""
    
    if bank_upper in ["VWFS", "BBVA", "SANTANDER", "HEY", "BANREGIO", "BAZ", "GALGO", 
                      "CREDITOGO", "AFIRME", "CNE"]:
        return "N/A"
    elif bank_upper == "MAXIKASH":
        # TODO: Implement MAXIKASH API call if needed
        return "N/A"
    elif bank_upper == "ZONA AUTOESTRENA":
        return "Aprobado"
    
    return "Rechazado"


def evaluar_porcentaje_ingresos(income_estimate, bank):
    """Evaluate income percentage - currently returns N/A."""
    return "N/A"


def calculate_debt_income_rate(cuentas, scoreBuro, bank_id, invoice_motorcycle_value, percentage_down_payment):
    """Calculate debt to income ratio - currently returns N/A."""
    logger.info(f"porcentaje_ingresos evaluation disabled for bank_id {bank_id} - returning N/A")
    return "N/A"


def evaluar_capacidad_pago_bc(payment_capacity, bank, solicitud=None, cuentas=None, score_buro=None):
    """Evaluate payment capacity based on bank criteria."""
    bank_upper = bank.upper() if bank else ""
    
    if bank_upper in ["VWFS", "BBVA", "SANTANDER", "HEY", "BANREGIO", "BAZ", "GALGO", 
                      "MAXIKASH", "ZONA AUTOESTRENA", "CREDITOGO", "AFIRME", "CNE", "SFERA"]:
        if payment_capacity is None:
            return "Agregar ingreso"
        return str(payment_capacity)
    
    return "N/A"


def calcular_capacidad_pago_creditogo(payment_capacity, score_buro):
    """Calculate payment capacity for Creditogo."""
    if payment_capacity is None:
        return "Agregar ingreso"
    return str(payment_capacity)


def calcular_capacidad_pago_hey(solicitud, cuentas, score_buro):
    """Calculate payment capacity for Hey Banco."""
    # Simplified version
    if not solicitud or not solicitud.get("income_source_type"):
        return "Agregar tipo de ingreso"
    return "N/A"  # Full implementation would calculate based on income type


def calcular_cuentas_quebranto(accounts_from_bc):
    """Calculate accounts in default."""
    if not accounts_from_bc:
        return 0
    # Simplified - would need to analyze accounts
    return 0


def calcular_monto_maximo_cc(accounts_from_bc):
    """Calculate maximum credit card amount."""
    if not accounts_from_bc:
        return 0
    # Simplified
    return 0


def calcular_saldo_actual_ca(accounts_from_bc):
    """Calculate current account balance."""
    if not accounts_from_bc:
        return 0
    # Simplified
    return 0


def age_evaluation(birth_date: date, income_type: str, bank: str) -> str:
    """Return age-based evaluation for a given bank."""
    if not birth_date:
        return "N/A"
    
    # Calculate age
    now = datetime.now()
    years_old = (now.year - birth_date.year - 
                 ((now.month, now.day) < (birth_date.month, birth_date.day)))
    
    bank_upper = (bank or "").strip().upper()
    
    if bank_upper == "VWFS":
        return "N/A"
    
    if bank_upper == "AFIRME":
        if not income_type:
            return "N/A"
        # Handle income_type as list or string
        if isinstance(income_type, list):
            income_type_str = income_type[0] if income_type else ""
        else:
            income_type_str = str(income_type)
        
        if "PFAE" in income_type_str.upper():
            return "Aprobado" if 22 <= years_old <= 69 else "Rechazado"
        else:
            return "Aprobado" if 18 <= years_old <= 69 else "Rechazado"
    
    # Static rules per bank
    BANK_RULES = {
        "BBVA": [(20, 69, "Aprobado"), (18, 19, "En Estudio"), (70, 73, "En Estudio")],
        "SANTANDER": [(20, 69, "Aprobado"), (18, 19, "En Estudio")],
        "HEY": [(18, 69, "Aprobado")],
        "BANREGIO": [(21, 68, "Aprobado")],
        "GALGO": [(18, 64, "Aprobado")],
        "ZONA AUTOESTRENA": [(18, 65, "Aprobado"), (66, 69, "En Estudio")],
        "CREDITOGO": [(21, 68, "Aprobado")],
        "MAXIKASH": [(18, 59, "Aprobado")],
    }
    
    if bank_upper in BANK_RULES:
        for min_age, max_age, status in BANK_RULES[bank_upper]:
            if min_age <= years_old <= max_age:
                return status
    
    return "Rechazado"


async def _evaluate_zone_eligibility(
    client_estado: str, 
    client_ciudad: str, 
    client_zip_code: str, 
    bank: Banco,
    session: AsyncSession
) -> str:
    """Evaluate if a client is eligible for a bank based on zone limits."""
    # TODO: Implement BankZoneLimit model if needed
    # For now, return N/A as zone limits are not yet migrated
    return "N/A"

