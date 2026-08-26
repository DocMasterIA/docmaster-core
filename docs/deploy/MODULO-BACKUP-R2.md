# Módulo — Backup independente para Cloudflare R2

**Status:** implementação inicial (scripts + runbook)  
**Data:** 2026-08-25  
**Objetivo:** cópias versionadas na nuvem dos dados críticos do DocMaster, para que quedas, volumes errados ou `compose down -v` não virem perda permanente.

A aplicação **continua a ler SQLite/volumes locais**. O R2 é camada de segurança, não o banco “vivo”.

---

## 1. O que entra no backup

| Artefato | Volume típico (prod) | Path no volume | Por quê |
|----------|----------------------|----------------|---------|
| Django SQLite | `docmaster_backend_data` | `/v/db.sqlite3` (ou sob `/app/backend/data`) | usuários, cotação, templates metadata |
| Django MEDIA | `docmaster_backend_media` | templates/docx, previews | arquivos reais dos templates |
| Índice PNCP | `docmaster_pncp_researcher_data` | `pncp_researcher_local.db` | ~4 GB itens/contratos |
| Plataformas | `docmaster-pncp_price_platform_data` | `tce_rs_local.db`, `compras_gov_local.db`, `notas_fiscais_local.db` | ~20+ GB |
| Crosslink | `docmaster-pncp_price_crosslink_data` | `price_cross_refs.db` | opcional |

**Fora do escopo deste módulo (de propósito):** Ollama weights, Grafana, Prometheus, build cache Docker.

Nomes de volume variam entre projetos Compose (`docmaster` vs `docmaster-core`). Configure em `backup-r2.env` — não hardcode só um nome.

---

## 2. Arquitetura

```
Docker volumes (produção)
  → snapshot consistente (sqlite3 .backup / tar media)
  → staging local (~/docmaster-backups/staging/<stamp>/)
  → rclone copy → Cloudflare R2 (S3-compatible)
  → prune retenção (ex. 7–14 stamps)
```

Ferramenta: **rclone** (API S3 do R2). Credenciais só no host (arquivo env + rclone.conf), nunca no git.

Custo estimado (Standard R2, ~26 GB × retenção 7): ordem **US$ 1–5/mês** (free tier 10 GB). Ver pricing Cloudflare R2.

---

## 3. Pré-requisitos (conta R2)

1. Cloudflare Dashboard → R2 → Create bucket (ex. `docmaster-backups`).
2. R2 → Manage R2 API Tokens → Create API token  
   - Object Read & Write no bucket (ou Account R2).
3. Anotar:
   - Account ID
   - Access Key ID
   - Secret Access Key
   - Endpoint: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
4. No host WSL: `rclone` instalado (`curl https://rclone.org/install.sh | sudo bash` ou pacote distro).

Configurar remote:

```bash
./scripts/backup/setup-rclone-r2.sh
# ou manual: rclone config  → New remote → s3 → Cloudflare R2
```

---

## 4. Scripts

| Script | Função |
|--------|--------|
| [`scripts/backup/setup-rclone-r2.sh`](../../scripts/backup/setup-rclone-r2.sh) | Cria remote rclone a partir do env |
| [`scripts/backup/backup-to-r2.sh`](../../scripts/backup/backup-to-r2.sh) | Snapshot + upload + prune |
| [`scripts/backup/run-daily-backup.sh`](../../scripts/backup/run-daily-backup.sh) | Wrapper agendado (espera Docker + log) |
| [`scripts/backup/install-backup-cron.sh`](../../scripts/backup/install-backup-cron.sh) | Instala/remove cron diário no WSL |
| [`scripts/windows-register-r2-backup.ps1`](../../scripts/windows-register-r2-backup.ps1) | Task Scheduler Windows (acorda WSL) |
| [`scripts/backup/resume-upload-r2.sh`](../../scripts/backup/resume-upload-r2.sh) | Retoma upload se SSH/rclone caiu (sem re-snapshot) |
| [`scripts/backup/verify-r2-backup.sh`](../../scripts/backup/verify-r2-backup.sh) | Lista stamps / confere tamanhos |
| [`scripts/backup/diagnose-volumes.sh`](../../scripts/backup/diagnose-volumes.sh) | Tamanhos dos VOL_* no Docker |
| [`scripts/backup/restore-from-r2.sh`](../../scripts/backup/restore-from-r2.sh) | Baixa stamp e restaura volumes (com confirmação) |
| [`config/backup-r2.env.example`](../../config/backup-r2.env.example) | Template de env (copiar para fora do git) |

Uso típico:

