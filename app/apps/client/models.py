"""
Client models
Migrated from Django apps/client/models.py
"""
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional
from datetime import datetime, date
from app.common.fields import handle_postgresql_json


class Cliente(SQLModel, table=True):
    """
    Client model - migrated from Flask/Django
    Table: clientes
    """
    __tablename__ = "clientes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Name fields
    name: str = Field(max_length=50)
    second_name: Optional[str] = Field(default=None, max_length=50)
    first_last_name: Optional[str] = Field(default=None, max_length=50)
    second_last_name: Optional[str] = Field(default=None, max_length=50)
    
    # Contact Information
    phone: str = Field(max_length=15, unique=True, index=True)
    email: str = Field(max_length=100, unique=True, index=True)
    carrier: Optional[str] = Field(default=None, max_length=100)
    
    # Birth Information
    born_state: Optional[str] = Field(default=None, max_length=50)
    birth_date: Optional[date] = Field(default=None)
    
    # Personal Information
    economic_dependants: Optional[int] = Field(default=None)
    sex: Optional[str] = Field(default=None, max_length=1)
    rfc: Optional[str] = Field(default=None, max_length=13, index=True)
    curp: Optional[str] = Field(default=None, max_length=18, index=True)
    
    # Address Information
    street_address: Optional[str] = Field(default=None, max_length=100)
    zip_code: Optional[str] = Field(default=None, max_length=10)
    suburb_colonia: Optional[str] = Field(default=None, max_length=50)
    ciudad: Optional[str] = Field(default=None, max_length=50)
    estado: Optional[str] = Field(default=None, max_length=50)
    time_living_there: Optional[str] = Field(default=None, max_length=50)
    interior_number: Optional[str] = Field(default=None, max_length=10)
    
    # Optional Information
    id_type: Optional[str] = Field(default=None, max_length=50)
    id_number: Optional[str] = Field(default=None, max_length=100)
    id_expiration_date: Optional[date] = Field(default=None)
    marital_status: Optional[str] = Field(default=None, max_length=30)
    level_studies: Optional[str] = Field(default=None, max_length=30)
    profesion: Optional[str] = Field(default=None, max_length=50)
    housing_status: Optional[str] = Field(default=None, max_length=20)
    
    # Metadata
    created_at: Optional[datetime] = Field(default_factory=datetime.now, index=True)
    crm_sync_id: Optional[str] = Field(default=None, max_length=255)


class FileStatus(SQLModel, table=True):
    """
    File status model for client documents
    Table: file_statuses
    """
    __tablename__ = "file_statuses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="clientes.id")
    
    # Status options: 'null', 'validating', 'validated'
    officialId_front: Optional[str] = Field(default="null", max_length=50)
    officialId_reverse: Optional[str] = Field(default="null", max_length=50)
    addressProof: Optional[str] = Field(default="null", max_length=50)


class IncomeProofDocument(SQLModel, table=True):
    """
    Income proof document model
    Table: income_proof_documents
    """
    __tablename__ = "income_proof_documents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="clientes.id")  # Note: Flask uses 'client_id'
    
    document_type: str = Field(max_length=50)  # estado_cuenta, nomina_semanal, etc.
    status: str = Field(default="null", max_length=50)  # null, validating, validated, rejected
    
    sequence_number: Optional[int] = Field(default=None)
    total_income: Optional[float] = Field(default=None)
    month: Optional[int] = Field(default=None)
    year: Optional[int] = Field(default=None)


class Report(SQLModel, table=True):
    """
    Report model - used by client validation
    Table: reports
    """
    __tablename__ = "reports"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    kiban_id: str = Field(max_length=255, unique=True, index=True)
    cliente_id: int = Field(foreign_key="clientes.id")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.now, index=True)
    finished_at: Optional[datetime] = Field(default=None)
    duration: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None, max_length=50)
    raw_query_report: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    finva_evaluation: Optional[dict] = Field(default=None, sa_column=Column(JSONB))


