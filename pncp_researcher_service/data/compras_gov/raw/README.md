# CSV Dados Abertos Compras.gov (não versionar dumps grandes).
#
# Doc de status da integração:
#   docs/pncp/MODULO-FONTES-PRECOS-04-COMPRAS-GOV.md
#
# Esperado (qualquer subpasta):
#   *VW_FT_PNCP_COMPRA*.csv        — cabeçalho do processo (órgão, UF, modalidade, link)
#   *VW_FT_PNCP_COMPRA_ITEM*.csv   — item + preço unitário + fornecedor
#
# Exemplos de layout:
#   raw/comprasGOV-anual-VW_FT_PNCP_COMPRA-latest.csv
#   raw/comprasGOV-mensal-VW_FT_PNCP_COMPRA_ITEM-2026-07.csv
#   raw/mensal/2026-07/*.csv
#
# Ingest: FEED_PLATFORM=compras_gov → price_index_feed_compras_gov (:8016)
# Parser/materialize ainda não implementados (POST ingest → 501).
