# Deploy de templates DOCX e `rag_service`

Como publicar alterações de **código Python** e **arquivos `.docx`** em `template_packages/` na VPS de produção.

---

## Por que `git pull` + recreate não basta

O `rag_service` é construído via Docker. O `Dockerfile` **copia** `template_packages/` para dentro da imagem no build:

```dockerfile
COPY template_packages/ /app/template_packages/
```

| Comando | Atualiza código Python? | Atualiza DOCX do template? |
|---------|-------------------------|----------------------------|
| `docker compose up -d --force-recreate rag_service` | Só se imagem já foi rebuild | **Não** |
| `docker compose build rag_service` + up | **Sim** | **Sim** |

Sem `build`, o container usa a imagem antiga com templates antigos.

---

## Procedimento completo (VPS)

Ambiente típico: usuário `docmaster`, compose em `~/docker-compose.yml`, repo em `~/docmaster-core`.

```bash
cd ~/docmaster-core && git pull

cd ~
docker compose build rag_service
docker compose up -d --force-recreate rag_service
```

### Se houve mudança no frontend Vue

Slots, formulários e dados fixos exigem rebuild do `frontend-vue`:

```bash
docker compose build frontend-vue
docker compose up -d --force-recreate frontend-vue
```

### Comando combinado

```bash
cd ~/docmaster-core && git pull
cd ~
docker compose build rag_service frontend-vue
docker compose up -d --force-recreate rag_service frontend-vue
```

---

## Verificar que o código novo está na imagem

```bash
docker exec rag_service sh -c \
  'PYTHONPATH=/app python -c "from rag_service.app.docx_typography import ensure_signature_nome_blank_lines; print(\"ok\")"'
```

Saída esperada: `ok`

Para inspecionar data de build da imagem:

```bash
docker inspect rag_service --format '{{.Image}}'
docker images --format '{{.ID}} {{.CreatedAt}}' | head
```

---

## Onde ficam os templates

```
template_packages/
  lei_14133/
    dispensa_75_ii_compras/
      TR_modelo_base.docx
      DFD_modelo_base.docx
      OFICIO_modelo_base.docx
    dispensa_75_ii_servicos/
    dispensa_75_i_obras_engenharia/
    ...
  tr_base/
```

O pacote é escolhido pelo frontend via `slot_package_key` (ver [01-slots-tr-dfd-oficio.md](./01-slots-tr-dfd-oficio.md)).

---

## Merge com biblioteca de modelos (Django)

Após o RAG gerar o DOCX, o backend pode aplicar `merge_docx_with_template_body()` (`backend/app/services/services.py`) para combinar com capa/cabeçalho da biblioteca do tenant.

Esse merge **substitui o corpo** do documento da biblioteca pelo corpo gerado pelo RAG. Não deve alterar o espaçamento interno já normalizado no corpo RAG — desde que o merge preserve parágrafos do corpo fonte.

Se o espaçamento da assinatura voltar a falhar **só** em documentos com biblioteca, investigar esse merge separadamente.

---

## Logs úteis

```bash
docker compose logs --tail 80 rag_service
docker compose ps rag_service
```

---

## Checklist pós-deploy

- [ ] `git pull` sem conflitos
- [ ] `build` do(s) serviço(s) alterado(s)
- [ ] `force-recreate` aplicado
- [ ] Import Python de novas funções retorna `ok`
- [ ] Gerar TR de teste com data normal e com «datado e assinado digitalmente»
- [ ] Conferir 3 linhas entre cidade e nome no Word
- [ ] Conferir DFD seção 2.1 (setor requisitante)

---

## Referências

- [deploy/README.md](../deploy/README.md) — índice operacional geral
- [CHANGELOG-2026-06.md](./CHANGELOG-2026-06.md)
