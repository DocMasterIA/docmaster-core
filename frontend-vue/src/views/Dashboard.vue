<template>
  <div>
    <header class="gov-page-header">
      <h1 class="gov-page-title">Painel</h1>
      <p class="gov-page-subtitle">
        Interface para geração de documentos com IA.
      </p>
      <div class="gov-page-header__actions">
        <button class="gov-btn gov-btn--primary" type="button">
          Nova licitação
        </button>
        <button class="gov-btn gov-btn--secondary" type="button">
          Importar edital
        </button>
        <button class="gov-btn gov-btn--outline" type="button">
          Configurações
        </button>
      </div>
    </header>

    <section class="gov-grid gov-mb-md">
      <div class="gov-grid__col-4">
        <div class="gov-surface">
          <div class="gov-surface__header">
            <div>
              <h2 class="gov-surface__title">Resumo</h2>
              <p class="gov-surface__subtitle">
                Indicadores do sistema
              </p>
            </div>
          </div>
          <p class="gov-text-soft">
            Estes cards serão alimentados pelo backend Django via API
            (ex.: contagem de licitações abertas, em julgamento, homologadas).
          </p>
        </div>
      </div>

      <div class="gov-grid__col-8">
        <div class="gov-surface">
          <div class="gov-surface__header">
            <div>
              <h2 class="gov-surface__title">Documentos recentes</h2>
              <p class="gov-surface__subtitle">
                Lista pronta para integração com API
              </p>
            </div>
          </div>
          <table class="gov-table">
            <thead>
              <tr>
                <th>Processo</th>
                <th>Objeto</th>
                <th>Modalidade</th>
                <th>Situação</th>
                <th>Prazo</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>PE 012/2025</td>
                <td>Aquisição de equipamentos de TI</td>
                <td><span class="gov-chip">Pregão eletrônico</span></td>
                <td>
                  <span class="gov-badge gov-badge--info">
                    Aberta para propostas
                  </span>
                </td>
                <td>3 dias</td>
              </tr>
              <tr>
                <td>CONC 008/2025</td>
                <td>Obras de pavimentação urbana</td>
                <td><span class="gov-chip">Concorrência</span></td>
                <td>
                  <span class="gov-badge gov-badge--success">
                    Homologada
                  </span>
                </td>
                <td>Concluído</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
</script>
