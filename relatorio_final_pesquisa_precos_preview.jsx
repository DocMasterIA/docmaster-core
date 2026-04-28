import React from "react";

const CENTRAL_PRECOS_LOGO = "data:image/webp;base64,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";

function parseQuantidade(quantidade) {
  if (!quantidade) {
    return { valor: "N/D", unidade: "N/D" };
  }

  const texto = String(quantidade).trim().replace(/\s+/g, " ");
  const match = texto.match(/^([\d.,]+)\s*(.*)$/);

  if (!match) {
    return { valor: texto, unidade: "N/D" };
  }

  const valor = match[1]?.trim() || "N/D";
  const unidade = match[2]?.trim() || "N/D";

  return { valor, unidade };
}

function moedaParaNumero(valor) {
  if (!valor) return 0;

  return (
    parseFloat(
      String(valor)
        .replace("R$", "")
        .trim()
        .replace(/\./g, "")
        .replace(",", ".")
    ) || 0
  );
}

function quantidadeParaNumero(quantidade) {
  const parsed = parseQuantidade(quantidade);
  return parseFloat(String(parsed.valor).replace(/\./g, "").replace(",", ".")) || 0;
}

function formatarMoeda(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function calcularTotalItem(item) {
  return quantidadeParaNumero(item.quantidade) * moedaParaNumero(item.media);
}

function obterModalidade(tipo) {
  const map = {
    PNCP: "Pregão Eletrônico",
    BBMNET: "Dispensa",
    CMED: "Pregão Eletrônico",
    "Cotação Direta": "Dispensa",
    ComprasGov: "Pregão",
  };

  return map[tipo] || tipo || "N/D";
}

function obterFonte(tipo) {
  const fontesConvertidas = ["Cotação Direta", "BBMNET", "ComprasGov", "CMED"];
  return fontesConvertidas.includes(tipo) ? "PNCP" : tipo || "N/D";
}

function Icon({ name, className = "" }) {
  const icons = {
    file: "📄",
    building: "🏛️",
    user: "👤",
    calendar: "📅",
    sigma: "Σ",
    check: "✓",
    shield: "🛡️",
    badge: "✓",
  };

  return (
    <span className={`inline-flex items-center justify-center leading-none ${className}`} aria-hidden="true">
      {icons[name] || "•"}
    </span>
  );
}

const itensPesquisa = [
  {
    id: 1,
    nome: "FORFIG",
    quantidade: "5,00 CX",
    cotacoes: 3,
    media: "R$ 199,53",
    risco: "Baixo",
    situacao: "Válido",
    fontes: [
      {
        tipo: "Cotação Direta",
        fornecedor: "ITAFARMA Drogaria e Perfumaria Ltda",
        cnpj: "01.012.426/0001-28",
        orgao: "Fornecedor Privado",
        municipio: "Itajá",
        uf: "GO",
        processo: "-",
        data: "31/03/2026",
        valor: "R$ 198,00",
        ajuste: "Sem frete",
        status: "Selecionada",
      },
      {
        tipo: "PNCP",
        fornecedor: "Play Pharma Comércio de Produtos Hospitalares Ltda",
        cnpj: "32.321.488/0001-45",
        orgao: "Prefeitura Municipal",
        municipio: "Goiânia",
        uf: "GO",
        processo: "PNCP-2025",
        data: "02/04/2025",
        valor: "R$ 200,75",
        ajuste: "Sem frete",
        status: "Selecionada",
      },
      {
        tipo: "BBMNET",
        fornecedor: "Carla Janaina Rodrigues Silva",
        cnpj: "25.257.455/0002-07",
        orgao: "Órgão Licitante",
        municipio: "Rio Verde",
        uf: "GO",
        processo: "PE-102/2025",
        data: "07/04/2025",
        valor: "R$ 199,85",
        ajuste: "Sem frete",
        status: "Selecionada",
      },
    ],
  },
  {
    id: 2,
    nome: "INDAPAMIDA 1.5MG",
    quantidade: "2,00 CX",
    cotacoes: 3,
    media: "R$ 20,24",
    risco: "Baixo",
    situacao: "Válido",
    fontes: [
      {
        tipo: "CMED",
        fornecedor: "Secretaria Executiva da CMED",
        cnpj: "03.112.386/0001-11",
        orgao: "Governo Federal",
        municipio: "Brasília",
        uf: "DF",
        processo: "Tabela CMED",
        data: "06/11/2025",
        valor: "R$ 22,21",
        ajuste: "Sem frete",
        status: "Selecionada",
      },
      {
        tipo: "Cotação Direta",
        fornecedor: "ITAFARMA Drogaria e Perfumaria Ltda",
        cnpj: "01.012.426/0001-28",
        orgao: "Fornecedor Privado",
        municipio: "Itajá",
        uf: "GO",
        processo: "-",
        data: "31/03/2026",
        valor: "R$ 16,00",
        ajuste: "Sem frete",
        status: "Selecionada",
      },
      {
        tipo: "ComprasGov",
        fornecedor: "Drogaria e Farmácia Livramento Ltda",
        cnpj: "03.525.940/0003-54",
        orgao: "Órgão Público",
        municipio: "Campo Grande",
        uf: "MS",
        processo: "CG-445/2025",
        data: "16/05/2025",
        valor: "R$ 22,50",
        ajuste: "Sem frete",
        status: "Selecionada",
      },
    ],
  },
  {
    id: 3,
    nome: "POVIZTRA 1MG",
    quantidade: "1,00 CX",
    cotacoes: 3,
    media: "R$ 960,55",
    risco: "Médio",
    situacao: "Válido com ressalva",
    fontes: [
      {
        tipo: "CMED",
        fornecedor: "Secretaria Executiva da CMED",
        cnpj: "03.112.386/0001-11",
        orgao: "Governo Federal",
        municipio: "Brasília",
        uf: "DF",
        processo: "Tabela CMED",
        data: "08/03/2026",
        valor: "R$ 980,83",
        ajuste: "Sem frete",
        status: "Selecionada",
      },
      {
        tipo: "CMED",
        fornecedor: "Secretaria Executiva da CMED",
        cnpj: "03.112.386/0001-11",
        orgao: "Governo Federal",
        municipio: "Brasília",
        uf: "DF",
        processo: "Tabela CMED",
        data: "08/03/2026",
        valor: "R$ 980,83",
        ajuste: "Sem frete",
        status: "Selecionada",
      },
      {
        tipo: "Cotação Direta",
        fornecedor: "ITAFARMA Drogaria e Perfumaria Ltda",
        cnpj: "01.012.426/0001-28",
        orgao: "Fornecedor Privado",
        municipio: "Itajá",
        uf: "GO",
        processo: "-",
        data: "31/03/2026",
        valor: "R$ 920,00",
        ajuste: "Sem frete",
        status: "Selecionada",
      },
    ],
  },
];

function runDeveloperTests() {
  const tests = [
    {
      name: "parseQuantidade separa valor e unidade",
      pass: parseQuantidade("5,00 CX").valor === "5,00" && parseQuantidade("5,00 CX").unidade === "CX",
    },
    {
      name: "moedaParaNumero converte moeda brasileira",
      pass: moedaParaNumero("R$ 1.998,68") === 1998.68,
    },
    {
      name: "calcularTotalItem calcula quantidade vezes média",
      pass: Math.abs(calcularTotalItem({ quantidade: "5,00 CX", media: "R$ 199,53" }) - 997.65) < 0.001,
    },
    {
      name: "obterFonte converte bases auxiliares para PNCP",
      pass: obterFonte("CMED") === "PNCP" && obterFonte("PNCP") === "PNCP",
    },
  ];

  const failed = tests.filter((test) => !test.pass);
  if (failed.length) {
    console.error("Falha nos testes do relatório:", failed.map((test) => test.name));
  }
}

runDeveloperTests();

export default function TelaRelatorioPesquisaPrecos() {
  const itens = itensPesquisa;
  const valorTotalEstimado = itens.reduce((total, item) => total + calcularTotalItem(item), 0);
  const fornecedoresUnicos = Array.from(
    new Map(
      itens
        .flatMap((item) => item.fontes)
        .filter((fonte) => fonte.cnpj !== "25.257.455/0002-07")
        .map((fonte) => [fonte.cnpj, fonte])
    ).values()
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 via-gray-50 to-zinc-100">
      <div className="mx-auto max-w-[1200px] space-y-4 p-4 md:p-6">
        <header className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
                <h1 className="text-[22px] font-bold leading-tight text-slate-900">
                  Relatório de pesquisa de preços
                </h1>
                <p className="mt-1 max-w-2xl text-[13px] text-slate-700">
                  Aquisição de medicamentos específicos para atender doações a pacientes em situação de vulnerabilidade social e risco à saúde
                </p>
                <p className="mt-1 text-[11px] text-slate-500">
                  Documento técnico consolidado com metodologia, análise técnica, rastreabilidade das cotações e conclusão para suporte à contratação.
                </p>
              </div>
              <div className="hidden shrink-0 items-center justify-center rounded-[18px] border border-slate-200 bg-slate-50 px-3 py-2 shadow-sm sm:flex">
                <img
                  src={CENTRAL_PRECOS_LOGO}
                  alt="Central de Preços"
                  className="h-16 w-auto object-contain"
                />
              </div>
          </div>
        </header>

        <div className="grid grid-cols-1 gap-1 md:grid-cols-2 xl:grid-cols-5">
          <InfoCard icon={<Icon name="building" />} label="Órgão" value="Prefeitura Municipal de Itajá - GO" />
          <InfoCard icon={<Icon name="user" />} label="Responsável" value="Edislene Ferreira da Silva" />
          <InfoCard icon={<Icon name="calendar" />} label="Data da pesquisa" value="01/04/2026 08:59" />
          <InfoCard icon={<Icon name="sigma" />} label="Método aplicado" value="Média Aritmética" />
          <InfoCard icon={<Icon name="badge" />} label="Valor total estimado" value={formatarMoeda(valorTotalEstimado)} strong />
        </div>

        <section className="w-full">
          <div className="w-full rounded-[20px] border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-1">
              <div>
                <h2 className="text-[18px] font-semibold text-slate-900">Metodologia aplicada</h2>
                <p className="mt-1 text-[12px] text-slate-500">Base legal, método matemático e critérios técnicos adotados</p>
              </div>
              <span className="rounded-full bg-[#edf4ff] px-3 py-0.5 text-[11px] font-semibold text-[#5f7f9a]">
                IN 65/2021 · Lei 14.133
              </span>
            </div>

            <div className="space-y-2 text-[13px] leading-6 text-slate-700">
              <p>
                A pesquisa foi realizada com base na Lei nº 14.133/2021 e na IN nº 65/2021.
              </p>
              <p>
                As cotações selecionadas foram obtidas por meio de consultas ao Portal Nacional de Contratações Públicas – PNCP, bancos de dados públicos e pesquisa direta de mercado, observando-se a compatibilidade da descrição do objeto, a unidade de medida, a recência das informações, a natureza da contratação e a consistência dos dados utilizados para formação do preço estimado.
              </p>
              <p>
                Os valores estimados mostram-se compatíveis com o mercado e adequados para subsidiar a contratação.
              </p>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-1 md:grid-cols-3">
              <MiniMetric title="Critério" value="Compatibilidade" />
              <MiniMetric title="Recência" value="Até 12 meses" />
              <MiniMetric title="Rastreabilidade" value="CNPJ, fonte e data" />
            </div>
          </div>
        </section>

        <section className="overflow-hidden rounded-[20px] border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-1 border-b border-slate-200 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-[18px] font-semibold text-slate-900">Resultado consolidado</h2>
              <p className="mt-1 text-[12px] text-slate-500">Resumo dos itens com média definida e situação da pesquisa</p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="w-[5%] px-2 py-2 text-left text-[12px] font-semibold">Item</th>
                  <th className="w-[45%] px-3 py-2 text-left text-[12px] font-semibold">Descrição</th>
                  <th className="w-[10%] px-2 py-2 text-left text-[12px] font-semibold">Quantidade</th>
                  <th className="w-[15%] px-2 py-2 text-left text-[12px] font-semibold">Cotações válidas</th>
                  <th className="w-[12%] px-2 py-2 text-left text-[12px] font-semibold">Média</th>
                  <th className="w-[13%] px-2 py-2 text-left text-[12px] font-semibold">Valor total</th>
                </tr>
              </thead>
              <tbody>
                {itens.map((item) => {
                  const total = formatarMoeda(calcularTotalItem(item));

                  return (
                    <tr key={item.id} className="border-t border-slate-200 hover:bg-slate-50/70">
                      <td className="px-2 py-2 font-semibold text-slate-700">{item.id}</td>
                      <td className="w-[45%] px-3 py-2">
                        <div className="font-semibold text-slate-900">{item.nome}</div>
                      </td>
                      <td className="px-2 py-2 text-slate-700">{item.quantidade}</td>
                      <td className="px-3 py-2 text-slate-700">{item.cotacoes}</td>
                      <td className="px-2 py-2 font-medium text-slate-900">{item.media}</td>
                      <td className="px-2 py-2 font-semibold text-[#5f7f9a]">{total}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section className="overflow-hidden rounded-[20px] border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-4">
            <div>
              <h2 className="text-[18px] font-semibold text-slate-900">Detalhamento dos itens</h2>
              <p className="mt-1 text-[12px] text-slate-500">Ficha técnica do item e fontes utilizadas na composição do preço</p>
            </div>
          </div>

          <div className="space-y-2 p-2">
            {itens.map((item) => {
              const { valor: quantidadeValor, unidade: unidadeValor } = parseQuantidade(item.quantidade);

              return (
                <div key={item.id} className="overflow-hidden rounded-[14px] border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
                  <div className="border-b border-slate-200 bg-slate-50 px-3 py-2">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">Item {item.id}</div>
                    <div className="mt-0.5 text-[13px] font-bold leading-4 text-slate-900">{item.nome}</div>
                  </div>

                  <div className="space-y-1.5 p-2">
                    {item.fontes.map((fonte, idx) => (
                      <div key={`${item.id}-${idx}`} className="relative rounded-[10px] border border-slate-200 bg-slate-50/60 pl-7">
                        <div className="absolute left-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded-full bg-[#5f7f9a] text-[8px] font-bold text-white shadow-sm">
                          {idx + 1}
                        </div>

                        <div className="space-y-1 p-1.5">
                          <div className="grid grid-cols-1 gap-1 md:grid-cols-[1.8fr_1fr_0.9fr]">
                            <DetailMiniCard label="Fornecedor" value={fonte.fornecedor} featured compact />
                            <DetailMiniCard label="CNPJ" value={fonte.cnpj} compact />
                            <DetailMiniCard label="Valor" value={fonte.valor} strong featured compact />
                          </div>

                          <div className="grid grid-cols-1 gap-1 md:grid-cols-[1.8fr_1fr_0.9fr]">
                            <DetailMiniCard label="Órgão" value={fonte.orgao} compact />
                            <DetailMiniCard label="Modalidade" value={obterModalidade(fonte.tipo)} compact />
                            <DetailMiniCard label="Data" value={fonte.data} compact />
                          </div>

                          <div className="grid grid-cols-2 gap-1 md:grid-cols-[1.8fr_1fr_1fr_1fr_1fr]">
                            <DetailMiniCard label="ID / Processo" value={`${idx + 1} / ${fonte.processo || "N/D"}`} compact wide />
                            <DetailMiniCard label="Qtd." value={quantidadeValor} compact />
                            <DetailMiniCard label="Unid." value={unidadeValor} compact />
                            <DetailMiniCard label="Fonte" value={obterFonte(fonte.tipo)} compact />
                            <DetailMiniCard label="UF" value={fonte.uf} compact />
                          </div>

                          <div className="grid grid-cols-1 gap-1 md:grid-cols-[1fr_0.7fr]">
                            <DetailMiniCard label="Descrição do item" value={item.nome} compact wide />
                            <DetailMiniCard label="Ajuste" value={fonte.ajuste} compact wide />
                          </div>

                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-[20px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#edf4ff] text-[#5f7f9a]">
              <Icon name="check" />
            </div>
            <div>
              <h2 className="text-[18px] font-semibold text-slate-900">Conclusão técnica</h2>
              <p className="text-[12px] text-slate-500">Síntese conclusiva da pesquisa de preços</p>
            </div>
          </div>

          <div className="rounded-[14px] border border-slate-200 bg-slate-50 p-4">
            <p className="text-[13px] leading-6 text-slate-700">
              Com base nas cotações obtidas, na metodologia aplicada e na análise técnica dos dados, conclui-se que os valores estimados refletem adequadamente os preços praticados no mercado, estando aptos a subsidiar a contratação pública pretendida, com observância aos princípios da economicidade, razoabilidade e eficiência.
            </p>
          </div>
        </section>

        <section className="rounded-[20px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#edf4ff] text-[#2f6f86]">
              <Icon name="shield" />
            </div>
            <div>
              <h2 className="text-[18px] font-semibold text-slate-900">Responsabilidade sobre as informações</h2>
              <p className="text-[12px] text-slate-500">Esclarecimento quanto ao uso da plataforma</p>
            </div>
          </div>

          <div className="space-y-2 rounded-[14px] border border-slate-200 bg-slate-50 p-4">
            <p className="text-[13px] leading-6 text-slate-700">
              A plataforma disponibiliza um ambiente digital de apoio à pesquisa de preços, no qual são consolidadas informações oriundas de diferentes origens, tais como bases públicas, sistemas oficiais e registros de mercado, com o objetivo de auxiliar na formação de referência de valores.
            </p>
            <p className="text-[13px] leading-6 text-slate-700">
              Compete exclusivamente ao servidor público responsável pela pesquisa a análise crítica, validação, seleção e utilização dos preços, em conformidade com a legislação vigente, especialmente a Lei nº 14.133/2021, normativos aplicáveis e orientações dos órgãos de controle.
            </p>
            <p className="text-[13px] leading-6 text-slate-700">
              Dessa forma, a plataforma atua como ferramenta de apoio à tomada de decisão, não substituindo o dever de diligência, responsabilidade técnica e julgamento administrativo do agente público.
            </p>
          </div>
        </section>

        <section className="rounded-[20px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#edf4ff] text-[#2f6f86]">
              <Icon name="building" />
            </div>
            <div>
              <h2 className="text-[18px] font-semibold text-slate-900">Informações dos fornecedores</h2>
              <p className="text-[12px] text-slate-500">Dados cadastrais e de contato</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {fornecedoresUnicos.map((fornecedor, idx) => (
              <div key={`${fornecedor.cnpj}-${idx}`} className="rounded-[14px] border border-slate-200 bg-slate-50 p-4">
                <div className="mb-2 text-[13px] font-bold uppercase text-slate-900">{fornecedor.fornecedor}</div>
                <div className="grid grid-cols-1 gap-1 text-[12px] text-slate-700">
                  <div>
                    <span className="font-semibold text-slate-600">CNPJ:</span> {fornecedor.cnpj}
                  </div>
                  <div>
                    <span className="font-semibold text-slate-600">Telefone:</span> {fornecedor.telefone || "Não informado"}
                  </div>
                  <div>
                    <span className="font-semibold text-slate-600">Email:</span> {fornecedor.email || "Não informado"}
                  </div>
                  <div>
                    <span className="font-semibold text-slate-600">Endereço:</span> {fornecedor.endereco || "Não informado"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function InfoCard({ icon, label, value, strong = false }) {
  return (
    <div className="rounded-[16px] border border-slate-200 bg-white px-3 py-2 shadow-sm">
      <div className="flex items-center gap-1 text-slate-500">
        <span className="text-[13px]">{icon}</span>
        <span className="text-[10px] leading-none">{label}</span>
      </div>
      <div className={`mt-1.5 text-[12px] leading-4 ${strong ? "font-bold text-slate-900" : "font-medium text-slate-700"}`}>
        {value}
      </div>
    </div>
  );
}

function MiniMetric({ title, value }) {
  return (
    <div className="rounded-[12px] border border-slate-200 bg-slate-50 p-1">
      <div className="text-[11px] text-slate-500">{title}</div>
      <div className="mt-1 text-[14px] font-semibold text-slate-800">{value}</div>
    </div>
  );
}

function DetailMiniCard({ label, value, strong = false, compact = false, featured = false, wide = false }) {
  if (compact) {
    return (
      <div
        className={`rounded-[6px] border border-slate-200 bg-white px-1.5 py-1 ${featured ? "bg-slate-50" : ""} ${
          wide ? "min-h-[28px]" : "min-h-[24px]"
        }`}
      >
        <div className="text-[7px] font-medium uppercase leading-none tracking-[0.04em] text-slate-500">{label}</div>
        <div
          className={`${wide ? "mt-0.5 text-[9px] leading-[1.15]" : "mt-0.5 text-[8.5px] leading-[1.1]"} break-words ${
            strong ? "font-bold text-slate-900" : featured ? "font-semibold text-slate-900" : "font-medium text-slate-800"
          }`}
        >
          {value}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[76px] rounded-[12px] border border-slate-200 bg-white p-1">
      <div className="text-[11px] leading-4 text-slate-500">{label}</div>
      <div className={`mt-1 break-words text-[14px] leading-5 ${strong ? "font-bold text-slate-900" : "font-semibold text-slate-800"}`}>
        {value}
      </div>
    </div>
  );
}
