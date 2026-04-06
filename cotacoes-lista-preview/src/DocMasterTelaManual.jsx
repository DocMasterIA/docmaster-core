import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, Play } from 'lucide-react';

export default function TelaResultadosComSemaforoIA() {
  const resultados = [
    {
      id: 1,
      titulo: 'Registro de Preços para futura e eventual aquisição de medicamentos e alimentação especial',
      descricao: 'SILYBUM MARIANUM (SILIMARINA) EXTRATO 100 MG (FORFIG)',
      quantidade: '8000 Comprimidos',
      uf: 'SP',
      data: '10/03/2026',
      valor: 'R$ 0,66',
      statusIa: 'Alta',
      observacao: 'Correspondência altamente compatível',
      selecionado: true,
    },
    {
      id: 2,
      titulo: 'Registro de Preços para futura e eventual aquisição de medicamentos e alimentação especial',
      descricao: 'SILYBUM MARIANUM (SILIMARINA) EXTRATO 200 MG (FORFIG)',
      quantidade: '8000 Comprimidos',
      uf: 'SP',
      data: '10/03/2026',
      valor: 'R$ 0,75',
      statusIa: 'Média',
      observacao: 'Descrição próxima, requer conferência de dosagem',
      selecionado: false,
    },
    {
      id: 3,
      titulo: 'Aquisição de medicamentos manipulados',
      descricao: 'CARDUS MARIANUS 100 MG (FORFIG)',
      quantidade: '6000 Cápsulas',
      uf: 'SP',
      data: '09/03/2026',
      valor: 'R$ 0,20',
      statusIa: 'Baixa',
      observacao: 'Similaridade parcial identificada',
      selecionado: false,
    },
    {
      id: 4,
      titulo: 'FORFIG',
      descricao: 'FORFIG SILYBUM MARIANUM 200 MG CAP DURA CT BL AL PLAS PVC/PVDC TRANS X 60 A5B',
      quantidade: '1 Unidade',
      uf: 'Todos',
      data: '03/2026',
      valor: 'R$ 158,28',
      statusIa: 'Baixa',
      observacao: 'Unidade e contexto divergentes do item principal',
      selecionado: false,
    },
  ];

  const [ordenarPor, setOrdenarPor] = useState('Produto');
  const [ordenarPorOpen, setOrdenarPorOpen] = useState(false);
  const [ordem, setOrdem] = useState('Decrescente');
  const [ordemOpen, setOrdemOpen] = useState(false);
  const [periodo, setPeriodo] = useState('Último Ano');
  const [tipo, setTipo] = useState('Material');
  const [tipoOpen, setTipoOpen] = useState(false);
  const [modalidade, setModalidade] = useState('Pregão');
  const [modalidadeOpen, setModalidadeOpen] = useState(false);
  const [periodoOpen, setPeriodoOpen] = useState(false);
  const [valorBase, setValorBase] = useState('R$ 15,00');
  const [variacao, setVariacao] = useState('20%');
  const [descricao, setDescricao] = useState('FORFIG');

  return (
    <div className="min-h-screen bg-[#f4f6f8] p-4 text-slate-800">
      <div className="mx-auto max-w-[1280px] space-y-4">
        <div className="rounded-[18px] border border-slate-200 bg-white shadow-sm">
          <div className="space-y-4 px-4 py-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2 text-[13px] font-semibold">
                <button
                  type="button"
                  className="border-b-2 border-[#0f8a78] px-2 pb-2 text-[#0f8a78]"
                >
                  BUSCA AVANÇADA
                </button>
              </div>
              <Link to="/busca-item" className="text-[13px] font-medium text-[#0f8a78] hover:underline">
                ← Voltar à busca compacta
              </Link>
            </div>

            <div className="flex flex-wrap items-end gap-2">
              <div className="min-w-[280px] flex-[1.3]">
                <InputField label="Descrição" value={descricao} onChange={setDescricao} />
              </div>

              <div className="relative min-w-[170px] flex-[0.6]">
                <button
                  type="button"
                  onClick={() => setPeriodoOpen((v) => !v)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-left"
                >
                  <div className="text-[11px] text-slate-500">Período</div>
                  <div className="mt-1 flex items-center justify-between text-[13px] text-slate-700">
                    <span>{periodo}</span>
                    <ChevronDown className="h-4 w-4 text-slate-400" />
                  </div>
                </button>

                {periodoOpen && (
                  <div className="absolute z-20 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-md">
                    {['Último Mês', 'Últimos 3 Meses', 'Últimos 6 Meses'].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          setPeriodo(opt);
                          setPeriodoOpen(false);
                        }}
                        className="block w-full px-3 py-2 text-left text-[13px] text-slate-700 hover:bg-slate-50"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="relative min-w-[220px] flex-[0.8]">
                <button
                  type="button"
                  onClick={() => setTipoOpen((v) => !v)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-left"
                >
                  <div className="text-[11px] text-slate-500">Tipo</div>
                  <div className="mt-1 flex items-center justify-between text-[13px] text-slate-700">
                    <span>{tipo}</span>
                    <ChevronDown className="h-4 w-4 text-slate-400" />
                  </div>
                </button>

                {tipoOpen && (
                  <div className="absolute z-20 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-md">
                    {['Material', 'Serviço', 'Materiais e Serviços'].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          setTipo(opt);
                          setTipoOpen(false);
                        }}
                        className="block w-full px-3 py-2 text-left text-[13px] text-slate-700 hover:bg-slate-50"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div className="relative min-w-[220px] flex-[0.9]">
                <button
                  type="button"
                  onClick={() => setModalidadeOpen((v) => !v)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-left"
                >
                  <div className="text-[11px] text-slate-500">Modalidade</div>
                  <div className="mt-1 flex items-center justify-between text-[13px] text-slate-700">
                    <span>{modalidade}</span>
                    <ChevronDown className="h-4 w-4 text-slate-400" />
                  </div>
                </button>

                {modalidadeOpen && (
                  <div className="absolute z-20 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-md">
                    {[
                      'Todas',
                      'Pregão',
                      'Pregão Eletrônico',
                      'Compra Direta',
                      'Concorrência',
                      'Leilão',
                      'Inexigibilidade',
                      'Chamada Pública',
                    ].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          setModalidade(opt);
                          setModalidadeOpen(false);
                        }}
                        className="block w-full px-3 py-2 text-left text-[13px] text-slate-700 hover:bg-slate-50"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button
                type="button"
                className="h-[42px] rounded-lg bg-[#11b59b] px-6 text-[13px] font-semibold text-white"
              >
                BUSCAR
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative min-w-[200px]">
                <button
                  type="button"
                  onClick={() => setOrdenarPorOpen((v) => !v)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-left"
                >
                  <div className="text-[11px] text-slate-500">Ordenar por</div>
                  <div className="mt-1 flex items-center justify-between text-[13px] font-medium text-slate-700">
                    <span>{ordenarPor}</span>
                    <ChevronDown className="h-4 w-4 text-slate-400" />
                  </div>
                </button>

                {ordenarPorOpen && (
                  <div className="absolute z-20 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-md">
                    {['Produto', 'Quantidade', 'Valor', 'UF'].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          setOrdenarPor(opt);
                          setOrdenarPorOpen(false);
                        }}
                        className="block w-full px-3 py-2 text-left text-[13px] text-slate-700 hover:bg-slate-50"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="relative min-w-[180px]">
                <button
                  type="button"
                  onClick={() => setOrdemOpen((v) => !v)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-left"
                >
                  <div className="text-[11px] text-slate-500">&nbsp;</div>
                  <div className="mt-1 flex items-center justify-between text-[13px] font-medium text-slate-700">
                    <span>{ordem}</span>
                    <ChevronDown className="h-4 w-4 text-slate-400" />
                  </div>
                </button>

                {ordemOpen && (
                  <div className="absolute z-20 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-md">
                    {['Decrescente', 'Crescente'].map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          setOrdem(opt);
                          setOrdemOpen(false);
                        }}
                        className="block w-full px-3 py-2 text-left text-[13px] text-slate-700 hover:bg-slate-50"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="min-w-[150px]">
                <InputField label="Valor Base" value={valorBase} onChange={setValorBase} />
              </div>
              <div className="min-w-[130px]">
                <InputField label="Variação %" value={variacao} onChange={setVariacao} />
              </div>
              <button
                type="button"
                className="flex h-10 items-center gap-2 rounded-lg bg-[#dff0e9] px-4 text-sm font-semibold text-[#2f7a68]"
              >
                <Play className="h-4 w-4" />
                Selecionar Melhores pela IA
              </button>

              {resultados.some((r) => r.selecionado) && (
                <button
                  type="button"
                  className="flex h-10 items-center gap-2 rounded-lg bg-[#0f8a78] px-4 text-sm font-semibold text-white shadow"
                >
                  <Play className="h-4 w-4" />
                  Incluir Manualmente
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <ResumoCard titulo="Alta Confiabilidade" valor="1" cor="verde" />
          <ResumoCard titulo="Média Confiabilidade" valor="1" cor="amarelo" />
          <ResumoCard titulo="Baixa Confiabilidade" valor="2" cor="vermelho" />
          <ResumoCard titulo="Selecionadas pela IA" valor="1" cor="azul" />
        </div>

        <div className="space-y-3">
          {resultados.map((item) => (
            <ResultadoCard key={item.id} item={item} />
          ))}
        </div>
      </div>
    </div>
  );
}

function InputField({ label, value, onChange }) {
  return (
    <div className="rounded-lg border border-slate-300 bg-white px-3 py-2">
      <div className="text-[11px] text-slate-500">{label}</div>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full bg-transparent text-[13px] text-slate-700 outline-none"
      />
    </div>
  );
}

function ResumoCard({ titulo, valor, cor }) {
  const cores = {
    verde: 'bg-[#e7f6ee] text-[#1f7a53] border-[#cfe9da]',
    amarelo: 'bg-[#fff6e6] text-[#9a6a00] border-[#f0dfb3]',
    vermelho: 'bg-[#fff0f0] text-[#b54747] border-[#f0d0d0]',
    azul: 'bg-[#edf4ff] text-[#2f6f86] border-[#d9e6f5]',
  };

  return (
    <div className="rounded-[16px] border bg-white px-4 py-3 shadow-sm">
      <div className="text-[12px] text-slate-500">{titulo}</div>
      <div className="mt-2 flex items-center justify-between">
        <div className="text-[24px] font-bold text-slate-800">{valor}</div>
        <div className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${cores[cor]}`}>IA</div>
      </div>
    </div>
  );
}

function ResultadoCard({ item }) {
  const statusMap = {
    Alta: {
      faixa: 'bg-[#e7f6ee] border-[#cfe9da]',
      badge: 'bg-[#dff0e9] text-[#1f7a53]',
      semaforo: 'bg-[#26a269]',
    },
    Média: {
      faixa: 'bg-[#fffaf0] border-[#f0dfb3]',
      badge: 'bg-[#fff0c7] text-[#9a6a00]',
      semaforo: 'bg-[#e0a100]',
    },
    Baixa: {
      faixa: 'bg-[#fff7f7] border-[#f0d0d0]',
      badge: 'bg-[#ffe1e1] text-[#b54747]',
      semaforo: 'bg-[#d94b4b]',
    },
  };

  const estilo = statusMap[item.statusIa];

  return (
    <div className={`overflow-hidden rounded-[18px] border ${estilo.faixa} bg-white shadow-sm`}>
      <div className="grid grid-cols-1 items-stretch lg:grid-cols-[1.7fr_0.8fr_0.65fr_0.65fr_0.85fr_0.55fr]">
        <div className="flex items-center gap-3 border-b border-slate-200 px-4 py-4 lg:border-b-0 lg:border-r">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-[#e7f1ec] text-[11px] font-bold text-[#2f7a68]">
            RP
          </div>
          <div className="min-w-0">
            <div className="text-[13px] font-semibold leading-tight text-[#0f8a78]">{item.titulo}</div>
            <div className="mt-1 text-[12px] leading-tight text-slate-600">{item.descricao}</div>
            <div className="mt-2 inline-flex items-center gap-2 rounded-md bg-slate-50 px-2 py-1 text-[11px] font-semibold text-slate-700">
              <span className={`h-2.5 w-2.5 rounded-full ${estilo.semaforo}`} />
              <span>IA: {item.statusIa} confiabilidade</span>
            </div>
            <div className="mt-1 text-[11px] text-slate-500">{item.observacao}</div>
          </div>
        </div>

        <InfoColuna label="Quantidade" value={item.quantidade} />
        <InfoColuna label="UF" value={item.uf} />
        <InfoColuna label="Data" value={item.data} />

        <div className="flex flex-col justify-center border-b border-slate-200 px-4 py-4 lg:border-b-0 lg:border-l">
          <div className="text-[11px] text-slate-500">Valor Unit.</div>
          <div className="mt-1 text-[18px] font-bold text-slate-800">{item.valor}</div>
          <div className={`mt-2 inline-flex w-fit rounded-full px-2.5 py-1 text-[11px] font-semibold ${estilo.badge}`}>
            {item.statusIa}
          </div>
        </div>

        <div className="flex items-center justify-center border-slate-200 px-4 py-4 lg:border-l">
          <input type="checkbox" checked={item.selecionado} readOnly className="h-4 w-4 rounded border-slate-300" />
        </div>
      </div>
    </div>
  );
}

function InfoColuna({ label, value }) {
  return (
    <div className="flex flex-col justify-center border-b border-slate-200 px-4 py-4 lg:border-b-0 lg:border-l">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="mt-1 text-[13px] font-semibold text-slate-700">{value}</div>
    </div>
  );
}
