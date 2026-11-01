# Templates by package (Law 14.133)

Standard structure per package:

- `TR_modelo_base.docx`
- `DFD_modelo_base.docx`
- `OFICIO_modelo_base.docx` (when applicable)

Expected package folders:

- `dispensa_75_i_manutencao_veiculos`
- `dispensa_75_i_obras_engenharia`
- `dispensa_75_ii_compras`
- `dispensa_75_ii_servicos`
- `dispensa_75_ii_compras_servicos_inclusos`
- `inexigibilidade_74_i_manutencao_de_veiculos` / `inexigibilidade_74_i_fornecedor_exclusivo`
- `tr_dfd_generico`

Notes:

- The system uses `slot_package_key` to resolve the package.
- `dispensa_rapida_*` keys (fast flow in the frontend) point to the same folders as `dispensa_75_*`.
- Until a package has its own DOCX, there is an automatic fallback to `template_packages/tr_base/*.docx`.
