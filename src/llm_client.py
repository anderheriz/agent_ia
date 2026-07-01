# -*- coding: utf-8 -*-
"""Cliente LLM compatible con APIs estilo OpenAI.

Por defecto se prepara para Groq, usando la libreria oficial de OpenAI con
un base_url compatible.
"""

from __future__ import annotations

import os

from .config import LLM_API_KEY_ENV, LLM_BASE_URL, LLM_MODELO, LLM_TEMPERATURE


class LLMConfigError(RuntimeError):
    """Error de configuracion del proveedor LLM."""


def obtener_api_key(required: bool = True, api_key_env: str = LLM_API_KEY_ENV) -> str | None:
    """Lee la API key desde variables de entorno."""
    api_key = os.getenv(api_key_env)
    if required and not api_key:
        raise LLMConfigError(
            f"No se encontro la variable de entorno {api_key_env}. "
            f"Define {api_key_env} con tu API key antes de ejecutar el agente LLM."
        )
    return api_key


def crear_cliente_llm(api_key: str | None = None, base_url: str = LLM_BASE_URL):
    """Crea el cliente OpenAI-compatible para Groq/OpenRouter/OpenAI."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMConfigError(
            "Falta instalar la libreria openai. Ejecuta: pip install openai"
        ) from exc

    api_key = api_key or obtener_api_key(required=True)
    return OpenAI(api_key=api_key, base_url=base_url)


def llamar_modelo_chat(
    mensajes: list[dict],
    cliente=None,
    modelo: str = LLM_MODELO,
    temperature: float = LLM_TEMPERATURE,
) -> str:
    """Llama al modelo mediante chat.completions."""
    cliente = cliente or crear_cliente_llm()
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=mensajes,
        temperature=temperature,
    )
    return respuesta.choices[0].message.content