class ClientesUnknown(SQLModel, table=True):
    """
    Unknown clients model
    Table: clientes_unknown
    """
    __tablename__ = "clientes_unknown"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=15)
    motorcycle_id: Optional[int] = Field(default=None, foreign_key="motorcycles.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    flow_process: Optional[str] = Field(default=None, max_length=50)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)


class Cuentas(SQLModel, table=True):
    """
    Accounts model from credit bureau reports
    Table: cuentas
    """
    __tablename__ = "cuentas"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id", nullable=False)
    clave_observacion: Optional[str] = Field(default=None, max_length=100)
    clave_otorgante: Optional[str] = Field(default=None, max_length=50)
    clave_unidad_monetaria: Optional[str] = Field(default=None, max_length=3)
    credito_maximo: Optional[int] = Field(default=None)
    fecha_actualizacion: Optional[date] = Field(default=None)
    fecha_apertura_can: Optional[date] = Field(default=None)
    fecha_apertura_cuenta: Optional[date] = Field(default=None)
    fecha_cancelacion_can: Optional[date] = Field(default=None)
    fecha_cierre_cuenta: Optional[date] = Field(default=None)
    fecha_historica_morosidad_mas_grave: Optional[date] = Field(default=None)
    fecha_inicio_reestructura: Optional[date] = Field(default=None)
    fecha_mas_antigua_historico_can: Optional[date] = Field(default=None)
    fecha_mas_antigua_historico_pagos: Optional[date] = Field(default=None)
    fecha_mas_reciente_historico_can: Optional[date] = Field(default=None)
    fecha_mas_reciente_historico_pagos: Optional[date] = Field(default=None)
    fecha_reporte: Optional[date] = Field(default=None)
    fecha_ultima_compra: Optional[date] = Field(default=None)
    fecha_ultimo_pago: Optional[date] = Field(default=None)
    forma_pago_actual: Optional[str] = Field(default=None, max_length=20)
    frecuencia_pagos: Optional[str] = Field(default=None, max_length=1)
    garantia: Optional[str] = Field(default=None, max_length=100)
    historico_can: Optional[str] = Field(default=None, max_length=100)
    historico_pagos: Optional[str] = Field(default=None, max_length=100)
    identificador_can: Optional[str] = Field(default=None, max_length=50)
    identificador_de_credito: Optional[str] = Field(default=None, max_length=50)
    identificador_sociedad_informacion_crediticia: Optional[str] = Field(default=None, max_length=1)
    importe_saldo_morosidad_hist_mas_grave: Optional[int] = Field(default=None)
    indicador_tipo_responsabilidad: Optional[str] = Field(default=None, max_length=1)
    limite_credito: Optional[int] = Field(default=None)
    modo_reportar: Optional[str] = Field(default=None, max_length=1)
    monto_pagar: Optional[int] = Field(default=None)
    monto_ultimo_pago: Optional[int] = Field(default=None)
    mop_historico_morosidad_mas_grave: Optional[str] = Field(default=None, max_length=50)
    nombre_otorgante: Optional[str] = Field(default=None, max_length=100)
    numero_cuenta_actual: Optional[str] = Field(default=None, max_length=50)
    numero_pagos: Optional[int] = Field(default=None)
    numero_pagos_vencidos: Optional[int] = Field(default=None)
    numero_telefono_otorgante: Optional[str] = Field(default=None, max_length=15)
    registro_impugnado: Optional[str] = Field(default=None, max_length=2)
    saldo_actual: Optional[int] = Field(default=None)
    saldo_vencido: Optional[int] = Field(default=None)
    tipo_contrato: Optional[str] = Field(default=None, max_length=50)
    tipo_cuenta: Optional[str] = Field(default=None, max_length=1)
    total_pagos_calificados_mop2: Optional[int] = Field(default=None)
    total_pagos_calificados_mop3: Optional[int] = Field(default=None)
    total_pagos_calificados_mop4: Optional[int] = Field(default=None)
    total_pagos_calificados_mop5: Optional[int] = Field(default=None)
    total_pagos_reportados: Optional[int] = Field(default=None)
    ultima_fecha_saldo_cero: Optional[date] = Field(default=None)
    valor_activo_valuacion: Optional[str] = Field(default=None, max_length=100)


class Domicilios(SQLModel, table=True):
    """
    Addresses model from credit bureau reports
    Table: domicilios
    """
    __tablename__ = "domicilios"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id", nullable=False)
    cp: Optional[str] = Field(default=None, max_length=10)
    ciudad: Optional[str] = Field(default=None, max_length=100)
    colonia_poblacion: Optional[str] = Field(default=None, max_length=100)
    delegacion_municipio: Optional[str] = Field(default=None, max_length=100)
    direccion1: Optional[str] = Field(default=None, max_length=150)
    direccion2: Optional[str] = Field(default=None, max_length=150)
    estado: Optional[str] = Field(default=None, max_length=100)
    extension: Optional[str] = Field(default=None, max_length=10)
    fax: Optional[str] = Field(default=None, max_length=20)
    fecha_reporte_direccion: Optional[date] = Field(default=None)
    fecha_residencia: Optional[date] = Field(default=None)
    indicador_especial_domicilio: Optional[str] = Field(default=None, max_length=1)
    numero_telefono: Optional[str] = Field(default=None, max_length=15)
    origen_del_domicilio: Optional[str] = Field(default=None, max_length=50)
    tipo_domicilio: Optional[str] = Field(default=None, max_length=1)


class ResumenReporte(SQLModel, table=True):
    """
    Report summary model from credit bureau reports
    Table: resumen_reporte
    """
    __tablename__ = "resumen_reporte"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id", nullable=False)
    cuentas_cerradas: Optional[int] = Field(default=None)
    cuentas_claves_historia_negativa: Optional[int] = Field(default=None)
    cuentas_disputa: Optional[int] = Field(default=None)
    cuentas_negativas_actuales: Optional[int] = Field(default=None)
    cuentas_pagos_fijos_hipotecas: Optional[int] = Field(default=None)
    cuentas_revolventes_abiertas: Optional[int] = Field(default=None)
    existencia_declaraciones_consumidor: Optional[str] = Field(default=None, max_length=1)
    fecha_apertura_cuenta_mr_despacho_cobranza: Optional[date] = Field(default=None)
    fecha_apertura_cuenta_mas_antigua: Optional[date] = Field(default=None)
    fecha_apertura_cuenta_mas_reciente: Optional[date] = Field(default=None)
    fecha_ingreso_bd: Optional[date] = Field(default=None)
    fecha_solicitud_mas_reciente_despacho_cobranza: Optional[date] = Field(default=None)
    fecha_solicitud_reporte_mas_reciente: Optional[date] = Field(default=None)
    mensajes_alerta: Optional[str] = Field(default=None, max_length=250)
    nueva_direccion_reportada_ultimos_60_dias: Optional[str] = Field(default=None, max_length=1)
    numero_cuentas: Optional[int] = Field(default=None)
    numero_mop0: Optional[str] = Field(default=None, max_length=50)
    numero_mop1: Optional[str] = Field(default=None, max_length=50)
    numero_mop2: Optional[str] = Field(default=None, max_length=50)
    numero_mop3: Optional[str] = Field(default=None, max_length=50)
    numero_mop4: Optional[str] = Field(default=None, max_length=50)
    numero_mop5: Optional[str] = Field(default=None, max_length=50)
    numero_mop6: Optional[str] = Field(default=None, max_length=50)
    numero_mop7: Optional[str] = Field(default=None, max_length=50)
    numero_mop96: Optional[str] = Field(default=None, max_length=50)
    numero_mop97: Optional[str] = Field(default=None, max_length=50)
    numero_mop99: Optional[str] = Field(default=None, max_length=50)
    numero_mopur: Optional[str] = Field(default=None, max_length=50)
    numero_solicitudes_ultimos_6_meses: Optional[int] = Field(default=None)
    numero_total_cuentas_despacho_cobranza: Optional[int] = Field(default=None)
    numero_total_solicitudes_despachos_cobranza: Optional[int] = Field(default=None)
    pct_limite_credito_utilizado_revolventes: Optional[int] = Field(default=None)
    tipo_moneda: Optional[str] = Field(default=None, max_length=3)
    total_creditos_maximos_pagos_fijos: Optional[int] = Field(default=None)
    total_creditos_maximos_revolventes: Optional[int] = Field(default=None)
    total_limites_credito_revolventes: Optional[int] = Field(default=None)
    total_pagos_pagos_fijos: Optional[int] = Field(default=None)
    total_pagos_revolventes: Optional[int] = Field(default=None)
    total_saldos_actuales_pagos_fijos: Optional[int] = Field(default=None)
    total_saldos_actuales_revolventes: Optional[int] = Field(default=None)
    total_saldos_vencidos_pagos_fijos: Optional[int] = Field(default=None)
    total_saldos_vencidos_revolventes: Optional[int] = Field(default=None)
    total_solicitudes_reporte: Optional[int] = Field(default=None)


class ScoreBuroCredito(SQLModel, table=True):
    """
    Credit bureau score model
    Table: score_buro_credito
    """
    __tablename__ = "score_buro_credito"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id", nullable=False)
    codigo_razon1: Optional[str] = Field(default=None, max_length=50)
    codigo_razon2: Optional[str] = Field(default=None, max_length=50)
    codigo_razon3: Optional[str] = Field(default=None, max_length=50)
    codigo_score: Optional[str] = Field(default=None, max_length=50)
    nombre_score: Optional[str] = Field(default=None, max_length=100)
    valor_score: Optional[int] = Field(default=None)
    codigo_error: Optional[str] = Field(default=None, max_length=50)
