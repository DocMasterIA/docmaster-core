export default function DocMasterBuscaCompacta() {
  const rows = [
    {
      id: 1,
      titulo: "Chamada Pública – Hortifrutigranjeiros para Alimentação Escolar",
      item: "Abacate",
      normalizado: "Abacate in natura",
      orgao: "Prefeitura de Itajá",
      cidade: "Itajá/GO",
      modalidade: "Chamada Pública",
      processo: "CP 002/2028",
      data: "08/04/2028",
      qtd: "200 KG",
      valor: "R$ 13,00",
      score: "96%",
      confiabilidade: "Alta",
      risco: "Baixo",
      status: "Selecionado",
    },
    {
      id: 2,
      titulo: "Pregão Eletrônico – Aquisição de Hortifrutigranjeiros",
      item: "Abacate em kg",
      normalizado: "Abacate in natura",
      orgao: "Prefeitura de Cassilândia",
      cidade: "Cassilândia/MS",
      modalidade: "Pregão Eletrônico",
      processo: "PE 014/2028",
      data: "11/04/2028",
      qtd: "180 KG",
      valor: "R$ 12,80",
      score: "91%",
      confiabilidade: "Alta",
      risco: "Baixo",
      status: "Selecionado",
    },
    {
      id: 3,
      titulo: "Registro de Preços – Frutas e Verduras",
      item: "Abacate 1 kg",
      normalizado: "Abacate in natura",
      orgao: "Fundo Municipal de Educação",
      cidade: "Jataí/GO",
      modalidade: "Pregão Eletrônico SRP",
      processo: "PE-SRP 021/2028",
      data: "02/04/2028",
      qtd: "250 KG",
      valor: "R$ 13,20",
      score: "87%",
      confiabilidade: "Média",
      risco: "Médio",
      status: "Selecionado",
    },
    {
      id: 4,
      titulo: "Dispensa Eletrônica – Gêneros Alimentícios",
      item: "Abacate unidade",
      normalizado: "Divergência de unidade",
      orgao: "Secretaria Municipal de Educação",
      cidade: "Rio Verde/GO",
      modalidade: "Dispensa Eletrônica",
      processo: "DE 008/2028",
      data: "09/04/2028",
      qtd: "300 UN",
      valor: "R$ 9,90",
      score: "52%",
      confiabilidade: "Baixa",
      risco: "Alto",
      status: "Selecionado",
    },
  ];

  const confiabilidadeClass = (value) => {
    if (value === "Alta") return "bg-emerald-50 text-emerald-700 border-emerald-200";
    if (value === "Média") return "bg-amber-50 text-amber-700 border-amber-200";
    return "bg-rose-50 text-rose-700 border-rose-200";
  };

  const riscoClass = (value) => {
    if (value === "Baixo") return "bg-emerald-50 text-emerald-700";
    if (value === "Médio") return "bg-amber-50 text-amber-700";
    return "bg-rose-50 text-rose-700";
  };

  const statusClass = (value) => {
    return value === "Selecionado"
      ? "bg-cyan-50 text-cyan-700 border-cyan-200"
      : "bg-slate-100 text-slate-600 border-slate-200";
  };

  return (
    <div className="min-h-screen bg-slate-100 p-5 text-slate-800">
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="bg-white border border-slate-200 rounded-3xl shadow-sm p-5">
          <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
            <div className="space-y-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">DocMaster IA • Pesquisa de Preços</div>
                <h1 className="text-2xl font-bold mt-1">Busca Inteligente de Cotações</h1>
                <p className="text-sm text-slate-500 mt-2 max-w-4xl">
                  Interface compacta para análise, comparação e seleção das cotações mais consistentes, com foco em rastreabilidade e auditoria.
                </p>
              </div>

              <div className="flex flex-wrap gap-2 text-sm">
                <Tag>Item pesquisado: <strong>Abacate</strong></Tag>
                <Tag>Descrição IA: <strong>Abacate in natura</strong></Tag>
                <Tag>Base: <strong>PNCP + banco interno</strong></Tag>
                <Tag accent>Modo auditoria TCU ativo</Tag>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 min-w-full xl:min-w-[540px]">
              <Summary title="Válidas" value="3" />
                            <Summary title="Média" value="R$ 13,00" />
              <Summary title="Risco" value="Baixo" highlight />
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-3xl shadow-sm p-4 space-y-4">
          <div className="flex flex-col xl:flex-row xl:items-end gap-3">
            <Filter label="Descrição" value="ABACATE" className="xl:flex-[1.4]" />
            <Filter label="Período" value="Últimos 12 meses" className="xl:flex-1" />
            <Filter label="Tipo" value="Material" className="xl:flex-1" />
            <Filter label="Modalidade" value="Todas" className="xl:flex-1" />
            <Filter label="UF" value="GO, MS" className="xl:flex-1" />
            <button className="h-12 px-5 rounded-2xl bg-cyan-600 text-white font-semibold shadow-sm">Buscar</button>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-sm">
            <MiniPill>Faixa válida: R$ 11,00 a R$ 14,00</MiniPill>
            <MiniPill>Agrupamento de duplicidades ativo</MiniPill>
            <MiniPill>Ordenação: maior similaridade</MiniPill>
            <MiniPill>Seleção automática: 3 melhores</MiniPill>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
            <div className="flex flex-wrap gap-2 text-sm">
              <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">3 aptas para média</span>
              <span className="px-3 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200"></span>
              <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">2 duplicidades agrupadas</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="px-4 py-2 rounded-2xl border border-slate-300 text-sm font-medium">Gerar Excel resumido</button>
              <button className="px-4 py-2 rounded-2xl border border-slate-300 text-sm font-medium">Relatório técnico</button>
              <button className="px-4 py-2 rounded-2xl bg-slate-900 text-white text-sm font-semibold">Aplicar seleção</button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-white border-b border-slate-200">
                <tr className="text-left text-slate-500 uppercase text-[11px] tracking-wide">
                  <th className="px-4 py-3">Seleção</th>
                  <th className="px-4 py-3">Cotação</th>
                  <th className="px-4 py-3">Órgão / Local</th>
                  <th className="px-4 py-3">Processo</th>
                  <th className="px-4 py-3">Qtd.</th>
                  <th className="px-4 py-3">Valor</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Confiabilidade</th>
                  <th className="px-4 py-3">Risco</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Ações</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b border-slate-200 hover:bg-slate-50 transition">
                    <td className="px-4 py-4 align-top">
                      <input type="checkbox" checked={row.status === "Selecionado"} readOnly className="h-4 w-4 rounded" />
                    </td>
                    <td className="px-4 py-4 align-top min-w-[320px]">
                      <div className="font-semibold leading-5">{row.titulo}</div>
                      <div className="text-slate-500 mt-1 leading-5">
                        Item: <strong>{row.item}</strong><br />
                        IA: <strong>{row.normalizado}</strong><br />
                        Modalidade: {row.modalidade} • Data: {row.data}
                      </div>
                    </td>
                    <td className="px-4 py-4 align-top min-w-[220px]">
                      <div className="font-medium leading-5">{row.orgao}</div>
                      <div className="text-slate-500 mt-1">{row.cidade}</div>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <div className="font-medium">{row.processo}</div>
                    </td>
                    <td className="px-4 py-4 align-top font-semibold whitespace-nowrap">{row.qtd}</td>
                    <td className="px-4 py-4 align-top font-bold whitespace-nowrap">{row.valor}</td>
                    <td className="px-4 py-4 align-top whitespace-nowrap">{row.score}</td>
                    <td className="px-4 py-4 align-top">
                      <span className={`px-3 py-1 rounded-full border text-xs font-semibold whitespace-nowrap ${confiabilidadeClass(row.confiabilidade)}`}>
                        {row.confiabilidade}
                      </span>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${riscoClass(row.risco)}`}>
                        {row.risco}
                      </span>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <span className={`px-3 py-1 rounded-full border text-xs font-semibold whitespace-nowrap ${statusClass(row.status)}`}>
                        {row.status}
                      </span>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <div className="flex flex-col gap-2 min-w-[140px]">
                        <button className="px-3 py-2 rounded-xl border border-slate-300 text-left text-xs font-medium">Ver docs</button>
                        <button className="px-3 py-2 rounded-xl border border-slate-300 text-left text-xs font-medium">Justificativa IA</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-3xl shadow-sm p-4">
          <div className="text-sm text-slate-600 leading-6">
            <strong className="text-slate-800">Justificativa técnica da seleção:</strong> as cotações classificadas como válidas foram selecionadas com base na compatibilidade da descrição, unidade de medida, recência, diversidade mínima de fontes e consistência dos dados encontrados. As cotações apresentadas foram selecionadas com base em critérios técnicos de compatibilidade, recência e consistência dos dados.
          </div>
        </div>
      </div>
    </div>
  );
}

function Tag({ children, accent = false }) {
  return (
    <span className={`px-3 py-1 rounded-full border ${accent ? "bg-cyan-50 text-cyan-700 border-cyan-200" : "bg-slate-100 text-slate-700 border-slate-200"}`}>
      {children}
    </span>
  );
}

function Summary({ title, value, highlight = false }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{title}</div>
      <div className={`text-xl font-bold mt-1 ${highlight ? "text-emerald-700" : "text-slate-800"}`}>{value}</div>
    </div>
  );
}

function Filter({ label, value, className = "" }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 ${className}`}>
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="font-medium mt-1">{value}</div>
    </div>
  );
}

function MiniPill({ children }) {
  return <span className="px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-700">{children}</span>;
}
