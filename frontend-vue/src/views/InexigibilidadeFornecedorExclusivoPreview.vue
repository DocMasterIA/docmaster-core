<template>
  <div class="fe-page">
    <div class="fe-wrap">
      <div class="fe-grid">
        <section class="fe-main">
          <div class="fe-main-head">
            <div class="fe-main-title">
              <div>
                <small>Módulo ativo</small>
                <h2>Inexigibilidade</h2>
                <p>Fornecedor Exclusivo Geral — Bens, Serviços e Soluções (Art. 74, I)</p>
              </div>
            </div>
            <button type="button" class="fe-btn-secondary" @click="drawerOpen = true">Dados fixos</button>
          </div>

          <div class="fe-main-body">
            <article class="fe-card">
              <h3>Dados básicos</h3>
              <div class="fe-body">
                <label class="fe-check">
                  <input v-model="processoAtivo" type="checkbox" />
                  Informar número do processo (opcional)
                </label>
                <div class="fe-grid-2">
                  <div v-if="processoAtivo" class="fe-field">
                    <label>Processo</label>
                    <input v-model="processo" placeholder="Ex: 123/2026" />
                  </div>
                  <div class="fe-field">
                    <label>Órgão/Unidade responsável pelo equipamento</label>
                    <input v-model="orgao" placeholder="Digite o órgão" />
                  </div>
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Objeto específico</h3>
              <div class="fe-body">
                <div class="fe-field">
                  <label>Selecione o objeto específico da contratação</label>
                  <select v-model="objetoEspecifico">
                    <option value="">Selecione</option>
                    <option v-for="o in objetoOptions" :key="o" :value="o">{{ o }}</option>
                  </select>
                </div>
                <div v-if="objetoEspecifico === 'Outro'" class="fe-field">
                  <label>Descreva o objeto específico da contratação</label>
                  <input
                    v-model="outroObjetoEspecifico"
                    placeholder="Ex: Fornecimento de kit de manutenção original"
                  />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Dados do equipamento</h3>
              <div class="fe-body fe-grid-3">
                <div class="fe-field"><label>Equipamento</label><input v-model="equipamento" /></div>
                <div class="fe-field"><label>Marca</label><input v-model="marca" /></div>
                <div class="fe-field"><label>Modelo</label><input v-model="modelo" /></div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Fornecedor exclusivo</h3>
              <div class="fe-body fe-grid-2">
                <div class="fe-field">
                  <label>Razão social / Nome do fornecedor</label>
                  <input v-model="fornecedor" @input="fornecedor = iniciarComMaiuscula(fornecedor)" />
                </div>
                <div class="fe-field">
                  <label>CNPJ</label>
                  <input :value="cnpj" placeholder="00.000.000/0001-00" @input="cnpj = formatarCNPJ(String($event.target.value || ''))" />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Dotação orçamentária</h3>
              <div class="fe-body">
                <label class="fe-check">
                  <input v-model="dotacaoAtiva" type="checkbox" />
                  Informar dotação orçamentária (opcional)
                </label>
                <div v-if="dotacaoAtiva" class="fe-field">
                  <label>Dotação orçamentária</label>
                  <textarea v-model="dotacao" rows="3" :placeholder="placeholderDotacao" />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Itens e valores</h3>
              <div class="fe-body">
                <div v-for="(item, index) in itens" :key="index" class="fe-item">
                  <div class="fe-item-head">
                    <span>Item {{ index + 1 }}</span>
                    <button v-if="itens.length > 1" type="button" class="fe-link-danger" @click="removerItem(index)">Remover</button>
                  </div>
                  <div class="fe-grid-item">
                    <div class="fe-field"><label>Descrição</label><input :value="item.descricao" @input="atualizarItem(index, 'descricao', $event)" /></div>
                    <div class="fe-field"><label>Quantidade</label><input :value="item.quantidade" @input="atualizarItem(index, 'quantidade', $event)" /></div>
                    <div class="fe-field"><label>Unidade medida</label><input :value="item.unidade" @input="atualizarItem(index, 'unidade', $event)" /></div>
                    <div class="fe-field"><label>Valor unitário</label><input :value="item.valorUnitario" @input="atualizarItem(index, 'valorUnitario', $event)" /></div>
                    <div class="fe-field"><label>Valor total</label><input :value="item.valorTotal" @input="atualizarItem(index, 'valorTotal', $event)" /></div>
                    <button type="button" class="fe-btn-secondary" @click="adicionarItem">+</button>
                  </div>
                </div>
                <div class="fe-field fe-half">
                  <label>Valor total do processo</label>
                  <input v-model="valorGlobal" />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Fiscalização</h3>
              <div class="fe-body"><div class="fe-field"><label>Nome do fiscal de contratos</label><input v-model="fiscal" /></div></div>
            </article>

            <article class="fe-card">
              <h3>Responsável pelo Termo de Referência</h3>
              <div class="fe-body fe-grid-2">
                <div class="fe-field"><label>Nome do responsável</label><input v-model="responsavel" /></div>
                <div class="fe-field"><label>Cargo/Função</label><input v-model="responsavelCargo" /></div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Data</h3>
              <div class="fe-body fe-grid-2">
                <div class="fe-field">
                  <label>Modo da data</label>
                  <select v-model="modoData">
                    <option value="">Selecione</option>
                    <option v-for="o in dataOptions" :key="o" :value="o">{{ o }}</option>
                  </select>
                </div>
                <div v-if="modoData === 'Data manual'" class="fe-field">
                  <label>Data manual</label>
                  <input :value="dataManual" @input="dataManual = formatarData(String($event.target.value || ''))" />
                </div>
              </div>
            </article>
          </div>
        </section>

        <aside class="fe-summary">
          <div class="fe-summary-head">
            <small>Resumo em tempo real</small>
            <h3>Painel do documento</h3>
            <span>{{ progresso }}%</span>
          </div>
          <div class="fe-progress"><div :style="{ width: `${progresso}%` }"></div></div>
          <p>{{ completos }} de {{ secoes.length }} blocos preenchidos</p>
          <div class="fe-summary-list">
            <article v-for="sec in secoes" :key="sec.titulo" class="fe-summary-card">
              <header>{{ sec.titulo }} <strong :class="sec.completo ? 'ok' : 'warn'">{{ sec.completo ? 'OK' : 'Pendente' }}</strong></header>
              <div v-for="linha in sec.linhas" :key="linha[0]" :class="['fe-line', linha[2] ? 'is-ok' : 'is-warn']">
                <span>{{ linha[0] }}</span><b>{{ linha[1] }}</b>
              </div>
            </article>
          </div>
        </aside>
      </div>
    </div>

    <div v-if="drawerOpen" class="fe-overlay" @click="drawerOpen = false"></div>
    <aside :class="['fe-drawer', drawerOpen && 'is-open']">
      <div class="fe-drawer-head">
        <div><small>Configuração oculta</small><h3>Dados fixos</h3></div>
        <button type="button" class="fe-btn-secondary" @click="drawerOpen = false">X</button>
      </div>
      <div class="fe-drawer-body">
        <article class="fe-card">
          <h3>1. Solicitação / Ofício</h3>
          <div class="fe-body">
            <div class="fe-grid-3">
              <div class="fe-field">
                <label>Tratamento</label>
                <select v-model="tratNome"><option value="">Selecione</option><option v-for="o in tratamentoNome" :key="o" :value="o">{{ o }}</option></select>
              </div>
              <div class="fe-field fe-col-2"><label>1.1 A quem é direcionada a solicitação — Nome</label><input v-model="nome" /></div>
            </div>
            <div class="fe-grid-3">
              <div class="fe-field">
                <label>Tratamento</label>
                <select v-model="tratCargo"><option value="">Selecione</option><option v-for="o in tratamentoCargo" :key="o" :value="o">{{ o }}</option></select>
              </div>
              <div class="fe-field fe-col-2"><label>1.2 A quem é direcionada a solicitação — Função/Cargo</label><input v-model="cargo" /></div>
            </div>
          </div>
        </article>
      </div>
      <div class="fe-drawer-foot">
        <button type="button" class="fe-btn-primary" @click="drawerOpen = false">Aplicar dados fixos</button>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const dataOptions = ['Data automática', 'Datado e assinado digitalmente', 'Data manual'];
