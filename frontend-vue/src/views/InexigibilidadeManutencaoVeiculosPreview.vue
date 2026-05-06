<template>
  <div class="ixp-page">
    <div class="ixp-wrap">
      <div class="ixp-grid">
        <section class="ixp-main">
          <div class="ixp-main-head">
            <div class="ixp-main-title">
              <div class="ixp-bot">IA</div>
              <div>
                <small>Modulo ativo</small>
                <h2>Inexigibilidade</h2>
                <p>Fornecedor Exclusivo para manutencao de veiculos (Art. 74, I)</p>
              </div>
            </div>
            <button type="button" class="ixp-btn-secondary" @click="drawerOpen = true">Dados fixos</button>
          </div>

          <div class="ixp-main-body">
            <article class="ixp-card">
              <h3>Dados basicos</h3>
              <div class="ixp-body">
                <label class="ixp-check">
                  <input v-model="processoAtivo" type="checkbox" />
                  Informar numero do processo (opcional)
                </label>
                <div class="ixp-grid-2">
                  <div v-if="processoAtivo" class="ixp-field">
                    <label>Processo</label>
                    <input v-model="processo" placeholder="Ex: 123/2026" />
                  </div>
                  <div class="ixp-field">
                    <label>Orgao/Unidade responsavel pelo veiculo</label>
                    <input v-model="orgao" placeholder="Digite o orgao" />
                  </div>
                </div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Dados do veiculo</h3>
              <div class="ixp-body ixp-grid-3">
                <div class="ixp-field"><label>Marca</label><input v-model="marca" placeholder="Ex: Chevrolet" /></div>
                <div class="ixp-field"><label>Modelo</label><input v-model="modelo" placeholder="Ex: S10" /></div>
                <div class="ixp-field"><label>Placa</label><input :value="placa" placeholder="Ex: ABC-1234" @input="placa = String($event.target.value || '').toUpperCase()" /></div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Tipo de manutencao</h3>
              <div class="ixp-body">
                <div class="ixp-grid-2">
                  <button type="button" :class="['ixp-choice', tipoManutencao === 'Corretiva' && 'is-active']" @click="setCorretiva">
                    <strong>Manutencao corretiva</strong>
                    <span>Reparo por falha, defeito ou necessidade imediata.</span>
                  </button>
                  <button type="button" :class="['ixp-choice', tipoManutencao === 'Preventiva' && 'is-active']" @click="tipoManutencao = 'Preventiva'">
                    <strong>Manutencao preventiva</strong>
                    <span>Revisao programada conforme quilometragem ou plano.</span>
                  </button>
                </div>
                <div v-if="tipoManutencao === 'Preventiva'" class="ixp-field ixp-mt">
                  <label>Quilometragem / Revisao preventiva</label>
                  <input v-model="revisaoKm" placeholder="Ex: Revisao de 10.000 km" />
                </div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Fornecedor exclusivo</h3>
              <div class="ixp-body ixp-grid-2">
                <div class="ixp-field"><label>Razao social / Nome do fornecedor</label><input v-model="fornecedor" placeholder="Digite a razao social" /></div>
                <div class="ixp-field"><label>CNPJ</label><input :value="cnpj" placeholder="00.000.000/0001-00" @input="cnpj = formatarCNPJ(String($event.target.value || ''))" /></div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Dotacao orcamentaria</h3>
              <div class="ixp-body">
                <label class="ixp-check">
                  <input v-model="dotacaoAtiva" type="checkbox" />
                  Informar dotacao orcamentaria (opcional)
                </label>
                <div v-if="dotacaoAtiva" class="ixp-field">
                  <label>Dotacao orcamentaria</label>
                  <textarea v-model="dotacao" rows="3" :placeholder="placeholderDotacao" />
                </div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Itens e valores</h3>
              <div class="ixp-body ixp-items">
                <div v-for="(item, index) in itens" :key="index" class="ixp-item">
                  <div class="ixp-item-head">
                    <span>Item {{ index + 1 }}</span>
                    <button v-if="itens.length > 1" type="button" class="ixp-link-danger" @click="removerItem(index)">Remover</button>
                  </div>
                  <div class="ixp-grid-item">
                    <div class="ixp-field"><label>Descricao</label><input :value="item.descricao" @input="atualizarItem(index, 'descricao', $event)" /></div>
                    <div class="ixp-field"><label>Quantidade</label><input :value="item.quantidade" @input="atualizarItem(index, 'quantidade', $event)" /></div>
                    <div class="ixp-field"><label>Unidade medida</label><input :value="item.unidade" @input="atualizarItem(index, 'unidade', $event)" /></div>
                    <div class="ixp-field"><label>Valor unitario</label><input :value="item.valorUnitario" @input="atualizarItem(index, 'valorUnitario', $event)" /></div>
                    <div class="ixp-field"><label>Valor total</label><input :value="item.valorTotal" @input="atualizarItem(index, 'valorTotal', $event)" /></div>
                    <button type="button" class="ixp-btn-secondary" @click="adicionarItem">+</button>
                  </div>
                </div>
              </div>
            </article>

            <div class="ixp-field ixp-half">
              <label>Valor total do processo</label>
              <input v-model="valorGlobal" placeholder="R$ 0,00" />
            </div>

            <article class="ixp-card">
              <h3>Fiscalizacao</h3>
              <div class="ixp-body">
                <div class="ixp-field"><label>Nome do fiscal de contratos</label><input v-model="fiscal" /></div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Responsavel pelo Termo de Referencia</h3>
              <div class="ixp-body ixp-grid-2">
                <div class="ixp-field"><label>Nome do responsavel</label><input v-model="responsavel" /></div>
                <div class="ixp-field"><label>Cargo/Funcao</label><input v-model="responsavelCargo" /></div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Data</h3>
              <div class="ixp-body ixp-grid-2">
                <div class="ixp-field">
                  <label>Modo da data</label>
                  <select v-model="modoData">
                    <option value="">Selecione</option>
                    <option v-for="op in dataOptions" :key="op" :value="op">{{ op }}</option>
                  </select>
                </div>
                <div v-if="modoData === 'Data manual'" class="ixp-field">
                  <label>Data manual</label>
                  <input :value="dataManual" placeholder="01/02/2026" @input="dataManual = formatarData(String($event.target.value || ''))" />
                </div>
              </div>
            </article>

            <button class="ixp-btn-primary" type="button">Gerar Documento com IA</button>
          </div>
        </section>

        <aside class="ixp-summary">
          <div class="ixp-summary-head">
            <small>Resumo em tempo real</small>
            <h3>Painel do documento</h3>
            <span>{{ progresso }}%</span>
          </div>
          <div class="ixp-progress"><div :style="{ width: `${progresso}%` }"></div></div>
          <p>{{ completos }} de {{ secoes.length }} blocos preenchidos</p>
          <div class="ixp-summary-list">
            <article v-for="sec in secoes" :key="sec.titulo" class="ixp-summary-card">
              <header>{{ sec.titulo }} <strong :class="sec.completo ? 'ok' : 'warn'">{{ sec.completo ? 'OK' : 'Pendente' }}</strong></header>
              <div v-for="linha in sec.linhas" :key="linha[0]" :class="['ixp-line', linha[2] ? 'is-ok' : 'is-warn']">
                <span>{{ linha[0] }}</span><b>{{ linha[1] }}</b>
              </div>
            </article>
          </div>
        </aside>
      </div>
    </div>

    <div v-if="drawerOpen" class="ixp-overlay" @click="drawerOpen = false"></div>
    <aside :class="['ixp-drawer', drawerOpen && 'is-open']">
      <div class="ixp-drawer-head">
        <div><small>Configuracao oculta</small><h3>Dados fixos</h3></div>
        <button type="button" class="ixp-btn-secondary" @click="drawerOpen = false">X</button>
      </div>
      <div class="ixp-drawer-body">
        <article class="ixp-card">
          <h3>1. Solicitacao / Oficio</h3>
          <div class="ixp-body">
            <div class="ixp-grid-3">
              <div class="ixp-field"><label>Tratamento</label><select v-model="fixoTratNome"><option value="">Selecione</option><option v-for="op in tratamentoNome" :key="op" :value="op">{{ op }}</option></select></div>
              <div class="ixp-field ixp-col-2"><label>1.1 A quem e direcionada a solicitacao — Nome</label><input v-model="fixoNome" placeholder="Digite o nome" /></div>
            </div>
            <div class="ixp-grid-3">
              <div class="ixp-field"><label>Tratamento</label><select v-model="fixoTratCargo"><option value="">Selecione</option><option v-for="op in tratamentoCargo" :key="op" :value="op">{{ op }}</option></select></div>
              <div class="ixp-field ixp-col-2"><label>1.2 A quem e direcionada a solicitacao — Funcao / Cargo</label><input v-model="fixoCargo" placeholder="Digite a funcao ou cargo" /></div>
            </div>
            <div class="ixp-grid-2">
              <div class="ixp-field"><label>Nome do responsavel</label><input v-model="fixoResponsavel" placeholder="Digite o nome do responsavel" /></div>
              <div class="ixp-field"><label>Funcao / Cargo</label><input v-model="fixoResponsavelCargo" placeholder="Digite o cargo" /></div>
            </div>
          </div>
        </article>
        <article class="ixp-card">
          <h3>2. DFD - Documento de Formalizacao da Demanda</h3>
          <div class="ixp-body ixp-grid-1">
            <div class="ixp-field"><label>2.1 Setor requisitante (Unidade / Setor / Departamento)</label><input v-model="fixoSetor" /></div>
            <div class="ixp-field"><label>2.2 Responsavel pela demanda</label><input v-model="fixoDemanda" /></div>
            <div class="ixp-field"><label>2.3 E-mail</label><input v-model="fixoEmail" /></div>
            <div class="ixp-field"><label>2.4 Nome do(a) gestor(a) de contratos</label><input v-model="fixoGestor" /></div>
            <div class="ixp-field"><label>2.5 Nome do(a) fiscal de contratos</label><input v-model="fixoFiscal" /></div>
            <div class="ixp-grid-2">
              <div class="ixp-field"><label>Nome do responsavel</label><input v-model="fixoAssinatura" placeholder="Digite o nome do responsavel" /></div>
              <div class="ixp-field"><label>Funcao / Cargo</label><input v-model="fixoAssinaturaCargo" placeholder="Digite o cargo" /></div>
            </div>
          </div>
        </article>
      </div>
      <div class="ixp-drawer-foot">
        <button type="button" class="ixp-btn-primary" @click="drawerOpen = false">Aplicar dados fixos</button>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const dataOptions = ['Data automatica', 'Datado e assinado digitalmente', 'Data manual'];
