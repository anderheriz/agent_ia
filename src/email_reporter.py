# -*- coding: utf-8 -*-
"""Preparacion segura de emails para BI Reporter."""

from __future__ import annotations

import re
from datetime import datetime
from html import escape
from pathlib import Path


def _inline_markdown(texto: str) -> str:
    """Escapa texto y convierte negritas Markdown sencillas a HTML."""
    partes = re.split(r"(\*\*.*?\*\*)", texto)
    salida = []
    for parte in partes:
        if parte.startswith("**") and parte.endswith("**") and len(parte) > 4:
            salida.append(f"<strong>{escape(parte[2:-2])}</strong>")
        else:
            salida.append(escape(parte))
    return "".join(salida)


def _cerrar_listas(lineas_html: list[str], lista_abierta: str | None) -> None:
    if lista_abierta:
        lineas_html.append(f"</{lista_abierta}>")


def _render_barra_dashboard(celda: str) -> str | None:
    """Renderiza barras ASCII del reporte como mini graficos HTML."""
    if not re.fullmatch(r"[+-][#.]+", celda):
        return None

    total = max(len(celda) - 1, 1)
    relleno = celda.count("#")
    ancho = max(round((relleno / total) * 100), 4 if relleno else 0)
    positivo = celda.startswith("+")
    color = "#0f766e" if positivo else "#b42318"
    etiqueta = "mejora" if positivo else "caida"

    return (
        '<div style="min-width:120px;">'
        '<div style="height:8px;background:#e5e7eb;border-radius:999px;overflow:hidden;">'
        f'<div style="height:8px;width:{ancho}%;background:{color};"></div>'
        "</div>"
        f'<div style="font-size:11px;color:#52606d;margin-top:3px;">{etiqueta}</div>'
        "</div>"
    )


def _render_variacion_pct(celda: str) -> str | None:
    """Colorea variaciones porcentuales positivas/negativas."""
    texto = celda.strip()
    if not re.fullmatch(r"[+-]?\d+(?:[\.,]\d+)?%", texto):
        return None

    try:
        valor = float(texto.replace("%", "").replace(",", "."))
    except ValueError:
        return None

    if valor > 0:
        color = "#0f766e"
    elif valor < 0:
        color = "#b42318"
    else:
        color = "#52606d"

    return f'<span style="color:{color};font-weight:700;">{escape(texto)}</span>'


def _render_valor_signado(celda: str) -> str | None:
    """Colorea importes positivos/negativos."""
    texto = celda.strip()
    patron = r"[+-]?\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*€|[+-]?\d+(?:,\d+)?\s*€"
    if not re.fullmatch(patron, texto):
        return None

    normalizado = texto.replace("€", "").strip().replace(".", "").replace(",", ".")
    try:
        valor = float(normalizado)
    except ValueError:
        return None

    if valor > 0:
        color = "#0f766e"
    elif valor < 0:
        color = "#b42318"
    else:
        color = "#52606d"

    return f'<span style="color:{color};font-weight:700;">{escape(texto)}</span>'


def _anchos_columnas(cabecera: list[str]) -> list[float]:
    """Define anchos estables para que Gmail no deforme las tablas."""
    nombres = [nombre.strip().lower() for nombre in cabecera]

    if nombres == [
        "kpi",
        "ayer",
        "antes de ayer",
        "media 7 días",
        "media 30 días",
        "variación vs 1d",
        "variación vs 7d",
    ]:
        return [22, 13, 13, 13, 13, 13, 13]

    if nombres == [
        "canal",
        "inversión",
        "ltr",
        "cpa",
        "beneficio neto",
        "ltr/cpa",
        "var. ltr/cpa",
        "var. cpa",
    ]:
        return [18, 12, 10, 10, 14, 10, 13, 13]

    if nombres == [
        "alias",
        "canal",
        "inversión",
        "ltr",
        "cpa",
        "beneficio esperado",
        "var. ltr vs 7d",
        "var. cpa vs 7d",
        "beneficio vs 7d",
    ]:
        return [22, 12, 10, 8, 8, 13, 9, 9, 9]

    if nombres == ["alias", "motivo", "ltr", "cpa", "ltr/cpa", "impacto beneficio"]:
        return [20, 34, 10, 10, 10, 16]

    if nombres == ["alerta", "aliases afectados", "impacto estimado", "lectura", "acción recomendada"]:
        return [24, 12, 14, 20, 30]

    ancho = round(100 / max(len(cabecera), 1), 2)
    return [ancho for _ in cabecera]


