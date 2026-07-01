param(
    [string]$Hora = "09:00",

    [ValidateSet("hoy", "ayer")]
    [string]$FechaModo = "hoy",

    [string]$TaskName = "BI Reporter Daily Report",

    [switch]$NoEnviarEmail
)

$ErrorActionPreference = "Stop"

$Runner = Join-Path $PSScriptRoot "run_bi_reporter_daily.ps1"
if (-not (Test-Path $Runner)) {
    throw "No se encuentra el runner: $Runner"
}

$Arguments = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$Runner`"",
    "-FechaModo", $FechaModo
)

if ($NoEnviarEmail) {
    $Arguments += "-NoEnviarEmail"
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument ($Arguments -join " ")

$Trigger = New-ScheduledTaskTrigger -Daily -At $Hora
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun `
    -Hidden

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Ejecuta BI Reporter a diario y envia el reporte por email." `
    -Force | Out-Null

Write-Host "Tarea programada creada/actualizada: $TaskName"
Write-Host "Hora diaria: $Hora"
Write-Host "FechaModo: $FechaModo"
Write-Host "Modo oculto: true"
Write-Host "Despertar equipo: true"
Write-Host "LLM obligatorio: true"
Write-Host "Runner: $Runner"
Write-Host ""
Write-Host "Puedes verla en: Programador de tareas > Biblioteca del Programador de tareas"
