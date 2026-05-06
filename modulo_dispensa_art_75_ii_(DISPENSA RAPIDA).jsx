import React from "react";

const DATA_OPTIONS = ["Data automática", "Datado e assinado digitalmente", "Data manual"];
const TRATAMENTO_NOME = ["Ao senhor", "A senhora"];
const TRATAMENTO_CARGO = ["Senhor", "Senhora"];
const CABECALHOS_DOCUMENTO = [
  "Cabeçalho padrão do município",
  "Cabeçalho do Fundo Municipal de Saúde",
  "Cabeçalho da Assistência Social",
  "Cabeçalho da Secretaria de Educação",
  "Cabeçalho sem brasão",
];

const TEXTO_PADRAO_ENDERECO_PROPOSTAS =
  "Nome Município - UF, localizado na rua xxxxxxxxxxxxx, Nº xx, bairro xxx, no horário das 07h00min às 11h00min e das 13h00min às 17h00min, de segunda a sexta-feira.";

const PLACEHOLDER_DOTACAO =
  "Ex:\nÓrgão: 02\nUnidade: 05\nProjeto/Atividade: 2.045\nElemento de despesa: 3.3.90.39.00\nFonte: 1.500";

const EMPTY_ITEM = { descricao: "", quantidade: "", unidade: "", mediaValor: "" };

function apenasNumeros(valor) {
  return valor.replace(/\D/g, "");
}

function campoPreenchido(valor) {
  return String(valor || "").trim().length > 0;
}

function primeiraMaiuscula(valor) {
  const indice = valor.search(/[A-Za-zÀ-ÿ]/);
  if (indice < 0) return valor;
  return valor.slice(0, indice) + valor[indice].toUpperCase() + valor.slice(indice + 1);
}

function formatarData(valor) {
  const n = apenasNumeros(valor).slice(0, 8);
  if (n.length <= 2) return n;
  if (n.length <= 4) return `${n.slice(0, 2)}/${n.slice(2)}`;
  return `${n.slice(0, 2)}/${n.slice(2, 4)}/${n.slice(4)}`;
}

