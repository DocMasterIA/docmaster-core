<template>
  <div class="da75-page">
    <div class="da75-page__inner">
      <div class="da75-grid-main da75-mt">
        <section class="ixp-main">
          <div class="ixp-main-head">
            <div class="ixp-main-title">
              <div class="ixp-bot">IA</div>
              <div>
                <small>Módulo ativo</small>
                <h2>Inexigibilidade</h2>
                <p>{{ pageSubtitle }}</p>
              </div>
            </div>
            <button type="button" class="ixp-btn-secondary" @click="drawerOpen = true">Dados fixos</button>
          </div>

          <div class="ixp-main-body">
            <section class="da75-block da75-block--muted">
              <h3>Dados básicos</h3>
              <div class="da75-block__body">
                <div
                  class="da75-row"
                  :class="
                    isFornecedorExclusivoRoute || isInexigibilidadeManutencaoRoute
                      ? 'da75-row--basic-4'
                      : 'da75-row--basic'
                  "
                >
                  <div class="da75-field">
                    <label class="da75-label da75-label--compact">Cabeçalho do documento</label>
                    <select v-model="cabecalhoDocumento" class="da75-select da75-select--sm">
                      <option value="">Selecione</option>
                      <option v-for="op in cabecalhoOptions" :key="op.id" :value="op.name">{{ op.name }}</option>
                    </select>
                  </div>
                  <div class="da75-field">
                    <label class="da75-label da75-label--compact">{{ LABEL_ORGAO_UNIDADE }}</label>
                    <input
                      :value="orgao"
                      class="da75-input da75-input--sm"
                      list="dl-orgao"
                      :placeholder="PLACEHOLDER_ORGAO_GERAL"
                      @input="onOrgaoInput($event)"
                    />
                  </div>
                  <label class="da75-check da75-check--inline">
                    <input v-model="processoAtivo" type="checkbox" />
                    Processo (opcional)
                  </label>
                  <div v-if="isFornecedorExclusivoRoute" class="da75-field">
                    <label class="da75-label da75-label--compact">{{ LABEL_ORGAO_UNIDADE_RESP_EQUIP }}</label>
                    <input
                      :value="orgaoResponsavelEquipamento"
                      class="da75-input da75-input--sm"
                      :placeholder="PLACEHOLDER_ORGAO_UNIDADE_RESP_EQUIP"
                      @input="onOrgaoResponsavelEquipamentoInput($event)"
                    />
                  </div>
                  <div v-else-if="isInexigibilidadeManutencaoRoute" class="da75-field">
                    <label class="da75-label da75-label--compact">{{ LABEL_ORGAO_UNIDADE_VEICULO }}</label>
                    <input
                      :value="orgaoUnidadeVeiculo"
                      class="da75-input da75-input--sm"
                      :placeholder="PLACEHOLDER_ORGAO_UNIDADE_VEICULO"
                      @input="onOrgaoUnidadeVeiculoInput($event)"
                    />
                  </div>
                </div>
                <div v-if="processoAtivo" class="da75-max-xs da75-mt">
                  <label class="da75-label">Número do processo (opcional)</label>
                  <input
                    v-model="processo"
                    class="da75-input"
                    list="dl-processo-numero"
                    placeholder="Ex: 123/2026"
                  />
                </div>
              </div>
            </section>

            <article v-if="isFornecedorExclusivoRoute" class="ixp-card">
              <h3>Objeto específico</h3>
              <div class="ixp-body">
                <div class="ixp-field">
                  <label>Selecione o objeto específico da contratação</label>
                  <select v-model="objetoEspecifico" class="da75-select">
                    <option value="">Selecione</option>
                    <option v-for="op in objetoEspecificoOptions" :key="op" :value="op">{{ op }}</option>
                  </select>
                </div>
                <div v-if="objetoEspecifico === 'Outro'" class="ixp-field">
                  <label>Descreva o objeto específico da contratação</label>
                  <input v-model="outroObjetoEspecifico" placeholder="Ex: Fornecimento de kit de manutenção original" />
                </div>
              </div>
            </article>

            <article v-if="isFornecedorExclusivoRoute" class="ixp-card">
              <h3>Dados do equipamento</h3>
              <div class="ixp-body ixp-grid-3">
                <div class="ixp-field"><label>Equipamento</label><input :value="equipamento" placeholder="Ex: Aparelho de raio-X" @input="equipamento = primeiraMaiuscula(String(($event.target).value || ''))" /></div>
                <div class="ixp-field"><label>Marca</label><input :value="marca" placeholder="Ex: Siemens" @input="marca = primeiraMaiuscula(String(($event.target).value || ''))" /></div>
                <div class="ixp-field"><label>Modelo</label><input :value="modelo" placeholder="Ex: Multix Select DR" @input="modelo = primeiraMaiuscula(String(($event.target).value || ''))" /></div>
              </div>
            </article>

            <article v-if="isManutencaoVeiculosRoute" class="ixp-card">
              <h3>Dados do veículo</h3>
              <div class="ixp-body ixp-grid-3">
                <div class="ixp-field"><label>Marca</label><input :value="marca" placeholder="Ex: Chevrolet" @input="marca = primeiraMaiuscula(String(($event.target).value || ''))" /></div>
                <div class="ixp-field"><label>Modelo</label><input :value="modelo" placeholder="Ex: S10" @input="modelo = primeiraMaiuscula(String(($event.target).value || ''))" /></div>
                <div class="ixp-field"><label>Placa</label><input :value="placa" placeholder="Ex: ABC-1234" @input="placa = String(($event.target).value || '').toUpperCase()" /></div>
              </div>
            </article>

            <article v-if="isDispensaManutencaoRoute" class="ixp-card">
              <h3>Tipo de manutenção</h3>
              <div class="ixp-body">
                <div class="ixp-grid-2">
                  <button type="button" :class="['ixp-choice', tipoManutencao === 'Corretiva' && 'is-active']" @click="setCorretiva">
                    <strong>Manutenção corretiva</strong>
                    <span>Reparo por falha, defeito ou necessidade imediata.</span>
                  </button>
                  <button type="button" :class="['ixp-choice', tipoManutencao === 'Preventiva' && 'is-active']" @click="tipoManutencao = 'Preventiva'">
                    <strong>Manutenção preventiva</strong>
                    <span>Revisão programada conforme quilometragem ou plano.</span>
                  </button>
                </div>
                <div v-if="tipoManutencao === 'Preventiva'" class="ixp-field ixp-mt">
                  <label>Quilometragem / revisão preventiva</label>
                  <input v-model="revisaoKm" placeholder="Ex: Revisão de 10.000 km" />
                </div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Fornecedor exclusivo</h3>
              <div class="ixp-body ixp-grid-2">
                <div class="ixp-field">
                  <label>Razão social / nome do fornecedor</label>
                  <input
                    :value="fornecedor"
                    list="dl-fornecedor"
                    placeholder="Digite a razão social"
                    @input="fornecedor = tituloNomePt(String(($event.target).value || ''))"
                  />
                </div>
                <div class="ixp-field"><label>CNPJ</label><input :value="cnpj" type="text" inputmode="numeric" maxlength="18" autocomplete="off" placeholder="00.000.000/0001-00" @keydown="onCnpjInputKeydown" @input="cnpj = formatCnpjBr(String(($event.target).value || ''))" /></div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Dotação orçamentária</h3>
              <div class="ixp-body">
                <label class="ixp-check">
                  <input v-model="dotacaoAtiva" type="checkbox" />
                  Informar dotação orçamentária (opcional)
                </label>
                <div v-if="dotacaoAtiva" class="ixp-field">
                  <label>Dotação orçamentária</label>
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
                    <div class="ixp-field"><label>Descrição</label><input :value="item.descricao" @input="atualizarItem(index, 'descricao', $event)" /></div>
                    <div class="ixp-field"><label>Quantidade</label><input :value="item.quantidade" @input="atualizarItem(index, 'quantidade', $event)" /></div>
                    <div class="ixp-field"><label>Unidade de medida</label><input :value="item.unidade" @input="atualizarItem(index, 'unidade', $event)" /></div>
                    <div class="ixp-field"><label>Valor unitário</label><input :value="item.valorUnitario" @input="atualizarItem(index, 'valorUnitario', $event)" /></div>
                    <div class="ixp-field"><label>Valor total</label><input :value="item.valorTotal" @input="atualizarItem(index, 'valorTotal', $event)" /></div>
                    <button type="button" class="ixp-btn-secondary" @click="adicionarItem">+</button>
                  </div>
                </div>
              </div>
            </article>

            <div class="ixp-field ixp-half">
              <label>Valor total do processo</label>
              <input :value="valorGlobal" placeholder="R$ 0,00" @input="valorGlobal = formatMoedaBRLInput(String($event.target.value || ''))" />
            </div>

            <article class="ixp-card">
              <h3>Fiscalização</h3>
              <div class="ixp-body">
                <div class="ixp-field">
                  <label>Nome do fiscal de contratos</label>
                  <input
                    :value="fiscal"
                    list="dl-fiscal"
                    @input="fiscal = tituloNomePt(String(($event.target).value || ''))"
                  />
                </div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Responsável pelo Termo de Referência</h3>
              <div class="ixp-body ixp-grid-2">
                <div class="ixp-field">
                  <label>Nome do responsável</label>
                  <input
                    :value="responsavel"
                    list="dl-tr-nome-assinante"
                    @input="responsavel = tituloNomePt(String(($event.target).value || ''))"
                  />
                </div>
                <div class="ixp-field">
                  <label>Cargo / função</label>
                  <input
                    :value="responsavelCargo"
                    list="dl-tr-cargo-assinante"
                    @input="responsavelCargo = tituloNomePt(String(($event.target).value || ''))"
                  />
                </div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Data</h3>
              <div class="ixp-body ixp-grid-2">
                <div class="ixp-field">
                  <label>Modo da data</label>
                  <select v-model="modoData" class="da75-select">
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

            <article v-if="isDispensaNormalRoute" class="ixp-card">
              <h3>Gerar cláusulas (IA)</h3>
              <div class="ixp-body">
                <p class="ixp-hint">
                  Gere e revise as cláusulas antes do documento final. Esse fluxo vale apenas para dispensa normal.
                </p>
                <div class="ixp-field"><label>O que será contratado?</label><textarea v-model="clausulaContratado" rows="3" placeholder="Ex: Aquisição de material de expediente" /></div>
                <div class="ixp-field"><label>Qual setor/secretaria será atendido?</label><input v-model="clausulaSetor" list="dl-clausula-setor" placeholder="Ex: Secretaria de Administração" /></div>
                <div class="ixp-field"><label>Características mínimas obrigatórias (opcional)</label><textarea v-model="clausulaCaracteristicas" rows="3" placeholder="Ex: Itens de primeira linha, entrega fracionada e suporte técnico" /></div>
                <button class="ixp-btn-secondary" type="button" :disabled="isGeneratingClauses" @click="onGenerateClauses">
                  Gerar objeto e justificativa
                </button>
                <DocGenIaLoaderBlock
                  v-if="isGeneratingClauses"
                  compact
                  message="Gerando objeto e justificativa…"
                />
                <div class="ixp-grid-1">
                  <div class="ixp-field">
                    <label>Objeto gerado pela IA</label>
                    <textarea v-model="clausulaObjeto" rows="3" placeholder="Objeto do TR (gerado por IA ou manual)" />
                  </div>
                  <div class="ixp-field">
                    <label>Justificativa da contratação</label>
                    <textarea v-model="clausulaJustificativa" rows="4" placeholder="Justificativa da necessidade" />
                  </div>
                </div>
              </div>
            </article>

            <div class="da75-space-y">
              <button
                type="button"
                class="da75-btn da75-btn--primary"
                :disabled="isSubmitting || !podeGerarDocumentos"
                @click="onSubmit"
              >
                Gerar documento com IA
              </button>
              <DocGenIaLoaderBlock v-if="isSubmitting" message="Gerando documentos…" />
              <p v-if="generateError" class="da75-helper">{{ generateError }}</p>
              <p v-if="documentReady && successMessage" class="da75-helper">{{ successMessage }}</p>
              <div v-if="documentReady" class="da75-inline-actions">
                <a v-if="documentTrUrl" :href="documentTrUrl" :download="documentTrFilename" class="da75-btn">Download TR</a>
                <a v-if="documentDfdUrl" :href="documentDfdUrl" :download="documentDfdFilename" class="da75-btn">Download DFD</a>
                <a v-if="documentOficioUrl" :href="documentOficioUrl" :download="documentOficioFilename" class="da75-btn">Download Ofício</a>
                <a v-if="documentZipUrl" :href="documentZipUrl" :download="documentZipFilename" class="da75-btn">Download ZIP</a>
              </div>
            </div>
          </div>
        </section>

        <aside class="da75-resumo">
          <div class="da75-resumo__head">
            <div>
              <div class="da75-resumo__kicker">Resumo em tempo real</div>
              <h3 class="da75-resumo__panel-title">Painel do documento</h3>
            </div>
            <div class="da75-resumo__pct">{{ progresso }}%</div>
          </div>
          <div class="da75-progress">
            <div class="da75-progress__bar" :style="{ width: `${progresso}%` }" />
          </div>
          <div class="da75-resumo__meta">
            {{ completos }} de {{ secoes.length }} blocos preenchidos
          </div>
          <div class="da75-resumo__secoes">
            <div v-for="secao in secoes" :key="secao.titulo" class="da75-secao">
              <div class="da75-secao__title">
                <span>{{ secao.titulo }}</span>
                <span :class="secao.completo ? 'da75-ok' : 'da75-warn'">{{ secao.completo ? '✓' : '!' }}</span>
              </div>
              <div class="da75-space-y da75-mt-sm">
                <div
                  v-for="[rotulo, valor, preenchido] in secao.linhas"
                  :key="rotulo"
                  class="da75-linha"
                  :class="preenchido ? 'da75-linha--ok' : 'da75-linha--no'"
                >
                  <span>{{ rotulo }}</span>
                  <span>{{ valor }}</span>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <div v-if="drawerOpen" class="ixp-overlay" @click="drawerOpen = false"></div>
    <aside :class="['ixp-drawer', drawerOpen && 'is-open']">
      <div class="ixp-drawer-head">
        <div><small>Configuração oculta</small><h3>Dados fixos</h3></div>
        <button type="button" class="ixp-btn-secondary" @click="drawerOpen = false">X</button>
      </div>
      <div class="ixp-drawer-body">
        <article class="ixp-card">
          <h3>Cadastros de Órgãos</h3>
          <div class="ixp-body">
            <div class="ixp-field">
              <label>Órgão cadastrado</label>
              <select
                :value="selectedOrgaoProfileId"
                class="da75-select da75-select--sm"
                @change="loadOrgaoProfile(($event.target).value)"
              >
                <option value="">Selecione um cadastro salvo</option>
                <option v-for="p in orgaoProfiles" :key="`org-${p.id}`" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div class="ixp-field">
              <label>Nome do cadastro</label>
              <input
                :value="orgaoProfileName"
                class="da75-input da75-input--sm"
                placeholder="Ex: Fundo Municipal de Saúde"
                @input="orgaoProfileName = tituloNomePt(String(($event.target).value || ''))"
              />
            </div>
            <div class="ixp-inline-actions ixp-orgao-profile-actions">
              <button type="button" class="ixp-btn-secondary ixp-btn-xs ixp-orgao-btn-new" @click="newOrgaoProfile">Novo cadastro</button>
              <button type="button" class="ixp-btn-secondary ixp-btn-xs ixp-orgao-btn-save" @click="saveOrgaoProfile">Salvar cadastro</button>
              <button type="button" class="ixp-btn-secondary ixp-btn-xs ixp-orgao-btn-delete" :disabled="!selectedOrgaoProfileId" @click="deleteOrgaoProfile">Excluir cadastro</button>
            </div>
          </div>
        </article>

        <article class="ixp-card">
          <h3>1. Solicitação / ofício</h3>
          <div class="ixp-body">
            <div class="ixp-grid-3">
              <div class="ixp-field">
                <label>Tratamento</label>
                <select v-model="fixoTratNome" class="da75-select da75-select--sm">
                  <option value="">Selecione</option>
                  <option v-for="op in tratamentoNome" :key="op" :value="op">{{ op }}</option>
                </select>
              </div>
              <div class="ixp-field ixp-col-2">
                <label>1.1 A quem é direcionada a solicitação — nome</label>
                <input
                  :value="fixoNome"
                  class="da75-input da75-input--sm"
                  list="dl-solicitacao-destinatario-nome"
                  placeholder="Digite o nome"
                  @input="fixoNome = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
            </div>
            <div class="ixp-grid-3">
              <div class="ixp-field">
                <label>Tratamento</label>
                <select v-model="fixoTratCargo" class="da75-select da75-select--sm">
                  <option value="">Selecione</option>
                  <option v-for="op in tratamentoCargo" :key="op" :value="op">{{ op }}</option>
                </select>
              </div>
              <div class="ixp-field ixp-col-2">
                <label>1.2 A quem é direcionada a solicitação — função / cargo</label>
                <input
                  :value="fixoCargo"
                  class="da75-input da75-input--sm"
                  list="dl-solicitacao-destinatario-cargo"
                  placeholder="Digite a função ou cargo"
                  @input="fixoCargo = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
            </div>
            <h4 class="ixp-subsection-title">1.3 Responsável pela solicitação</h4>
            <div class="ixp-grid-2">
              <div class="ixp-field">
                <label>Nome do responsável</label>
                <input
                  :value="fixoResponsavel"
                  class="da75-input da75-input--sm"
                  list="dl-solicitacao-responsavel-nome"
                  placeholder="Digite o nome do responsável"
                  @input="fixoResponsavel = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
              <div class="ixp-field">
                <label>Função / cargo</label>
                <input
                  :value="fixoResponsavelCargo"
                  class="da75-input da75-input--sm"
                  list="dl-solicitacao-responsavel-cargo"
                  placeholder="Digite o cargo"
                  @input="fixoResponsavelCargo = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
            </div>
          </div>
        </article>
        <article class="ixp-card">
          <h3>2. DFD — documento de formalização da demanda</h3>
          <div class="ixp-body ixp-grid-1">
            <div class="ixp-field">
              <label>2.1 Setor requisitante (Unidade / Setor / Departamento)</label>
              <input
                :value="fixoSetor"
                class="da75-input da75-input--sm"
                list="dl-dfd-setor-requisitante"
                @input="fixoSetor = tituloNomePt(String(($event.target).value || ''))"
              />
            </div>
            <div class="ixp-field">
              <label>2.2 Responsável pela demanda</label>
              <input
                :value="fixoDemanda"
                class="da75-input da75-input--sm"
                list="dl-dfd-responsavel-demanda"
                @input="fixoDemanda = tituloNomePt(String(($event.target).value || ''))"
              />
            </div>
            <div class="ixp-field">
              <label>2.3 E-mail</label>
              <input v-model="fixoEmail" class="da75-input da75-input--sm" list="dl-dfd-email" />
            </div>
            <div class="ixp-field">
              <label>2.4 Nome do(a) gestor(a) de contratos</label>
              <input
                :value="fixoGestor"
                class="da75-input da75-input--sm"
                list="dl-dfd-gestor-contratos"
                @input="fixoGestor = tituloNomePt(String(($event.target).value || ''))"
              />
            </div>
            <div class="ixp-field">
              <label>2.5 Nome do(a) fiscal de contratos</label>
              <input
                :value="fixoFiscal"
                class="da75-input da75-input--sm"
                list="dl-dfd-fiscal-contratos"
                @input="fixoFiscal = tituloNomePt(String(($event.target).value || ''))"
              />
            </div>
            <h4 class="ixp-subsection-title">2.6 Responsável pela assinatura do DFD</h4>
            <div class="ixp-grid-2">
              <div class="ixp-field">
                <label>Nome do responsável</label>
                <input
                  :value="fixoAssinatura"
                  class="da75-input da75-input--sm"
                  list="dl-dfd-assinatura-nome"
                  placeholder="Digite o nome do responsável"
                  @input="fixoAssinatura = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
              <div class="ixp-field">
                <label>Função / cargo</label>
                <input
                  :value="fixoAssinaturaCargo"
                  class="da75-input da75-input--sm"
                  list="dl-dfd-assinatura-cargo"
                  placeholder="Digite o cargo"
                  @input="fixoAssinaturaCargo = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
            </div>
          </div>
        </article>
      </div>
      <div class="ixp-drawer-foot">
        <button type="button" class="ixp-btn-primary" @click="onApplyFixedData">Aplicar dados fixos</button>
      </div>
    </aside>

    <datalist id="dl-processo-numero"><option v-for="v in (slotFieldOptions.processo_numero || [])" :key="`p-${v}`" :value="v" /></datalist>
    <datalist id="dl-orgao"><option v-for="v in mergedOrgaoOptions" :key="`o-${v}`" :value="v" /></datalist>
    <datalist id="dl-fornecedor"><option v-for="v in (slotFieldOptions.fornecedor || [])" :key="`f-${v}`" :value="v" /></datalist>
    <datalist id="dl-fiscal"><option v-for="v in (slotFieldOptions.fiscal || [])" :key="`fi-${v}`" :value="v" /></datalist>
    <datalist id="dl-tr-nome-assinante"><option v-for="v in (slotFieldOptions.tr_nome_assinante || [])" :key="`na-${v}`" :value="v" /></datalist>
    <datalist id="dl-tr-cargo-assinante"><option v-for="v in (slotFieldOptions.tr_cargo_assinante || [])" :key="`ca-${v}`" :value="v" /></datalist>
    <datalist id="dl-clausula-setor"><option v-for="v in (slotFieldOptions.clausula_setor || [])" :key="`cs-${v}`" :value="v" /></datalist>
    <datalist id="dl-solicitacao-destinatario-nome"><option v-for="v in (slotFieldOptions.solicitacao_destinatario_nome || [])" :key="`sdn-${v}`" :value="v" /></datalist>
    <datalist id="dl-solicitacao-destinatario-cargo"><option v-for="v in (slotFieldOptions.solicitacao_destinatario_cargo || [])" :key="`sdc-${v}`" :value="v" /></datalist>
    <datalist id="dl-solicitacao-responsavel-nome"><option v-for="v in (slotFieldOptions.solicitacao_responsavel_nome || [])" :key="`srn-${v}`" :value="v" /></datalist>
    <datalist id="dl-solicitacao-responsavel-cargo"><option v-for="v in (slotFieldOptions.solicitacao_responsavel_cargo || [])" :key="`src-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-setor-requisitante"><option v-for="v in (slotFieldOptions.dfd_setor_requisitante || [])" :key="`dsr-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-responsavel-demanda"><option v-for="v in (slotFieldOptions.dfd_responsavel_demanda || [])" :key="`drd-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-email"><option v-for="v in (slotFieldOptions.dfd_email || [])" :key="`de-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-gestor-contratos"><option v-for="v in (slotFieldOptions.dfd_gestor_contratos || [])" :key="`dgc-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-fiscal-contratos"><option v-for="v in (slotFieldOptions.dfd_fiscal_contratos || [])" :key="`dfc-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-assinatura-nome"><option v-for="v in (slotFieldOptions.dfd_assinatura_nome || [])" :key="`dan-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-assinatura-cargo"><option v-for="v in (slotFieldOptions.dfd_assinatura_cargo || [])" :key="`dac-${v}`" :value="v" /></datalist>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { fetchCabecalhosPrefeitura } from '@/utils/fetchCabecalhosPrefeitura.js';
