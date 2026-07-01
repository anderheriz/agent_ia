# -*- coding: utf-8 -*-
"""Envio real de emails via Composio + Gmail OAuth.

Este modulo sustituye el envio SMTP. No usa app passwords ni smtplib.
Composio gestiona la autenticacion OAuth de Gmail asociada a un user_id.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import (
    COMPOSIO_API_KEY_ENV,
    COMPOSIO_GMAIL_SEND_TOOL,
    COMPOSIO_USER_ID_ENV,
)

class EmailSenderError(RuntimeError):
    """Error base del modulo de envio de email."""


class EmailConfigError(EmailSenderError):
    """Falta configuracion de Composio/Groq necesaria."""


class EmailToolCallError(EmailSenderError):
    """El modelo no pidio o no pudo ejecutar la herramienta de Gmail."""


def validar_configuracion_envio() -> dict:
    """Valida la configuracion necesaria antes de gastar tokens o enviar."""
    composio_api_key = os.getenv(COMPOSIO_API_KEY_ENV)
    composio_user_id = os.getenv(COMPOSIO_USER_ID_ENV)
    if not composio_api_key:
        raise EmailConfigError(f"Falta la variable de entorno {COMPOSIO_API_KEY_ENV}.")
    if not composio_user_id:
        raise EmailConfigError(f"Falta la variable de entorno {COMPOSIO_USER_ID_ENV}.")
    return {
        "composio_api_key": composio_api_key,
        "composio_user_id": composio_user_id,
    }


def obtener_remitente_composio(default: str | None = None) -> str | None:
    """Devuelve un remitente descriptivo para borradores/logs."""
    user_id = os.getenv(COMPOSIO_USER_ID_ENV)
    if user_id:
        return f"composio:gmail:{user_id}"
    return default


def _crear_composio(api_key: str):
    try:
        from composio import Composio
        from composio_openai import OpenAIProvider
    except ImportError as exc:
        raise EmailConfigError(
            "Faltan dependencias de Composio. Ejecuta: pip install composio composio_openai"
        ) from exc

    return Composio(provider=OpenAIProvider(), api_key=api_key)


def _limpiar_tools_composio(tools: list[dict]) -> list[dict]:
    """Elimina campos strict=None que algunos modelos rechazan."""
    for tool in tools:
        function = tool.get("function", {})
        if function.get("strict") is None and "strict" in function:
            del function["strict"]
    return tools


def _jsonable(valor: Any) -> Any:
    try:
        json.dumps(valor, ensure_ascii=False)
        return valor
    except TypeError:
        return str(valor)


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


def enviar_email_real(email: dict) -> dict:
    """Envia el email via Composio usando la herramienta de Gmail."""
    config = validar_configuracion_envio()
    composio = _crear_composio(config["composio_api_key"])

    gmail_send_tool = os.getenv("COMPOSIO_GMAIL_SEND_TOOL", COMPOSIO_GMAIL_SEND_TOOL)
    argumentos = {
        "to": email["destinatario"],
        "subject": email["asunto"],
        "body": email["cuerpo_html"],
        "is_html": True,
    }

    resultado = composio.tools.execute(
        gmail_send_tool,
        arguments=argumentos,
        user_id=config["composio_user_id"],
        dangerously_skip_version_check=True,
    )

    return {
        "estado": "enviado",
        "proveedor": "composio_gmail",
        "composio_user_id": config["composio_user_id"],
        "herramienta": gmail_send_tool,
        "destinatario": email["destinatario"],
        "asunto": email["asunto"],
        "fecha_reporte": email["fecha_reporte"],
        "argumentos_envio": {
            "to": argumentos["to"],
            "subject": argumentos["subject"],
            "is_html": argumentos["is_html"],
            "body_chars": len(argumentos["body"]),
        },
        "resultado_composio": _jsonable(resultado),
        "enviado_en": datetime.now().isoformat(timespec="seconds"),
    }


def guardar_resultado_envio(resultado: dict, output_path: Path) -> Path:
    """Guarda un log sin secretos del resultado de envio."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path
