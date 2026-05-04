<template>
  <section class="gov-page">
    <div v-if="tituloSalvo" class="cot-page-toast">
      <i class="fa-solid fa-circle-check" aria-hidden="true"></i>
      Título salvo com sucesso
    </div>

    <header class="gov-page__header">
      <div class="cot-header-row">
        <div>
          <h1 class="gov-page__title">Detalhes da Cotação</h1>
          <p class="gov-page__subtitle">
            Cotações › Cotação #{{ cotacaoId }}
          </p>
        </div>
        <RouterLink to="/pesquisador-pncp" class="cot-back-btn">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Voltar para lista
        </RouterLink>
      </div>
      <p v-if="loadError" class="cot-meta cot-meta--error">{{ loadError }}</p>
      <p v-else-if="isLoading" class="cot-meta">Carregando itens da cotação no backend...</p>
    </header>

    <div class="gov-surface gov-page__content">
      <section class="cot-title-editor">
        <label class="cot-title-editor__field">
          <span>Título da cotação</span>
          <input
            v-model.trim="tituloCotacao"
            type="text"
            placeholder="Ex.: Cotação de medicamentos - abril/2026"
          />
        </label>
        <button type="button" class="cot-btn cot-btn--primary" :disabled="isSessaoFechada" @click="salvarTituloCotacao">
          <i class="fa-solid fa-floppy-disk" aria-hidden="true"></i>
          Salvar título
        </button>
      </section>

      <section class="cot-head">
        <div class="cot-head__summary">
          <div class="cot-card">
            <span class="cot-card__label">Criado por</span>
            <strong>{{ sessaoCriadoPor }}</strong>
            <span v-if="sessaoCriadoPorEmail" class="cot-card__email">{{ sessaoCriadoPorEmail }}</span>
          </div>
          <div class="cot-card">
            <span class="cot-card__label">Criado em</span>
            <strong>{{ sessaoCreatedAt }}</strong>
          </div>
          <div class="cot-card cot-card--highlight">
            <span class="cot-card__label">Soma dos itens (estimado)</span>
            <strong>{{ valorTotalItensFmt }}</strong>
          </div>
          <div class="cot-card">
            <span class="cot-card__label">Status</span>
            <strong>{{ sessaoStatusLabel }}</strong>
          </div>
        </div>
      </section>

      <section class="cot-formula">
        <div class="cot-formula__icon">∑</div>
        <div class="cot-formula__text">
          <div class="cot-formula__title">Fórmula de Cálculo</div>
          <div class="cot-formula__subtitle">Aplicada para consolidação</div>
        </div>
        <select
          class="cot-formula__select"
          :disabled="isSessaoFechada || isSavingFormula"
          :value="formulaCalculoId"
          @change="onChangeFormulaCalculo"
        >
          <option
            v-for="opt in formulaCalculoOptions"
            :key="opt.id"
            :value="opt.id"
          >
            {{ opt.label }}
          </option>
        </select>
      </section>

      <section class="cot-global-variacao">
        <div class="cot-global-variacao__text">
          <span class="cot-global-variacao__title">Variação global da cotação</span>
          <span class="cot-global-variacao__sep" aria-hidden="true">·</span>
          <span class="cot-global-variacao__subtitle">Aplicada para todos os itens da sessão</span>
        </div>
        <div class="cot-global-variacao__actions">
          <div class="cot-global-variacao__percent-wrap">
            <input
              :value="variacaoGlobalPercentual"
              type="text"
              inputmode="numeric"
              class="cot-sheet-inline-input cot-sheet-inline-input--variacao-global"
              placeholder="0"
              :disabled="isSessaoFechada || isSavingVariacaoGlobal"
              @input="onVariacaoGlobalInput"
            />
            <span class="cot-global-variacao__suffix" aria-hidden="true">%</span>
          </div>
          <label class="cot-global-variacao__direction">
            <span>Direção</span>
            <select
              v-model="variacaoGlobalSentido"
              class="cot-formula__select cot-global-variacao__select"
              :disabled="isSessaoFechada || isSavingVariacaoGlobal"
            >
              <option value="cima">Para cima</option>
              <option value="baixo">Para baixo</option>
            </select>
          </label>
          <button
            type="button"
            class="cot-btn cot-btn--primary cot-global-variacao__submit"
            :disabled="isSessaoFechada || isSavingVariacaoGlobal"
            @click="salvarVariacaoGlobal"
          >
            {{ isSavingVariacaoGlobal ? 'Salvando...' : 'Salvar variação global' }}
          </button>
        </div>
      </section>

      <section class="cot-actions">
        <button type="button" class="cot-btn" :disabled="importLoading || isSessaoFechada" @click="openImportSpreadsheet">
          <i class="fa-solid fa-file-arrow-up" aria-hidden="true"></i>
          {{ importLoading ? 'Importando planilha...' : 'Importar Planilha Preenchida' }}
        </button>
        <button type="button" class="cot-btn" @click="downloadModeloExcel">
          <i class="fa-solid fa-file-excel" aria-hidden="true"></i>
          Baixar Planilha Modelo (Excel)
        </button>
        <button type="button" class="cot-btn" @click="downloadModeloSheetsCsv">
          <i class="fa-solid fa-table" aria-hidden="true"></i>
          Baixar Modelo (Google Sheets CSV)
        </button>
        <button
          type="button"
          class="cot-btn"
          :disabled="supplierPdfLoading || isSessaoFechada"
          @click="openSupplierPdfPicker"
        >
          <i class="fa-solid fa-paperclip" aria-hidden="true"></i>
          {{
            supplierPdfLoading
              ? 'Anexando PDF(s)...'
              : (hasSupplierPdfAttachment ? 'Adicionar mais PDFs do Fornecedor' : 'Anexar Cotação do Fornecedor')
          }}
        </button>
        <button type="button" class="cot-btn cot-btn--primary" @click="openRelatorioModal">
          <i class="fa-solid fa-file-pdf" aria-hidden="true"></i>
          Gerar relatório PDF
        </button>
        <button
          type="button"
          class="cot-btn cot-btn--danger"
          :disabled="isClosingCotacao || isSessaoFechada"
          @click="finalizarCotacao"
        >
          <i class="fa-solid fa-lock" aria-hidden="true"></i>
          {{ isClosingCotacao ? 'Fechando cotação...' : 'Finalizar/Fechar Cotação' }}
        </button>
        <button
          v-if="isSessaoFechada"
          type="button"
          class="cot-btn cot-btn--success"
          :disabled="isReopeningCotacao"
          @click="reabrirCotacao"
        >
          <i class="fa-solid fa-lock-open" aria-hidden="true"></i>
          {{ isReopeningCotacao ? 'Reabrindo cotação...' : 'Reabrir Cotação' }}
        </button>
      </section>
      <section class="cot-fornecedor-field">
        <span class="cot-fornecedor-field__label">Cotação do Fornecedor</span>
        <strong class="cot-fornecedor-field__value" v-if="supplierPdfFilenames.length">
          {{ supplierPdfFilenames.length }} arquivo(s) anexado(s)
        </strong>
        <strong class="cot-fornecedor-field__value" v-else>Nenhum PDF anexado</strong>
        <ul v-if="supplierPdfFilenames.length" class="cot-fornecedor-field__list">
          <li v-for="(nome, idx) in supplierPdfFilenames" :key="`${idx}-${nome}`">{{ nome }}</li>
        </ul>
      </section>
      <input
        ref="importSpreadsheetInput"
        type="file"
        accept=".csv,.xlsx"
        class="cot-hidden-file-input"
        @change="onImportSpreadsheetSelected"
      />
      <input
        ref="supplierPdfInput"
        type="file"
        accept="application/pdf,.pdf"
        multiple
        class="cot-hidden-file-input"
        @change="onSupplierPdfSelected"
      />

      <section class="cot-new-item-block">
        <div class="cot-new-item-block__text">
          <h2>Novo item</h2>
          <p>Escolha como deseja iniciar a pesquisa para adicionar novos itens à cotação.</p>
        </div>
        <div class="cot-new-item-block__actions">
          <button
            type="button"
            class="cot-btn cot-btn--primary"
            :disabled="isSessaoFechada || isAddingManualItem"
            @click="toggleManualItemEditor"
          >
            <i class="fa-solid fa-plus" aria-hidden="true"></i>
            {{ showManualItemEditor ? 'Fechar adição manual' : 'Adicionar item manual' }}
          </button>
          <RouterLink
            :to="`/pesquisador-pncp/cotacoes/${cotacaoId}/busca-inteligente?autostart=1`"
            class="cot-btn cot-btn--primary"
            :class="{ 'cot-btn--disabled': isSessaoFechada }"
            :aria-disabled="isSessaoFechada ? 'true' : 'false'"
            @click="onStartSearchClick"
          >
            <i class="fa-solid fa-robot" aria-hidden="true"></i>
            Iniciar busca com I.A
          </RouterLink>
        </div>
      </section>
      <section class="cot-sheet-shell">
        <div class="cot-sheet-toolbar">
          <label class="cot-sheet-search">
            <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
            <input
              v-model.trim="searchTerm"
              type="text"
              placeholder="Buscar itens"
              aria-label="Buscar itens na planilha"
            />
          </label>
          <label class="cot-sheet-status-filter">
            <span>Status</span>
            <select v-model="statusFilter" aria-label="Filtrar itens por status">
              <option value="todos">Todos</option>
              <option value="completo">Completo</option>
              <option value="incompleto">Incompleto</option>
            </select>
          </label>
          <button
            type="button"
            class="cot-sheet-bulk-delete"
            :disabled="selectedIds.size === 0 || isSessaoFechada"
            @click="openBulkDeleteModal"
          >
            <i class="fa-solid fa-trash-can" aria-hidden="true"></i>
            Excluir selecionados
          </button>
        </div>
        <div class="cot-sheet-scroll">
          <table class="cot-sheet-table" aria-label="Estrutura base da planilha de cotacao">
            <colgroup class="cot-sheet-columns">
              <col style="width: 56px" />
              <col style="width: 64px" />
              <col style="width: 260px" />
              <col style="width: 110px" />
              <col style="width: 110px" />
              <col style="width: 110px" />
              <col style="width: 110px" />
              <col style="width: 110px" />
              <col style="width: 70px" />
              <col style="width: 70px" />
              <col style="width: 120px" />
              <col style="width: 170px" />
              <col style="width: 110px" />
              <col style="width: 170px" />
            </colgroup>
            <thead>
              <tr>
                <th rowspan="2" class="cot-sheet-center">
                  <input
                    type="checkbox"
                    class="cot-sheet-checkbox"
                    :checked="allSelected"
                    :disabled="isSessaoFechada"
                    :indeterminate.prop="isPartiallySelected"
                    @change="toggleSelectAll"
                    aria-label="Selecionar todos os itens"
                  />
                </th>
                <th rowspan="2" class="cot-sheet-center">Número do Item</th>
                <th rowspan="2">Nome do Item</th>
                <th colspan="5" class="cot-sheet-group">Fontes de Preco (Art. 5º)</th>
                <th rowspan="2" class="cot-sheet-center">Qtd.</th>
                <th rowspan="2" class="cot-sheet-center">Und.</th>
                <th rowspan="2" class="cot-sheet-center">Preco Total</th>
                <th rowspan="2">Faixa Regional do Item</th>
                <th rowspan="2" class="cot-sheet-center">Status</th>
                <th rowspan="2" class="cot-sheet-center">Acoes</th>
              </tr>
              <tr>
                <th class="cot-sheet-source">
                  <span class="cot-sheet-source__icon"><i class="fa-solid fa-building-columns" aria-hidden="true"></i></span>
                  <span class="cot-sheet-source__title">Precos Governamentais</span>
                  <span class="cot-sheet-source__sub">(Inciso I)</span>
                </th>
                <th class="cot-sheet-source">
                  <span class="cot-sheet-source__icon"><i class="fa-solid fa-building" aria-hidden="true"></i></span>
                  <span class="cot-sheet-source__title">Outros Entes Publicos</span>
                  <span class="cot-sheet-source__sub">(Inciso II)</span>
                </th>
                <th class="cot-sheet-source">
                  <span class="cot-sheet-source__icon"><i class="fa-solid fa-globe" aria-hidden="true"></i></span>
                  <span class="cot-sheet-source__title">Dominio Amplo</span>
                  <span class="cot-sheet-source__sub">(Inciso III)</span>
                </th>
                <th class="cot-sheet-source">
                  <span class="cot-sheet-source__icon"><i class="fa-solid fa-money-bill-wave" aria-hidden="true"></i></span>
                  <span class="cot-sheet-source__title">Cotacao Direta</span>
                  <span class="cot-sheet-source__sub">(Inciso IV)</span>
                </th>
                <th class="cot-sheet-source">
                  <span class="cot-sheet-source__icon"><i class="fa-solid fa-file-lines" aria-hidden="true"></i></span>
                  <span class="cot-sheet-source__title">Notas Fiscais</span>
                  <span class="cot-sheet-source__sub">(Inciso V)</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="showManualItemEditor" class="cot-sheet-row-add">
                <td class="cot-sheet-center">+</td>
                <td class="cot-sheet-center">—</td>
                <td>
                  <input
                    v-model.trim="manualItem.descricao_item"
                    type="text"
                    class="cot-sheet-inline-input"
                    placeholder="Nome/descrição do item"
                  />
                </td>
                <td class="cot-sheet-center">—</td>
                <td class="cot-sheet-center">—</td>
                <td class="cot-sheet-center">—</td>
                <td class="cot-sheet-center">—</td>
                <td class="cot-sheet-center">—</td>
                <td class="cot-sheet-center">
                  <input
                    v-model.trim="manualItem.quantidade"
                    type="text"
                    inputmode="decimal"
                    class="cot-sheet-inline-input"
                    placeholder="Qtd."
                  />
                </td>
                <td class="cot-sheet-center">
                  <input
                    v-model.trim="manualItem.unidade_medida"
                    type="text"
                    class="cot-sheet-inline-input"
                    placeholder="Unidade (ex.: UN, CX, KG)"
                  />
                </td>
                <td class="cot-sheet-center">—</td>
                <td>
                  <div class="cot-faixa-inline cot-faixa-inline--manual">
                    <input
                      :value="manualItem.valor_base"
                      type="text"
                      inputmode="numeric"
                      class="cot-sheet-inline-input cot-sheet-inline-input--faixa-base-manual"
                      placeholder="Valor base (R$)"
                      @input="onManualBaseInput"
                    />
                  </div>
                </td>
                <td class="cot-sheet-center">Novo</td>
                <td>
                  <div class="cot-sheet-actions">
                    <button type="button" class="cot-sheet-action-btn" :disabled="isAddingManualItem" @click="addManualItem">
                      {{ isAddingManualItem ? 'Salvando...' : 'Salvar' }}
                    </button>
                    <button type="button" class="cot-sheet-action-btn" :disabled="isAddingManualItem" @click="toggleManualItemEditor">
                      Cancelar
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-for="(linha, idx) in linhasFiltradas" :key="linha.id">
                <td class="cot-sheet-center">
                  <input
                    type="checkbox"
                    class="cot-sheet-checkbox"
                    :checked="selectedIds.has(linha.id)"
                    :disabled="isSessaoFechada"
                    @change="toggleSelectRow(linha.id)"
                    :aria-label="`Selecionar item ${linha.id}`"
                  />
                </td>
                <td class="cot-sheet-center">{{ idx + 1 }}</td>
                <td>
                  <div class="cot-item-nome-wrap">
                    <span>{{ linha.nomeItem }}</span>
                    <span
                      v-if="Number(linha.fontes.similaridadeEncontrada || 0) > 0"
                      class="cot-similaridade-tag"
                      title="A IA identificou cotação por similaridade de contexto"
                    >
                      Similaridade parcial encontrada
                    </span>
                  </div>
                </td>
                <td class="cot-sheet-center">
                  <button
                    type="button"
                    class="cot-sheet-source-cell"
                    :class="Number(linha.fontes.governamentais || 0) > 0 ? 'cot-sheet-source-cell--green' : 'cot-sheet-source-cell--gray'"
                    @click="openItemCotacoesFromFonte(linha.id, 'governamentais')"
                  >
                    {{ linha.fontes.governamentais }}
                  </button>
                </td>
                <td class="cot-sheet-center">
                  <button
                    type="button"
                    class="cot-sheet-source-cell"
                    :class="Number(linha.fontes.entesPublicos || 0) > 0 ? 'cot-sheet-source-cell--green' : 'cot-sheet-source-cell--gray'"
                    @click="openItemCotacoesFromFonte(linha.id, 'entes_publicos')"
                  >
                    {{ linha.fontes.entesPublicos }}
                  </button>
                </td>
                <td class="cot-sheet-center">
                  <button
                    type="button"
                    class="cot-sheet-source-cell"
                    :class="Number(linha.fontes.dominioAmplo || 0) > 0 ? 'cot-sheet-source-cell--green' : 'cot-sheet-source-cell--gray'"
                    @click="openItemCotacoesFromFonte(linha.id, 'dominio_amplo')"
                  >
                    {{ linha.fontes.dominioAmplo }}
                  </button>
                </td>
                <td class="cot-sheet-center">
                  <button
                    type="button"
                    class="cot-sheet-source-cell"
                    :class="Number(linha.fontes.cotacaoDireta || 0) > 0 ? 'cot-sheet-source-cell--green' : 'cot-sheet-source-cell--gray'"
                    @click="openItemCotacoesFromFonte(linha.id, 'cotacao_direta')"
                  >
                    {{ linha.fontes.cotacaoDireta }}
                  </button>
                </td>
                <td class="cot-sheet-center">
                  <button
                    type="button"
                    class="cot-sheet-source-cell"
                    :class="Number(linha.fontes.notasFiscais || 0) > 0 ? 'cot-sheet-source-cell--green' : 'cot-sheet-source-cell--gray'"
                    @click="openItemCotacoesFromFonte(linha.id, 'notas_fiscais')"
                  >
                    {{ linha.fontes.notasFiscais }}
                  </button>
                </td>
                <td class="cot-sheet-center">{{ linha.qtd }}</td>
                <td class="cot-sheet-center">{{ linha.und }}</td>
                <td class="cot-sheet-center">{{ linha.precoTotal }}</td>
                <td>
                  <div class="cot-faixa-cell">
                    <div class="cot-faixa-edit-row">
                      <span class="cot-faixa-block__label">BASE</span>
                      <input
                        type="text"
                        inputmode="numeric"
                        class="cot-sheet-inline-input cot-sheet-inline-input--faixa-base"
                        :disabled="isSessaoFechada || savingFaixaItemId === linha.id"
                        :value="faixaBaseDisplay(linha)"
                        @input="onFaixaBaseRowInput(linha.id, $event)"
                      />
                      <button
                        type="button"
                        class="cot-sheet-action-btn cot-sheet-action-btn--compact"
                        :disabled="isSessaoFechada || savingFaixaItemId === linha.id"
                        @click="salvarFaixaBaseItem(linha)"
                      >
                        {{ savingFaixaItemId === linha.id ? '…' : 'Salvar' }}
                      </button>
                    </div>
                    <div class="cot-faixa-var-row">
                      <span class="cot-faixa-block__label">VAR</span>
                      <strong class="cot-faixa-var-row__value">{{ linha.faixaRegionalVariacao }}</strong>
                      <span class="cot-faixa-var-row__hint">(global da cotação)</span>
                    </div>
                  </div>
                </td>
                <td class="cot-sheet-center">
                  <span
                    class="cot-sheet-status"
                    :class="linha.status === 'Completo' ? 'cot-sheet-status--completo' : 'cot-sheet-status--incompleto'"
                  >
                    {{ linha.status }}
                  </span>
                </td>
                <td>
                  <div class="cot-sheet-actions">
                    <RouterLink
                      class="cot-sheet-action-btn"
                      :to="itemDetalheTo(linha.id)"
                    >
                      Abrir
                    </RouterLink>
                    <button
                      type="button"
                      class="cot-sheet-action-btn cot-sheet-action-btn--danger"
                      :disabled="isSessaoFechada"
                      @click="openRowDeleteModal(linha)"
                    >
                      Excluir
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <Teleport to="body">
      <div
        v-if="pendingDelete"
        class="pncp-modal-backdrop"
        role="presentation"
        @click.self="cancelDelete"
      >
        <div
          class="pncp-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cot-pncp-delete-title"
        >
          <h2 id="cot-pncp-delete-title" class="pncp-modal__title">{{ deleteModalTitle }}</h2>
          <p class="pncp-modal__text">{{ deleteModalText }}</p>
          <p v-if="deleteModalQuote" class="pncp-modal__quote">{{ deleteModalQuote }}</p>
          <div class="pncp-modal__actions">
            <button type="button" class="pncp-modal__btn pncp-modal__btn--ghost" @click="cancelDelete">
              Cancelar
            </button>
            <button type="button" class="pncp-modal__btn pncp-modal__btn--danger" @click="confirmDelete">
              Excluir
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="relatorioModalOpen"
        class="pncp-modal-backdrop"
        role="presentation"
        @click.self="closeRelatorioModal"
      >
        <div
          class="pncp-modal pncp-modal--relatorio"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cot-relatorio-title"
          @click.stop
        >
          <h2 id="cot-relatorio-title" class="pncp-modal__title">Relatório PDF desta cotação</h2>
          <p class="pncp-modal__text">
            O PDF é <strong>gerado a partir desta cotação</strong> (itens e dados guardados no sistema). Ao confirmar,
            o ficheiro é produzido no servidor e o <strong>download começa automaticamente</strong>. Inclui título
            personalizado, resumo, detalhamento por fontes, CNPJs quando existirem, marca d’água e QR para abrir esta
            mesma cotação no site (com sessão iniciada).
          </p>
          <label class="cot-relatorio-field">
            <span>Título do relatório <abbr title="obrigatório">*</abbr></span>
            <input
              v-model.trim="relatorioTitulo"
              type="text"
              class="gov-input"
              placeholder="Ex.: Relatório de pesquisa de preços — material de expediente"
              autocomplete="off"
            />
          </label>
          <p class="cot-relatorio-info">
            Itens reais vinculados a esta cotação: <strong>{{ totalItensSessao }}</strong>
          </p>
          <p v-if="relatorioError" class="pncp-modal__error">{{ relatorioError }}</p>
          <div class="pncp-modal__actions">
            <button type="button" class="pncp-modal__btn pncp-modal__btn--ghost" @click="closeRelatorioModal">
              Cancelar
            </button>
            <button
              type="button"
              class="pncp-modal__btn pncp-modal__btn--primary"
              :disabled="relatorioLoading || totalItensSessao === 0"
              @click="submitRelatorioPdf"
            >
              {{ relatorioLoading ? 'A gerar…' : 'Gerar e baixar PDF' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  addItemsToResearchSession,
  deleteItemsFromResearchSession,
  downloadCotacaoRelatorioPdf,
  getResearchSession,
  importItemsSpreadsheetToResearchSession,
  uploadSupplierPdfToResearchSession,
  updateResearchSession,
  updateResearchSessionItem,
} from '../services/pncpResearch';

const route = useRoute();
const router = useRouter();
const cotacaoId = computed(() => route.params.cotacaoId || 'CT-2026-00421');

const sessionBackendId = computed(() => {
  const n = Number(route.params.cotacaoId);
  return Number.isFinite(n) ? n : null;
});

const linhasMock = ref([]);
const searchTerm = ref('');
const statusFilter = ref('todos');

const selectedIds = ref(new Set());
const tituloCotacao = ref('');
const sessaoCreatedAt = ref('—');
const sessaoCriadoPor = ref('—');
const sessaoCriadoPorEmail = ref('');
const valorTotalItensFmt = ref('R$ —');
const tituloSalvo = ref(false);
const isLoading = ref(false);
const loadError = ref('');
const relatorioModalOpen = ref(false);
const relatorioTitulo = ref('');
const relatorioError = ref('');
const relatorioLoading = ref(false);
const totalItensSessao = ref(0);
const formulaCalculoLabel = ref('Média aritmética dos preços obtidos');
const formulaCalculoId = ref('media_aritmetica_precos_obtidos');
const formulaCalculoOptions = [
  { id: 'media_aritmetica_precos_obtidos', label: 'Média Aritmética dos preços obtidos' },
  { id: 'mediana_precos_obtidos', label: 'Mediana dos preços obtidos' },
  { id: 'menor_preco', label: 'Menor preço' },
  { id: 'media_saneada', label: 'Média Saneada' },
  { id: 'media_ponderada', label: 'Média ponderada' },
  { id: 'media_relativa_25_50', label: 'Média relativa 25% - 50%' },
];
const isSavingFormula = ref(false);
const importLoading = ref(false);
const importSpreadsheetInput = ref(null);
const supplierPdfInput = ref(null);
const supplierPdfLoading = ref(false);
const hasSupplierPdfAttachment = ref(false);
const supplierPdfFilenames = ref([]);
const sessaoStatus = ref('aberta');
const isClosingCotacao = ref(false);
const isReopeningCotacao = ref(false);
const isAddingManualItem = ref(false);
const showManualItemEditor = ref(false);
const manualItem = ref({
  descricao_item: '',
  quantidade: '',
  unidade_medida: '',
  valor_base: '',
});
const variacaoGlobalPercentual = ref('20');
const variacaoGlobalSentido = ref('cima');
const isSavingVariacaoGlobal = ref(false);
/** Rascunho local do campo moeda por item_id (valor base da faixa). */
const faixaBaseDraft = ref({});
const savingFaixaItemId = ref(null);

const isSessaoFechada = computed(() => ['finalizada', 'cancelada'].includes(String(sessaoStatus.value || '')));
const sessaoStatusLabel = computed(() => {
  const s = String(sessaoStatus.value || '').toLowerCase();
  if (s === 'finalizada') return 'Fechada';
  if (s === 'cancelada') return 'Cancelada';
  if (s === 'aberta') return 'Aberta';
  return s || '—';
});

const allSelected = computed(() => {
  const rows = linhasFiltradas.value;
  return rows.length > 0 && selectedIds.value.size === rows.length;
});

const isPartiallySelected = computed(() => {
  const rows = linhasFiltradas.value;
  return selectedIds.value.size > 0 && selectedIds.value.size < rows.length;
});

const linhasFiltradas = computed(() => {
  const q = String(searchTerm.value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
  const byStatus = linhasMock.value.filter((linha) => {
    const st = String(linha?.status || '').trim().toLowerCase();
    if (statusFilter.value === 'completo') return st === 'completo';
    if (statusFilter.value === 'incompleto') return st === 'incompleto';
    return true;
  });
  if (!q) return byStatus;
  return byStatus.filter((linha) => {
    const nome = String(linha?.nomeItem || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();
    return nome.includes(q);
  });
});

function toggleSelectRow(id) {
  const next = new Set(selectedIds.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  selectedIds.value = next;
}

function toggleSelectAll(event) {
  if (event.target.checked) {
    selectedIds.value = new Set(linhasFiltradas.value.map((linha) => linha.id));
    return;
  }
  selectedIds.value = new Set();
}

/** Mesmo padrão de modal que em `PncpResearcher.vue`: exclusão em lote ou uma linha. */
const pendingDelete = ref(null);

const deleteModalTitle = computed(() => {
  const p = pendingDelete.value;
  if (!p) return '';
  return p.kind === 'bulk' ? 'Excluir itens' : 'Excluir item';
});

const deleteModalText = computed(() => {
  const p = pendingDelete.value;
  if (!p) return '';
  return p.kind === 'bulk'
    ? 'Tem certeza que deseja excluir os itens selecionados? Esta ação não pode ser desfeita.'
    : 'Tem certeza que deseja excluir este item? Esta ação não pode ser desfeita.';
});

const deleteModalQuote = computed(() => {
  const p = pendingDelete.value;
  if (!p) return '';
  if (p.kind === 'row') return p.row.nomeItem;
  const idSet = new Set(p.ids);
  const names = linhasMock.value.filter((l) => idSet.has(l.id)).map((l) => l.nomeItem);
  if (names.length === 0) return '';
  if (names.length <= 2) return names.join(' · ');
  return `${names.length} itens selecionados`;
});

function openBulkDeleteModal() {
  if (isSessaoFechada.value) return;
  if (selectedIds.value.size === 0) return;
  pendingDelete.value = { kind: 'bulk', ids: [...selectedIds.value] };
}

function openRowDeleteModal(row) {
  if (isSessaoFechada.value) return;
  pendingDelete.value = { kind: 'row', row };
}

function cancelDelete() {
  pendingDelete.value = null;
}

async function confirmDelete() {
  const p = pendingDelete.value;
  if (!p) return;
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Cotação inválida para excluir itens.';
    return;
  }
  const ids = p.kind === 'bulk' ? p.ids : [p.row.id];
  const itemIds = ids
    .map((x) => Number(x))
    .filter((x) => Number.isFinite(x) && x > 0);
  if (!itemIds.length) {
    pendingDelete.value = null;
    return;
  }
  loadError.value = '';
  try {
    await deleteItemsFromResearchSession(sessionId, itemIds);
    const remover = new Set(itemIds);
    linhasMock.value = linhasMock.value.filter((linha) => !remover.has(Number(linha.id)));
    const next = new Set(selectedIds.value);
    for (const id of itemIds) next.delete(id);
    selectedIds.value = next;
    pendingDelete.value = null;
    totalItensSessao.value = Math.max(0, totalItensSessao.value - itemIds.length);
  } catch (err) {
    loadError.value = `Falha ao excluir item(ns): ${err?.message || 'erro desconhecido'}.`;
  }
}

function openRelatorioModal() {
  relatorioError.value = '';
  if (totalItensSessao.value === 0) {
    relatorioError.value = 'Adicione ao menos 1 item real na cotação para gerar o PDF.';
  }
  relatorioTitulo.value =
    (tituloCotacao.value || '').trim() || `Relatório — cotação ${cotacaoId.value}`;
  relatorioModalOpen.value = true;
}

function openImportSpreadsheet() {
  if (isSessaoFechada.value) return;
  if (importLoading.value) return;
  importSpreadsheetInput.value?.click();
}

function openSupplierPdfPicker() {
  if (isSessaoFechada.value) return;
  if (supplierPdfLoading.value) return;
  supplierPdfInput.value?.click();
}

function onStartSearchClick(event) {
  if (!isSessaoFechada.value) return;
  event?.preventDefault?.();
  loadError.value = 'Cotação fechada: não é permitido iniciar novas buscas.';
}

function triggerTemplateDownload(url, filename) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function downloadModeloExcel() {
  triggerTemplateDownload(
    '/modelos/cotacao-manual-modelo-docmasteria.xlsx?v=20260421',
    'cotacao-manual-modelo-docmasteria.xlsx',
  );
}

function downloadModeloSheetsCsv() {
  triggerTemplateDownload('/modelos/cotacao-manual-modelo.csv?v=20260421', 'cotacao-manual-modelo.csv');
}

async function onChangeFormulaCalculo(event) {
  const nextId = String(event?.target?.value || '').trim();
  if (!nextId || nextId === formulaCalculoId.value) return;
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Cotação inválida para alterar fórmula.';
    return;
  }
  isSavingFormula.value = true;
  loadError.value = '';
  try {
    await updateResearchSession(sessionId, { formula_calculo_id: nextId });
    formulaCalculoId.value = nextId;
    formulaCalculoLabel.value =
      formulaCalculoOptions.find((x) => x.id === nextId)?.label || formulaCalculoLabel.value;
    await loadSessionFromBackend();
  } catch (err) {
    loadError.value = `Falha ao atualizar fórmula de cálculo (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isSavingFormula.value = false;
  }
}

async function finalizarCotacao() {
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Cotação inválida para finalizar.';
    return;
  }
  if (isSessaoFechada.value || isClosingCotacao.value) return;
  const ok = window.confirm(
    'Deseja finalizar/fechar esta cotação? Após fechar, não será possível importar, adicionar ou excluir itens.',
  );
  if (!ok) return;
  isClosingCotacao.value = true;
  loadError.value = '';
  try {
    await updateResearchSession(sessionId, { status: 'finalizada' });
    sessaoStatus.value = 'finalizada';
  } catch (err) {
    loadError.value = `Falha ao finalizar cotação (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isClosingCotacao.value = false;
  }
}

async function reabrirCotacao() {
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Cotação inválida para reabrir.';
    return;
  }
  if (!isSessaoFechada.value || isReopeningCotacao.value) return;
  const ok = window.confirm(
    'Deseja reabrir esta cotação? Após reabrir, será possível importar, adicionar e excluir itens novamente.',
  );
  if (!ok) return;
  isReopeningCotacao.value = true;
  loadError.value = '';
  try {
    await updateResearchSession(sessionId, { status: 'aberta' });
    sessaoStatus.value = 'aberta';
  } catch (err) {
    loadError.value = `Falha ao reabrir cotação (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isReopeningCotacao.value = false;
  }
}

async function addManualItem() {
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Cotação inválida para adicionar item manual.';
    return;
  }
  if (isSessaoFechada.value || isAddingManualItem.value) return;
  const descricao = String(manualItem.value.descricao_item || '').trim();
  if (!descricao) {
    loadError.value = 'Informe a descrição do item manual.';
    return;
  }
  const unidadeMedida = String(manualItem.value.unidade_medida || '').trim().toUpperCase();
  if (!unidadeMedida) {
    loadError.value = 'Informe a unidade do item manual (definida pelo usuário).';
    return;
  }
  const quantidade = parseQuantityInputToNumber(manualItem.value.quantidade);
  if (manualItem.value.quantidade && !Number.isFinite(quantidade)) {
    loadError.value = 'Quantidade inválida. Use apenas números (ex.: 10 ou 10,5).';
    return;
  }
  if (Number.isFinite(quantidade) && quantidade <= 0) {
    loadError.value = 'Quantidade deve ser maior que zero.';
    return;
  }
  const valorBase = parseCurrencyInputToNumber(manualItem.value.valor_base);

  isAddingManualItem.value = true;
  loadError.value = '';
  try {
    await addItemsToResearchSession(sessionId, [
      {
        descricao_item: descricao,
        quantidade: Number.isFinite(quantidade) ? quantidade : null,
        unidade_medida: unidadeMedida,
        valor_base: Number.isFinite(valorBase) ? valorBase : null,
        faixa_regional: {
          valor_base: Number.isFinite(valorBase) ? valorBase : null,
        },
        origem: 'item_manual_cotacao',
        unidade_definida_usuario: true,
      },
    ]);
    await loadSessionFromBackend();
    manualItem.value = {
      descricao_item: '',
      quantidade: '',
      unidade_medida: '',
      valor_base: '',
    };
    showManualItemEditor.value = false;
  } catch (err) {
    loadError.value = `Falha ao adicionar item manual (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isAddingManualItem.value = false;
  }
}

function toggleManualItemEditor() {
  if (isSessaoFechada.value || isAddingManualItem.value) return;
  showManualItemEditor.value = !showManualItemEditor.value;
}

function onManualBaseInput(event) {
  const raw = String(event?.target?.value || '');
  const digits = raw.replace(/\D/g, '');
  if (!digits) {
    manualItem.value.valor_base = '';
    return;
  }
  const cents = Number.parseInt(digits, 10);
  if (!Number.isFinite(cents)) {
    manualItem.value.valor_base = '';
    return;
  }
  const value = cents / 100;
  manualItem.value.valor_base = value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function parseCurrencyInputToNumber(value) {
  const s = String(value || '').trim();
  if (!s) return null;
  const only = s.replace(/[^\d,.-]/g, '').replace(/\./g, '').replace(',', '.');
  const n = Number(only);
  return Number.isFinite(n) ? n : null;
}

function parsePercentInputToNumber(value) {
  const s = String(value || '').trim();
  if (!s) return null;
  const only = s.replace(/\D/g, '');
  if (!only) return null;
  const n = Number.parseInt(only, 10);
  return Number.isFinite(n) ? n : null;
}

function onVariacaoGlobalInput(event) {
  const raw = String(event?.target?.value || '');
  const digits = raw.replace(/\D/g, '');
  if (!digits) {
    variacaoGlobalPercentual.value = '0';
    event.target.value = '0';
    return;
  }
  const n = Number.parseInt(digits, 10);
  const normalized = Number.isFinite(n) ? String(Math.min(100, Math.max(0, n))) : '0';
  variacaoGlobalPercentual.value = normalized;
  event.target.value = normalized;
}

async function salvarVariacaoGlobal() {
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Cotação inválida para salvar variação global.';
    return;
  }
  if (isSessaoFechada.value || isSavingVariacaoGlobal.value) return;
  const vg = parsePercentInputToNumber(variacaoGlobalPercentual.value);
  if (!Number.isFinite(vg) || vg < 0) {
    loadError.value = 'Informe uma variação global válida.';
    return;
  }
  isSavingVariacaoGlobal.value = true;
  loadError.value = '';
  try {
    await updateResearchSession(sessionId, {
      variacao_percentual_global: vg,
      variacao_sentido_global: variacaoGlobalSentido.value,
    });
    await loadSessionFromBackend();
  } catch (err) {
    loadError.value = `Falha ao salvar variação global (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isSavingVariacaoGlobal.value = false;
  }
}

function parseQuantityInputToNumber(value) {
  const s = String(value || '').trim();
  if (!s) return null;
  const normalized = s.replace(/\s+/g, '').replace(/\./g, '').replace(',', '.');
  const n = Number(normalized);
  return Number.isFinite(n) ? n : null;
}

async function onImportSpreadsheetSelected(event) {
  const sessionId = Number(cotacaoId.value);
  const file = event?.target?.files?.[0];
  event.target.value = '';
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Cotação inválida para importação.';
    return;
  }
  if (!file) return;
  importLoading.value = true;
  loadError.value = '';
  try {
    const res = await importItemsSpreadsheetToResearchSession(sessionId, file, {
      descricao_item: 'descricao_item',
      valor_base: 'valor_base',
      quantidade: 'quantidade',
      unidade_medida: 'unidade_medida',
      valor_unitario: 'valor_unitario',
      numero_item: 'numero_item',
    });
    await loadSessionFromBackend();
    const invalid = Number(res?.linhas_invalidas || 0);
    loadError.value =
      invalid > 0
        ? `Planilha importada com sucesso: ${res?.itens_inseridos || 0} itens. ${invalid} linha(s) inválida(s).`
        : '';
  } catch (err) {
    loadError.value = `Falha ao importar planilha: ${err?.message || 'erro desconhecido'}. Coluna obrigatória: descricao_item. Recomendada: valor_base.`;
  } finally {
    importLoading.value = false;
  }
}

async function onSupplierPdfSelected(event) {
  const sessionId = Number(cotacaoId.value);
  const files = Array.from(event?.target?.files || []);
  event.target.value = '';
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Cotação inválida para anexar PDF.';
    return;
  }
  if (!files.length) return;
  supplierPdfLoading.value = true;
  loadError.value = '';
  try {
    const res = await uploadSupplierPdfToResearchSession(sessionId, files);
    hasSupplierPdfAttachment.value = true;
    const novos = Array.isArray(res?.arquivos)
      ? res.arquivos.map((x) => String(x?.nome || '').trim()).filter(Boolean)
      : [];
    supplierPdfFilenames.value = [...novos, ...supplierPdfFilenames.value].filter(Boolean);
  } catch (err) {
    loadError.value = `Falha ao anexar PDF do fornecedor: ${err?.message || 'erro desconhecido'}.`;
  } finally {
    supplierPdfLoading.value = false;
  }
}

function closeRelatorioModal() {
  if (relatorioLoading.value) return;
  relatorioModalOpen.value = false;
}

function fallbackRelatorioFilename(sessionId, titulo) {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}`;
  const slug = String(titulo || 'relatorio')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/[-\s]+/g, '-')
    .slice(0, 42) || 'relatorio';
  return `docmaster-pesquisador-pncp_usuario_${stamp}_cotacao-${sessionId}_${slug}.pdf`;
}

async function submitRelatorioPdf() {
  const sessionId = Number(cotacaoId.value);
  const t = (relatorioTitulo.value || '').trim();
  if (Number.isNaN(sessionId)) {
    relatorioError.value = 'Cotação inválida.';
    return;
  }
  if (!t) {
    relatorioError.value = 'Informe o título do relatório.';
    return;
  }
  if (totalItensSessao.value === 0) {
    relatorioError.value = 'Esta cotação ainda não possui itens para gerar o relatório.';
    return;
  }
  relatorioError.value = '';
  relatorioLoading.value = true;
  try {
    const { blob, filename } = await downloadCotacaoRelatorioPdf(sessionId, t);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (filename || '').trim() || fallbackRelatorioFilename(sessionId, t);
    a.click();
    URL.revokeObjectURL(url);
    relatorioModalOpen.value = false;
  } catch (e) {
    relatorioError.value = e?.message || 'Falha ao gerar o PDF.';
  } finally {
    relatorioLoading.value = false;
  }
}

let escHandler = null;
watch(pendingDelete, (open) => {
  if (escHandler) {
    window.removeEventListener('keydown', escHandler);
    escHandler = null;
  }
  if (open) {
    escHandler = (e) => {
      if (e.key === 'Escape') cancelDelete();
    };
    window.addEventListener('keydown', escHandler);
  }
});

let escRelatorio = null;
watch(relatorioModalOpen, (open) => {
  if (escRelatorio) {
    window.removeEventListener('keydown', escRelatorio);
    escRelatorio = null;
  }
  if (open) {
    escRelatorio = (e) => {
      if (e.key === 'Escape') closeRelatorioModal();
    };
    window.addEventListener('keydown', escRelatorio);
  }
});

onUnmounted(() => {
  if (escHandler) window.removeEventListener('keydown', escHandler);
  if (escRelatorio) window.removeEventListener('keydown', escRelatorio);
});

onMounted(() => {
  loadSessionFromBackend();
});

async function loadSessionFromBackend() {
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'ID de cotação inválido para backend PNCP.';
    return;
  }
  isLoading.value = true;
  loadError.value = '';
  faixaBaseDraft.value = {};
  try {
    const data = await getResearchSession(sessionId);
    if (data?.ok && data.sessao) {
      const s = data.sessao;
      tituloCotacao.value = s.titulo || `Cotação ${cotacaoId.value}`;
      sessaoCreatedAt.value = formatDateTimePt(s.created_at);
      sessaoCriadoPor.value = s.criado_por || '—';
      sessaoCriadoPorEmail.value = (s.criado_por_email || '').trim();
      sessaoStatus.value = String(s.status || 'aberta').toLowerCase();
      hasSupplierPdfAttachment.value = !!s.anexo_fornecedor_pdf;
      supplierPdfFilenames.value = Array.isArray(s.anexos_fornecedor)
        ? s.anexos_fornecedor.map((x) => String(x?.nome || '').trim()).filter(Boolean)
        : (s.anexo_fornecedor_nome ? [String(s.anexo_fornecedor_nome).trim()] : []);
      totalItensSessao.value = Number(s.total_itens) || 0;
      formulaCalculoId.value = s.formula_calculo_id || 'media_aritmetica_precos_obtidos';
      formulaCalculoLabel.value =
        s.formula_calculo ||
        data?.calculo_precos?.formula_label ||
        'Média aritmética dos preços obtidos';
      const filtrosSessao = (s?.filtros && typeof s.filtros === 'object') ? s.filtros : {};
      const variacaoGlobal = Number(filtrosSessao.variacao_percentual_global);
      variacaoGlobalPercentual.value = Number.isFinite(variacaoGlobal) && variacaoGlobal >= 0
        ? String(Math.round(variacaoGlobal))
        : '20';
      const sentidoRaw = String(filtrosSessao.variacao_sentido_global || '').trim().toLowerCase();
      variacaoGlobalSentido.value = sentidoRaw === 'baixo' ? 'baixo' : 'cima';
    }
    if (data?.ok && Array.isArray(data.itens)) {
      let soma = 0;
      let temValor = false;
      const fontesPorGrupo = new Map();
      if (Array.isArray(data?.grupos_relatorio)) {
        for (const g of data.grupos_relatorio) {
          const key = buildGrupoStatusKey(g?.nome, g?.unidade, g?.quantidade_fmt);
          const nCot = Number(g?.n_cotacoes);
          fontesPorGrupo.set(key, Number.isFinite(nCot) ? nCot : 0);
        }
      }
      linhasMock.value = data.itens.map((it, idx) => {
        const vt = Number(
          it.valor_total_refletido ?? it.valor_total ?? it.valor_unitario,
        );
        if (Number.isFinite(vt) && vt >= 0) {
          soma += vt;
          temValor = true;
        }
        const statusKey = buildGrupoStatusKey(it?.descricao_item, it?.unidade_medida, it?.quantidade);
        const totalFontesRelatorio = Number(fontesPorGrupo.get(statusKey) ?? 0);
        const fontesContagem = it?.fontes_contagem || {};
        const totalCotacoesItem = Number(fontesContagem.governamentais || 0)
          + Number(fontesContagem.entesPublicos || 0)
          + Number(fontesContagem.dominioAmplo || 0)
          + Number(fontesContagem.cotacaoDireta || 0)
          + Number(fontesContagem.notasFiscais || 0);
        return {
          id: it.id || idx + 1,
          nomeItem: it.descricao_item || `Item ${idx + 1}`,
          fontes: {
            governamentais: Number(fontesContagem.governamentais || 0),
            entesPublicos: Number(fontesContagem.entesPublicos || 0),
            dominioAmplo: Number(fontesContagem.dominioAmplo || 0),
            cotacaoDireta: Number(fontesContagem.cotacaoDireta || 0),
            notasFiscais: Number(fontesContagem.notasFiscais || 0),
            similaridadeEncontrada: Number(fontesContagem.similaridadeEncontrada || 0),
          },
          qtd: (() => {
            const raw = it?.quantidade;
            if (raw === null || raw === undefined || raw === '') return '—';
            const n = Number(raw);
            return Number.isFinite(n) ? n : '—';
          })(),
          und: String(it.unidade_medida_refletida || '').trim() || it.unidade_medida || '-',
          precoTotal: formatCurrency(
            it.valor_total_refletido ?? it.valor_total ?? it.valor_unitario ?? 0,
          ),
          faixaRegionalBase: formatFaixaRegionalBase(it),
          faixaBaseInputSeed: initialFaixaBaseCurrencyInput(it),
          faixaRegionalVariacao: formatFaixaRegionalVariacao(it, variacaoGlobalPercentual.value),
          // Regra de status: 3 ou mais preços/cotações no item => Completo.
          // Fallback para grupos de relatório apenas quando não houver contagem detalhada.
          status: (totalCotacoesItem > 0 ? totalCotacoesItem : totalFontesRelatorio) >= 3 ? 'Completo' : 'Incompleto',
        };
      });
      valorTotalItensFmt.value = temValor ? formatCurrency(soma) : 'R$ —';
    } else if (data?.ok) {
      linhasMock.value = [];
      valorTotalItensFmt.value = 'R$ —';
      totalItensSessao.value = 0;
    }
  } catch (err) {
    loadError.value = `Não foi possível carregar a sessão no backend (${err.message || 'erro desconhecido'}).`;
    linhasMock.value = [];
    valorTotalItensFmt.value = 'R$ —';
    sessaoCriadoPor.value = '—';
    sessaoCriadoPorEmail.value = '';
    sessaoStatus.value = 'aberta';
    hasSupplierPdfAttachment.value = false;
    supplierPdfFilenames.value = [];
    totalItensSessao.value = 0;
    formulaCalculoId.value = 'media_aritmetica_precos_obtidos';
    formulaCalculoLabel.value = 'Média aritmética dos preços obtidos';
    variacaoGlobalPercentual.value = '20';
    variacaoGlobalSentido.value = 'cima';
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
    if (Number.isFinite(n) && n > 0) return n;
  }
  return null;
}

function extractItemSourceNumber(item, ...keys) {
  const src = item?.sourceRaw || item?.source;
  if (!src || typeof src !== 'object') return null;
  for (const k of keys) {
    const n = Number(src[k]);
    if (Number.isFinite(n) && n > 0) return n;
  }
  const faixa = src?.faixa_regional || src?.faixaRegional;
  if (faixa && typeof faixa === 'object') {
    for (const k of keys) {
      const n = Number(faixa[k]);
      if (Number.isFinite(n) && n > 0) return n;
    }
  }
  return null;
}

function formatFaixaRegionalBase(item) {
  const byItem = pickNumeric(
    extractItemSourceNumber(item, 'valor_base', 'valorBase', 'preco_base', 'precoBase'),
  );
  const byValue = pickNumeric(item?.valor_unitario, item?.valor_total);
  const base = byItem ?? byValue;
  return base ? formatCurrency(base) : 'R$ —';
}

function formatFaixaRegionalVariacao(_item, variacaoGlobalFallback = null) {
  const byGlobal = Number(variacaoGlobalFallback);
  const v = Number.isFinite(byGlobal) && byGlobal >= 0 ? byGlobal : null;
  return v !== null ? `${Math.round(Number(v)).toLocaleString('pt-BR')}%` : '—';
}

function initialFaixaBaseCurrencyInput(item) {
  const byItem = pickNumeric(
    extractItemSourceNumber(item, 'valor_base', 'valorBase', 'preco_base', 'precoBase'),
  );
  const byValue = pickNumeric(item?.valor_unitario, item?.valor_total);
  const base = byItem ?? byValue;
  if (!base) return '';
  return formatCurrency(base);
}

function faixaBaseDisplay(linha) {
  const d = faixaBaseDraft.value[linha.id];
  if (d !== undefined) return d;
  return linha.faixaBaseInputSeed || '';
}

function onFaixaBaseRowInput(itemId, event) {
  const raw = String(event?.target?.value || '');
  const digits = raw.replace(/\D/g, '');
  if (!digits) {
    faixaBaseDraft.value = { ...faixaBaseDraft.value, [itemId]: '' };
    return;
  }
  const cents = Number.parseInt(digits, 10);
  if (!Number.isFinite(cents)) {
    faixaBaseDraft.value = { ...faixaBaseDraft.value, [itemId]: '' };
    return;
  }
  const value = cents / 100;
  const formatted = value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  faixaBaseDraft.value = { ...faixaBaseDraft.value, [itemId]: formatted };
}

async function salvarFaixaBaseItem(linha) {
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId) || isSessaoFechada.value) return;
  if (savingFaixaItemId.value) return;
  const display = faixaBaseDisplay(linha);
  const valorNum = parseCurrencyInputToNumber(display);
  savingFaixaItemId.value = linha.id;
  loadError.value = '';
  try {
    await updateResearchSessionItem(sessionId, linha.id, {
      valor_base: valorNum,
    });
    const next = { ...faixaBaseDraft.value };
    delete next[linha.id];
    faixaBaseDraft.value = next;
    await loadSessionFromBackend();
  } catch (err) {
    loadError.value = `Falha ao salvar valor base do item (${err?.message || 'erro desconhecido'}).`;
  } finally {
    savingFaixaItemId.value = null;
  }
}