import { buildGerarTrEDfdUrl, getApiBase } from '@/utils/apiBase.js';
import { describeGerarTrEDfdNetworkFailure, fetchGerarTrEDfdWithRetry } from '@/utils/fetchGerarTrEDfd.js';
import { formatCnpjBr, onCnpjInputKeydown } from '@/utils/cnpjFormat.js';
import {
  capitalizeEachWordLeadingPt,
  capitalizeFirstSignificantLetter as primeiraMaiuscula,
  capitalizeNomeTituloPt as tituloNomePt,
  formatMoedaBRLInput,
  sanitizeQuantidadeInput,
} from '@/utils/itemValorCampos.js';

/** Rótulos com cada palavra iniciando em maiúscula (pt-BR), p.ex. «Do Veículo», «Pelo Equipamento». */
const LABEL_ORGAO_UNIDADE = capitalizeEachWordLeadingPt('Órgão / unidade');
const LABEL_ORGAO_UNIDADE_VEICULO = capitalizeEachWordLeadingPt('Órgão / unidade do veículo');
const LABEL_ORGAO_UNIDADE_RESP_EQUIP = capitalizeEachWordLeadingPt('Órgão / unidade responsável pelo equipamento');
const PLACEHOLDER_ORGAO_GERAL = capitalizeEachWordLeadingPt('Selecione ou digite o órgão');
const PLACEHOLDER_ORGAO_UNIDADE_VEICULO = capitalizeEachWordLeadingPt('Digite o órgão ou unidade do veículo');
const PLACEHOLDER_ORGAO_UNIDADE_RESP_EQUIP = capitalizeEachWordLeadingPt(
  'Digite o órgão ou unidade responsável pelo equipamento',
);
import '@/components/dispensa-art-75-ii/dispensaArt75ii.css';
import DocGenIaLoaderBlock from '@/components/DocGenIaLoaderBlock.vue';

