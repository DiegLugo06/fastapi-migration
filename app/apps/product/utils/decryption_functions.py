"""
Decryption functions for product module
Migrated from Flask app/product/utils/decryption_functions.py
"""
import hmac
import hashlib
import base64
import logging
from app.config import get_env_var

logger = logging.getLogger(__name__)


def generate_hash(motorcycle_id: int, discount_id: int, user_id: int) -> str:
    """
    Generate an encoded string with motorcycle_id, user_id, and discount_id, verified with HMAC.
    """
    SECRET_KEY = get_env_var("HASH_KEY")
    # Combine motorcycle_id, user_id, and discount_id as plain text
    data = f"{motorcycle_id}:{user_id}:{discount_id}".encode()
    
    # Generate an HMAC for the data using the secret key
    hmac_obj = hmac.new(SECRET_KEY.encode(), data, hashlib.sha256)
    hmac_digest = hmac_obj.digest()
    
    # Encode both the data and HMAC into a single string
    combined = data + hmac_digest
    return base64.urlsafe_b64encode(combined).decode()


def decode_hash(hash_str: str):
    """
    Decode the hash and verify it with HMAC to retrieve motorcycle_id, user_id, and discount_id.
    Returns tuple: (motorcycle_id, user_id, discount_id) or (None, None, None) on error.
    """
    try:
        # Decode the combined base64 string
        decoded = base64.urlsafe_b64decode(hash_str.encode())
        
        # Split the decoded data and HMAC
        # Fixed HMAC length for SHA-256
        data, received_hmac = decoded[:-32], decoded[-32:]
        SECRET_KEY = get_env_var("HASH_KEY")
        
        # Verify HMAC
        expected_hmac = hmac.new(
            SECRET_KEY.encode(), data, hashlib.sha256).digest()
        if not hmac.compare_digest(received_hmac, expected_hmac):
            raise ValueError("Invalid HMAC, data has been tampered with.")
        
        # Extract motorcycle_id, user_id, and discount_id
        data_str = data.decode()
        fields = data_str.split(":")
        if len(fields) != 3:
            raise ValueError("Invalid data format.")
        motorcycle_id, user_id, discount_id = map(int, fields)
        return motorcycle_id, user_id, discount_id
    
    except (ValueError, base64.binascii.Error) as e:
        logger.error(f"Decoding error: {e}")
        return None, None, None