function formatarMoeda(valor) {
  const numero = Number(apenasNumeros(valor)) / 100;
  return numero.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function moedaParaNumero(valor) {
  const numeros = apenasNumeros(valor || "");
  return numeros ? Number(numeros) / 100 : 0;
}

function quantidadeParaNumero(valor) {
  return Number(String(valor || "").replace(",", ".")) || 0;
}

function calcularValorTotalEstimado(itens) {
  const total = itens.reduce((acc, item) => acc + quantidadeParaNumero(item.quantidade) * moedaParaNumero(item.mediaValor), 0);
  return total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function criarPerfilDadosFixos(id, nomeCadastro) {
  return {
    id,
    nomeCadastro,
    tratNome: "",
    nome: "",
    tratCargo: "",
    cargo: "",
    responsavel: "",
    responsavelCargo: "",
    setor: "",
    demanda: "",
    email: "",
    gestor: "",
    fiscal: "",
    assinatura: "",
    assinaturaCargo: "",
    responsavelTR: "",
    responsavelCargoTR: "",
    enderecoEntregaPropostas: TEXTO_PADRAO_ENDERECO_PROPOSTAS,
    emailRecebimentoPropostas: "",
  };
}

function gerarObjetoTexto(contratado, setor, caracteristicas) {
  const objeto = contratado.trim() || "objeto não informado";
  const destino = setor.trim() ? `, visando atender às demandas de ${setor.trim()}` : "";
  const detalhes = caracteristicas.trim() ? `, observadas as seguintes características mínimas: ${caracteristicas.trim()}` : "";
  return `${primeiraMaiuscula(objeto)}${destino}${detalhes}.`;
}

function gerarJustificativaTexto(contratado, setor, caracteristicas) {
  const objeto = contratado.trim() || "o objeto indicado";
  const destino = setor.trim() ? ` do(a) ${setor.trim()}` : " da Administração Pública";
  const detalhes = caracteristicas.trim() ? ` A contratação deverá observar as características mínimas informadas: ${caracteristicas.trim()}.` : "";
  return `A presente contratação justifica-se pela necessidade de assegurar ${objeto} para atendimento das demandas${destino}, garantindo a continuidade, eficiência e adequada prestação dos serviços públicos.${detalhes}`;
}

function Campo({ label, value, onChange, placeholder, helper }) {
  return (
    <div>
      <label className="text-xs font-medium text-slate-600">{label}</label>
      {helper ? <p className="mt-1 text-[11px] text-slate-400">{helper}</p> : null}
      <input
        value={value}
        onChange={(e) => onChange(primeiraMaiuscula(e.target.value))}
        placeholder={placeholder}
        className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-sky-400"
      />
    </div>
  );
}

function Area({ label, value, onChange, placeholder, helper, rows = 3 }) {
  return (
    <div>
      <label className="text-xs font-medium text-slate-600">{label}</label>
      {helper ? <p className="mt-1 text-[11px] text-slate-400">{helper}</p> : null}
      <textarea
        value={value}
        onChange={(e) => onChange(primeiraMaiuscula(e.target.value))}
        placeholder={placeholder}
        rows={rows}
        className="mt-1 w-full resize-y rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-sky-400"
      />
    </div>
  );
}

function SelectCampo({ label, value, onChange, options, compacto = false }) {
  return (
    <div>
      <label className={compacto ? "text-[11px] font-medium text-slate-500" : "text-xs font-medium text-slate-600"}>{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={(compacto ? "mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-xs text-slate-800 outline-none focus:border-sky-400" : "mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-sky-400")}
      >
        <option value="">Selecione</option>
        {options.map((opcao) => (
          <option key={opcao} value={opcao}>{opcao}</option>
        ))}
      </select>
    </div>
  );
}

function Card({ title, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function DadosFixosDrawer({ aberto, onClose, perfis, setPerfis, perfilSelecionadoId, setPerfilSelecionadoId, onSelecionarPerfil }) {
  const [form, setForm] = React.useState(criarPerfilDadosFixos("", ""));

  function setCampo(campo, valor) {
    setForm((atual) => ({ ...atual, [campo]: valor }));
  }

  function carregarPerfil(id) {
    setPerfilSelecionadoId(id);
    const perfil = perfis.find((item) => item.id === id);
    setForm(perfil || criarPerfilDadosFixos("", ""));
    onSelecionarPerfil(id);
  }

  function novoCadastro() {
    setPerfilSelecionadoId("");
    setForm(criarPerfilDadosFixos("", ""));
    onSelecionarPerfil("");
  }

  function salvarCadastro() {
    const id = perfilSelecionadoId || `perfil-${Date.now()}`;
    const perfil = { ...form, id, nomeCadastro: form.nomeCadastro.trim() || "Cadastro sem nome" };
    setPerfis((atuais) => perfilSelecionadoId ? atuais.map((item) => item.id === id ? perfil : item) : [...atuais, perfil]);
    setPerfilSelecionadoId(id);
    onSelecionarPerfil(id);
  }

  function excluirCadastro() {
    if (!perfilSelecionadoId) return;
    setPerfis((atuais) => atuais.filter((item) => item.id !== perfilSelecionadoId));
    novoCadastro();
  }

  return (
    <>
      {aberto ? <div className="fixed inset-0 z-40 bg-slate-900/20" onClick={onClose} /> : null}
      <aside className={(aberto ? "translate-x-0" : "translate-x-full") + " fixed right-0 top-0 z-50 h-full w-full max-w-3xl border-l border-slate-200 bg-white shadow-2xl transition-transform duration-300"}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-slate-500">Configuração oculta</div>
            <h3 className="text-base font-semibold text-slate-900">Dados fixos</h3>
            <p className="mt-1 text-xs text-slate-500">Cadastre e reutilize informações fixas por órgão ou unidade.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-xl border border-slate-200 px-3 py-2 text-slate-500">×</button>
        </div>

        <div className="max-h-[calc(100vh-92px)] space-y-4 overflow-y-auto p-5">
          <Card title="Cadastros de órgãos">
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-600">Órgão cadastrado</label>
                <select value={perfilSelecionadoId} onChange={(e) => carregarPerfil(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-sky-400">
                  <option value="">Selecione um cadastro salvo</option>
                  {perfis.map((perfil) => <option key={perfil.id} value={perfil.id}>{perfil.nomeCadastro}</option>)}
                </select>
              </div>
              <Campo label="Nome do cadastro" value={form.nomeCadastro} onChange={(v) => setCampo("nomeCadastro", v)} placeholder="Ex: Fundo Municipal de Saúde" />
              <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                <button type="button" onClick={novoCadastro} className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold">Novo cadastro</button>
                <button type="button" onClick={salvarCadastro} className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white">Salvar cadastro</button>
                <button type="button" onClick={excluirCadastro} disabled={!perfilSelecionadoId} className="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-700 disabled:opacity-40">Excluir cadastro</button>
              </div>
            </div>
          </Card>

          <Card title="1. Solicitação / Ofício">
            <div className="grid grid-cols-1 gap-4">
              <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                <SelectCampo label="Tratamento" value={form.tratNome} onChange={(v) => setCampo("tratNome", v)} options={TRATAMENTO_NOME} />
                <div className="md:col-span-2"><Campo label="1.1 A quem é direcionada a solicitação — Nome" value={form.nome} onChange={(v) => setCampo("nome", v)} /></div>
              </div>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                <SelectCampo label="Tratamento" value={form.tratCargo} onChange={(v) => setCampo("tratCargo", v)} options={TRATAMENTO_CARGO} />
                <div className="md:col-span-2"><Campo label="1.2 A quem é direcionada a solicitação — Função / Cargo" value={form.cargo} onChange={(v) => setCampo("cargo", v)} /></div>
              </div>
              <div>
                <div className="mb-2 text-xs font-semibold text-slate-700">1.3 Responsável pela solicitação</div>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  <Campo label="Nome do responsável" value={form.responsavel} onChange={(v) => setCampo("responsavel", v)} />
                  <Campo label="Função / Cargo" value={form.responsavelCargo} onChange={(v) => setCampo("responsavelCargo", v)} />
                </div>
              </div>
            </div>
          </Card>

          <Card title="2. DFD – Documento de Formalização da Demanda">
            <div className="grid grid-cols-1 gap-4">
              <Campo label="2.1 Setor requisitante (Unidade / Setor / Departamento)" value={form.setor} onChange={(v) => setCampo("setor", v)} />
              <Campo label="2.2 Responsável pela demanda" value={form.demanda} onChange={(v) => setCampo("demanda", v)} />
              <Campo label="2.3 E-mail" value={form.email} onChange={(v) => setCampo("email", v)} />
              <Campo label="2.4 Nome do(a) gestor(a) de contratos" value={form.gestor} onChange={(v) => setCampo("gestor", v)} />
              <Campo label="2.5 Nome do(a) fiscal de contratos" value={form.fiscal} onChange={(v) => setCampo("fiscal", v)} />
              <div>
                <div className="mb-2 text-xs font-semibold text-slate-700">2.6 Responsável pela assinatura da DFD</div>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  <Campo label="Nome do responsável" value={form.assinatura} onChange={(v) => setCampo("assinatura", v)} />
                  <Campo label="Função / Cargo" value={form.assinaturaCargo} onChange={(v) => setCampo("assinaturaCargo", v)} />
                </div>
              </div>
            </div>
          </Card>

          <Card title="3. Termo de Referência">
            <div className="grid grid-cols-1 gap-4">
              <Area label="Endereço presencial para envio ou entrega de propostas" value={form.enderecoEntregaPropostas} onChange={(v) => setCampo("enderecoEntregaPropostas", v)} rows={3} helper="Texto pré-preenchido e editável. Ajuste o município, UF, endereço, número, bairro e horário conforme o órgão." />
              <Campo label="E-mail para recebimento de propostas" value={form.emailRecebimentoPropostas} onChange={(v) => setCampo("emailRecebimentoPropostas", v)} placeholder="Ex: propostas@municipio.go.gov.br" />
              <div>
                <div className="mb-2 text-xs font-semibold text-slate-700">Responsável pelo Termo de Referência</div>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  <Campo label="Nome do responsável" value={form.responsavelTR} onChange={(v) => setCampo("responsavelTR", v)} />
                  <Campo label="Cargo/Função" value={form.responsavelCargoTR} onChange={(v) => setCampo("responsavelCargoTR", v)} />
                </div>
              </div>
            </div>
          </Card>
        </div>
      </aside>
    </>
  );
}

function ItensValoresSection({ itens, setItens }) {
  function atualizarItem(index, campo, valor) {
    setItens((atuais) => atuais.map((item, i) => i === index ? { ...item, [campo]: campo === "mediaValor" ? formatarMoeda(valor) : valor } : item));
  }

  return (
    <Card title="Itens e valores">
      <div className="space-y-3">
        {itens.map((item, index) => (
          <div key={index} className="rounded-xl border border-slate-200 p-3">
            <div className="mb-2 flex justify-between text-xs font-semibold text-slate-500">
              <span>Item {index + 1}</span>
              {itens.length > 1 ? <button type="button" onClick={() => setItens((atuais) => atuais.filter((_, i) => i !== index))} className="text-red-600">Remover</button> : null}
            </div>
            <div className="grid grid-cols-12 gap-3">
              <div className="col-span-12 md:col-span-5"><Campo label="Descrição" value={item.descricao} onChange={(v) => atualizarItem(index, "descricao", v)} /></div>
              <div className="col-span-4 md:col-span-2"><Campo label="Qtd." value={item.quantidade} onChange={(v) => atualizarItem(index, "quantidade", v)} /></div>
              <div className="col-span-4 md:col-span-2"><Campo label="Unidade de medida" value={item.unidade} onChange={(v) => atualizarItem(index, "unidade", v)} /></div>
              <div className="col-span-4 md:col-span-3"><Campo label="Média de valor (opcional)" value={item.mediaValor} onChange={(v) => atualizarItem(index, "mediaValor", v)} /></div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-col gap-3 border-t border-slate-200 pt-4 md:flex-row md:items-center md:justify-between">
        <button type="button" onClick={() => setItens((atuais) => [...atuais, { ...EMPTY_ITEM }])} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold">Adicionar item</button>
        <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm">
          <span className="font-medium text-slate-600">Valor total estimado: </span>
          <span className="font-bold text-slate-950">{calcularValorTotalEstimado(itens)}</span>
        </div>
      </div>
    </Card>
  );
}

function ResumoLateral({ processoAtivo, processo, cabecalho, orgao, objeto, dotacaoAtiva, dotacao, data }) {
  const secoes = [
    {
      titulo: "Dados básicos",
      completo: campoPreenchido(cabecalho) && campoPreenchido(orgao) && (!processoAtivo || campoPreenchido(processo)),
      linhas: [
        ["Cabeçalho", cabecalho || "Não informado", campoPreenchido(cabecalho)],
        ["Órgão", orgao || "Não informado", campoPreenchido(orgao)],
        ["Processo", processoAtivo ? processo || "Não informado" : "Não se aplica", !processoAtivo || campoPreenchido(processo)],
      ],
    },
    {
      titulo: "Objeto da contratação",
      completo: campoPreenchido(objeto),
      linhas: [["O que será contratado", objeto || "Não informado", campoPreenchido(objeto)]],
    },
    {
      titulo: "Dotação orçamentária",
      completo: !dotacaoAtiva || campoPreenchido(dotacao),
      linhas: [
        ["Situação", dotacaoAtiva ? "Informar dotação" : "Não informada", true],
        ["Dotação", dotacaoAtiva ? dotacao || "Não informada" : "Não se aplica", !dotacaoAtiva || campoPreenchido(dotacao)],
      ],
    },
    {
      titulo: "Data",
      completo: campoPreenchido(data),
      linhas: [["Data / modo", data || "Não informada", campoPreenchido(data)]],
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
              <div className={secao.completo ? "text-emerald-600" : "text-amber-500"}>{secao.completo ? "✓" : "!"}</div>
            </div>
            <div className="mt-2 space-y-1">
              {secao.linhas.map(([rotulo, valor, preenchido]) => (
                <div key={rotulo} className={preenchido ? "flex items-start justify-between gap-3 rounded-lg border border-slate-200 border-l-4 border-l-emerald-600 bg-emerald-50/70 px-2 py-1.5 text-xs" : "flex items-start justify-between gap-3 rounded-lg border border-slate-200 border-l-4 border-l-rose-500 bg-rose-50/60 px-2 py-1.5 text-xs"}>
                  <span className="text-slate-600">{rotulo}</span>
                  <span className={preenchido ? "max-w-[65%] whitespace-pre-wrap text-right font-medium text-slate-800" : "max-w-[65%] text-right text-slate-400"}>{valor}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

function FormularioPrincipal() {
  const [drawerAberto, setDrawerAberto] = React.useState(false);
  const [perfis, setPerfis] = React.useState([]);
  const [perfilSelecionadoId, setPerfilSelecionadoId] = React.useState("");
  const [cabecalho, setCabecalho] = React.useState("");
  const [processoAtivo, setProcessoAtivo] = React.useState(false);
  const [processo, setProcesso] = React.useState("");
  const [objetoContratado, setObjetoContratado] = React.useState("");
  const [dotacaoAtiva, setDotacaoAtiva] = React.useState(false);
  const [dotacao, setDotacao] = React.useState("");
  const [modoData, setModoData] = React.useState("");
  const [dataManual, setDataManual] = React.useState("");

  const perfilSelecionado = perfis.find((perfil) => perfil.id === perfilSelecionadoId);

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-start justify-between border-b border-slate-200 p-5">
          <div>
            <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-[11px] font-bold uppercase text-blue-700">Módulo ativo</span>
            <h2 className="mt-2 text-lg font-semibold">Este módulo gera Solicitação/Ofício, DFD e Termo de Referência</h2>
          </div>
          <button type="button" onClick={() => setDrawerAberto(true)} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold">Dados fixos</button>
        </div>

        <div className="space-y-4 p-5">
          <section className="rounded-2xl border border-slate-200 bg-slate-50/80 p-3 shadow-sm">
            <div className="mb-2 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-slate-800">Dados básicos</h3>
            </div>
            <div className="grid items-end gap-3 md:grid-cols-[1.1fr_1.1fr_auto]">
              <SelectCampo compacto label="Cabeçalho do documento" value={cabecalho} onChange={setCabecalho} options={CABECALHOS_DOCUMENTO} />

              <div>
                <label className="text-[11px] font-medium text-slate-500">Órgão / dados fixos</label>
                <select value={perfilSelecionadoId} onChange={(e) => setPerfilSelecionadoId(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-xs text-slate-800 outline-none focus:border-sky-400">
                  <option value="">Selecione um órgão cadastrado</option>
                  {perfis.map((perfil) => <option key={perfil.id} value={perfil.id}>{perfil.nomeCadastro}</option>)}
                </select>
              </div>

              <label className="flex h-[34px] items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-600">
                <input type="checkbox" checked={processoAtivo} onChange={(e) => setProcessoAtivo(e.target.checked)} />Processo (opcional)
              </label>
            </div>
            {processoAtivo ? (
              <div className="mt-3 max-w-xs">
                <Campo label="Número do processo (opcional)" value={processo} onChange={setProcesso} />
              </div>
            ) : null}
          </section>

          <Card title="Objeto da contratação">
            <Area label="O que será contratado?" value={objetoContratado} onChange={setObjetoContratado} placeholder={`Ex: Aquisição de material de expediente para Secretaria da Administração
10 canetas azul, 2 grampeadores, 10 resmas de papel A4`} rows={4} />
          </Card>

          <Card title="Dotação orçamentária">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={dotacaoAtiva} onChange={(e) => { setDotacaoAtiva(e.target.checked); if (!e.target.checked) setDotacao(""); }} />Informar dotação orçamentária (opcional)
            </label>
            {dotacaoAtiva ? <div className="mt-3"><Area label="Dotação orçamentária" value={dotacao} onChange={setDotacao} placeholder={PLACEHOLDER_DOTACAO} /></div> : null}
          </Card>

          <Card title="Data">
            <div className="grid gap-4 md:grid-cols-2">
              <SelectCampo label="Modo da data" value={modoData} onChange={(valor) => { setModoData(valor); if (valor !== "Data manual") setDataManual(""); }} options={DATA_OPTIONS} />
              {modoData === "Data manual" ? <Campo label="Data manual" value={dataManual} onChange={(valor) => setDataManual(formatarData(valor))} /> : null}
            </div>
          </Card>

          <button className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white">Gerar documento com IA</button>
        </div>
      </section>

      <DadosFixosDrawer aberto={drawerAberto} onClose={() => setDrawerAberto(false)} perfis={perfis} setPerfis={setPerfis} perfilSelecionadoId={perfilSelecionadoId} setPerfilSelecionadoId={setPerfilSelecionadoId} onSelecionarPerfil={setPerfilSelecionadoId} />

      <ResumoLateral processoAtivo={processoAtivo} processo={processo} cabecalho={cabecalho} orgao={perfilSelecionado?.nomeCadastro || ""} objeto={objetoContratado} dotacaoAtiva={dotacaoAtiva} dotacao={dotacao} data={modoData === "Data manual" ? dataManual : modoData} />
    </div>
  );
}

export default function GeradorDocumentosPage() {
  return (
    <div className="min-h-screen bg-slate-100">
      <div className="mx-auto max-w-7xl space-y-4 px-4 py-4 md:px-6">
        <div>
          <h1 className="text-xl font-semibold">Gerador de Documentos</h1>
          <p className="mt-1 text-sm text-slate-500">Geração de Solicitação, DFD e Termo de Referência.</p>
        </div>
        <FormularioPrincipal />
      </div>
    </div>
  );
}
