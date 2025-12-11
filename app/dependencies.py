"""
Shared dependencies for FastAPI routes
"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from app.database import get_async_session
from typing import Optional

# Database dependency (already defined in database.py)
# Just re-export it for convenience
get_db = get_async_session


# You can add more shared dependencies here, such as:
# - Authentication dependencies
# - Permission checks
# - Common query parameters
# etc.