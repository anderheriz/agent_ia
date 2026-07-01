# -*- coding: utf-8 -*-
"""Analisis de KPIs y deteccion de anomalias."""

import pandas as pd

from .config import DIMENSIONES_ANALISIS


KPIS_GLOBALES = [
    "inversion",
    "conversiones",
    "cpa",
    "ltr_esperado_365d",
    "net_ltr",
    "beneficio_esperado_ltr",
    "tasa_conversion",
    "margen_beneficio_ltr",
]

KPIS_BASE_AGREGACION = [
    "inversion",
    "conversiones",
    "ingresos_ltr_esperados",
    "beneficio_esperado_ltr",
    "impresiones",
    "clics",
]


def _safe_div(numerador: float, denominador: float) -> float:
    if denominador is None or pd.isna(denominador) or denominador == 0:
        return 0.0
    return numerador / denominador


def _float_or_none(valor) -> float | None:
    if valor is None or pd.isna(valor):
        return None
    return float(valor)


def _variacion_pct(actual: float | None, referencia: float | None) -> float | None:
    if actual is None or referencia is None or pd.isna(referencia) or referencia == 0:
        return None
    return (actual - referencia) / referencia


def _formatear_pct(valor: float | None) -> str:
    if valor is None or pd.isna(valor):
        return "n/a"
    return f"{valor:.1%}"


def _serie_kpis_vacia() -> pd.Series:
    return pd.Series({kpi: None for kpi in KPIS_GLOBALES + KPIS_BASE_AGREGACION})


def _agregar_kpis(df: pd.DataFrame, group_cols: list[str] | None = None) -> pd.DataFrame:
    agg_dict = {
        "inversion": "sum",
        "conversiones": "sum",
        "ingresos_ltr_esperados": "sum",
        "beneficio_esperado_ltr": "sum",
        "impresiones": "sum",
        "clics": "sum",
    }

    if group_cols:
        out = df.groupby(group_cols, as_index=False).agg(**{k: (k, v) for k, v in agg_dict.items()})
    else:
        values = {k: getattr(df[k], v)() for k, v in agg_dict.items()}
        out = pd.DataFrame([values])

    out["cpa"] = out.apply(lambda row: _safe_div(row["inversion"], row["conversiones"]), axis=1)
    out["ltr_esperado_365d"] = out.apply(
        lambda row: _safe_div(row["ingresos_ltr_esperados"], row["conversiones"]),
        axis=1,
    )
    out["net_ltr"] = out.apply(
        lambda row: _safe_div(row["beneficio_esperado_ltr"], row["conversiones"]),
        axis=1,
    )
    out["roas_ltr"] = out.apply(lambda row: _safe_div(row["ingresos_ltr_esperados"], row["inversion"]), axis=1)
    out["margen_beneficio_ltr"] = out.apply(
        lambda row: _safe_div(row["beneficio_esperado_ltr"], row["ingresos_ltr_esperados"]),
        axis=1,
    )
    out["tasa_conversion"] = out.apply(lambda row: _safe_div(row["conversiones"], row["clics"]), axis=1)
    return out


def _media_diaria_kpis(df_hist: pd.DataFrame) -> pd.Series:
    if df_hist.empty:
        return _serie_kpis_vacia()

    diario = _agregar_kpis(df_hist, ["fecha"])
    medias = diario[KPIS_BASE_AGREGACION].mean(numeric_only=True)

    medias["cpa"] = _safe_div(medias["inversion"], medias["conversiones"])
    medias["ltr_esperado_365d"] = _safe_div(medias["ingresos_ltr_esperados"], medias["conversiones"])
    medias["net_ltr"] = _safe_div(medias["beneficio_esperado_ltr"], medias["conversiones"])
    medias["roas_ltr"] = _safe_div(medias["ingresos_ltr_esperados"], medias["inversion"])
    medias["margen_beneficio_ltr"] = _safe_div(
        medias["beneficio_esperado_ltr"], medias["ingresos_ltr_esperados"]
    )
    medias["tasa_conversion"] = _safe_div(medias["conversiones"], medias["clics"])
    return medias


def _kpis_dia(df_dia: pd.DataFrame) -> pd.Series:
    if df_dia.empty:
        return _serie_kpis_vacia()
    return _agregar_kpis(df_dia).iloc[0]


def _clasificar_kpi(kpi: str, variacion: float | None, umbral: float) -> str:
    if variacion is None or pd.isna(variacion):
        return "sin_referencia"
    if abs(variacion) < umbral:
        return "estable"

    subir_es_bueno = {
        "conversiones",
        "ltr_esperado_365d",
        "net_ltr",
        "beneficio_esperado_ltr",
        "roas_ltr",
        "margen_beneficio_ltr",
        "tasa_conversion",
    }
    subir_es_malo = {"cpa"}

    if kpi in subir_es_bueno:
        return "mejora" if variacion > 0 else "caida"
    if kpi in subir_es_malo:
        return "deterioro" if variacion > 0 else "mejora"
    if kpi == "inversion":
        return "subida_inversion" if variacion > 0 else "bajada_inversion"
    return "cambio_relevante"


