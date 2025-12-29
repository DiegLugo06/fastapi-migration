"""
CURP Response Transformers
Transform responses from different CURP validation services to a standardized format
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def transform_nubarium_curp_response(
    nubarium_response: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Transforms the response from Nubarium CURP validation service to match the required structure.

    Args:
        nubarium_response: The raw response from Nubarium CURP validation service

    Returns:
        A dictionary with the standardized structure for CURP validation responses

    Raises:
        KeyError: If required fields are missing in the input
        ValueError: If date formatting fails
    """
    try:
        # Transform date format from DD/MM/YYYY to YYYY-MM-DD
        try:
            birth_date = nubarium_response.get("fechaNacimiento")
            if not birth_date:
                raise KeyError("fechaNacimiento is missing in nubarium response")
            
            if "/" in birth_date:
                # Handle DD/MM/YYYY format
                day, month, year = birth_date.split("/")
                formatted_date = f"{year}-{month}-{day}"
            else:
                # Already in YYYY-MM-DD format
                formatted_date = birth_date
                
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to format birth date: {str(e)}")
            logger.error(f"Birth date value: {birth_date}")
            raise ValueError(f"Invalid date format in nubarium response: {str(e)}") from e

        # Map sex values
        sex_mapping = {
            "H": "HOMBRE",
            "M": "MUJER",
            "HOMBRE": "HOMBRE",
            "MUJER": "MUJER"
        }

        # Get datosDocProbatorio from nubarium response
        datos_doc_probatorio = nubarium_response.get("datosDocProbatorio", {})

        # Build the transformed response
        transformed = {
            "claveEntidad": datos_doc_probatorio.get("claveEntidadRegistro"),
            "curp": nubarium_response.get("curp"),
            "datosDocProbatorio": {
                "anioReg": datos_doc_probatorio.get("anioReg"),
                "claveEntidadRegistro": datos_doc_probatorio.get("claveEntidadRegistro"),
                "claveMunicipioRegistro": datos_doc_probatorio.get("claveMunicipioRegistro"),
                "entidadRegistro": datos_doc_probatorio.get("entidadRegistro"),
                "municipioRegistro": datos_doc_probatorio.get("municipioRegistro"),
                "numActa": datos_doc_probatorio.get("numActa"),
            },
            "docProbatorio": int(nubarium_response.get("docProbatorio", "1")),
            "docProbatorioDescripcion": "ACTA DE NACIMIENTO",
            "entidad": nubarium_response.get("estadoNacimiento"),
            "fechaNacimiento": formatted_date,
            "nacionalidad": nubarium_response.get("paisNacimiento", "MEXICO"),
            "nombres": nubarium_response.get("nombre"),
            "primerApellido": nubarium_response.get("apellidoPaterno"),
            "segundoApellido": nubarium_response.get("apellidoMaterno"),
            "sexo": sex_mapping.get(nubarium_response.get("sexo"), nubarium_response.get("sexo")),
            "status": "FOUND" if nubarium_response.get("estatus") == "OK" else "NOT_FOUND",
            "statusCurp": nubarium_response.get("estatusCurp"),
            "statusCurpDescripcion": nubarium_response.get("estatusCurp"),
            "rfc": nubarium_response.get("rfcGenerado", ""),
        }

        logger.info("Successfully transformed nubarium CURP response")
        return transformed

    except Exception as e:
        logger.error(
            f"Failed to transform nubarium CURP response: {str(e)}"
        )
        raise


