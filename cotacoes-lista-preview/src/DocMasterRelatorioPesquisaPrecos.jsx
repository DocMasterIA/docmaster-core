import { Link } from "react-router-dom";
import {
  FileText,
  Building2,
  User,
  CalendarDays,
  Sigma,
  Download,
  FileSpreadsheet,
  ShieldCheck,
  CircleCheck,
  AlertTriangle,
  ChevronDown,
  Eye,
  Printer,
  BadgeCheck,
  Info,
} from "lucide-react";

export default function TelaRelatorioPesquisaPrecos() {
  const itens = [
    {
      id: 1,
      nome: "FORFIG",
      quantidade: "1,00 CX",
      cotacoes: 3,
      media: "R$ 199,53",
      risco: "Baixo",
      situacao: "Válido",
      analise:
        "As cotações apresentaram alta consistência entre si, com baixa dispersão de valores e aderência ao objeto pesquisado.",
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
      quantidade: "1,00 CX",
      cotacoes: 3,
      media: "R$ 20,24",
      risco: "Baixo",
      situacao: "Válido",
      analise:
        "Os preços coletados demonstram razoável estabilidade e compatibilidade de unidade, com valor estimado consistente para definição da contratação.",
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
      analise:
        "Há concentração em valores de referência e uma cotação direta inferior. Recomenda-se registro da justificativa técnica para manutenção da média adotada.",
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

  return (
    <div className="min-h-screen bg-[#f4f6f8] text-slate-800 p-4">
      <div className="mx-auto max-w-[1380px] space-y-4">
        <div className="flex justify-end">
          <Link to="/busca-item" className="text-[13px] font-medium text-[#0f8a78] hover:underline">
            ← Voltar à busca compacta
          </Link>
        </div>
        <header className="rounded-[20px] border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="bg-gradient-to-r from-[#0f8a78] to-[#2f6f86] px-5 py-4 text-white">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
              <div className="space-y-2 max-w-[920px]">
                <div className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-[11px] font-semibold tracking-wide">
                  <FileText className="h-3.5 w-3.5" />
                  RELATÓRIO DE PESQUISA DE PREÇOS
                </div>
                <h1 className="text-[24px] md:text-[30px] font-semibold leading-tight">
                  Aquisição de medicamentos específicos para atender doações a pacientes em situação de vulnerabilidade social e risco à saúde
                </h1>
                <p className="text-[13px] md:text-[14px] text-white/90">
                  Documento técnico consolidado com metodologia, análise inteligente, rastreabilidade das cotações e conclusão para suporte à contratação.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 justify-end">
                <TopAction icon={<Eye className="h-4 w-4" />} label="Visualizar PDF" />
                <TopAction icon={<Printer className="h-4 w-4" />} label="Imprimir" />
                <TopAction icon={<FileSpreadsheet className="h-4 w-4" />} label="Exportar Excel" />
                <TopAction icon={<Download className="h-4 w-4" />} label="Baixar Relatório" primary />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3 p-4">
            <InfoCard icon={<Building2 className="h-4 w-4" />} label="Órgão" value="Prefeitura Municipal de Itajá - GO" />
            <InfoCard icon={<User className="h-4 w-4" />} label="Responsável" value="Edislene Ferreira da Silva" />
            <InfoCard icon={<CalendarDays className="h-4 w-4" />} label="Data da pesquisa" value="01/04/2026 08:59" />
            <InfoCard icon={<Sigma className="h-4 w-4" />} label="Método aplicado" value="Média Aritmética" />
            <InfoCard icon={<BadgeCheck className="h-4 w-4" />} label="Valor total estimado" value="R$ 2.026,33" strong />
          </div>
        </header>

        <section className="grid grid-cols-1 lg:grid-cols-[1.35fr_0.95fr] gap-4">
          <div className="rounded-[20px] border border-slate-200 bg-white shadow-sm p-4">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <h2 className="text-[18px] font-semibold text-slate-900">Metodologia Aplicada</h2>
                <p className="text-[12px] text-slate-500 mt-1">Base legal, método matemático e critérios de seleção das cotações</p>
              </div>
              <span className="rounded-full bg-[#e7f6ee] px-3 py-1 text-[11px] font-semibold text-[#1f7a53]">
                IN 65/2021 · Lei 14.133
              </span>
            </div>

            <div className="space-y-3 text-[13px] leading-6 text-slate-700">
              <p>
                A presente pesquisa de preços foi materializada com base na Lei nº 14.133/2021 e na Instrução Normativa nº 65/2021, adotando como método matemático a <strong>média aritmética dos preços obtidos</strong>, em conformidade com o art. 3º da referida instrução.
              </p>
              <p>
                Para composição do valor estimado, foram consideradas cotações provenientes de <strong>contratação direta, PNCP, CMED, ComprasGov e plataformas eletrônicas</strong>, observando compatibilidade do objeto, unidade de medida, recência da contratação, identificação do fornecedor e consistência dos dados.
              </p>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
              <MiniMetric title="Critério de seleção" value="Compatibilidade do objeto" />
              <MiniMetric title="Recência observada" value="Até 12 meses" />
              <MiniMetric title="Rastreabilidade" value="CNPJ, fonte e data" />
            </div>
          </div>

          <div className="rounded-[20px] border border-slate-200 bg-white shadow-sm p-4">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <h2 className="text-[18px] font-semibold text-slate-900">Diagnóstico da Pesquisa</h2>
                <p className="text-[12px] text-slate-500 mt-1">Resumo executivo para tomada de decisão</p>
              </div>
              <ShieldCheck className="h-5 w-5 text-[#2f6f86]" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <SummaryBox title="Itens analisados" value="3" tone="blue" />
              <SummaryBox title="Cotações válidas" value="9" tone="green" />
              <SummaryBox title="Risco predominante" value="Baixo" tone="green" />
              <SummaryBox title="Itens com ressalva" value="1" tone="yellow" />
            </div>

            <div className="mt-4 rounded-[16px] border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-[#2f6f86] mt-0.5" />
                <div>
                  <div className="text-[13px] font-semibold text-slate-800">Síntese automática da IA</div>
                  <p className="mt-1 text-[12px] leading-5 text-slate-600">
                    Os itens analisados apresentam, em sua maioria, consistência adequada entre as fontes consultadas, sem indícios relevantes de sobrepreço. Apenas um item demanda reforço de justificativa técnica em razão da concentração em valores de referência.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-[20px] border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="px-4 py-4 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
            <div>
              <h2 className="text-[18px] font-semibold text-slate-900">Resultado Consolidado</h2>
              <p className="text-[12px] text-slate-500 mt-1">Resumo dos itens com média definida e situação da pesquisa</p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <FilterButton label="Todos os itens" />
              <FilterButton label="Risco baixo" />
              <FilterButton label="Com ressalva" />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-4 py-3 text-left text-[12px] font-semibold">Item</th>
                  <th className="px-4 py-3 text-left text-[12px] font-semibold">Descrição</th>
                  <th className="px-4 py-3 text-left text-[12px] font-semibold">Quantidade</th>
                  <th className="px-4 py-3 text-left text-[12px] font-semibold">Cotações válidas</th>
                  <th className="px-4 py-3 text-left text-[12px] font-semibold">Média</th>
                  <th className="px-4 py-3 text-left text-[12px] font-semibold">Situação</th>
                </tr>
              </thead>
              <tbody>
                {itens.map((item) => (
                  <tr key={item.id} className="border-t border-slate-200 hover:bg-slate-50/70">
                    <td className="px-4 py-3 font-semibold text-slate-700">{item.id}</td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{item.nome}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{item.quantidade}</td>
                    <td className="px-4 py-3 text-slate-700">{item.cotacoes}</td>
                    <td className="px-4 py-3 font-semibold text-slate-900">{item.media}</td>
                    <td className="px-4 py-3"><StatusBadge status={item.situacao} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-[20px] border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="px-4 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-[18px] font-semibold text-slate-900">Detalhamento dos Itens</h2>
              <p className="text-[12px] text-slate-500 mt-1">Ficha técnica do item e fontes utilizadas na composição do preço</p>
            </div>
          </div>

          <div className="p-4 space-y-6">
            {itens.map((item) => {
              const quantidadePartes = item.quantidade.split(" ");
              const quantidadeValor = quantidadePartes[0] || item.quantidade;
              const unidadeValor = quantidadePartes.slice(1).join(" ") || "N/D";

              return (
                <div key={item.id} className="overflow-hidden rounded-[18px] border border-slate-200 bg-white">
                  <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Item {item.id}</div>
                    <div className="mt-1 text-[16px] font-semibold text-slate-900">{item.nome}</div>
                  </div>

                  <div className="border-b border-slate-200 bg-white px-4 py-4">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <DetailMiniCard label="Identificação (ID do item)" value={`ID ${item.id}`} />
                      <DetailMiniCard label="Quantidade" value={quantidadeValor} />
                      <DetailMiniCard label="Unidade" value={unidadeValor} />
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 text-slate-600">
                        <tr>
                          <th className="px-4 py-3 text-left text-[12px] font-semibold">Fonte</th>
                          <th className="px-4 py-3 text-left text-[12px] font-semibold">Fornecedor</th>
                          <th className="px-4 py-3 text-left text-[12px] font-semibold">CNPJ</th>
                          <th className="px-4 py-3 text-left text-[12px] font-semibold">Data</th>
                          <th className="px-4 py-3 text-left text-[12px] font-semibold">Valor</th>
                          <th className="px-4 py-3 text-left text-[12px] font-semibold">Órgão</th>
                          <th className="px-4 py-3 text-left text-[12px] font-semibold">Município/UF</th>
                          <th className="px-4 py-3 text-left text-[12px] font-semibold">Processo</th>
                          <th className="px-4 py-3 text-left text-[12px] font-semibold">Ajuste</th>
                        </tr>
                      </thead>
                      <tbody>
                        {item.fontes.map((fonte, idx) => (
                          <tr key={`${item.id}-${idx}`} className="border-t border-slate-200 hover:bg-slate-50/70">
                            <td className="px-4 py-3">{fonte.tipo}</td>
                            <td className="px-4 py-3">{fonte.fornecedor}</td>
                            <td className="px-4 py-3 text-[12px] text-slate-600">{fonte.cnpj}</td>
                            <td className="px-4 py-3">{fonte.data}</td>
                            <td className="px-4 py-3 font-semibold text-slate-900">{fonte.valor}</td>
                            <td className="px-4 py-3">{fonte.orgao}</td>
                            <td className="px-4 py-3">{fonte.municipio}/{fonte.uf}</td>
                            <td className="px-4 py-3 text-[12px]">{fonte.processo}</td>
                            <td className="px-4 py-3">{fonte.ajuste}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-[1.15fr_0.85fr] gap-4">
          <div className="rounded-[20px] border border-slate-200 bg-white shadow-sm p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-4 w-4 text-[#9a6a00]" />
              <h2 className="text-[18px] font-semibold text-slate-900">Análise de Risco da Pesquisa</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <RiskPanel title="Risco de inconsistência" value="Baixo" tone="green" />
              <RiskPanel title="Risco de desatualização" value="Baixo" tone="green" />
              <RiskPanel title="Risco de sobrepreço" value="Baixo" tone="green" />
            </div>
          </div>

          <div className="rounded-[20px] border border-slate-200 bg-white shadow-sm p-4">
            <div className="flex items-center gap-2 mb-3">
              <CircleCheck className="h-4 w-4 text-[#1f7a53]" />
              <h2 className="text-[18px] font-semibold text-slate-900">Conclusão Técnica</h2>
            </div>
            <p className="text-[13px] leading-6 text-slate-700">
              Com base nas cotações obtidas, na metodologia aplicada e na análise técnica dos dados, conclui-se que os valores estimados refletem adequadamente os preços praticados no mercado, estando aptos a subsidiar a contratação pública pretendida, com observância aos princípios da economicidade, razoabilidade e eficiência.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}

function TopAction({ icon, label, primary = false }) {
  return (
    <button
      type="button"
      className={`inline-flex h-10 items-center gap-2 rounded-lg px-4 text-[13px] font-semibold transition ${
        primary
          ? "bg-white text-[#0f8a78]"
          : "border border-white/25 bg-white/10 text-white hover:bg-white/15"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function InfoCard({ icon, label, value, strong = false }) {
  return (
    <div className="rounded-[16px] border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {icon}
        {label}
      </div>
      <div className={`mt-2 text-[13px] ${strong ? "font-bold text-slate-900" : "font-medium text-slate-700"}`}>
        {value}
      </div>
    </div>
  );
}

function MiniMetric({ title, value }) {
  return (
    <div className="rounded-[14px] border border-slate-200 bg-white px-3 py-3">
      <div className="text-[11px] text-slate-500">{title}</div>
      <div className="mt-1 text-[13px] font-semibold text-slate-800">{value}</div>
    </div>
  );
}

function SummaryBox({ title, value, tone = "green" }) {
  const toneMap = {
    green: "bg-[#e7f6ee] text-[#1f7a53] border-[#cfe9da]",
    yellow: "bg-[#fff6e6] text-[#9a6a00] border-[#f0dfb3]",
    blue: "bg-[#edf4ff] text-[#2f6f86] border-[#d9e6f5]",
  };

  return (
    <div className={`rounded-[16px] border px-4 py-3 ${toneMap[tone]}`}>
      <div className="text-[11px] font-semibold uppercase tracking-wide opacity-80">{title}</div>
      <div className="mt-2 text-[22px] font-bold">{value}</div>
    </div>
  );
}

function FilterButton({ label }) {
  return (
    <button
      type="button"
      className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-[12px] font-medium text-slate-700"
    >
      {label}
      <ChevronDown className="h-4 w-4 text-slate-400" />
    </button>
  );
}

function StatusBadge({ status }) {
  const map = {
    Válido: "bg-[#e7f6ee] text-[#1f7a53]",
    "Válido com ressalva": "bg-[#fff6e6] text-[#9a6a00]",
    Inválido: "bg-[#fff0f0] text-[#b54747]",
  };

  return <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${map[status]}`}>{status}</span>;
}

function DetailMiniCard({ label, value }) {
  return (
    <div className="rounded-[14px] border border-slate-200 bg-slate-50 px-3 py-3">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="mt-1 text-[13px] font-semibold text-slate-800">{value}</div>
    </div>
  );
}

function RiskPanel({ title, value, tone = "green" }) {
  const toneMap = {
    green: "bg-[#e7f6ee] border-[#cfe9da] text-[#1f7a53]",
    yellow: "bg-[#fff6e6] border-[#f0dfb3] text-[#9a6a00]",
    red: "bg-[#fff0f0] border-[#f0d0d0] text-[#b54747]",
  };

  return (
    <div className={`rounded-[16px] border px-4 py-4 ${toneMap[tone]}`}>
      <div className="text-[12px] font-semibold">{title}</div>
      <div className="mt-2 text-[20px] font-bold">{value}</div>
    </div>
  );
}
