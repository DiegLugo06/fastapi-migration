"""
Extract credit data from reports
Async version migrated from Flask app/loan/utils/extract_credit_data.py
"""
from typing import Dict, List, Optional, Tuple, Union
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.apps.client.models import Report, Cuentas, Domicilios, ResumenReporte, ScoreBuroCredito

logger = logging.getLogger(__name__)


async def extract_credit_data(
    reports: List[Report],
    session: AsyncSession
) -> Tuple[Optional[Dict[str, Union[str, int, date]]], Optional[List[Domicilios]]]:
    """Extract credit data (scores, summary, accounts, addresses) from reports (async version)."""
    
    scores, summaryBuro, accounts, addresses = None, None, None, None
    
    # Process reports in reverse order (most recent first)
    for report in reversed(reports):
        # Fetch scores for this report
        stmt_scores = select(ScoreBuroCredito).where(ScoreBuroCredito.report_id == report.id)
        result_scores = await session.execute(stmt_scores)
        scores = result_scores.scalars().all()
        
        # Fetch summary for this report
        stmt_summary = select(ResumenReporte).where(ResumenReporte.report_id == report.id)
        result_summary = await session.execute(stmt_summary)
        summaryBuro = result_summary.scalar_one_or_none()
        
        # Fetch accounts for this report
        stmt_accounts = select(Cuentas).where(Cuentas.report_id == report.id)
        result_accounts = await session.execute(stmt_accounts)
        accounts = result_accounts.scalars().all()
        
        # Fetch addresses for this report
        stmt_addresses = select(Domicilios).where(Domicilios.report_id == report.id)
        result_addresses = await session.execute(stmt_addresses)
        addresses = result_addresses.scalars().all()

        if scores and summaryBuro and addresses:
            break

    if not scores or not summaryBuro or not addresses:
        logger.error("Missing a part of scores, summaryBuro, or addresses in the report")
        return None, None

    income_estimate, scoreBC, payment_capacity = None, None, 0
    total_pagos_revolventes = 0
    total_pagos_fijos = 0

    for score in scores:
        if score.codigo_score == "016":
            income_estimate = score.valor_score
        if score.codigo_score == "007":
            scoreBC = score.valor_score
        if score.codigo_score == "resumen_reporte":
            total_pagos_revolventes = score.total_pagos_revolventes or 0
            total_pagos_fijos = score.total_pagos_fijos or 0

    if not income_estimate or not scoreBC:
        logger.error("Missing income estimate or scoreBC")

    else:
        # Calculate payment capacity
        payment_capacity = float(
            income_estimate * 1000 - (total_pagos_revolventes + total_pagos_fijos)
        )
        logger.info(f"Payment capacity calculated: {payment_capacity}")

    return {
        "income_estimate": income_estimate,
        "scoreBC": scoreBC,
        "consultas_buro": summaryBuro.numero_solicitudes_ultimos_6_meses,
        "antiguedad_historial": summaryBuro.fecha_apertura_cuenta_mas_antigua,
        "historic_payments": [
            account.historico_pagos for account in accounts if account.forma_pago_actual
        ],
        "forma_pago_actual": [
            account.forma_pago_actual
            for account in accounts
            if account.forma_pago_actual
        ],
        "monto_pagar": [
            account.monto_pagar for account in accounts if account.forma_pago_actual
        ],
        "quita": summaryBuro.numero_mop97,
        "payment_capacity_by_bc": payment_capacity,
    }, addresses