const tratamentoNome = ['Ao senhor', 'A senhora'];
const tratamentoCargo = ['Senhor', 'Senhora'];
const emptyItem = { descricao: '', quantidade: '', unidade: '', valorUnitario: '', valorTotal: '' };
const placeholderDotacao = ['Ex:', 'Orgao: 02', 'Unidade: 05', 'Projeto/Atividade: 2.045', 'Elemento de despesa: 3.3.90.39.00', 'Fonte: 1.500'].join('\n');

const drawerOpen = ref(false);
const processoAtivo = ref(false);
const processo = ref('');
const orgao = ref('');
const marca = ref('');
const modelo = ref('');
const placa = ref('');
const tipoManutencao = ref('');
const revisaoKm = ref('');
const fornecedor = ref('');
const cnpj = ref('');
const dotacaoAtiva = ref(false);
const dotacao = ref('');
const itens = ref([{ ...emptyItem }]);
const valorGlobal = ref('');
const fiscal = ref('');
const responsavel = ref('');
const responsavelCargo = ref('');
const modoData = ref('');
const dataManual = ref('');

const fixoTratNome = ref('');
const fixoNome = ref('');
const fixoTratCargo = ref('');
const fixoCargo = ref('');
const fixoResponsavel = ref('');
const fixoResponsavelCargo = ref('');
const fixoSetor = ref('');
const fixoDemanda = ref('');
const fixoEmail = ref('');
const fixoGestor = ref('');
const fixoFiscal = ref('');
const fixoAssinatura = ref('');
const fixoAssinaturaCargo = ref('');

