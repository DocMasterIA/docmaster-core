# Geração de documentos (TR / DFD / Ofício)

Documentação das correções e convenções aplicadas em **junho/2026** no pipeline de geração DOCX da Dispensa Art. 75, II (e pacotes relacionados).

## Índice

| Documento | Conteúdo |
|-----------|----------|
| [../SISTEMA-DOCMASTER-VISAO-COMPLETA.md](../SISTEMA-DOCMASTER-VISAO-COMPLETA.md) | **Mapa mestre** do sistema inteiro |
| [01-slots-tr-dfd-oficio.md](./01-slots-tr-dfd-oficio.md) | Mapeamento slots ↔ placeholders ↔ `rag_service` |
| [02-dfd-setor-requisitante.md](./02-dfd-setor-requisitante.md) | Correção do slot `(DFD_SETOR_REQUISITANTE)` |
| [03-docx-tipografia-e-assinatura.md](./03-docx-tipografia-e-assinatura.md) | Justificação automática e 3 linhas antes do nome |
| [04-deploy-templates-docx.md](./04-deploy-templates-docx.md) | Como publicar templates e código na VPS |
| [CHANGELOG-2026-06.md](./CHANGELOG-2026-06.md) | Resumo cronológico: problema → solução → status |
| [TR_MODELO_BASE_ANALISE.md](./TR_MODELO_BASE_ANALISE.md) | Análise estrutural do modelo TR |
| [INGESTAO_GUIA_ETP_DFD_TR.md](./INGESTAO_GUIA_ETP_DFD_TR.md) | Ingestão RAG de ETP/DFD/TR |

## Arquivos de código principais

| Área | Caminho |
|------|---------|
| Tipografia DOCX | `rag_service/app/docx_typography.py` |
| Template TR | `rag_service/app/tr_template.py` |
| Template DFD | `rag_service/app/dfd_template.py` |
| Template Ofício | `rag_service/app/oficio_template.py` |
| Sanitização DFD | `rag_service/app/dfd_slot_sanitize.py` |
| Merge slots + IA | `rag_service/app/tr_slots_llm.py` |
| Formulário normal | `frontend-vue/src/components/dispensa-art-75-ii/DispensaArt75IINormalForm.vue` |
| Formulário rápido | `frontend-vue/src/components/dispensa-art-75-ii/DispensaArt75IIRapidaForm.vue` |
| Helpers compartilhados | `frontend-vue/src/components/dispensa-art-75-ii/dispensaArt75iiShared.js` |
| Templates DOCX | `template_packages/lei_14133/<pacote>/` |

## Testes automatizados

```bash
cd rag_service
pytest tests/test_signature_nome_spacing.py tests/test_docx_typography.py tests/test_dfd_slot_sanitize.py -v
```

## Ordem do pipeline de render (RAG)

1. Substituição de placeholders nos parágrafos do modelo.
2. Inserção de tabelas, cláusulas IA, quebras de parágrafo.
3. `apply_standard_body_font_to_document()` — fonte padrão do corpo.
4. `apply_default_justify_to_document()` — justificação sem sobrescrever alinhamentos explícitos.
5. `ensure_signature_nome_blank_lines()` — **último passo**: normaliza 3 linhas vazias entre cidade/data e nome.
