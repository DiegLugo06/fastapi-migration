"""
Verificamex API Service for FastAPI
Async-compatible service for interacting with Verificamex API
"""
import httpx
from typing import Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class VerificamexService:
    """Service for interacting with the Verificamex API with async support."""

    def __init__(self):
        self.base_url = os.getenv("VERIFICAMEX_URL", "")
        self.access_token = os.getenv("VERIFICAMEX_ACCESS_TOKEN", "")
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        self.timeout = 45.0

    async def _post_request(self, endpoint: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Makes an async POST request to the Verificamex API.

        Args:
            endpoint (str): API endpoint.
            body (Dict[str, Any]): Request payload.

        Returns:
            Dict[str, Any]: API response or formatted error.
        """
        url = f"{self.base_url}{endpoint}"
        logger.info(
            f"Making POST request to Verificamex API - endpoint: {endpoint}, body_keys: {list(body.keys())}"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=self.headers, json=body)
                response.raise_for_status()

                # Check if response has content
                if response.status_code == 204 or not response.content.strip():
                    logger.warning(
                        f"Empty response from Verificamex API - endpoint: {endpoint}, status_code: {response.status_code}"
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
                        f"Received response from Verificamex API - endpoint: {endpoint}"
                    )
                    return response_data
                except Exception as json_err:
                    logger.error(
                        f"Invalid JSON response from Verificamex API - endpoint: {endpoint}, status_code: {response.status_code}"
                    )
                    return {
                        "error": "InvalidJSONResponse",
                        "status_code": response.status_code,
                        "message": "API response is not valid JSON",
                        "raw_response": response.text[:500],
                    }

        except httpx.HTTPStatusError as http_err:
            logger.error(
                f"HTTP Error from Verificamex API - endpoint: {endpoint}, status_code: {http_err.response.status_code if http_err.response else 'Unknown'}, message: {str(http_err)}"
            )
            return {
                "error": "HTTPError",
                "status_code": http_err.response.status_code if http_err.response else "Unknown",
                "message": str(http_err),
                "raw_response": http_err.response.text[:500] if http_err.response else "No response",
            }

        except httpx.RequestError as req_err:
            logger.error(
                f"Request Exception from Verificamex API - endpoint: {endpoint}, message: {str(req_err)}"
            )
            return {"error": "RequestException", "message": str(req_err)}

        except Exception as e:
            logger.error(
                f"Unexpected error from Verificamex API - endpoint: {endpoint}, error_type: {type(e).__name__}, message: {str(e)}"
            )
            return {"error": "Exception", "message": str(e)}

    async def ocr_obverse(self, img_base_64: str) -> Dict[str, Any]:
        """Processes the front of an INE card using OCR."""
        return await self._post_request(
            "/identity/v1/ocr/obverse", {"ine_front": img_base_64}
        )

    async def ocr_reverse(self, img_base_64: str) -> Dict[str, Any]:
        """Processes the back of an INE card using OCR."""
        return await self._post_request("/identity/v1/ocr/reverse", {"ine_back": img_base_64})

    async def validate_curp(self, curp: str) -> Dict[str, Any]:
        """Validate CURP using Verificamex."""
        return await self._post_request("/v1/scraping/renapo", {"curp": curp})

    async def validate_ine(self, body: Dict[str, str]) -> Dict[str, Any]:
        """Validate INE using Verificamex."""
        return await self._post_request("/v1/scraping/ine", body)

    async def validate_rfc(self, rfc: str) -> Dict[str, Any]:
        """Validate RFC using Verificamex."""
        return await self._post_request("/v1/miscellaneous/sat/rfc", {"rfc": rfc})


# Initialize the Verificamex API service instance
verificamex_service = VerificamexService()

