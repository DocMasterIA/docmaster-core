# Guia de Slots TR/DFD

Este documento centraliza o mapeamento entre:

- campos do card `Dados do assistente (slots)` no frontend;
- chaves enviadas em `slots_override`;
- placeholders no `TR_modelo_base.docx` e `DFD_modelo_base.docx`;
- aplicação no `rag_service`.

---

## Fluxo resumido

1. Frontend (`DocumentGenerator.vue`) monta `slots_override`.
2. Frontend envia também `slot_package_key` conforme a rota (pacote de documentos).
3. Backend Django repassa `slots_override` + `slot_package_key` para o `rag_service` (em `context`).
4. `rag_service/app/tr_slots_llm.py` faz merge IA + override.
5. `tr_template.py` e `dfd_template.py` substituem placeholders no DOCX.

---

## Pacotes por rota (`slot_package_key`)

Para suportar múltiplos pacotes de TR/DFD/Ofício por página:

- `DispensaArt75IManutencaoVeiculos` -> `dispensa_75_i_manutencao_veiculos`
- `DispensaArt75IObrasEngenharia` -> `dispensa_75_i_obras_engenharia`
- `DispensaArt75IICompras` -> `dispensa_75_ii_compras`
- `DispensaArt75IIServicos` -> `dispensa_75_ii_servicos`
- `DispensaArt75IIComprasServicosInclusos` -> `dispensa_75_ii_compras_servicos_inclusos`
- `InexigibilidadeArt74IShowArtistico` -> `inexigibilidade_74_i_show_artistico`
- `EtpLivre` -> `etp_livre`
- fallback -> `tr_dfd_generico`

---

## Padrão oficial de placeholders

Adotar sempre:

- prefixo por documento (`TR_`, `DFD_`, `SOL_OFICIO_`);
- caixa alta;
- palavras separadas por `_`;
- texto entre parênteses no DOCX.

Ex.: `(TR_OBJETO)`, `(DFD_EMAIL)`, `(SOL_OFICIO_DESTINATARIO_NOME)`.

---

## TR - Placeholders e slots

### Placeholders padronizados TR (preferenciais)

- `(TR_OBJETO)` -> `objeto`
- `(TR_DISPENSA_INCISO)` -> `dispensa.inciso`
- `(TR_JUSTIFICATIVA)` -> `justificativa`
- `(TR_FISCAL_NOME)` -> `fiscal.nome`
- `(TR_DOTACAO)` -> `dotacao`
- `(TR_CIDADE)` -> `cidade`
- `(TR_CODIGO_UF)` -> `codigo_uf`
- `(TR_CIDADE_ESTADO)` -> `cidade_estado`
- `(TR_SECRETARIA_USUARIO)` -> `secretaria_usuario`
- `(TR_NOME_USUARIO)` -> `nome_usuario`
- `(TR_ENDERECO_ENTREGA)` -> `endereco_entrega`
- `(TR_EMAIL_ENVIO_PROPOSTAS)` -> `email_envio_propostas`
- `(TR_DATA_TERMO)` -> `data_termo`
- `(TR_NOME_ASSINANTE_TERMO)` -> `nome_assinante_termo`
- `(TR_CARGO_ASSINANTE_TERMO)` -> `cargo_assinante_termo`
- `(TR_TABELA_ITENS)` -> âncora de posicionamento da tabela de itens (não é valor textual)

### Placeholders legados TR (compatibilidade)

- `(descrever o objeto solicitado)` -> `objeto`
- `(descrever o artigo de acordo com objeto)` -> `dispensa.inciso`
- `(Formalizar justificava de acordo com objeto solicitado)` -> `justificativa`
- `(Inserir o inciso de acordo com o objeto solicitado)` -> `dispensa.inciso`
- `(inserir nome do fiscal)` -> `fiscal.nome`
- `(Inserir Dotação)` -> `dotacao`
- `(CIDADE)` -> `cidade`
- `(CÓDIGO UF)` -> `codigo_uf`
- `(CIDADE - ESTADO)` -> `cidade_estado`
- `(SECRETARIA DO USUARIO)` -> `secretaria_usuario`
- `(Nome do USUARIO)` -> `nome_usuario`
- `(TR_OBJETO_MANUAL)` -> `objeto`
- `(TR_BENEFICIO_ESPERADO)` -> `justificativa` (fallback provisório)
- `(TR_PROBLEMA_ADMINISTRATIVO)` -> `justificativa` (fallback provisório)

## DFD - Placeholders e slots

### Placeholders padronizados DFD (preferenciais)

