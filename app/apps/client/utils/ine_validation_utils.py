"""
INE Validation Utilities for FastAPI
Async-compatible utilities for INE validation and OCR processing
"""
import time
import base64
import asyncio
from typing import Dict, Any, Tuple, Optional
import logging

from app.apps.client.services.nobarium_service import nobarium_service
from app.apps.client.services.valida_curp_service import valida_curp_service
from app.apps.client.services.verificamex_service import verificamex_service
from app.apps.client.utils.curp_transformers import (
    transform_nubarium_curp_response,
    transform_first_service_response,
    transform_second_service_response,
)

logger = logging.getLogger(__name__)


def extract_curp_from_nobarium(ine_full_info: Dict[str, Any]) -> str:
    """
    Extract CURP from Nobarium OCR response.
    
    Args:
        ine_full_info (dict): The complete response from Nobarium OCR service
        
    Returns:
        str: The CURP value or empty string if not found
    """
    try:
        curp = ine_full_info.get('curp', '')
        if curp:
            curp = str(curp).strip().upper()
        logger.info(f"Extracted CURP from Nobarium: {curp}")
        return curp
    except Exception as e:
        logger.error(f"Error extracting CURP from Nobarium response: {e}")
        return ""


def prepare_validation_body_nobarium(ine_full_info: Dict[str, Any]) -> Dict[str, str]:
    """Prepare validation body for INE validation using Nobarium."""
    return {
        "cic": ine_full_info.get("cic", ""),
        "identificadorCiudadano": ine_full_info.get("identificadorCiudadano", ""),
    }


def prepare_validation_body(back_data: Dict[str, Any]) -> Dict[str, str]:
    """Prepare validation body for INE validation using Verificamex."""
    return {
        "cic": back_data.get("doc_number", ""),
        "id_citizen": back_data.get("first_optional", "").replace("<", ""),
        "model": "E",
    }


