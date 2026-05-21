"""Testes do atalho sem LLM em gerar-tr-e-dfd (timeout nginx/Cloudflare)."""
import unittest

from app.tr_slots_llm import (
    _is_objeto_justificativa_fill_mode,
    _override_has_prefilled_clauses,
    _should_skip_llm_for_prefilled_override,
    _strip_clause_draft_from_override,
)


class TrSlotsSkipLlmTests(unittest.TestCase):
    def test_inexigibilidade_prefilled_skips_when_skip_context(self):
        override = {
            "objeto": "Prestação de serviços de manutenção veicular conforme especificações.",
            "justificativa": "Inexigibilidade art. 74, inciso I, fornecedor exclusivo.",
        }
        ctx = {"slot_package_key": "inexigibilidade_74_i_manutencao_veiculos"}
        self.assertTrue(
            _should_skip_llm_for_prefilled_override(
                override, ctx, skip_context_in_prompt=True
            )
        )

    def test_inexigibilidade_package_skips_without_skip_context_flag(self):
        override = {
            "objeto": "Aquisição de peças e serviços técnicos especializados.",
            "justificativa": "Hipótese de inexigibilidade por fornecedor exclusivo.",
            "slot_package_key": "inexigibilidade_74_i_fornecedor_exclusivo",
        }
        self.assertTrue(_should_skip_llm_for_prefilled_override(override, None))

    def test_fill_tr_slots_does_not_skip_without_context_flag_or_inexig_package(self):
        override = {
            "objeto": "Objeto longo o suficiente para o teste de skip.",
            "justificativa": "Justificativa longa o suficiente para o teste de skip.",
            "dispensa_fluxo_ui": "normal",
        }
        self.assertFalse(
            _should_skip_llm_for_prefilled_override(
                override, None, skip_context_in_prompt=False
            )
        )

    def test_short_clauses_never_skip(self):
        override = {"objeto": "curto", "justificativa": "curta"}
        self.assertFalse(_override_has_prefilled_clauses(override))

    def test_clausulas_only_forces_lite_even_with_draft_objeto(self):
        override = {
            "clausulas_only": True,
            "objeto": "Aquisição de medicamentos para a rede municipal de saúde.",
            "justificativa": "Texto longo que existiria no override por engano.",
            "dispensa_fluxo_ui": "normal",
        }
        self.assertTrue(_is_objeto_justificativa_fill_mode(override))
        stripped = _strip_clause_draft_from_override(override)
        self.assertNotIn("objeto", stripped)
        self.assertNotIn("clausulas_only", stripped)


if __name__ == "__main__":
    unittest.main()
