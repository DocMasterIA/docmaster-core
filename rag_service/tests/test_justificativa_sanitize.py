"""Normalização da justificativa — exatamente 3 parágrafos."""
import unittest

from app.justificativa_clause_sanitize import normalize_justificativa_tres_paragrafos


SAMPLE_FIVE = """A deterioração avançada das instalações do prédio sede compromete a funcionalidade dos setores administrativos, exigindo intervenções técnicas imediatas para garantir a habitabilidade e a segurança dos servidores e cidadãos que frequentam o local diariamente.

A não realização das obras acarretaria riscos elevados de colapso parcial de elementos construtivos, falhas nos sistemas elétricos e hidráulicos, além da interrupção contínua dos serviços públicos essenciais prestados pela administração municipal, gerando passivos trabalhistas e civis.

A execução da reforma assegura a preservação do patrimônio público imobiliário, otimiza a eficiência operacional dos departamentos lotados no imóvel e demonstra o cumprimento do dever estatal de manutenção adequada das infraestruturas governamentais em prol do interesse coletivo.

A deterioração avançada das instalações do prédio sede representa um risco significativo à continuidade dos serviços públicos essenciais, comprometendo a segurança e a eficiência operacional dos servidores. A não realização das obras poderia levar a colapso parcial de elementos construtivos e falhas nos sistemas elétricos e hidráulicos, gerando passivos trabalhistas e civis.

A execução da reforma assegura a preservação do patrimônio público imobiliário, otimiza a eficiência operacional dos departamentos lotados no prédio e garante a continuidade dos serviços públicos essenciais, contribuindo para o interesse coletivo e a satisfação dos cidadãos."""


SAMPLE_BULLETS = """A intervenção é imperativa para sanar patologias construtivas e desgastes naturais que comprometem a habitabilidade e a segurança do imóvel onde operam os órgãos municipais. A deterioração atual exige ações corretivas imediatas para garantir condições adequadas de trabalho aos servidores e atendimento digno à população.

A ausência da execução dos reparos acarreta risco iminente de colapso de elementos construtivos, além de agravar problemas de infiltrações e instalações elétricas obsoletas. Tal cenário ameaça a continuidade dos serviços públicos essenciais, expõe a administração a passivos trabalhistas por insalubridade e eleva exponencialmente os custos de manutenção emergencial futura.

A realização da reforma assegura a preservação do patrimônio público municipal e otimiza a eficiência operacional da máquina administrativa através de um ambiente funcional e seguro. A medida atende ao princípio da economicidade ao prevenir a ruína prematura do bem imóvel, garantindo a regularidade e a perenidade das atividades governamentais locais.
- A inexecução dos serviços de reforma predial pode levar a um colapso estrutural iminente, comprometendo a segurança dos servidores e cidadãos.
- O agravamento de problemas como infiltrações e instalações elétricas obsoletas pode resultar em interrupção dos serviços públicos essenciais.
- A reforma assegura a continuidade das atividades governamentais, preservando o patrimônio público municipal.
- O ambiente funcional e seguro promove a eficiência operacional da máquina administrativa, melhorando a qualidade do atendimento à população."""


SAMPLE_ECHO = """A deterioração avançada das instalações físicas do edifício sede compromete a habitabilidade dos ambientes e a segurança dos servidores e cidadãos que frequentam o órgão. A intervenção é imprescindível para sanar patologias construtivas identificadas, garantindo que a infraestrutura atenda aos padrões mínimos de funcionamento exigidos para a prestação dos serviços públicos.

A não realização das obras acarretará riscos iminentes à integridade física dos ocupantes devido ao possível colapso de elementos estruturais ou falhas nas instalações elétricas e hidrossanitárias. Além disso, a degradação contínua do imóvel resultará em perda de eficiência operacional, com interrupções frequentes nas atividades administrativas e elevação exponencial dos custos de manutenção corretiva emergencial.

A execução da reforma assegura a preservação do patrimônio público municipal e a continuidade administrativa ininterrupta, alinhando-se ao interesse público de manter um ambiente de trabalho seguro e adequado. A medida promove a otimização dos recursos públicos ao evitar a necessidade de relocação temporária dos setores ou a construção de novas instalações, garantindo a regularidade do atendimento à população.

A deterioração avançada das instalações físicas do edifício sede representa um risco iminente à integridade física dos ocupantes, podendo acarretar danos estruturais e interrupção nas atividades administrativas. A não realização das obras comprometeria a continuidade operacional e resultaria em custos elevados de manutenção emergencial.

A execução da reforma assegura a preservação do patrimônio público municipal, otimizando os recursos ao evitar relocação temporária dos setores ou construção de novas instalações. A medida garante um ambiente seguro e adequado para o funcionamento contínuo das atividades administrativas, alinhando-se aos interesses públicos."""


class JustificativaSanitizeTests(unittest.TestCase):
    def test_dedupes_semantic_echo_paragraphs(self):
        out = normalize_justificativa_tres_paragrafos(SAMPLE_ECHO)
        paras = [p for p in out.split("\n\n") if p.strip()]
        self.assertEqual(len(paras), 3)
        self.assertIn("patologias construtivas", paras[0].lower())
        self.assertIn("não realização", paras[1].lower())
        self.assertIn("execução da reforma", paras[2].lower())
        self.assertNotIn("danos estruturais", out.lower())
        self.assertNotIn("interesses públicos", out.lower())

    def test_strips_trailing_bullet_list(self):
        out = normalize_justificativa_tres_paragrafos(SAMPLE_BULLETS)
        paras = [p for p in out.split("\n\n") if p.strip()]
        self.assertEqual(len(paras), 3)
        self.assertNotIn("- A inexecução", out)
        self.assertNotIn("colapso estrutural iminente", out.lower())
        self.assertIn("patologias construtivas", paras[0].lower())
        self.assertIn("ausência da execução", paras[1].lower())
        self.assertIn("realização da reforma", paras[2].lower())

    def test_truncates_five_paragraphs_to_three(self):
        out = normalize_justificativa_tres_paragrafos(SAMPLE_FIVE)
        paras = [p for p in out.split("\n\n") if p.strip()]
        self.assertEqual(len(paras), 3)
        self.assertIn("deterioração avançada", paras[0].lower())
        self.assertIn("não realização", paras[1].lower())
        self.assertIn("execução da reforma", paras[2].lower())
        self.assertNotIn("satisfação dos cidadãos", out.lower())

    def test_single_newline_paragraphs(self):
        raw = "Primeiro bloco longo sobre necessidade administrativa da reforma predial no prédio sede.\nSegundo bloco sobre riscos da não contratação e falhas nos sistemas.\nTerceiro bloco sobre interesse público e continuidade.\nQuarto bloco repetindo riscos.\nQuinto bloco repetindo benefícios."
        out = normalize_justificativa_tres_paragrafos(raw)
        self.assertEqual(len([p for p in out.split("\n\n") if p.strip()]), 3)

    def test_preserves_three_paragraphs(self):
        raw = "P1 necessidade.\n\nP2 riscos.\n\nP3 interesse público."
        self.assertEqual(normalize_justificativa_tres_paragrafos(raw), raw)


if __name__ == "__main__":
    unittest.main()
