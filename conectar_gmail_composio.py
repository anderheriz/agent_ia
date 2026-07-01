# -*- coding: utf-8 -*-
"""Conecta Gmail a Composio mediante OAuth.

Ejecuta este script una vez, abre el enlace que imprime y autoriza tu cuenta
de Gmail. Despues BI Reporter podra enviar correos mediante Composio.
"""

from __future__ import annotations

import os

from src.config import COMPOSIO_API_KEY_ENV, COMPOSIO_USER_ID_ENV


def main() -> None:
    try:
        from composio import Composio
        from composio_openai import OpenAIProvider
    except ImportError as exc:
        raise SystemExit(
            "Faltan dependencias. Ejecuta: pip install composio composio_openai"
        ) from exc

    api_key = os.getenv(COMPOSIO_API_KEY_ENV)
    user_id = os.getenv(COMPOSIO_USER_ID_ENV)

    if not api_key:
        raise SystemExit(
            f"Falta {COMPOSIO_API_KEY_ENV}. Define la variable de entorno antes de ejecutar."
        )
    if not user_id:
        raise SystemExit(
            f"Falta {COMPOSIO_USER_ID_ENV}. Define un identificador de usuario de Composio "
            "antes de ejecutar."
        )

    composio = Composio(provider=OpenAIProvider(), api_key=api_key)
    auth_config_id = composio.toolkits._get_auth_config_id(toolkit="GMAIL")
    conexion = composio.connected_accounts.link(user_id=user_id,auth_config_id=auth_config_id,)

    print("Abre este enlace para autorizar Gmail en Composio:")
    print(conexion.redirect_url)
    print()
    print(f"User ID usado: {user_id}")
    print("Cuando termines la autorizacion, ejecuta main.py con --enviar-email.")


if __name__ == "__main__":
    main()
