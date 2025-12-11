"""
SEPOMEX Service
Migrated from Flask app/extensions/sepomex.py
"""
import httpx
from typing import Dict, Any, Optional
import logging

from app.config import get_env_var

logger = logging.getLogger(__name__)


class SEPOMEXService:
    def __init__(self):
        self.api_url = get_env_var("SEPOMEX_URL", "")
        self.access_key = get_env_var("SEPOMEX_KEY", "")
        self.timeout = 3  # Set a default timeout of 3 seconds

    async def validate_cp(self, zip_code: str) -> Optional[Dict[str, Any]]:
        """
        Validate a ZIP code using the SEPOMEX API.

        Args:
            zip_code: The ZIP code to validate.

        Returns:
            A dictionary containing the validation result, or None if an error occurs.
        """
        if not self.api_url or not self.access_key:
            logger.warning("SEPOMEX API URL or key not configured")
            return None

        headers = {
            "APIKEY": self.access_key
        }
        params = {
            'cp': zip_code
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.api_url,
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.error(f"SEPOMEX request timed out after {self.timeout} seconds")
        except httpx.HTTPStatusError as http_err:
            logger.error(f"SEPOMEX HTTP error: {http_err}")
        except httpx.RequestError as req_err:
            logger.error(f"SEPOMEX request error: {req_err}")
        except Exception as e:
            logger.error(f"SEPOMEX unexpected error: {e}")

        return None


# Initialize the SEPOMEX service
sepomex_service = SEPOMEXService()

