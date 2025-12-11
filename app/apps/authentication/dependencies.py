"""
Authentication dependencies for FastAPI
Migrated from Flask app/auth/decorators.py
"""
import os
import time
import random
import uuid
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status, Header, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.database import get_async_session
from app.apps.authentication.models import User
from app.config import get_supabase_url, get_supabase_token, get_env_var
from supabase import create_client

logger = logging.getLogger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


def retry_with_exponential_backoff(func, max_retries=2, base_delay=1, max_delay=10):
    """
    Retry a function with exponential backoff for transient failures.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay in seconds
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            error_message = str(e).lower()
            
            # Only retry on specific transient errors
            if any(
                transient_error in error_message
                for transient_error in [
                    "server disconnected",
                    "connection error",
                    "timeout",
                    "network error",
                    "service unavailable",
                    "temporary failure",
                ]
            ):
                if attempt < max_retries:
                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2**attempt), max_delay)
                    jitter = random.uniform(0.1, 0.3) * delay
                    total_delay = delay + jitter
                    
                    logger.warning(
                        f"Transient error on attempt {attempt + 1}/{max_retries + 1}: {e}. "
                        f"Retrying in {total_delay:.2f} seconds..."
                    )
                    time.sleep(total_delay)
                    continue
                else:
                    logger.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
                    raise e
            else:
                # Non-transient error, don't retry
                raise e
    
    # This should never be reached, but just in case
    raise Exception("Retry mechanism failed unexpectedly")


def get_supabase_client():
    """Get Supabase client instance"""
    try:
        supabase = create_client(get_supabase_url(), get_supabase_token())
        return supabase
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    authorization: Optional[str] = Header(None),
    public_key: Optional[str] = Header(None, alias="Public-Key"),
    access_token: Optional[str] = Cookie(None),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """
    Dependency to get current authenticated user.
    Supports JWT tokens via Authorization header, Public-Key (API key), or access_token cookie.
    
    Migrated from Flask @token_required decorator
    """
    # Check Public-Key first (API key authentication)
    if public_key:
        stored_key = get_env_var("API_KEY")
        if not stored_key:
            logger.error("API_KEY environment variable not set")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key validation not configured",
            )
        
        if public_key != stored_key:
            logger.warning("Invalid API key provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The provided API key is incorrect",
            )
        
        # API key is valid - allow request to proceed
        # In Flask, API key auth just validates the key and proceeds without requiring a user
        # For FastAPI, we need to return a User object, but we'll create a minimal one
        # without querying the database (to avoid connection issues)
        logger.info("API key authentication successful")
        
        # Create a minimal user object for API key authentication
        # This matches Flask behavior where API key auth doesn't require database lookup
        # The user object is minimal but sufficient for endpoints that need basic user info
        api_key_user = User(
            id=0,  # Placeholder - endpoints should handle API key users appropriately
            email="api_key@system.local",
            uuid=uuid.uuid4(),
            role_id=1,  # Default role - adjust if needed
            is_active=True,
            name="API Key User",
            is_selected=False,
        )
        
        logger.info("Using API key user context (no database lookup required)")
        return api_key_user
    
    # Extract JWT token from header or cookie
    jwt_token = None
    if credentials:
        jwt_token = credentials.credentials
    elif authorization:
        # Handle both "Bearer <token>" and direct token
        if authorization.startswith("Bearer "):
            jwt_token = authorization[7:]
        else:
            jwt_token = authorization
    elif access_token:
        jwt_token = access_token
    
    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Token or Public-Key are missing",
        )
    
    try:
        # Initialize Supabase client
        supabase = get_supabase_client()
        if not supabase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not available",
            )
        
        # Validate JWT token with Supabase using retry mechanism
        def validate_jwt_token():
            response = supabase.auth.get_user(jwt_token)
            if not response or not response.user:
                raise Exception("Invalid JWT token: No user found in response")
            return response
        
        try:
            response = retry_with_exponential_backoff(validate_jwt_token)
        except Exception as e:
            logger.warning(f"Invalid JWT token provided: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The provided token is invalid or expired",
            )
        
        # Extract user UUID and validate user exists
        try:
            user_uuid = UUID(response.user.id)
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid user ID format: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token contains invalid user information",
            )
        
        # Query user from database
        stmt = select(User).where(User.uuid == user_uuid)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found in database: {user_uuid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found",
            )
        
        logger.info(f"User {user.id} authenticated successfully")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    authorization: Optional[str] = Header(None),
    public_key: Optional[str] = Header(None, alias="Public-Key"),
    access_token: Optional[str] = Cookie(None),
    session: AsyncSession = Depends(get_async_session),
) -> Optional[User]:
    """
    Optional authentication dependency - returns None if not authenticated.
    Useful for endpoints that work with or without authentication.
    Only attempts authentication if credentials are actually provided.
    """
    # Check if any authentication method is provided
    has_public_key = public_key is not None
    has_credentials = credentials is not None
    has_authorization = authorization is not None
    has_access_token = access_token is not None
    
    # If no authentication method is provided, return None without trying to authenticate
    if not (has_public_key or has_credentials or has_authorization or has_access_token):
        return None
    
    # If authentication is provided, try to validate it
    try:
        return await get_current_user(credentials, authorization, public_key, access_token, session)
    except HTTPException:
        # Silently return None for optional auth - don't log warnings for missing/invalid tokens
        return None

