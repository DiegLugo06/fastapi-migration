"""
Authentication router
Migrated from Flask app/auth/routes.py
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import logging

from app.database import get_async_session
from app.apps.authentication.models import User
from app.apps.authentication.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    SignupResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SendEmailPasswordResetRequest,
    SendEmailPasswordResetResponse,
    ValidateRefreshRequest,
    ValidateRefreshResponse,
)
from app.apps.authentication.dependencies import (
    get_current_user,
    retry_with_exponential_backoff,
)
from app.apps.authentication.utils import get_supabase_client
from app.config import get_supabase_confirmation_url

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest):
    """
    Endpoint for user login using Supabase.
    Equivalent to Flask: POST /login
    """
    logger.info("Attempting to log in user")
    
    try:
        supabase = get_supabase_client()
        if supabase is None:
            logger.error("Supabase client is not initialized")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase client is not initialized."
            )
        
        response = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )
        
        if not response.user:
            logger.warning("Login failed: Invalid credentials")
            error_msg = response.get("error", {}).get("message", "Invalid credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Login failed: {error_msg}"
            )
        
        logger.info(f"User logged in successfully, User ID: {response.user.id}")
        
        return LoginResponse(
            message="Login successful",
            user_id=response.user.id,
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during login: {str(e)}"
        )


@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
async def refresh(request: RefreshRequest):
    """
    Endpoint for refreshing access tokens using Supabase.
    Equivalent to Flask: POST /refresh
    """
    logger.info("Received refresh token request")
    
    if not request.access_token:
        logger.warning("Missing refresh token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token is required"
        )
    
    try:
        supabase = get_supabase_client()
        if supabase is None:
            logger.error("Supabase client is not initialized")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase client is not initialized."
            )
        
        response = supabase.auth.refresh_session(request.access_token)
        
        if not response.user:
            logger.warning("Refresh token is invalid")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        logger.info("Access token refreshed successfully")
        
        return RefreshResponse(
            message="Access token refreshed successfully",
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during refresh: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during refresh: {str(e)}"
        )


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Endpoint for user signup using Supabase.
    Sends a confirmation email with a custom redirect URL.
    Equivalent to Flask: POST /signup
    Note: Requires role_required("finva_admin") - implement permission check
    """
    logger.info("Attempting to sign up user")
    
    try:
        supabase = get_supabase_client()
        redirect_url = get_supabase_confirmation_url()
        
        # Check if user already exists
        stmt = select(User).where(User.email == request.email)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            logger.warning(f"User already exists: {existing_user.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists"
            )
        
        # Invite user via Supabase
        response = supabase.auth.admin.invite_user_by_email(
            email=request.email, options={"redirect_to": redirect_url}
        )
        
        if not response.user:
            error_message = response.get("error", {}).get("message", "Unknown error")
            logger.warning(f"Signup failed: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Signup failed: {error_message}"
            )
        
        logger.info(f"User signed up successfully, User ID: {response.user.id}")
        
        # Save user role and sucursal associations
        user_uuid = UUID(response.user.id)
        
        stmt = select(User).where(User.uuid == user_uuid)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User not found in database: {user_uuid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database"
            )
        
        user.role_id = request.role_id
        await session.commit()
        
        # TODO: Handle user_sucursales association table
        # insert_data = [{"user_id": user.id, "sucursal_id": sid} for sid in request.sucursal_id]
        # await session.execute(user_sucursales.insert(), insert_data)
        # await session.commit()
        
        return SignupResponse(
            message="Signup successful, check your email to confirm your account.",
            user_id=response.user.id,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error during signup: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during signup: {str(e)}"
        )


