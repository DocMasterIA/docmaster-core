"""Testes do atalho sem LLM em gerar-tr-e-dfd (timeout nginx/Cloudflare)."""
import unittest

from app.tr_slots_llm import (
    _build_tr_slots_from_override_prefilled,
    _is_dispensa_tr_flow,
    _is_objeto_justificativa_fill_mode,
    _override_has_prefilled_itens,
    _override_has_prefilled_clauses,
    _parse_itens_llm_payload,
    _parse_secao4_normal_llm_payload,
    _should_enrich_itens_llm,
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

    def test_dispensa_rapida_prefilled_skips_on_gerar_tr_e_dfd(self):
        override = {
            "objeto": "Objeto longo o suficiente para o teste de skip.",
            "justificativa": "Justificativa longa o suficiente para o teste de skip.",
            "dispensa_fluxo_ui": "rapida",
        }
        self.assertTrue(
            _should_skip_llm_for_prefilled_override(
                override, None, skip_context_in_prompt=True
            )
        )
        self.assertTrue(_should_skip_llm_for_prefilled_override(override, None))

    def test_dispensa_rapida_prefilled_skip_leaves_problema_beneficio_empty_until_enrich(self):
        jus = "Justificativa da contratação para atender demanda da secretaria de saúde municipal."
        slots = _build_tr_slots_from_override_prefilled(
            {
                "objeto": "Objeto longo o suficiente para o teste de skip.",
                "justificativa": jus,
                "dispensa_fluxo_ui": "rapida",
            },
            None,
        )
        self.assertEqual(slots.justificativa, jus)
        self.assertEqual(slots.problema_administrativo, "")
        self.assertEqual(slots.beneficio_esperado, "")

    def test_dispensa_normal_prefilled_skips_on_gerar_tr_e_dfd(self):
        override = {
            "objeto": "Objeto longo o suficiente para o teste de skip.",
            "justificativa": "Justificativa longa o suficiente para o teste de skip.",
            "dispensa_fluxo_ui": "normal",
        }
        self.assertTrue(
            _should_skip_llm_for_prefilled_override(
                override, None, skip_context_in_prompt=True
            )
        )
        self.assertTrue(
            _should_skip_llm_for_prefilled_override(override, None, skip_context_in_prompt=False)
        )

    def test_short_clauses_never_skip(self):
        override = {"objeto": "curto", "justificativa": "curta"}
        self.assertFalse(_override_has_prefilled_clauses(override))

    def test_prefilled_does_not_duplicate_justificativa_into_problema_beneficio(self):
        jus = (
            "É necessário garantir a disponibilidade adequada de medicamentos nas unidades básicas de saúde."
        )
        slots = _build_tr_slots_from_override_prefilled(
            {
                "objeto": "Objeto longo o suficiente para o teste de skip.",
                "justificativa": jus,
                "dispensa_fluxo_ui": "normal",
            },
            None,
        )
        self.assertEqual(slots.justificativa, jus)
        self.assertEqual(slots.problema_administrativo, "")
        self.assertEqual(slots.beneficio_esperado, "")

    def test_parse_secao4_normal_llm_payload(self):
        raw = (
            '{"problema_administrativo": "Risco de descontinuidade.", '
            '"beneficio_esperado": "Melhoria da eficiência."}'
        )
        parsed = _parse_secao4_normal_llm_payload(raw)
        self.assertEqual(parsed["problema_administrativo"], "Risco de descontinuidade.")
        self.assertEqual(parsed["beneficio_esperado"], "Melhoria da eficiência.")

    def test_strip_clause_draft_removes_objeto_from_override(self):
        override = {
            "objeto": "Aquisição de medicamentos para a rede municipal de saúde.",
            "justificativa": "Texto de rascunho.",
            "dispensa_fluxo_ui": "normal",
            "itens": [{"descricao": "Item 1"}],
        }
        stripped = _strip_clause_draft_from_override(override)
        self.assertNotIn("objeto", stripped)
        self.assertNotIn("justificativa", stripped)
        self.assertIn("itens", stripped)

    def test_override_has_prefilled_itens(self):
        self.assertTrue(_override_has_prefilled_itens({"itens": [{"descricao": "Item X"}]}))
        self.assertFalse(_override_has_prefilled_itens({"itens": []}))
        self.assertFalse(_override_has_prefilled_itens({}))

    def test_is_dispensa_tr_flow(self):
        self.assertTrue(_is_dispensa_tr_flow({"dispensa_fluxo_ui": "rapida"}))
        self.assertTrue(_is_dispensa_tr_flow({"slot_package_key": "dispensa_75_ii_obras"}))
        self.assertFalse(_is_dispensa_tr_flow({"slot_package_key": "inexigibilidade_74_i"}))

    def test_should_enrich_itens_dispensa_rapida_without_override_itens(self):
        override = {"dispensa_fluxo_ui": "rapida"}
        slots = _build_tr_slots_from_override_prefilled(
            {
                "objeto": "Objeto longo o suficiente para o teste de skip.",
                "justificativa": "Justificativa longa o suficiente para o teste de skip.",
                **override,
            },
            None,
        )
        self.assertTrue(_should_enrich_itens_llm(override, None, slots))

    def test_should_not_enrich_itens_when_override_has_itens(self):
        override = {
            "dispensa_fluxo_ui": "rapida",
            "itens": [{"descricao": "Item manual", "unidade": "un", "quantidade": 2}],
        }
        slots = _build_tr_slots_from_override_prefilled(
            {
                "objeto": "Objeto longo o suficiente para o teste de skip.",
                "justificativa": "Justificativa longa o suficiente para o teste de skip.",
                **override,
            },
            None,
        )
        self.assertFalse(_should_enrich_itens_llm(override, None, slots))

    def test_should_not_enrich_itens_inexigibilidade(self):
        override = {"slot_package_key": "inexigibilidade_74_i_manutencao_veiculos"}
        slots = _build_tr_slots_from_override_prefilled(
            {
                "objeto": "Objeto longo o suficiente para o teste de skip.",
                "justificativa": "Justificativa longa o suficiente para o teste de skip.",
                **override,
            },
            None,
        )
        self.assertFalse(_should_enrich_itens_llm(override, None, slots))

    def test_parse_itens_llm_payload(self):
        raw = (
            '{"itens": [{"descricao": "Manutenção preventiva de veículos", '
            '"unidade": "sv", "quantidade": 1, "valor_unitario": "", "valor_total": ""}]}'
        )
        items = _parse_itens_llm_payload(raw)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].descricao, "Manutenção preventiva de veículos")
        self.assertEqual(items[0].unidade, "sv")
        self.assertEqual(items[0].quantidade, 1)


if __name__ == "__main__":
    unittest.main()
