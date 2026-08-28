# Regista tarefa no Windows para subir DocMaster ao iniciar sessão (WSL não sobe sozinho).
#
# Execute no PowerShell do Windows (utilizador que faz login no PC):
#   cd \\wsl$\Ubuntu\home\docmaster\docmaster-core\scripts
#   powershell -ExecutionPolicy Bypass -File .\windows-register-wsl-boot.ps1 -WslDistro "Ubuntu"
#
# Requer: WSL Ubuntu, user docmaster, repo em /home/docmaster/docmaster-core, Docker Desktop no login.

param(
    [string]$TaskName = "DocMaster-WSL-Stack",
    [string]$WslDistro = "Ubuntu",
    [string]$LinuxUser = "docmaster",
    [string]$LinuxDeploy = "/home/docmaster/docmaster-core"
)

$ErrorActionPreference = "Stop"

$bootScript = "$LinuxDeploy/scripts/wsl-boot-docmaster.sh"
# Uma string só para bash -lc (Task Scheduler parte argumentos sem aspas)
$bashCmd = "DOCMASTER_DEPLOY_DIR=$LinuxDeploy $bootScript"

$argParts = @()
if ($WslDistro) { $argParts += @("-d", $WslDistro) }
$argParts += @("-u", $LinuxUser, "-e", "bash", "-lc")
$argString = ($argParts -join " ") + " `"$bashCmd`""

$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument $argString

# Ao iniciar sessão Windows (WSL acorda aqui)
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Reforço: 2 min após boot
$triggerBoot = New-ScheduledTaskTrigger -AtStartup
$triggerBoot.Delay = "PT2M"

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($triggerLogon, $triggerBoot) `
    -Settings $settings `
    -Description "Acorda WSL Ubuntu + Docker stack DocMaster (evita Cloudflare 1033 apos ligar o PC)" `
    -Force | Out-Null

Write-Host "OK  Tarefa agendada: $TaskName"
Write-Host "    wsl.exe $argString"
Write-Host ""
Write-Host "Tambem configure no Windows:"
Write-Host "  1) C:\Users\$env:USERNAME\.wslconfig  ->  vmIdleTimeout=-1"
Write-Host "  2) Docker Desktop -> Start when you sign in to your computer"
Write-Host "  3) wsl --shutdown  (uma vez) e reabrir WSL apos editar .wslconfig"
Write-Host ""
Write-Host "Teste: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Log:   wsl -d $WslDistro -u $LinuxUser -- tail -30 $LinuxDeploy/wsl-boot.log"
Write-Host "Check: wsl -d $WslDistro -u $LinuxUser -- docker ps --format '{{.Names}} {{.Status}}'"
