# Regista tarefa diária no Windows para backup R2 (acorda WSL + corre o script).
#
# Execute no PowerShell do Windows (utilizador que faz login no PC):
#   cd \\wsl$\Debian\home\docmaster\docmaster-core\scripts
#   powershell -ExecutionPolicy Bypass -File .\windows-register-r2-backup.ps1
#
# Ajusta -WslDistro se não for a distro default (wsl -l -v).

param(
    [string]$TaskName = "DocMaster-R2-Backup-Daily",
    [string]$WslDistro = "",
    [string]$LinuxUser = "docmaster",
    [string]$LinuxDeploy = "/home/docmaster/docmaster-core",
    [int]$Hour = 3,
    [int]$Minute = 30
)

$ErrorActionPreference = "Stop"

$runner = "$LinuxDeploy/scripts/backup/run-daily-backup.sh"
$bashCmd = "BACKUP_R2_ENV=`$HOME/docmaster-backups/backup-r2.env RCLONE_CONFIG=`$HOME/docmaster-backups/rclone.conf $runner"

$wslArgs = @()
if ($WslDistro) { $wslArgs += @("-d", $WslDistro) }
$wslArgs += @("-u", $LinuxUser, "-e", "bash", "-lc", $bashCmd)

$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument ($wslArgs -join " ")

# Diário à hora local do Windows
$trigger = New-ScheduledTaskTrigger -Daily -At ("{0:D2}:{1:D2}" -f $Hour, $Minute)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Backup diario DocMaster -> Cloudflare R2 (snapshot volumes + upload)" `
    -Force | Out-Null

Write-Host "OK  Tarefa agendada: $TaskName"
Write-Host "    Hora: ${Hour}:$($Minute.ToString('00')) (hora do Windows)"
Write-Host "    wsl.exe $($wslArgs -join ' ')"
Write-Host ""
Write-Host "Requisitos:"
Write-Host "  - ~/docmaster-backups/backup-r2.env e rclone.conf no user $LinuxUser"
Write-Host "  - Docker Desktop a correr (ou a acordar com o login)"
Write-Host "  - Preferivel: C:\Users\$env:USERNAME\.wslconfig -> vmIdleTimeout=-1"
Write-Host ""
Write-Host "Teste agora: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Log WSL:     tail -f /home/$LinuxUser/docmaster-backups/backup.log"
Write-Host "Ver R2:      wsl -u $LinuxUser -- bash -lc 'cd $LinuxDeploy && ./scripts/backup/verify-r2-backup.sh'"
