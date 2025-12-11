"""
Qualitas service for FastAPI
Migrated from Django apps/quote/services/qualitas_service.py
"""
import os
import requests
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds.transport import TransportError
from typing import Optional, Dict, Any, List
from app.config import get_env_var

logger = logging.getLogger(__name__)

# Singleton instance
_qualitas_service = None


def get_qualitas_service():
    """Get Qualitas service instance (singleton pattern)"""
    global _qualitas_service
    if _qualitas_service is None:
        _qualitas_service = QualitasService()
    return _qualitas_service


class QualitasMappings:
    """Mappings for Qualitas codes to human-readable names"""
    
    # Estados mapping
    ESTADOS = {
        "1": "Aguascalientes",
        "2": "Baja California Norte",
        "3": "Baja California Sur",
        "4": "Campeche",
        "5": "Coahuila",
        "6": "Colima",
        "7": "Chiapas",
        "8": "Chihuahua",
        "9": "Ciudad de México",
        "10": "Durango",
        "11": "Guanajuato",
        "12": "Guerrero",
        "13": "Hidalgo",
        "14": "Jalisco",
        "15": "Estado de México",
        "16": "Michoacán",
        "17": "Morelos",
        "18": "Nayarit",
        "19": "Nuevo Leon",
        "20": "Oaxaca",
        "21": "Puebla",
        "22": "Queretaro",
        "23": "Quintana Roo",
        "24": "San Luis Potosí",
        "25": "Sinaloa",
        "26": "Sonora",
        "27": "Tabasco",
        "28": "Tamaulipas",
        "29": "Tlaxcala",
        "30": "Veracruz",
        "31": "Yucatán",
        "32": "Zacatecas",
    }

    # Uso del vehículo mapping
    USO_VEHICULO = {"1": "Normal", "2": "Mensajeria", "5": "Personal"}

    # Servicio mapping
    SERVICIO = {
        "1": "Servicio Particular",
        "2": "Servicio Público",
        "3": "Servicio Público Federal",
    }

    # Forma de pago mapping
    FORMA_PAGO = {"C": "Contado"}

    # Tipo de suma asegurada mapping
    TIPO_SUMA = {
        "0": "Valor Convenido",
        "1": "Valor Factura",
        "3": "Valor Comercial"
    }

    # Coberturas mapping
    COBERTURAS = {
        "1": "DM - Daños Materiales",
        "2": "SPT - DM Sólo pérdida total",
        "3": "RT - Robo Total",
        "4": "RC - Responsabilidad Civil",
        "5": "GM - Gastos Médicos",
        "6": "MC - Muerte del Conductor X Accidente",
        "7": "GL - Gastos Legales",
        "8": "Equipo Especial",
        "9": "Adaptaciones Daños Materiales",
        "10": "Adaptaciones Robo Total",
        "11": "ERC - Extensión de RC",
        "12": "EDDM - Exención de Deducible Daños Materiales",
        "13": "RCPAS - RC Pasajero",
        "14": "AV - Asistencia Vial",
        "17": "GT/GxPUxPT - Gastos de Transporte/Gastos X Perdida de Uso X Pérdidas Totales",
        "22": "RCL - RC Legal Ocupantes",
        "26": "CADE - Cancelación de deducible por vuelco o colisión",
        "28": "GxPUxPP - Gastos X Perdida de Uso X Perdidas Parciales",
        "31": "Daños por la carga",
        "40": "EDRT - Exención de Deducible Robo Total",
    }
    
    # Paquetes mapping
    PAQUETES = {"1": "AMPLIA", "3": "LIMITADA", "4": "RESP. CIVIL"}

    @classmethod
    def get_estado(cls, codigo):
        return cls.ESTADOS.get(str(codigo), "Desconocido")

    @classmethod
    def get_uso_vehiculo(cls, codigo):
        return cls.USO_VEHICULO.get(str(codigo), "Desconocido")

    @classmethod
    def get_servicio(cls, codigo):
        return cls.SERVICIO.get(str(codigo), "Desconocido")

    @classmethod
    def get_forma_pago(cls, codigo):
        return cls.FORMA_PAGO.get(str(codigo), "Desconocido")

    @classmethod
    def get_tipo_suma(cls, codigo):
        return cls.TIPO_SUMA.get(str(codigo), "Desconocido")

    @classmethod
    def get_cobertura(cls, codigo):
        return cls.COBERTURAS.get(str(codigo), "Cobertura Desconocida")

    @classmethod
    def get_paquete(cls, codigo):
        return cls.PAQUETES.get(str(codigo), "Paquete Desconocido")


