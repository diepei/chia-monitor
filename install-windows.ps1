[CmdletBinding()]
param(
    [string]$InstallDirectory = "$env:LOCALAPPDATA\ChiaMonitor",
    [switch]$ConfigureTailscale
)

$ErrorActionPreference = "Stop"
$Repository = "diepei/chia-monitor"
$AssetName = "chia-monitor-windows-x86_64.exe"
$TaskName = "Chia Monitor Agent"

function Stop-WithMessage([string]$Message) {
    Write-Error $Message
    exit 1
}

function Stop-InstalledAgent([string]$ExecutablePath) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    }

    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        $processes = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $ExecutablePath })
        if ($processes.Count -eq 0) {
            return $task
        }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)

    $processes | Invoke-CimMethod -MethodName Terminate | Out-Null
    Start-Sleep -Seconds 1
    $remaining = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $ExecutablePath })
    if ($remaining.Count -gt 0) {
        Stop-WithMessage "Could not stop the existing Chia Monitor process."
    }
    return $task
}

if (-not [Environment]::Is64BitOperatingSystem) {
    Stop-WithMessage "Chia Monitor currently requires 64-bit Windows."
}

$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repository/releases/latest" -Headers @{ "User-Agent" = "ChiaMonitorInstaller" }
$asset = $release.assets | Where-Object { $_.name -eq $AssetName } | Select-Object -First 1
$checksums = $release.assets | Where-Object { $_.name -eq "SHA256SUMS" } | Select-Object -First 1
if (-not $asset -or -not $checksums) {
    Stop-WithMessage "The latest release does not contain the Windows agent and checksum."
}

New-Item -ItemType Directory -Path $InstallDirectory -Force | Out-Null
$exePath = Join-Path $InstallDirectory "chia-monitor.exe"
$downloadPath = Join-Path $env:TEMP "chia-monitor-download.exe"
$checksumPath = Join-Path $env:TEMP "chia-monitor-SHA256SUMS"

Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $downloadPath
Invoke-WebRequest -Uri $checksums.browser_download_url -OutFile $checksumPath
$expected = ((Get-Content $checksumPath | Where-Object { $_ -match [regex]::Escape($AssetName) }) -split "\s+")[0].ToLower()
$actual = (Get-FileHash $downloadPath -Algorithm SHA256).Hash.ToLower()
if (-not $expected -or $actual -ne $expected) {
    Stop-WithMessage "Checksum verification failed. The downloaded executable was not installed."
}
$existingTask = Stop-InstalledAgent $exePath
$backupPath = $null
if (Test-Path $exePath) {
    $backupPath = "$exePath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Move-Item -LiteralPath $exePath -Destination $backupPath
    Write-Host "Previous agent saved as: $backupPath"
}
try {
    Move-Item -LiteralPath $downloadPath -Destination $exePath
} catch {
    if ($backupPath -and (Test-Path $backupPath) -and -not (Test-Path $exePath)) {
        Move-Item -LiteralPath $backupPath -Destination $exePath
    }
    if ($existingTask) {
        Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    }
    throw
}

$configPath = Join-Path $InstallDirectory "config.yaml"
if (-not (Test-Path $configPath)) {
    & $exePath --init-config --config $configPath --chia-root "$env:USERPROFILE\.chia\mainnet"
}

$action = New-ScheduledTaskAction -Execute $exePath -Argument "--config `"$configPath`"" -WorkingDirectory $InstallDirectory
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

Write-Host ""
Write-Host "Chia Monitor is installed and running." -ForegroundColor Green
Write-Host "Configuration: $configPath"
Write-Host "Local check: http://127.0.0.1:8926/healthz"

if ($ConfigureTailscale) {
    $tailscale = Get-Command tailscale.exe -ErrorAction SilentlyContinue
    if (-not $tailscale) {
        Write-Warning "Tailscale was not found. Install it, sign in, then run: tailscale serve --bg localhost:8926"
    } else {
        & $tailscale.Source serve --bg localhost:8926
        $status = & $tailscale.Source status --json | ConvertFrom-Json
        $dnsName = $status.Self.DNSName.TrimEnd(".")
        if ($dnsName) {
            Write-Host "Scriptable URL: https://$dnsName" -ForegroundColor Cyan
        }
    }
} else {
    Write-Host ""
    Write-Host "For private iPhone access, install Tailscale and run this in an Administrator PowerShell:"
    Write-Host "  tailscale serve --bg localhost:8926"
}

Write-Host ""
Write-Host "Open config.yaml to copy api_token and add your farm drive letters."
