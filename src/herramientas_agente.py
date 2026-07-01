# -*- coding: utf-8 -*-
"""Herramientas disponibles para el agente BI Reporter."""

from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

from .analisis_kpis import analizar_kpis_y_anomalias
from .carga_datos import cargar_csv_kpis
from .config import EMAIL_DESTINO, FECHA_OBJETIVO_DEMO
from .reporte import generar_reporte_texto, _formatear_kpi, _kpi_label, _estado_label


def _redondear_valor(valor: Any) -> Any:
    if isinstance(valor, pd.Timestamp):
        return valor.date().isoformat()
    if pd.isna(valor) if not isinstance(valor, (list, dict, tuple)) else False:
        return None
    if isinstance(valor, float):
        return round(valor, 4)
    return valor


def _normalizar_argumento(argumento: str | dict | None) -> dict:
    if argumento is None:
        return {}
    if isinstance(argumento, dict):
        return argumento

    texto = str(argumento).strip()
    if not texto:
        return {}

    try:
        data = json.loads(texto)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
        return {"fecha": texto}
    return {"texto": texto}


def _df_to_records(df: pd.DataFrame, columnas: list[str], n: int = 10) -> list[dict]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []

    columnas_existentes = [col for col in columnas if col in df.columns]
    records = df[columnas_existentes].head(n).to_dict(orient="records")
    return [
        {clave: _redondear_valor(valor) for clave, valor in row.items()}
        for row in records
    ]


def _serie_to_dict(serie: pd.Series | dict) -> dict:
    data = serie.to_dict() if isinstance(serie, pd.Series) else dict(serie)
    return {clave: _redondear_valor(valor) for clave, valor in data.items()}


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _comparacion_formateada(df: pd.DataFrame) -> list[dict]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []

    filas = []
    for _, row in df.iterrows():
        kpi = row["kpi"]
        filas.append(
            {
                "kpi": _kpi_label(kpi),
                "ayer": _formatear_kpi(kpi, row.get("valor_fecha_objetivo")),
                "antes_de_ayer": _formatear_kpi(kpi, row.get("valor_dia_anterior")),
                "media_7_dias": _formatear_kpi(kpi, row.get("media_7d")),
                "media_30_dias": _formatear_kpi(kpi, row.get("media_30d")),
                "variacion_vs_1d": row.get("variacion_vs_1d_pct_fmt"),
                "variacion_vs_7d": row.get("variacion_vs_7d_pct_fmt"),
                "estado": _estado_label(row.get("estado")),
            }
        )
    return filas


