"""
CMS models for content management
"""
from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, Dict, Any
from datetime import datetime


class PageContent(SQLModel, table=True):
    """
    CMS Page Content model
    Table: page_content
    """
    __tablename__ = "page_content"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    page_key: str = Field(max_length=100, unique=True, index=True)  # e.g., "marketplace_landing"
    content: Dict[str, Any] = Field(sa_column=Column(JSONB))  # JSON content stored as JSONB
    version: int = Field(default=1)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")

