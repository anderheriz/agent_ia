param(
    [ValidateSet("hoy", "ayer")]
    [string]$FechaModo = "hoy",

    [string]$Fecha = "",

    [switch]$NoEnviarEmail
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$MainPy = Join-Path $ProjectDir "main.py"
$LogsDir = Join-Path $ProjectDir "outputs\automation_logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

if (-not $Fecha) {
    if ($FechaModo -eq "ayer") {
        $Fecha = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
    } else {
        $Fecha = (Get-Date).ToString("yyyy-MM-dd")
    }
}

$PythonExe = "python"
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
}

$Missing = @()
if (-not $env:GROQ_API_KEY) { $Missing += "GROQ_API_KEY" }
if (-not $NoEnviarEmail) {
    if (-not $env:COMPOSIO_API_KEY) { $Missing += "COMPOSIO_API_KEY" }
    if (-not $env:COMPOSIO_USER_ID) { $Missing += "COMPOSIO_USER_ID" }
}

if ($Missing.Count -gt 0) {
    throw "Faltan variables de entorno: $($Missing -join ', '). Configuralas como variables de usuario y abre una nueva terminal."
}

$ArgsList = @($MainPy, "--fecha", $Fecha, "--usar-llm")

if (-not $NoEnviarEmail) {
    $ArgsList += "--enviar-email"
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogsDir "bi_reporter_$Timestamp.log"

Set-Location $ProjectDir

"[$(Get-Date -Format s)] Inicio BI Reporter. Fecha=$Fecha FechaModo=$FechaModo" | Tee-Object -FilePath $LogFile
& $PythonExe @ArgsList 2>&1 | Tee-Object -FilePath $LogFile -Append
$ExitCode = $LASTEXITCODE
"[$(Get-Date -Format s)] Fin BI Reporter. ExitCode=$ExitCode" | Tee-Object -FilePath $LogFile -Append

exit $ExitCode
