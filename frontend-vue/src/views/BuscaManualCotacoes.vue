<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <div class="manual-header">
        <h1 class="gov-page__title">Busca Manual de Cotações</h1>
        <RouterLink :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`" class="manual-link-back">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Voltar à busca compacta
        </RouterLink>
      </div>
      <p class="gov-page__subtitle">Busca avançada com semáforo de confiabilidade da IA.</p>
    </header>

    <div class="gov-surface gov-page__content">
      <section class="manual-filters">
        <div class="manual-filters__row">
          <label class="manual-field manual-field--grow">
            <span>Descrição</span>
            <input v-model.trim="filtros.descricao" type="text" />
          </label>
          <label class="manual-field">
            <span>Período</span>
            <select v-model="filtros.periodo">
              <option>Último Mês</option>
              <option>Últimos 3 Meses</option>
              <option>Últimos 6 Meses</option>
              <option>Último Ano</option>
            </select>
          </label>
          <label class="manual-field">
            <span>Tipo</span>
            <select v-model="filtros.tipo">
              <option>Material</option>
              <option>Serviço</option>
            </select>
          </label>
          <label class="manual-field">
            <span>Modalidade</span>
            <select v-model="filtros.modalidade">
              <option>Pregão</option>
              <option>Pregão Eletrônico</option>
              <option>Compra direta</option>
              <option>Concorrência</option>
              <option>Concorrência eletrônica</option>
              <option>Inexigibilidade</option>
              <option>Dispensa</option>
              <option>Chamada Pública</option>
            </select>
          </label>
          <button type="button" class="manual-btn-search">Buscar</button>
        </div>
      </section>

      <section class="manual-controls">
        <div class="manual-controls__left">
          <label class="manual-field">
            <span>Ordenar por</span>
            <select v-model="filtros.ordenarPor">
              <option>Produto</option>
              <option>Quantidade</option>
              <option>Valor</option>
              <option>UF</option>
            </select>
          </label>
          <label class="manual-field">
            <span>Ordem</span>
            <select v-model="filtros.ordem">
              <option>Decrescente</option>
              <option>Crescente</option>
            </select>
          </label>
        </div>
        <div class="manual-controls__right">
          <label class="manual-field">
            <span>Valor Base</span>
            <div class="manual-input-prefix-wrap">
              <span class="manual-input-prefix">R$</span>
              <input v-model="filtros.valorBase" type="text" inputmode="decimal" />
            </div>
          </label>
          <label class="manual-field">
            <span>Variação %</span>
            <div class="manual-input-suffix-wrap">
              <input
                :value="filtros.variacao"
                type="text"
                inputmode="numeric"
                maxlength="3"
                @input="onVariacaoInput"
              />
              <span class="manual-input-suffix">%</span>
            </div>
          </label>
        </div>
      </section>

      <section class="manual-summary">
        <div class="manual-summary-card"><span>Alta Confiabilidade</span><strong>1</strong></div>
        <div class="manual-summary-card"><span>Média Confiabilidade</span><strong>1</strong></div>
        <div class="manual-summary-card"><span>Baixa Confiabilidade</span><strong>2</strong></div>
        <div class="manual-summary-card"><span>Selecionadas pela IA</span><strong>1</strong></div>
      </section>

      <section class="manual-results-table-shell">
        <div class="manual-results-head">
          <RouterLink
            :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`"
            class="manual-add-cotacao-btn"
          >
            <i class="fa-solid fa-plus" aria-hidden="true"></i>
            Adicionar itens na cotação {{ cotacaoId }}
          </RouterLink>
        </div>
        <div class="manual-results-table-scroll">
          <table class="manual-results-table">
            <thead>
              <tr>
                <th>Seleção</th>
                <th>Cotação</th>
                <th>Quantidade</th>
                <th>UF</th>
                <th>Data</th>
                <th>Valor Unit.</th>
                <th>Confiabilidade IA</th>
                <th>Observação</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in resultados" :key="item.id">
                <td class="manual-cell-center">
                  <input type="checkbox" :checked="item.selecionado" />
                </td>
                <td>
                  <div class="manual-cot-main">{{ item.titulo }}</div>
                  <div class="manual-cot-sub">{{ item.descricao }}</div>
                </td>
                <td>{{ item.quantidade }}</td>
                <td class="manual-cell-center">{{ item.uf }}</td>
                <td class="manual-cell-center">{{ item.data }}</td>
                <td class="manual-cell-money">{{ item.valor }}</td>
                <td class="manual-cell-center">
                  <span class="manual-status" :class="statusClass(item.statusIa)">{{ item.statusIa }}</span>
                </td>
                <td>{{ item.observacao }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const cotacaoId = computed(() => route.params.cotacaoId || 'CT-2026-00421');

const filtros = reactive({
  descricao: 'FORFIG',
  periodo: 'Último Ano',
  tipo: 'Material',
  modalidade: 'Pregão',
  ordenarPor: 'Produto',
  ordem: 'Decrescente',
  valorBase: '15,00',
  variacao: '20',
});

function onVariacaoInput(event) {
  const raw = String(event.target.value || '');
  const onlyDigits = raw.replace(/\D/g, '');
  if (!onlyDigits) {
    filtros.variacao = '0';
    event.target.value = '0';
    return;
  }
  const normalized = String(Math.min(100, Math.max(0, Number.parseInt(onlyDigits, 10))));
  filtros.variacao = normalized;
  event.target.value = normalized;
}

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
    titulo: 'Registro de Preços para aquisição de antibióticos',
    descricao: 'AMOXICILINA 500 MG CÁPSULA',
    quantidade: '12000 Cápsulas',
    uf: 'GO',
    data: '11/03/2026',
    valor: 'R$ 0,42',
    statusIa: 'Alta',
    observacao: 'Descrição aderente ao item de referência',
    selecionado: true,
  },
  {
    id: 5,
    titulo: 'Pregão eletrônico para fornecimento de analgésicos',
    descricao: 'DIPIRONA SÓDICA 500 MG COMPRIMIDO',
    quantidade: '15000 Comprimidos',
    uf: 'MS',
    data: '12/03/2026',
    valor: 'R$ 0,18',
    statusIa: 'Média',
    observacao: 'Unidade compatível, marca divergente',
    selecionado: false,
  },
  {
    id: 6,
    titulo: 'Compra direta de medicamentos para atenção básica',
    descricao: 'LOSARTANA POTÁSSICA 50 MG COMPRIMIDO',
    quantidade: '20000 Comprimidos',
    uf: 'SP',
    data: '14/03/2026',
    valor: 'R$ 0,11',
    statusIa: 'Alta',
    observacao: 'Alta similaridade com histórico recente',
    selecionado: true,
  },
  {
    id: 7,
    titulo: 'Registro de preços para insumos hospitalares',
    descricao: 'SORO FISIOLÓGICO 0,9% 500 ML',
    quantidade: '5000 Frascos',
    uf: 'MG',
    data: '15/03/2026',
    valor: 'R$ 4,90',
    statusIa: 'Média',
    observacao: 'Compatível com pequena variação de embalagem',
    selecionado: false,
  },
  {
    id: 8,
    titulo: 'Aquisição de medicamentos para farmácia municipal',
    descricao: 'METFORMINA 850 MG COMPRIMIDO',
    quantidade: '18000 Comprimidos',
    uf: 'PR',
    data: '16/03/2026',
    valor: 'R$ 0,14',
    statusIa: 'Alta',
    observacao: 'Parâmetros equivalentes ao item pesquisado',
    selecionado: true,
  },
  {
    id: 9,
    titulo: 'Chamada pública para aquisição de medicamentos essenciais',
    descricao: 'OMEPRAZOL 20 MG CÁPSULA',
    quantidade: '13000 Cápsulas',
    uf: 'BA',
    data: '18/03/2026',
    valor: 'R$ 0,23',
    statusIa: 'Baixa',
    observacao: 'Diferença de lote e apresentação secundária',
    selecionado: false,
  },
  {
    id: 10,
    titulo: 'Pregão eletrônico para medicamentos cardiovasculares',
    descricao: 'ATENOLOL 25 MG COMPRIMIDO',
    quantidade: '9000 Comprimidos',
    uf: 'SC',
    data: '19/03/2026',
    valor: 'R$ 0,19',
    statusIa: 'Média',
    observacao: 'Semelhança parcial; validar equivalência terapêutica',
    selecionado: false,
  },
  {
    id: 11,
    titulo: 'Registro de preços para medicamentos de uso contínuo',
    descricao: 'LEVOTIROXINA SÓDICA 50 MCG COMPRIMIDO',
    quantidade: '7000 Comprimidos',
    uf: 'RS',
    data: '20/03/2026',
    valor: 'R$ 0,27',
    statusIa: 'Alta',
    observacao: 'Dados consistentes com histórico de aquisição',
    selecionado: true,
  },
  {
    id: 12,
    titulo: 'Aquisição emergencial de medicamentos',
    descricao: 'PREDNISONA 20 MG COMPRIMIDO',
    quantidade: '6000 Comprimidos',
    uf: 'RJ',
    data: '21/03/2026',
    valor: 'R$ 0,31',
    statusIa: 'Baixa',
    observacao: 'Contexto da compra diferente da demanda principal',
    selecionado: false,
  },
];

