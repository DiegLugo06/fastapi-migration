"""
Supabase client utility for client module
Migrated from Flask extensions/supabase.py
"""
from app.apps.authentication.utils import get_supabase_client

# Re-export for convenience
__all__ = ['get_supabase_client']