function formatCurrency(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return 'R$ -';
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDateTimePt(iso) {
  if (!iso) return '—';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return String(iso);
  return dt.toLocaleString('pt-BR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function salvarTituloCotacao() {
  saveTituloNoBackend();
}

function itemDetalheTo(itemId) {
  return {
    name: 'CotacaoItemDetalhe',
    params: {
      cotacaoId: String(cotacaoId.value),
      itemId: String(itemId),
    },
  };
}

function openItemCotacoesFromFonte(itemId, fonte) {
  const iid = Number(itemId);
  if (!Number.isFinite(iid) || iid <= 0) return;
  router.push({
    name: 'CotacaoItemDetalhe',
    params: {
      cotacaoId: String(cotacaoId.value),
      itemId: String(iid),
    },
    query: { fonte },
  });
}

async function saveTituloNoBackend() {
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Não foi possível salvar: cotação sem ID numérico.';
    return;
  }
  loadError.value = '';
  try {
    await updateResearchSession(sessionId, {
      titulo: tituloCotacao.value || `Cotação ${sessionId}`,
    });
    tituloSalvo.value = true;
    setTimeout(() => {
      tituloSalvo.value = false;
    }, 1500);
  } catch (err) {
    loadError.value = `Falha ao salvar título (${err.message || 'erro desconhecido'}).`;
  }
}
</script>

<style scoped>
.gov-page { display: flex; flex-direction: column; gap: 16px; width: 100%; min-width: 0; }
.gov-page__title { margin: 0; font-size: 24px; }
.gov-page__subtitle { margin: 6px 0 0; color: var(--color-text-soft); }
.cot-meta { margin: 8px 0 0; font-size: 12px; color: #64748b; }
.cot-meta--error { color: #b91c1c; }
.gov-page__content { padding: 16px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.cot-header-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.cot-back-btn { border: 1px solid #cfd8e3; border-radius: 10px; background: #fff; color: #1f2937; padding: 7px 12px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 7px; }

.cot-head__summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; }
.cot-card { border: 1px solid #d6dde8; border-radius: 10px; background: #fff; padding: 10px; display: flex; flex-direction: column; gap: 2px; }
.cot-card--highlight strong { color: #1f4e79; }
.cot-card__label { font-size: 11px; text-transform: uppercase; color: var(--color-text-soft); }
.cot-card__email {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: var(--color-text-soft);
  word-break: break-all;
}
.cot-title-editor {
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  display: flex;
  align-items: end;
  gap: 8px;
  flex-wrap: wrap;
}

.cot-title-editor__field {
  flex: 1 1 320px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cot-title-editor__field span {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--color-text-soft);
}

.cot-title-editor__field input {
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  outline: none;
}

.cot-page-toast {
  position: fixed;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 999;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #b7d2ef;
  background: #e8f1fb;
  color: #1f4e79;
  border-radius: 999px;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 600;
}

.cot-formula {
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.cot-formula__icon {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: #e8f1fb;
  color: #1f4e79;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.cot-formula__text { display: flex; flex-direction: column; gap: 2px; }
.cot-formula__title { font-size: 13px; font-weight: 600; }
.cot-formula__subtitle { font-size: 12px; color: var(--color-text-soft); }

.cot-formula__select {
  margin-left: auto;
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  padding: 7px 10px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.cot-global-variacao {
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  padding: 10px 12px;
  box-sizing: border-box;
  max-width: 100%;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px 12px;
}

.cot-global-variacao__text {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  flex-wrap: nowrap;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
  line-height: 1.25;
}

.cot-global-variacao__title {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.cot-global-variacao__sep {
  font-size: 13px;
  color: #94a3b8;
  flex-shrink: 0;
  user-select: none;
}

.cot-global-variacao__subtitle {
  font-size: 12px;
  color: var(--color-text-soft);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.cot-global-variacao__actions {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  min-width: 0;
  max-width: 100%;
  justify-self: end;
}

.cot-global-variacao__direction {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--color-text-soft);
  white-space: nowrap;
}

.cot-global-variacao__direction > span {
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.cot-global-variacao__select {
  margin-left: 0;
  min-width: 110px;
  padding: 6px 10px;
}

.cot-global-variacao__percent-wrap {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.cot-sheet-inline-input--variacao-global {
  width: 3.25rem;
  min-width: 2.5rem;
  max-width: 100%;
  box-sizing: border-box;
  text-align: right;
}

.cot-global-variacao__suffix {
  font-size: 14px;
  font-weight: 700;
  color: #334155;
  line-height: 1;
  user-select: none;
}

.cot-global-variacao__submit {
  white-space: nowrap;
}

@media (max-width: 720px) {
  .cot-global-variacao {
    grid-template-columns: 1fr;
  }
  .cot-global-variacao__actions {
    justify-self: stretch;
    justify-content: flex-end;
    flex-wrap: wrap;
    row-gap: 8px;
  }
}

.cot-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.cot-btn { border: 1px solid #cfd8e3; border-radius: 10px; background: #fff; color: #1f2937; padding: 7px 12px; font-size: 12px; text-decoration: none; cursor: pointer; display: inline-flex; align-items: center; gap: 7px; }
.cot-btn--primary { background: #1f4e79; color: #fff; border-color: #1f4e79; }
.cot-btn--danger { background: #b91c1c; color: #fff; border-color: #b91c1c; }
.cot-btn--success { background: #166534; color: #fff; border-color: #166534; }
.cot-btn--disabled { pointer-events: none; opacity: 0.55; }
.cot-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.cot-fornecedor-field {
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cot-fornecedor-field__label {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--color-text-soft);
}
.cot-fornecedor-field__value {
  font-size: 13px;
  color: #111827;
  word-break: break-word;
}
.cot-fornecedor-field__list {
  margin: 2px 0 0;
  padding-left: 18px;
  color: #374151;
  font-size: 12px;
  display: grid;
  gap: 2px;
}
.cot-hidden-file-input { display: none; }

.cot-new-item-block {
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.cot-new-item-block__text h2 {
  margin: 0;
  font-size: 16px;
}

.cot-new-item-block__text p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-soft);
}

.cot-new-item-block__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.cot-sheet-row-add { background: #f8fbff; }
.cot-sheet-inline-input {
  width: 100%;
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 12px;
  outline: none;
  background: #fff;
}
.cot-faixa-inline {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.cot-faixa-inline--manual {
  grid-template-columns: 1fr;
  min-width: 0;
}

.cot-sheet-inline-input--faixa-base-manual {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
}

.cot-faixa-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.cot-faixa-edit-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.cot-sheet-inline-input--faixa-base {
  width: 6.5rem;
  min-width: 4rem;
  flex: 1 1 4rem;
  max-width: 100%;
  box-sizing: border-box;
}

.cot-faixa-var-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 6px;
  font-size: 11px;
  color: var(--color-text-soft);
}

.cot-faixa-var-row__value {
  font-size: 12px;
  color: #0f172a;
}

.cot-faixa-var-row__hint {
  font-size: 10px;
  font-weight: 500;
  color: #64748b;
}

.cot-sheet-action-btn--compact {
  padding: 4px 8px;
  font-size: 11px;
}

.cot-sheet-shell {
  width: 100%;
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  padding: 12px;
  min-width: 0;
  max-width: 100%;
}

.cot-sheet-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.cot-sheet-search {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #cfd8e3;
  border-radius: 10px;
  background: #fff;
  color: #64748b;
  padding: 7px 10px;
  min-width: 260px;
  flex: 1 1 320px;
}

.cot-sheet-search input {
  border: 0;
  outline: none;
  width: 100%;
  min-width: 0;
  font-size: 12px;
  color: #1f2937;
  background: transparent;
}

.cot-sheet-status-filter {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #cfd8e3;
  border-radius: 10px;
  background: #fff;
  color: #475569;
  padding: 7px 10px;
  font-size: 12px;
  flex-shrink: 0;
}

.cot-sheet-status-filter span {
  font-weight: 600;
  color: #64748b;
}

.cot-sheet-status-filter select {
  border: 0;
  outline: none;
  background: transparent;
  color: #1f2937;
  font-size: 12px;
}

.cot-sheet-bulk-delete {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
  border: 1px solid #e5c9c9;
  border-radius: 10px;
  background: #fff;
  color: #b05d5d;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.cot-sheet-bulk-delete:hover:not(:disabled) {
  background: #fff5f5;
}

.cot-sheet-bulk-delete:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.cot-sheet-scroll {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  min-width: 0;
}

.cot-sheet-table {
  width: 100%;
  min-width: 1100px;
  border-collapse: collapse;
  table-layout: fixed;
}

.cot-sheet-table th,
.cot-sheet-table td {
  border: 1px solid #e5eaf3;
  padding: 8px;
  font-size: 11px;
  line-height: 1.25;
}

.cot-sheet-table thead th {
  background: #f8fafc;
  color: #334155;
  font-weight: 700;
  text-transform: uppercase;
}

.cot-sheet-group {
  text-align: center;
  background: #edf4ff !important;
}

.cot-sheet-source {
  background: #edf4ff !important;
}

.cot-sheet-source__icon {
  display: block;
  text-align: center;
  font-size: 13px;
  margin-bottom: 3px;
  color: #334155;
}

.cot-sheet-source__title {
  display: block;
  font-size: 10px;
  line-height: 1.15;
}

.cot-sheet-source__sub {
  display: block;
  font-size: 10px;
  line-height: 1.15;
  color: #64748b;
  text-transform: none;
}

.cot-sheet-center {
  text-align: center;
}

.cot-sheet-checkbox {
  width: 15px;
  height: 15px;
  cursor: pointer;
}

.cot-sheet-source-cell {
  min-width: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  border: 1px solid #d4dbe6;
  padding: 4px 7px;
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  cursor: pointer;
}

.cot-sheet-source-cell--gray {
  background: #eef2f7;
  color: #475569;
  border-color: #d5dde9;
}

.cot-sheet-source-cell--green {
  background: #e4efff;
  color: #1f4e79;
  border-color: #b7d2ef;
}

.cot-sheet-source-cell:hover {
  filter: brightness(0.97);
}

.cot-sheet-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 10px;
  white-space: nowrap;
}

.cot-sheet-status--completo {
  border: 1px solid #b7d2ef;
  background: #e8f1ff;
  color: #1f4e79;
}

.cot-sheet-status--incompleto {
  border: 1px solid #f3c1c1;
  background: #fff1f1;
  color: #b42323;
}

.cot-faixa-block {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #d6dde8;
  border-radius: 8px;
  background: #f8fafc;
  padding: 4px 6px;
  white-space: nowrap;
}

.cot-faixa-block__label {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
}

.cot-faixa-block__value {
  font-size: 11px;
  color: #1f2937;
}

.cot-faixa-block__dot {
  color: #64748b;
}

.cot-sheet-actions {
  display: flex;
  gap: 6px;
  flex-wrap: nowrap;
}

.cot-sheet-action-btn {
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  color: #1f2937;
  padding: 4px 8px;
  font-size: 11px;
  white-space: nowrap;
  cursor: pointer;
}

.cot-sheet-action-btn--danger {
  border-color: #e5c9c9;
  color: #b05d5d;
}

.cot-item-nome-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cot-similaridade-tag {
  display: inline-flex;
  align-items: center;
  border: 1px solid #f2dfb7;
  background: #fff7e6;
  color: #9a6a10;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}


/* Alinhado ao modal de exclusão em `PncpResearcher.vue` */
.pncp-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(15, 23, 42, 0.45);
}

.pncp-modal {
  width: 100%;
  max-width: 420px;
  border-radius: var(--radius-md);
  background: #fff;
  border: 1px solid #d6dde8;
  box-shadow: 0 16px 48px rgba(15, 23, 42, 0.18);
  padding: 20px;
}

.pncp-modal__title {
  margin: 0 0 10px;
  font-size: 18px;
  color: #0f172a;
}

.pncp-modal__text {
  margin: 0 0 10px;
  font-size: 14px;
  line-height: 1.45;
  color: var(--color-text-soft);
}

.pncp-modal__quote {
  margin: 0 0 16px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f6f9fc;
  border: 1px solid #e8edf4;
  font-size: 12px;
  line-height: 1.4;
  color: #334155;
}

.pncp-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.pncp-modal__btn {
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.pncp-modal__btn--ghost {
  background: #fff;
  border-color: #cfd8e3;
  color: #334155;
}

.pncp-modal__btn--ghost:hover {
  background: #f6f9fc;
}

a.pncp-modal__link-btn {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.pncp-modal__btn--danger {
  background: #b91c1c;
  border-color: #b91c1c;
  color: #fff;
}

.pncp-modal__btn--danger:hover {
  filter: brightness(0.95);
}

.pncp-modal--relatorio {
  max-width: 560px;
}

.pncp-modal__error {
  margin: 0 0 12px;
  font-size: 13px;
  color: #b91c1c;
}

.pncp-modal__btn--primary {
  background: #1f4e79;
  border-color: #1f4e79;
  color: #fff;
}

.pncp-modal__btn--primary:hover:not(:disabled) {
  filter: brightness(0.95);
}

.pncp-modal__btn--primary:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.cot-relatorio-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 0 16px;
  font-size: 12px;
  color: var(--color-text-soft);
}

.cot-relatorio-field span abbr {
  text-decoration: none;
  color: #b91c1c;
}

.cot-relatorio-info {
  margin: -4px 0 12px;
  font-size: 12px;
  color: #475569;
}

/* Dark mode dedicado da rota /pesquisador-pncp/cotacoes/:id */
:deep(.dm-dark) .cot-back-btn,
:deep(.dm-dark) .cot-btn,
:deep(.dm-dark) .cot-sheet-action-btn,
:deep(.dm-dark) .cot-sheet-bulk-delete {
  background: #0f172a !important;
  border-color: #475569 !important;
  color: #e2e8f0 !important;
}

:deep(.dm-dark) .cot-btn--primary {
  background: #1e293b !important;
  border-color: #64748b !important;
  color: #f8fafc !important;
}

:deep(.dm-dark) .cot-btn--danger,
:deep(.dm-dark) .cot-sheet-action-btn--danger {
  background: rgba(185, 28, 28, 0.18) !important;
  border-color: #7f1d1d !important;
  color: #fecaca !important;
}

:deep(.dm-dark) .cot-card,
:deep(.dm-dark) .cot-title-editor,
:deep(.dm-dark) .cot-formula,
:deep(.dm-dark) .cot-global-variacao,
:deep(.dm-dark) .cot-fornecedor-field,
:deep(.dm-dark) .cot-new-item-block,
:deep(.dm-dark) .cot-sheet-shell {
  background: #0f172a !important;
  border-color: #334155 !important;
}

:deep(.dm-dark) .cot-card strong,
:deep(.dm-dark) .cot-new-item-block__text h2,
:deep(.dm-dark) .cot-fornecedor-field__value,
:deep(.dm-dark) .cot-sheet-table td,
:deep(.dm-dark) .cot-item-nome-wrap span {
  color: #e2e8f0 !important;
}

:deep(.dm-dark) .cot-card__label,
:deep(.dm-dark) .cot-meta,
:deep(.dm-dark) .cot-title-editor__field span,
:deep(.dm-dark) .cot-formula__subtitle,
:deep(.dm-dark) .cot-global-variacao__subtitle,
:deep(.dm-dark) .cot-global-variacao__sep,
:deep(.dm-dark) .cot-global-variacao__suffix {
  color: #f8fafc !important;
}

:deep(.dm-dark) .cot-global-variacao__direction {
  color: #e2e8f0 !important;
}

:deep(.dm-dark) .cot-fornecedor-field__label,
:deep(.dm-dark) .cot-new-item-block__text p,
:deep(.dm-dark) .cot-sheet-table thead th,
:deep(.dm-dark) .cot-sheet-source__sub,
:deep(.dm-dark) .cot-faixa-block__label,
:deep(.dm-dark) .cot-relatorio-field,
:deep(.dm-dark) .cot-relatorio-info {
  color: #94a3b8 !important;
}

:deep(.dm-dark) .cot-title-editor__field input,
:deep(.dm-dark) .cot-formula__select,
:deep(.dm-dark) .cot-sheet-inline-input,
:deep(.dm-dark) .cot-sheet-search,
:deep(.dm-dark) .cot-sheet-status-filter,
:deep(.dm-dark) .cot-sheet-search input,
:deep(.dm-dark) .cot-sheet-status-filter select {
  background: #111827 !important;
  border-color: #334155 !important;
  color: #e2e8f0 !important;
}

:deep(.dm-dark) .cot-sheet-row-add,
:deep(.dm-dark) .cot-sheet-table thead th {
  background: #111827 !important;
}

:deep(.dm-dark) .cot-sheet-table th,
:deep(.dm-dark) .cot-sheet-table td {
  border-color: #334155 !important;
}

:deep(.dm-dark) .cot-sheet-group,
:deep(.dm-dark) .cot-sheet-source {
  background: #1e293b !important;
}

:deep(.dm-dark) .cot-sheet-source__icon,
:deep(.dm-dark) .cot-sheet-source__title {
  color: #cbd5e1 !important;
}

:deep(.dm-dark) .cot-sheet-source-cell--gray {
  background: #0f172a !important;
  border-color: #475569 !important;
  color: #cbd5e1 !important;
}

:deep(.dm-dark) .cot-sheet-source-cell--green {
  background: rgba(30, 64, 175, 0.22) !important;
  border-color: #1d4ed8 !important;
  color: #93c5fd !important;
}

:deep(.dm-dark) .cot-sheet-status--completo {
  background: rgba(22, 101, 52, 0.22) !important;
  border-color: #166534 !important;
  color: #86efac !important;
}

:deep(.dm-dark) .cot-sheet-status--incompleto {
  background: rgba(185, 28, 28, 0.22) !important;
  border-color: #7f1d1d !important;
  color: #fecaca !important;
}

:deep(.dm-dark) .cot-faixa-block {
  background: #111827 !important;
  border-color: #334155 !important;
}

:deep(.dm-dark) .cot-faixa-var-row__value {
  color: #e2e8f0 !important;
}

:deep(.dm-dark) .cot-faixa-var-row__hint {
  color: #94a3b8 !important;
}

:deep(.dm-dark) .cot-faixa-block__value,
:deep(.dm-dark) .cot-faixa-block__dot {
  color: #e2e8f0 !important;
}

:deep(.dm-dark) .cot-similaridade-tag {
  background: rgba(161, 98, 7, 0.22) !important;
  color: #fcd34d !important;
  border-color: #a16207 !important;
}

</style>
