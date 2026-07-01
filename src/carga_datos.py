# -*- coding: utf-8 -*-
"""Carga y validación del CSV que simula el warehouse."""

from pathlib import Path

import pandas as pd

from .config import COLUMNAS_NUMERICAS, COLUMNAS_OBLIGATORIAS, DATA_PATH


def cargar_csv_kpis(
    path: Path = DATA_PATH,
    columnas_obligatorias: list[str] = COLUMNAS_OBLIGATORIAS,
    columnas_numericas: list[str] = COLUMNAS_NUMERICAS,
) -> tuple[pd.DataFrame, dict]:
    """Carga y valida el CSV que simula el warehouse de BI Reporter."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"No se ha encontrado el CSV: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("El CSV existe, pero está vacío.")

    columnas_faltantes = [col for col in columnas_obligatorias if col not in df.columns]
    if columnas_faltantes:
        raise ValueError(f"Faltan columnas obligatorias: {columnas_faltantes}")

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    fechas_invalidas = int(df["fecha"].isna().sum())
    if fechas_invalidas > 0:
        raise ValueError(f"Hay {fechas_invalidas} filas con fecha inválida.")

    if "es_futuro_simulado" in df.columns and df["es_futuro_simulado"].dtype != bool:
        df["es_futuro_simulado"] = (
            df["es_futuro_simulado"].astype(str).str.lower().isin(["true", "1", "yes", "si"])
        )

    columnas_numericas_presentes = [col for col in columnas_numericas if col in df.columns]
    for col in columnas_numericas_presentes:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    nulos_obligatorios = df[columnas_obligatorias].isna().sum()
    nulos_obligatorios = nulos_obligatorios[nulos_obligatorios > 0].to_dict()
    if nulos_obligatorios:
        raise ValueError(f"Hay nulos en columnas obligatorias: {nulos_obligatorios}")

    advertencias = []

    duplicados_id = int(df["id_registro"].duplicated().sum()) if "id_registro" in df.columns else 0
    if duplicados_id > 0:
        advertencias.append(f"Hay {duplicados_id} id_registro duplicados.")

    columnas_no_negativas = [
        "inversion",
        "conversiones",
        "cpa",
        "arpu_esperado_7d",
        "arpu_esperado_30d",
        "ltr_esperado_365d",
        "ingresos_ltr_esperados",
        "roas_ltr",
    ]
    negativos = {
        col: int((df[col] < 0).sum())
        for col in columnas_no_negativas
        if col in df.columns and int((df[col] < 0).sum()) > 0
    }
    if negativos:
        advertencias.append(f"Hay valores negativos inesperados: {negativos}")

    registros_por_dia = df.groupby("fecha").size()
    if registros_por_dia.nunique() > 1:
        advertencias.append("No todos los días tienen el mismo número de registros.")

    resumen = {
        "ruta_csv": str(path),
        "filas": int(df.shape[0]),
        "columnas": int(df.shape[1]),
        "fecha_min": df["fecha"].min().date().isoformat(),
        "fecha_max": df["fecha"].max().date().isoformat(),
        "dias_disponibles": int(df["fecha"].nunique()),
        "registros_por_dia_min": int(registros_por_dia.min()),
        "registros_por_dia_max": int(registros_por_dia.max()),
        "cuentas_google": int(df["id_cuenta_google"].nunique()),
        "aliases": int(df["alias"].nunique()),
        "paises": int(df["codigo_pais"].nunique()),
        "canales_anuncio": sorted(df["canal_anuncio"].dropna().unique().tolist()),
        "advertencias": advertencias,
    }

    df = df.sort_values(["fecha", "id_cuenta_google", "alias"]).reset_index(drop=True)
    df.attrs["resumen_validacion"] = resumen
    return df, resumen