@router.post("/reset_password", response_model=ResetPasswordResponse, status_code=status.HTTP_200_OK)
async def reset_password(
    request: ResetPasswordRequest,
    authorization: str = Header(None, alias="Authorization"),
    refresh_token: str = Header(None, alias="Refresh-Token"),
):
    """
    Endpoint to reset a user's password using Supabase.
    Equivalent to Flask: POST /reset_password
    """
    logger.info("Received password reset request")
    
    try:
        # Extract tokens from request headers
        access_token = authorization
        refresh_token_header = refresh_token
        
        if not access_token or not refresh_token_header:
            logger.warning("Missing authorization or refresh token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization and refresh token are required"
            )
        
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Step 1: Set the session using the access & refresh tokens
        session_response = supabase.auth.set_session(access_token, refresh_token_header)
        if "error" in session_response:
            error_msg = session_response.get("error", {}).get("message", None)
            logger.error(f"Session error: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Step 2: Update the password
        user_response = supabase.auth.update_user({"password": request.password})
        
        if "error" in user_response:
            error_msg = user_response.get("error", {}).get("message", None)
            logger.error(f"Password update error: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        logger.info("Password updated successfully")
        return ResetPasswordResponse(message="Password updated successfully!")
    
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        logger.error(f"Unexpected error during password reset: {str(e)}", exc_info=True)
        
        # Check if the error contains "New password should be different from the old password"
        if "New password should be different from the old password" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your new password must be different from the current password."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/send_email_password_reset", response_model=SendEmailPasswordResetResponse, status_code=status.HTTP_200_OK)
async def send_email_password_reset(request: SendEmailPasswordResetRequest):
    """
    Endpoint to send an email with a password reset link using Supabase.
    Equivalent to Flask: POST /send_email_password_reset
    """
    logger.info("Received email send request")
    
    try:
        supabase = get_supabase_client()
        
        # Send email for password reset
        supabase.auth.reset_password_for_email(request.email)
        
        return SendEmailPasswordResetResponse(message="Email sent successfully")
    
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
        )


@router.post("/validate-refresh", response_model=ValidateRefreshResponse, status_code=status.HTTP_200_OK)
async def validate_refresh(request: ValidateRefreshRequest):
    """
    Validate refresh_token and return a new access token if valid.
    Equivalent to Flask: POST /validate-refresh
    """
    if not request.refresh_token:
        return ValidateRefreshResponse(
            valid=False,
            message="Refresh token is required"
        )
    
    try:
        supabase = get_supabase_client()
        response = supabase.auth.refresh_session(request.refresh_token)
        
        if not response.user:
            return ValidateRefreshResponse(
                valid=False,
                message="Invalid or expired refresh token"
            )
        
        return ValidateRefreshResponse(
            valid=True,
            user_id=response.user.id,
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in,
        )
    
    except Exception as e:
        return ValidateRefreshResponse(
            valid=False,
            message="Error validating refresh token",
            error=str(e)
        )


