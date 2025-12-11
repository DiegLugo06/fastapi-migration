"""
Configuration settings for FastAPI application
Migrated from Django config/settings.py
"""
import os
import tempfile
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-ovwrrjs0oc2xmqwwna4)sq1_30gudtv=qty^pw4rhf^uzo9t&q')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Allowed hosts
ALLOWED_HOSTS: List[str] = [
    'localhost',
    '127.0.0.1',
    # Add your production domains here
]

# Get mode (development or production)
MODE = os.getenv("MODE", "development")


def get_env_var(key: str, default: str = None) -> str:
    """Fetch an environment variable and raise an error if it's missing (unless default is provided)."""
    value = os.getenv(key, default)
    if value is None and default is None:
        raise ValueError(f"Missing environment variable: {key}")
    return value


# Database URL
DATABASE_URL = get_env_var(
    "PRODUCTION_DB_URL" if MODE == "production" else "STAGING_DB_URL"
)

# SSL Certificate handling (similar to Django)
DB_SSL_CERT_CONTENT = get_env_var("DB_SSL_CERT")
DB_SSL_CERT_PATH = os.path.join(tempfile.gettempdir(), "db-ca.crt")

# Write the certificate to a file at runtime
with open(DB_SSL_CERT_PATH, "w") as f:
    f.write(DB_SSL_CERT_CONTENT)

# CORS Configuration
# Include both localhost and 127.0.0.1 as browsers treat them as different origins
CORS_ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "https://nuxt-naive-project-production.up.railway.app",
    "https://nuxt-quasar-migration-production.up.railway.app"
]

CORS_ALLOW_CREDENTIALS = True

# Time zone configuration
TIME_ZONE = 'America/Mexico_City'
LANGUAGE_CODE = 'en-us'

# Frontend URL for quote links
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Hash key for discount encoding/decoding
HASH_KEY = os.getenv('SECRET_HASH_KEY', os.getenv('HASH_KEY', ''))

# Supabase Configuration
def get_supabase_url() -> str:
    """Get Supabase URL based on mode"""
    if MODE == "production":
        return get_env_var("PRODUCTION_SUPABASE_URL")
    return get_env_var("STAGING_SUPABASE_URL")


def get_supabase_token() -> str:
    """Get Supabase token based on mode"""
    if MODE == "production":
        return get_env_var("PRODUCTION_SUPABASE_TOKEN")
    return get_env_var("STAGING_SUPABASE_TOKEN")


def get_supabase_confirmation_url() -> str:
    """Get Supabase confirmation URL based on mode"""
    if MODE == "production":
        return os.getenv("PRODUCTION_SUPABASE_URL_CONFIRMATION", "")
    return os.getenv("STAGING_SUPABASE_URL_CONFIRMATION", "")