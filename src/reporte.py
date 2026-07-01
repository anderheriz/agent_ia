# -*- coding: utf-8 -*-
"""Generacion de reportes diarios en texto/Markdown."""

from pathlib import Path

import pandas as pd


def _formato_es(valor: float, decimales: int = 0) -> str:
    if valor is None or pd.isna(valor):
        return "n/a"
    return f"{valor:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _eur(valor: float) -> str:
    if valor is None or pd.isna(valor):
        return "n/a"
    decimales = 0 if abs(float(valor)) >= 100 else 2
    return f"{_formato_es(float(valor), decimales)} €"


def _num(valor: float) -> str:
    if valor is None or pd.isna(valor):
        return "n/a"
    return _formato_es(float(valor), 0)


def _ratio(valor: float) -> str:
    if valor is None or pd.isna(valor):
        return "n/a"
    return f"{float(valor):.2f}x"


def _pct(valor: float, decimales: int = 1) -> str:
    if valor is None or pd.isna(valor):
        return "n/a"
    return f"{float(valor):.{decimales}%}".replace(".", ",")


def _pct_delta(valor: float) -> str:
    if valor is None or pd.isna(valor):
        return "n/a"
    return f"{float(valor):.1%}"


def _kpi_label(kpi: str) -> str:
    labels = {
        "inversion": "Inversión",
        "conversiones": "Conversiones",
        "cpa": "CPA",
        "roas_ltr": "LTR/CPA",
        "ltr_esperado_365d": "Life Time Revenue (LTR)",
        "net_ltr": "Beneficio Neto (LTR)",
        "beneficio_esperado_ltr": "Beneficio esperado (LTR)",
        "tasa_conversion": "Tasa de conversión",
        "margen_beneficio_ltr": "Margen Neto (LTR)",
    }
    return labels.get(kpi, kpi.replace("_", " ").title())


def _formatear_kpi(kpi: str, valor: float) -> str:
    if valor is None or pd.isna(valor):
        return "n/a"
    if kpi in {"inversion", "cpa", "ltr_esperado_365d", "net_ltr", "ingresos_ltr_esperados", "beneficio_esperado_ltr"}:
        return _eur(valor)
    if kpi in {"roas_ltr"}:
        return _ratio(valor)
    if kpi == "tasa_conversion":
        return _pct(valor, decimales=2)
    if kpi == "margen_beneficio_ltr":
        return _pct(valor)
    return _num(valor)


def _estado_label(estado: str) -> str:
    return str(estado).replace("_", " ").capitalize()


def _fila_comparacion(comparacion_global: pd.DataFrame, kpi: str) -> pd.Series | None:
    fila = comparacion_global[comparacion_global["kpi"] == kpi]
    if fila.empty:
        return None
    return fila.iloc[0]


def _tabla(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return ["Sin datos disponibles."]
    lineas = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---" for _ in headers]) + " |",
    ]
    for row in rows:
        lineas.append("| " + " | ".join(str(value) for value in row) + " |")
    return lineas


def _tabla_resumen(comparacion_global: pd.DataFrame) -> list[str]:
    kpis_dashboard = [
        "inversion",
        "conversiones",
        "tasa_conversion",
        "cpa",
        "ltr_esperado_365d",
        "net_ltr",
        "beneficio_esperado_ltr",
        "margen_beneficio_ltr",
    ]
    rows = []
    for kpi in kpis_dashboard:
        fila = _fila_comparacion(comparacion_global, kpi)
        if fila is None:
            continue
        rows.append(
            [
                f"**{_kpi_label(kpi)}**",
                _formatear_kpi(kpi, fila["valor_fecha_objetivo"]),
                _formatear_kpi(kpi, fila["valor_dia_anterior"]),
                _formatear_kpi(kpi, fila["media_7d"]),
                _formatear_kpi(kpi, fila["media_30d"]),
                fila["variacion_vs_1d_pct_fmt"],
                fila["variacion_vs_7d_pct_fmt"],
            ]
        )
    return _tabla(
        ["KPI", "Ayer", "Antes de ayer", "Media 7 días", "Media 30 días", "Variación vs 1d", "Variación vs 7d"],
        rows,
    )


