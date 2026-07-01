# -*- coding: utf-8 -*-
"""Agente BI Reporter con function calling nativo.

El modelo recibe `tools`, devuelve `tool_calls`, Python ejecuta las funciones
y devuelve mensajes con rol `tool` antes de redactar la respuesta final.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import EMAIL_DESTINO, FECHA_OBJETIVO_DEMO, LLM_MODELO, LLM_TEMPERATURE
from .herramientas_agente import HerramientasBI
from .llm_client import crear_cliente_llm


INSTRUCCIONES_AGENTE_BI_FUNCTION_CALLING = """Eres BI Reporter Basebone, un agente creado por el departamento de BI para ayudar al departamento de Marketing.

Tu mision es redactar un email diario profesional para Marketing, elaborado desde BI.
El email debe explicar que ocurrio en la fecha objetivo y compararlo contra dia anterior, media 7 dias y media 30 dias,
destacar canales/aliases con mejor performance, detectar anomalias y proponer acciones prudentes.

REGLAS:
- Usa herramientas cuando necesites datos. No inventes metricas.
- Antes de redactar el email final debes usar estas herramientas como minimo:
  1) analizar_dia_bi
  2) obtener_top_canales
  3) obtener_top_aliases
  4) obtener_anomalias
  5) obtener_reporte_base
