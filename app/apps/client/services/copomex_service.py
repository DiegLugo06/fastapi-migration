"""
Copomex API Service
Migrated from Flask app/extensions/copomex.py
"""
import httpx
from typing import Dict, Any, Union
import logging

from app.config import get_env_var

logger = logging.getLogger(__name__)


class CopomexAPIService:
    def __init__(self):
        self.api_url = get_env_var("COPOMEX_URL", "")
        self.access_key = get_env_var("COPOMEX_KEY", "")
        self.headers = {
            "Content-Type": "application/json",
        }
        self.timeout = 10

    async def _get_request(self, endpoint: str) -> Union[Dict[str, Any], Dict[str, Any]]:
        """Helper method to make GET requests."""
        if not self.api_url or not self.access_key:
            logger.warning("Copomex API URL or key not configured")
            return {"error": "ConfigurationError", "message": "API not configured"}

        url = f"{self.api_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as http_err:
            error_response = {
                "error": "HTTPError",
                "status_code": http_err.response.status_code,
                "message": str(http_err),
            }
            try:
                error_response["details"] = http_err.response.json()
            except Exception:
                error_response["details"] = None
            return error_response
        except httpx.RequestError as req_err:
            return {"error": "RequestException", "message": str(req_err)}
        except Exception as e:
            return {"error": "Exception", "message": str(e)}

    async def get_neighborhoods_by_zip(self, zip_code: str) -> Dict[str, Any]:
        """Get neighborhoods by zip code."""
        endpoint = (
            f"/query/get_colonia_por_cp/{zip_code}?token={self.access_key}"
        )
        return await self._get_request(endpoint)

    async def get_zip_codes_by_state(self, state: str) -> Dict[str, Any]:
        """Get zip codes by state."""
        endpoint = f"/query/get_cp_por_estado/{state}?token={self.access_key}"
        return await self._get_request(endpoint)

    async def validate_cp(self, zip_code: str) -> Dict[str, Any]:
        """Validate zip code."""
        endpoint = f"/query/info_cp_geocoding/{zip_code}?type=simplified&token={self.access_key}"
        return await self._get_request(endpoint)


# Initialize the Copomex API service
copomex_service = CopomexAPIService()

