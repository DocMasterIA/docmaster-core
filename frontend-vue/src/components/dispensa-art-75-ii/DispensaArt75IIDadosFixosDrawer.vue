<template>
  <Teleport to="body">
    <div v-if="open" class="ixp-overlay" role="presentation" @click="$emit('close')" />
    <aside :class="['ixp-drawer', open && 'is-open']" :aria-hidden="!open">
      <div class="ixp-drawer-head">
        <div>
          <small>Configuração oculta</small>
          <h3>Dados fixos</h3>
        </div>
        <button type="button" class="ixp-btn-secondary" @click="$emit('close')">X</button>
      </div>

      <div class="ixp-drawer-body">
        <article class="ixp-card">
          <h3>Cadastros de Órgãos</h3>
          <div class="ixp-body">
            <div class="ixp-field">
              <label>Órgão cadastrado</label>
              <select :value="ctx.selectedOrgaoProfileId" @change="ctx.loadOrgaoProfile(($event.target).value)">
                <option value="">Selecione um cadastro salvo</option>
                <option v-for="p in (ctx.orgaoProfiles || [])" :key="`org-${p.id}`" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div class="ixp-field">
              <label>Nome do cadastro</label>
              <input v-model="ctx.orgaoProfileName" placeholder="Ex: Fundo Municipal de Saúde" />
            </div>
            <div class="ixp-inline-actions ixp-orgao-profile-actions">
              <button type="button" class="ixp-btn-secondary ixp-btn-xs ixp-orgao-btn-new" @click="ctx.newOrgaoProfile()">Novo cadastro</button>
              <button type="button" class="ixp-btn-secondary ixp-btn-xs ixp-orgao-btn-save" @click="ctx.saveOrgaoProfile()">Salvar cadastro</button>
              <button
                type="button"
                class="ixp-btn-secondary ixp-btn-xs ixp-orgao-btn-delete"
                :disabled="!ctx.selectedOrgaoProfileId"
                @click="ctx.deleteOrgaoProfile()"
              >
                Excluir cadastro
              </button>
            </div>
          </div>
        </article>

        <article class="ixp-card">
          <h3>1. Solicitação / Ofício</h3>
          <div class="ixp-body">
            <div class="ixp-grid-3">
              <div class="ixp-field">
                <label>Tratamento</label>
                <select v-model="ctx.fixoTratNome">
                  <option value="">Selecione</option>
                  <option v-for="op in ctx.tratamentoNome" :key="op" :value="op">{{ op }}</option>
                </select>
              </div>
              <div class="ixp-field ixp-col-2">
                <label>1.1 A quem é direcionada a solicitação — Nome</label>
                <input v-model="ctx.fixoNome" list="da75-dl-solicitacao-destinatario-nome" placeholder="Digite o nome" />
              </div>
            </div>
            <div class="ixp-grid-3">
              <div class="ixp-field">
                <label>Tratamento</label>
                <select v-model="ctx.fixoTratCargo">
                  <option value="">Selecione</option>
                  <option v-for="op in ctx.tratamentoCargo" :key="op" :value="op">{{ op }}</option>
                </select>
              </div>
              <div class="ixp-field ixp-col-2">
                <label>1.2 A quem é direcionada a solicitação — Função / Cargo</label>
                <input v-model="ctx.fixoCargo" list="da75-dl-solicitacao-destinatario-cargo" placeholder="Digite a função ou cargo" />
              </div>
            </div>
            <h4 class="ixp-subsection-title">1.3 Responsável pela solicitação</h4>
            <div class="ixp-grid-2">
              <div class="ixp-field">
                <label>Nome do responsável</label>
                <input v-model="ctx.fixoResponsavel" list="da75-dl-solicitacao-responsavel-nome" placeholder="Digite o nome do responsável" />
              </div>
              <div class="ixp-field">
                <label>Função / Cargo</label>
                <input v-model="ctx.fixoResponsavelCargo" list="da75-dl-solicitacao-responsavel-cargo" placeholder="Digite o cargo" />
              </div>
            </div>
          </div>
        </article>

        <article class="ixp-card">
          <h3>2. DFD – Documento de Formalização da Demanda</h3>
          <div class="ixp-body ixp-grid-1">
            <div class="ixp-field">
              <label>2.1 Setor requisitante (Unidade / Setor / Departamento)</label>
              <input v-model="ctx.fixoSetor" list="da75-dl-dfd-setor-requisitante" />
            </div>
            <div class="ixp-field">
              <label>2.2 Responsável pela demanda</label>
              <input v-model="ctx.fixoDemanda" list="da75-dl-dfd-responsavel-demanda" />
            </div>
            <div class="ixp-field">
              <label>2.3 E-mail</label>
              <input v-model="ctx.fixoEmail" list="da75-dl-dfd-email" />
            </div>
            <div class="ixp-field">
              <label>2.4 Nome do(a) gestor(a) de contratos</label>
              <input v-model="ctx.fixoGestor" list="da75-dl-dfd-gestor-contratos" />
            </div>
            <div class="ixp-field">
              <label>2.5 Nome do(a) fiscal de contratos</label>
              <input v-model="ctx.fixoFiscal" list="da75-dl-dfd-fiscal-contratos" />
            </div>
            <h4 class="ixp-subsection-title">2.6 Responsável pela assinatura do DFD</h4>
            <div class="ixp-grid-2">
              <div class="ixp-field">
                <label>Nome do responsável</label>
                <input v-model="ctx.fixoAssinatura" list="da75-dl-dfd-assinatura-nome" placeholder="Digite o nome do responsável" />
              </div>
              <div class="ixp-field">
                <label>Função / Cargo</label>
                <input v-model="ctx.fixoAssinaturaCargo" list="da75-dl-dfd-assinatura-cargo" placeholder="Digite o cargo" />
              </div>
            </div>
          </div>
        </article>

        <article class="ixp-card">
          <h3>3. Termo de Referência</h3>
          <div class="ixp-body ixp-grid-1">
            <div class="ixp-field">
              <label>Endereço presencial para envio ou entrega de propostas</label>
              <textarea v-model="ctx.fixoEnderecoEntrega" rows="3" />
              <p class="ixp-hint">Texto pré-preenchido e editável. Ajuste município, UF, endereço e horário conforme o órgão.</p>
            </div>
            <div class="ixp-field">
              <label>E-mail para recebimento de propostas</label>
              <input v-model="ctx.fixoEmailPropostas" list="da75-dl-tr-email-propostas" placeholder="Ex: propostas@municipio.go.gov.br" />
            </div>
            <div class="ixp-grid-2">
              <div class="ixp-field">
                <label>Responsável pelo Termo de Referência — Nome</label>
                <input v-model="ctx.fixoTrResponsavelNome" list="da75-dl-tr-resp-nome" />
              </div>
              <div class="ixp-field">
                <label>Cargo / Função</label>
                <input v-model="ctx.fixoTrResponsavelCargo" list="da75-dl-tr-resp-cargo" />
              </div>
            </div>
          </div>
        </article>
      </div>

      <div class="ixp-drawer-foot">
        <button type="button" class="ixp-btn-primary" @click="$emit('apply')">Aplicar dados fixos</button>
      </div>

      <datalist id="da75-dl-solicitacao-destinatario-nome">
        <option v-for="v in (ctx.slotFieldOptions.solicitacao_destinatario_nome || [])" :key="`sdn-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-solicitacao-destinatario-cargo">
        <option v-for="v in (ctx.slotFieldOptions.solicitacao_destinatario_cargo || [])" :key="`sdc-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-solicitacao-responsavel-nome">
        <option v-for="v in (ctx.slotFieldOptions.solicitacao_responsavel_nome || [])" :key="`srn-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-solicitacao-responsavel-cargo">
        <option v-for="v in (ctx.slotFieldOptions.solicitacao_responsavel_cargo || [])" :key="`src-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-dfd-setor-requisitante">
        <option v-for="v in (ctx.slotFieldOptions.dfd_setor_requisitante || [])" :key="`dsr-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-dfd-responsavel-demanda">
        <option v-for="v in (ctx.slotFieldOptions.dfd_responsavel_demanda || [])" :key="`drd-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-dfd-email">
        <option v-for="v in (ctx.slotFieldOptions.dfd_email || [])" :key="`de-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-dfd-gestor-contratos">
        <option v-for="v in (ctx.slotFieldOptions.dfd_gestor_contratos || [])" :key="`dgc-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-dfd-fiscal-contratos">
        <option v-for="v in (ctx.slotFieldOptions.dfd_fiscal_contratos || [])" :key="`dfc-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-dfd-assinatura-nome">
        <option v-for="v in (ctx.slotFieldOptions.dfd_assinatura_nome || [])" :key="`dan-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-dfd-assinatura-cargo">
        <option v-for="v in (ctx.slotFieldOptions.dfd_assinatura_cargo || [])" :key="`dac-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-tr-email-propostas">
        <option v-for="v in (ctx.slotFieldOptions.tr_email_recebimento_propostas || [])" :key="`trem-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-tr-resp-nome">
        <option v-for="v in (ctx.slotFieldOptions.tr_termo_responsavel_nome || [])" :key="`trn-${v}`" :value="v" />
      </datalist>
      <datalist id="da75-dl-tr-resp-cargo">
        <option v-for="v in (ctx.slotFieldOptions.tr_termo_responsavel_cargo || [])" :key="`trc-${v}`" :value="v" />
      </datalist>
    </aside>
  </Teleport>
