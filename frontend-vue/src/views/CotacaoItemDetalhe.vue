<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <div class="item-header-row">
        <div>
          <h1 class="gov-page__title">Item da cotação</h1>
          <p class="gov-page__subtitle">
            Cotação #{{ cotacaoId }} · Item #{{ itemId }}
          </p>
        </div>
        <RouterLink :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`" class="item-back-btn">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Voltar para cotação
        </RouterLink>
      </div>
    </header>

    <div class="gov-surface gov-page__content">
      <p v-if="isLoading" class="item-meta">Carregando item...</p>
      <p v-else-if="loadError" class="item-meta item-meta--error">{{ loadError }}</p>

      <template v-else-if="item">
        <section class="item-summary">
          <div class="item-card item-card--wide">
            <span class="item-card__label">Nome do item</span>
            <strong>{{ item.descricao_item || '—' }}</strong>
          </div>
          <div class="item-card">
            <span class="item-card__label">Quantidade</span>
            <strong>{{ quantidadeRefletida ?? '—' }}</strong>
          </div>
          <div class="item-card">
            <span class="item-card__label">Unidade</span>
            <strong>{{ unidadeRefletida || '—' }}</strong>
          </div>
          <div class="item-card">
            <span class="item-card__label">Data do registro</span>
            <strong>{{ formatDateTimePt(item.created_at) }}</strong>
          </div>
        </section>

        <section class="item-prices">
          <div class="item-price-card">
            <span>Valor unitário</span>
            <strong>{{ formatCurrency(valorUnitarioRefletido) }}</strong>
          </div>
          <div class="item-price-card">
            <span>Valor total</span>
            <strong>{{ formatCurrency(valorTotalRefletido) }}</strong>
          </div>
          <div class="item-price-card">
            <span>Valor base (faixa regional)</span>
            <strong>{{ formatCurrency(faixaValorBase) }}</strong>
          </div>
          <div class="item-price-card">
            <span>Variação (%)</span>
            <strong>{{ faixaVariacaoFmt }}</strong>
          </div>
        </section>

        <section class="item-actions">
          <RouterLink
            class="item-search-btn"
            :to="`/pesquisador-pncp/cotacoes/${cotacaoId}/busca-inteligente?itemId=${itemId}`"
          >
            <i class="fa-solid fa-robot" aria-hidden="true"></i>
            Buscar preços com I.A para este item
          </RouterLink>
          <RouterLink
            class="item-search-btn item-search-btn--manual"
            :to="`/pesquisador-pncp/cotacoes/${cotacaoId}/busca-manual?itemId=${itemId}`"
          >
            <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
            Iniciar busca manual para este item
          </RouterLink>
          <RouterLink
            class="item-search-btn item-search-btn--direta"
            :to="`/pesquisador-pncp/cotacoes/${cotacaoId}/itens/${itemId}/cotacao-direta`"
          >
            <i class="fa-solid fa-file-signature" aria-hidden="true"></i>
            Registrar Cotação Direta (Inciso IV)
          </RouterLink>
        </section>

        <section class="item-related">
          <h2>Cotações de preço deste item</h2>
          <p class="item-meta">
            {{ itemCotacoesFiltradas.length }} de {{ itemCotacoes.length }} cotação(ões) vinculadas ao item
            <template v-if="fonteSelecionadaLabel !== 'Todas'"> (filtro: {{ fonteSelecionadaLabel }})</template>.
          </p>
          <div v-if="itemCotacoesFiltradas.length > 0" class="item-cotacoes-cards">
            <article v-for="r in itemCotacoesFiltradas" :key="r.id" class="item-cotacao-card">
              <header class="item-cotacao-card__head">
                <span class="item-cotacao-card__id">#{{ r.id }}</span>
                <div class="item-cotacao-card__badges">
                  <span class="item-cotacao-card__fonte">{{ labelFonte(classificarFonte(r)) }}</span>
                  <span
                    v-if="Boolean(r?.source?.similaridade_encontrada)"
                    class="item-cotacao-card__similaridade"
                    title="Cotação vinculada por similaridade semântica"
                  >
                    Similaridade parcial encontrada
                  </span>
                </div>
              </header>
              <div
                v-if="isCotacaoDireta(r)"
                class="item-cotacao-card__grid item-cotacao-card__grid--direta"
              >
                <div class="item-cotacao-card__field item-cotacao-card__field--wide">
                  <span>Fornecedor (cotação direta)</span>
                  <strong>{{ diretaFornecedorLabel(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field item-cotacao-card__field--wide">
                  <span>Descrição da proposta</span>
                  <strong>{{ nomeItemDaCotacao(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Data/Hora da cotação</span>
                  <strong>{{ formatDateTimePt(r.data_publicacao || r.created_at) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Ajuste de frete</span>
                  <strong>{{ diretaAjusteFrete(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Valor de frete</span>
                  <strong>{{ formatCurrency(diretaValorFrete(r)) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Quantidade</span>
                  <strong>{{ formatQuantidadeCotacao(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Valor unitário</span>
                  <strong>{{ formatCurrency(r.valor_unitario) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Valor total</span>
                  <strong>{{ formatCurrency(r.valor_total) }}</strong>
                </div>
                <div class="item-cotacao-card__field item-cotacao-card__field--wide">
                  <span>Observações</span>
                  <strong>{{ diretaObservacoes(r) }}</strong>
                </div>
              </div>
              <div
                v-else-if="isDominioAmploCotacao(r)"
                class="item-cotacao-card__grid item-cotacao-card__grid--dominio"
              >
                <div class="item-cotacao-card__field item-cotacao-card__field--wide">
                  <span>Produto/Referência capturada</span>
                  <strong>{{ nomeItemDaCotacao(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field item-cotacao-card__field--wide">
                  <span>Fonte / Loja</span>
                  <strong>{{ dominioFonteNome(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field item-cotacao-card__field--wide">
                  <span>Link da oferta</span>
                  <a
                    v-if="dominioLink(r)"
                    :href="dominioLink(r)"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="item-cotacao-card__link"
                  >
                    {{ dominioLink(r) }}
                  </a>
                  <strong v-else>—</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Fornecedor</span>
                  <strong>{{ dominioFornecedor(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Data da captura</span>
                  <strong>{{ formatDateTimePt(r.created_at) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Código / Referência</span>
                  <strong>{{ dominioReferencia(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Quantidade</span>
                  <strong>{{ formatQuantidadeCotacao(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Valor unitário</span>
                  <strong>{{ formatCurrency(r.valor_unitario) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Valor total</span>
                  <strong>{{ formatCurrency(r.valor_total) }}</strong>
                </div>
                <div class="item-cotacao-card__field item-cotacao-card__field--wide">
                  <span>Observações do domínio amplo</span>
                  <strong>{{ dominioObservacoes(r) }}</strong>
                </div>
              </div>
              <div v-else class="item-cotacao-card__grid">
                <div class="item-cotacao-card__field item-cotacao-card__field--wide">
                  <span>Nome (PNCP)</span>
                  <strong>{{ nomeItemDaCotacao(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field item-cotacao-card__field--wide">
                  <span>Órgão</span>
                  <strong>{{ r.orgao || '—' }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Município/UF</span>
                  <strong>{{ formatCidadeUf(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Data</span>
                  <strong>{{ formatDateTimePt(r.created_at) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Inciso</span>
                  <strong>{{ labelIncisoFromCotacao(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Quantidade</span>
                  <strong>{{ formatQuantidadeCotacao(r) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Valor unitário</span>
                  <strong>{{ formatCurrency(r.valor_unitario) }}</strong>
                </div>
                <div class="item-cotacao-card__field">
                  <span>Valor total</span>
                  <strong>{{ formatCurrency(r.valor_total) }}</strong>
                </div>
              </div>
            </article>
          </div>
          <div v-else class="item-empty-state">
            Nenhuma cotação de preço registrada para este item neste filtro.
          </div>
        </section>
      </template>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { getItemCotacoesFromResearchSession, getResearchSession } from '../services/pncpResearch';

const route = useRoute();
const cotacaoId = computed(() => String(route.params.cotacaoId || ''));
const itemId = computed(() => Number(route.params.itemId));

const isLoading = ref(false);
const loadError = ref('');
const item = ref(null);
const allItems = ref([]);
const itemCotacoes = ref([]);

const fonteSelecionada = computed(() => normalizeFonte(route.query.fonte));
const fonteSelecionadaLabel = computed(() => (fonteSelecionada.value ? labelFonte(fonteSelecionada.value) : 'Todas'));
const faixaValorBase = computed(() => {
  const src = item.value?.source || {};
  return pickNumeric(src?.valor_base, src?.valorBase, src?.preco_base, src?.precoBase);
});

const faixaVariacaoFmt = computed(() => {
  const src = item.value?.source || {};
  const n = pickNumeric(src?.variacao, src?.variacao_percentual, src?.variacaoPercentual);
  if (!Number.isFinite(n)) return '—';
  return `${Number(n).toLocaleString('pt-BR')}%`;
});

const quantidadeRefletida = computed(() => {
  if (Number.isFinite(Number(item.value?.quantidade))) return Number(item.value.quantidade);
  const first = itemCotacoes.value.find((x) => Number.isFinite(Number(x?.quantidade)));
  if (first) return Number(first.quantidade);
  return null;
});

const unidadeRefletida = computed(() => {
  const first = itemCotacoes.value.find((x) => String(x?.unidade_medida || '').trim());
  if (first) return String(first.unidade_medida || '').trim();
  return String(item.value?.unidade_medida || '').trim() || null;
});

const valorUnitarioRefletido = computed(() => {
  const rows = itemCotacoesFiltradas.value;

  // Prioriza valor_unitario válido (> 0) vindo das cotações filtradas.
  const units = rows
    .map((x) => Number(x?.valor_unitario))
    .filter((n) => Number.isFinite(n) && n > 0);
  if (units.length > 0) {
    return units.reduce((acc, n) => acc + n, 0) / units.length;
  }

  // Fallback: deriva unitário de total/quantidade quando unitário vier ausente/zerado.
  const derivados = rows
    .map((x) => {
      const total = Number(x?.valor_total);
      const qtd = Number.isFinite(Number(item.value?.quantidade))
        ? Number(item.value.quantidade)
        : Number(x?.quantidade);
      if (!Number.isFinite(total) || total <= 0 || !Number.isFinite(qtd) || qtd <= 0) return null;
      return total / qtd;
    })
    .filter((n) => Number.isFinite(n) && Number(n) > 0);
  if (derivados.length > 0) {
    return derivados.reduce((acc, n) => acc + Number(n), 0) / derivados.length;
  }

  const itemUnit = Number(item.value?.valor_unitario);
  if (Number.isFinite(itemUnit) && itemUnit > 0) return itemUnit;

  return null;
});

const valorTotalRefletido = computed(() => {
  // Na página do item, o total deve refletir as cotações reais (somatório),
  // respeitando o filtro atual de fonte/inciso quando houver.
  const rows = itemCotacoesFiltradas.value;
  const totals = rows
    .map((x) => Number(x?.valor_total))
    .filter((n) => Number.isFinite(n) && n >= 0);
  if (totals.length > 0) {
    return totals.reduce((acc, n) => acc + n, 0);
  }

  const derivados = rows
    .map((x) => {
      const qtd = Number.isFinite(Number(item.value?.quantidade))
        ? Number(item.value.quantidade)
        : Number(x?.quantidade);
      const unit = Number(x?.valor_unitario);
      if (!Number.isFinite(qtd) || qtd < 0 || !Number.isFinite(unit) || unit < 0) return null;
      return qtd * unit;
    })
    .filter((n) => Number.isFinite(n));
  if (derivados.length > 0) {
    return derivados.reduce((acc, n) => acc + Number(n), 0);
  }

  const legacy = Number(item.value?.valor_total);
  return Number.isFinite(legacy) ? legacy : null;
});

const itemCotacoesFiltradas = computed(() => {
  const alvo = fonteSelecionada.value;
  if (!alvo) return itemCotacoes.value;
  return itemCotacoes.value.filter((c) => classificarFonte(c) === alvo);
});

onMounted(loadItem);

async function loadItem() {
  const sessionId = Number(cotacaoId.value);
  if (!Number.isFinite(sessionId) || sessionId <= 0 || !Number.isFinite(itemId.value) || itemId.value <= 0) {
    loadError.value = 'Parâmetros inválidos para abrir o item.';
    return;
  }
  isLoading.value = true;
  loadError.value = '';
  try {
    const data = await getResearchSession(sessionId);
    const itens = Array.isArray(data?.itens) ? data.itens : [];
    allItems.value = itens;
    item.value = itens.find((x) => Number(x?.id) === Number(itemId.value)) || null;
    if (!item.value) loadError.value = 'Item não encontrado nesta cotação.';
    const cot = await getItemCotacoesFromResearchSession(sessionId, itemId.value);
    itemCotacoes.value = Array.isArray(cot?.cotacoes) ? cot.cotacoes : [];
  } catch (err) {
    loadError.value = `Não foi possível carregar o item (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isLoading.value = false;
  }
}