async def process_ocr_with_nobarium(
    ine_front_base64: str, ine_back_base64: str, request_id: str
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Process OCR with Nobarium."""
    ocr_start = time.time()
    try:
        ine_full_info = await nobarium_service.ocr_extract_data(
            ine_front_base64, ine_back_base64
        )
        timing_metrics = {"OCR_extraction": time.time() - ocr_start}
        return ine_full_info, timing_metrics
    except Exception as e:
        logger.error(f"[{request_id}] OCR processing failed - error: {str(e)}")
        raise


async def process_ocr_parallel(
    ine_front_base64: str, ine_back_base64: str, request_id: str
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    """Process OCR for both front and back images in parallel."""
    ocr_start = time.time()
    
    try:
        # Process both images concurrently
        front_task = verificamex_service.ocr_obverse(ine_front_base64)
        back_task = verificamex_service.ocr_reverse(ine_back_base64)
        
        front_info, back_info = await asyncio.gather(front_task, back_task)
        
        timing_metrics = {"ocr_processing": time.time() - ocr_start}
        return front_info, back_info, timing_metrics
    except Exception as e:
        logger.error(f"[{request_id}] OCR processing failed - error: {str(e)}")
        raise


def validate_ocr_results(
    front_info: Dict[str, Any], back_info: Dict[str, Any], request_id: str
) -> Tuple[Optional[Tuple[list, Dict]], Optional[Dict[str, Any]]]:
    """Validate OCR results and return error details if validation fails."""
    back_data = back_info.get("data", {}).get("mrz", {})
    front_data = front_info.get("data", {}).get("parse_ocr", [])

    if (
        back_data == {}
        or front_data == []
        or "error" in front_info
        or "error" in back_info
    ):
        error_details = {
            "front_error": bool("error" in front_info),
            "back_error": bool("error" in back_info),
            "front_error_message": front_info.get("error", ""),
            "back_error_message": back_info.get("error", ""),
        }

        logger.error(f"[{request_id}] OCR validation failed")
        return None, error_details

    return (front_data, back_data), None


async def validate_curp_and_ine_parallel(
    curp: str,
    body_validate_ine: Dict[str, Any],
    request_id: str,
    ocr_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """
    Validate CURP and INE sequentially - try nubarium first, then fallback to verificamex.
    """
    start_time = time.time()
    validation_results = {}
    timing_metrics = {}

    try:
        # Validate CURP with nubarium first
        curp_primary_result = await nobarium_service.validate_curp(curp)

        # Check if nubarium CURP validation was successful
        if curp_primary_result and curp_primary_result.get("estatus") == "OK":
            validation_results["curp"] = {
                "data": transform_nubarium_curp_response(curp_primary_result),
                "service": "nubarium",
                "is_valid": True,
            }
            # Extract RFC if available
            rfc = curp_primary_result.get("rfcGenerado", "")
            if rfc:
                validation_results["curp"]["rfc"] = rfc
        else:
            # Try fallback CURP validation
            curp_fallback_result = await valida_curp_service.get_curp_data(curp)

            if curp_fallback_result and not curp_fallback_result.get("error", True):
                validation_results["curp"] = {
                    "data": transform_first_service_response(curp_fallback_result),
                    "service": "valida_curp",
                    "is_valid": True,
                }
            else:
                # Try second fallback (Verificamex)
                curp_second_fallback = await verificamex_service.validate_curp(curp)
                if curp_second_fallback and "error" not in curp_second_fallback:
                    validation_results["curp"] = {
                        "data": transform_second_service_response(curp_second_fallback),
                        "service": "verificamex",
                        "is_valid": True,
                    }
                else:
                    validation_results["curp"] = {
                        "error": "All CURP validation services failed",
                        "is_valid": False,
                    }

        # Validate INE with nubarium first (if OCR data is available)
        if ocr_data:
            body_validate_ine_nobarium = prepare_validation_body_nobarium(ocr_data)

            cic = body_validate_ine_nobarium.get("cic", "")
            identificador_ciudadano = body_validate_ine_nobarium.get(
                "identificadorCiudadano", ""
            )

            if cic and identificador_ciudadano:
                ine_primary_result = await nobarium_service.validate_ine(
                    cic, identificador_ciudadano
                )

                if ine_primary_result:
                    if ine_primary_result.get("estatus") == "OK":
                        validation_results["ine"] = {
                            "data": ine_primary_result,
                            "service": "nubarium",
                            "is_valid": True,
                            "status": "completed",
                        }
                    else:
                        # Check for mapped error codes
                        clave_mensaje = ine_primary_result.get("claveMensaje", "")
                        if clave_mensaje in ["0", "1", "3", "5", "6", "7", "8", "9"]:
                            is_valid = clave_mensaje == "3"
                            validation_results["ine"] = {
                                "data": ine_primary_result,
                                "service": "nubarium",
                                "is_valid": is_valid,
                                "status": "completed" if is_valid else "failed",
                            }
                        else:
                            # Fall back to verificamex
                            ine_fallback_result = await verificamex_service.validate_ine(
                                body_validate_ine
                            )

                            if ine_fallback_result and "error" not in ine_fallback_result:
                                ine_result = ine_fallback_result.get("data", {})
                                if ine_result:
                                    # Remove pdf field if it exists
                                    if (
                                        "ineNominalList" in ine_result
                                        and "pdf" in ine_result["ineNominalList"]
                                    ):
                                        del ine_result["ineNominalList"]["pdf"]

                                    validation_results["ine"] = {
                                        "data": ine_result,
                                        "service": "verificamex",
                                        "is_valid": True,
                                        "status": "completed",
                                    }
                                else:
                                    validation_results["ine"] = {
                                        "error": "No data returned from verificamex fallback",
                                        "status": "failed",
                                        "is_valid": False,
                                    }
                            else:
                                validation_results["ine"] = {
                                    "error": (
                                        ine_fallback_result.get("error", "Unknown error")
                                        if ine_fallback_result
                                        else "Verificamex fallback failed"
                                    ),
                                    "status": "failed",
                                    "is_valid": False,
                                }
            else:
                validation_results["ine"] = {
                    "error": "Missing required parameters for nubarium validation",
                    "status": "failed",
                    "is_valid": False,
                }
        else:
            # Use verificamex for INE validation
            ine_fallback_result = await verificamex_service.validate_ine(body_validate_ine)

            if ine_fallback_result and "error" not in ine_fallback_result:
                ine_result = ine_fallback_result.get("data", {})
                if ine_result:
                    # Remove pdf field if it exists
                    if (
                        "ineNominalList" in ine_result
                        and "pdf" in ine_result["ineNominalList"]
                    ):
                        del ine_result["ineNominalList"]["pdf"]

                    validation_results["ine"] = {
                        "data": ine_result,
                        "service": "verificamex",
                        "is_valid": True,
                        "status": "completed",
                    }
                else:
                    validation_results["ine"] = {
                        "error": "No data returned from verificamex",
                        "status": "failed",
                        "is_valid": False,
                    }
            else:
                validation_results["ine"] = {
                    "error": ine_fallback_result.get("error", "Unknown error") if ine_fallback_result else "Verificamex failed",
                    "status": "failed",
                    "is_valid": False,
                }

        timing_metrics["validation_time"] = time.time() - start_time
        return validation_results, timing_metrics

    except Exception as e:
        logger.error(f"[{request_id}] Sequential validation failed: {str(e)}")
        # Set default error responses
        if "curp" not in validation_results:
            validation_results["curp"] = {"error": str(e), "status": "failed", "is_valid": False}
        if "ine" not in validation_results:
            validation_results["ine"] = {
                "error": str(e),
                "status": "failed",
                "is_valid": False,
            }

        timing_metrics["validation_time"] = time.time() - start_time
        return validation_results, timing_metrics


def prepare_nobarium_combined_response(
    ocr_data: Dict[str, Any],
    validation_results: Dict[str, Any],
    timing_metrics: Dict[str, float],
) -> Dict[str, Any]:
    """Prepare the combined response with Nobarium OCR and validation results."""
    curp = ocr_data.get("curp", "")
    body_validate_ine = prepare_validation_body_nobarium(ocr_data)

    # Extract RFC from validation results if available
    rfc = ""
    if (
        "curp" in validation_results
        and "error" not in validation_results["curp"]
        and "rfc" in validation_results["curp"]
    ):
        rfc = validation_results["curp"]["rfc"]
    elif (
        "curp" in validation_results
        and "error" not in validation_results["curp"]
        and "data" in validation_results["curp"]
    ):
        rfc = validation_results["curp"]["data"].get("rfc", "")

    response = {
        "curp": curp,
        "rfc": rfc,
        "front_info": {
            "data": {
                "parse_ocr": [
                    {"value": ocr_data.get("nombre", "")},
                    {"value": ocr_data.get("apellidoPaterno", "")},
                    {"value": ocr_data.get("apellidoMaterno", "")},
                ]
            }
        },
        "back_info": {
            "data": {
                "mrz": {
                    "doc_number": ocr_data.get("cic", ""),
                    "first_optional": ocr_data.get("identificadorCiudadano", ""),
                }
            }
        },
        "body_validate_ine": body_validate_ine,
        "timing_metrics": timing_metrics,
        "validation_results": validation_results,
    }

    # Add validation status
    curp_valid = (
        "curp" in validation_results
        and "error" not in validation_results["curp"]
        and validation_results["curp"].get("is_valid", True)
    )
    ine_valid = (
        "ine" in validation_results
        and validation_results["ine"].get("is_valid", False)
    )
    response["is_valid"] = curp_valid and ine_valid

    # Add validation details
    response["validation_details"] = {
        "curp": {
            "is_valid": curp_valid,
            "service_used": validation_results.get("curp", {}).get("service", "none"),
        },
        "ine": {
            "is_valid": ine_valid,
            "service_used": validation_results.get("ine", {}).get("service", "none"),
        },
    }

    # Add INE validation message if available
    if "ine" in validation_results and "data" in validation_results["ine"]:
        ine_data = validation_results["ine"]["data"]
        response["ine_validation_message"] = ine_data.get("mensaje", "")
        response["ine_validation_clave_mensaje"] = ine_data.get("claveMensaje", "")
        response["ine_validation_user_message"] = ine_data.get("mensajeUsuario", "")

    return response


def prepare_combined_response(
    ocr_data: Tuple[Dict[str, Any], Dict[str, Any]],
    validation_results: Dict[str, Any],
    timing_metrics: Dict[str, float],
) -> Dict[str, Any]:
    """Prepare the combined response with OCR and validation results."""
    front_info, back_info = ocr_data
    front_data = front_info.get("data", {}).get("parse_ocr", [])
    back_data = back_info.get("data", {}).get("mrz", {})

    body_validate_ine = prepare_validation_body(back_data)
    curp = front_data[8].get("value", "") if len(front_data) > 8 else ""

    response = {
        "front_info": front_info,
        "back_info": back_info,
        "body_validate_ine": body_validate_ine,
        "curp": curp,
        "timing_metrics": timing_metrics,
        "validation_results": validation_results,
    }

    # Add validation status
    curp_valid = (
        "curp" in validation_results and "error" not in validation_results["curp"]
    )
    ine_valid = (
        "ine" in validation_results
        and validation_results["ine"].get("is_valid", "error" not in validation_results["ine"])
    )
    response["is_valid"] = curp_valid and ine_valid

    # Add validation details
    response["validation_details"] = {
        "curp": {
            "is_valid": curp_valid,
            "service_used": validation_results.get("curp", {}).get("service", "none"),
        },
        "ine": {
            "is_valid": ine_valid,
            "service_used": validation_results.get("ine", {}).get("service", "none"),
        },
    }

    return response