```bash
cp config/backup-r2.env.example ~/docmaster-backups/backup-r2.env
# editar volumes, bucket, remote

export BACKUP_R2_ENV=~/docmaster-backups/backup-r2.env
./scripts/backup/setup-rclone-r2.sh
./scripts/backup/backup-to-r2.sh
./scripts/backup/verify-r2-backup.sh
```

---

## 5. Agendamento automático (cron diário)

Há **duas camadas** (recomendado usar as duas no PC Windows+WSL):

| Camada | O quê | Quando usar |
|--------|--------|-------------|
| **Cron dentro do WSL** | `install-backup-cron.sh` | WSL já acordado (`vmIdleTimeout=-1`) |
| **Task Scheduler Windows** | `windows-register-r2-backup.ps1` | Garante que o WSL acorda e corre o backup mesmo sem terminal aberto |

### 5.1 Instalar cron no Linux (`docmaster`)

```bash
cd ~/docmaster-core
chmod +x scripts/backup/install-backup-cron.sh scripts/backup/run-daily-backup.sh

# Default 03:30
./scripts/backup/install-backup-cron.sh

# Ou outra hora:
./scripts/backup/install-backup-cron.sh --hour 4 --minute 0

# Remover:
./scripts/backup/install-backup-cron.sh --remove
```

Teste manual do wrapper (mesmo path do cron):

```bash
./scripts/backup/run-daily-backup.sh
tail -f ~/docmaster-backups/backup.log
```

### 5.2 Task Scheduler no Windows (recomendado no DESKTOP)

No **PowerShell do Windows**:

```powershell
cd \\wsl$\Debian\home\docmaster\docmaster-core\scripts
# Se a distro não for Debian: wsl -l -v  e use -WslDistro "Ubuntu"

powershell -ExecutionPolicy Bypass -File .\windows-register-r2-backup.ps1
# Hora default 03:30. Ex.: -Hour 4 -Minute 0
```

Teste sem esperar o dia seguinte:

```powershell
Start-ScheduledTask -TaskName "DocMaster-R2-Backup-Daily"
```

### 5.3 Linha cron (referência)

```cron
30 3 * * * BACKUP_R2_ENV=/home/docmaster/docmaster-backups/backup-r2.env \
  RCLONE_CONFIG=/home/docmaster/docmaster-backups/rclone.conf \
  BACKUP_LOG=/home/docmaster/docmaster-backups/backup.log \
  /home/docmaster/docmaster-core/scripts/backup/run-daily-backup.sh
```

Retenção: `BACKUP_KEEP_REMOTE=7` no env (stamps antigos são podados após upload ok).

---

## 6. Retenção e staging

- `BACKUP_KEEP_REMOTE=7` — quantos stamps manter no R2.
- `BACKUP_KEEP_LOCAL_STAGING=1` — após upload ok, apagar staging antigo (disco do PC é limitado).
- Snapshots SQLite usam `.backup` (consistente com WAL), não `cp` cru do `.db` aberto.

---

## 7. Restore (cuidado)

1. `verify-r2-backup.sh` — escolher stamp.
2. Parar serviços que escrevem nos volumes (`backend`, `pncp_researcher_service`, feeds).
3. `restore-from-r2.sh <stamp>` — pede confirmação digitando `RESTORE`.
4. Subir serviços; validar counts (usuários, itens PNCP, templates).

**Nunca** `docker compose down -v` “para limpar” sem restore testado.

---

## 8. Relação com outros riscos

| Problema | Este módulo |
|----------|-------------|
| Volume errado / vazio após recreate | Sim — dá para repor do R2 |
| PC off / 1033 | Não — isso é tunnel/Docker up |
| Cotação lenta | Não — módulo paralelo separado |

---

## 9. Próximos passos (após v1)

- [ ] Conta R2 + primeiro backup completo no host do cliente
- [ ] Cron diário + alerta se exit ≠ 0 (e-mail/Telegram opcional)
- [ ] `verify-prod-dbs.sh` (counts + sizes) pós-restore
- [ ] Override Compose `external: true` com nomes fixos de volume (reduz “volume errado”)
- [ ] Segundo destino (B2) só se quiserem redundância multi-cloud

---

## 10. Índice de ficheiros

```
config/backup-r2.env.example
docs/deploy/MODULO-BACKUP-R2.md          ← este ficheiro
scripts/backup/lib/common.sh
scripts/backup/setup-rclone-r2.sh
scripts/backup/backup-to-r2.sh
scripts/backup/verify-r2-backup.sh
scripts/backup/restore-from-r2.sh
```