def _comparar_kpis_globales(
    kpis_actuales: pd.Series,
    kpis_dia_anterior: pd.Series,
    kpis_media_7d: pd.Series,
    kpis_media_30d: pd.Series,
    umbral: float,
) -> pd.DataFrame:
    filas = []
    for kpi in KPIS_GLOBALES:
        actual = _float_or_none(kpis_actuales.get(kpi))
        dia_anterior = _float_or_none(kpis_dia_anterior.get(kpi))
        media_7d = _float_or_none(kpis_media_7d.get(kpi))
        media_30d = _float_or_none(kpis_media_30d.get(kpi))
        variacion_1d = _variacion_pct(actual, dia_anterior)
        variacion_7d = _variacion_pct(actual, media_7d)
        variacion_abs_7d = None if actual is None or media_7d is None else actual - media_7d

        filas.append(
            {
                "kpi": kpi,
                "valor_fecha_objetivo": actual,
                "valor_dia_anterior": dia_anterior,
                "media_7d": media_7d,
                "media_30d": media_30d,
                "media_diaria_historica": media_7d,
                "variacion_absoluta_vs_7d": variacion_abs_7d,
                "variacion_vs_1d_pct": variacion_1d,
                "variacion_vs_1d_pct_fmt": _formatear_pct(variacion_1d),
                "variacion_vs_7d_pct": variacion_7d,
                "variacion_vs_7d_pct_fmt": _formatear_pct(variacion_7d),
                "variacion_pct": variacion_7d,
                "variacion_pct_fmt": _formatear_pct(variacion_7d),
                "estado": _clasificar_kpi(kpi, variacion_7d, umbral),
            }
        )
    return pd.DataFrame(filas)


def _ventana_resumen(df_ventana: pd.DataFrame) -> dict:
    if df_ventana.empty:
        return {"fecha_inicio": None, "fecha_fin": None, "dias": 0}
    return {
        "fecha_inicio": df_ventana["fecha"].min().date().isoformat(),
        "fecha_fin": df_ventana["fecha"].max().date().isoformat(),
        "dias": int(df_ventana["fecha"].nunique()),
    }


def _analizar_dimension(
    df_objetivo: pd.DataFrame,
    df_historico: pd.DataFrame,
    dimension: str,
    umbral_variacion: float,
    min_inversion: float,
) -> pd.DataFrame:
    actual = _agregar_kpis(df_objetivo, [dimension])

    historico_diario = _agregar_kpis(df_historico, [dimension, "fecha"])
    historico = (
        historico_diario
        .groupby(dimension, as_index=False)
        .agg(
            inversion_hist=("inversion", "mean"),
            conversiones_hist=("conversiones", "mean"),
            ingresos_ltr_esperados_hist=("ingresos_ltr_esperados", "mean"),
            beneficio_esperado_ltr_hist=("beneficio_esperado_ltr", "mean"),
            impresiones_hist=("impresiones", "mean"),
            clics_hist=("clics", "mean"),
        )
    )
    historico["cpa_hist"] = historico.apply(lambda row: _safe_div(row["inversion_hist"], row["conversiones_hist"]), axis=1)
    historico["roas_ltr_hist"] = historico.apply(
        lambda row: _safe_div(row["ingresos_ltr_esperados_hist"], row["inversion_hist"]),
        axis=1,
    )

    comparacion = actual.merge(historico, on=dimension, how="left")

    for kpi in ["inversion", "conversiones", "cpa", "roas_ltr", "beneficio_esperado_ltr"]:
        hist_col = f"{kpi}_hist"
        comparacion[f"var_{kpi}_pct"] = comparacion.apply(
            lambda row: _variacion_pct(row[kpi], row[hist_col]),
            axis=1,
        )
        comparacion[f"estado_{kpi}"] = comparacion[f"var_{kpi}_pct"].apply(
            lambda value: _clasificar_kpi(kpi, value, umbral_variacion)
        )

    comparacion["impacto_beneficio_ltr"] = (
        comparacion["beneficio_esperado_ltr"] - comparacion["beneficio_esperado_ltr_hist"]
    )

    def detectar_motivo(row) -> str:
        motivos = []
        if row["inversion"] >= min_inversion:
            if row["var_roas_ltr_pct"] is not None and not pd.isna(row["var_roas_ltr_pct"]):
                if row["var_roas_ltr_pct"] <= -umbral_variacion:
                    motivos.append("LTR/CPA cae")
                elif row["var_roas_ltr_pct"] >= umbral_variacion:
                    motivos.append("LTR/CPA mejora")
            if row["var_cpa_pct"] is not None and not pd.isna(row["var_cpa_pct"]):
                if row["var_cpa_pct"] >= umbral_variacion:
                    motivos.append("CPA sube")
                elif row["var_cpa_pct"] <= -umbral_variacion:
                    motivos.append("CPA mejora")
            if row["var_conversiones_pct"] is not None and not pd.isna(row["var_conversiones_pct"]):
                if row["var_conversiones_pct"] <= -umbral_variacion:
                    motivos.append("conversiones caen")
                elif row["var_conversiones_pct"] >= umbral_variacion:
                    motivos.append("conversiones suben")
        return "; ".join(motivos)

    comparacion["motivo_anomalia"] = comparacion.apply(detectar_motivo, axis=1)
    comparacion["es_anomalia"] = comparacion["motivo_anomalia"].str.len() > 0

    columnas_salida = [
        dimension,
        "inversion",
        "conversiones",
        "cpa",
        "ingresos_ltr_esperados",
        "ltr_esperado_365d",
        "roas_ltr",
        "beneficio_esperado_ltr",
        "net_ltr",
        "inversion_hist",
        "conversiones_hist",
        "cpa_hist",
        "roas_ltr_hist",
        "beneficio_esperado_ltr_hist",
        "var_conversiones_pct",
        "var_cpa_pct",
        "var_roas_ltr_pct",
        "impacto_beneficio_ltr",
        "es_anomalia",
        "motivo_anomalia",
    ]
    return comparacion[columnas_salida].sort_values("impacto_beneficio_ltr", ascending=False)