class HerramientasBI:
    """Agrupa las herramientas que el LLM puede pedir durante el bucle agente."""

    def __init__(self, destinatario: str = EMAIL_DESTINO):
        self.destinatario = destinatario
        self.df_kpis: pd.DataFrame | None = None
        self.resumen_csv: dict | None = None
        self.resultados: dict | None = None
        self.fecha_actual: str | None = None

    def _asegurar_analisis(self, fecha: str) -> dict:
        if self.resultados is not None and self.fecha_actual == fecha:
            return self.resultados

        self.df_kpis, self.resumen_csv = cargar_csv_kpis()
        self.resultados = analizar_kpis_y_anomalias(
            self.df_kpis,
            fecha_objetivo=fecha,
            ventana_historica_dias=14,
            umbral_variacion=0.20,
        )
        self.fecha_actual = fecha
        return self.resultados

    def _fecha_desde_argumento(self, argumento: str | dict | None) -> str:
        data = _normalizar_argumento(argumento)
        return data.get("fecha") or self.fecha_actual or FECHA_OBJETIVO_DEMO

    def analizar_dia_bi(self, argumento: str | dict | None = None) -> str:
        """Devuelve resumen global calculado para una fecha."""
        fecha = self._fecha_desde_argumento(argumento)
        resultados = self._asegurar_analisis(fecha)

        comparacion = _df_to_records(
            resultados["comparacion_global"],
            [
                "kpi",
                "valor_fecha_objetivo",
                "valor_dia_anterior",
                "media_7d",
                "media_30d",
                "variacion_vs_1d_pct_fmt",
                "variacion_vs_7d_pct_fmt",
                "estado",
            ],
            n=20,
        )
        comparacion_formateada = _comparacion_formateada(resultados["comparacion_global"])

        return _json(
            {
                "tipo": "resumen_global_bi",
                "fecha_objetivo": resultados["fecha_objetivo"],
                "ventanas_comparacion": resultados.get("ventanas_comparacion"),
                "ventana_historica": resultados["ventana_historica"],
                "calidad_csv": self.resumen_csv,
                "kpis_objetivo": _serie_to_dict(resultados["kpis_objetivo"]),
                "comparacion_global": comparacion,
                "comparacion_global_formateada": comparacion_formateada,
            }
        )

    def obtener_top_canales(self, argumento: str | dict | None = None) -> str:
        """Devuelve los canales con mayor Beneficio esperado (LTR)."""
        fecha = self._fecha_desde_argumento(argumento)
        resultados = self._asegurar_analisis(fecha)
        data = _normalizar_argumento(argumento)
        n = int(data.get("n", 5))

        return _json(
            {
                "tipo": "top_canales",
                "fecha_objetivo": resultados["fecha_objetivo"],
                "canales": _df_to_records(
                    resultados["top_canales"],
                    [
                        "canal_anuncio",
                        "inversion",
                        "ingresos_ltr_esperados",
                        "conversiones",
                        "ltr_esperado_365d",
                        "net_ltr",
                        "cpa",
                        "roas_ltr",
                        "beneficio_esperado_ltr",
                        "var_roas_ltr_pct",
                        "var_cpa_pct",
                    ],
                    n=n,
                ),
            }
        )

    def obtener_top_aliases(self, argumento: str | dict | None = None) -> str:
        """Devuelve los mejores aliases por Beneficio esperado (LTR)."""
        fecha = self._fecha_desde_argumento(argumento)
        resultados = self._asegurar_analisis(fecha)
        data = _normalizar_argumento(argumento)
        n = int(data.get("n", 5))

        return _json(
            {
                "tipo": "top_aliases",
                "fecha_objetivo": resultados["fecha_objetivo"],
                "aliases": _df_to_records(
                    resultados["top_aliases"],
                    [
                        "alias",
                        "canal_anuncio",
                        "inversion",
                        "conversiones",
                        "ltr_esperado_365d",
                        "cpa",
                        "net_ltr",
                        "beneficio_esperado_ltr",
                        "ltr_esperado_365d_media_7d",
                        "cpa_media_7d",
                        "net_ltr_media_7d",
                        "beneficio_esperado_ltr_media_7d",
                        "var_ltr_esperado_365d_vs_media_7d_pct",
                        "var_cpa_vs_media_7d_pct",
                        "var_beneficio_esperado_ltr_vs_media_7d_pct",
                    ],
                    n=n,
                ),
            }
        )

    def obtener_anomalias(self, argumento: str | dict | None = None) -> str:
        """Devuelve segmentos anomalos o a revisar."""
        fecha = self._fecha_desde_argumento(argumento)
        resultados = self._asegurar_analisis(fecha)
        data = _normalizar_argumento(argumento)
        n = int(data.get("n", 8))

        return _json(
            {
                "tipo": "anomalias_dimensiones",
                "fecha_objetivo": resultados["fecha_objetivo"],
                "anomalias": _df_to_records(
                    resultados["anomalias_dimensiones"],
                    [
                        "dimension",
                        "valor_dimension",
                        "motivo_anomalia",
                        "inversion",
                        "conversiones",
                        "cpa",
                        "roas_ltr",
                        "beneficio_esperado_ltr",
                        "impacto_beneficio_ltr",
                    ],
                    n=n,
                ),
            }
        )

    def obtener_reporte_base(self, argumento: str | dict | None = None) -> str:
        """Devuelve un reporte base determinista para que el LLM lo pueda mejorar."""
        fecha = self._fecha_desde_argumento(argumento)
        resultados = self._asegurar_analisis(fecha)
        reporte = generar_reporte_texto(resultados, destinatario=self.destinatario)
        return _json(
            {
                "tipo": "reporte_base_markdown",
                "fecha_objetivo": resultados["fecha_objetivo"],
                "markdown": reporte,
            }
        )

    def mapa_herramientas(self) -> dict:
        return {
            "analizar_dia_bi": self.analizar_dia_bi,
            "obtener_top_canales": self.obtener_top_canales,
            "obtener_top_aliases": self.obtener_top_aliases,
            "obtener_anomalias": self.obtener_anomalias,
            "obtener_reporte_base": self.obtener_reporte_base,
        }