const API_BASE = getApiBase();
const route = useRoute();
const dataOptions = ['Data automática', 'Datado e assinado digitalmente', 'Data manual'];
const GLOBAL_SLOT_FORM_PRESET_KEY = 'global_slots_preset_v1';
const ORGAO_PROFILES_STORAGE_KEY = 'orgao_profiles_v1';
const cabecalhoOptions = ref([]);
const tratamentoNome = ['Ao senhor', 'A senhora'];
const tratamentoCargo = ['Senhor', 'Senhora'];
const objetoEspecificoOptions = [
  'Aquisição de bens/produtos',
  'Fornecimento de peças',
  'Peças originais',
  'Peças de reposição',
  'Componentes e acessórios',
  'Insumos e materiais',
  'Prestação de serviços',
  'Assistência técnica autorizada',
  'Suporte técnico especializado',
  'Outro',
];
const emptyItem = { descricao: '', quantidade: '', unidade: '', valorUnitario: '', valorTotal: '' };
const placeholderDotacao = ['Ex:', 'Órgão: 02', 'Unidade: 05', 'Projeto/Atividade: 2.045', 'Elemento de despesa: 3.3.90.39.00', 'Fonte: 1.500'].join('\n');
const DISPENSA_RAPIDA_TO_LOGICAL = {
  DispensaRapidaArt75IObrasEngenharia: 'DispensaArt75IObrasEngenharia',
  DispensaRapidaArt75IManutencaoVeiculos: 'DispensaArt75IManutencaoVeiculos',
  DispensaRapidaArt75IICompras: 'DispensaArt75IICompras',
  DispensaRapidaArt75IIServicos: 'DispensaArt75IIServicos',
  DispensaRapidaArt75IIComprasServicosInclusos: 'DispensaArt75IIComprasServicosInclusos',
};
const SLOT_PACKAGE_BY_ROUTE = {
  DispensaArt75IManutencaoVeiculos: 'dispensa_75_i_manutencao_veiculos',
  DispensaArt75IObrasEngenharia: 'dispensa_75_i_obras_engenharia',
  DispensaArt75IICompras: 'dispensa_75_ii_compras',
  DispensaArt75IIServicos: 'dispensa_75_ii_servicos',
  DispensaArt75IIComprasServicosInclusos: 'dispensa_75_ii_compras_servicos_inclusos',
  InexigibilidadeArt74IFornecedorExclusivoPreview: 'inexigibilidade_74_i_fornecedor_exclusivo',
  InexigibilidadeArt74IManutencaoVeiculosPreview: 'inexigibilidade_74_i_manutencao_veiculos',
};
/** Rotas que compartilham este SFC; ao alternar entre elas o router reutiliza a instância — é preciso zerar o formulário. */
const INEX_ART74_I_SHARED_ROUTE_NAMES = new Set([
  'InexigibilidadeArt74IManutencaoVeiculosPreview',
  'InexigibilidadeArt74IFornecedorExclusivoPreview',
]);
const SOL_OFICIO_FUNDAMENTO_LEGAL_BY_ROUTE = {
  DispensaArt75I: 'Art. 75, Inciso I, da Lei no 14.133/2021',
  DispensaArt75IManutencaoVeiculos: 'Art. 75, Inciso I, da Lei no 14.133/2021',
  DispensaArt75IObrasEngenharia: 'Art. 75, Inciso I, da Lei no 14.133/2021',
  DispensaArt75II: 'Art. 75, Inciso II, da Lei no 14.133/2021',
  DispensaArt75IICompras: 'Art. 75, Inciso II, da Lei no 14.133/2021',
  DispensaArt75IIServicos: 'Art. 75, Inciso II, da Lei no 14.133/2021',
  DispensaArt75IIComprasServicosInclusos: 'Art. 75, Inciso II, da Lei no 14.133/2021',
  InexigibilidadeArt74I: 'Art. 74, Inciso I, da Lei no 14.133/2021',
  InexigibilidadeArt74IManutencaoVeiculosPreview: 'Art. 74, Inciso I, da Lei no 14.133/2021',
  InexigibilidadeArt74IManutencaoVeiculos: 'Art. 74, Inciso I, da Lei no 14.133/2021',
  InexigibilidadeArt74IFornecedorExclusivoPreview: 'Art. 74, Inciso I, da Lei no 14.133/2021',
  InexigibilidadeArt74IFornecedorExclusivo: 'Art. 74, Inciso I, da Lei no 14.133/2021',
};

function resolveSolOficioFundamentoLegal(routeName) {
  const name = String(routeName || '').trim();
  if (!name) return '';
  if (SOL_OFICIO_FUNDAMENTO_LEGAL_BY_ROUTE[name]) return SOL_OFICIO_FUNDAMENTO_LEGAL_BY_ROUTE[name];
  if (name.startsWith('InexigibilidadeArt74I')) return 'Art. 74, Inciso I, da Lei no 14.133/2021';
  if (name.startsWith('DispensaArt75I')) return 'Art. 75, Inciso I, da Lei no 14.133/2021';
  if (name.startsWith('DispensaArt75II')) return 'Art. 75, Inciso II, da Lei no 14.133/2021';
  return '';
}

const drawerOpen = ref(false);
const cabecalhoDocumento = ref('');
const processoAtivo = ref(false);
const processo = ref('');
const orgao = ref('');
const orgaoResponsavelEquipamento = ref('');
const orgaoUnidadeVeiculo = ref('');

function onOrgaoInput(ev) {
  orgao.value = tituloNomePt(String(ev?.target?.value ?? ''));
}
function onOrgaoResponsavelEquipamentoInput(ev) {
  orgaoResponsavelEquipamento.value = tituloNomePt(String(ev?.target?.value ?? ''));
}
function onOrgaoUnidadeVeiculoInput(ev) {
  orgaoUnidadeVeiculo.value = tituloNomePt(String(ev?.target?.value ?? ''));
}

const objetoEspecifico = ref('');
const outroObjetoEspecifico = ref('');
const equipamento = ref('');
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
const isSubmitting = ref(false);
const generateError = ref('');
const successMessage = ref('');
const documentReady = ref(false);
const documentTrUrl = ref('');
const documentDfdUrl = ref('');
const documentOficioUrl = ref('');
const documentZipUrl = ref('');
const documentTrFilename = ref('termo_referencia.docx');
const documentDfdFilename = ref('dfd.docx');
const documentOficioFilename = ref('oficio.docx');
const documentZipFilename = ref('tr_dfd_oficio.zip');
const isGeneratingClauses = ref(false);
const clausulaContratado = ref('');
const clausulaSetor = ref('');
const clausulaCaracteristicas = ref('');
const clausulaObjeto = ref('');
const clausulaJustificativa = ref('');

const logicalRouteName = computed(() => DISPENSA_RAPIDA_TO_LOGICAL[route.name] || route.name);
const slotPackageKey = computed(() => SLOT_PACKAGE_BY_ROUTE[logicalRouteName.value] || 'tr_dfd_generico');
const cabecalhoMergeTemplateId = computed(() => {
  const n = String(cabecalhoDocumento.value || '').trim();
  if (!n) return null;
  const hit = cabecalhoOptions.value.find((o) => o.name === n);
  return hit?.id ? String(hit.id) : null;
});
const isDispensaNormalRoute = computed(() => String(route.name || '').startsWith('DispensaArt75'));
const isFornecedorExclusivoRoute = computed(() =>
  logicalRouteName.value === 'InexigibilidadeArt74IFornecedorExclusivoPreview'
  || logicalRouteName.value === 'InexigibilidadeArt74IFornecedorExclusivo',
);
const isDispensaManutencaoRoute = computed(() =>
  logicalRouteName.value === 'DispensaArt75IManutencaoVeiculos'
  || logicalRouteName.value === 'InexigibilidadeArt74IManutencaoVeiculosPreview'
  || logicalRouteName.value === 'InexigibilidadeArt74IManutencaoVeiculos',
);
const isInexigibilidadeManutencaoRoute = computed(() =>
  logicalRouteName.value === 'InexigibilidadeArt74IManutencaoVeiculosPreview'
  || logicalRouteName.value === 'InexigibilidadeArt74IManutencaoVeiculos',
);
/** Card marca/modelo/placa para rotas de manutenção de veículos (dispensa e inexigibilidade). */
const isManutencaoVeiculosRoute = computed(() =>
  logicalRouteName.value === 'DispensaArt75IManutencaoVeiculos'
  || logicalRouteName.value === 'InexigibilidadeArt74IManutencaoVeiculosPreview'
  || logicalRouteName.value === 'InexigibilidadeArt74IManutencaoVeiculos',
);
/** Subtítulo da cabeceira conforme a rota (manutenção de veículos vs. fornecedor exclusivo geral). */
const pageSubtitle = computed(() => {
  if (isInexigibilidadeManutencaoRoute.value) {
    return 'Fornecedor exclusivo — manutenção de veículos (Art. 74, I)';
  }
  if (isFornecedorExclusivoRoute.value) {
    return 'Fornecedor exclusivo geral — bens, serviços e soluções (Art. 74, I)';
  }
  return 'Documentos de inexigibilidade ou dispensa';
});
const slotFieldOptions = reactive({});
const orgaoProfiles = ref([]);
const selectedOrgaoProfileId = ref('');
const orgaoProfileName = ref('');
const orgaoOptionsFromProfiles = computed(() => {
  const values = orgaoProfiles.value
    .map((p) => String(p?.name || '').trim())
    .filter(Boolean);
  return [...new Set(values)];
});
const mergedOrgaoOptions = computed(() => orgaoOptionsFromProfiles.value);
const CATALOG_KEYS = [
  'cabecalho_documento',
  'orgao',
  'fornecedor',
  'fiscal',
  'tr_nome_assinante',
  'tr_cargo_assinante',
  'solicitacao_destinatario_nome',
  'solicitacao_destinatario_cargo',
  'solicitacao_responsavel_nome',
  'solicitacao_responsavel_cargo',
  'dfd_setor_requisitante',
  'dfd_responsavel_demanda',
  'dfd_email',
  'dfd_gestor_contratos',
  'dfd_fiscal_contratos',
  'dfd_assinatura_nome',
  'dfd_assinatura_cargo',
  'clausula_contratado',
  'clausula_setor',
  'clausula_caracteristicas',
];

function collectGlobalFormStatePayload() {
  return {
    cabecalho_documento: cabecalhoDocumento.value,
    processo_ativo: false,
    processo_numero: '',
    orgao: orgao.value,
    solicitacao_destinatario_nome: fixoNome.value,
    solicitacao_destinatario_cargo: fixoCargo.value,
    solicitacao_responsavel_nome: fixoResponsavel.value,
    solicitacao_responsavel_cargo: fixoResponsavelCargo.value,
    dfd_setor_requisitante: fixoSetor.value,
    dfd_responsavel_demanda: fixoDemanda.value,
    dfd_email: fixoEmail.value,
    dfd_gestor_contratos: fixoGestor.value,
    dfd_fiscal_contratos: fixoFiscal.value,
    dfd_assinatura_nome: fixoAssinatura.value,
    dfd_assinatura_cargo: fixoAssinaturaCargo.value,
    tr_nome_assinante: responsavel.value,
    tr_cargo_assinante: responsavelCargo.value,
    clausula_contratado: clausulaContratado.value,
    clausula_setor: clausulaSetor.value,
    clausula_caracteristicas: clausulaCaracteristicas.value,
    clausula_objeto: clausulaObjeto.value,
    clausula_justificativa: clausulaJustificativa.value,
    ao_senhor_genero: fixoTratNome.value,
    senhor_senhora_genero: fixoTratCargo.value,
  };
}

