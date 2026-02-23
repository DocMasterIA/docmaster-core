# Template base – Termo de Referência

Pasta do **modelo fixo** de Termo de Referência usado pela geração via slots.

- **Arquivo:** `TR_modelo_base.docx`
- **Uso:** O módulo `rag_service/app/tr_template.py` preenche apenas os campos entre `( ... )` (objeto, justificativa, itens da tabela, fiscal, dotação, etc.), sem alterar o resto do texto.

Não remova nem renomeie `TR_modelo_base.docx` sem atualizar `TEMPLATE_PATH_DEFAULT` em `tr_template.py`.