const tratamentoNome = ['Ao senhor', 'A senhora'];
const tratamentoCargo = ['Senhor', 'Senhora'];
const objetoOptions = [
  'Aquisição de bens/produtos', 'Fornecimento de peças', 'Peças originais', 'Peças de reposição',
  'Componentes e acessórios', 'Insumos e materiais', 'Prestação de serviços', 'Manutenção preventiva',
  'Manutenção corretiva', 'Manutenção preventiva e corretiva', 'Assistência técnica autorizada',
  'Suporte técnico especializado', 'Outro',
];
const placeholderDotacao = 'Ex:\nÓrgão: 02\nUnidade: 05\nProjeto/Atividade: 2.045\nElemento de despesa: 3.3.90.39.00\nFonte: 1.500';

const drawerOpen = ref(false);
const processoAtivo = ref(false);
const processo = ref('');
const orgao = ref('');
const objetoEspecifico = ref('');
const outroObjetoEspecifico = ref('');
const equipamento = ref('');
const marca = ref('');
const modelo = ref('');
const fornecedor = ref('');
const cnpj = ref('');
const dotacaoAtiva = ref(false);
const dotacao = ref('');
const itens = ref([{ descricao: '', quantidade: '', unidade: '', valorUnitario: '', valorTotal: '' }]);
const valorGlobal = ref('');
const fiscal = ref('');
const responsavel = ref('');
const responsavelCargo = ref('');
const modoData = ref('');
const dataManual = ref('');