function applyGlobalFormStatePayload(data) {
  if (!data || typeof data !== 'object') return;
  if ('cabecalho_documento' in data) cabecalhoDocumento.value = String(data.cabecalho_documento || '');
  if ('orgao' in data) {
    const t = String(data.orgao || '').trim();
    orgao.value = t ? tituloNomePt(t) : '';
  }
  if ('solicitacao_destinatario_nome' in data) {
    const v = String(data.solicitacao_destinatario_nome || '').trim();
    fixoNome.value = v ? tituloNomePt(v) : '';
  }
  if ('solicitacao_destinatario_cargo' in data) {
    const v = String(data.solicitacao_destinatario_cargo || '').trim();
    fixoCargo.value = v ? tituloNomePt(v) : '';
  }
  if ('solicitacao_responsavel_nome' in data) {
    const v = String(data.solicitacao_responsavel_nome || '').trim();
    fixoResponsavel.value = v ? tituloNomePt(v) : '';
  }
  if ('solicitacao_responsavel_cargo' in data) {
    const v = String(data.solicitacao_responsavel_cargo || '').trim();
    fixoResponsavelCargo.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_setor_requisitante' in data) {
    const v = String(data.dfd_setor_requisitante || '').trim();
    fixoSetor.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_responsavel_demanda' in data) {
    const v = String(data.dfd_responsavel_demanda || '').trim();
    fixoDemanda.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_email' in data) fixoEmail.value = String(data.dfd_email || '');
  if ('dfd_gestor_contratos' in data) {
    const v = String(data.dfd_gestor_contratos || '').trim();
    fixoGestor.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_fiscal_contratos' in data) {
    const v = String(data.dfd_fiscal_contratos || '').trim();
    fixoFiscal.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_assinatura_nome' in data) {
    const v = String(data.dfd_assinatura_nome || '').trim();
    fixoAssinatura.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_assinatura_cargo' in data) {
    const v = String(data.dfd_assinatura_cargo || '').trim();
    fixoAssinaturaCargo.value = v ? tituloNomePt(v) : '';
  }
  if ('tr_nome_assinante' in data) {
    const v = String(data.tr_nome_assinante || '').trim();
    responsavel.value = v ? tituloNomePt(v) : '';
  }
  if ('tr_cargo_assinante' in data) {
    const v = String(data.tr_cargo_assinante || '').trim();
    responsavelCargo.value = v ? tituloNomePt(v) : '';
  }
  if ('clausula_contratado' in data) clausulaContratado.value = String(data.clausula_contratado || '');
  if ('clausula_setor' in data) clausulaSetor.value = String(data.clausula_setor || '');
  if ('clausula_caracteristicas' in data) clausulaCaracteristicas.value = String(data.clausula_caracteristicas || '');
  if ('clausula_objeto' in data) clausulaObjeto.value = String(data.clausula_objeto || '');
  if ('clausula_justificativa' in data) clausulaJustificativa.value = String(data.clausula_justificativa || '');
  if ('ao_senhor_genero' in data) fixoTratNome.value = String(data.ao_senhor_genero || '');
  if ('senhor_senhora_genero' in data) fixoTratCargo.value = String(data.senhor_senhora_genero || '');
}

async function saveUserGlobalPreset() {
  try {
    await fetch(`${API_BASE}/api/slots/form-state/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        slot_package_key: GLOBAL_SLOT_FORM_PRESET_KEY,
        data: collectGlobalFormStatePayload(),
      }),
    });
    await persistSlotEntries(buildCatalogEntries());
  } catch (_e) {
    // silencioso
  }
}

function buildCatalogEntries() {
  const pairs = [
    ['cabecalho_documento', cabecalhoDocumento.value],
    ['orgao', orgao.value],
    ['fornecedor', fornecedor.value],
    ['fiscal', fiscal.value],
    ['tr_nome_assinante', responsavel.value],
    ['tr_cargo_assinante', responsavelCargo.value],
    ['solicitacao_destinatario_nome', fixoNome.value],
    ['solicitacao_destinatario_cargo', fixoCargo.value],
    ['solicitacao_responsavel_nome', fixoResponsavel.value],
    ['solicitacao_responsavel_cargo', fixoResponsavelCargo.value],
    ['dfd_setor_requisitante', fixoSetor.value],
    ['dfd_responsavel_demanda', fixoDemanda.value],
    ['dfd_email', fixoEmail.value],
    ['dfd_gestor_contratos', fixoGestor.value],
    ['dfd_fiscal_contratos', fixoFiscal.value],
    ['dfd_assinatura_nome', fixoAssinatura.value],
    ['dfd_assinatura_cargo', fixoAssinaturaCargo.value],
    ['clausula_contratado', clausulaContratado.value],
    ['clausula_setor', clausulaSetor.value],
    ['clausula_caracteristicas', clausulaCaracteristicas.value],
  ];
  return pairs
    .map(([field_key, value]) => ({ field_key, value: String(value || '').trim() }))
    .filter((e) => e.value);
}

async function persistSlotEntries(entries) {
  if (!Array.isArray(entries) || entries.length === 0) return;
  try {
    await fetch(`${API_BASE}/api/slots/catalog/upsert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ entries }),
    });
  } catch (_e) {
    // silencioso
  }
}

