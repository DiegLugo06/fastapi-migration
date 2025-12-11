"""
CORS middleware configuration
"""
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ALLOWED_ORIGINS, CORS_ALLOW_CREDENTIALS


def setup_cors(app):
    """
    Setup CORS middleware for FastAPI app
    
    FastAPI's CORSMiddleware automatically handles OPTIONS preflight requests,
    so no additional configuration is needed for that.
    
    Usage:
        from app.middleware.cors import setup_cors
        setup_cors(app)
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWED_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Public-Key"],
    )