"""
Pydantic schemas for authentication
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response schema"""
    message: str
    user_id: str
    access_token: str
    refresh_token: str
    expires_in: int


class RefreshRequest(BaseModel):
    """Refresh token request schema"""
    access_token: str  # Note: Flask uses "access_token" for refresh token


class RefreshResponse(BaseModel):
    """Refresh token response schema"""
    message: str
    access_token: str
    refresh_token: str


class SignupRequest(BaseModel):
    """Signup request schema"""
    email: EmailStr
    role_id: int
    sucursal_id: list[int]


class SignupResponse(BaseModel):
    """Signup response schema"""
    message: str
    user_id: str


class ResetPasswordRequest(BaseModel):
    """Reset password request schema"""
    password: str


class ResetPasswordResponse(BaseModel):
    """Reset password response schema"""
    message: str


class SendEmailPasswordResetRequest(BaseModel):
    """Send email password reset request schema"""
    email: EmailStr


class SendEmailPasswordResetResponse(BaseModel):
    """Send email password reset response schema"""
    message: str


class ValidateRefreshRequest(BaseModel):
    """Validate refresh token request schema"""
    refresh_token: str


class ValidateRefreshResponse(BaseModel):
    """Validate refresh token response schema"""
    valid: bool
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    email: str
    name: Optional[str] = None
    role_id: int
    is_active: Optional[bool] = None
    
    class Config:
        from_attributes = True