function buildGrupoStatusKey(nome, unidade, quantidade) {
  const n = String(nome || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
  const u = String(unidade || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
  const qRaw = String(quantidade ?? '').trim().replace(',', '.');
  const qNum = Number(qRaw);
  const q = Number.isFinite(qNum) ? String(qNum) : qRaw;
  return `${n}|${u}|${q}`;
}
function pickNumeric(...vals) {
  for (const v of vals) {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function formatCurrency(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return 'R$ —';
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDateTimePt(iso) {
  if (!iso) return '—';
  const dt = new Date(iso);
  if (!Number.isFinite(dt.getTime())) return String(iso);
  return dt.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatCidadeUf(r) {
  const m = String(r?.municipio || '').trim();
  const uf = String(r?.uf || '').trim();
  if (m && uf) return `${m}/${uf}`;
  return m || uf || '—';
}

function formatQuantidadeCotacao(r) {
  const qtd = Number(r?.quantidade);
  const und = String(r?.unidade_medida || '').trim();
  if (Number.isFinite(qtd)) {
    const qtdFmt = Number.isInteger(qtd) ? String(qtd) : qtd.toLocaleString('pt-BR');
    return und ? `${qtdFmt} ${und}` : qtdFmt;
  }
  if (und) return und;
  return '—';
}

function nomeItemDaCotacao(r) {
  const src = r?.source || {};
  const nome = String(
    r?.descricao_item ||
      src?.descricao_item ||
      src?.descricaoItem ||
      src?.descricao ||
      src?.objeto_resumido ||
      src?.objetoResumido ||
      src?.objetoCompra ||
      '',
  ).trim();
  return nome || '—';
}

function isCotacaoDireta(r) {
  return classificarFonte(r) === 'cotacao_direta';
}

function diretaFornecedorLabel(r) {
  const src = r?.source || {};
  const cadastro = src?.fornecedor_cadastro || {};
  const cnpj = String(cadastro?.cnpj || src?.cnpj_fornecedor || src?.cnpj || '').trim();
  const nome = String(
    cadastro?.razao_social ||
      cadastro?.nome_fantasia ||
      src?.fornecedor ||
      src?.fornecedor_nome ||
      src?.nome_fornecedor ||
      r?.orgao ||
      '',
  ).trim();
  if (cnpj && nome) return `${cnpj} - ${nome}`;
  return nome || cnpj || '—';
}

function diretaAjusteFrete(r) {
  const src = r?.source || {};
  const a = String(src?.ajuste_frete || '').trim().toLowerCase();
  if (a === 'com_frete') return 'Com frete';
  if (a === 'sem_frete') return 'Sem frete';
  return 'Não informado';
}

function diretaValorFrete(r) {
  const src = r?.source || {};
  const n = Number(src?.valor_frete);
  return Number.isFinite(n) ? n : null;
}

function diretaObservacoes(r) {
  const src = r?.source || {};
  return String(
    src?.observacoes ||
      src?.descricao_complementar ||
      src?.descricaoComplementar ||
      '',
  ).trim() || '—';
}

function isDominioAmploCotacao(r) {
  return classificarFonte(r) === 'dominio_amplo';
}

function dominioFonteNome(r) {
  const src = r?.source || {};
  return String(
    src?.site ||
      src?.fonte_nome ||
      src?.fonteNome ||
      src?.origem_site ||
      src?.origemSite ||
      src?.marketplace ||
      src?.loja ||
      r?.orgao ||
      '',
  ).trim() || '—';
}

function dominioLink(r) {
  const src = r?.source || {};
  const link = String(src?.url || src?.link || src?.link_oferta || src?.linkOferta || '').trim();
  if (!link) return '';
  if (/^https?:\/\//i.test(link)) return link;
  return `https://${link}`;
}

function dominioFornecedor(r) {
  const src = r?.source || {};
  return String(
    src?.fornecedor ||
      src?.fornecedor_nome ||
      src?.nome_fornecedor ||
      src?.razao_social ||
      src?.razaoSocial ||
      r?.orgao ||
      '',
  ).trim() || '—';
}

function dominioReferencia(r) {
  const src = r?.source || {};
  return String(
    src?.codigo_referencia ||
      src?.codigoReferencia ||
      src?.sku ||
      src?.modelo ||
      src?.numero_item ||
      r?.numero_item ||
      '',
  ).trim() || '—';
}

function dominioObservacoes(r) {
  const src = r?.source || {};
  return String(
    src?.observacoes ||
      src?.descricao_complementar ||
      src?.descricaoComplementar ||
      src?.observacao ||
      '',
  ).trim() || '—';
}

function normalizeFonte(v) {
  const s = String(v || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
  if (!s || s === 'todas') return '';
  if (s.includes('govern') || s.includes('inciso_i') || s === 'inciso-i') return 'governamentais';
  if (s.includes('ente') || s.includes('inciso_ii') || s === 'inciso-ii') return 'entes_publicos';
  if (s.includes('dominio')) return 'dominio_amplo';
  if (s.includes('direta')) return 'cotacao_direta';
  if (s.includes('nota')) return 'notas_fiscais';
  return '';
}

function classificarFonte(cotacao) {
  const resolved = normalizeFonte(cotacao?.fonte_resolvida || cotacao?.inciso_resolvido);
  if (resolved === 'governamentais' || resolved === 'inciso_i') return 'governamentais';
  if (resolved === 'entespublicos' || resolved === 'entes_publicos' || resolved === 'inciso_ii') return 'entes_publicos';
  if (resolved === 'dominio_amplo') return 'dominio_amplo';
  if (resolved === 'cotacao_direta') return 'cotacao_direta';
  if (resolved === 'notas_fiscais') return 'notas_fiscais';

  const incisoRaw = normalizeFonte(
    cotacao?.inciso_classificacao ||
      cotacao?.source?.inciso_classificacao ||
      cotacao?.source?.incisoClassificacao,
  );
  if (
    [
      'inciso_i',
      'inciso-i',
      'governamentais',
      'precos_governamentais',
      'precos governamentais',
    ].includes(incisoRaw)
  ) return 'governamentais';
  if (
    [
      'inciso_ii',
      'inciso-ii',
      'entes_publicos',
      'outros_entes_publicos',
      'outros entes publicos',
    ].includes(incisoRaw)
  ) return 'entes_publicos';

  const esferaId = normalizeFonte(
    cotacao?.esfera_id ||
      cotacao?.source?.esfera_id ||
      cotacao?.source?.esferaId,
  );
  const esferaAdm = normalizeFonte(
    cotacao?.esfera_administrativa ||
      cotacao?.source?.esfera_administrativa ||
      cotacao?.source?.esferaAdministrativa,
  );
  // Mesma regra do backend para evitar divergência visual:
  // Federal => Inciso I; Estadual/Municipal/Distrital => Inciso II.
  if (esferaId === 'f' || esferaAdm === 'federal') return 'governamentais';
  if (['e', 'm', 'd'].includes(esferaId) || ['estadual', 'municipal', 'distrital'].includes(esferaAdm)) {
    return 'entes_publicos';
  }

  const raw = normalizeFonte(
    cotacao?.fonte ||
      cotacao?.tipo_fonte ||
      cotacao?.source?.fonte ||
      cotacao?.source?.tipo_fonte ||
      cotacao?.source?.categoria_fonte,
  );
  if (raw) return raw;
  return '';
}

function labelFonte(code) {
  if (code === 'governamentais') return 'Preços Governamentais (Inciso I)';
  if (code === 'entes_publicos') return 'Outros Entes Públicos (Inciso II)';
  if (code === 'dominio_amplo') return 'Domínio amplo';
  if (code === 'cotacao_direta') return 'Cotação direta';
  if (code === 'notas_fiscais') return 'Notas fiscais';
  return 'Não classificada';
}

function labelIncisoFromCotacao(cotacao) {
  const inciso = normalizeFonte(
    cotacao?.inciso_classificacao ||
      cotacao?.source?.inciso_classificacao ||
      cotacao?.source?.incisoClassificacao,
  );
  if (inciso === 'inciso_i' || classificarFonte(cotacao) === 'governamentais') return 'Inciso I';
  if (inciso === 'inciso_ii' || classificarFonte(cotacao) === 'entes_publicos') return 'Inciso II';
  return 'Não classificado';
}
</script>

<style scoped>
.gov-page { display: flex; flex-direction: column; gap: 16px; width: 100%; min-width: 0; }
.gov-page__title { margin: 0; font-size: 24px; }
.gov-page__subtitle { margin: 6px 0 0; color: var(--color-text-soft); }
.gov-page__content { padding: 16px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.item-header-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.item-back-btn { border: 1px solid #cfd8e3; border-radius: 10px; background: #fff; color: #1f2937; padding: 7px 12px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 7px; }
.item-meta { margin: 0; font-size: 12px; color: #64748b; }
.item-meta--error { color: #b91c1c; }
.item-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 8px; }
.item-card { border: 1px solid #d6dde8; border-radius: 10px; background: #fff; padding: 10px; display: flex; flex-direction: column; gap: 4px; }
.item-card--wide { grid-column: 1 / -1; }
.item-card__label { font-size: 10px; text-transform: uppercase; color: #64748b; }
.item-prices { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px; }
.item-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.item-search-btn {
  border: 1px solid #1f4e79;
  border-radius: 10px;
  background: #1f4e79;
  color: #fff;
  padding: 8px 12px;
  font-size: 12px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.item-search-btn--manual {
  border-color: #cfd8e3;
  background: #fff;
  color: #1f2937;
}
.item-search-btn--direta {
  border-color: #0f766e;
  background: #0f766e;
}
.item-price-card { border: 1px solid #b7d2ef; border-radius: 10px; background: #e8f1fb; padding: 10px; display: flex; flex-direction: column; gap: 4px; }
.item-price-card span { font-size: 11px; text-transform: uppercase; color: #1f4e79; }
.item-price-card strong { font-size: 18px; color: #0f4c81; }
.item-related h2 { margin: 0 0 6px; font-size: 18px; }
.item-cotacoes-cards { display: grid; gap: 10px; }
.item-cotacao-card {
  border: 1px solid #d6dde8;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}
.item-cotacao-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.item-cotacao-card__id {
  font-size: 11px;
  font-weight: 700;
  color: #1f4e79;
}
.item-cotacao-card__fonte {
  border: 1px solid #cfe0f3;
  border-radius: 999px;
  background: #eef5fc;
  color: #1f4e79;
  padding: 3px 8px;
  font-size: 10px;
  white-space: nowrap;
}
.item-cotacao-card__badges {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.item-cotacao-card__similaridade {
  border: 1px solid #f2dfb7;
  border-radius: 999px;
  background: #fff7e6;
  color: #9a6a10;
  padding: 3px 8px;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}
.item-cotacao-card__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 8px;
}
.item-cotacao-card__grid--dominio {
  border-top: 1px dashed #cbd5e1;
  padding-top: 8px;
}
.item-cotacao-card__grid--direta {
  border-top: 1px dashed #bbf7d0;
  padding-top: 8px;
}
.item-cotacao-card__field {
  border: 1px solid #e5eaf3;
  border-radius: 10px;
  background: #f8fafc;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.item-cotacao-card__field--wide { grid-column: 1 / -1; }
.item-cotacao-card__field span {
  font-size: 10px;
  text-transform: uppercase;
  color: #64748b;
}
.item-cotacao-card__field strong {
  font-size: 12px;
  color: #0f172a;
}
.item-cotacao-card__link {
  color: #0f4c81;
  text-decoration: underline;
  word-break: break-all;
  font-size: 12px;
}
.item-empty-state {
  border: 1px dashed #d6dde8;
  border-radius: 12px;
  background: #f8fafc;
  padding: 14px;
  font-size: 12px;
  color: #64748b;
}
</style>
