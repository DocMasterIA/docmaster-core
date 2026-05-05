import React from "react";

type ItemLinha = {
  descricao: string;
  quantidade: string;
  unidade: string;
  valorUnitario: string;
  valorTotal: string;
};

type CampoProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  helper?: string;
};

type TextAreaProps = CampoProps & {
  rows?: number;
};

type LinhaResumo = [string, string, boolean];

type SecaoResumo = {
  titulo: string;
  completo: boolean;
  linhas: LinhaResumo[];
};

const EMPTY_ITEM: ItemLinha = {
  descricao: "",
  quantidade: "",
  unidade: "",
  valorUnitario: "",
  valorTotal: "",
};

const DATA_OPTIONS = ["Data automática", "Datado e assinado digitalmente", "Data manual"];
const TRATAMENTO_NOME = ["Ao senhor", "A senhora"];
const TRATAMENTO_CARGO = ["Senhor", "Senhora"];
const TIPOS_MANUTENCAO = ["Corretiva", "Preventiva"];
const QUEBRA_LINHA = String.fromCharCode(10);
const PLACEHOLDER_DOTACAO = [
  "Ex:",
  "Órgão: 02",
  "Unidade: 05",
  "Projeto/Atividade: 2.045",
  "Elemento de despesa: 3.3.90.39.00",
  "Fonte: 1.500",
].join(QUEBRA_LINHA);

function apenasNumeros(valor: string) {
  return valor
    .split("")
    .filter((char) => char >= "0" && char <= "9")
    .join("");
}

function Icone({ children, className = "h-4 w-4" }: { children: React.ReactNode; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <Icone className={className}>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </Icone>
  );
}

function BotIcon({ className }: { className?: string }) {
  return (
    <Icone className={className}>
      <rect x="5" y="7" width="14" height="12" rx="3" />
      <path d="M12 3v4" />
      <path d="M9 13h.01" />
      <path d="M15 13h.01" />
      <path d="M9 17h6" />
    </Icone>
  );
}

function SparkIcon({ className }: { className?: string }) {
  return (
    <Icone className={className}>
      <path d="M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2 2-5z" />
    </Icone>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <Icone className={className}>
      <path d="M18 6L6 18" />
      <path d="M6 6l12 12" />
    </Icone>
  );
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <Icone className={className}>
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </Icone>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <Icone className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12l2.5 2.5L16 9" />
    </Icone>
  );
}

function formatarData(valor: string) {
  const n = apenasNumeros(valor).slice(0, 8);
  if (n.length <= 2) return n;
  if (n.length <= 4) return `${n.slice(0, 2)}/${n.slice(2)}`;
  return `${n.slice(0, 2)}/${n.slice(2, 4)}/${n.slice(4)}`;
}

function campoPreenchido(valor: string) {
  return valor.trim().length > 0;
}

function ehLetra(char: string) {
  return char.toLowerCase() !== char.toUpperCase();
}

function iniciarComMaiuscula(valor: string) {
  if (!valor) return valor;
  const caracteres = valor.split("");
  const indice = caracteres.findIndex((char) => ehLetra(char));
  if (indice < 0) return valor;
  caracteres[indice] = caracteres[indice].toUpperCase();
  return caracteres.join("");
}