def _es_metrica_compacta(celda: str) -> bool:
    """Evita que importes, ratios y porcentajes salten de línea dentro de Gmail."""
    texto = re.sub(r"^\*\*(.*)\*\*$", r"\1", celda.strip())
    patrones = [
        r"[+-]?\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*€",
        r"[+-]?\d+(?:[\.,]\d+)?\s*€",
        r"[+-]?\d+(?:[\.,]\d+)?%",
        r"[+-]?\d+(?:[\.,]\d+)?x",
        r"[+-]?\d{1,3}(?:\.\d{3})*",
    ]
    return any(re.fullmatch(patron, texto) for patron in patrones)


def _convertir_tabla_markdown(tabla: list[str]) -> str:
    """Convierte tablas Markdown simples en tablas HTML para Gmail."""
    filas = []
    for linea in tabla:
        celdas = [celda.strip().strip("`") for celda in linea.strip("|").split("|")]
        if all(set(celda.replace(":", "").replace("-", "")) == set() for celda in celdas):
            continue
        filas.append(celdas)

    if not filas:
        return ""

    cabecera = filas[0]
    cuerpo = filas[1:]
    anchos = _anchos_columnas(cabecera)
    html = [
        '<table style="width:100%;table-layout:fixed;border-collapse:collapse;'
        'margin:10px 0 18px 0;font-size:13px;">',
        "<thead><tr>",
    ]
    for idx, celda in enumerate(cabecera):
        ancho = anchos[idx] if idx < len(anchos) else round(100 / max(len(cabecera), 1), 2)
        html.append(
            '<th style="text-align:center;background:#eef2f7;color:#243b53;border:1px solid #d9dee7;'
            f'padding:8px 8px;font-weight:700;line-height:1.25;width:{ancho}%;">'
            f"{_inline_markdown(celda)}</th>"
        )
    html.append("</tr></thead><tbody>")

    indices_variacion = {
        idx
        for idx, nombre in enumerate(cabecera)
        if (
            "variación" in nombre.lower()
            or "variacion" in nombre.lower()
            or nombre.lower().startswith("var.")
            or nombre.lower().startswith("var ")
            or nombre.lower().endswith("vs 7d")
        )
    }
    indices_signo = {
        idx
        for idx, nombre in enumerate(cabecera)
        if nombre.lower() in {"impacto beneficio", "impacto estimado"}
    }
    nombres_cabecera = [nombre.strip().lower() for nombre in cabecera]
    tabla_aliases_revisar = nombres_cabecera == [
        "alias",
        "motivo",
        "ltr",
        "cpa",
        "ltr/cpa",
        "impacto beneficio",
    ]
    tabla_top_aliases = nombres_cabecera == [
        "alias",
        "canal",
        "inversión",
        "ltr",
        "cpa",
        "beneficio esperado",
        "var. ltr vs 7d",
        "var. cpa vs 7d",
        "beneficio vs 7d",
    ]

    for fila in cuerpo:
        html.append("<tr>")
        for idx, celda in enumerate(fila):
            barra_html = _render_barra_dashboard(celda)
            variacion_html = _render_variacion_pct(celda) if idx in indices_variacion else None
            signo_html = _render_valor_signado(celda) if idx in indices_signo else None
            contenido = barra_html or variacion_html or signo_html or _inline_markdown(celda)
            if tabla_aliases_revisar and idx == 1:
                contenido = f"<strong>{contenido}</strong>"
            nowrap = "white-space:nowrap;" if _es_metrica_compacta(celda) else ""
            ajuste_alias = (
                "font-size:12px;overflow-wrap:anywhere;word-break:break-word;"
                if tabla_top_aliases and idx == 0
                else ""
            )
            html.append(
                '<td style="text-align:center;border:1px solid #e4e7eb;padding:8px 8px;'
                f'vertical-align:middle;line-height:1.25;{nowrap}{ajuste_alias}">'
                f"{contenido}</td>"
            )
        html.append("</tr>")

    html.append("</tbody></table>")
    return "".join(html)


