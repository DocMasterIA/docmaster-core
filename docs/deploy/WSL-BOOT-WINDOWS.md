# WSL + Windows: site offline até abrir o terminal

## Sintoma (o seu caso)

- `docmaster-stack.service` **enabled** e **active** dentro do WSL
- Após **desligar e ligar o PC**, o site dá **1033** na Cloudflare
- Ao **abrir o WSL** (terminal), tudo volta a funcionar

## Causa

O **systemd dentro do Linux** só corre quando a **VM do WSL2 está ligada**. Por defeito, o Windows **não** inicia o WSL no boot — só quando você abre Ubuntu/Debian ou o Docker Desktop acorda a VM.

Não é falha do token nem do `install-docmaster-boot-service.sh`. Falta **acordar o WSL no login do Windows**.

## Solução em 3 passos (PC com WSL)

### 1) Impedir o WSL de “dormir” (`.wslconfig`)

No **Windows**, ficheiro `C:\Users\SEU_USUARIO_WINDOWS\.wslconfig` (troque o nome da pasta do seu user Windows):

```ini
[wsl2]
vmIdleTimeout=-1
```

Depois, no PowerShell:

```text
wsl --shutdown
```

Abra o WSL outra vez.

### 2) Docker Desktop no arranque

Docker Desktop → **Settings** → **General** → **Start Docker Desktop when you sign in to your computer**.

### 3) Tarefa agendada no Windows (acorda WSL + stack)

No **PowerShell do Windows** (não dentro do WSL):

```powershell
cd \\wsl$\Debian\home\docmaster\scripts
# Se a distro não for Debian, liste: wsl -l -v
# e use: -WslDistro "Ubuntu" no comando abaixo

powershell -ExecutionPolicy Bypass -File .\windows-register-wsl-boot.ps1 -LinuxDeploy "/home/docmaster" -LinuxUser "docmaster"
```

Teste sem reiniciar o PC:

```powershell
Start-ScheduledTask -TaskName "DocMaster-WSL-Stack"
```

No WSL:

```bash
tail -20 /home/docmaster/wsl-boot.log
docker ps | grep -E 'cloudflared|backend|frontend'
```

### 4) Confirmar systemd no WSL (se ainda não tiver)

Dentro do WSL:

```bash
cat /etc/wsl.conf
```

Deve incluir:

```ini
[boot]
systemd=true
```

Se alterar, `wsl --shutdown` no Windows e reabrir.

## Erro «ports are not available» na porta 9100

O `node_exporter` (métricas) disputa `127.0.0.1:9100` no WSL. Isso **não** deve impedir o site.

```bash
docker rm -f node_exporter 2>/dev/null || true
ss -tlnp | grep 9100 || true
cd /home/docmaster && ./scripts/ensure-docmaster-stack.sh
```

Scripts recentes sobem **backend + cloudflared** antes de Grafana/Prometheus.

## Erro «Interactive authentication required» no log

Se `wsl-boot.log` mostrar falha em `systemctl start docmaster-stack.service`, a tarefa Windows corre como `docmaster` sem sudo. O script `wsl-boot-docmaster.sh` atualizado chama **`ensure-docmaster-stack.sh`** diretamente (mesmo efeito, sem polkit). Atualize o ficheiro em `/home/docmaster/scripts/` e rode de novo:

```powershell
Start-ScheduledTask -TaskName "DocMaster-WSL-Stack"
```

O `docmaster-stack.service` no boot **Linux puro** (VPS) continua válido; no WSL a tarefa Windows substitui o arranque via `ensure-*`.

## Teste real

1. Reinicie o **Windows** (não só `wsl --shutdown`).
2. **Faça login** na sessão Windows (a tarefa dispara no logon).
3. Aguarde ~2–3 min (Docker + compose).
4. Abra o site — deve responder **sem** abrir terminal WSL.

Se o PC ligar mas **ninguém fizer login**, a tarefa “At log on” não corre. Para servidor 24/7 use **VPS Linux** ou auto-login Windows (menos recomendado).

## Produção 24/7

Para clientes sempre online: **VPS Debian** com o mesmo `install-docmaster-boot-service.sh` — lá não há WSL e o boot systemd basta.

## Referências

- [BOOT-AUTOMATICO.md](BOOT-AUTOMATICO.md) — systemd dentro do Linux
- [ESTABILIDADE-E-CLOUDFLARE.md](ESTABILIDADE-E-CLOUDFLARE.md) — erro 1033 e túnel
