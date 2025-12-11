"""
Common custom field types
Migrated from Django apps/common_fields.py
"""
from typing import Any, Dict, List, Union
import json


def handle_postgresql_json(value: Any) -> Union[Dict, List, None]:
    """
    Handle PostgreSQL JSONB fields correctly.
    
    PostgreSQL's asyncpg adapter returns JSONB columns as Python dicts/lists,
    not strings. This function handles both cases:
    - When value is already a dict/list (from PostgreSQL) -> return as-is
    - When value is a string (from other DBs or serialization) -> parse it
    
    Args:
        value: The value from database (could be dict, list, str, or None)
    
    Returns:
        Parsed JSON value (dict, list) or None
    """
    if value is None:
        return value
    
    # If value is already a dict/list (from PostgreSQL JSONB), return it directly
    if isinstance(value, (dict, list)):
        return value
    
    # Otherwise, parse it as JSON string
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value