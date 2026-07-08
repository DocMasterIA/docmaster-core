from unittest import TestCase

from backend.app.utils.valor_extenso_pt import (
    inteiro_por_extenso,
    parse_valor_monetario_br,
    valor_monetario_extenso_payload,
    valor_monetario_por_extenso,
)


class ValorExtensoPtTests(TestCase):
    def test_parse_moeda_br(self):
        self.assertEqual(parse_valor_monetario_br("R$ 1.234,56"), parse_valor_monetario_br("1234.56"))
        self.assertIsNone(parse_valor_monetario_br(""))

    def test_zero(self):
        self.assertEqual(valor_monetario_por_extenso(0), "zero reais")

    def test_centavos(self):
        self.assertEqual(valor_monetario_por_extenso("0,01"), "um centavo")
        self.assertEqual(valor_monetario_por_extenso("0,02"), "dois centavos")

    def test_reais_inteiros(self):
        self.assertEqual(valor_monetario_por_extenso(1), "um real")
        self.assertEqual(valor_monetario_por_extenso(2), "dois reais")
        self.assertEqual(valor_monetario_por_extenso(10), "dez reais")

    def test_reais_e_centavos(self):
        self.assertEqual(
            valor_monetario_por_extenso("1,01"),
            "um real e um centavo",
        )
        self.assertEqual(
            valor_monetario_por_extenso("10,50"),
            "dez reais e cinquenta centavos",
        )

    def test_centenas_e_milhares(self):
        self.assertEqual(valor_monetario_por_extenso(100), "cem reais")
        self.assertEqual(valor_monetario_por_extenso(101), "cento e um reais")
        self.assertEqual(valor_monetario_por_extenso(1000), "mil reais")
        self.assertEqual(valor_monetario_por_extenso(1001), "mil e um reais")
        self.assertEqual(
            valor_monetario_por_extenso("1.234,56"),
            "mil duzentos e trinta e quatro reais e cinquenta e seis centavos",
        )

    def test_milhoes(self):
        self.assertEqual(valor_monetario_por_extenso(1_000_000), "um milhão reais")
        self.assertEqual(
            valor_monetario_por_extenso(1_234_567.89),
            "um milhão duzentos e trinta e quatro mil quinhentos e sessenta e sete reais e oitenta e nove centavos",
        )

    def test_inteiro_por_extenso(self):
        self.assertEqual(inteiro_por_extenso(21), "vinte e um")
        self.assertEqual(inteiro_por_extenso(1100), "mil e cem")

    def test_payload_api(self):
        payload = valor_monetario_extenso_payload("1234.56")
        self.assertEqual(payload["valor"], 1234.56)
        self.assertEqual(payload["reais"], 1234)
        self.assertEqual(payload["centavos"], 56)
        self.assertIn("reais", payload["extenso"])

    def test_valor_invalido(self):
        with self.assertRaises(ValueError):
            valor_monetario_por_extenso("abc")
        with self.assertRaises(ValueError):
            valor_monetario_por_extenso(-1)
