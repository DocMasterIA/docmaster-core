import { Link } from 'react-router-dom';
import {
  Search,
  Eye,
  Pencil,
  Trash2,
  Paperclip,
  FileSpreadsheet,
  Plus,
  ChevronDown,
  Calculator,
  User,
  CalendarDays,
  LogOut,
  Play,
  Receipt,
  Upload,
} from "lucide-react";

export default function DocMasterDetalheCotacaoFuncional() {
  const itens = [
    {
      id: 1,
      nome: "1. MANUTENÇÃO PREVENTIVA E CORRETIVA DE AR CONDICIONADO",
      fontes: [0, 2, 0, 1, 0],
      qtd: 3,
      und: "Serv.",
      valor: "R$ 721,50",
      base: "R$ 15,00",
      variacao: "20%",
      status: "Completo",
      alerta: true,
    },
    {
      id: 2,
      nome: "2. SERVIÇO DE LIMPEZA E SANITIZAÇÃO AMBIENTAL",
      fontes: [0, 2, 0, 1, 0],
      qtd: 1,
      und: "Serv.",
      valor: "R$ 156,00",
      base: "R$ 18,00",
      variacao: "15%",
      status: "Completo",
      alerta: false,
    },
    {
      id: 3,
      nome: "3. SERVIÇO DE SUPORTE TÉCNICO E MANUTENÇÃO DE TI",
      fontes: [0, 2, 0, 1, 0],
      qtd: 1,
      und: "Serv.",
      valor: "R$ 438,89",
      base: "R$ 420,00",
      variacao: "10%",
      status: "Completo",
      alerta: false,
    },
    {
      id: 4,
      nome: "4. SERVIÇO DE MANUTENÇÃO PREVENTIVA DE ELEVADORES",
      fontes: [0, 2, 1, 1, 1],
      qtd: 1,
      und: "Serv.",
      valor: "R$ 533,33",
      base: "R$ 500,00",
      variacao: "12%",
      status: "Completo",
      alerta: false,
    },
  ];

  return (
    <div className="min-h-screen bg-[#f3f4f6] p-3 text-slate-800">
      <div className="mx-auto max-w-[1180px] space-y-3">
        <header className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-[32px] font-semibold leading-none tracking-tight text-slate-900">
              Detalhes da Cotação
            </h1>
            <div className="mt-1.5 flex items-center gap-2 text-[13px] text-slate-500">
              <Link to="/" className="hover:text-slate-800 hover:underline">
                Cotações
              </Link>
              <span>›</span>
              <span className="text-slate-700">Cotação #CT-2026-00421</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <span className="rounded-lg bg-[#eef3ef] px-3 py-2 text-xs font-semibold text-[#446f62]">
              Ambiente: Varejo
            </span>
            <div className="flex items-center gap-2 text-[13px] font-medium text-slate-700">
              <span>🇧🇷</span>
              <span>UF: GO — 4: Prefeitura de Itajá</span>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#2f7a68] text-sm font-semibold text-white">
              DL
            </div>
            <button type="button" className="flex h-9 items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-[#7a4444]">
              <LogOut className="h-4 w-4" />
              Sair
            </button>
          </div>
        </header>

        <section className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <TopCard
            icon={<User className="h-5 w-5 text-[#2f7a68]" />}
            iconBg="bg-[#e7f1ec]"
            title="Criado por"
            value="Diniz Luiz Martins Neto"
            badge="Responsável"
          />
          <TopCard
            icon={<CalendarDays className="h-5 w-5 text-[#6974a7]" />}
            iconBg="bg-[#eceef8]"
            title="Criado em"
            value="1 de Abril de 2026 às 14:49"
          />
          <TopCard
            icon={<Receipt className="h-5 w-5 text-[#2f7a68]" />}
            iconBg="bg-[#e7f1ec]"
            title="Valor Total da Cotação"
            value="R$ 1.849,72"
            highlight
            withChart
          />
        </section>

        <section className="rounded-[18px] border border-slate-200 bg-white p-3 shadow-sm">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#e7f1ec]">
                <Calculator className="h-5 w-5 text-[#2f7a68]" />
              </div>
              <div>
                <div className="text-[13px] font-semibold text-slate-900">Fórmula de Cálculo</div>
                <div className="text-[12px] text-slate-500">Aplicada para consolidação</div>
              </div>
              <button type="button" className="ml-2 flex h-9 items-center gap-3 rounded-lg border border-slate-300 bg-white px-3 text-[13px] font-medium">
                <span>Média aritmética dos preços obtidos</span>
                <ChevronDown className="h-4 w-4 text-slate-500" />
              </button>
            </div>

            <div className="flex w-full items-center justify-end gap-1 overflow-hidden xl:gap-2">
              <button type="button" className="flex h-9 items-center gap-1.5 rounded-lg bg-[#0f8a78] px-3 text-[13px] font-semibold text-white shadow-sm whitespace-nowrap">
                <Plus className="h-4 w-4" />
                Novo Item
              </button>
              <button type="button" className="flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-[13px] font-semibold whitespace-nowrap">
                <Upload className="h-4 w-4" />
                Importar Planilha Preenchida
              </button>
              <button type="button" className="flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-[13px] font-semibold whitespace-nowrap">
                <FileSpreadsheet className="h-4 w-4" />
                Baixar Planilha Modelo
              </button>
              <button type="button" className="flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-[13px] font-semibold whitespace-nowrap">
                <Paperclip className="h-4 w-4" />
                Anexar Cotação do Fornecedor
              </button>
              <button type="button" className="flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-[13px] font-semibold whitespace-nowrap">
                <FileSpreadsheet className="h-4 w-4 shrink-0" />
                <span className="leading-none">Gerar Relatório</span>
              </button>
            </div>
          </div>
        </section>

        <section className="overflow-hidden rounded-[18px] border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-2 border-b border-slate-200 p-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex min-w-0 flex-1 items-center gap-2">
              <div className="flex h-9 w-full max-w-[260px] items-center gap-2 rounded-lg border border-slate-300 bg-white px-3">
                <Search className="h-4 w-4 text-slate-500" />
                <input
                  placeholder="Buscar item..."
                  className="w-full bg-transparent text-[13px] outline-none placeholder:text-slate-400"
                />
              </div>
              <button type="button" className="flex h-9 items-center gap-2 rounded-lg bg-[#0f8a78] px-4 text-sm font-semibold text-white">
                <Plus className="h-4 w-4" />
                Novo Item
              </button>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2">
              <Link
                to="/busca-item"
                className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#dff0e9] px-4 text-sm font-semibold text-[#2f7a68]"
              >
                <Play className="h-4 w-4" />
                Iniciar Cotação Automática
              </Link>
            </div>
          </div>

          <table className="w-full table-fixed text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-white">
                <th rowSpan={2} className="w-[240px] px-2 py-3 text-left align-bottom text-[14px] font-semibold text-slate-800">
                  <div className="flex items-center gap-2">
                    <input type="checkbox" className="h-4 w-4 rounded border-slate-300" />
                    <span>Nome do Item</span>
                  </div>
                </th>
                <th colSpan={5} className="border-x border-slate-200 bg-[#eef7f0] px-2 py-2 text-center text-[14px] font-semibold text-slate-800">
                  Fontes de Preço (Art. 5º)
                </th>
                <th rowSpan={2} className="w-[36px] px-1 py-3 text-center align-bottom text-[11px] font-semibold text-slate-800">
                  Qtd.
                </th>
                <th rowSpan={2} className="w-[46px] px-1 py-3 text-center align-bottom text-[11px] font-semibold text-slate-800">
                  Und.
                </th>
                <th rowSpan={2} className="w-[72px] px-1 py-3 text-center align-bottom text-[11px] font-semibold text-slate-800">
                  Preço Total
                </th>
                <th rowSpan={2} className="w-[180px] px-2 py-3 text-left align-bottom text-[14px] font-semibold text-slate-800">
                  Faixa Regional do Item
                </th>
                <th rowSpan={2} className="w-[82px] px-1 py-3 text-center align-bottom text-[13px] font-semibold text-slate-800">
                  Status
                </th>
                <th rowSpan={2} className="w-[92px] px-1 py-3 text-center align-bottom text-[13px] font-semibold text-slate-800">
                  Ações
                </th>
              </tr>
              <tr className="border-b border-slate-200 bg-white text-slate-700">
                <th className="w-[60px] border-x border-slate-200 bg-[#eef7f0] px-1 py-2">
                  <SourceHeader icon="🏛" title="Preços Governamentais" subtitle="(Inciso I)" />
                </th>
                <th className="w-[60px] border-r border-slate-200 bg-[#eef7f0] px-1 py-2">
                  <SourceHeader icon="🏢" title="Outros Entes Públicos" subtitle="(Inciso II)" />
                </th>
                <th className="w-[60px] border-r border-slate-200 bg-[#eef7f0] px-1 py-2">
                  <SourceHeader icon="🌐" title="Domínio Amplo" subtitle="(Inciso III)" />
                </th>
                <th className="w-[60px] border-r border-slate-200 bg-[#eef7f0] px-1 py-2">
                  <SourceHeader icon="💲" title="Cotação Direta" subtitle="(Inciso IV)" />
                </th>
                <th className="w-[60px] border-r border-slate-200 bg-[#eef7f0] px-1 py-2">
                  <SourceHeader icon="📄" title="Notas Fiscais" subtitle="(Inciso V)" />
                </th>
              </tr>
            </thead>
            <tbody>
              {itens.map((item) => (
                <tr key={item.id} className="border-b border-slate-200 hover:bg-slate-50/60">
                  <td className="px-2 py-2 align-middle">
                    <div className="flex items-start gap-2">
                      <input type="checkbox" className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300" />
                      <div>
                        <div className="break-words text-[10px] font-semibold uppercase leading-4 text-slate-900">
                          {item.nome}
                        </div>
                        {item.alerta ? (
                          <div className="mt-1 inline-flex items-center gap-1 rounded-md bg-[#fff4e5] px-2 py-0.5 text-[9px] font-semibold text-[#a15c00]">
                            ⚠ Similaridade parcial identificada
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </td>
                  {item.fontes.map((fonte, index) => (
                    <td key={index} className="border-r border-slate-100 px-1 py-2 align-middle">
                      <SourceBadge value={fonte} variant={index === 1 || index === 3 ? "green" : "gray"} />
                    </td>
                  ))}
                  <td className="px-1 py-2 align-middle text-center text-[11px] font-semibold">{item.qtd}</td>
                  <td className="px-1 py-2 align-middle text-center text-[11px]">{item.und}</td>
                  <td className="whitespace-nowrap px-1 py-2 align-middle text-center text-[11px] font-bold text-slate-900">{item.valor}</td>
                  <td className="px-1 py-2 align-middle">
                    <div className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-[#fafbfc] px-2 py-1 text-[10px]">
                      <span className="font-semibold text-slate-500">BASE</span>
                      <span className="font-bold text-slate-900">{item.base}</span>
                      <span className="text-slate-300">·</span>
                      <span className="font-semibold text-slate-500">VAR</span>
                      <span className="font-bold text-slate-900">{item.variacao}</span>
                    </div>
                  </td>
                  <td className="px-1 py-2 align-middle text-center">
                    <span className="whitespace-nowrap rounded-full bg-[#dff0e9] px-2 py-1 text-[10px] font-semibold text-[#2f7a68]">
                      {item.status}
                    </span>
                  </td>
                  <td className="px-1 py-2 align-middle">
                    <div className="flex items-center justify-center gap-1">
                      <IconAction>
                        <Eye className="h-3.5 w-3.5" />
                      </IconAction>
                      <IconAction>
                        <Pencil className="h-3.5 w-3.5" />
                      </IconAction>
                      <IconAction danger>
                        <Trash2 className="h-3.5 w-3.5" />
                      </IconAction>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex flex-col gap-3 border-t border-slate-200 bg-white px-3 py-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="text-[12px] text-slate-600">Mostrando 4 Itens · Página 1 de 1</div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1">
                <button type="button" className="h-8 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-600">‹</button>
                <button type="button" className="h-8 w-8 rounded-lg bg-[#0f8a78] text-sm font-semibold text-white">1</button>
                <button type="button" className="h-8 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-600">›</button>
              </div>
              <div className="flex items-center gap-2 text-[12px]">
                <span className="font-semibold text-slate-700">Itens/pág.:</span>
                <button type="button" className="flex h-8 min-w-[90px] items-center justify-between gap-2 rounded-lg border border-slate-300 bg-white px-3 text-sm">
                  <span>10</span>
                  <ChevronDown className="h-4 w-4 text-slate-500" />
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function TopCard({ icon, iconBg, title, value, badge, highlight = false, withChart = false }) {
  return (
    <div className="flex min-h-[82px] items-center justify-between gap-3 rounded-[18px] border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex min-w-0 items-center gap-3">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${iconBg}`}>
          {icon}
        </div>
        <div className="min-w-0">
          <div className="text-[12px] font-semibold text-slate-800">{title}</div>
          <div className={`mt-1 text-[15px] font-semibold ${highlight ? "text-[#2f7a68]" : "text-slate-900"}`}>
            {value}
          </div>
          {badge ? (
            <span className="mt-1.5 inline-flex rounded-md bg-[#eef0f6] px-2 py-0.5 text-[11px] font-semibold text-[#545f87]">
              {badge}
            </span>
          ) : null}
        </div>
      </div>
      {withChart ? (
        <svg width="72" height="32" viewBox="0 0 120 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="shrink-0">
          <defs>
            <linearGradient id="g1" x1="0" y1="0" x2="120" y2="0" gradientUnits="userSpaceOnUse">
              <stop stopColor="#2F7A68" />
              <stop offset="1" stopColor="#6FBFA9" />
            </linearGradient>
          </defs>
          <path
            d="M4 36C18 28 28 30 38 26C48 22 58 20 70 14C82 8 94 10 104 6"
            stroke="url(#g1)"
            strokeWidth="2.6"
            strokeLinecap="round"
            style={{ strokeDasharray: 140, strokeDashoffset: 140, animation: "drawLine 1.2s ease-out forwards" }}
          />
          <path
            d="M4 42C18 34 28 36 38 32C48 28 58 26 70 20C82 14 94 16 104 12"
            stroke="#D9EFE8"
            strokeWidth="2"
            strokeLinecap="round"
            style={{ strokeDasharray: 140, strokeDashoffset: 140, animation: "drawLineSoft 1.4s ease-out forwards" }}
          />
          <circle
            cx="104"
            cy="6"
            r="3"
            fill="#2F7A68"
            style={{ opacity: 0, transformOrigin: "104px 6px", animation: "popDot 0.35s ease-out 1.05s forwards" }}
          />
          <style>{`
            @keyframes drawLine { to { stroke-dashoffset: 0; } }
            @keyframes drawLineSoft { to { stroke-dashoffset: 0; } }
            @keyframes popDot { 0% { opacity: 0; transform: scale(0.4); } 100% { opacity: 1; transform: scale(1); } }
          `}</style>
        </svg>
      ) : null}
    </div>
  );
}

function SourceHeader({ icon, title, subtitle }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 text-center leading-tight">
      <span className="text-[16px]">{icon}</span>
      <span className="break-words whitespace-normal text-[9px] font-semibold">{title}</span>
      <span className="text-[9px] font-bold text-slate-700">{subtitle}</span>
    </div>
  );
}

function SourceBadge({ value, variant = "gray" }) {
  const classes =
    variant === "green"
      ? "border-[#cbe3d9] bg-[#dff0e9] text-[#2f7a68]"
      : "border-[#dddddd] bg-[#ededed] text-slate-700";

  return (
    <div className={`flex h-7 min-w-[44px] items-center justify-center rounded-lg border px-2 text-[10px] font-semibold ${classes}`}>
      <span>{value}</span>
    </div>
  );
}

function IconAction({ children, danger = false }) {
  return (
    <button
      type="button"
      className={`flex h-7 w-7 items-center justify-center rounded-md border ${danger ? "border-[#e5c9c9] bg-white text-[#b05d5d]" : "border-slate-300 bg-white text-slate-600"}`}
    >
      {children}
    </button>
  );
}
