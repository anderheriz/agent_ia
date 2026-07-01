# -*- coding: utf-8 -*-
"""Configuración central del proyecto BI Reporter."""

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_DIR / "data" / "warehouse.csv"
OUTPUTS_DIR = PROJECT_DIR / "outputs"

EMAIL_DESTINO = os.getenv("EMAIL_DESTINO", "marketing@example.com")
EMAIL_REMITENTE = os.getenv("EMAIL_REMITENTE", "composio:gmail")
COMPOSIO_API_KEY_ENV = "COMPOSIO_API_KEY"
COMPOSIO_USER_ID_ENV = "COMPOSIO_USER_ID"
COMPOSIO_GMAIL_SEND_TOOL = "GMAIL_SEND_EMAIL"
FECHA_OBJETIVO_DEMO = "2026-06-29"

LLM_API_KEY_ENV = "GROQ_API_KEY"
LLM_BASE_URL = "https://api.groq.com/openai/v1"
LLM_MODELO = "llama-3.3-70b-versatile"
LLM_TEMPERATURE = 0.2

COLUMNAS_OBLIGATORIAS = [
    "fecha",
    "id_registro",
    "estado_reporte",
    "es_futuro_simulado",
    "id_cuenta_google",
    "nombre_cuenta_google",
    "alias",
    "codigo_pais",
    "pais",
    "producto",
    "id_campana",
    "nombre_campana",
    "canal_anuncio",
    "inversion",
    "conversiones",
    "cpa",
    "arpu_esperado_7d",
    "arpu_esperado_30d",
    "ltr_esperado_365d",
    "ingresos_ltr_esperados",
    "roas_ltr",
    "beneficio_esperado_ltr",
    "evento_sintetico",
]

COLUMNAS_NUMERICAS = [
    "presupuesto_diario",
    "impresiones",
    "clics",
    "ctr",
    "cpc_medio",
    "inversion",
    "conversiones",
    "tasa_conversion",
    "cpa",
    "arpu_esperado_7d",
    "arpu_esperado_30d",
    "ltr_esperado_365d",
    "ingresos_esperados_7d",
    "ingresos_esperados_30d",
    "ingresos_ltr_esperados",
    "roas_7d",
    "roas_30d",
    "roas_ltr",
    "beneficio_esperado_30d",
    "beneficio_esperado_ltr",
    "ratio_rentabilidad_ltr",
    "margen_beneficio_ltr",
    "puntuacion_calidad",
]

DIMENSIONES_ANALISIS = [
    "canal_anuncio",
    "alias",
    "codigo_pais",
    "id_cuenta_google",
]

KPIS_PRINCIPALES = [
    "inversion",
    "conversiones",
    "cpa",
    "arpu_esperado_7d",
    "arpu_esperado_30d",
    "ltr_esperado_365d",
    "roas_ltr",
    "beneficio_esperado_ltr",
]
