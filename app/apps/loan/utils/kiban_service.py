"""
Kiban API Service
Migrated from app/extensions/kiban.py
"""
import httpx
from typing import Dict, Any, Union
import logging
from app.config import MODE

logger = logging.getLogger(__name__)


class KIBANAPIService:
    def __init__(self):
        import os
        # Get KIBAN API settings based on mode
        self.api_url = os.getenv(
            "KIBAN_API_URL_PRODUCTION" if MODE == "production" else "KIBAN_API_URL_STAGING"
        )
        self.access_key = os.getenv(
            "KIBAN_API_KEY_PRODUCTION" if MODE == "production" else "KIBAN_API_KEY_STAGING"
        )
        
        if not self.api_url or not self.access_key:
            logger.warning("KIBAN API configuration missing. Some features may not work.")
        
        self.headers = {
            "x-api-key": self.access_key,
            "Content-Type": "application/json",
        }
        self.timeout = 10.0

    async def _post_request(
        self, endpoint: str, parameters: Dict[str, Any], body: Dict[str, Any]
    ) -> Union[Dict[str, Any], Dict[str, Any]]:
        """Helper method to make POST requests."""
        if not self.api_url:
            return {
                "error": "ConfigurationError",
                "message": "KIBAN API URL not configured"
            }
        
        url = f"{self.api_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    params=parameters,
                    headers=self.headers,
                    json=body,
                )
                response.raise_for_status()  # Raises an HTTPError for bad responses (4xx, 5xx)
                return response.json()
        except httpx.HTTPStatusError as http_err:
            error_detail = None
            try:
                error_detail = http_err.response.json() if http_err.response.content else None
            except:
                error_detail = http_err.response.text if http_err.response.content else None
            
            return {
                "error": "HTTPError",
                "status_code": http_err.response.status_code,
                "message": str(http_err),
                "details": error_detail,
            }
        except httpx.RequestError as req_err:
            return {"error": "RequestException", "message": str(req_err)}
        except Exception as e:
            return {"error": "Exception", "message": str(e)}

    async def generate_rfc(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Generate RFC."""
        params = (
            {"testCaseId": "664230608659f0c02fcd3f0c"} if MODE != "production" else {}
        )
        return await self._post_request("/sat/rfc_pf", params, body)

    async def send_nip_kiban(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Send NIP to KIBAN."""
        params = {"testCase": "success"} if MODE != "production" else {}
        return await self._post_request("/nip/send", params, body)

    async def verify_nip_kiban(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Verify NIP."""
        params = {"testCase": "success"} if MODE != "production" else {}
        return await self._post_request("/nip/validate", params, body)

    async def query_bc_pf_by_kiban(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Query BC PF by KIBAN."""
        params = (
            {"testCaseId": "66c3a67c799bfa07801e8dbe"} if MODE != "production" else {}
        )
        endpoint = (
            "/bc_pf_rce/query" if MODE != "production" else "/bc_pf_by_kiban/query"
        )
        return await self._post_request(endpoint, params, body)

    async def validate_rfc(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Validate RFC."""
        params = (
            {"testCaseId": "663567bb713cf2110a1106ce"} if MODE != "production" else {}
        )
        return await self._post_request("/rfc_sat/rfc_validate", params, body)

    async def validate_nominal_list(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Validate nominal list."""
        params = (
            {"testCaseId": "663567bb713cf2110a1106c6"} if MODE != "production" else {}
        )
        return await self._post_request("/ine/validate", params, body)

    async def query_cc_pf(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Query CC PF."""
        params = (
            {"testCaseId": "663567bb713cf2110a110698"} if MODE != "production" else {}
        )
        return await self._post_request("/cc_pf/query", params, body)

    async def get_ocr_data(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Get OCR data."""
        params = (
            {"testCaseId": "66e374b4922ebf2dc27ab3bf"} if MODE != "production" else {}
        )
        return await self._post_request("/ine/data_extraction", params, body)

    async def get_curp_data(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Get CURP data."""
        params = (
            {"testCaseId": "663567bb713cf2110a1106b0"} if MODE != "production" else {}
        )
        return await self._post_request("/curp/validate", params, body)

    async def generate_curp(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Generate CURP from data."""
        params = (
            {"testCaseId": "663567bb713cf2110a1106b3"} if MODE != "production" else {}
        )
        return await self._post_request("/curp/validateData", params, body)


# Initialize the KIBAN API service
kiban_api = KIBANAPIService()