def transform_first_service_response(
    first_response: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Transforms the response from the first CURP validation service (ValidaCurp) to match the required structure.

    Args:
        first_response: The raw response from ValidaCurp service

    Returns:
        A dictionary with the standardized structure for CURP validation responses

    Raises:
        KeyError: If required fields are missing in the input
        ValueError: If date formatting fails
    """
    try:
        # Transform date format from DD/MM/YYYY to YYYY-MM-DD
        try:
            # Access FechaNacimiento from the correct path in the response
            birth_date = first_response.get("response", {}).get("Solicitante", {}).get("FechaNacimiento")
            if not birth_date:
                raise KeyError("FechaNacimiento is missing in response")
                
            if "/" in birth_date:
                # Handle DD/MM/YYYY format
                day, month, year = birth_date.split("/")
                formatted_date = f"{year}-{month}-{day}"
            else:
                # Already in YYYY-MM-DD format
                formatted_date = birth_date
                
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to format birth date: {str(e)}")
            logger.error(f"Birth date value: {birth_date}")
            raise ValueError(f"Invalid date format in response: {str(e)}") from e

        # Map sex values
        sex_mapping = {
            "H": "HOMBRE",
            "M": "MUJER"
        }

        # Get the correct data from response structure
        solicitante = first_response.get("response", {}).get("Solicitante", {})
        doc_probatorio = first_response.get("response", {}).get("DocProbatorio", {})

        # Build the transformed response
        transformed = {
            "claveEntidad": solicitante.get("ClaveEntidadNacimiento"),
            "curp": solicitante.get("CURP"),
            "datosDocProbatorio": {
                "anioReg": doc_probatorio.get("AnioRegistro"),
                "claveEntidadRegistro": doc_probatorio.get("ClaveEntidadEmisora"),
                "claveMunicipioRegistro": doc_probatorio.get("ClaveMunicipioRegistro"),
                "entidadRegistro": doc_probatorio.get("EntidadRegistrante"),
                "municipioRegistro": doc_probatorio.get("MunicipioRegistro"),
                "numActa": doc_probatorio.get("NumActa"),
            },
            "docProbatorio": int(solicitante.get("ClaveDocProbatorio", "1")),
            "docProbatorioDescripcion": solicitante.get("DocProbatorio", "ACTA DE NACIMIENTO"),
            "entidad": solicitante.get("EntidadNacimiento"),
            "fechaNacimiento": formatted_date,
            "nacionalidad": "MEXICO" if solicitante.get("Nacionalidad") == "MEX" else solicitante.get("Nacionalidad"),
            "nombres": solicitante.get("Nombres"),
            "primerApellido": solicitante.get("ApellidoPaterno"),
            "segundoApellido": solicitante.get("ApellidoMaterno"),
            "sexo": sex_mapping.get(solicitante.get("ClaveSexo"), solicitante.get("Sexo")),
            "status": "FOUND",
            "statusCurp": solicitante.get("ClaveStatusCurp"),
            "statusCurpDescripcion": solicitante.get("StatusCurp"),
        }

        logger.info("Successfully transformed first service response")
        return transformed

    except Exception as e:
        logger.error(
            f"Failed to transform first service response: {str(e)}"
        )
        raise


def transform_second_service_response(
    second_response: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Transforms the response from the second CURP validation service (Verificamex) to match the structure
    of the primary service's response.

    Args:
        second_response: The raw response from Verificamex service

    Returns:
        A dictionary with the same structure as the primary service's response

    Raises:
        KeyError: If required fields are missing in the input
        ValueError: If date formatting fails
    """
    try:
        # Extract the first citizen record (assuming at least one exists)
        if not second_response.get("data", {}).get("citizen", {}).get("registros"):
            raise KeyError(f"No citizen records found in response: {second_response}")

        citizen = second_response["data"]["citizen"]["registros"][0]

        # Transform date format from DD/MM/YYYY to YYYY-MM-DD
        try:
            birth_date = citizen["fechaNacimiento"]
            day, month, year = birth_date.split("/")
            formatted_date = f"{year}-{month}-{day}"
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to format birth date: {str(e)}")
            raise ValueError("Invalid date format in response") from e

        # Build the transformed response
        transformed = {
            "claveEntidad": citizen.get("claveEntidad"),
            "curp": citizen.get("curp"),
            "datosDocProbatorio": {
                "anioReg": citizen.get("datosDocProbatorio", {}).get("anioReg"),
                "claveEntidadRegistro": citizen.get("datosDocProbatorio", {}).get(
                    "claveEntidadRegistro"
                ),
                "claveMunicipioRegistro": citizen.get("datosDocProbatorio", {}).get(
                    "claveMunicipioRegistro"
                ),
                "entidadRegistro": citizen.get("datosDocProbatorio", {}).get(
                    "entidadRegistro"
                ),
                "municipioRegistro": citizen.get("datosDocProbatorio", {}).get(
                    "municipioRegistro"
                ),
                "numActa": citizen.get("datosDocProbatorio", {}).get("numActa"),
            },
            "docProbatorio": str(
                citizen.get("docProbatorio", "")
            ),  # Convert to string to match primary service
            "docProbatorioDescripcion": "ACTA DE NACIMIENTO",  # Assuming constant value
            "entidad": citizen.get("entidad"),
            "fechaNacimiento": formatted_date,
            "nacionalidad": citizen.get("nacionalidad"),
            "nombres": citizen.get("nombres"),
            "primerApellido": citizen.get("primerApellido"),
            "segundoApellido": citizen.get("segundoApellido"),
            "sexo": citizen.get("sexo"),
            "status": "FOUND",  # Assuming success since we got a response
            "statusCurp": citizen.get("statusCurp"),
            "statusCurpDescripcion": "REGISTRO DE CAMBIO NO AFECTANDO A CURP",  # Assuming constant
        }

        logger.info("Successfully transformed second service response")
        return transformed

    except Exception as e:
        logger.error(
            f"Failed to transform second service response: {str(e)}"
        )
        raise


def get_curp_validation_message_mapping(codigo_mensaje: str, mensaje: str = "") -> str:
    """
    Get the user-friendly message based on the CURP validation codigoMensaje.
    
    Args:
        codigo_mensaje (str): The validation code from CURP service
        mensaje (str): Original error message from service
        
    Returns:
        str: User-friendly message
    """
    message_mapping = {
        "1": "El CURP proporcionado no es válido. Por favor, verifica que esté correctamente escrito.",
        "2": "El CURP tiene un formato inválido. Debe tener exactamente 18 caracteres alfanuméricos.",
        "3": "El CURP proporcionado no es válido. Por favor, verifica que esté correctamente escrito.",
        "5": "Error en los datos del CURP. Por favor, verifica la información proporcionada.",
        "-1": "El servicio de validación de CURP está temporalmente sobrecargado. Por favor, intenta nuevamente en unos minutos.",
    }
    
    # Try to get mapped message first
    user_message = message_mapping.get(codigo_mensaje)
    
    # If no mapped message, use the original message or a generic one
    if not user_message:
        if mensaje:
            user_message = f"Error en la validación: {mensaje}"
        else:
            user_message = "Error de validación desconocido. Por favor, contacta al soporte."
    
    return user_message