def convertir_markdown_a_html_basico(
    reporte_markdown: str,
    incluir_aviso_borrador: bool = True,
) -> str:
    """Convierte Markdown sencillo a HTML compatible con Gmail."""
    lineas_html: list[str] = []
    lista_abierta: str | None = None

    lineas = reporte_markdown.splitlines()
    idx = 0
    while idx < len(lineas):
        linea_original = lineas[idx]
        linea = linea_original.strip()

        if linea.startswith("|") and "|" in linea[1:]:
            tabla = []
            while idx < len(lineas) and lineas[idx].strip().startswith("|"):
                tabla.append(lineas[idx].strip())
                idx += 1
            _cerrar_listas(lineas_html, lista_abierta)
            lista_abierta = None
            lineas_html.append(_convertir_tabla_markdown(tabla))
            continue

        if not linea:
            _cerrar_listas(lineas_html, lista_abierta)
            lista_abierta = None
            idx += 1
            continue

        if linea.startswith("# "):
            _cerrar_listas(lineas_html, lista_abierta)
            lista_abierta = None
            lineas_html.append(
                '<h1 style="margin:0 0 18px 0;color:#102a43;font-size:24px;line-height:1.25;">'
                f"{_inline_markdown(linea[2:])}</h1>"
            )
        elif linea.startswith("## "):
            _cerrar_listas(lineas_html, lista_abierta)
            lista_abierta = None
            lineas_html.append(
                '<h2 style="margin:24px 0 10px 0;color:#243b53;font-size:17px;'
                'line-height:1.3;border-bottom:1px solid #e4e7eb;padding-bottom:6px;">'
                f"{_inline_markdown(linea[3:])}</h2>"
            )
        elif linea.startswith("### "):
            _cerrar_listas(lineas_html, lista_abierta)
            lista_abierta = None
            lineas_html.append(
                '<h3 style="margin:18px 0 8px 0;color:#334e68;font-size:15px;line-height:1.3;">'
                f"{_inline_markdown(linea[4:])}</h3>"
            )
        elif linea.startswith("- "):
            if lista_abierta != "ul":
                _cerrar_listas(lineas_html, lista_abierta)
                lineas_html.append('<ul style="margin:8px 0 14px 22px;padding:0;">')
                lista_abierta = "ul"
            lineas_html.append(
                '<li style="margin:0 0 8px 0;">'
                f"{_inline_markdown(linea[2:])}</li>"
            )
        elif re.match(r"^\d+\.\s+", linea):
            if lista_abierta != "ol":
                _cerrar_listas(lineas_html, lista_abierta)
                lineas_html.append('<ol style="margin:8px 0 14px 22px;padding:0;">')
                lista_abierta = "ol"
            contenido = re.sub(r"^\d+\.\s+", "", linea)
            lineas_html.append(
                '<li style="margin:0 0 8px 0;">'
                f"{_inline_markdown(contenido)}</li>"
            )
        else:
            _cerrar_listas(lineas_html, lista_abierta)
            lista_abierta = None
            lineas_html.append(
                '<p style="margin:0 0 12px 0;">'
                f"{_inline_markdown(linea)}</p>"
            )

        idx += 1

    _cerrar_listas(lineas_html, lista_abierta)

    aviso = (
        '<div style="margin:0 0 18px 0;padding:12px 14px;border:1px solid #f0b429;'
        'border-radius:6px;background:#fffbea;color:#5f370e;font-size:14px;">'
        "Borrador local de demo. Este email no ha sido enviado.</div>"
        if incluir_aviso_borrador
        else ""
    )

    cuerpo = "\n".join(lineas_html)
    return f"""<!doctype html>
<html lang="es">
<body style="margin:0;padding:0;background:#f6f7f9;color:#1f2933;font-family:Arial,Helvetica,sans-serif;line-height:1.5;">
  <div style="max-width:860px;margin:0 auto;background:#ffffff;border:1px solid #d9dee7;border-radius:8px;padding:28px;">
    {aviso}
    {cuerpo}
  </div>
</body>
</html>
"""


def preparar_email_reporte(
    resultados: dict,
    reporte_markdown: str,
    destinatario: str,
    remitente: str,
    modo_borrador: bool = True,
) -> dict:
    """Prepara el email diario en formato texto y HTML."""
    fecha = resultados["fecha_objetivo"]
    asunto = f"Resumen Performance Google Ads {fecha}"

    if modo_borrador:
        cuerpo_texto = "\n".join(
            [
                "BORRADOR LOCAL - NO ENVIADO",
                f"Para: {destinatario}",
                f"De: {remitente}",
                f"Asunto: {asunto}",
                "",
                reporte_markdown,
            ]
        )
    else:
        cuerpo_texto = reporte_markdown

    return {
        "estado": "borrador_local_no_enviado" if modo_borrador else "preparado_para_envio",
        "fecha_reporte": fecha,
        "destinatario": destinatario,
        "remitente": remitente,
        "asunto": asunto,
        "cuerpo_texto": cuerpo_texto,
        "cuerpo_html": convertir_markdown_a_html_basico(
            reporte_markdown,
            incluir_aviso_borrador=modo_borrador,
        ),
        "creado_en": datetime.now().isoformat(timespec="seconds"),
    }


def guardar_borrador_email(email: dict, output_dir: Path) -> dict[str, Path]:
    """Guarda el email en TXT y HTML para revision humana."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fecha = email["fecha_reporte"]

    txt_path = output_dir / f"email_reporte_{fecha}.txt"
    html_path = output_dir / f"email_reporte_{fecha}.html"

    txt_path.write_text(email["cuerpo_texto"], encoding="utf-8")
    html_path.write_text(email["cuerpo_html"], encoding="utf-8")

    return {
        "txt": txt_path,
        "html": html_path,
    }
