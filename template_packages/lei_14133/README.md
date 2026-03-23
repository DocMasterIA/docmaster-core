# Templates por pacote (Lei 14.133)

Estrutura padrão por pacote:

- `TR_modelo_base.docx`
- `DFD_modelo_base.docx`
- `OFICIO_modelo_base.docx` (quando aplicável)

Pastas de pacote previstas:

- `dispensa_75_i_manutencao_veiculos`
- `dispensa_75_i_obras_engenharia`
- `dispensa_75_ii_compras`
- `dispensa_75_ii_servicos`
- `dispensa_75_ii_compras_servicos_inclusos`
- `inexigibilidade_74_i_show_artistico`
- `tr_dfd_generico`

Observação:

- O sistema usa `slot_package_key` para resolver o pacote.
- Enquanto um pacote não tiver DOCX próprio, há fallback automático para `template_packages/tr_base/*.docx`.
