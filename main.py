# -*- coding: utf-8 -*-
"""Punto de entrada principal de BI Reporter."""

from __future__ import annotations

import argparse
import unicodedata
from datetime import date

from src.agente_bi_function_calling import (
    ejecutar_agente_bi_function_calling,
    guardar_traza_agente_function_calling,
)
from src.config import EMAIL_DESTINO, EMAIL_REMITENTE, FECHA_OBJETIVO_DEMO, OUTPUTS_DIR
from src.email_reporter import guardar_borrador_email, preparar_email_reporte
from src.email_sender import (
    enviar_email_real,
    guardar_resultado_envio,
    obtener_remitente_composio,
    validar_configuracion_envio,
)
from src.llm_client import obtener_api_key
from src.reporte import guardar_reporte


def _normalizar_para_validacion(texto: str) -> str:
    """Normaliza el Markdown para validar estructura sin pelearse con negritas o acentos."""
    texto = texto.replace("**", "").lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return " ".join(texto.split())


def _reporte_tiene_estructura_esperada(reporte: str) -> bool:
    """Comprueba que el texto final conserva las secciones clave del email."""
    normalizado = _normalizar_para_validacion(reporte)
    fragmentos_requeridos = [
        "# resumen performance google ads ",
        "## resumen",
        "## top canales",
        "## top aliases",
        "## aliases a revisar",
        "## alertas detectadas",
        "## recomend",
        "kpi | ayer | antes de ayer",
        "canal | inversion | ltr | cpa | beneficio neto | ltr/cpa | var. ltr/cpa | var. cpa",
        "alias | canal | inversion | ltr | cpa | beneficio esperado",
        "alias | motivo | ltr | cpa | ltr/cpa | impacto beneficio",
        "alerta | aliases afectados | impacto estimado | lectura",
    ]
    return all(fragmento in normalizado for fragmento in fragmentos_requeridos)


def _validar_fecha_no_futura(fecha: str) -> None:
    """Evita materializar outputs para dias que aun no existirian en un warehouse real."""
    try:
        fecha_objetivo = date.fromisoformat(fecha)
    except ValueError as exc:
        raise ValueError("La fecha debe tener formato YYYY-MM-DD.") from exc

    hoy = date.today()
    if fecha_objetivo > hoy:
        raise ValueError(
            f"No se puede generar el reporte de {fecha}: es una fecha futura. "
            "BI Reporter simula un warehouse incremental, por lo que cada output "
            "debe crearse el propio dia del reporte o despues."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ejecuta BI Reporter.")
    parser.add_argument("--fecha", default=FECHA_OBJETIVO_DEMO, help="Fecha objetivo YYYY-MM-DD.")
    parser.add_argument(
        "--usar-llm",
        action="store_true",
        help="Opcion conservada por compatibilidad. El agente LLM se usa siempre.",
    )
    parser.add_argument(
        "--enviar-email",
        action="store_true",
        help="Envia el email real por Gmail mediante Composio OAuth.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fecha = args.fecha
    _validar_fecha_no_futura(fecha)

    if args.enviar_email:
        validar_configuracion_envio()

    obtener_api_key(required=True)
    resultado_agente = ejecutar_agente_bi_function_calling(
        fecha=fecha,
        destinatario=EMAIL_DESTINO,
        verbose=True,
    )
    reporte = resultado_agente["respuesta"]
    resumen_csv = resultado_agente.get("resumen_csv") or {}
    traza_path = guardar_traza_agente_function_calling(
        resultado_agente,
        OUTPUTS_DIR / f"traza_agente_{fecha}.json",
    )
    if not _reporte_tiene_estructura_esperada(reporte):
        raise RuntimeError(
            "El LLM no respeto la estructura esperada del reporte. "
            "No se genera fallback sin LLM para evitar un resultado que no sea del agente."
        )
    modo_reporte = "agente_llm_groq_function_calling"

    output_path = OUTPUTS_DIR / f"reporte_diario_{fecha}.md"
    guardar_reporte(reporte, output_path)

    remitente = obtener_remitente_composio(default=EMAIL_REMITENTE) if args.enviar_email else EMAIL_REMITENTE
    email = preparar_email_reporte(
        resultados={"fecha_objetivo": fecha},
        reporte_markdown=reporte,
        destinatario=EMAIL_DESTINO,
        remitente=remitente or EMAIL_REMITENTE,
        modo_borrador=not args.enviar_email,
    )
    rutas_email = guardar_borrador_email(email, OUTPUTS_DIR)

    envio_path = None
    resultado_envio = None
    if args.enviar_email:
        resultado_envio = enviar_email_real(email)
        envio_path = guardar_resultado_envio(
            resultado_envio,
            OUTPUTS_DIR / f"envio_email_{fecha}.json",
        )

    print("BI Reporter ejecutado correctamente.")
    print(f"Modo reporte: {modo_reporte}")
    if resumen_csv:
        print(f"Filas cargadas: {resumen_csv.get('filas', 'n/a')}")
    print(f"Fecha objetivo: {fecha}")
    print(f"Reporte Markdown generado: {output_path}")
    print(f"Email TXT generado: {rutas_email['txt']}")
    print(f"Email HTML generado: {rutas_email['html']}")
    if traza_path:
        print(f"Traza del agente generada: {traza_path}")
    if resultado_envio:
        print(f"Email enviado via Composio a: {resultado_envio['destinatario']}")
        print(f"Log de envio generado: {envio_path}")
    if not args.enviar_email:
        print("Estado email: borrador local, no enviado.")


if __name__ == "__main__":
    main()