async function removeCatalogEntry(fieldKey, value) {
  const v = String(value || '').trim();
  if (!v) return;
  try {
    await fetch(`${API_BASE}/api/slots/catalog/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ field_key: fieldKey, value: v }),
    });
  } catch (_e) {
    // silencioso
  }
}

async function addFieldHistory(fieldKey, rawValue) {
  const value = String(rawValue || '').trim();
  if (!value) return;
  const current = Array.isArray(slotFieldOptions[fieldKey]) ? slotFieldOptions[fieldKey] : [];
  if (!current.includes(value)) slotFieldOptions[fieldKey] = [...current, value];
  await persistSlotEntries([{ field_key: fieldKey, value }]);
}

function canDeleteFieldHistory(fieldKey, rawValue) {
  const value = String(rawValue || '').trim();
  if (!value) return false;
  const current = Array.isArray(slotFieldOptions[fieldKey]) ? slotFieldOptions[fieldKey] : [];
  return current.includes(value);
}

async function removeFieldHistory(fieldKey, rawValue) {
  const value = String(rawValue || '').trim();
  if (!value) return;
  const current = Array.isArray(slotFieldOptions[fieldKey]) ? slotFieldOptions[fieldKey] : [];
  slotFieldOptions[fieldKey] = current.filter((v) => v !== value);
  await removeCatalogEntry(fieldKey, value);
}

function loadOrgaoProfiles() {
  try {
    const raw = localStorage.getItem(ORGAO_PROFILES_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    const list = Array.isArray(parsed) ? parsed : [];
    let dirty = false;
    orgaoProfiles.value = list.map((p) => {
      const trimmed = String(p?.name ?? '').trim();
      const n = trimmed ? tituloNomePt(trimmed) : '';
      if (n !== trimmed) dirty = true;
      return { ...p, name: n };
    });
    if (dirty) persistOrgaoProfiles();
  } catch {
    orgaoProfiles.value = [];
  }
}

function persistOrgaoProfiles() {
  try {
    localStorage.setItem(ORGAO_PROFILES_STORAGE_KEY, JSON.stringify(orgaoProfiles.value));
  } catch {
    // silencioso
  }
}

function loadOrgaoProfile(profileId) {
  const id = String(profileId || '');
  selectedOrgaoProfileId.value = id;
  const hit = orgaoProfiles.value.find((p) => String(p.id) === id);
  if (!hit) return;
  const trimmed = String(hit.name || '').trim();
  orgaoProfileName.value = trimmed ? tituloNomePt(trimmed) : '';
  applyGlobalFormStatePayload(hit.data || {});
}

function newOrgaoProfile() {
  selectedOrgaoProfileId.value = '';
  orgaoProfileName.value = '';
}

function saveOrgaoProfile() {
  const nameRaw = String(orgaoProfileName.value || '').trim();
  const name = nameRaw ? tituloNomePt(nameRaw) : '';
  if (!name) return false;
  orgaoProfileName.value = name;
  const data = collectGlobalFormStatePayload();
  data.orgao = name;
  const orgaoValue = String(data?.orgao || '').trim();
  const idx = orgaoProfiles.value.findIndex((p) => String(p.id) === String(selectedOrgaoProfileId.value || ''));
  if (idx >= 0) {
    orgaoProfiles.value[idx] = { ...orgaoProfiles.value[idx], name, data };
  } else {
    const id = String(Date.now());
    orgaoProfiles.value.push({ id, name, data });
    selectedOrgaoProfileId.value = id;
  }
  persistOrgaoProfiles();
  if (orgaoValue) {
    const current = Array.isArray(slotFieldOptions.orgao) ? slotFieldOptions.orgao : [];
    if (!current.includes(orgaoValue)) slotFieldOptions.orgao = [...current, orgaoValue];
    void persistSlotEntries([{ field_key: 'orgao', value: orgaoValue }]);
  }
  return true;
}

function deleteOrgaoProfile() {
  const id = String(selectedOrgaoProfileId.value || '');
  if (!id) return;
  orgaoProfiles.value = orgaoProfiles.value.filter((p) => String(p.id) !== id);
  persistOrgaoProfiles();
  selectedOrgaoProfileId.value = '';
  orgaoProfileName.value = '';
}

async function loadSlotCatalogSuggestions() {
  try {
    const url = `${API_BASE}/api/slots/catalog/batch?fields=${encodeURIComponent(CATALOG_KEYS.join(','))}&limit=25`;
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) return;
    const payload = await res.json().catch(() => ({}));
    const map = payload?.items || {};
    CATALOG_KEYS.forEach((key) => {
      const incoming = Array.isArray(map[key]) ? map[key] : [];
      slotFieldOptions[key] = [...new Set(incoming.map((x) => String(x || '').trim()).filter(Boolean))];
    });
  } catch (_e) {
    // silencioso
  }
}
async function loadCabecalhoOptions() {
  try {
    const opts = await fetchCabecalhosPrefeitura(API_BASE);
    cabecalhoOptions.value = opts;
    if (cabecalhoDocumento.value && !opts.some((o) => o.name === cabecalhoDocumento.value)) {
      cabecalhoDocumento.value = '';
    }
  } catch (_e) {
    // silencioso
  }
}

async function loadUserGlobalPreset() {
  try {
    const url = `${API_BASE}/api/slots/form-state?slot_package_key=${encodeURIComponent(GLOBAL_SLOT_FORM_PRESET_KEY)}`;
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) return;
    const payload = await res.json().catch(() => ({}));
    applyGlobalFormStatePayload(payload?.data || {});
  } catch (_e) {
    // silencioso
  }
}

function apenasNumeros(v) {
  return String(v || '').replace(/\D/g, '');
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
  let nextVal = raw;
  if (campo === 'descricao' || campo === 'unidade') {
    nextVal = primeiraMaiuscula(raw);
  } else if (campo === 'quantidade') {
    nextVal = sanitizeQuantidadeInput(raw);
  } else if (campo === 'valorUnitario' || campo === 'valorTotal') {
    nextVal = formatMoedaBRLInput(raw);
  }
  const next = [...itens.value];
  const item = { ...next[index], [campo]: nextVal };
  if (campo === 'quantidade' || campo === 'valorUnitario') {
    item.valorTotal = calcularTotalItem(item.quantidade, item.valorUnitario);
  }
  next[index] = item;
  itens.value = next;
  valorGlobal.value = calcularValorGlobal(next);
}
function revokeDocumentUrls() {
  [documentTrUrl, documentDfdUrl, documentOficioUrl, documentZipUrl].forEach((urlRef) => {
    if (urlRef.value) URL.revokeObjectURL(urlRef.value);
    urlRef.value = '';
  });
}
function toBlobUrl(base64, mimeType) {
  if (!base64) return '';
  const binary = atob(base64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i += 1) bytes[i] = binary.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mimeType }));
}
function toBrDate(iso) {
  const v = String(iso || '').trim();
  if (!v) return '';
  const m = v.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return v;
  return `${m[3]}/${m[2]}/${m[1]}`;
}
function gerarObjetoTexto(contratado, setor, caracteristicas, tipoManutencaoValue = '', revisaoKmValue = '') {
  const objeto = String(contratado || '').trim() || 'objeto não informado';
  const destino = String(setor || '').trim() ? `, visando atender as demandas de ${String(setor).trim()}` : '';
  const manutencao = String(tipoManutencaoValue || '').trim()
    ? `, no escopo de manutenção ${String(tipoManutencaoValue).trim().toLowerCase()}`
    : '';
  const revisao = String(revisaoKmValue || '').trim() ? ` (referência: ${String(revisaoKmValue).trim()})` : '';
  const detalhes = String(caracteristicas || '').trim() ? `, observadas as seguintes características mínimas: ${String(caracteristicas).trim()}` : '';
  return `${primeiraMaiuscula(objeto)}${destino}${manutencao}${revisao}${detalhes}.`;
}
function gerarJustificativaTexto(contratado, setor, caracteristicas, tipoManutencaoValue = '', revisaoKmValue = '') {
  const objeto = String(contratado || '').trim() || 'o objeto indicado';
  const destino = String(setor || '').trim() ? ` do(a) ${String(setor).trim()}` : ' da Administração Pública';
  const manutencao = String(tipoManutencaoValue || '').trim()
    ? ` Considera-se a manutenção ${String(tipoManutencaoValue).trim().toLowerCase()} como eixo da contratação.`
    : '';
  const revisao = String(revisaoKmValue || '').trim() ? ` Foi indicada a referência de revisão/quilometragem: ${String(revisaoKmValue).trim()}.` : '';
  const detalhes = String(caracteristicas || '').trim() ? ` A contratação deverá observar as características mínimas informadas: ${String(caracteristicas).trim()}.` : '';
  return `A presente contratação justifica-se pela necessidade de assegurar ${objeto} para atendimento das demandas${destino}, garantindo a continuidade, eficiência e adequada prestação dos serviços públicos.${manutencao}${revisao}${detalhes}`;
}

/** Texto para (DFD_OBJETO_REFERENCIA) — redacao em prosa; inexigibilidade Art. 74.I manutencao de veiculos. */
function buildInexig74ManutencaoDfdObjetoReferencia() {
  const m = String(marca.value || '').trim();
  const mod = String(modelo.value || '').trim();
  const pl = String(placa.value || '').trim();
  const tipo = String(tipoManutencao.value || '').trim();
  const rk = String(revisaoKm.value || '').trim();
  const orgVeic = String(orgaoUnidadeVeiculo.value || '').trim();
  const ident = [m && `marca ${m}`, mod && `modelo ${mod}`, pl && `placa ${pl}`].filter(Boolean).join(', ');
  if (!ident && !tipo) return '';

  const paragrafos = [];
  if (ident) {
    paragrafos.push(
      `A necessidade insere-se na manutenção do veículo identificado (${ident}), indispensável à disponibilidade e à segurança da frota utilizada na prestação de serviços públicos.`,
    );
  }
  if (tipo === 'Corretiva') {
    paragrafos.push(
      'Trata-se de intervenção corretiva, orientada ao reparo de falha, defeito ou situação que exija retorno imediato à condição de uso, evitando prolongada indisponibilidade do veículo.',
    );
  } else if (tipo === 'Preventiva') {
    let t = 'Trata-se de manutenção preventiva, alinhada à revisão programada por quilometragem ou plano de conservação, visando reduzir custos corretivos futuros e preservar o estado mecânico do veículo.';
    if (rk) t += ` A referência informada para a revisão é: ${rk}.`;
    paragrafos.push(t);
  } else if (tipo) {
    paragrafos.push(`O tipo de manutenção previsto é ${tipo}.`);
  }
  if (orgVeic) {
    paragrafos.push(`A unidade de lotação ou uso do veículo é ${orgVeic}.`);
  }
  return paragrafos.join('\n\n');
}

/** Texto para (DFD_JUSTIFICATIVA) — apenas inexigibilidade Art. 74.I manutencao de veiculos. */
function buildInexig74ManutencaoDfdJustificativa() {
  const m = String(marca.value || '').trim();
  const mod = String(modelo.value || '').trim();
  const pl = String(placa.value || '').trim();
  const orgVeic = String(orgaoUnidadeVeiculo.value || '').trim();
  const tipo = String(tipoManutencao.value || '').trim();
  const rk = String(revisaoKm.value || '').trim();
  const forn = String(fornecedor.value || '').trim();
  const cnpjStr = String(cnpj.value || '').trim();
  const identVeiculo = [m, mod, pl].filter(Boolean).join(' / ') || 'veículo indicado nos dados da demanda';
  let natureza = 'serviço de manutenção do veículo';
  if (tipo === 'Corretiva') {
    natureza = 'manutenção corretiva (reparo por falha, defeito ou necessidade imediata)';
  } else if (tipo === 'Preventiva') {
    natureza = 'manutenção preventiva (revisão programada conforme quilometragem ou plano de conservação)';
  } else if (tipo) {
    natureza = `manutenção ${tipo.toLowerCase()}`;
  }
  const nl = natureza.trim().toLowerCase();
  const artObjetoRef = nl.startsWith('manutenção') || nl.startsWith('manutencao') ? 'a' : 'o';
  const partes = [
    'A presente demanda insere-se no âmbito da contratação direta por inexigibilidade de licitação, nos termos do art. 74, inciso I, da Lei nº 14.133/2021, ante a necessidade de aquisição de peças, componentes ou serviços técnicos de natureza singular, com fornecedor exclusivo.',
    `O objeto da referência é ${artObjetoRef} ${natureza} do veículo (${identVeiculo}), com vistas a preservar a disponibilidade, a segurança e a economicidade da frota vinculada ao serviço público.`,
  ];
  if (orgVeic) {
    partes.push(`${LABEL_ORGAO_UNIDADE_VEICULO}: ${orgVeic}.`);
  }
  if (tipo === 'Preventiva' && rk) {
    partes.push(`Para a manutenção preventiva, foi indicada a referência de quilometragem ou revisão: ${rk}.`);
  }
  if (forn) {
    partes.push(
      `O fornecedor exclusivo indicado é ${forn}${cnpjStr ? ` (CNPJ ${cnpjStr})` : ''}, nos limites do artigo e da fundamentação do termo de referência.`,
    );
  }
  return partes.join('\n\n');
}

/**
 * Objeto do TR / Ofício na inexigibilidade art. 74, I — manutenção veicular (redação padrão).
 * Começa pela prestação de serviços (sem o preâmbulo «Contratação por inexigibilidade…»).
 */
function buildInexig74ManutencaoObjetoTrResumo() {
  const m = String(marca.value || '').trim();
  const mod = String(modelo.value || '').trim();
  const pl = String(placa.value || '').trim();
  const org = String(orgaoUnidadeVeiculo.value || orgao.value || '').trim();
  const partesVeic = [];
  if (m) partesVeic.push(`marca ${m}`);
  if (mod) partesVeic.push(`modelo ${mod}`);
  if (pl) partesVeic.push(`placa ${pl}`);
  const veiculo = partesVeic.length ? partesVeic.join(', ') : 'identificação do veículo a constar nos autos';
  const orgaoFrase = org ? `pertencente ao ${org}` : 'pertencente ao órgão ou unidade competente';
  return (
    'Prestação de serviços de manutenção veicular, com fornecimento de peças, componentes e acessórios, '
    + `destinado ao veículo, ${veiculo}, ${orgaoFrase}.`
  );
}

function objetoEspecificoContratacaoIx() {
  if (objetoEspecifico.value === 'Outro') return String(outroObjetoEspecifico.value || '').trim();
  return String(objetoEspecifico.value || '').trim();
}

function necessidadeConsisteComObjetoIx(obRaw) {
  const t = String(obRaw || '').trim();
  if (!t) return '';
  const low = t.toLowerCase();
  const lowAscii = low.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  if (/^(prestacao|aquisicao|fornecimento|manutencao|assistencia|implementacao)\b/.test(lowAscii)) {
    return `na ${low}`;
  }
  return `em assegurar ${low}`;
}

/** DFD_OBJETO_REFERENCIA — redacao em prosa; fornecedor exclusivo nesta tela compartilhada. */
function buildInexigFornecedorExclusivoDfdObjetoReferencia() {
  const eq = String(equipamento.value || '').trim();
  const m = String(marca.value || '').trim();
  const mod = String(modelo.value || '').trim();
  const ob = objetoEspecificoContratacaoIx();
  const org = String(orgaoResponsavelEquipamento.value || orgao.value || '').trim();
  const temEquip = !!(eq || m || mod);
  const fichaEquip = [eq, m && `marca ${m}`, mod && `modelo ${mod}`].filter(Boolean).join(', ');
  const obFrase = ob ? (ob.charAt(0).toUpperCase() + ob.slice(1)) : '';

  const paragrafos = [];
  if (obFrase && temEquip) {
    const nucleo = necessidadeConsisteComObjetoIx(ob);
    paragrafos.push(
      `A necessidade a ser atendida consiste ${nucleo} `
      + `no âmbito do equipamento identificado (${fichaEquip}), de forma a preservar a continuidade operacional, a rastreabilidade técnica e condições seguras de uso do bem, `
      + 'evitando paralisações ou degradação do serviço público que depende dessa infraestrutura.',
    );
  } else if (obFrase) {
    paragrafos.push(
      `A necessidade administrativa consiste em formalizar a contratação referente a ${obFrase.charAt(0).toLowerCase() + obFrase.slice(1)}, `
      + 'alinhada à hipótese de inexigibilidade por fornecedor exclusivo e à continuidade adequada das atividades do órgão.',
    );
  } else if (temEquip) {
    paragrafos.push(
      `A necessidade reporta-se ao equipamento (${fichaEquip}), cuja manutenção da condição de uso e do desempenho técnico é imprescindível à rotina administrativa ou assistencial, `
      + 'devendo a contratação observar a singularidade do fornecimento e os requisitos legais aplicáveis.',
    );
  }
  if (org && paragrafos.length) {
    paragrafos.push(
      `A demanda é apresentada em nome do órgão ou unidade ${org}, responsável pela guarda, operação ou manutenção do equipamento.`,
    );
  }
  return paragrafos.join('\n\n');
}

/** Justificativa para TR, DFD e oficio — fornecedor exclusivo nesta tela. */
function buildInexigFornecedorExclusivoJustificativaTrDfd() {
  const org = String(orgaoResponsavelEquipamento.value || orgao.value || '').trim();
  const ob = objetoEspecificoContratacaoIx();
  const partesEq = [String(equipamento.value || '').trim(), String(marca.value || '').trim(), String(modelo.value || '').trim()].filter(Boolean);
  const eqRef = partesEq.length ? partesEq.join(', ') : '';
  const forn = String(fornecedor.value || '').trim();
  const cnpjStr = String(cnpj.value || '').trim();
  const obTxt = ob ? ob.charAt(0).toLowerCase() + ob.slice(1) : '';

  const partes = [
    'A contratação direta enquadra-se na hipótese de inexigibilidade de licitação prevista no art. 74, inciso I, da Lei nº 14.133/2021, em razão da exclusividade do fornecimento ou da prestação técnica especializada e da imprescindibilidade de compatibilidade com solução já existente no âmbito do órgão.',
  ];
  if (obTxt && eqRef) {
    partes.push(
      `Do ponto de vista fático, a medida decorre da necessidade de ${obTxt} em relação ao equipamento ${eqRef}${org ? `, sob a responsabilidade da unidade ${org}` : ''}, `
      + 'de modo a restabelecer ou manter o padrão técnico exigido para o uso regular do bem.',
    );
  } else if (obTxt) {
    partes.push(
      `A medida atende à necessidade de ${obTxt}${org ? `, conforme demanda apresentada pelo órgão ou unidade ${org}` : ''}, nos limites da legislação aplicável.`,
    );
  } else if (eqRef) {
    partes.push(
      `A medida atende à necessidade vinculada ao equipamento ${eqRef}${org ? `, sob a responsabilidade da unidade ${org}` : ''}, preservando a continuidade operacional e a segurança de uso.`,
    );
  }
  if (forn) {
    partes.push(
      `Para fins de instrução do processo, o fornecedor exclusivo indicado é ${forn}${cnpjStr ? `, inscrito no CNPJ ${cnpjStr}` : ''}, observados os requisitos de idoneidade e a compatibilidade técnica exigidos para a espécie.`,
    );
  }
  partes.push(
    'Por conseguinte, a justificativa demonstra a singularidade do fornecimento e a adequação da contratação direta à continuidade do serviço público, com observância dos demais requisitos legais.',
  );
  return partes.join('\n\n');
}

/**
 * Objeto resumido — TR (com art. 74 na frase) vs ofício/assunto (termina em «fornecedor exclusivo.»).
 * @param {{ forOficio?: boolean }} [opts]
 */
function buildInexigFornecedorExclusivoObjetoTrResumo(opts = {}) {
  const forOficio = opts.forOficio === true;
  const ob = String(objetoEspecificoContratacaoIx() || '').trim();
  const eq = String(equipamento.value || '').trim();
  const m = String(marca.value || '').trim();
  const mod = String(modelo.value || '').trim();
  const nomeEq = [eq, m, mod].filter(Boolean).join(', ');
  const tail = forOficio
    ? 'na hipótese de fornecedor exclusivo.'
    : 'na hipótese de fornecedor exclusivo (art. 74, inciso I, da Lei nº 14.133/2021).';
  if (ob && nomeEq) {
    return `Contratação de ${ob.charAt(0).toLowerCase() + ob.slice(1)} vinculada ao equipamento ${nomeEq}, ${tail}`;
  }
  if (ob) {
    return `Contratação de ${ob.charAt(0).toLowerCase() + ob.slice(1)}, ${tail}`;
  }
  if (nomeEq) {
    return `Contratação vinculada ao equipamento ${nomeEq}, ${tail}`;
  }
  return '';
}

function buildSlotsOverride() {
  const o = {};
  const solDestNome = fixoNome.value.trim();
  const solDestCargo = fixoCargo.value.trim();
  const solRespNome = fixoResponsavel.value.trim();
  const solRespCargo = fixoResponsavelCargo.value.trim();
  if (solDestNome) o.sol_oficio_destinatario_nome = solDestNome;
  if (solDestCargo) o.sol_oficio_destinatario_cargo = solDestCargo;
  if (solRespNome) o.sol_oficio_responsavel_nome = solRespNome;
  if (solRespCargo) o.sol_oficio_responsavel_cargo = solRespCargo;

  const setor = (fixoSetor.value || orgao.value).trim();
  if (setor) {
    o.dfd_setor_requisitante = setor;
  }
  const demanda = fixoDemanda.value.trim();
  if (demanda) {
    o.nome_usuario = demanda;
    o.dfd_responsavel_demanda = demanda;
  }
  if (fixoEmail.value.trim()) o.dfd_email = fixoEmail.value.trim();
  if (fixoGestor.value.trim()) o.dfd_gestor_contratos = fixoGestor.value.trim();
  const fiscalNome = (fixoFiscal.value || fiscal.value).trim();
  if (fiscalNome) {
    o.fiscal = { nome: fiscalNome };
    o.dfd_fiscal_contratos = fiscalNome;
  }
  if (fixoAssinatura.value.trim()) o.dfd_assinatura_nome = fixoAssinatura.value.trim();
  if (fixoAssinaturaCargo.value.trim()) o.dfd_assinatura_cargo = fixoAssinaturaCargo.value.trim();

  const dataManualFmt = toBrDate(dataManual.value);
  let dataTermo = '';
  const modoDataNormalizado = String(modoData.value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
  if (modoDataNormalizado === 'data automatica') {
    const now = new Date();
    dataTermo = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
  } else if (modoDataNormalizado === 'data manual' && dataManualFmt) {
    dataTermo = dataManualFmt;
  }
  if (modoDataNormalizado === 'datado e assinado digitalmente') {
    dataTermo = 'datado e assinado digitalmente';
  }
  if (dataTermo) o.data_termo = dataTermo;

  if (responsavel.value.trim()) o.nome_assinante_termo = responsavel.value.trim();
  if (responsavelCargo.value.trim()) o.cargo_assinante_termo = responsavelCargo.value.trim();
  if (responsavelCargo.value.trim()) o.secretaria_usuario = responsavelCargo.value.trim();

  // Tipo/revisão só na dispensa art. 75, I — na inexigibilidade 74, I não usar isto como objeto do ofício/TR.
  const manutencaoFallbackParts =
    logicalRouteName.value === 'DispensaArt75IManutencaoVeiculos'
      ? [
          tipoManutencao.value ? `Tipo: ${tipoManutencao.value}` : '',
          revisaoKm.value ? `Revisão/KM: ${revisaoKm.value}` : '',
        ]
      : [];
  const veiculoFallbackParts =
    logicalRouteName.value === 'DispensaArt75IManutencaoVeiculos'
      ? [
          marca.value ? `Marca: ${marca.value}` : '',
          modelo.value ? `Modelo: ${modelo.value}` : '',
          placa.value ? `Placa: ${placa.value}` : '',
        ]
      : [];
  const objetoFallback = [...manutencaoFallbackParts, ...veiculoFallbackParts].filter(Boolean).join(' | ');
  const justificativaFallback = fornecedor.value.trim()
    ? `Fornecedor exclusivo: ${fornecedor.value.trim()} (CNPJ: ${cnpj.value.trim() || 'não informado'})`
    : '';
  const entregasFallback = valorGlobal.value.trim() ? `Valor total estimado: ${valorGlobal.value.trim()}` : '';
  const resultadosFallback = dotacaoAtiva.value && dotacao.value.trim() ? `Dotação orçamentária: ${dotacao.value.trim()}` : '';
  const dotacaoTexto = dotacaoAtiva.value && dotacao.value.trim() ? dotacao.value.trim() : '';
  /*
   * TR + DFD + Solicitacao/Oficio (rag_service): estes campos entram em slots_override e, apos
   * fill_tr_slots_with_llm, _merge_slots() da prioridade ao override sobre a IA (tr_slots_llm.py).
   * tr_template / dfd_template / oficio_template substituem placeholders a partir dos mesmos slots.
   */
  const objetoResumoInexig74M = isInexigibilidadeManutencaoRoute.value ? buildInexig74ManutencaoObjetoTrResumo().trim() : '';
  const objetoFinal = clausulaObjeto.value.trim() || objetoResumoInexig74M || objetoFallback;
  o.objeto = objetoFinal;
  const justificativaFinal = (clausulaJustificativa.value.trim() || justificativaFallback) || '';
  if (justificativaFinal) o.justificativa = justificativaFinal;
  if (entregasFallback) o.objeto_entregas = entregasFallback;
  if (resultadosFallback) o.objeto_resultados = resultadosFallback;
  if (dotacaoTexto) o.dotacao = dotacaoTexto;
  if (objetoFinal.trim()) o.sol_oficio_objeto = objetoFinal.trim();
  if (justificativaFinal.trim()) o.sol_oficio_justificativa = justificativaFinal.trim();

  const numeroProcesso = processoAtivo.value ? processo.value.trim() : '';
  if (numeroProcesso) {
    o.numero_processo = numeroProcesso;
    o.dfd_numero_processo = numeroProcesso;
  }
  if (isInexigibilidadeManutencaoRoute.value) {
    if (orgaoUnidadeVeiculo.value.trim()) o.orgao = orgaoUnidadeVeiculo.value.trim();
  } else if (isFornecedorExclusivoRoute.value) {
    if (orgaoResponsavelEquipamento.value.trim()) o.orgao = orgaoResponsavelEquipamento.value.trim();
    else if (orgao.value.trim()) o.orgao = orgao.value.trim();
  } else if (orgao.value.trim()) {
    o.orgao = orgao.value.trim();
  }
  const objetoEspecificoFinal = (
    objetoEspecifico.value === 'Outro'
      ? outroObjetoEspecifico.value.trim()
      : objetoEspecifico.value.trim()
  );
  if (objetoEspecificoFinal) o.objeto_especifico = objetoEspecificoFinal;
  if (equipamento.value.trim()) o.equipamento = equipamento.value.trim();
  if (marca.value.trim()) o.marca = marca.value.trim();
  if (modelo.value.trim()) o.modelo = modelo.value.trim();
  if (placa.value.trim()) o.numero_placa = placa.value.trim();
  if (fornecedor.value.trim()) o.fornecedor = fornecedor.value.trim();
  if (cnpj.value.trim()) o.cnpj_fornecedor = cnpj.value.trim();
  if (valorGlobal.value.trim()) o.valor_total = valorGlobal.value.trim();
  if (fixoTratNome.value.trim()) o.ao_senhor_genero = fixoTratNome.value.trim();
  if (fixoTratCargo.value.trim()) o.senhor_senhora_genero = fixoTratCargo.value.trim();

  if (isInexigibilidadeManutencaoRoute.value) {
    const dfdObjRef = buildInexig74ManutencaoDfdObjetoReferencia().trim();
    const dfdJust = buildInexig74ManutencaoDfdJustificativa().trim();
    if (dfdObjRef) o.dfd_objeto_referencia = dfdObjRef;
    if (dfdJust) o.dfd_justificativa = dfdJust;
  } else if (isFornecedorExclusivoRoute.value) {
    const dfdObjFe = buildInexigFornecedorExclusivoDfdObjetoReferencia().trim();
    const justFe = buildInexigFornecedorExclusivoJustificativaTrDfd().trim();
    const objetoFeTr = buildInexigFornecedorExclusivoObjetoTrResumo({ forOficio: false }).trim();
    const objetoFeOf = buildInexigFornecedorExclusivoObjetoTrResumo({ forOficio: true }).trim();
    if (dfdObjFe) o.dfd_objeto_referencia = dfdObjFe;
    if (justFe) {
      o.justificativa = justFe;
      o.dfd_justificativa = justFe;
      o.sol_oficio_justificativa = justFe;
    }
    if (objetoFeTr) {
      o.objeto = objetoFeTr;
    }
    if (objetoFeOf) {
      o.sol_oficio_objeto = objetoFeOf;
      o.sol_oficio_assunto = objetoFeOf;
    }
  }

  const fundamentoLegal = resolveSolOficioFundamentoLegal(logicalRouteName.value);
  if (fundamentoLegal) o.sol_oficio_artigo_inciso = fundamentoLegal;

  const itensPayload = itens.value
    .filter((i) => Object.values(i).some((v) => String(v || '').trim()))
    .map((i) => ({
      descricao: String(i.descricao || '').trim(),
      unidade: String(i.unidade || '').trim(),
      quantidade: String(i.quantidade || '').trim(),
      valor_unitario: String(i.valorUnitario || '').trim(),
      valor_total: String(i.valorTotal || '').trim(),
    }));
  if (itensPayload.length) o.itens = itensPayload;

  return Object.keys(o).length ? o : null;
}
function parseClauseSections(text) {
  const normalized = String(text || '').replace(/\r/g, '');
  const sections = {
    objeto: '',
    justificativa: '',
    escopo: '',
    entregas: '',
    resultados: '',
  };
  const lines = normalized.split('\n');
  let current = '';
  const keyByHeader = {
    objeto: 'objeto',
    justificativa: 'justificativa',
    escopo: 'escopo',
    entregas: 'entregas',
    'resultados esperados': 'resultados',
    resultados: 'resultados',
  };
  lines.forEach((line) => {
    const trimmed = line.trim();
    const low = trimmed.toLowerCase().replace(/[*:#-]/g, '').trim();
    const headerMatch = Object.keys(keyByHeader).find((k) => low.startsWith(k));
    if (headerMatch) {
      current = keyByHeader[headerMatch];
      const content = trimmed.replace(/^.*?:\s*/, '');
      if (content && content !== trimmed) sections[current] += (sections[current] ? '\n' : '') + content;
      return;
    }
    if (current) sections[current] += (sections[current] ? '\n' : '') + trimmed;
  });
  return sections;
}
function extractClausesFromSectionTexts(sectionTexts) {
  const get = (...keys) => {
    for (const key of keys) {
      const value = sectionTexts?.[key];
      if (typeof value === 'string' && value.trim()) return value.trim();
    }
    return '';
  };
  return {
    objeto: get('objeto', 'objeto_licitacao', 'do_objeto'),
    justificativa: get('justificativa', 'necessidade', 'fundamentacao', 'da_necessidade'),
  };
}
async function onGenerateClauses() {
  isGeneratingClauses.value = true;
  generateError.value = '';
  try {
    const contratado = String(clausulaContratado.value || '').trim();
    const setor = String(clausulaSetor.value || '').trim();
    const caracteristicas = String(clausulaCaracteristicas.value || '').trim();
    if (!contratado || !setor) {
      generateError.value = 'Preencha "O que será contratado?" e "Qual setor/secretaria será atendido?" para gerar objeto e justificativa.';
      return;
    }
    const prompt = [
      'Com base EXCLUSIVAMENTE nos dados abaixo, gere APENAS duas seções:',
      'Objeto:',
      'Justificativa:',
      '',
      'REGRAS OBRIGATÓRIAS:',
      '- Não inventar órgão, secretaria, tipo de objeto, localidade, frota, veículos, alunos ou professores se não estiver explicitamente informado.',
      '- Não reutilizar contexto de mensagens anteriores.',
      '- Usar apenas os três campos fornecidos pelo usuário.',
      '- Se faltar informação, escrever de forma genérica sem adicionar fatos novos.',
      '',
      `O que será contratado: ${contratado}`,
      `Setor/secretaria atendido: ${setor}`,
      `Características mínimas (opcional): ${caracteristicas || 'não informado'}`,
      `Tipo de manutenção: ${isDispensaManutencaoRoute.value ? (tipoManutencao.value || 'não informado') : 'não se aplica'}`,
      `Revisão/KM: ${isDispensaManutencaoRoute.value ? (revisaoKm.value || 'não informado') : 'não se aplica'}`,
    ].join('\n');
    async function requestClausesFast(promptText) {
      const fastPrompt = [
        promptText,
        '',
        'Formato obrigatório de resposta:',
        'Objeto: <texto>',
        'Justificativa: <texto>',
        '',
        'Não inclua nenhuma seção extra.',
      ].join('\n');
      const res = await fetch(`${API_BASE}/api/llm/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ prompt: fastPrompt, stream: false }),
      });
      const data = await res.json().catch(() => ({}));
      const text = data?.data?.response || data?.data?.text || data?.response || data?.text || '';
      return { res, data: { ok: !!data?.ok, response: text } };
    }
    const { res, data } = await requestClausesFast(prompt);
    if (!res.ok || !data.ok) {
      generateError.value = res.status === 504
        ? 'A IA demorou para responder (504 Gateway Timeout). Tente um prompt mais objetivo ou gere novamente em alguns instantes.'
        : (data.error || data.detail || `Erro ${res.status} ao gerar cláusulas`);
      return;
    }
    const bySections = extractClausesFromSectionTexts(data.section_texts || {});
    const text = data.generated_text || data.text || data.content || data.response || '';
    const parsed = (bySections.objeto || bySections.justificativa)
      ? bySections
      : parseClauseSections(text);
    if (!parsed.objeto && !parsed.justificativa && !String(text).trim()) {
      clausulaObjeto.value = gerarObjetoTexto(contratado, setor, caracteristicas, tipoManutencao.value, revisaoKm.value);
      clausulaJustificativa.value = gerarJustificativaTexto(contratado, setor, caracteristicas, tipoManutencao.value, revisaoKm.value);
      return;
    }
    clausulaObjeto.value = parsed.objeto || gerarObjetoTexto(contratado, setor, caracteristicas, tipoManutencao.value, revisaoKm.value);
    clausulaJustificativa.value = parsed.justificativa || gerarJustificativaTexto(contratado, setor, caracteristicas, tipoManutencao.value, revisaoKm.value);
    await saveUserGlobalPreset();
  } catch (e) {
    clausulaObjeto.value = gerarObjetoTexto(clausulaContratado.value, clausulaSetor.value, clausulaCaracteristicas.value, tipoManutencao.value, revisaoKm.value);
    clausulaJustificativa.value = gerarJustificativaTexto(clausulaContratado.value, clausulaSetor.value, clausulaCaracteristicas.value, tipoManutencao.value, revisaoKm.value);
    generateError.value = e?.message || 'Não foi possível gerar via IA; aplicamos a versão padrão local.';
    await saveUserGlobalPreset();
  } finally {
    isGeneratingClauses.value = false;
  }
}
function buildUserPrompt() {
  const lines = [
    `Gerar documento com base nos dados preenchidos para ${String(route.meta?.title || 'a rota atual')}.`,
    `Cabeçalho do documento: ${cabecalhoDocumento.value || 'Não informado'}`,
    `Processo: ${processoAtivo.value ? (processo.value || 'Não informado') : 'Não se aplica'}`,
    `Órgão: ${orgao.value || 'Não informado'}`,
    ...(isManutencaoVeiculosRoute.value
      ? [`Veículo: ${marca.value || '-'} ${modelo.value || '-'} / Placa ${placa.value || '-'}`]
      : []),
    `Fornecedor: ${fornecedor.value || 'Não informado'} / CNPJ: ${cnpj.value || 'Não informado'}`,
    `Valor global: ${valorGlobal.value || 'Não informado'}`,
  ];
  if (isDispensaManutencaoRoute.value) {
    const idx = isManutencaoVeiculosRoute.value ? 5 : 4;
    lines.splice(idx, 0, `Tipo de manutenção: ${tipoManutencao.value || 'Não informado'}`);
  }
  return lines.join('\n');
}
async function onSubmit() {
  generateError.value = '';
  successMessage.value = '';
  documentReady.value = false;
  revokeDocumentUrls();
  if (isDispensaNormalRoute.value) {
    const hasObjeto = !!clausulaObjeto.value.trim();
    const hasJustificativa = !!clausulaJustificativa.value.trim();
    if (!hasObjeto || !hasJustificativa) {
      generateError.value =
        'Para Dispensa normal, gere as cláusulas com IA (ou preencha Objeto e Justificativa manualmente) antes de gerar o documento.';
      return;
    }
  }
  const pendente = secoes.value.find((s) => !s.completo);
  if (pendente) {
    generateError.value = `Preencha todos os campos obrigatórios em «${pendente.titulo}» antes de gerar os documentos.`;
    return;
  }
  isSubmitting.value = true;
  try {
    const payload = {
      user_prompt: buildUserPrompt(),
      slots_override: buildSlotsOverride(),
      slot_package_key: slotPackageKey.value,
    };
    if (cabecalhoMergeTemplateId.value) payload.template_id = cabecalhoMergeTemplateId.value;
    const gerarUrl = buildGerarTrEDfdUrl(API_BASE);
    const result = await fetchGerarTrEDfdWithRetry(API_BASE, payload);
    if (!result.ok) {
      if (result.kind === 'network') {
        const msg = String(result.errorMessage || '');
        const looksNetwork = /fetch|network|failed|load|aborted|timed out|timeout/i.test(msg);
        generateError.value = looksNetwork
          ? `${describeGerarTrEDfdNetworkFailure(gerarUrl)}\n\nConfira rede, VPN e HTTPS (VITE_API_URL no build, ex.: https://api.docmasteria.com.br).`
          : msg;
      } else {
        generateError.value =
          result.status === 500
            ? result.data?.error || result.data?.detail || result.errorMessage || 'Erro 500 no servidor. Veja logs do backend.'
            : result.errorMessage;
      }
      return;
    }
    const { data } = result;
    if (!data.tr?.docx_base64 || !data.dfd?.docx_base64 || !data.oficio?.docx_base64) {
      generateError.value = data.error || 'TR, DFD ou Solicitação/Ofício não vieram na resposta.';
      return;
    }
    documentTrUrl.value = toBlobUrl(data.tr.docx_base64, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    documentDfdUrl.value = toBlobUrl(data.dfd.docx_base64, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    documentOficioUrl.value = toBlobUrl(data.oficio.docx_base64, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    documentZipUrl.value = data.zip?.zip_base64 ? toBlobUrl(data.zip.zip_base64, 'application/zip') : '';
    documentTrFilename.value = data.tr?.filename || 'termo_referencia.docx';
    documentDfdFilename.value = data.dfd?.filename || 'dfd.docx';
    documentOficioFilename.value = data.oficio?.filename || 'oficio.docx';
    documentZipFilename.value = data.zip?.filename || 'tr_dfd_oficio.zip';
    documentReady.value = true;
    successMessage.value = 'Termo de Referência, DFD e Solicitação/Ofício gerados com sucesso. Baixe os arquivos abaixo.';
    await saveUserGlobalPreset();
  } catch (e) {
    generateError.value = e?.message || 'Erro ao gerar documento';
  } finally {
    isSubmitting.value = false;
  }
}
async function onApplyFixedData() {
  await saveUserGlobalPreset();
  {
    const current = String(orgao.value || '').trim();
    if (current) {
      const allowed = new Set((mergedOrgaoOptions.value || []).map((x) => String(x || '').trim()).filter(Boolean));
      if (!allowed.has(current)) orgao.value = '';
    }
  }
  drawerOpen.value = false;
}

/** Zera o estado da tela e reaplica preset global / catálogo (mesmo fluxo do primeiro acesso). */
async function resetFormStateForNewRoute() {
  revokeDocumentUrls();
  drawerOpen.value = false;
  cabecalhoDocumento.value = '';
  processoAtivo.value = false;
  processo.value = '';
  orgao.value = '';
  orgaoResponsavelEquipamento.value = '';
  orgaoUnidadeVeiculo.value = '';
  objetoEspecifico.value = '';
  outroObjetoEspecifico.value = '';
  equipamento.value = '';
  marca.value = '';
  modelo.value = '';
  placa.value = '';
  tipoManutencao.value = '';
  revisaoKm.value = '';
  fornecedor.value = '';
  cnpj.value = '';
  dotacaoAtiva.value = false;
  dotacao.value = '';
  itens.value = [{ ...emptyItem }];
  valorGlobal.value = '';
  fiscal.value = '';
  responsavel.value = '';
  responsavelCargo.value = '';
  modoData.value = '';
  dataManual.value = '';
  fixoTratNome.value = '';
  fixoNome.value = '';
  fixoTratCargo.value = '';
  fixoCargo.value = '';
  fixoResponsavel.value = '';
  fixoResponsavelCargo.value = '';
  fixoSetor.value = '';
  fixoDemanda.value = '';
  fixoEmail.value = '';
  fixoGestor.value = '';
  fixoFiscal.value = '';
  fixoAssinatura.value = '';
  fixoAssinaturaCargo.value = '';
  isSubmitting.value = false;
  generateError.value = '';
  successMessage.value = '';
  documentReady.value = false;
  documentTrFilename.value = 'termo_referencia.docx';
  documentDfdFilename.value = 'dfd.docx';
  documentOficioFilename.value = 'oficio.docx';
  documentZipFilename.value = 'tr_dfd_oficio.zip';
  isGeneratingClauses.value = false;
  clausulaContratado.value = '';
  clausulaSetor.value = '';
  clausulaCaracteristicas.value = '';
  clausulaObjeto.value = '';
  clausulaJustificativa.value = '';
  selectedOrgaoProfileId.value = '';
  orgaoProfileName.value = '';
  Object.keys(slotFieldOptions).forEach((k) => {
    delete slotFieldOptions[k];
  });
  loadOrgaoProfiles();
  await loadUserGlobalPreset();
  await loadCabecalhoOptions();
  await loadSlotCatalogSuggestions();
  {
    const current = String(orgao.value || '').trim();
    if (current) {
      const allowed = new Set((mergedOrgaoOptions.value || []).map((x) => String(x || '').trim()).filter(Boolean));
      if (!allowed.has(current)) orgao.value = '';
    }
  }
}

onMounted(async () => {
  await resetFormStateForNewRoute();
});

watch(
  () => route.name,
  async (name, prev) => {
    if (prev === undefined) return;
    const n = String(name || '');
    const p = String(prev || '');
    if (n === p) return;
    if (!INEX_ART74_I_SHARED_ROUTE_NAMES.has(n) || !INEX_ART74_I_SHARED_ROUTE_NAMES.has(p)) return;
    await resetFormStateForNewRoute();
  },
);
onBeforeUnmount(() => {
  revokeDocumentUrls();
});

const secoes = computed(() => {
  const itensValidos = itens.value.filter((i) => Object.values(i).some(isFilled));
  return [
    {
      titulo: 'Dados básicos',
      completo: (
        isFilled(cabecalhoDocumento.value)
        && (!processoAtivo.value || isFilled(processo.value))
        && isFilled(orgao.value)
        && (!isFornecedorExclusivoRoute.value || isFilled(orgaoResponsavelEquipamento.value))
        && (!isInexigibilidadeManutencaoRoute.value || isFilled(orgaoUnidadeVeiculo.value))
      ),
      linhas: [
        ['Cabeçalho', cabecalhoDocumento.value || 'Não informado', isFilled(cabecalhoDocumento.value)],
        ['Processo', processoAtivo.value ? processo.value || 'Não informado' : 'Não se aplica', !processoAtivo.value || isFilled(processo.value)],
        ['Órgão', orgao.value || 'Não informado', isFilled(orgao.value)],
        ...(isFornecedorExclusivoRoute.value
          ? [[LABEL_ORGAO_UNIDADE_RESP_EQUIP, orgaoResponsavelEquipamento.value || 'Não informado', isFilled(orgaoResponsavelEquipamento.value)]]
          : []),
        ...(isInexigibilidadeManutencaoRoute.value
          ? [[LABEL_ORGAO_UNIDADE_VEICULO, orgaoUnidadeVeiculo.value || 'Não informado', isFilled(orgaoUnidadeVeiculo.value)]]
          : []),
      ],
    },
    ...(isManutencaoVeiculosRoute.value ? [{ titulo: 'Veículo', completo: isFilled(marca.value) && isFilled(modelo.value) && isFilled(placa.value), linhas: [['Marca', marca.value || 'Não informado', isFilled(marca.value)], ['Modelo', modelo.value || 'Não informado', isFilled(modelo.value)], ['Placa', placa.value || 'Não informado', isFilled(placa.value)]] }] : []),
    ...(isFornecedorExclusivoRoute.value ? [{
      titulo: 'Objeto específico',
      completo: isFilled(objetoEspecifico.value) && (objetoEspecifico.value !== 'Outro' || isFilled(outroObjetoEspecifico.value)),
      linhas: [
        ['Objeto específico', objetoEspecifico.value || 'Não informado', isFilled(objetoEspecifico.value)],
        ['Descrição', objetoEspecifico.value === 'Outro' ? (outroObjetoEspecifico.value || 'Não informada') : 'Não se aplica', objetoEspecifico.value !== 'Outro' || isFilled(outroObjetoEspecifico.value)],
      ],
    }] : []),
    ...(isFornecedorExclusivoRoute.value ? [{
      titulo: 'Equipamento',
      completo: isFilled(equipamento.value) && isFilled(marca.value) && isFilled(modelo.value),
      linhas: [
        ['Equipamento', equipamento.value || 'Não informado', isFilled(equipamento.value)],
        ['Marca', marca.value || 'Não informado', isFilled(marca.value)],
        ['Modelo', modelo.value || 'Não informado', isFilled(modelo.value)],
      ],
    }] : []),
    ...(isDispensaManutencaoRoute.value ? [{
      titulo: 'Manutenção',
      completo: isFilled(tipoManutencao.value) && (tipoManutencao.value !== 'Preventiva' || isFilled(revisaoKm.value)),
      linhas: [
        ['Tipo', tipoManutencao.value || 'Não informado', isFilled(tipoManutencao.value)],
        ['Revisão/KM', tipoManutencao.value === 'Preventiva' ? revisaoKm.value || 'Não informado' : 'Não se aplica', tipoManutencao.value !== 'Preventiva' || isFilled(revisaoKm.value)],
      ],
    }] : []),
    { titulo: 'Fornecedor', completo: isFilled(fornecedor.value) && isFilled(cnpj.value), linhas: [['Razão social', fornecedor.value || 'Não informado', isFilled(fornecedor.value)], ['CNPJ', cnpj.value || 'Não informado', isFilled(cnpj.value)]] },
    { titulo: 'Dotação orçamentária', completo: !dotacaoAtiva.value || isFilled(dotacao.value), linhas: [['Situação', dotacaoAtiva.value ? 'Informar dotação' : 'Não informada', true], ['Dotação', dotacaoAtiva.value ? dotacao.value || 'Não informada' : 'Não se aplica', !dotacaoAtiva.value || isFilled(dotacao.value)]] },
    { titulo: 'Itens', completo: itensValidos.length > 0 && isFilled(valorGlobal.value), linhas: [['Itens lançados', String(itensValidos.length), itensValidos.length > 0], ['Valor global', valorGlobal.value || 'Não informado', isFilled(valorGlobal.value)]] },
    { titulo: 'Fiscalização', completo: isFilled(fiscal.value), linhas: [['Fiscal', fiscal.value || 'Não informado', isFilled(fiscal.value)]] },
    { titulo: 'Responsável pelo TR', completo: isFilled(responsavel.value) && isFilled(responsavelCargo.value), linhas: [['Responsável', responsavel.value || 'Não informado', isFilled(responsavel.value)], ['Cargo/função', responsavelCargo.value || 'Não informado', isFilled(responsavelCargo.value)]] },
    { titulo: 'Data', completo: isFilled(modoData.value) && (modoData.value !== 'Data manual' || isFilled(dataManual.value)), linhas: [['Modo', modoData.value || 'Não informado', isFilled(modoData.value)], ['Data', modoData.value === 'Data manual' ? dataManual.value || 'Não informada' : 'Não se aplica', modoData.value !== 'Data manual' || isFilled(dataManual.value)]] },
  ];
});

const completos = computed(() => secoes.value.filter((s) => s.completo).length);
const progresso = computed(() => Math.round((completos.value / secoes.value.length) * 100));
/** Dispensa normal exige objeto/justificativa do bloco de cláusulas; demais rotas seguem o resumo (opcionais não bloqueiam). */
const podeGerarDocumentos = computed(() => {
  if (isDispensaNormalRoute.value) {
    if (!clausulaObjeto.value.trim() || !clausulaJustificativa.value.trim()) return false;
  }
  return secoes.value.every((s) => s.completo);
});
</script>

<style>
.ixp-header h1 { margin: 0; font-size: 20px; color: #0f172a; }
.ixp-header p { margin: 4px 0 0; font-size: 13px; color: #64748b; }
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
.ixp-field input:not(.da75-input), .ixp-field textarea { width: 100%; border: 1px solid #cbd5e1; border-radius: 12px; padding: 10px 11px; font-size: 14px; color: #1e293b; outline: none; }
.ixp-field select:not(.da75-select) { width: 100%; border: 1px solid #cbd5e1; border-radius: 12px; padding: 10px 11px; font-size: 14px; color: #1e293b; outline: none; }
.ixp-field input:not(.da75-input):focus, .ixp-field textarea:focus { border-color: #38bdf8; }
.ixp-field select:not(.da75-select):focus { border-color: #38bdf8; }
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
.ixp-btn-xs { padding: 6px 10px; font-size: 12px; border-radius: 10px; }
.ixp-inline-actions { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.ixp-orgao-profile-actions { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; width: 100%; }
.ixp-orgao-profile-actions > button { width: 100%; padding: 10px 12px; font-size: 13px; border-radius: 10px; }
.ixp-orgao-btn-save { background: #2563eb; border-color: #2563eb; color: #fff; }
.ixp-orgao-btn-delete { background: #dc2626; border-color: #dc2626; color: #fff; }
.ixp-orgao-profile-actions > button:disabled { opacity: 0.6; }
.ixp-subsection-title { margin: 6px 0 0; font-size: 13px; color: #334155; }
.ixp-btn-primary { border: 0; background: #2563eb; color: #fff; border-radius: 12px; padding: 10px 14px; font-size: 13px; font-weight: 700; width: fit-content; }
.ixp-hint { margin: 0; font-size: 12px; color: #64748b; }
.ixp-error { margin: 0; border: 1px solid #fecaca; background: #fff1f2; color: #b91c1c; border-radius: 12px; padding: 9px 11px; font-size: 13px; white-space: pre-wrap; }
.ixp-success { margin: 0; border: 1px solid #bbf7d0; background: #f0fdf4; color: #166534; border-radius: 12px; padding: 9px 11px; font-size: 13px; }
.ixp-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, .2); z-index: 40; }
.ixp-drawer { position: fixed; right: 0; top: 0; height: 100%; width: 100%; max-width: 880px; transform: translateX(100%); transition: transform .25s ease; background: #fff; border-left: 1px solid #e2e8f0; z-index: 50; display: grid; grid-template-rows: auto 1fr auto; }
.ixp-drawer.is-open { transform: translateX(0); }
.ixp-drawer-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding: 14px 16px; }
.ixp-drawer-head small { font-size: 11px; text-transform: uppercase; color: #64748b; letter-spacing: .08em; }
.ixp-drawer-head h3 { margin: 3px 0 0; font-size: 16px; color: #0f172a; }
.ixp-drawer-body { overflow: auto; padding: 16px; display: grid; gap: 12px; }
/* Mesmos rótulos que «Dados básicos» (da75-label--compact) */
.ixp-drawer .ixp-field > label {
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  letter-spacing: 0.02em;
}
.ixp-drawer-foot { border-top: 1px solid #e2e8f0; padding: 14px 16px; }
.ixp-drawer-foot .ixp-btn-primary { width: 100%; }
@media (max-width: 900px) { .ixp-grid-2, .ixp-grid-3, .ixp-grid-item { grid-template-columns: 1fr; } .ixp-col-2 { grid-column: auto; } }
.dm-dark .ixp-main, .dm-dark .ixp-card, .dm-dark .ixp-drawer, .dm-dark .ixp-item,
.dm-dark-theme .ixp-main, .dm-dark-theme .ixp-card, .dm-dark-theme .ixp-drawer, .dm-dark-theme .ixp-item { background: #0f172a; border-color: #334155; }
.dm-dark .ixp-main-head, .dm-dark .ixp-drawer-head, .dm-dark .ixp-drawer-foot,
.dm-dark-theme .ixp-main-head, .dm-dark-theme .ixp-drawer-head, .dm-dark-theme .ixp-drawer-foot { border-color: #334155; }
.dm-dark .ixp-drawer .ixp-field > label,
.dm-dark-theme .ixp-drawer .ixp-field > label { color: #94a3b8; }
.dm-dark .ixp-main-title h2, .dm-dark .ixp-main-title p, .dm-dark .ixp-card h3, .dm-dark .ixp-choice strong,
.dm-dark-theme .ixp-main-title h2, .dm-dark-theme .ixp-main-title p, .dm-dark-theme .ixp-card h3, .dm-dark-theme .ixp-choice strong { color: #e2e8f0; }
.dm-dark .ixp-main-title small, .dm-dark .ixp-field label, .dm-dark .ixp-check, .dm-dark .ixp-item-head span, .dm-dark .ixp-choice span, .dm-dark .ixp-drawer-head small,
.dm-dark-theme .ixp-main-title small, .dm-dark-theme .ixp-field label, .dm-dark-theme .ixp-check, .dm-dark-theme .ixp-item-head span, .dm-dark-theme .ixp-choice span, .dm-dark-theme .ixp-drawer-head small { color: #94a3b8; }
.dm-dark .ixp-field input:not(.da75-input), .dm-dark .ixp-field textarea, .dm-dark .ixp-field select:not(.da75-select), .dm-dark .ixp-btn-secondary, .dm-dark .ixp-choice,
.dm-dark-theme .ixp-field input:not(.da75-input), .dm-dark-theme .ixp-field textarea, .dm-dark-theme .ixp-field select:not(.da75-select), .dm-dark-theme .ixp-btn-secondary, .dm-dark-theme .ixp-choice { background: #0b1222; border-color: #334155; color: #e2e8f0; }
.dm-dark .ixp-field input::placeholder, .dm-dark .ixp-field textarea::placeholder,
.dm-dark-theme .ixp-field input::placeholder, .dm-dark-theme .ixp-field textarea::placeholder { color: #64748b; }
.dm-dark .ixp-field input:not(.da75-input):focus, .dm-dark .ixp-field textarea:focus, .dm-dark .ixp-field select:not(.da75-select):focus,
.dm-dark-theme .ixp-field input:not(.da75-input):focus, .dm-dark-theme .ixp-field textarea:focus, .dm-dark-theme .ixp-field select:not(.da75-select):focus { border-color: #0ea5e9; }
.dm-dark .ixp-btn-secondary,
.dm-dark-theme .ixp-btn-secondary { color: #cbd5e1; }
.dm-dark .ixp-orgao-btn-save,
.dm-dark-theme .ixp-orgao-btn-save { background: #2563eb; border-color: #2563eb; color: #fff; }
.dm-dark .ixp-orgao-btn-delete,
.dm-dark-theme .ixp-orgao-btn-delete { background: #dc2626; border-color: #dc2626; color: #fff; }
.dm-dark .ixp-choice.is-active,
.dm-dark-theme .ixp-choice.is-active { border-color: #38bdf8; background: #082f49; }
.dm-dark .ixp-overlay,
.dm-dark-theme .ixp-overlay { background: rgba(2, 6, 23, 0.72); }
.dm-dark .ixp-error,
.dm-dark-theme .ixp-error { border-color: #9f1239; background: #3f1d2e; color: #fecdd3; }
.dm-dark .ixp-success,
.dm-dark-theme .ixp-success { border-color: #166534; background: #052e16; color: #bbf7d0; }
.dm-dark .ixp-hint,
.dm-dark-theme .ixp-hint { color: #94a3b8; }
.dm-dark .ixp-subsection-title,
.dm-dark-theme .ixp-subsection-title { color: #cbd5e1; }
</style>
