"""
Product models
Migrated from Django apps/product/models.py
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime


class MotorcycleBrand(SQLModel, table=True):
    """
    Motorcycle brand model
    Table: motorcycle_brands
    """
    __tablename__ = "motorcycle_brands"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, unique=True)


class Motorcycles(SQLModel, table=True):
    """
    Motorcycle model
    Table: motorcycles
    """
    __tablename__ = "motorcycles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    brand_id: int = Field(foreign_key="motorcycle_brands.id", index=True)
    model: str = Field(max_length=255)
    inner_brand_model: Optional[str] = Field(default=None, max_length=255)
    year: int = Field(index=True)
    price: float = Field(ge=0)
    color: Optional[str] = Field(default=None, max_length=100)
    active: Optional[bool] = Field(default=True, index=True)
    review_video_url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None, max_length=2000)
    
    # Relationship
    specifications: Optional["MotorcycleSpecifications"] = Relationship(
        back_populates="motorcycle",
        sa_relationship_kwargs={"uselist": False}
    )


class MotorcycleQualitasAmis(SQLModel, table=True):
    """
    Motorcycle Qualitas AMIS keys model
    Table: claves_amis
    """
    __tablename__ = "claves_amis"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    motorcycle_id: int = Field(foreign_key="motorcycles.id")
    clave_amis_qualitas: str = Field(max_length=5)


class Discounts(SQLModel, table=True):
    """
    Discount model
    Table: discounts
    """
    __tablename__ = "discounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str
    type: str = Field(max_length=20)  # 'percentage' or 'fixed'
    value: float = Field(ge=0)
    start_date: datetime = Field(default_factory=datetime.now, index=True)
    end_date: Optional[datetime] = Field(default=None, index=True)
    status: str = Field(default="active", max_length=20, index=True)  # 'active', 'inactive', 'expired'
    sucursal_id: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})


class MotorcycleSpecifications(SQLModel, table=True):
    """
    Motorcycle specifications model
    Table: motorcycle_specifications
    One-to-one relationship with motorcycles
    """
    __tablename__ = "motorcycle_specifications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    motorcycle_id: int = Field(
        foreign_key="motorcycles.id",
        unique=True,
        index=True
    )
    
    # Technical Specifications
    engine: Optional[str] = Field(default=None, max_length=200)
    displacement: Optional[str] = Field(default=None, max_length=50)  # Cilindrada
    bore_x_stroke: Optional[str] = Field(default=None, max_length=100)  # Diámetro x carrera
    power: Optional[str] = Field(default=None, max_length=100)
    torque: Optional[str] = Field(default=None, max_length=100)
    starting_system: Optional[str] = Field(default=None, max_length=100)  # Arranque
    fuel_capacity: Optional[str] = Field(default=None, max_length=50)
    transmission: Optional[str] = Field(default=None, max_length=100)
    cooling: Optional[str] = Field(default=None, max_length=100)
    ignition: Optional[str] = Field(default=None, max_length=100)
    
    # Chassis Specifications
    frame: Optional[str] = Field(default=None, max_length=200)
    front_suspension: Optional[str] = Field(default=None, max_length=200)
    rear_suspension: Optional[str] = Field(default=None, max_length=200)
    front_brake: Optional[str] = Field(default=None, max_length=200)
    rear_brake: Optional[str] = Field(default=None, max_length=200)
    front_tire: Optional[str] = Field(default=None, max_length=100)
    rear_tire: Optional[str] = Field(default=None, max_length=100)
    
    # Dimensions
    weight: Optional[str] = Field(default=None, max_length=50)
    length: Optional[str] = Field(default=None, max_length=50)
    width: Optional[str] = Field(default=None, max_length=50)
    height: Optional[str] = Field(default=None, max_length=50)
    wheelbase: Optional[str] = Field(default=None, max_length=50)
    seat_height: Optional[str] = Field(default=None, max_length=50)
    ground_clearance: Optional[str] = Field(default=None, max_length=50)
    
    # Relationship
    motorcycle: Optional["Motorcycles"] = Relationship(back_populates="specifications")


class StaticQuotes(SQLModel, table=True):
    """
    Static quotes model
    Table: static_quotes
    """
    __tablename__ = "static_quotes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    motorcycle_id: int = Field(foreign_key="motorcycles.id", index=True)
    bank_id: int = Field(index=True)
    enganche: float = Field(ge=0)
    monto_a_financiar: float = Field(ge=0)
    monto_enganche: float = Field(ge=0)
    pago: float = Field(ge=0)
    pago_inicial: float = Field(ge=0)
    seguro_de_vehiculo: float = Field(ge=0)
    seguro_de_vida: float = Field(ge=0)
    tasa_nominal: float = Field(ge=0)

