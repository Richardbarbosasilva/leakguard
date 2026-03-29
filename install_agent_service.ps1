param(
    [string]$ServiceName = "ScreenshotAuditAgent",
    [string]$BinaryPath = "C:\Program Files\ScreenshotAudit\ScreenshotAuditAgent.exe",
    [string]$ConfigPath = "C:\Program Files\ScreenshotAudit\agent_config.json",
    [string]$NssmPath = "C:\Tools\nssm\nssm.exe",
    [string]$ProgramDataRoot = "$env:ProgramData\ScreenshotAudit"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $NssmPath)) {
    throw "NSSM nao encontrado em $NssmPath"
}

if (-not (Test-Path $BinaryPath)) {
    throw "Executavel nao encontrado em $BinaryPath"
}

if (-not (Test-Path $ConfigPath)) {
    throw "Config nao encontrada em $ConfigPath"
}

New-Item -ItemType Directory -Force -Path $ProgramDataRoot | Out-Null
New-Item -ItemType Directory -Force -Path "$ProgramDataRoot\logs" | Out-Null

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    & $NssmPath stop $ServiceName | Out-Null
    & $NssmPath remove $ServiceName confirm | Out-Null
}

& $NssmPath install $ServiceName $BinaryPath | Out-Null
& $NssmPath set $ServiceName AppDirectory (Split-Path -Path $BinaryPath -Parent) | Out-Null
& $NssmPath set $ServiceName AppParameters "--config `"$ConfigPath`"" | Out-Null
& $NssmPath set $ServiceName Start SERVICE_AUTO_START | Out-Null
& $NssmPath set $ServiceName AppStdout "$ProgramDataRoot\logs\service-stdout.log" | Out-Null
& $NssmPath set $ServiceName AppStderr "$ProgramDataRoot\logs\service-stderr.log" | Out-Null

Start-Service $ServiceName
Get-Service $ServiceName