function apenasNumeros(v) {
  return String(v || '').replace(/\D/g, '');
}
function formatarCNPJ(v) {
  const n = apenasNumeros(v).slice(0, 14);
  if (n.length <= 2) return n;
  if (n.length <= 5) return `${n.slice(0, 2)}.${n.slice(2)}`;
  if (n.length <= 8) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5)}`;
  if (n.length <= 12) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8)}`;
  return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8, 12)}-${n.slice(12)}`;
}
function formatarData(v) {
  const n = apenasNumeros(v).slice(0, 8);
  if (n.length <= 2) return n;
  if (n.length <= 4) return `${n.slice(0, 2)}/${n.slice(2)}`;
  return `${n.slice(0, 2)}/${n.slice(2, 4)}/${n.slice(4)}`;
}
function moedaParaNumero(v) {
  const n = apenasNumeros(v);
  if (!n) return 0;
  return Number(n) / 100;
}
function formatarMoeda(v) {
  const numero = Number(apenasNumeros(v)) / 100;
  return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function calcularTotalItem(qtd, unitario) {
  const q = Number(String(qtd || '').replace(',', '.')) || 0;
  const v = moedaParaNumero(unitario);
  return (q * v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function calcularValorGlobal(lista) {
  const total = lista.reduce((acc, item) => acc + moedaParaNumero(item.valorTotal), 0);
  return total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function isFilled(v) {
  return String(v || '').trim().length > 0;
}
function setCorretiva() {
  tipoManutencao.value = 'Corretiva';
  revisaoKm.value = '';
}
function adicionarItem() {
  itens.value.push({ ...emptyItem });
}
function removerItem(index) {
  itens.value.splice(index, 1);
  if (!itens.value.length) itens.value = [{ ...emptyItem }];
  valorGlobal.value = calcularValorGlobal(itens.value);
}
function atualizarItem(index, campo, event) {
  const raw = String(event.target.value || '');
  const next = [...itens.value];
  const item = { ...next[index] };
  item[campo] = campo === 'valorUnitario' ? formatarMoeda(raw) : raw;
  if (campo === 'quantidade' || campo === 'valorUnitario') {
    item.valorTotal = calcularTotalItem(item.quantidade, item.valorUnitario);
  }
  next[index] = item;
  itens.value = next;
  valorGlobal.value = calcularValorGlobal(next);
}

const secoes = computed(() => {
  const itensValidos = itens.value.filter((i) => Object.values(i).some(isFilled));
  return [
    { titulo: 'Dados basicos', completo: (!processoAtivo.value || isFilled(processo.value)) && isFilled(orgao.value), linhas: [['Processo', processoAtivo.value ? processo.value || 'Nao informado' : 'Nao se aplica', !processoAtivo.value || isFilled(processo.value)], ['Orgao', orgao.value || 'Nao informado', isFilled(orgao.value)]] },
    { titulo: 'Veiculo', completo: isFilled(marca.value) && isFilled(modelo.value) && isFilled(placa.value), linhas: [['Marca', marca.value || 'Nao informado', isFilled(marca.value)], ['Modelo', modelo.value || 'Nao informado', isFilled(modelo.value)], ['Placa', placa.value || 'Nao informado', isFilled(placa.value)]] },
    { titulo: 'Manutencao', completo: isFilled(tipoManutencao.value) && (tipoManutencao.value !== 'Preventiva' || isFilled(revisaoKm.value)), linhas: [['Tipo', tipoManutencao.value || 'Nao informado', isFilled(tipoManutencao.value)], ['Revisao/KM', tipoManutencao.value === 'Preventiva' ? revisaoKm.value || 'Nao informado' : 'Nao se aplica', tipoManutencao.value !== 'Preventiva' || isFilled(revisaoKm.value)]] },
    { titulo: 'Fornecedor', completo: isFilled(fornecedor.value) && isFilled(cnpj.value), linhas: [['Razao social', fornecedor.value || 'Nao informado', isFilled(fornecedor.value)], ['CNPJ', cnpj.value || 'Nao informado', isFilled(cnpj.value)]] },
    { titulo: 'Dotacao orcamentaria', completo: !dotacaoAtiva.value || isFilled(dotacao.value), linhas: [['Situacao', dotacaoAtiva.value ? 'Informar dotacao' : 'Nao informada', true], ['Dotacao', dotacaoAtiva.value ? dotacao.value || 'Nao informada' : 'Nao se aplica', !dotacaoAtiva.value || isFilled(dotacao.value)]] },
    { titulo: 'Itens', completo: itensValidos.length > 0 && isFilled(valorGlobal.value), linhas: [['Itens lancados', String(itensValidos.length), itensValidos.length > 0], ['Valor global', valorGlobal.value || 'Nao informado', isFilled(valorGlobal.value)]] },
    { titulo: 'Fiscalizacao', completo: isFilled(fiscal.value), linhas: [['Fiscal', fiscal.value || 'Nao informado', isFilled(fiscal.value)]] },
    { titulo: 'Responsavel pelo TR', completo: isFilled(responsavel.value) && isFilled(responsavelCargo.value), linhas: [['Responsavel', responsavel.value || 'Nao informado', isFilled(responsavel.value)], ['Cargo/Funcao', responsavelCargo.value || 'Nao informado', isFilled(responsavelCargo.value)]] },
    { titulo: 'Data', completo: isFilled(modoData.value) && (modoData.value !== 'Data manual' || isFilled(dataManual.value)), linhas: [['Modo', modoData.value || 'Nao informado', isFilled(modoData.value)], ['Data', modoData.value === 'Data manual' ? dataManual.value || 'Nao informada' : 'Nao se aplica', modoData.value !== 'Data manual' || isFilled(dataManual.value)]] },
  ];
});

const completos = computed(() => secoes.value.filter((s) => s.completo).length);
const progresso = computed(() => Math.round((completos.value / secoes.value.length) * 100));
</script>

<style scoped>
.ixp-page { min-height: 100vh; background: #f1f5f9; padding: 16px; }
.ixp-wrap { max-width: 1280px; margin: 0 auto; }
.ixp-header h1 { margin: 0; font-size: 20px; color: #0f172a; }
.ixp-header p { margin: 4px 0 0; font-size: 13px; color: #64748b; }
.ixp-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 16px; }
.ixp-main { border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; overflow: hidden; }
.ixp-main-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; border-bottom: 1px solid #e2e8f0; padding: 16px; }
.ixp-main-title { display: flex; gap: 12px; }
.ixp-main-title small { display: block; font-size: 11px; text-transform: uppercase; color: #64748b; letter-spacing: .08em; }
.ixp-main-title h2 { margin: 4px 0 0; font-size: 18px; color: #0f172a; }
.ixp-main-title p { margin: 4px 0 0; font-size: 14px; font-weight: 600; color: #020617; }
.ixp-bot { width: 40px; height: 40px; border-radius: 12px; background: #dbeafe; color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
.ixp-main-body { padding: 16px; display: grid; gap: 14px; }
.ixp-card { border: 1px solid #e2e8f0; border-radius: 16px; background: #fff; padding: 14px; }
.ixp-card h3 { margin: 0; font-size: 14px; color: #1e293b; }
.ixp-body { margin-top: 10px; display: grid; gap: 10px; }
.ixp-grid-1 { display: grid; gap: 10px; }
.ixp-grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.ixp-grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.ixp-col-2 { grid-column: span 2; }
.ixp-grid-item { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr 44px; gap: 10px; }
.ixp-field { display: grid; gap: 4px; }
.ixp-field label { font-size: 12px; color: #475569; font-weight: 500; }
.ixp-field input, .ixp-field textarea, .ixp-field select { width: 100%; border: 1px solid #cbd5e1; border-radius: 12px; padding: 10px 11px; font-size: 14px; color: #1e293b; outline: none; }
.ixp-field input:focus, .ixp-field textarea:focus, .ixp-field select:focus { border-color: #38bdf8; }
.ixp-check { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #334155; }
.ixp-choice { border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; padding: 12px; text-align: left; }
.ixp-choice strong { display: block; font-size: 14px; color: #1e293b; }
.ixp-choice span { display: block; margin-top: 4px; font-size: 12px; color: #64748b; }
.ixp-choice.is-active { border-color: #3b82f6; background: #eff6ff; }
.ixp-mt { margin-top: 4px; }
.ixp-items { gap: 12px; }
.ixp-item { border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; }
.ixp-item-head { display: flex; justify-content: space-between; margin-bottom: 8px; }
.ixp-item-head span { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: #64748b; }
.ixp-link-danger { border: 0; background: transparent; color: #dc2626; font-size: 12px; font-weight: 600; }
.ixp-half { max-width: 400px; }
.ixp-btn-secondary { border: 1px solid #cbd5e1; background: #fff; color: #334155; border-radius: 12px; padding: 9px 12px; font-size: 13px; font-weight: 600; }
.ixp-btn-primary { border: 0; background: #2563eb; color: #fff; border-radius: 12px; padding: 10px 14px; font-size: 13px; font-weight: 700; width: fit-content; }
.ixp-summary { position: sticky; top: 16px; align-self: start; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; padding: 14px; }
.ixp-summary-head small { font-size: 11px; text-transform: uppercase; color: #64748b; letter-spacing: .08em; }
.ixp-summary-head h3 { margin: 4px 0 0; font-size: 16px; color: #0f172a; }
.ixp-summary-head span { display: inline-block; margin-top: 8px; border-radius: 999px; background: #e0f2fe; color: #0369a1; padding: 4px 10px; font-size: 12px; font-weight: 700; }
.ixp-progress { margin-top: 10px; height: 8px; background: #e2e8f0; border-radius: 999px; overflow: hidden; }
.ixp-progress > div { height: 100%; background: #0ea5e9; }
.ixp-summary > p { font-size: 12px; color: #64748b; margin: 8px 0 0; }
.ixp-summary-list { margin-top: 10px; display: grid; gap: 8px; }
.ixp-summary-card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px; }
.ixp-summary-card header { display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 6px; }
.ixp-summary-card .ok { color: #16a34a; }
.ixp-summary-card .warn { color: #d97706; }
.ixp-line { display: flex; justify-content: space-between; gap: 8px; border-radius: 8px; padding: 6px; font-size: 11px; margin-bottom: 5px; }
.ixp-line b { text-align: right; max-width: 65%; white-space: pre-wrap; color: #0f172a; }
.ixp-line.is-ok { border: 1px solid #86efac; background: #f0fdf4; }
.ixp-line.is-warn { border: 1px solid #fda4af; background: #fff1f2; }
.ixp-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, .2); z-index: 40; }
.ixp-drawer { position: fixed; right: 0; top: 0; height: 100%; width: 100%; max-width: 880px; transform: translateX(100%); transition: transform .25s ease; background: #fff; border-left: 1px solid #e2e8f0; z-index: 50; display: grid; grid-template-rows: auto 1fr auto; }
.ixp-drawer.is-open { transform: translateX(0); }
.ixp-drawer-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding: 14px 16px; }
.ixp-drawer-head small { font-size: 11px; text-transform: uppercase; color: #64748b; letter-spacing: .08em; }
.ixp-drawer-head h3 { margin: 3px 0 0; font-size: 16px; color: #0f172a; }
.ixp-drawer-body { overflow: auto; padding: 16px; display: grid; gap: 12px; }
.ixp-drawer-foot { border-top: 1px solid #e2e8f0; padding: 14px 16px; }
.ixp-drawer-foot .ixp-btn-primary { width: 100%; }
@media (max-width: 1200px) { .ixp-grid { grid-template-columns: 1fr; } .ixp-summary { position: static; } }
@media (max-width: 900px) { .ixp-grid-2, .ixp-grid-3, .ixp-grid-item { grid-template-columns: 1fr; } .ixp-col-2 { grid-column: auto; } }
@media (prefers-color-scheme: dark) {
  .ixp-page { background: #020617; }
  .ixp-main,
  .ixp-card,
  .ixp-summary,
  .ixp-drawer,
  .ixp-item,
  .ixp-summary-card { background: #0f172a; border-color: #334155; }
  .ixp-main-head,
  .ixp-drawer-head,
  .ixp-drawer-foot { border-color: #334155; }
  .ixp-main-title h2,
  .ixp-main-title p,
  .ixp-card h3,
  .ixp-summary-head h3,
  .ixp-summary-card header,
  .ixp-line b,
  .ixp-choice strong { color: #e2e8f0; }
  .ixp-main-title small,
  .ixp-field label,
  .ixp-check,
  .ixp-item-head span,
  .ixp-summary > p,
  .ixp-choice span,
  .ixp-summary-head small,
  .ixp-drawer-head small { color: #94a3b8; }
  .ixp-field input,
  .ixp-field textarea,
  .ixp-field select,
  .ixp-btn-secondary,
  .ixp-choice { background: #0b1222; border-color: #334155; color: #e2e8f0; }
  .ixp-field input::placeholder,
  .ixp-field textarea::placeholder { color: #64748b; }
  .ixp-field input:focus,
  .ixp-field textarea:focus,
  .ixp-field select:focus { border-color: #0ea5e9; }
  .ixp-btn-secondary { color: #cbd5e1; }
  .ixp-choice.is-active { border-color: #38bdf8; background: #082f49; }
  .ixp-progress { background: #1e293b; }
  .ixp-summary-head span { background: #082f49; color: #7dd3fc; }
  .ixp-line.is-ok { background: #052e16; border-color: #166534; }
  .ixp-line.is-warn { background: #3f1d2e; border-color: #9f1239; }
  .ixp-overlay { background: rgba(2, 6, 23, 0.72); }
}
</style>
