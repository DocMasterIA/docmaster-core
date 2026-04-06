import { Link } from 'react-router-dom';

export default function DocMasterListaCotacoes() {
  const rows = [
    {
      id: 1,
      data: '01/04/2026 14:49',
      descricao: 'Contratação de empresa para manutenção de ar-condicionado',
      itens: 4,
      usuario: 'Diniz Luiz Martins Neto',
      status: 'Em andamento',
    },
    {
      id: 2,
      data: '01/04/2026 13:40',
      descricao: 'Aquisição de gêneros alimentícios',
      itens: 4,
      usuario: 'Diniz Luiz Martins Neto',
      status: 'Finalizada',
    },
    {
      id: 3,
      data: '01/04/2026 03:50',
      descricao: 'Aquisição de medicamentos',
      itens: 10,
      usuario: 'Edislene Ferreira da Silva',
      status: 'Finalizada',
    },
  ];

  const statusClass = (status) => {
    if (status === 'Finalizada') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    return 'bg-cyan-50 text-cyan-700 border-cyan-200';
  };

  return (
    <div className="min-h-screen bg-slate-100 p-5 text-slate-800">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* HEADER */}
        <div className="bg-white border border-slate-200 rounded-3xl shadow-sm p-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-cyan-700">DocMaster IA</div>
            <h1 className="text-2xl font-bold mt-1">Pesquisa de Preços Inteligente</h1>
            <p className="text-sm text-slate-500 mt-1">
              Gerencie e acompanhe as cotações realizadas com rastreabilidade e controle.
            </p>
          </div>

          <div className="flex gap-2">
            <button type="button" className="px-4 py-2 rounded-2xl bg-cyan-600 text-white font-semibold">
              + Nova Cotação
            </button>
          </div>
        </div>

        {/* FILTROS */}
        <div className="bg-white border border-slate-200 rounded-3xl shadow-sm p-4 flex flex-col lg:flex-row gap-3 lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            <Filter active label="Todos" />
            <Filter label="Em andamento" />
            <Filter label="Finalizadas" />
          </div>

          <div className="flex gap-2 items-center">
            <input
              placeholder="Filtrar cotações..."
              className="h-10 px-4 rounded-2xl border border-slate-300 text-sm w-[250px]"
            />
          </div>
        </div>

        {/* RESUMO IA */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Summary title="Total" value="12" />
          <Summary title="Em andamento" value="4" />
          <Summary title="Finalizadas" value="8" />
          <Summary title="Eficiência" value="Alta" highlight />
        </div>

        {/* TABELA */}
        <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
            <span className="text-sm text-slate-600">Lista de cotações registradas</span>
            <button type="button" className="text-sm px-3 py-1 rounded-xl border border-slate-300">
              Exportar
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-white border-b border-slate-200">
                <tr className="text-left text-slate-500 uppercase text-[11px]">
                  <th className="px-4 py-3">Data</th>
                  <th className="px-4 py-3">Descrição</th>
                  <th className="px-4 py-3">Itens</th>
                  <th className="px-4 py-3">Responsável</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Ações</th>
                </tr>
              </thead>

              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b border-slate-200 hover:bg-slate-50">
                    <td className="px-4 py-4 whitespace-nowrap">{row.data}</td>

                    <td className="px-4 py-4 min-w-[300px]">
                      <div className="font-medium">{row.descricao}</div>
                      <div className="text-xs text-slate-500 mt-1">Gerenciado pela IA DocMaster</div>
                    </td>

                    <td className="px-4 py-4 font-semibold">{row.itens}</td>

                    <td className="px-4 py-4">{row.usuario}</td>

                    <td className="px-4 py-4">
                      <span
                        className={`px-3 py-1 rounded-full border text-xs font-semibold ${statusClass(row.status)}`}
                      >
                        {row.status}
                      </span>
                    </td>

                    <td className="px-4 py-4">
                      <div className="flex gap-2">
                        <Link
                          to="/cotacao"
                          className="px-3 py-1 rounded-xl border text-xs inline-flex items-center justify-center hover:bg-slate-50"
                        >
                          Abrir
                        </Link>
                        <button type="button" className="px-3 py-1 rounded-xl border text-xs">
                          Editar
                        </button>
                        <button type="button" className="px-3 py-1 rounded-xl border text-xs">
                          Excluir
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function Filter({ label, active = false }) {
  return (
    <button
      type="button"
      className={`px-4 py-2 rounded-2xl text-sm font-medium border ${
        active ? 'bg-cyan-600 text-white border-cyan-600' : 'bg-white text-slate-600 border-slate-300'
      }`}
    >
      {label}
    </button>
  );
}

function Summary({ title, value, highlight = false }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
      <div className="text-xs uppercase text-slate-500">{title}</div>
      <div className={`text-lg font-bold mt-1 ${highlight ? 'text-emerald-700' : ''}`}>{value}</div>
    </div>
  );
}