- El email final debe empezar exactamente con '# Resumen Performance Google Ads YYYY-MM-DD', usando la fecha objetivo real.
- El reporte va dirigido solo al departamento de Marketing; BI actua como area que lo elabora y valida.
- No incluyas una seccion de Introduccion. Despues del titulo crea '## Resumen' y deja solo la tabla dentro de ese bloque.
- En '## Resumen' incluye una tabla con estas columnas exactas: KPI, Ayer, Antes de ayer, Media 7 días, Media 30 días, Variación vs 1d, Variación vs 7d.
- En la tabla de Resumen, pon en negrita todos los valores de la columna KPI usando Markdown: **Nombre KPI**.
- No añadas texto explicativo antes de la tabla ni apartados de Lectura rápida o Cambios globales.
- Usa tablas comparativas, no listados largos, en Top Canales, Top aliases, Aliases a Revisar y Alertas Detectadas.
- En Aliases a Revisar, usa estas columnas exactas: Alias, Motivo, LTR, CPA, LTR/CPA, Impacto beneficio. No incluyas la columna Dimensión.
- En Alertas Detectadas, usa estas columnas exactas: Alerta, Aliases afectados, Impacto estimado, Lectura, Accion recomendada.
- En Top Canales, usa estas columnas exactas: Canal, Inversión, LTR, CPA, Beneficio Neto, LTR/CPA, Var. LTR/CPA, Var. CPA.
- En Top canales, pon en negrita todos los valores de la columna Canal usando Markdown: **Canal**.
- En esa tabla, LTR = ltr_esperado_365d (ingresos_ltr_esperados / conversiones) y Beneficio Neto = net_ltr (beneficio_esperado_ltr / conversiones).
- En Top aliases, usa estas columnas exactas: Alias, Canal, Inversión, LTR, CPA, Beneficio Esperado, Var. LTR vs 7d, Var. CPA vs 7d, Beneficio vs 7d.
- En Top aliases, pon en negrita todos los valores de la columna Alias usando Markdown: **Alias**.
- En Top aliases, Beneficio Esperado = beneficio_esperado_ltr; las variaciones comparan la fecha objetivo contra la media de los 7 días anteriores usando los campos var_*_vs_media_7d_pct.
- La columna de variación debe compararse solo contra la media de los 7 días anteriores.
- Usa los valores ya formateados de 'comparacion_global_formateada' cuando estén disponibles; no escribas números raw del JSON.
- En valores monetarios usa euros: importes de 3 o más cifras sin decimales, importes menores de 100 con 2 decimales.
- El email final debe ser el cuerpo del email en Markdown, no incluyas cabeceras SMTP.
- Escribe en castellano, con tono ejecutivo, claro y accionable.
- La estructura exacta de secciones debe ser: # Resumen Performance Google Ads YYYY-MM-DD, ## Resumen, ## Top Canales, ## Top aliases, ## Aliases a Revisar, ## Alertas Detectadas, ## Recomendacion.
- Usa el Markdown devuelto por obtener_reporte_base como plantilla obligatoria de estructura y tablas. Puedes mejorar redaccion y recomendaciones, pero no elimines secciones ni cambies nombres de columnas.
- Para no duplicar contexto, cuando llames a obtener_top_canales, obtener_top_aliases y obtener_anomalias pide n=3; obtener_reporte_base ya contiene las tablas completas.
- En Recomendación, usa exactamente 6 bullet points accionables para Marketing; no uses tabla en esta sección.
- Incluye una recomendacion de revision humana antes de tocar presupuestos.
"""


TOOLS_BI = [
    {
        "type": "function",
        "function": {
            "name": "analizar_dia_bi",
            "description": "Calcula KPIs globales de una fecha y los compara contra dia anterior, media 7 dias y media 30 dias.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {
                        "type": "string",
                        "description": "Fecha objetivo en formato YYYY-MM-DD.",
                    }
                },
                "required": ["fecha"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_top_canales",
            "description": "Devuelve los canales con mayor Beneficio esperado (LTR).",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "Fecha objetivo YYYY-MM-DD."},
                    "n": {"type": "integer", "description": "Numero de canales a devolver."},
                },
                "required": ["fecha"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_top_aliases",
            "description": "Devuelve los mejores aliases/campanas por Beneficio esperado (LTR).",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "Fecha objetivo YYYY-MM-DD."},
                    "n": {"type": "integer", "description": "Numero de aliases a devolver."},
                },
                "required": ["fecha"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_anomalias",
            "description": "Devuelve segmentos anomalos o que requieren revision.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "Fecha objetivo YYYY-MM-DD."},
                    "n": {"type": "integer", "description": "Numero de anomalias a devolver."},
                },
                "required": ["fecha"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_reporte_base",
            "description": "Devuelve el reporte base completo en Markdown con la estructura oficial del email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "Fecha objetivo YYYY-MM-DD."},
                },
                "required": ["fecha"],
            },
        },
    },

]


def construir_peticion_email(fecha: str, destinatario: str) -> str:
    return (
        "Genera el email diario de BI Reporter para la fecha "
        f"{fecha}. El destinatario de referencia es {destinatario}. "
        f"El email debe titularse '# Resumen Performance Google Ads {fecha}'. El reporte lo elabora BI para Marketing. Necesito un resumen tipo dashboard sobre performance de Google Ads, "
        "incluyendo KPIs globales, comparativa contra dia anterior, media 7 dias y media 30 dias, mejores canales, "
        "mejores aliases/campanas, anomalias relevantes, alertas detectadas y recomendaciones prudentes."
    )


def _serializar_tool_calls(tool_calls) -> list[dict]:
    return [
        {
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            },
        }
        for tc in tool_calls
    ]


def _cargar_argumentos(argumentos_raw: str | None) -> dict:
    if not argumentos_raw:
        return {}
    try:
        argumentos = json.loads(argumentos_raw)
    except json.JSONDecodeError:
        return {}
    return argumentos if isinstance(argumentos, dict) else {}


def _crear_funciones(fecha_default: str, destinatario: str) -> tuple[HerramientasBI, dict[str, Any]]:
    herramientas_bi = HerramientasBI(destinatario=destinatario)

    def analizar_dia_bi(fecha: str = fecha_default) -> str:
        return herramientas_bi.analizar_dia_bi({"fecha": fecha or fecha_default})

    def obtener_top_canales(fecha: str = fecha_default, n: int = 3) -> str:
        return herramientas_bi.obtener_top_canales({"fecha": fecha or fecha_default, "n": n})

    def obtener_top_aliases(fecha: str = fecha_default, n: int = 3) -> str:
        return herramientas_bi.obtener_top_aliases({"fecha": fecha or fecha_default, "n": n})

    def obtener_anomalias(fecha: str = fecha_default, n: int = 3) -> str:
        return herramientas_bi.obtener_anomalias({"fecha": fecha or fecha_default, "n": n})

    def obtener_reporte_base(fecha: str = fecha_default) -> str:
        return herramientas_bi.obtener_reporte_base({"fecha": fecha or fecha_default})

    funciones = {
        "analizar_dia_bi": analizar_dia_bi,
        "obtener_top_canales": obtener_top_canales,
        "obtener_top_aliases": obtener_top_aliases,
        "obtener_anomalias": obtener_anomalias,
        "obtener_reporte_base": obtener_reporte_base,
    }
    return herramientas_bi, funciones


def _herramientas_minimas_usadas(herramientas_usadas: list[dict]) -> bool:
    usadas = {item["herramienta"] for item in herramientas_usadas}
    requeridas = {
        "analizar_dia_bi",
        "obtener_top_canales",
        "obtener_top_aliases",
        "obtener_anomalias",
        "obtener_reporte_base",
    }
    return requeridas.issubset(usadas)


def ejecutar_agente_bi_function_calling(
    fecha: str = FECHA_OBJETIVO_DEMO,
    destinatario: str = EMAIL_DESTINO,
    cliente=None,
    max_pasos: int = 10,
    verbose: bool = True,
) -> dict:
    """Ejecuta el agente con function calling nativo."""
    cliente = cliente or crear_cliente_llm()
    herramientas_bi, funciones = _crear_funciones(fecha, destinatario)
    herramientas_usadas: list[dict] = []

    mensajes: list[dict] = [
        {"role": "system", "content": INSTRUCCIONES_AGENTE_BI_FUNCTION_CALLING},
        {"role": "user", "content": construir_peticion_email(fecha, destinatario)},
    ]

    for paso in range(1, max_pasos + 1):
        respuesta = cliente.chat.completions.create(
            model=LLM_MODELO,
            messages=mensajes,
            tools=TOOLS_BI,
            tool_choice="auto",
            temperature=LLM_TEMPERATURE,
        )
        msg = respuesta.choices[0].message
        tool_calls = msg.tool_calls or []

        if not tool_calls:
            contenido = msg.content or ""
            if _herramientas_minimas_usadas(herramientas_usadas):
                if verbose:
                    print(f"[Paso {paso}] El agente redacta el email final.")
                return {
                    "estado": "completado",
                    "modo_agente": "function_calling_nativo",
                    "fecha": fecha,
                    "respuesta": contenido,
                    "herramientas_usadas": herramientas_usadas,
                    "mensajes": mensajes + [{"role": "assistant", "content": contenido}],
                    "resumen_csv": herramientas_bi.resumen_csv,
                }

            mensajes.append({"role": "assistant", "content": contenido})
            mensajes.append(
                {
                    "role": "user",
                    "content": (
                        "Antes de redactar el email final debes usar analizar_dia_bi, "
                        "obtener_top_canales, obtener_top_aliases y obtener_anomalias."
                    ),
                }
            )
            continue

        mensajes.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": _serializar_tool_calls(tool_calls),
            }
        )

        for tc in tool_calls:
            nombre = tc.function.name
            argumentos = _cargar_argumentos(tc.function.arguments)
            funcion = funciones.get(nombre)
            if funcion is None:
                resultado = f"Error: la herramienta '{nombre}' no existe."
            else:
                try:
                    resultado = funcion(**argumentos)
                except Exception as exc:
                    resultado = f"Error al ejecutar {nombre}: {exc}"

            herramientas_usadas.append(
                {
                    "paso": paso,
                    "herramienta": nombre,
                    "argumentos": argumentos,
                }
            )

            if verbose:
                preview = str(resultado).replace("\n", " ")[:220]
                print(f"[Paso {paso}] {nombre}({argumentos}) -> {preview}...")

            mensajes.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(resultado),
                }
            )

    raise RuntimeError(
        "El agente LLM agoto el limite de pasos sin generar respuesta final. "
        "No se devuelve fallback sin LLM."
    )


def guardar_traza_agente_function_calling(resultado_agente: dict, output_path: Path) -> Path:
    """Guarda una traza simple para auditar el ciclo function calling del agente."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {
        "estado": resultado_agente.get("estado"),
        "modo_agente": resultado_agente.get("modo_agente"),
        "fecha": resultado_agente.get("fecha"),
        "herramientas_usadas": resultado_agente.get("herramientas_usadas", []),
        "mensajes": resultado_agente.get("mensajes", []),
    }
    output_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