function formatarMoeda(valor: string) {
  const numero = Number(apenasNumeros(valor)) / 100;
  return numero.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function moedaParaNumero(valor: string) {
  const numeros = apenasNumeros(valor);
  if (!numeros) return 0;
  return Number(numeros) / 100;
}

function calcularTotalItem(quantidade: string, unitario: string) {
  const q = Number(quantidade.replace(",", ".")) || 0;
  const v = moedaParaNumero(unitario);
  return (q * v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function calcularValorGlobal(itens: ItemLinha[]) {
  const total = itens.reduce((acc, item) => acc + moedaParaNumero(item.valorTotal), 0);
  return total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatarCNPJ(valor: string) {
  const n = apenasNumeros(valor).slice(0, 14);
  if (n.length <= 2) return n;
  if (n.length <= 5) return `${n.slice(0, 2)}.${n.slice(2)}`;
  if (n.length <= 8) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5)}`;
  if (n.length <= 12) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8)}`;
  return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8, 12)}-${n.slice(12)}`;
}

function removerTratamentoNome(valor: string) {
  return valor.replace("Ao senhor ", "").replace("A senhora ", "").replace("Ao senhor", "").replace("A senhora", "");
}

function removerTratamentoCargo(valor: string) {
  return valor.replace("Senhor ", "").replace("Senhora ", "").replace("Senhor", "").replace("Senhora", "");
}

function Campo({ label, value, onChange, placeholder, helper }: CampoProps) {
  return (
    <div>
      <label className="text-xs font-medium text-slate-600">{label}</label>
      {helper ? <p className="mt-1 text-[11px] text-slate-400">{helper}</p> : null}
      <input
        value={value}
        onChange={(e) => onChange(iniciarComMaiuscula(e.target.value))}
        placeholder={placeholder}
        className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-400"
      />
    </div>
  );
}

function TextAreaCampo({ label, value, onChange, placeholder, helper, rows = 3 }: TextAreaProps) {
  return (
    <div>
      <label className="text-xs font-medium text-slate-600">{label}</label>
      {helper ? <p className="mt-1 text-[11px] text-slate-400">{helper}</p> : null}
      <textarea
        value={value}
        onChange={(e) => onChange(iniciarComMaiuscula(e.target.value))}
        placeholder={placeholder}
        rows={rows}
        className="mt-1 w-full resize-y rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-400"
      />
    </div>
  );
}

function SelectCampo({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  return (
    <div>
      <label className="text-xs font-medium text-slate-600">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-400"
      >
        <option value="">Selecione</option>
        {options.map((opcao) => (
          <option key={opcao} value={opcao}>{opcao}</option>
        ))}
      </select>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function CampoComAdicionar({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-[minmax(0,1fr)_36px] md:items-end">
      <div>{children}</div>
      <button type="button" title="Adicionar" aria-label="Adicionar" className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-300 bg-white text-slate-700 hover:bg-slate-50">
        <PlusIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

function DadosFixosDrawer({ aberto, onClose }: { aberto: boolean; onClose: () => void }) {
  const [tratNome, setTratNome] = React.useState("");
  const [nome, setNome] = React.useState("");
  const [tratCargo, setTratCargo] = React.useState("");
  const [cargo, setCargo] = React.useState("");
  const [responsavel, setResponsavel] = React.useState("");
  const [responsavelCargo, setResponsavelCargo] = React.useState("");
  const [setor, setSetor] = React.useState("");
  const [demanda, setDemanda] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [gestor, setGestor] = React.useState("");
  const [fiscal, setFiscal] = React.useState("");
  const [assinatura, setAssinatura] = React.useState("");
  const [assinaturaCargo, setAssinaturaCargo] = React.useState("");

  const camposDFD: Array<[string, string, React.Dispatch<React.SetStateAction<string>>]> = [
    ["2.1 Setor requisitante (Unidade / Setor / Departamento)", setor, setSetor],
    ["2.2 Responsável pela demanda", demanda, setDemanda],
    ["2.3 E-mail", email, setEmail],
    ["2.4 Nome do(a) gestor(a) de contratos", gestor, setGestor],
    ["2.5 Nome do(a) fiscal de contratos", fiscal, setFiscal],
  ];

  return (
    <>
      {aberto ? <div className="fixed inset-0 z-40 bg-slate-900/20" onClick={onClose} /> : null}
      <aside className={aberto ? "fixed right-0 top-0 z-50 h-full w-full max-w-3xl translate-x-0 border-l border-slate-200 bg-white shadow-2xl transition-transform duration-300" : "fixed right-0 top-0 z-50 h-full w-full max-w-3xl translate-x-full border-l border-slate-200 bg-white shadow-2xl transition-transform duration-300"}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-slate-500">Configuração oculta</div>
            <h3 className="text-base font-semibold text-slate-900">Dados fixos</h3>
          </div>
          <button type="button" onClick={onClose} className="rounded-xl border border-slate-200 p-2 text-slate-500 hover:bg-slate-50">
            <XIcon className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-[calc(100vh-140px)] space-y-4 overflow-y-auto p-5">
          <Card title="1. Solicitação / Ofício">
            <div className="grid grid-cols-1 gap-4">
              <CampoComAdicionar>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                  <SelectCampo label="Tratamento" value={tratNome} onChange={setTratNome} options={TRATAMENTO_NOME} />
                  <div className="md:col-span-2">
                    <Campo label="1.1 A quem é direcionada a solicitação — Nome" value={nome} onChange={setNome} placeholder="Digite o nome" />
                  </div>
                </div>
              </CampoComAdicionar>

              <CampoComAdicionar>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                  <SelectCampo label="Tratamento" value={tratCargo} onChange={setTratCargo} options={TRATAMENTO_CARGO} />
                  <div className="md:col-span-2">
                    <Campo label="1.2 A quem é direcionada a solicitação — Função / Cargo" value={cargo} onChange={setCargo} placeholder="Digite a função ou cargo" />
                  </div>
                </div>
              </CampoComAdicionar>

              <CampoComAdicionar>
                <div>
                  <div className="mb-2 text-xs font-semibold text-slate-700">1.3 Responsável pela solicitação</div>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    <Campo label="Nome do responsável" value={responsavel} onChange={setResponsavel} placeholder="Digite o nome do responsável" />
                    <Campo label="Função / Cargo" value={responsavelCargo} onChange={setResponsavelCargo} placeholder="Digite a função ou cargo" />
                  </div>
                </div>
              </CampoComAdicionar>
            </div>
          </Card>

          <Card title="2. DFD – Documento de Formalização da Demanda">
            <div className="grid grid-cols-1 gap-4">
              {camposDFD.map(([label, value, setter]) => (
                <CampoComAdicionar key={label}>
                  <Campo label={label} value={value} onChange={setter} />
                </CampoComAdicionar>
              ))}

              <CampoComAdicionar>
                <div>
                  <div className="mb-2 text-xs font-semibold text-slate-700">2.6 Responsável pela assinatura da DFD</div>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    <Campo label="Nome do responsável" value={assinatura} onChange={setAssinatura} placeholder="Digite o nome do responsável" />
                    <Campo label="Função / Cargo" value={assinaturaCargo} onChange={setAssinaturaCargo} placeholder="Digite a função ou cargo" />
                  </div>
                </div>
              </CampoComAdicionar>
            </div>
          </Card>
        </div>

        <div className="border-t border-slate-200 p-5">
          <button type="button" onClick={onClose} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800">
            <SparkIcon className="h-4 w-4" />
            Aplicar dados fixos
          </button>
        </div>
      </aside>
    </>
  );
}

function ItensValoresSection({ itens, setItens, setValorGlobal }: { itens: ItemLinha[]; setItens: React.Dispatch<React.SetStateAction<ItemLinha[]>>; setValorGlobal: React.Dispatch<React.SetStateAction<string>> }) {
  function atualizarItem(index: number, campo: keyof ItemLinha, valor: string) {
    setItens((atuais) => {
      const novos = atuais.map((item, i) => {
        if (i !== index) return item;
        const atualizado = { ...item, [campo]: campo === "valorUnitario" ? formatarMoeda(valor) : valor };
        if (campo === "quantidade" || campo === "valorUnitario") {
          atualizado.valorTotal = calcularTotalItem(atualizado.quantidade, atualizado.valorUnitario);
        }
        return atualizado;
      });
      setValorGlobal(calcularValorGlobal(novos));
      return novos;
    });
  }

  function adicionarItem() {
    setItens((atuais) => [...atuais, { ...EMPTY_ITEM }]);
  }

  function removerItem(index: number) {
    setItens((atuais) => {
      const novos = atuais.filter((_, i) => i !== index);
      const final = novos.length ? novos : [{ ...EMPTY_ITEM }];
      setValorGlobal(calcularValorGlobal(final));
      return final;
    });
  }

  return (
    <Card title="Itens e valores">
      <div className="space-y-3">
        {itens.map((item, index) => (
          <div key={index} className="rounded-xl border border-slate-200 p-3">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Item {index + 1}</span>
              {itens.length > 1 ? (
                <button type="button" onClick={() => removerItem(index)} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50">
                  <TrashIcon className="h-3.5 w-3.5" />
                  Remover
                </button>
              ) : null}
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-12">
              <div className="md:col-span-5"><Campo label="Descrição" value={item.descricao} onChange={(v) => atualizarItem(index, "descricao", v)} placeholder="Descreva o item" /></div>
              <div className="md:col-span-2"><Campo label="Quantidade" value={item.quantidade} onChange={(v) => atualizarItem(index, "quantidade", v)} placeholder="1" /></div>
              <div className="md:col-span-2"><Campo label="Unidade medida" value={item.unidade} onChange={(v) => atualizarItem(index, "unidade", v)} placeholder="Ex: Unidade" /></div>
              <div className="md:col-span-2"><Campo label="Valor unitário" value={item.valorUnitario} onChange={(v) => atualizarItem(index, "valorUnitario", v)} placeholder="R$ 0,00" /></div>
              <div className="md:col-span-2"><Campo label="Valor total" value={item.valorTotal} onChange={(v) => atualizarItem(index, "valorTotal", v)} placeholder="R$ 0,00" /></div>
              <div className="flex items-end md:col-span-1">
                <button type="button" onClick={adicionarItem} className="inline-flex w-full items-center justify-center rounded-xl border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                  <PlusIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function ResumoLateral(props: {
  processoAtivo: boolean;
  processo: string;
  orgao: string;
  marca: string;
  modelo: string;
  placa: string;
  tipoManutencao: string;
  revisaoKm: string;
  fornecedor: string;
  cnpj: string;
  dotacaoAtiva: boolean;
  dotacao: string;
  itens: ItemLinha[];
  valorGlobal: string;
  fiscal: string;
  responsavel: string;
  responsavelCargo: string;
  modoData: string;
  dataManual: string;
}) {
  const itensValidos = props.itens.filter((item) => Object.values(item).some(campoPreenchido));

  const secoes: SecaoResumo[] = [
    {
      titulo: "Dados básicos",
      completo: (!props.processoAtivo || campoPreenchido(props.processo)) && campoPreenchido(props.orgao),
      linhas: [
        ["Processo", props.processoAtivo ? props.processo || "Não informado" : "Não se aplica", !props.processoAtivo || campoPreenchido(props.processo)],
        ["Órgão", props.orgao || "Não informado", campoPreenchido(props.orgao)],
      ],
    },
    {
      titulo: "Veículo",
      completo: campoPreenchido(props.marca) && campoPreenchido(props.modelo) && campoPreenchido(props.placa),
      linhas: [
        ["Marca", props.marca || "Não informado", campoPreenchido(props.marca)],
        ["Modelo", props.modelo || "Não informado", campoPreenchido(props.modelo)],
        ["Placa", props.placa || "Não informado", campoPreenchido(props.placa)],
      ],
    },
    {
      titulo: "Manutenção",
      completo: campoPreenchido(props.tipoManutencao) && (props.tipoManutencao !== "Preventiva" || campoPreenchido(props.revisaoKm)),
      linhas: [
        ["Tipo", props.tipoManutencao || "Não informado", campoPreenchido(props.tipoManutencao)],
        ["Revisão/KM", props.tipoManutencao === "Preventiva" ? props.revisaoKm || "Não informado" : "Não se aplica", props.tipoManutencao !== "Preventiva" || campoPreenchido(props.revisaoKm)],
      ],
    },
    {
      titulo: "Fornecedor",
      completo: campoPreenchido(props.fornecedor) && campoPreenchido(props.cnpj),
      linhas: [
        ["Razão social", props.fornecedor || "Não informado", campoPreenchido(props.fornecedor)],
        ["CNPJ", props.cnpj || "Não informado", campoPreenchido(props.cnpj)],
      ],
    },
    {
      titulo: "Dotação orçamentária",
      completo: !props.dotacaoAtiva || campoPreenchido(props.dotacao),
      linhas: [
        ["Situação", props.dotacaoAtiva ? "Informar dotação" : "Não informada", true],
        ["Dotação", props.dotacaoAtiva ? props.dotacao || "Não informada" : "Não se aplica", !props.dotacaoAtiva || campoPreenchido(props.dotacao)],
      ],
    },
    {
      titulo: "Itens",
      completo: itensValidos.length > 0 && campoPreenchido(props.valorGlobal),
      linhas: [
        ["Itens lançados", String(itensValidos.length), itensValidos.length > 0],
        ["Valor global", props.valorGlobal || "Não informado", campoPreenchido(props.valorGlobal)],
      ],
    },
    {
      titulo: "Fiscalização",
      completo: campoPreenchido(props.fiscal),
      linhas: [["Fiscal", props.fiscal || "Não informado", campoPreenchido(props.fiscal)]],
    },
    {
      titulo: "Responsável pelo TR",
      completo: campoPreenchido(props.responsavel) && campoPreenchido(props.responsavelCargo),
      linhas: [
        ["Responsável", props.responsavel || "Não informado", campoPreenchido(props.responsavel)],
        ["Cargo/Função", props.responsavelCargo || "Não informado", campoPreenchido(props.responsavelCargo)],
      ],
    },
    {
      titulo: "Data",
      completo: campoPreenchido(props.modoData) && (props.modoData !== "Data manual" || campoPreenchido(props.dataManual)),
      linhas: [
        ["Modo", props.modoData || "Não informado", campoPreenchido(props.modoData)],
        ["Data", props.modoData === "Data manual" ? props.dataManual || "Não informada" : "Não se aplica", props.modoData !== "Data manual" || campoPreenchido(props.dataManual)],
      ],
    },
  ];

  const completos = secoes.filter((secao) => secao.completo).length;
  const progresso = Math.round((completos / secoes.length) * 100);

  return (
    <aside className="sticky top-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-slate-500">Resumo em tempo real</div>
          <h3 className="mt-1 text-base font-semibold text-slate-900">Painel do documento</h3>
        </div>
        <div className="rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700">{progresso}%</div>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-sky-500 transition-all" style={{ width: `${progresso}%` }} />
      </div>

      <div className="mt-2 text-xs text-slate-500">{completos} de {secoes.length} blocos preenchidos</div>

      <div className="mt-4 space-y-3">
        {secoes.map((secao) => (
          <div key={secao.titulo} className="rounded-xl border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-semibold text-slate-800">{secao.titulo}</div>
              <div className={secao.completo ? "text-emerald-600" : "text-amber-500"}>
                <CheckIcon className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-2 space-y-1">
              {secao.linhas.map(([rotulo, valor, preenchido]) => (
                <div
                  key={rotulo}
                  className={preenchido ? "flex items-start justify-between gap-3 rounded-lg border border-slate-200 border-l-4 border-l-emerald-600 bg-emerald-50/70 px-2 py-1.5 text-xs" : "flex items-start justify-between gap-3 rounded-lg border border-slate-200 border-l-4 border-l-rose-500 bg-rose-50/60 px-2 py-1.5 text-xs"}
                >
                  <span className="text-slate-600">{rotulo}</span>
                  <span className={preenchido ? "max-w-[65%] whitespace-pre-wrap text-right font-medium text-slate-800" : "max-w-[65%] text-right text-slate-400"}>{valor}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
        <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Itens lançados</div>
        <div className="mt-2 space-y-2">
          {itensValidos.length > 0 ? (
            itensValidos.map((item, index) => (
              <div key={index} className="rounded-lg bg-white p-2 text-xs text-slate-700">
                <div className="font-semibold text-slate-800">Item {index + 1}</div>
                <div>{item.descricao || "Sem descrição"}</div>
                <div>Qtd: {item.quantidade || "-"}</div>
                <div>Unidade: {item.unidade || "-"}</div>
                <div>Valor unitário: {item.valorUnitario || "-"}</div>
                <div>Valor total: {item.valorTotal || "-"}</div>
              </div>
            ))
          ) : (
            <div className="text-xs text-slate-500">Nenhum item preenchido ainda.</div>
          )}
        </div>
      </div>
    </aside>
  );
}

function FormularioPrincipal() {
  const [drawerAberto, setDrawerAberto] = React.useState(false);
  const [processoAtivo, setProcessoAtivo] = React.useState(false);
  const [processo, setProcesso] = React.useState("");
  const [orgao, setOrgao] = React.useState("");
  const [marca, setMarca] = React.useState("");
  const [modelo, setModelo] = React.useState("");
  const [placa, setPlaca] = React.useState("");
  const [tipoManutencao, setTipoManutencao] = React.useState("");
  const [revisaoKm, setRevisaoKm] = React.useState("");
  const [fornecedor, setFornecedor] = React.useState("");
  const [cnpj, setCnpj] = React.useState("");
  const [dotacaoAtiva, setDotacaoAtiva] = React.useState(false);
  const [dotacao, setDotacao] = React.useState("");
  const [itens, setItens] = React.useState<ItemLinha[]>([{ ...EMPTY_ITEM }]);
  const [valorGlobal, setValorGlobal] = React.useState("");
  const [fiscal, setFiscal] = React.useState("");
  const [responsavel, setResponsavel] = React.useState("");
  const [responsavelCargo, setResponsavelCargo] = React.useState("");
  const [modoData, setModoData] = React.useState("");
  const [dataManual, setDataManual] = React.useState("");

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section className="w-full rounded-[14px] border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                <BotIcon className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-slate-500">Módulo ativo</div>
                <h2 className="mt-1 text-[18px] font-semibold text-slate-900">Inexigibilidade</h2>
                <p className="mt-1 text-sm font-medium text-slate-950">Fornecedor Exclusivo para manutenção de veículos (Art. 74, I)</p>
              </div>
            </div>
            <button type="button" onClick={() => setDrawerAberto(true)} className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Dados fixos</button>
          </div>
        </div>

        <div className="space-y-4 p-5">
          <Card title="Dados básicos">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="flex items-center gap-2 text-sm text-slate-700 md:col-span-2">
                <input type="checkbox" checked={processoAtivo} onChange={(e) => setProcessoAtivo(e.target.checked)} />
                Informar número do processo (opcional)
              </label>
              {processoAtivo ? <Campo label="Processo" value={processo} onChange={setProcesso} placeholder="Ex: 123/2026" /> : null}
              <CampoComAdicionar>
                <Campo label="Órgão/Unidade responsável pelo veículo" value={orgao} onChange={setOrgao} placeholder="Digite o órgão" />
              </CampoComAdicionar>
            </div>
          </Card>

          <Card title="Dados do veículo">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Campo label="Marca" value={marca} onChange={setMarca} placeholder="Ex: Chevrolet" />
              <Campo label="Modelo" value={modelo} onChange={setModelo} placeholder="Ex: S10" />
              <Campo label="Placa" value={placa} onChange={(v) => setPlaca(v.toUpperCase())} placeholder="Ex: ABC-1234" />
            </div>
          </Card>

          <Card title="Tipo de manutenção">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <button type="button" onClick={() => { setTipoManutencao("Corretiva"); setRevisaoKm(""); }} className={tipoManutencao === "Corretiva" ? "rounded-2xl border border-blue-500 bg-blue-50 px-4 py-3 text-left shadow-sm" : "rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left hover:bg-slate-50"}>
                <div className={tipoManutencao === "Corretiva" ? "text-sm font-semibold text-blue-700" : "text-sm font-semibold text-slate-800"}>Manutenção corretiva</div>
                <div className="mt-1 text-xs text-slate-500">Reparo por falha, defeito ou necessidade imediata.</div>
              </button>
              <button type="button" onClick={() => setTipoManutencao("Preventiva")} className={tipoManutencao === "Preventiva" ? "rounded-2xl border border-blue-500 bg-blue-50 px-4 py-3 text-left shadow-sm" : "rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left hover:bg-slate-50"}>
                <div className={tipoManutencao === "Preventiva" ? "text-sm font-semibold text-blue-700" : "text-sm font-semibold text-slate-800"}>Manutenção preventiva</div>
                <div className="mt-1 text-xs text-slate-500">Revisão programada conforme quilometragem ou plano.</div>
              </button>
            </div>
            {tipoManutencao === "Preventiva" ? (
              <div className="mt-4">
                <Campo label="Quilometragem / Revisão preventiva" value={revisaoKm} onChange={setRevisaoKm} placeholder="Ex: Revisão de 10.000 km" helper="Informe a quilometragem ou o tipo de revisão preventiva." />
              </div>
            ) : null}
          </Card>

          <Card title="Fornecedor exclusivo">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Campo label="Razão social / Nome do fornecedor" value={fornecedor} onChange={setFornecedor} placeholder="Digite a razão social" />
              <Campo label="CNPJ" value={cnpj} onChange={(v) => setCnpj(formatarCNPJ(v))} placeholder="00.000.000/0001-00" />
            </div>
          </Card>

          <Card title="Dotação orçamentária">
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={dotacaoAtiva} onChange={(e) => { setDotacaoAtiva(e.target.checked); if (!e.target.checked) setDotacao(""); }} />
                Informar dotação orçamentária (opcional)
              </label>
              {dotacaoAtiva ? <TextAreaCampo label="Dotação orçamentária" value={dotacao} onChange={setDotacao} rows={3} placeholder={PLACEHOLDER_DOTACAO} helper="Informe manualmente a dotação orçamentária conforme os dados do processo." /> : null}
            </div>
          </Card>

          <ItensValoresSection itens={itens} setItens={setItens} setValorGlobal={setValorGlobal} />

          <div className="max-w-sm">
            <Campo label="Valor total do processo" value={valorGlobal} onChange={setValorGlobal} placeholder="R$ 0,00" />
          </div>

          <Card title="Fiscalização">
            <div className="grid grid-cols-1 gap-4">
              <CampoComAdicionar>
                <Campo label="Nome do fiscal de contratos" value={fiscal} onChange={setFiscal} placeholder="Digite o nome do fiscal de contratos" />
              </CampoComAdicionar>
            </div>
          </Card>

          <Card title="Responsável pelo Termo de Referência">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Campo label="Nome do responsável" value={responsavel} onChange={setResponsavel} placeholder="Digite o nome" />
              <CampoComAdicionar>
                <Campo label="Cargo/Função" value={responsavelCargo} onChange={setResponsavelCargo} placeholder="Digite o cargo" />
              </CampoComAdicionar>
            </div>
          </Card>

          <Card title="Data">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <SelectCampo label="Modo da data" value={modoData} onChange={(v) => { setModoData(v); if (v !== "Data manual") setDataManual(""); }} options={DATA_OPTIONS} />
              {modoData === "Data manual" ? <Campo label="Data manual" value={dataManual} onChange={(v) => setDataManual(formatarData(v))} placeholder="01/02/2026" /> : null}
            </div>
          </Card>

          <button className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700">
            <SparkIcon className="h-4 w-4" />
            Gerar Documento com IA
          </button>
        </div>
      </section>

      <DadosFixosDrawer aberto={drawerAberto} onClose={() => setDrawerAberto(false)} />
      <ResumoLateral
        processoAtivo={processoAtivo}
        processo={processo}
        orgao={orgao}
        marca={marca}
        modelo={modelo}
        placa={placa}
        tipoManutencao={tipoManutencao}
        revisaoKm={revisaoKm}
        fornecedor={fornecedor}
        cnpj={cnpj}
        dotacaoAtiva={dotacaoAtiva}
        dotacao={dotacao}
        itens={itens}
        valorGlobal={valorGlobal}
        fiscal={fiscal}
        responsavel={responsavel}
        responsavelCargo={responsavelCargo}
        modoData={modoData}
        dataManual={dataManual}
      />
    </div>
  );
}

export default function GeradorDocumentosPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <div className="mx-auto w-full max-w-7xl space-y-4 px-4 py-4 md:px-6">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight text-slate-900">Gerador de Documentos</h1>
          <p className="mt-1 text-sm text-slate-500">Tela simplificada para teste: somente Inexigibilidade.</p>
        </div>
        <FormularioPrincipal />
      </div>
    </div>
  );
}

export function __tests__() {
  console.assert(DATA_OPTIONS.includes("Data manual"), "A lista de data deve permitir data manual");
  console.assert(Object.keys(EMPTY_ITEM).length === 5, "Estrutura de item deve conter 5 campos");
  console.assert(formatarData("01022026") === "01/02/2026", "Data manual deve formatar dd/mm/aaaa");
  console.assert(formatarData("01a02b2026") === "01/02/2026", "Data deve ignorar caracteres não numéricos");
  console.assert(campoPreenchido("abc") === true, "campoPreenchido deve reconhecer texto preenchido");
  console.assert(iniciarComMaiuscula("marcelo") === "Marcelo", "Campos preenchíveis devem iniciar com letra maiúscula");
  console.assert(iniciarComMaiuscula("  marcelo") === "  Marcelo", "Capitalização deve preservar espaços iniciais");
  console.assert(iniciarComMaiuscula("  águia") === "  Águia", "Capitalização deve aceitar letras acentuadas");
  console.assert(campoPreenchido("   ") === false, "campoPreenchido deve rejeitar espaços vazios");
  console.assert(formatarCNPJ("12345678000199") === "12.345.678/0001-99", "CNPJ deve ser formatado corretamente");
  console.assert(formatarMoeda("1000").includes("10,00"), "Moeda deve formatar centavos corretamente");
  console.assert(calcularTotalItem("2", "R$ 10,00").includes("20,00"), "Total do item deve multiplicar quantidade por valor unitário");
  console.assert(calcularValorGlobal([{ ...EMPTY_ITEM, valorTotal: "R$ 20,00" }, { ...EMPTY_ITEM, valorTotal: "R$ 30,00" }]).includes("50,00"), "Valor global deve somar os itens");
  console.assert(removerTratamentoNome("Ao senhor João") === "João", "Deve remover tratamento do nome");
  console.assert(removerTratamentoCargo("Senhora Secretária") === "Secretária", "Deve remover tratamento do cargo");
  console.assert(TIPOS_MANUTENCAO.includes("Preventiva"), "Tipos de manutenção devem permitir preventiva");
  console.assert(PLACEHOLDER_DOTACAO.includes("Órgão"), "Placeholder da dotação deve existir sem quebrar string");
  console.assert(typeof TextAreaCampo === "function", "Campo de texto longo para dotação deve existir");
  console.assert(typeof GeradorDocumentosPage === "function", "Componente principal deve existir");
  return "ok";
}