@router.post("/login-portal", status_code=status.HTTP_200_OK)
async def login_portal(request: LoginRequest, response: Response):
    """
    Portal login endpoint with cookie-based authentication.
    Equivalent to Flask: POST /login-portal
    """
    try:
        supabase = get_supabase_client()
        auth_response = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Set HttpOnly cookies
        response.set_cookie(
            key="access_token",
            value=auth_response.session.access_token,
            httponly=True,
            secure=True,  # only send over HTTPS
            samesite="strict",
            max_age=auth_response.session.expires_in,
        )
        response.set_cookie(
            key="refresh_token",
            value=auth_response.session.refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=60 * 60 * 24 * 7,  # 7 days
        )
        
        return {
            "message": "Login successful",
            "user_id": auth_response.user.id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login_portal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh-portal", status_code=status.HTTP_200_OK)
async def refresh_portal(response: Response, refresh_token: str = Cookie(None)):
    """
    Portal refresh endpoint with cookie-based authentication.
    Equivalent to Flask: POST /refresh-portal
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token"
        )
    
    try:
        supabase = get_supabase_client()
        auth_response = supabase.auth.refresh_session(refresh_token)
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Set new cookies
        response.set_cookie(
            key="access_token",
            value=auth_response.session.access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=auth_response.session.expires_in,
        )
        response.set_cookie(
            key="refresh_token",
            value=auth_response.session.refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=60 * 60 * 24 * 7,
        )
        
        return {"message": "Token refreshed"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in refresh_portal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/validate-portal", status_code=status.HTTP_200_OK)
async def validate_portal(
    response: Response,
    access_token: str = Cookie(None),
    refresh_token: str = Cookie(None)
):
    """
    Endpoint to validate access and refresh tokens from cookies.
    Handles all authentication scenarios for welcome page.
    Equivalent to Flask: POST /validate-portal
    """
    logger.info("Validating portal tokens")
    
    try:
        # Scenario 1: No tokens at all - user should stay on welcome page
        if not access_token or not refresh_token:
            logger.info("No authentication tokens found - user should stay on welcome page")
            return {
                "valid": False,
                "action": "stay_on_welcome",
                "message": "No authentication tokens found"
            }
        
        supabase = get_supabase_client()
        if supabase is None:
            logger.error("Supabase client is not initialized")
            return {
                "valid": False,
                "action": "stay_on_welcome",
                "message": "Authentication service unavailable"
            }
        
        # Scenario 2: Try to validate access token first
        def validate_access_token():
            user_response = supabase.auth.get_user(access_token)
            if not user_response.user:
                raise Exception("Invalid access token: No user found in response")
            return user_response
        
        try:
            user_response = retry_with_exponential_backoff(validate_access_token)
            logger.info(f"Access token is valid for user: {user_response.user.id}")
            return {
                "valid": True,
                "action": "redirect_to_dashboard",
                "user_id": user_response.user.id,
                "email": user_response.user.email,
                "message": "Access token is valid"
            }
        except Exception as e:
            logger.info(f"Access token invalid, trying refresh: {str(e)}")
        
        # Scenario 3: Access token invalid, try to refresh
        def refresh_tokens():
            refresh_response = supabase.auth.refresh_session(refresh_token)
            if not refresh_response.user:
                raise Exception("Invalid refresh token: No user found in response")
            return refresh_response
        
        try:
            refresh_response = retry_with_exponential_backoff(refresh_tokens)
            logger.info(f"Tokens refreshed successfully for user: {refresh_response.user.id}")
            
            # Set new cookies
            response.set_cookie(
                key="access_token",
                value=refresh_response.session.access_token,
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=refresh_response.session.expires_in,
            )
            response.set_cookie(
                key="refresh_token",
                value=refresh_response.session.refresh_token,
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=60 * 60 * 24 * 7,  # 7 days
            )
            
            return {
                "valid": True,
                "action": "redirect_to_dashboard",
                "user_id": refresh_response.user.id,
                "email": refresh_response.user.email,
                "message": "Tokens refreshed successfully"
            }
                
        except Exception as e:
            logger.warning(f"Refresh failed: {str(e)}")
            
            # Scenario 4: Both tokens are invalid - clear cookies and stay on welcome page
            response.set_cookie(
                key="access_token",
                value="",
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=0,
            )
            response.set_cookie(
                key="refresh_token",
                value="",
                httponly=True,
                secure=True,
                samesite="strict",
                max_age=0,
            )
            
            return {
                "valid": False,
                "action": "stay_on_welcome",
                "message": "Invalid credentials - please log in"
            }
            
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {str(e)}")
        return {
            "valid": False,
            "action": "stay_on_welcome",
            "message": "Authentication validation failed"
        }


@router.post("/logout-portal", status_code=status.HTTP_200_OK)
async def logout_portal(response: Response):
    """
    Endpoint for user logout - clears authentication cookies.
    Equivalent to Flask: POST /logout-portal
    """
    logger.info("User logging out")
    
    # Clear authentication cookies
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=0,  # Expire immediately
    )
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=0,  # Expire immediately
    )
    
    logger.info("Authentication cookies cleared")
    return {"message": "Logged out successfully"}