function statusClass(status) {
  if (status === 'Alta') return 'manual-ia-dot--high';
  if (status === 'Média') return 'manual-ia-dot--mid';
  return 'manual-ia-dot--low';
}
</script>

<style scoped>
.gov-page { display: flex; flex-direction: column; gap: 16px; width: 100%; min-width: 0; }
.gov-page__title { margin: 0; font-size: 24px; }
.gov-page__subtitle { margin: 6px 0 0; color: var(--color-text-soft); }
.gov-page__content { padding: 16px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }

.manual-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.manual-link-back { border: 1px solid #cfd8e3; border-radius: 10px; background: #fff; color: #1f2937; padding: 7px 12px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 7px; }

.manual-filters,
.manual-controls { border: 1px solid #d6dde8; border-radius: 12px; background: #fff; padding: 10px; }
.manual-filters__row,
.manual-controls,
.manual-controls__left,
.manual-controls__right { display: flex; flex-wrap: wrap; gap: 8px; align-items: end; }
.manual-controls { justify-content: space-between; }

.manual-filters__row {
  justify-content: flex-start;
}

.manual-field { border: 1px solid #d6dde8; border-radius: 10px; background: #f8fafc; padding: 8px 10px; display: flex; flex-direction: column; gap: 4px; min-width: 170px; }
.manual-field--grow { flex: 1 1 320px; }
.manual-field span { font-size: 10px; text-transform: uppercase; color: #64748b; }
.manual-field input,
.manual-field select { border: 1px solid #cfd8e3; border-radius: 8px; background: #fff; font-size: 13px; padding: 7px 9px; outline: none; }

.manual-input-suffix-wrap {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
}

.manual-input-prefix-wrap {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
}

.manual-input-prefix-wrap input {
  border: 0;
  border-radius: 0 8px 8px 0;
}

.manual-input-prefix {
  padding: 0 6px 0 9px;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.manual-input-suffix-wrap input {
  border: 0;
  border-radius: 8px 0 0 8px;
}

.manual-input-suffix {
  padding: 0 9px 0 4px;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.manual-btn-search { height: 42px; border: 1px solid #1f4e79; border-radius: 10px; background: #1f4e79; color: #fff; font-weight: 600; padding: 0 16px; }
.manual-btn-search {
  flex: 0 0 auto;
  margin-left: auto;
}
/* Mantem o bloco de ordenacao/valor em linha (cards lado a lado) */
.manual-controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
}

.manual-controls__left,
.manual-controls__right {
  min-width: 0;
}

.manual-controls__left {
  display: grid;
  grid-template-columns: repeat(2, minmax(170px, 1fr));
  gap: 8px;
}

.manual-controls__right {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) minmax(130px, 1fr);
  gap: 8px;
  align-items: end;
}

@media (min-width: 1120px) {
  .manual-controls {
    grid-template-columns: minmax(340px, 0.95fr) minmax(620px, 1.45fr);
    align-items: end;
  }
}

.manual-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 8px; }
.manual-summary-card { border: 1px solid #d6dde8; border-radius: 12px; background: #fff; padding: 10px; }
.manual-summary-card span { display: block; font-size: 12px; color: #64748b; }
.manual-summary-card strong { display: block; margin-top: 4px; font-size: 22px; color: #0f172a; }

.manual-results-table-shell {
  border: 1px solid #d6dde8;
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
}

.manual-results-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  border-bottom: 1px solid #e5eaf3;
  background: #f8fafc;
  padding: 10px;
}

.manual-add-cotacao-btn {
  border: 1px solid #1f4e79;
  border-radius: 10px;
  background: #1f4e79;
  color: #fff;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
}

.manual-add-cotacao-btn:hover {
  filter: brightness(0.95);
}

.manual-results-table-scroll {
  width: 100%;
  max-height: 460px;
  overflow-x: auto;
  overflow-y: auto;
}

.manual-results-table {
  width: 100%;
  min-width: 1200px;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 12px;
}

.manual-results-table th,
.manual-results-table td {
  border-bottom: 1px solid #e8edf4;
  padding: 9px 8px;
  text-align: left;
  vertical-align: top;
}

.manual-results-table th {
  font-size: 11px;
  text-transform: uppercase;
  color: #64748b;
  background: #f8fafc;
}

.manual-cell-center { text-align: center !important; }
.manual-cell-money { white-space: nowrap; font-weight: 700; }
.manual-cot-main { font-weight: 600; color: #1f4e79; line-height: 1.25; }
.manual-cot-sub { margin-top: 3px; color: #475569; line-height: 1.3; }

.manual-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid transparent;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}

.manual-ia-dot--high { background: #e7f6ee; border-color: #cfe9da; color: #1f7a53; }
.manual-ia-dot--mid { background: #fff6e6; border-color: #f0dfb3; color: #9a6a00; }
.manual-ia-dot--low { background: #fff0f0; border-color: #f0d0d0; color: #b54747; }
</style>
