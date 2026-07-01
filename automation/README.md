# Automatizacion diaria de BI Reporter

Estos scripts automatizan la ejecucion diaria con Windows Task Scheduler. La tarea no precrea outputs futuros: genera los archivos del dia objetivo justo antes de preparar o enviar el email.

## 1. Configurar variables de entorno de usuario

Ejecuta esto una vez en PowerShell, sustituyendo los valores secretos:

```powershell
[Environment]::SetEnvironmentVariable("GROQ_API_KEY", "tu_api_key_de_groq", "User")
[Environment]::SetEnvironmentVariable("COMPOSIO_API_KEY", "comp_...", "User")
[Environment]::SetEnvironmentVariable("COMPOSIO_USER_ID", "tu_usuario_composio", "User")
[Environment]::SetEnvironmentVariable("EMAIL_DESTINO", "marketing@example.com", "User")
```

Cierra PowerShell y abre una terminal nueva para que Windows cargue esas variables. `GROQ_API_KEY` es obligatoria siempre porque BI Reporter ya no tiene modo sin LLM. Las variables de Composio solo son necesarias cuando se envia el email real. `EMAIL_DESTINO` define la cuenta que recibira el reporte.

## 2. Autorizar Gmail en Composio

Desde la raiz del proyecto:

```powershell
python conectar_gmail_composio.py
```

Abre el enlace que imprime y concede permisos a Gmail. Esto se hace una sola vez por `COMPOSIO_USER_ID`.

## 3. Probar manualmente antes de programar

Desde la raiz del proyecto, primero prueba el flujo completo del agente LLM sin enviar email real:

```powershell
.\automation\run_bi_reporter_daily.ps1 -FechaModo hoy -NoEnviarEmail
```

Para hacer una prueba real con envio por Gmail/Composio:

```powershell
.\automation\run_bi_reporter_daily.ps1 -FechaModo hoy
```

No existe modo `-SinLLM`: el reporte siempre lo redacta el agente LLM con function calling.

## 4. Registrar la tarea diaria

Por defecto se programa a las 09:00 y usa la fecha de hoy. Esto imita un warehouse incremental en el que los datos se cargan dia a dia:

```powershell
.\automation\register_daily_task.ps1 -Hora "09:00" -FechaModo hoy
```

Si prefieres que el reporte sea de ayer:

```powershell
.\automation\register_daily_task.ps1 -Hora "09:00" -FechaModo ayer
```

## 5. Nota si ya existia la tarea antigua

Si ya tenias programada la tarea anterior, registra de nuevo la tarea con `register_daily_task.ps1` para que Windows apunte al runner `run_bi_reporter_daily.ps1`.

## 6. Logs

Cada ejecucion deja un log en:

```text
outputs\automation_logs\
```

El envio correcto tambien crea:

```text
outputs\envio_email_YYYY-MM-DD.json
```

## 7. Borrar la tarea programada

```powershell
Unregister-ScheduledTask -TaskName "BI Reporter Daily Report" -Confirm:$false
```
