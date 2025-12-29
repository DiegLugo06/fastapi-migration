"""
Nobarium API Service for FastAPI
Async-compatible service for interacting with Nobarium API
"""
import base64
import httpx
from typing import Dict, Any, Optional
from app.config import MODE
import logging

logger = logging.getLogger(__name__)


class NobariumService:
    """Service for interacting with the Nobarium API with async support."""

    def __init__(self):
        import os
        username = os.getenv("NOBARIUM_USERNAME")
        password = os.getenv("NOBARIUM_PASSWORD")
        
        if not username or not password:
            raise ValueError("NOBARIUM_USERNAME and NOBARIUM_PASSWORD must be set")
        
        # Generate Basic Auth token
        credentials = f"{username}:{password}"
        self.auth_token = base64.b64encode(credentials.encode()).decode()
        
        self.ocr_base_url = "https://ocr.nubarium.com"
        self.ine_base_url = "https://ine.nubarium.com"
        self.curp_base_url = "https://curp.nubarium.com"
        self.headers = {
            "Authorization": f"Basic {self.auth_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.timeout = 45.0

    async def _post_request(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Makes an async POST request to the Nobarium API.

        Args:
            url (str): Full API URL.
            body (Dict[str, Any]): Request payload.

        Returns:
            Dict[str, Any]: API response or formatted error.
        """
        logger.info(f"Making POST request to Nobarium API - url: {url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=self.headers, json=body)
                response.raise_for_status()

                # Check if response has content
                if response.status_code == 204 or not response.content.strip():
                    logger.warning(
                        f"Empty response from Nobarium API - url: {url}, status_code: {response.status_code}"
                    )
                    return {
                        "error": "EmptyResponse",
                        "status_code": response.status_code,
                        "message": "No content returned from API",
                    }

                # Parse JSON response
                try:
                    response_data = response.json()
                    logger.info(
                        f"Received response from Nobarium API - url: {url}, status_code: {response.status_code}"
                    )
                    return response_data
                except Exception as json_err:
                    logger.error(
                        f"Invalid JSON response from Nobarium API - url: {url}, status_code: {response.status_code}"
                    )
                    return {
                        "error": "InvalidJSONResponse",
                        "status_code": response.status_code,
                        "message": "API response is not valid JSON",
                        "raw_response": response.text[:500],
                    }

        except httpx.HTTPStatusError as http_err:
            logger.error(
                f"HTTP Error from Nobarium API - url: {url}, status_code: {http_err.response.status_code if http_err.response else 'Unknown'}, message: {str(http_err)}"
            )
            return {
                "error": "HTTPError",
                "status_code": http_err.response.status_code if http_err.response else "Unknown",
                "message": str(http_err),
                "raw_response": http_err.response.text[:500] if http_err.response else "No response",
            }

        except httpx.RequestError as req_err:
            logger.error(
                f"Request Exception from Nobarium API - url: {url}, message: {str(req_err)}"
            )
            return {"error": "RequestException", "message": str(req_err)}

        except Exception as e:
            logger.error(
                f"Unexpected error from Nobarium API - url: {url}, error_type: {type(e).__name__}, message: {str(e)}"
            )
            return {"error": "Exception", "message": str(e)}

    async def ocr_extract_data(self, id_front_base64: str, id_back_base64: str) -> Dict[str, Any]:
        """
        Extracts data from INE card using OCR.
        
        Args:
            id_front_base64 (str): Front of the ID in base64 format
            id_back_base64 (str): Back of the ID in base64 format
            
        Returns:
            Dict[str, Any]: Extracted data from the INE card
        """
        endpoint = f"{self.ocr_base_url}/ocr/v1/obtener_datos_id"
        
        # Clean base64 data (remove data URI prefix if present)
        if id_front_base64.startswith('data:'):
            id_front_base64 = id_front_base64.split(',', 1)[1] if ',' in id_front_base64 else id_front_base64
        if id_back_base64.startswith('data:'):
            id_back_base64 = id_back_base64.split(',', 1)[1] if ',' in id_back_base64 else id_back_base64
        
        body = {
            "id": id_front_base64,
            "idReverso": id_back_base64
        }
        
        logger.info(f"Nobarium OCR request - endpoint: {endpoint}")
        result = await self._post_request(endpoint, body)
        
        if 'error' in result:
            logger.error(f"Nobarium OCR error: {result}")
        elif result.get('estatus') == 'ERROR':
            logger.error(f"Nobarium OCR API error: {result}")
        
        return result

    async def validate_ine(self, cic: str, identificador_ciudadano: str) -> Dict[str, Any]:
        """
        Validates INE using extracted data.
        
        Args:
            cic (str): CIC number from OCR extraction
            identificador_ciudadano (str): Citizen identifier from OCR extraction
            
        Returns:
            Dict[str, Any]: Validation result
        """
        endpoint = f"{self.ine_base_url}/ine/v2/valida_ine"
        body = {
            "cic": cic,
            "identificadorCiudadano": identificador_ciudadano
        }
        
        logger.info(f"Nobarium INE validation request - cic: {cic}, identificadorCiudadano: {identificador_ciudadano}")
        result = await self._post_request(endpoint, body)
        
        return result

    async def validate_curp(self, curp: str) -> Dict[str, Any]:
        """
        Validates CURP using Nobarium RENAPO service.
        
        Args:
            curp (str): CURP to validate
            
        Returns:
            Dict[str, Any]: Validation result including RFC generation
        """
        endpoint = f"{self.curp_base_url}/renapo/v3/valida_curp"
        body = {
            "curp": curp,
            "generarRFC": True
        }
        return await self._post_request(endpoint, body)


# Initialize the Nobarium API service instance
nobarium_service = NobariumService()