const tratNome = ref('');
const nome = ref('');
const tratCargo = ref('');
const cargo = ref('');

function apenasNumeros(valor) { return String(valor || '').replace(/\D/g, ''); }
function campoPreenchido(valor) { return String(valor || '').trim().length > 0; }
function formatarData(valor) {
  const n = apenasNumeros(valor).slice(0, 8);
  if (n.length <= 2) return n;
  if (n.length <= 4) return `${n.slice(0, 2)}/${n.slice(2)}`;
  return `${n.slice(0, 2)}/${n.slice(2, 4)}/${n.slice(4)}`;
}
function iniciarComMaiuscula(v) {
  const txt = String(v || '');
  const idx = txt.search(/[A-Za-zÀ-ÿ]/);
  if (idx < 0) return txt;
  return txt.slice(0, idx) + txt[idx].toUpperCase() + txt.slice(idx + 1);
}
function formatarMoeda(v) {
  const n = Number(apenasNumeros(v)) / 100;
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function moedaParaNumero(v) {
  const n = apenasNumeros(v || '');
  return n ? Number(n) / 100 : 0;
}
function calcularTotalItem(quantidade, unitario) {
  const q = Number(String(quantidade || '').replace(',', '.')) || 0;
  const val = moedaParaNumero(unitario);
  return (q * val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function calcularValorGlobal() {
  const total = itens.value.reduce((acc, item) => acc + moedaParaNumero(item.valorTotal), 0);
  return total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function formatarCNPJ(v) {
  const n = apenasNumeros(v).slice(0, 14);
  if (n.length <= 2) return n;
  if (n.length <= 5) return `${n.slice(0, 2)}.${n.slice(2)}`;
  if (n.length <= 8) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5)}`;
  if (n.length <= 12) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8)}`;
  return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8, 12)}-${n.slice(12)}`;
}

function atualizarItem(index, campo, ev) {
  const valorRaw = String(ev.target?.value || '');
  const valor = campo === 'valorUnitario' ? formatarMoeda(valorRaw) : iniciarComMaiuscula(valorRaw);
  itens.value = itens.value.map((it, i) => {
    if (i !== index) return it;
    const next = { ...it, [campo]: valor };
    if (campo === 'quantidade' || campo === 'valorUnitario') next.valorTotal = calcularTotalItem(next.quantidade, next.valorUnitario);
    return next;
  });
  valorGlobal.value = calcularValorGlobal();
}
function adicionarItem() { itens.value.push({ descricao: '', quantidade: '', unidade: '', valorUnitario: '', valorTotal: '' }); }
function removerItem(index) {
  itens.value = itens.value.filter((_, i) => i !== index);
  if (!itens.value.length) itens.value = [{ descricao: '', quantidade: '', unidade: '', valorUnitario: '', valorTotal: '' }];
  valorGlobal.value = calcularValorGlobal();
}

const itensValidos = computed(() => itens.value.filter((it) => Object.values(it).some(campoPreenchido)));
const secoes = computed(() => [
  {
    titulo: 'Dados básicos',
    completo: (!processoAtivo.value || campoPreenchido(processo.value)) && campoPreenchido(orgao.value),
    linhas: [
      ['Processo', processoAtivo.value ? processo.value || 'Não informado' : 'Não se aplica', !processoAtivo.value || campoPreenchido(processo.value)],
      ['Órgão', orgao.value || 'Não informado', campoPreenchido(orgao.value)],
    ],
  },
  {
    titulo: 'Objeto específico',
    completo: campoPreenchido(objetoEspecifico.value) && (objetoEspecifico.value !== 'Outro' || campoPreenchido(outroObjetoEspecifico.value)),
    linhas: [
      ['Objeto específico', objetoEspecifico.value || 'Não informado', campoPreenchido(objetoEspecifico.value)],
      ['Descrição', objetoEspecifico.value === 'Outro' ? (outroObjetoEspecifico.value || 'Não informada') : 'Não se aplica', objetoEspecifico.value !== 'Outro' || campoPreenchido(outroObjetoEspecifico.value)],
    ],
  },
  {
    titulo: 'Equipamento',
    completo: campoPreenchido(equipamento.value) && campoPreenchido(marca.value) && campoPreenchido(modelo.value),
    linhas: [
      ['Equipamento', equipamento.value || 'Não informado', campoPreenchido(equipamento.value)],
      ['Marca', marca.value || 'Não informado', campoPreenchido(marca.value)],
      ['Modelo', modelo.value || 'Não informado', campoPreenchido(modelo.value)],
    ],
  },
]);
const completos = computed(() => secoes.value.filter((s) => s.completo).length);
const progresso = computed(() => Math.round((completos.value / secoes.value.length) * 100));
</script>

<style scoped>
.fe-page { min-height: 100vh; background: #f1f5f9; padding: 16px; }
.fe-wrap { max-width: 1280px; margin: 0 auto; }
.fe-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 14px; }
.fe-main, .fe-summary, .fe-drawer, .fe-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; }
.fe-main-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding: 14px; }
.fe-main-title small { font-size: 11px; text-transform: uppercase; color: #64748b; }
.fe-main-title h2 { margin: 4px 0 0; font-size: 18px; }
.fe-main-title p { margin: 2px 0 0; color: #64748b; font-size: 13px; }
.fe-main-body { padding: 14px; display: grid; gap: 12px; }
.fe-card { padding: 12px; }
.fe-card h3 { margin: 0 0 8px; font-size: 14px; }
.fe-body { display: grid; gap: 8px; }
.fe-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.fe-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
.fe-grid-item { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; align-items: end; }
.fe-field label { font-size: 12px; color: #475569; display: block; margin-bottom: 3px; }
.fe-field input, .fe-field select, .fe-field textarea { width: 100%; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 10px; }
.fe-check { font-size: 13px; color: #334155; }
.fe-item { border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; }
.fe-item-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 12px; color: #64748b; }
.fe-link-danger { border: 0; background: transparent; color: #dc2626; cursor: pointer; }
.fe-half { max-width: 360px; }
.fe-summary { padding: 12px; position: sticky; top: 10px; height: fit-content; }
.fe-summary-head small { color: #64748b; text-transform: uppercase; font-size: 11px; }
.fe-summary-head h3 { margin: 4px 0; font-size: 15px; }
.fe-summary-head span { font-size: 12px; font-weight: 700; color: #0369a1; }
.fe-progress { margin: 8px 0; height: 8px; border-radius: 8px; background: #e2e8f0; overflow: hidden; }
.fe-progress > div { height: 100%; background: #0ea5e9; }
.fe-summary-list { display: grid; gap: 8px; margin-top: 8px; }
.fe-summary-card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px; }
.fe-summary-card header { font-size: 13px; display: flex; justify-content: space-between; margin-bottom: 6px; }
.fe-summary-card .ok { color: #15803d; }
.fe-summary-card .warn { color: #d97706; }
.fe-line { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; padding: 4px 6px; border-radius: 6px; margin-bottom: 4px; }
.fe-line.is-ok { background: #ecfdf5; border-left: 3px solid #22c55e; }
.fe-line.is-warn { background: #fff7ed; border-left: 3px solid #f59e0b; }
.fe-overlay { position: fixed; inset: 0; background: rgba(2, 6, 23, 0.25); z-index: 40; }
.fe-drawer { position: fixed; right: 0; top: 0; height: 100%; width: min(880px, 100%); transform: translateX(100%); transition: transform .2s; z-index: 50; display: grid; grid-template-rows: auto 1fr auto; }
.fe-drawer.is-open { transform: translateX(0); }
.fe-drawer-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding: 12px; }
.fe-drawer-head small { font-size: 11px; color: #64748b; text-transform: uppercase; }
.fe-drawer-head h3 { margin: 2px 0 0; font-size: 16px; }
.fe-drawer-body { padding: 12px; overflow: auto; display: grid; gap: 10px; }
.fe-drawer-foot { border-top: 1px solid #e2e8f0; padding: 12px; }
.fe-col-2 { grid-column: span 2; }
.fe-btn-primary, .fe-btn-secondary { border-radius: 8px; border: 1px solid #cbd5e1; padding: 8px 12px; cursor: pointer; }
.fe-btn-primary { background: #0f172a; color: #fff; border-color: #0f172a; width: 100%; }
.fe-btn-secondary { background: #fff; color: #334155; }
@media (max-width: 1180px) { .fe-grid { grid-template-columns: 1fr; } .fe-summary { position: static; } }
</style>
