"""
ValidaCurp API Service for FastAPI
Async-compatible service for interacting with ValidaCurp API
"""
import httpx
from typing import Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class ValidaCurpAPIService:
    """Service for interacting with the ValidaCurp API with async support."""

    def __init__(self):
        self.api_url = os.getenv("VALIDACURP_API_URL", "")
        self.access_key = os.getenv("VALIDACURP_ACCESS_KEY", "")
        self.headers = {
            "Content-Type": "application/json",
        }
        self.timeout = 10.0

    async def _get_request(self, endpoint: str) -> Dict[str, Any]:
        """Helper method to make async GET requests."""
        url = f"{self.api_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as http_err:
            logger.error(f"HTTP Error from ValidaCurp API - endpoint: {endpoint}, status_code: {http_err.response.status_code if http_err.response else 'Unknown'}")
            return {
                "error": "HTTPError",
                "status_code": http_err.response.status_code if http_err.response else "Unknown",
                "message": str(http_err),
                "details": http_err.response.json() if http_err.response and http_err.response.content else None,
            }
        except httpx.RequestError as req_err:
            logger.error(f"Request Exception from ValidaCurp API - endpoint: {endpoint}, message: {str(req_err)}")
            return {"error": "RequestException", "message": str(req_err)}
        except Exception as e:
            logger.error(f"Exception from ValidaCurp API - endpoint: {endpoint}, message: {str(e)}")
            return {"error": "Exception", "message": str(e)}

    async def validate_curp(self, curp: str) -> Dict[str, Any]:
        """Validate CURP structure."""
        endpoint = f"/curp/validar/?token={self.access_key}&curp={curp}"
        return await self._get_request(endpoint)

    async def get_curp_data(self, curp: str) -> Dict[str, Any]:
        """Get data from a CURP."""
        endpoint = f"/curp/obtener_datos/?token={self.access_key}&curp={curp}"
        return await self._get_request(endpoint)

    async def calculate_curp(
        self,
        entidad: str,
        sexo: str,
        anio_nacimiento: str,
        mes_nacimiento: str,
        dia_nacimiento: str,
        apellido_paterno: str,
        apellido_materno: str,
        nombres: str
    ) -> Dict[str, Any]:
        """Calculate CURP from person's data."""
        endpoint = (
            f"/curp/calcular_curp?token={self.access_key}"
            f"&entidad={entidad}"
            f"&sexo={sexo}"
            f"&anio_nacimiento={anio_nacimiento}"
            f"&mes_nacimiento={mes_nacimiento}"
            f"&dia_nacimiento={dia_nacimiento}"
            f"&apellido_paterno={apellido_paterno}"
            f"&apellido_materno={apellido_materno}"
            f"&nombres={nombres}"
        )
        return await self._get_request(endpoint)


# Initialize the ValidaCurp API service instance
valida_curp_service = ValidaCurpAPIService()

