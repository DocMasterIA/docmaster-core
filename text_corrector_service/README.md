# Text Corrector Service (initial composition)

Microserviço FastAPI para correção textual PT-BR com:

- normalização básica;
- dicionário custom de erros recorrentes;
- integração com LanguageTool (`/v2/check`);
- regras determinísticas simples de pós-processamento.

## Endpoints

- `GET /health`
- `POST /correct`

### Exemplo de request

```json
{
  "text": "Atenção: Este texto foi gerado com base em instruções. mantẽncao da indendidaud.",
  "mode": "generic",
  "language": "pt-BR"
}
```

### Exemplo de resposta

```json
{
  "ok": true,
  "corrected_text": "manutenção da identidade.",
  "warnings": [],
  "changes": [
    {"from_text":"mantẽncao","to_text":"manutenção","rule":"custom_dictionary"},
    {"from_text":"indendidaud","to_text":"identidade","rule":"custom_dictionary"},
    {"from_text":"Atenção:","to_text":"","rule":"post_rule:strip_atencao_prefix"}
  ],
  "language_tool_applied": true
}
```

## Run local (standalone)

```bash
docker build -t text-corrector -f text_corrector_service/Dockerfile .
docker run --rm -p 8011:8011 \
  -e LANGUAGETOOL_BASE_URL=http://host.docker.internal:8010 \
  text-corrector
```

## Env vars

- `LANGUAGETOOL_BASE_URL` (default: `http://languagetool:8010`)
- `LANGUAGETOOL_CHECK_PATH` (default: `/v2/check`)
- `CORRECTOR_HTTP_TIMEOUT` (default: `20`)
