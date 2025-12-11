"""
Association tables for many-to-many relationships
These are join tables that connect models together
"""
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlmodel import SQLModel

# Association table for User ↔ Sucursal (many-to-many)
# This table links users to their assigned sucursales (stores)
user_sucursales = Table(
    "user_sucursales",
    SQLModel.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# Association table for Cliente ↔ User (many-to-many)
# This table links clients to their assigned users/advisors
clientes_users = Table(
    "clientes_users",
    SQLModel.metadata,
    Column(
        "cliente_id",
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# Ensure tables are registered with SQLModel metadata
# This is important for table creation in tests
__all__ = ["user_sucursales", "clientes_users"]