def analizar_kpis_y_anomalias(
    df: pd.DataFrame,
    fecha_objetivo: str,
    ventana_historica_dias: int = 14,
    dimensiones: list[str] | None = None,
    umbral_variacion: float = 0.20,
    min_inversion_dimension: float = 250.0,
    top_n: int = 10,
) -> dict:
    """Analiza KPIs de una fecha frente a dia anterior, media 7d y media 30d."""
    if dimensiones is None:
        dimensiones = DIMENSIONES_ANALISIS

    fecha_objetivo_ts = pd.Timestamp(fecha_objetivo)
    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    df_objetivo = df[df["fecha"] == fecha_objetivo_ts].copy()
    if df_objetivo.empty:
        raise ValueError(f"No hay datos para la fecha objetivo: {fecha_objetivo}")

    fecha_dia_anterior = fecha_objetivo_ts - pd.Timedelta(days=1)
    fecha_inicio_7d = fecha_objetivo_ts - pd.Timedelta(days=7)
    fecha_inicio_30d = fecha_objetivo_ts - pd.Timedelta(days=30)
    fecha_inicio_dimensiones = fecha_objetivo_ts - pd.Timedelta(days=ventana_historica_dias)

    df_dia_anterior = df[df["fecha"] == fecha_dia_anterior].copy()
    df_media_7d = df[(df["fecha"] >= fecha_inicio_7d) & (df["fecha"] < fecha_objetivo_ts)].copy()
    df_media_30d = df[(df["fecha"] >= fecha_inicio_30d) & (df["fecha"] < fecha_objetivo_ts)].copy()
    df_historico_dimensiones = df[
        (df["fecha"] >= fecha_inicio_dimensiones)
        & (df["fecha"] < fecha_objetivo_ts)
    ].copy()

    if df_media_7d.empty:
        raise ValueError("No hay historico suficiente para calcular la media de los 7 dias anteriores.")
    if df_historico_dimensiones.empty:
        raise ValueError("No hay historico suficiente para comparar la fecha objetivo.")

    kpis_objetivo = _agregar_kpis(df_objetivo).iloc[0]
    kpis_dia_anterior = _kpis_dia(df_dia_anterior)
    kpis_media_7d = _media_diaria_kpis(df_media_7d)
    kpis_media_30d = _media_diaria_kpis(df_media_30d)

    comparacion_global = _comparar_kpis_globales(
        kpis_objetivo,
        kpis_dia_anterior,
        kpis_media_7d,
        kpis_media_30d,
        umbral_variacion,
    )
    anomalias_globales = comparacion_global[comparacion_global["estado"] != "estable"].copy()

    analisis_dimensiones = {}
    anomalias_dimensiones = []
    for dimension in dimensiones:
        comparacion_dimension = _analizar_dimension(
            df_objetivo,
            df_historico_dimensiones,
            dimension,
            umbral_variacion,
            min_inversion_dimension,
        )
        analisis_dimensiones[dimension] = comparacion_dimension
        anomalias = comparacion_dimension[comparacion_dimension["es_anomalia"]].copy()
        if not anomalias.empty:
            anomalias.insert(0, "dimension", dimension)
            anomalias = anomalias.rename(columns={dimension: "valor_dimension"})
            anomalias_dimensiones.append(anomalias)

    if anomalias_dimensiones:
        anomalias_dimensiones_df = pd.concat(anomalias_dimensiones, ignore_index=True)
        anomalias_dimensiones_df = anomalias_dimensiones_df.sort_values(
            "impacto_beneficio_ltr",
            ascending=True,
        )
    else:
        anomalias_dimensiones_df = pd.DataFrame()

    por_alias = _agregar_kpis(df_objetivo, ["alias", "id_cuenta_google", "canal_anuncio", "codigo_pais", "producto"])

    alias_diario_7d = _agregar_kpis(df_media_7d, ["alias", "fecha"])
    por_alias_media_7d = (
        alias_diario_7d
        .groupby("alias", as_index=False)
        .agg(
            inversion_media_7d=("inversion", "mean"),
            conversiones_media_7d=("conversiones", "mean"),
            ingresos_ltr_esperados_media_7d=("ingresos_ltr_esperados", "mean"),
            beneficio_esperado_ltr_media_7d=("beneficio_esperado_ltr", "mean"),
        )
    )
    por_alias_media_7d["ltr_esperado_365d_media_7d"] = por_alias_media_7d.apply(
        lambda row: _safe_div(row["ingresos_ltr_esperados_media_7d"], row["conversiones_media_7d"]),
        axis=1,
    )
    por_alias_media_7d["cpa_media_7d"] = por_alias_media_7d.apply(
        lambda row: _safe_div(row["inversion_media_7d"], row["conversiones_media_7d"]),
        axis=1,
    )
    por_alias_media_7d["net_ltr_media_7d"] = por_alias_media_7d.apply(
        lambda row: _safe_div(row["beneficio_esperado_ltr_media_7d"], row["conversiones_media_7d"]),
        axis=1,
    )
    por_alias = por_alias.merge(por_alias_media_7d, on="alias", how="left")

    variaciones_alias = [
        ("ltr_esperado_365d", "ltr_esperado_365d_media_7d", "var_ltr_esperado_365d_vs_media_7d_pct"),
        ("cpa", "cpa_media_7d", "var_cpa_vs_media_7d_pct"),
        ("beneficio_esperado_ltr", "beneficio_esperado_ltr_media_7d", "var_beneficio_esperado_ltr_vs_media_7d_pct"),
    ]
    for actual_col, referencia_col, variacion_col in variaciones_alias:
        por_alias[variacion_col] = por_alias.apply(
            lambda row: _variacion_pct(row[actual_col], row[referencia_col]),
            axis=1,
        )

    top_aliases = por_alias.sort_values("beneficio_esperado_ltr", ascending=False).head(top_n)
    peores_aliases = por_alias.sort_values("beneficio_esperado_ltr", ascending=True).head(top_n)
    top_canales = analisis_dimensiones["canal_anuncio"].sort_values(
        "beneficio_esperado_ltr",
        ascending=False,
    ).head(top_n)

    eventos_detectados = (
        df_objetivo[df_objetivo["evento_sintetico"] != "sin_evento"]
        .groupby("evento_sintetico", as_index=False)
        .agg(
            registros=("id_registro", "count"),
            inversion=("inversion", "sum"),
            conversiones=("conversiones", "sum"),
            beneficio_esperado_ltr=("beneficio_esperado_ltr", "sum"),
        )
        .sort_values("beneficio_esperado_ltr", ascending=False)
    )

    ventanas_comparacion = {
        "dia_anterior": fecha_dia_anterior.date().isoformat(),
        "media_7d": _ventana_resumen(df_media_7d),
        "media_30d": _ventana_resumen(df_media_30d),
        "anomalias_dimensiones": _ventana_resumen(df_historico_dimensiones),
    }

    return {
        "fecha_objetivo": fecha_objetivo_ts.date().isoformat(),
        "ventana_historica": ventanas_comparacion["media_7d"],
        "ventanas_comparacion": ventanas_comparacion,
        "kpis_objetivo": kpis_objetivo.to_dict(),
        "comparacion_global": comparacion_global,
        "anomalias_globales": anomalias_globales,
        "analisis_dimensiones": analisis_dimensiones,
        "anomalias_dimensiones": anomalias_dimensiones_df,
        "top_aliases": top_aliases,
        "peores_aliases": peores_aliases,
        "top_canales": top_canales,
        "eventos_detectados": eventos_detectados,
    }