</template>

<script setup>
defineProps({
  open: { type: Boolean, default: false },
  /** Retorno de `useDispensaArt75IIDadosFixos` */
  ctx: { type: Object, required: true },
});

defineEmits(['close', 'apply']);
</script>

<style scoped>
.ixp-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.2);
  z-index: 40;
}
.ixp-drawer {
  position: fixed;
  right: 0;
  top: 0;
  height: 100%;
  width: 100%;
  max-width: 880px;
  transform: translateX(100%);
  transition: transform 0.25s ease;
  background: #fff;
  border-left: 1px solid #e2e8f0;
  z-index: 50;
  display: grid;
  grid-template-rows: auto 1fr auto;
}
.ixp-drawer.is-open {
  transform: translateX(0);
}
.ixp-drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  padding: 14px 16px;
}
.ixp-drawer-head small {
  font-size: 11px;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.08em;
}
.ixp-drawer-head h3 {
  margin: 3px 0 0;
  font-size: 16px;
  color: #0f172a;
}
.ixp-drawer-body {
  overflow: auto;
  padding: 16px;
  display: grid;
  gap: 12px;
}
.ixp-drawer-foot {
  border-top: 1px solid #e2e8f0;
  padding: 14px 16px;
}
.ixp-drawer-foot .ixp-btn-primary {
  width: 100%;
}
.ixp-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
  padding: 14px;
}
.ixp-card h3 {
  margin: 0;
  font-size: 14px;
  color: #1e293b;
}
.ixp-subsection-title {
  margin: 6px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}
