# Regista tarefa no Windows para subir DocMaster ao iniciar sessão (WSL não sobe sozinho).
#
# Execute no PowerShell do Windows (como utilizador que faz login no PC):
#   cd \\wsl$\Ubuntu\home\docmaster\docmaster-core\scripts
#   powershell -ExecutionPolicy Bypass -File .\windows-register-wsl-boot.ps1 `
#     -WslDistro "Ubuntu" -LinuxDeploy "/home/docmaster/docmaster-core" -LinuxUser "docmaster"
#
# Limite: se o PC desligar, o site CAI (Tailscale não mantém Docker). Para 24/7 real → VPS.

param(
    [string]$TaskName = "DocMaster-WSL-Stack",
    [string]$WslDistro = "Ubuntu",
    [string]$LinuxUser = "docmaster",
    [string]$LinuxDeploy = "/home/docmaster/docmaster-core"
)

$ErrorActionPreference = "Stop"

$bootScript = "$LinuxDeploy/scripts/wsl-boot-docmaster.sh"
$wslArgs = @()
if ($WslDistro) { $wslArgs += @("-d", $WslDistro) }
$wslArgs += @("-u", $LinuxUser, "-e", "bash", "-lc", "$bootScript")

$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument ($wslArgs -join " ")

# Ao iniciar sessão Windows (WSL acorda aqui — é o que faltava vs. só systemd dentro do Linux)
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Reforço: 2 min após boot (se já estiver com sessão / auto-login)
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
    -Description "Acorda WSL e inicia docmaster-stack (evita Cloudflare 1033 após ligar o PC)" `
    -Force | Out-Null

Write-Host "OK  Tarefa agendada: $TaskName"
Write-Host "    wsl.exe $($wslArgs -join ' ')"
Write-Host ""
Write-Host "Também configure no Windows:"
Write-Host "  1) C:\Users\$env:USERNAME\.wslconfig  ->  vmIdleTimeout=-1"
Write-Host "  2) Docker Desktop -> Start when you sign in"
Write-Host "  3) wsl --shutdown  (uma vez) e reabrir WSL após editar .wslconfig"
Write-Host ""
Write-Host "Teste: Start-ScheduledTask -TaskName $TaskName"
Write-Host "Log WSL: tail -f $LinuxDeploy/wsl-boot.log"
