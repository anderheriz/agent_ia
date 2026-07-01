# Estructura del codigo

Esta carpeta contiene la logica del agente separada por responsabilidad:

- `config.py`: rutas, columnas obligatorias, parametros del proyecto y configuracion LLM/Composio.
- `carga_datos.py`: carga y validacion del CSV que simula el warehouse.
- `analisis_kpis.py`: calculo de KPIs y deteccion de anomalias.
- `reporte.py`: plantilla/base Markdown reutilizable por herramientas internas; el reporte final lo redacta siempre el LLM.
- `email_reporter.py`: preparacion segura del email en TXT y HTML.
- `email_sender.py`: envio real opcional via Composio + Gmail OAuth.
- `llm_client.py`: cliente OpenAI-compatible para Groq/OpenRouter/OpenAI.
- `herramientas_agente.py`: herramientas Python de negocio.
- `agente_bi_function_calling.py`: version principal con function calling nativo.

El archivo `main.py`, en la raiz del proyecto, une todos los modulos, exige `GROQ_API_KEY`, ejecuta siempre el agente LLM con function calling y genera:

- `outputs/reporte_diario_YYYY-MM-DD.md`
- `outputs/email_reporte_YYYY-MM-DD.txt`
- `outputs/email_reporte_YYYY-MM-DD.html`
- `outputs/traza_agente_YYYY-MM-DD.json` en cada ejecucion correcta, porque el LLM se usa siempre.
- `outputs/envio_email_YYYY-MM-DD.json` cuando se envia por Composio.

Por seguridad, el proyecto solo envia emails reales si se ejecuta con `--enviar-email` y Gmail ya esta autorizado en Composio.
