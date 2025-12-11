"""
Authentication models
Migrated from Flask app/api/models.py
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from uuid import UUID
from datetime import datetime


class User(SQLModel, table=True):
    """
    User model - migrated from Flask
    Table: users
    """
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None, max_length=50)
    second_name: Optional[str] = Field(default=None, max_length=50)
    first_last_name: Optional[str] = Field(default=None, max_length=50)
    second_last_name: Optional[str] = Field(default=None, max_length=50)
    email: str = Field(max_length=100, unique=True, index=True)
    uuid: UUID = Field(unique=True, index=True)
    phone_number: Optional[str] = Field(default=None, max_length=30)
    role_id: int = Field(foreign_key="roles.id")
    is_active: Optional[bool] = Field(default=True)
    is_selected: Optional[bool] = Field(default=False)
    last_selected_at: Optional[datetime] = Field(default=None)
    zona_autoestrena_url: Optional[str] = Field(default=None)
    
    # Relationships will be added as needed
    # role: Optional["Role"] = Relationship(back_populates="users")

