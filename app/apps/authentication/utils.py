"""
Authentication utilities
"""
from supabase import create_client
from app.config import get_supabase_url, get_supabase_token, get_supabase_confirmation_url
import logging

logger = logging.getLogger(__name__)

# Singleton instance
_supabase_service = None


def get_supabase_client():
    """
    Get Supabase client instance (singleton pattern).
    
    Returns:
        Client: Supabase client instance
    """
    global _supabase_service
    
    if _supabase_service is None:
        try:
            _supabase_service = create_client(get_supabase_url(), get_supabase_token())
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise
    
    return _supabase_service