.ixp-body {
  margin-top: 10px;
  display: grid;
  gap: 10px;
}
.ixp-grid-1 {
  display: grid;
  gap: 10px;
}
.ixp-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.ixp-grid-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.ixp-col-2 {
  grid-column: span 2;
}
.ixp-field {
  display: grid;
  gap: 4px;
}
.ixp-field label {
  font-size: 12px;
  color: #475569;
  font-weight: 500;
}
.ixp-field input,
.ixp-field textarea,
.ixp-field select {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 10px 11px;
  font-size: 14px;
  color: #1e293b;
  outline: none;
}
.ixp-field input:focus,
.ixp-field textarea:focus,
.ixp-field select:focus {
  border-color: #38bdf8;
}
.ixp-inline-actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  flex-wrap: wrap;
}
.ixp-orgao-profile-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  width: 100%;
}
.ixp-orgao-profile-actions > button {
  width: 100%;
  padding: 10px 12px;
  font-size: 13px;
  border-radius: 10px;
}
.ixp-orgao-profile-actions > button:disabled {
  opacity: 0.6;
}
.ixp-btn-secondary {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
  border-radius: 12px;
  padding: 9px 12px;
  font-size: 13px;
  font-weight: 600;
}
.ixp-btn-xs {
  padding: 6px 10px;
  font-size: 12px;
  border-radius: 10px;
}
/* Depois de .ixp-btn-secondary: mesma ordem que inexigibilidade (evita sumir azul/vermelho). */
.ixp-btn-secondary.ixp-orgao-btn-save {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.ixp-btn-secondary.ixp-orgao-btn-delete {
  background: #dc2626;
  border-color: #dc2626;
  color: #fff;
}
.ixp-btn-primary {
  border: 0;
  background: #2563eb;
  color: #fff;
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 700;
}
.ixp-hint {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}
@media (max-width: 900px) {
  .ixp-grid-2,
  .ixp-grid-3 {
    grid-template-columns: 1fr;
  }
  .ixp-col-2 {
    grid-column: auto;
  }
}

.dm-dark .ixp-drawer,
.dm-dark-theme .ixp-drawer {
  background: #0f172a;
  border-color: #334155;
}
.dm-dark .ixp-drawer-head,
.dm-dark .ixp-drawer-foot,
.dm-dark-theme .ixp-drawer-head,
.dm-dark-theme .ixp-drawer-foot {
  border-color: #334155;
}
.dm-dark .ixp-drawer-head small,
.dm-dark-theme .ixp-drawer-head small {
  color: #94a3b8;
}
.dm-dark .ixp-drawer-head h3,
.dm-dark-theme .ixp-drawer-head h3 {
  color: #e2e8f0;
}
.dm-dark .ixp-card,
.dm-dark-theme .ixp-card {
  background: #0f172a;
  border-color: #334155;
}
.dm-dark .ixp-card h3,
.dm-dark-theme .ixp-card h3 {
  color: #e2e8f0;
}
.dm-dark .ixp-subsection-title,
.dm-dark-theme .ixp-subsection-title {
  color: #cbd5e1;
}
.dm-dark .ixp-field label,
.dm-dark-theme .ixp-field label {
  color: #94a3b8;
}
.dm-dark .ixp-field input,
.dm-dark .ixp-field textarea,
.dm-dark .ixp-field select,
.dm-dark .ixp-btn-secondary,
.dm-dark-theme .ixp-field input,
.dm-dark-theme .ixp-field textarea,
.dm-dark-theme .ixp-field select,
.dm-dark-theme .ixp-btn-secondary {
  background: #0b1222;
  border-color: #334155;
  color: #e2e8f0;
}
.dm-dark .ixp-field input::placeholder,
.dm-dark .ixp-field textarea::placeholder,
.dm-dark-theme .ixp-field input::placeholder,
.dm-dark-theme .ixp-field textarea::placeholder {
  color: #64748b;
}
.dm-dark .ixp-field input:focus,
.dm-dark .ixp-field textarea:focus,
.dm-dark .ixp-field select:focus,
.dm-dark-theme .ixp-field input:focus,
.dm-dark-theme .ixp-field textarea:focus,
.dm-dark-theme .ixp-field select:focus {
  border-color: #0ea5e9;
}
.dm-dark .ixp-btn-secondary,
.dm-dark-theme .ixp-btn-secondary {
  color: #cbd5e1;
}
.dm-dark .ixp-btn-secondary.ixp-orgao-btn-save,
.dm-dark-theme .ixp-btn-secondary.ixp-orgao-btn-save {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.dm-dark .ixp-btn-secondary.ixp-orgao-btn-delete,
.dm-dark-theme .ixp-btn-secondary.ixp-orgao-btn-delete {
  background: #dc2626;
  border-color: #dc2626;
  color: #fff;
}
.dm-dark .ixp-overlay,
.dm-dark-theme .ixp-overlay {
  background: rgba(2, 6, 23, 0.72);
}
.dm-dark .ixp-hint,
.dm-dark-theme .ixp-hint {
  color: #94a3b8;
}
</style>
