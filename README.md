# BI Reporter Basebone

Agente de IA creado por el departamento de BI para generar un reporte diario accionable para el departamento de Marketing a partir de `data/warehouse.csv`, que simula un data warehouse incremental.

## Uso obligatorio del LLM

El reporte final se genera siempre con el agente LLM. Python calcula KPIs y expone herramientas, pero el LLM coordina el flujo mediante function calling y redacta el resultado final. No hay modo de ejecucion sin LLM ni fallback determinista: si falta `GROQ_API_KEY` o el LLM no respeta la estructura esperada, el proceso se detiene.

## Como ejecutarlo con Groq + function calling

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

2. Define tu API key de Groq:

```powershell
$env:GROQ_API_KEY="tu_api_key"
```

3. Ejecuta el agente:

```bash
python main.py --fecha 2026-06-29
```

El flag `--usar-llm` se conserva solo por compatibilidad, pero ya no cambia el comportamiento porque el LLM se usa siempre.

El modelo no recibe el CSV entero. El agente usa function calling nativo (`tools` y `tool_calls`) para pedir herramientas Python de BI:

- `analizar_dia_bi`
- `obtener_top_canales`
- `obtener_top_aliases`
- `obtener_anomalias`
## Generacion diaria de outputs

Los archivos de `outputs/` no se precrean para fechas futuras. Cada ejecucion genera solamente el Markdown, TXT, HTML, traza y log de envio de la fecha objetivo. Para simular un warehouse realista, `main.py` bloquea fechas futuras: si hoy es `2026-06-30`, no permite generar `2026-07-01` hasta que llegue ese dia.

Aunque el CSV de bootcamp pueda contener filas futuras simuladas para facilitar demos, el comportamiento del agente se mantiene incremental: el reporte se materializa justo antes del envio automatico diario.

## Como conectar Gmail con Composio

El proyecto usa Composio como unica via de envio real de email. Ya no usa SMTP ni app passwords de Gmail.

1. Crea una API key gratuita en Composio.
2. Define las variables:

```powershell
$env:COMPOSIO_API_KEY="comp_..."
$env:COMPOSIO_USER_ID="tu_usuario_composio"
$env:EMAIL_DESTINO="marketing@example.com"
```

3. Autoriza Gmail una vez:

```powershell
python conectar_gmail_composio.py
```

Abre el enlace que imprime y concede permisos a Gmail.

## Como enviar el email real por Gmail via Composio

```powershell
$env:GROQ_API_KEY="tu_api_key_de_groq"
$env:COMPOSIO_API_KEY="comp_..."
$env:COMPOSIO_USER_ID="tu_usuario_composio"
$env:EMAIL_DESTINO="marketing@example.com"

python main.py --fecha 2026-06-29 --enviar-email
```

Cuando se envia correctamente, se genera tambien:

```text
outputs/envio_email_YYYY-MM-DD.json
```

Ese log no guarda claves ni secretos.

## Seguridad de credenciales

Las claves de Groq y Composio nunca se pasan al modelo. El LLM solo pide herramientas; Python y Composio ejecutan esas herramientas usando variables de entorno y OAuth.
