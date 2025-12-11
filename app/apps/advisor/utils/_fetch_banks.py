"""
Fetch banks utility
Migrated from Flask
"""
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.apps.quote.models import Banco


async def _fetch_banks_for_sucursal(sucursal_id: int, session: AsyncSession) -> List[Banco]:
    """Fetch banks associated with a sucursal."""
    # Query bancos_sucursal association table
    stmt = text("""
        SELECT b.id, b.name, b.valor_factura, b.minimo_financiar
        FROM bancos b
        INNER JOIN bancos_sucursal bs ON b.id = bs.banco_id
        WHERE bs.sucursal_id = :sucursal_id
    """)
    result = await session.execute(stmt, {"sucursal_id": sucursal_id})
    rows = result.fetchall()
    
    banks = []
    for row in rows:
        bank = Banco(
            id=row[0],
            name=row[1],
            valor_factura=row[2],
            minimo_financiar=row[3]
        )
        banks.append(bank)
    
    return banks

