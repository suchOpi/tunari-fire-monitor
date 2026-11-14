param([switch]$Desactivar)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$backendRoot = Join-Path $projectRoot 'backend'
$python = Join-Path $backendRoot '.venv\Scripts\pythonw.exe'
$taskName = 'Tunari Fire Monitor - Ingesta NRT'
$envPath = Join-Path $projectRoot '.env'
$envText = [IO.File]::ReadAllText($envPath)
$intervalMatch = [regex]::Match($envText, '(?m)^NRT_INTERVAL_HOURS=(\d+)\s*$')
$hours = if ($intervalMatch.Success) { [int]$intervalMatch.Groups[1].Value } else { 3 }
if ($hours -lt 3) { throw 'El intervalo debe ser al menos de 3 horas.' }
if ($Desactivar) {
    Disable-ScheduledTask -TaskName $taskName | Out-Null
    $enabled = 'false'
} else {
    if (-not (Test-Path -LiteralPath $python)) { throw 'No se encuentra el entorno virtual existente.' }
    $userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $action = New-ScheduledTaskAction -Execute $python -Argument '-m app.workers.ingesta_nrt --once --scheduled' -WorkingDirectory $backendRoot
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours $hours)
    $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
    $options = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $options -Description 'Lote NASA NRT cada 3 h; PostGIS local, sin procesos residentes ni notificaciones externas.' -Force | Out-Null
    $enabled = 'true'
}
$flag = 'NRT_SCHEDULER_ENABLED=' + $enabled
if ($envText -match '(?m)^NRT_SCHEDULER_ENABLED=.*$') {
    $envText = [regex]::Replace($envText, '(?m)^NRT_SCHEDULER_ENABLED=.*$', $flag)
} else { $envText = $envText.TrimEnd() + "`r`n" + $flag + "`r`n" }
[IO.File]::WriteAllText($envPath, $envText, [Text.UTF8Encoding]::new($false))
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName,State
Get-ScheduledTaskInfo -TaskName $taskName | Select-Object LastRunTime,NextRunTime,LastTaskResult
Write-Output 'Reinicia FastAPI si estaba abierto para recargar la configuración. La tarea termina al finalizar cada lote.'
