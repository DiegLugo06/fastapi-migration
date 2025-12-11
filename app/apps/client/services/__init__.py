"""
Client services module
"""
from app.apps.client.services.sepomex_service import sepomex_service
from app.apps.client.services.copomex_service import copomex_service
from app.apps.client.services.supabase_storage import supabase_storage

__all__ = ['sepomex_service', 'copomex_service', 'supabase_storage']