def _tabla_canales(resultados: dict) -> list[str]:
    rows = []
    for _, row in resultados["top_canales"].head(7).iterrows():
        conversiones = row.get("conversiones")

        ltr = row.get("ltr_esperado_365d")
        if (ltr is None or pd.isna(ltr)) and conversiones and not pd.isna(conversiones):
            ltr = row["ingresos_ltr_esperados"] / conversiones

        net_ltr = row.get("net_ltr")
        if (net_ltr is None or pd.isna(net_ltr)) and conversiones and not pd.isna(conversiones):
            net_ltr = row["beneficio_esperado_ltr"] / conversiones

        rows.append(
            [
                f"**{row['canal_anuncio']}**",
                _eur(row["inversion"]),
                _eur(ltr),
                _eur(row["cpa"]),
                _eur(net_ltr),
                _ratio(row["roas_ltr"]),
                _pct_delta(row["var_roas_ltr_pct"]),
                _pct_delta(row["var_cpa_pct"]),
            ]
        )
    return _tabla(
        ["Canal", "Inversión", "LTR", "CPA", "Beneficio Neto", "LTR/CPA", "Var. LTR/CPA", "Var. CPA"],
        rows,
    )


def _tabla_aliases(resultados: dict) -> list[str]:
    rows = []
    for _, row in resultados["top_aliases"].head(7).iterrows():
        rows.append(
            [
                f"**{row['alias']}**",
                row["canal_anuncio"],
                _eur(row["inversion"]),
                _eur(row["ltr_esperado_365d"]),
                _eur(row["cpa"]),
                _eur(row["beneficio_esperado_ltr"]),
                _pct_delta(row.get("var_ltr_esperado_365d_vs_media_7d_pct")),
                _pct_delta(row.get("var_cpa_vs_media_7d_pct")),
                _pct_delta(row.get("var_beneficio_esperado_ltr_vs_media_7d_pct")),
            ]
        )
    return _tabla(
        [
            "Alias",
            "Canal",
            "Inversión",
            "LTR",
            "CPA",
            "Beneficio Esperado",
            "Var. LTR vs 7d",
            "Var. CPA vs 7d",
            "Beneficio vs 7d",
        ],
        rows,
    )


def _tabla_anomalias(resultados: dict) -> list[str]:
    anomalias = resultados["anomalias_dimensiones"]
    rows = []
    if isinstance(anomalias, pd.DataFrame) and not anomalias.empty:
        for _, row in anomalias.head(8).iterrows():
            rows.append(
                [
                    row["valor_dimension"],
                    row["motivo_anomalia"],
                    _eur(row["ltr_esperado_365d"]),
                    _eur(row["cpa"]),
                    _ratio(row["roas_ltr"]),
                    _eur(row["impacto_beneficio_ltr"]),
                ]
            )
    return _tabla(
        ["Alias", "Motivo", "LTR", "CPA", "LTR/CPA", "Impacto beneficio"],
        rows,
    )


def _accion_alerta(motivo: str) -> str:
    motivo_lower = str(motivo).lower()
    if "ltr/cpa cae" in motivo_lower and "cpa sube" in motivo_lower:
        return "Revisar pujas, tracking y calidad de conversiones antes de invertir más."
    if "conversiones caen" in motivo_lower:
        return "Comprobar volumen, landing y cambios recientes de campaña."
    if "cpa sube" in motivo_lower:
        return "Controlar pujas y coste; no escalar hasta estabilizar CPA."
    if "ltr/cpa cae" in motivo_lower:
        return "Validar si el deterioro viene de LTR, CPA o mix de país/producto."
    return "Revisar el segmento antes de aplicar cambios de presupuesto."


def _tabla_alertas(resultados: dict) -> list[str]:
    anomalias = resultados["anomalias_dimensiones"]
    rows = []
    if isinstance(anomalias, pd.DataFrame) and not anomalias.empty:
        alertas = (
            anomalias.groupby("motivo_anomalia", as_index=False)
            .agg(
                aliases_afectados=("valor_dimension", "count"),
                impacto_estimado=("impacto_beneficio_ltr", "sum"),
                ltr_medio=("ltr_esperado_365d", "mean"),
                cpa_medio=("cpa", "mean"),
            )
        )
        alertas = alertas[alertas["impacto_estimado"] < 0]
        alertas = alertas.sort_values("impacto_estimado", ascending=True).head(6)
        for _, row in alertas.iterrows():
            rows.append(
                [
                    f"**{row['motivo_anomalia']}**",
                    _num(row["aliases_afectados"]),
                    _eur(row["impacto_estimado"]),
                    f"LTR medio {_eur(row['ltr_medio'])} / CPA medio {_eur(row['cpa_medio'])}",
                    _accion_alerta(row["motivo_anomalia"]),
                ]
            )
    return _tabla(
        ["Alerta", "Aliases afectados", "Impacto estimado", "Lectura", "Acción recomendada"],
        rows,
    )


