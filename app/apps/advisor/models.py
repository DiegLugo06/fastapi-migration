"""
Advisor models
Additional models needed for advisor module
"""
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List
from app.common.fields import handle_postgresql_json


class Sucursal(SQLModel, table=True):
    """
    Sucursal (Branch) model
    Table: sucursales
    """
    __tablename__ = "sucursales"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=255)
    brand_id: int = Field(foreign_key="motorcycle_brands.id")
    ubicacion: str = Field(max_length=255)
    razon_social: Optional[str] = Field(default=None, max_length=255)
    credit_card_payment_method: Optional[bool] = Field(default=None)
    crm_sync: Optional[str] = Field(default=None, max_length=255)
    zip_code: Optional[str] = Field(default=None, max_length=5)
    active: bool = Field(default=True)
    coordinates: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    
    # Relationships will be added as needed
    # brand: Optional["MotorcycleBrand"] = Relationship(back_populates="sucursales")


class Role(SQLModel, table=True):
    """
    Role model
    Table: roles
    """
    __tablename__ = "roles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, unique=True)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)


# MotorcycleBrand is defined in app.apps.product.models
# Banco is defined in app.apps.quote.models
# Import them from there instead of defining here