class QualitasConstants:
    """Constants for Qualitas service"""
    
    # Cobertura values
    COBERTURA_RC = {
        "NoCobertura": "4",
        "SumaAsegurada": "3000000",
        "TipoSuma": "0",
        "Deducible": "0",
    }

    COBERTURA_GM = {
        "NoCobertura": "5",
        "SumaAsegurada": "20000",
        "TipoSuma": "0",
        "Deducible": "0",
    }

    COBERTURA_GL = {
        "NoCobertura": "7",
        "SumaAsegurada": "0",
        "TipoSuma": "0",
        "Deducible": "0",
    }

    COBERTURA_AV = {
        "NoCobertura": "14",
        "SumaAsegurada": "0",
        "TipoSuma": "0",
        "Deducible": "0",
    }

    # Package definitions
    PAQUETE_AMPLIA = "1"
    PAQUETE_LIMITADA = "3"
    PAQUETE_RESP_CIVIL = "4"

    # Default values
    DEFAULT_USO = "1"
    DEFAULT_SERVICIO = "1"
    DEFAULT_AGENTE = "44457"
    DEFAULT_FORMAPAGO = "C"
    DEFAULT_TARIFA = "LINEA"
    DEFAULT_DERECHO = "600"


class QualitasService:
    """Qualitas SOAP service client"""

    def __init__(self):
        self.client = None
        self.tarifa_client = None
        self.mappings = QualitasMappings()
        self.constants = QualitasConstants()

        # Get URLs from environment variables
        try:
            self.base_url = get_env_var('QUALITAS_BASE_URL')
            self.tarifa_url = get_env_var('QUALITAS_TARIFA_URL')
        except ValueError:
            logger.error("Qualitas URLs not configured in environment variables")
            raise ValueError("QUALITAS_BASE_URL and QUALITAS_TARIFA_URL must be set")
        
        self.wsdl_url = f"{self.base_url}/WsEmision/WsEmision.asmx?WSDL"
        self.tarifa_wsdl_url = f"{self.tarifa_url}?WSDL"

    def _initialize_client(self):
        """Initialize the SOAP client with proper settings."""
        if self.client is not None:
            return

        if not self.base_url or not self.wsdl_url:
            logger.error("Qualitas service URL is not configured")
            raise Exception("Qualitas service URL is not configured")

        try:
            # First verify if WSDL is accessible
            response = requests.get(self.wsdl_url, timeout=30, verify=False)
            response.raise_for_status()

            # Create client with custom transport and options
            transport = HttpAuthenticated(timeout=30)
            self.client = Client(
                self.wsdl_url,
                transport=transport,
                cache=None,
                location=self.base_url,
                faults=True
            )

            # Set SOAP headers
            self.client.set_options(
                soapheaders={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': 'http://tempuri.org/obtenerNuevaEmision'
                }
            )

            # Set service location
            self.client.set_options(
                location=f"{self.base_url}/WsEmision/WsEmision.asmx"
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to access Qualitas WSDL: {str(e)}")
            raise Exception(f"Qualitas service is not accessible: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to initialize Qualitas SOAP client: {str(e)}")
            raise

    def _initialize_tarifa_client(self):
        """Initialize the SOAP client for tarifa service."""
        if self.tarifa_client is not None:
            return

        try:
            # First verify if WSDL is accessible
            response = requests.get(self.tarifa_wsdl_url, timeout=30, verify=False)
            response.raise_for_status()

            # Create client with custom transport and options
            transport = HttpAuthenticated(timeout=30)
            self.tarifa_client = Client(
                self.tarifa_wsdl_url,
                transport=transport,
                cache=None,
                location=self.tarifa_url,
                faults=True
            )

            # Set SOAP headers
            self.tarifa_client.set_options(
                soapheaders={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': 'http://tempuri.org/WSQBC/QBCDE/listaTarifas'
                }
            )

            # Set service location
            self.tarifa_client.set_options(location=self.tarifa_url)

            logger.info("Qualitas Tarifa SOAP client initialized successfully")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to access Qualitas Tarifa WSDL: {str(e)}")
            raise Exception(f"Qualitas Tarifa service is not accessible: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to initialize Qualitas Tarifa SOAP client: {str(e)}")
            raise

    def _validate_numeric_field(self, value, field_name):
        """Validate and convert numeric fields."""
        try:
            if value is None or value == "" or (isinstance(value, str) and value.strip() == ""):
                logger.debug(f"Empty value for {field_name}, returning 0")
                return 0
            return float(value)
        except ValueError as ve:
            logger.error(f"Invalid numeric value for {field_name}: {value}")
            return 0

    def _parse_movimientos(self, xml_string):
        """Parse the Movimientos XML and extract relevant information."""
        try:
            root = ET.fromstring(xml_string)
            movimientos = []

            for movimiento in root.findall(".//Movimiento"):
                mov_data = {
                    "TipoMovimiento": movimiento.get("TipoMovimiento"),
                    "NoNegocio": movimiento.get("NoNegocio"),
                    "NoPoliza": movimiento.get("NoPoliza"),
                    "NoCotizacion": movimiento.get("NoCotizacion"),
                    "NoEndoso": movimiento.get("NoEndoso"),
                    "TipoEndoso": movimiento.get("TipoEndoso"),
                    "NoOTra": movimiento.get("NoOTra"),
                }

                # Get DatosAsegurado
                asegurado = movimiento.find(".//DatosAsegurado")
                if asegurado is not None:
                    mov_data["DatosAsegurado"] = {
                        "NoAsegurado": asegurado.get("NoAsegurado"),
                        "Nombre": asegurado.findtext("Nombre"),
                        "Direccion": asegurado.findtext("Direccion"),
                        "Colonia": asegurado.findtext("Colonia"),
                        "Poblacion": asegurado.findtext("Poblacion"),
                        "Estado": asegurado.findtext("Estado"),
                        "CodigoPostal": asegurado.findtext("CodigoPostal"),
                    }

                # Get DatosVehiculo
                vehiculo = movimiento.find(".//DatosVehiculo")
                if vehiculo is not None:
                    mov_data["DatosVehiculo"] = {
                        "NoInciso": vehiculo.get("NoInciso"),
                        "ClaveAmis": vehiculo.findtext("ClaveAmis"),
                        "Modelo": vehiculo.findtext("Modelo"),
                        "DescripcionVehiculo": vehiculo.findtext("DescripcionVehiculo"),
                        "Uso": vehiculo.findtext("Uso"),
                        "Servicio": vehiculo.findtext("Servicio"),
                        "Paquete": vehiculo.findtext("Paquete"),
                        "Motor": vehiculo.findtext("Motor"),
                        "Serie": vehiculo.findtext("Serie"),
                    }

                    # Get Coberturas with numeric validation
                    coberturas = []
                    for cobertura in vehiculo.findall(".//Coberturas"):
                        coberturas.append({
                            "NoCobertura": cobertura.get("NoCobertura"),
                            "SumaAsegurada": self._validate_numeric_field(
                                cobertura.findtext("SumaAsegurada"),
                                "SumaAsegurada"
                            ),
                            "TipoSuma": cobertura.findtext("TipoSuma"),
                            "Deducible": self._validate_numeric_field(
                                cobertura.findtext("Deducible"), "Deducible"
                            ),
                            "Prima": self._validate_numeric_field(
                                cobertura.findtext("Prima"), "Prima"
                            ),
                        })
                    mov_data["DatosVehiculo"]["Coberturas"] = coberturas

                # Get DatosGenerales
                generales = movimiento.find(".//DatosGenerales")
                if generales is not None:
                    mov_data["DatosGenerales"] = {
                        "FechaEmision": generales.findtext("FechaEmision"),
                        "FechaInicio": generales.findtext("FechaInicio"),
                        "FechaTermino": generales.findtext("FechaTermino"),
                        "Moneda": generales.findtext("Moneda"),
                        "Agente": generales.findtext("Agente"),
                        "FormaPago": generales.findtext("FormaPago"),
                        "TarifaValores": generales.findtext("TarifaValores"),
                        "TarifaCuotas": generales.findtext("TarifaCuotas"),
                        "TarifaDerechos": generales.findtext("TarifaDerechos"),
                        "Plazo": generales.findtext("Plazo"),
                        "PorcentajeDescuento": self._validate_numeric_field(
                            generales.findtext("PorcentajeDescuento"),
                            "PorcentajeDescuento",
                        ),
                    }

                # Get Primas with numeric validation
                primas = movimiento.find(".//Primas")
                if primas is not None:
                    mov_data["Primas"] = {
                        "PrimaNeta": self._validate_numeric_field(
                            primas.findtext("PrimaNeta"), "PrimaNeta"
                        ),
                        "Derecho": self._validate_numeric_field(
                            primas.findtext("Derecho"), "Derecho"
                        ),
                        "Recargo": self._validate_numeric_field(
                            primas.findtext("Recargo"), "Recargo"
                        ),
                        "Impuesto": self._validate_numeric_field(
                            primas.findtext("Impuesto"), "Impuesto"
                        ),
                        "PrimaTotal": self._validate_numeric_field(
                            primas.findtext("PrimaTotal"), "PrimaTotal"
                        ),
                        "Comision": self._validate_numeric_field(
                            primas.findtext("Comision"), "Comision"
                        ),
                    }

                # Get Recibos with numeric validation
                recibos = []
                for recibo in movimiento.findall(".//Recibos"):
                    recibos.append({
                        "NoRecibo": recibo.get("NoRecibo"),
                        "FechaInicio": recibo.findtext("FechaInicio"),
                        "FechaTermino": recibo.findtext("FechaTermino"),
                        "PrimaNeta": self._validate_numeric_field(
                            recibo.findtext("PrimaNeta"), "PrimaNeta"
                        ),
                        "Derecho": self._validate_numeric_field(
                            recibo.findtext("Derecho"), "Derecho"
                        ),
                        "Recargo": self._validate_numeric_field(
                            recibo.findtext("Recargo"), "Recargo"
                        ),
                        "Impuesto": self._validate_numeric_field(
                            recibo.findtext("Impuesto"), "Impuesto"
                        ),
                        "PrimaTotal": self._validate_numeric_field(
                            recibo.findtext("PrimaTotal"), "PrimaTotal"
                        ),
                        "Comision": self._validate_numeric_field(
                            recibo.findtext("Comision"), "Comision"
                        ),
                    })
                mov_data["Recibos"] = recibos

                # Get CodigoError
                mov_data["CodigoError"] = movimiento.findtext("CodigoError")

                movimientos.append(mov_data)

            return movimientos
        except Exception as e:
            logger.error(f"Error parsing Movimientos XML: {str(e)}")
            return None

    def format_policy_for_display(self, parsed_data):
        """Format the parsed policy data for user-friendly display."""
        if (not parsed_data or not isinstance(parsed_data, list)
                or len(parsed_data) == 0):
            return "No policy data available"

        policy = parsed_data[0]  # Get the first policy
        formatted_data = {
            "Información General": {
                "Número de Cotización": policy.get("NoCotizacion", ""),
                "Número de Negocio": policy.get("NoNegocio", ""),
                "Número de Póliza": policy.get("NoPoliza", ""),
                "Número de Endoso": policy.get("NoEndoso", ""),
                "Número de OTra": policy.get("NoOTra", ""),
            },
            "Datos del Asegurado": {
                "Nombre": policy.get("DatosAsegurado", {}).get("Nombre", ""),
                "Dirección": policy.get("DatosAsegurado", {}).get("Direccion", ""),
                "Colonia": policy.get("DatosAsegurado", {}).get("Colonia", ""),
                "Población": policy.get("DatosAsegurado", {}).get("Poblacion", ""),
                "Estado": self.mappings.get_estado(
                    policy.get("DatosAsegurado", {}).get("Estado", "")
                ),
                "Código Postal": policy.get("DatosAsegurado", {}).get("CodigoPostal", ""),
            },
            "Datos del Vehículo": {
                "Clave AMIS": policy.get("DatosVehiculo", {}).get("ClaveAmis", ""),
                "Modelo": policy.get("DatosVehiculo", {}).get("Modelo", ""),
                "Descripción": policy.get("DatosVehiculo", {}).get("DescripcionVehiculo", ""),
                "Uso": self.mappings.get_uso_vehiculo(
                    policy.get("DatosVehiculo", {}).get("Uso", "")
                ),
                "Servicio": self.mappings.get_servicio(
                    policy.get("DatosVehiculo", {}).get("Servicio", "")
                ),
                "Paquete": self.mappings.get_paquete(
                    policy.get("DatosVehiculo", {}).get("Paquete", "")
                ),
            },
            "Coberturas": [],
        }

        # Add coberturas
        for cobertura in policy.get("DatosVehiculo", {}).get("Coberturas", []):
            formatted_data["Coberturas"].append({
                "Nombre": self.mappings.get_cobertura(cobertura.get("NoCobertura", "")),
                "Suma Asegurada": f"${float(cobertura.get('SumaAsegurada', 0)):,.2f}",
                "Deducible": cobertura.get("Deducible", ""),
                "Prima": f"${float(cobertura.get('Prima', 0)):,.2f}",
            })

        # Add dates and payment information
        formatted_data["Fechas"] = {
            "Emisión": policy.get("DatosGenerales", {}).get("FechaEmision", ""),
            "Inicio": policy.get("DatosGenerales", {}).get("FechaInicio", ""),
            "Término": policy.get("DatosGenerales", {}).get("FechaTermino", ""),
            "Forma de Pago": self.mappings.get_forma_pago(
                policy.get("DatosGenerales", {}).get("FormaPago", "")
            ),
        }

        # Add premium information
        formatted_data["Primas"] = {
            "Prima Neta": f"${float(policy.get('Primas', {}).get('PrimaNeta', 0)):,.2f}",
            "Derecho": f"${float(policy.get('Primas', {}).get('Derecho', 0)):,.2f}",
            "Recargo": f"${float(policy.get('Primas', {}).get('Recargo', 0)):,.2f}",
            "Impuesto": f"${float(policy.get('Primas', {}).get('Impuesto', 0)):,.2f}",
            "Prima Total": f"${float(policy.get('Primas', {}).get('PrimaTotal', 0)):,.2f}",
        }

        return formatted_data

    def obtener_nueva_emision(self, xml_data):
        """
        Call the obtenerNuevaEmision SOAP endpoint.
        """
        if self.client is None:
            self._initialize_client()

        try:
            # Parse the input XML to validate ClaveAmis
            try:
                root = ET.fromstring(xml_data)
                clave_amis = root.find(".//ClaveAmis")
                if clave_amis is not None:
                    if not clave_amis.text or not clave_amis.text.strip():
                        return {
                            "success": False,
                            "error": "ClaveAmis is required",
                            "details": "The ClaveAmis field cannot be empty",
                        }
            except ET.ParseError as e:
                logger.error(f"Error parsing input XML: {str(e)}")
                return {
                    "success": False,
                    "error": "Invalid XML format",
                    "details": str(e),
                }

            # Call the service with the XML data
            response = self.client.service.obtenerNuevaEmision(xmlEmision=xml_data)

            # Parse and format the response
            parsed_data = self._parse_movimientos(str(response))
            display_data = self.format_policy_for_display(parsed_data)

            return {"success": True, "data": display_data}
        except TransportError as te:
            logger.error(f"Transport error in obtenerNuevaEmision: {str(te)}")
            return {
                "success": False,
                "error": str(te),
                "details": "Network or transport error occurred"
            }
        except Exception as e:
            logger.error(f"Error in obtenerNuevaEmision: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "details": "Check the XML format and ensure all required fields are present",
            }

    def _parse_tarifa_results(self, response_data):
        """
        Parse and format the tarifa results from the response.
        """
        try:
            if not response_data or "salida" not in response_data:
                logger.warning("No salida in response data")
                return []

            salida = response_data["salida"]
            if not salida or "datos" not in salida:
                logger.warning("No datos in salida")
                return []

            datos = salida["datos"]
            if not datos:
                logger.warning("Empty datos")
                return []

            results = []

            # Check if datos is a list or a single item
            if isinstance(datos, list):
                items = datos
            else:
                items = [datos]

            for item in items:
                if hasattr(item, "Elemento"):
                    elemento = item.Elemento
                    result = {
                        "cTarifa": getattr(elemento, "cTarifa", ""),
                        "cMarca": getattr(elemento, "cMarca", ""),
                        "cTipo": getattr(elemento, "cTipo", ""),
                        "cVersion": getattr(elemento, "cVersion", ""),
                        "cModelo": getattr(elemento, "cModelo", ""),
                        "CAMIS": getattr(elemento, "CAMIS", ""),
                        "cCategoria": getattr(elemento, "cCategoria", ""),
                        "cTransmision": getattr(elemento, "cTransmision", ""),
                        "cOcupantes": getattr(elemento, "cOcupantes", ""),
                        "nV1": getattr(elemento, "nV1", ""),
                        "nV2": getattr(elemento, "nV2", ""),
                        "cNvaAMIS": getattr(elemento, "cNvaAMIS", ""),
                        "cMarcaLarga": getattr(elemento, "cMarcaLarga", "")
                    }
                    results.append(result)
                else:
                    logger.warning(f"Item without Elemento attribute: {item}")

            return results
        except Exception as e:
            logger.error(f"Error parsing tarifa results: {str(e)}")
            return []

    def get_listTarifas(self, xml_data):
        """
        Call method listaTarifas from Qualitas tarifa service
        """
        if self.tarifa_client is None:
            self._initialize_tarifa_client()

        try:
            # Call the service with the parameters
            response = self.tarifa_client.service.listaTarifas(
                cUsuario=xml_data.get("cUsuario", ""),
                cTarifa=xml_data.get("cTarifa", ""),
                cMarca=xml_data.get("cMarca", ""),
                cTipo=xml_data.get("cTipo", ""),
                cVersion=xml_data.get("cVersion", ""),
                cModelo=xml_data.get("cModelo", ""),
                cCAMIS=xml_data.get("cCAMIS", ""),
                cCategoria=xml_data.get("cCategoria", ""),
                cNvaAMIS=xml_data.get("cNvaAMIS", ""),
            )

            # Convert response to dictionary
            result = {
                "salida": {
                    "datos": (
                        response.salida.datos
                        if hasattr(response, "salida") and hasattr(response.salida, "datos")
                        else None
                    ),
                    "retorno": {
                        "codigo": (
                            response.salida.retorno.codigo
                            if hasattr(response, "salida") and hasattr(response.salida, "retorno")
                            else None
                        ),
                        "descripcion": (
                            response.salida.retorno.descripcion
                            if hasattr(response, "salida") and hasattr(response.salida, "retorno")
                            else None
                        )
                    }
                }
            }

            # Parse and format the results
            parsed_results = self._parse_tarifa_results(result)

            # If we have no results but the call was successful, return an empty list instead of null
            if parsed_results is None:
                parsed_results = []

            return {"success": True, "data": parsed_results}
        except Exception as e:
            logger.error(f"Error in listaTarifas: {str(e)}")
            return {"success": False, "error": str(e)}

    def _generate_xml_body(self,
                           clave_amis,
                           paquete,
                           vehicle_cost=None,
                           valor_regla_1=None,
                           model=None,
                           postal_code=None):
        """
        Generate XML body for Qualitas service request based on clave amis and paquete.
        """
        # Get current date and calculate end date (1 year from now)
        current_date = datetime.now()
        end_date = current_date + timedelta(days=365)

        # Format dates
        fecha_emision = current_date.strftime("%Y-%m-%d")
        fecha_inicio = current_date.strftime("%Y-%m-%d")
        fecha_termino = end_date.strftime("%Y-%m-%d")

        # Convert vehicle_cost to string with no decimal places
        vehicle_cost_str = str(int(vehicle_cost)) if vehicle_cost is not None else "48400"

        # Convert clave_amis to array and calculate valor_regla_1
        clave_amis_array = [int(digit) for digit in str(clave_amis)]

        def get_Valor_regla(clave_amis_array):
            # Sum par positions (even indices) and multiply by 3
            par_positions_sum = sum(clave_amis_array[::2])
            multiplied_sum = par_positions_sum * 3

            # Add sum of non-positions (odd indices)
            non_positions_sum = sum(clave_amis_array[1::2])
            total = multiplied_sum + non_positions_sum

            # Find what number needs to be added to make it a multiple of 10
            remainder = total % 10
            valor_regla_1 = (10 - remainder) if remainder != 0 else 0

            return valor_regla_1

        valor_regla_1 = get_Valor_regla(clave_amis_array)
        valor_regla_1_str = str(valor_regla_1)

        # Define coberturas based on paquete
        coberturas = {
            self.constants.PAQUETE_AMPLIA: [  # AMPLIA
                {
                    "NoCobertura": "1",
                    "SumaAsegurada": vehicle_cost_str,
                    "TipoSuma": "0",
                    "Deducible": "10",
                },
                {
                    "NoCobertura": "3",
                    "SumaAsegurada": vehicle_cost_str,
                    "TipoSuma": "0",
                    "Deducible": "20",
                },
                self.constants.COBERTURA_RC,
                self.constants.COBERTURA_GM,
                self.constants.COBERTURA_GL,
                self.constants.COBERTURA_AV,
            ],
            self.constants.PAQUETE_LIMITADA: [  # LIMITADA
                {
                    "NoCobertura": "3",
                    "SumaAsegurada": vehicle_cost_str,
                    "TipoSuma": "0",
                    "Deducible": "20",
                },
                self.constants.COBERTURA_RC,
                self.constants.COBERTURA_GM,
                self.constants.COBERTURA_GL,
                self.constants.COBERTURA_AV,
            ],
            self.constants.PAQUETE_RESP_CIVIL: [  # RESP. CIVIL
                self.constants.COBERTURA_RC,
                self.constants.COBERTURA_GM,
                self.constants.COBERTURA_GL,
                self.constants.COBERTURA_AV,
            ],
        }

        # Generate coberturas XML
        coberturas_xml = ""
        for cobertura in coberturas.get(paquete, []):
            coberturas_xml += f"""
<Coberturas NoCobertura="{cobertura['NoCobertura']}">
<SumaAsegurada>{cobertura['SumaAsegurada']}</SumaAsegurada>
<TipoSuma>{cobertura['TipoSuma']}</TipoSuma>
<Deducible>{cobertura['Deducible']}</Deducible>
<Prima>0</Prima>
</Coberturas>"""

        # Generate the complete XML
        xml_template = f"""<Movimientos>
<Movimiento TipoMovimiento="2" NoPoliza="" NoCotizacion="" NoEndoso="" TipoEndoso="" NoOTra="" NoNegocio="08112">
<DatosAsegurado NoAsegurado="">
<Nombre/>
<Direccion/>
<Colonia/>
<Poblacion/>
<Estado>15</Estado>
<CodigoPostal>{postal_code or '53100'}</CodigoPostal>
<NoEmpleado/>
<Agrupador/>
</DatosAsegurado>
<DatosVehiculo NoInciso="1">
<ClaveAmis>{clave_amis}</ClaveAmis>
<Modelo>{model}</Modelo>
<DescripcionVehiculo/>
<Uso>{self.constants.DEFAULT_USO}</Uso>
<Servicio>{self.constants.DEFAULT_SERVICIO}</Servicio>
<Paquete>{paquete}</Paquete>
<Motor/>
<Serie/>
{coberturas_xml}
</DatosVehiculo>
<DatosGenerales>
<FechaEmision>{fecha_emision}</FechaEmision>
<FechaInicio>{fecha_inicio}</FechaInicio>
<FechaTermino>{fecha_termino}</FechaTermino>
<Moneda>0</Moneda>
<Agente>{self.constants.DEFAULT_AGENTE}</Agente>
<FormaPago>{self.constants.DEFAULT_FORMAPAGO}</FormaPago>
<TarifaValores>{self.constants.DEFAULT_TARIFA}</TarifaValores>
<TarifaCuotas>{self.constants.DEFAULT_TARIFA}</TarifaCuotas>
<TarifaDerechos>{self.constants.DEFAULT_TARIFA}</TarifaDerechos>
<Plazo/>
<Agencia/>
<Contrato/>
<PorcentajeDescuento>0</PorcentajeDescuento>
<ConsideracionesAdicionalesDG NoConsideracion="1">
<TipoRegla>0</TipoRegla>
<ValorRegla>{valor_regla_1_str}</ValorRegla>
</ConsideracionesAdicionalesDG>
<ConsideracionesAdicionalesDG NoConsideracion="4">
<TipoRegla>0</TipoRegla>
<ValorRegla>1</ValorRegla>
</ConsideracionesAdicionalesDG>
<ConsideracionesAdicionalesDG NoConsideracion="5">
<TipoRegla>0</TipoRegla>
<ValorRegla>14</ValorRegla>
</ConsideracionesAdicionalesDG>
</DatosGenerales>
<Primas>
<PrimaNeta/>
<Derecho>{self.constants.DEFAULT_DERECHO}</Derecho>
<Recargo/>
<Impuesto/>
<PrimaTotal/>
<Comision/>
</Primas>
<CodigoError/>
</Movimiento>
</Movimientos>"""

        return xml_template

    def get_quote(self,
                  clave_amis,
                  paquete,
                  vehicle_cost=None,
                  valor_regla_1=None,
                  model=None,
                  postal_code=None):
        """
        Get a quote from Qualitas service.
        """
        try:
            # Try different vehicle costs if the original fails
            vehicle_costs_to_try = []
            if vehicle_cost is not None:
                vehicle_costs_to_try = [
                    vehicle_cost,                    # Try original first (100%)
                    int(vehicle_cost * 0.95),        # Try 95%
                    int(vehicle_cost * 0.90),        # Try 90%
                    int(vehicle_cost * 0.80),        # Try 80%
                    int(vehicle_cost * 0.70),        # Try 70%
                    int(vehicle_cost * 0.60),        # Try 60%
                    int(vehicle_cost * 0.50),        # Try 50%
                ]
            else:
                vehicle_costs_to_try = [48400]
            
            for try_cost in vehicle_costs_to_try:
                # Generate XML body with this vehicle cost
                xml_data = self._generate_xml_body(
                    clave_amis, paquete, try_cost, valor_regla_1, model, postal_code
                )

                # Call obtenerNuevaEmision with the generated XML
                response = self.obtener_nueva_emision(xml_data)

                if not response.get("success"):
                    continue

                # Get the data from the response
                data = response.get("data", {})

                # Check if we got a valid prima total
                prima_total = data.get("Primas", {}).get("Prima Total", "0")
                prima_total = prima_total.replace("$", "").replace(",", "")

                # If we got a valid prima total (not 0), use this result
                if float(prima_total) > 0:
                    # Extract coverage names
                    coberturas = data.get("Coberturas", [])
                    coverage_names = [
                        cobertura.get("Nombre", "") for cobertura in coberturas
                        if isinstance(cobertura, dict)
                    ]

                    # Return cleaned response
                    result = {
                        "success": True,
                        "data": {
                            "prima_total": float(prima_total),
                            "coverage_names": coverage_names,
                        },
                    }
                    
                    return result
            
            # If we get here, none of the vehicle costs worked
            return {
                "success": True,
                "data": {
                    "prima_total": 0.0,
                    "coverage_names": [],
                },
            }

        except Exception as e:
            logger.error(f"Error getting quote: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "details": "Error generating quote",
            }