def _lista_recomendaciones(resultados: dict) -> list[str]:
    recomendaciones = []

    top_canales = resultados.get("top_canales")
    top_aliases = resultados.get("top_aliases")
    anomalias = resultados.get("anomalias_dimensiones")

    if isinstance(top_canales, pd.DataFrame) and not top_canales.empty:
        canal = top_canales.iloc[0]
        recomendaciones.append(
            f"- Evaluar si **{canal['canal_anuncio']}** puede absorber mas inversion controlada: "
            f"hoy mueve {_eur(canal['inversion'])}, con LTR/CPA {_ratio(canal['roas_ltr'])} "
            f"y CPA {_eur(canal['cpa'])}."
        )

    if isinstance(top_canales, pd.DataFrame) and len(top_canales) >= 2:
        canal_1 = top_canales.iloc[0]
        canal_2 = top_canales.iloc[1]
        recomendaciones.append(
            f"- Comparar **{canal_1['canal_anuncio']}** vs **{canal_2['canal_anuncio']}** antes de mover presupuesto: "
            f"validar si la diferencia de LTR/CPA se mantiene por pais, producto y dispositivo."
        )

    if isinstance(top_aliases, pd.DataFrame) and not top_aliases.empty:
        alias = top_aliases.iloc[0]
        recomendaciones.append(
            f"- Replicar aprendizajes de **{alias['alias']}** en aliases similares: "
            f"canal {alias['canal_anuncio']}, inversion {_eur(alias['inversion'])}, "
            f"LTR {_eur(alias['ltr_esperado_365d'])} y CPA {_eur(alias['cpa'])}."
        )

    if isinstance(anomalias, pd.DataFrame) and not anomalias.empty:
        peor = anomalias.iloc[0]
        recomendaciones.append(
            f"- Revisar de forma prioritaria **{peor['valor_dimension']}**: {peor['motivo_anomalia']}; "
            f"impacto estimado {_eur(peor['impacto_beneficio_ltr'])}."
        )
        recomendaciones.append(
            f"- Bloquear incrementos de presupuesto en los {min(len(anomalias), 8)} aliases marcados en "
            "Aliases a Revisar hasta comprobar tracking, cambios de landing, pais y calidad de conversiones."
        )

    recomendaciones.extend(
        [
            "- Hacer cambios de presupuesto en tests pequenos y medibles, preferiblemente entre 5% y 10%, nunca como redistribucion masiva sin revision humana.",
            "- Priorizar presupuesto hacia combinaciones canal/alias con LTR estable, CPA controlado y Beneficio Esperado positivo frente a su media de 7 dias.",
            "- Revisar creatividades y audiencias de aliases con CPA subiendo aunque el beneficio siga siendo positivo, para evitar deterioro antes de escalar.",
            "- Documentar cada cambio de puja, presupuesto o segmentacion y revisar en el reporte de manana si mejora LTR/CPA sin empeorar CPA.",
        ]
    )

    return recomendaciones[:6]


def generar_reporte_texto(resultados: dict, destinatario: str) -> str:
    """Convierte el analisis en un reporte diario legible."""
    fecha = resultados["fecha_objetivo"]
    comparacion_global = resultados["comparacion_global"]

    lineas = [
        f"# Resumen Performance Google Ads {fecha}",
        "",
        "**Elaborado por:** BI | **Audiencia:** Marketing",
        "",
        "## Resumen",
        "",
    ]
    lineas.extend(_tabla_resumen(comparacion_global))

    lineas.extend(["", "## Top Canales", ""])
    lineas.extend(_tabla_canales(resultados))

    lineas.extend(["", "## Top aliases", ""])
    lineas.extend(_tabla_aliases(resultados))

    lineas.extend(["", "## Aliases a Revisar", ""])
    lineas.extend(_tabla_anomalias(resultados))

    lineas.extend(["", "## Alertas Detectadas", ""])
    lineas.extend(_tabla_alertas(resultados))

    lineas.extend(["", "## Recomendación", ""])
    lineas.extend(_lista_recomendaciones(resultados))

    return "\n".join(lineas)


def guardar_reporte(reporte: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(reporte, encoding="utf-8")
    return output_path