- `(DFD_OBJETO_REFERENCIA)` -> `objeto`
- `(DFD_JUSTIFICATIVA)` -> `justificativa`
- `(DFD_CIDADE)` -> `cidade`
- `(DFD_SETOR_REQUISITANTE)` -> `dfd_setor_requisitante`
- `(DFD_NUMERO_PROCESSO)` -> `dfd_numero_processo`
- `(DFD_RESPONSAVEL_DEMANDA)` -> `dfd_responsavel_demanda`
- `(DFD_EMAIL)` -> `dfd_email`
- `(DFD_GESTOR_CONTRATOS)` -> `dfd_gestor_contratos`
- `(DFD_FISCAL_CONTRATOS)` -> `dfd_fiscal_contratos`
- `(DFD_CARGO_ASSINATURA)` -> `dfd_assinatura_cargo`
- `(DFD_NOME_ASSINATURA)` -> `dfd_assinatura_nome`
- `(DFD_DATA)` -> `dfd_data`

### Placeholders legados DFD (compatibilidade)

- `(Descrever objeto do termo de referencia)` -> `objeto`
- `(descrever a justificativa usada no termo de referencias)` -> `justificativa`
- `(CIDADE)` -> `cidade`

---

## Solicitação / Ofício - esquema de slots (pré-template)

Ainda sem documento base oficial de Solicitação/Ofício no pipeline, mas o esquema
já pode ficar padronizado para integração futura.

### Campos do card e chaves sugeridas

- `solicitacao_destinatario_nome` -> `sol_oficio_destinatario_nome`
- `solicitacao_destinatario_cargo` -> `sol_oficio_destinatario_cargo`
- `solicitacao_responsavel_nome` -> `sol_oficio_responsavel_nome`
- `solicitacao_responsavel_cargo` -> `sol_oficio_responsavel_cargo`

### Placeholders sugeridos para o futuro DOCX

- `(SOL_OFICIO_DESTINATARIO_NOME)` -> `sol_oficio_destinatario_nome`
- `(SOL_OFICIO_DESTINATARIO_CARGO)` -> `sol_oficio_destinatario_cargo`
- `(SOL_OFICIO_RESPONSAVEL_NOME)` -> `sol_oficio_responsavel_nome`
- `(SOL_OFICIO_RESPONSAVEL_CARGO)` -> `sol_oficio_responsavel_cargo`

### Estratégia

Enquanto não existir template de Solicitação/Ofício:

- manter essas chaves no `slots_override` e no bloco de contexto do prompt;
- não aplicar substituição em DOCX (sem placeholders no modelo);
- quando o documento existir, adicionar mapping no renderer correspondente.

---

## Frontend -> slots_override (referência)

Campos principais do card:

- `tr_endereco_propostas` -> `endereco_entrega`
- `tr_email_propostas` -> `email_envio_propostas`
- `tr_data_termo` / `tr_data_automatica` -> `data_termo`
- `tr_assinatura_digital` -> sufixa `data_termo` com `", datado e assinado digitalmente"` (ou define apenas esse texto quando não há data)
- `tr_nome_assinante` -> `nome_assinante_termo`
- `tr_cargo_assinante` -> `cargo_assinante_termo`
- `dfd_setor_requisitante` -> `dfd_setor_requisitante`
- `dfd_responsavel_demanda` -> `dfd_responsavel_demanda`
- `dfd_email` -> `dfd_email`
- `dfd_gestor_contratos` -> `dfd_gestor_contratos`
- `dfd_fiscal_contratos` -> `dfd_fiscal_contratos`
- `dfd_assinatura_cargo` -> `dfd_assinatura_cargo`
- `solicitacao_destinatario_nome` -> `sol_oficio_destinatario_nome`
- `solicitacao_destinatario_cargo` -> `sol_oficio_destinatario_cargo`
- `solicitacao_responsavel_nome` -> `sol_oficio_responsavel_nome`
- `solicitacao_responsavel_cargo` -> `sol_oficio_responsavel_cargo`

Obs.: `dfd_numero_processo`, `dfd_assinatura_nome` e `dfd_data` já estão previstos no backend e podem ser adicionados ao card quando desejado.

---

## Arquivos de código relevantes

- `frontend-vue/src/views/DocumentGenerator.vue`
- `backend/app/api.py`
- `rag_service/app/tr_slots_llm.py`
- `rag_service/app/tr_template.py`
- `rag_service/app/dfd_template.py`

---

## Checklist ao alterar modelo DOCX

1. Atualizar placeholders no `.docx`.
2. Se quiser posicionamento determinístico da tabela de itens, inserir `(TR_TABELA_ITENS)` no ponto desejado.
3. Atualizar mapping em `tr_template.py` e/ou `dfd_template.py`.
4. Garantir campo em `TRTemplateSlots`.
5. Garantir merge em `tr_slots_llm.py`.
6. Atualizar `slots_override` no frontend.
7. Testar geração TR e DFD no fluxo completo.
