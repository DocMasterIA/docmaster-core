<template>
  <div class="ixfe-page">
    <div class="ixfe-head">
      <h1>Gerador de Documentos</h1>
      <p>Inexigibilidade - Art. 74, I - Fornecedor Exclusivo</p>
    </div>

    <div class="ixfe-grid">
      <section class="ixfe-card">
        <h2>Dados básicos</h2>
        <label class="ixfe-check"><input v-model="processoAtivo" type="checkbox" /> Informar número do processo (opcional)</label>
        <input v-if="processoAtivo" v-model="processo" class="ixfe-input" placeholder="Ex: 123/2026" />
        <input v-model="orgao" class="ixfe-input" placeholder="Órgão/Unidade responsável pelo equipamento" />
      </section>

      <section class="ixfe-card">
        <h2>Objeto específico</h2>
        <select v-model="objetoEspecifico" class="ixfe-input">
          <option value="">Selecione</option>
          <option v-for="opt in objetoOptions" :key="opt" :value="opt">{{ opt }}</option>
        </select>
        <input
          v-if="objetoEspecifico === 'Outro'"
          v-model="outroObjetoEspecifico"
          class="ixfe-input"
          placeholder="Descreva o objeto específico"
        />
      </section>

      <section class="ixfe-card">
        <h2>Dados do equipamento</h2>
        <input v-model="equipamento" class="ixfe-input" placeholder="Equipamento" />
        <input v-model="marca" class="ixfe-input" placeholder="Marca" />
        <input v-model="modelo" class="ixfe-input" placeholder="Modelo" />
      </section>

      <section class="ixfe-card">
        <h2>Fornecedor exclusivo</h2>
        <input v-model="fornecedor" class="ixfe-input" placeholder="Razão social / Nome do fornecedor" />
        <input v-model="cnpj" class="ixfe-input" placeholder="00.000.000/0001-00" />
      </section>

      <section class="ixfe-card">
        <h2>Itens e valores</h2>
        <input v-model="itemDescricao" class="ixfe-input" placeholder="Descrição" />
        <div class="ixfe-row">
          <input v-model="itemQuantidade" class="ixfe-input" placeholder="Quantidade" />
          <input v-model="itemUnidade" class="ixfe-input" placeholder="Unidade medida" />
        </div>
        <div class="ixfe-row">
          <input v-model="itemValorUnitario" class="ixfe-input" placeholder="Valor unitário" />
          <input v-model="itemValorTotal" class="ixfe-input" placeholder="Valor total" />
        </div>
        <input v-model="valorTotalProcesso" class="ixfe-input" placeholder="Valor total do processo" />
      </section>

      <section class="ixfe-card">
        <h2>Fiscalização e assinatura</h2>
        <input v-model="fiscal" class="ixfe-input" placeholder="Nome do fiscal de contratos" />
        <input v-model="responsavel" class="ixfe-input" placeholder="Nome do responsável" />
        <input v-model="responsavelCargo" class="ixfe-input" placeholder="Cargo/Função" />
      </section>

      <section class="ixfe-card">
        <h2>Data</h2>
        <select v-model="modoData" class="ixfe-input">
          <option value="">Selecione</option>
          <option>Data automática</option>
          <option>Datado e assinado digitalmente</option>
          <option>Data manual</option>
        </select>
        <input v-if="modoData === 'Data manual'" v-model="dataManual" class="ixfe-input" placeholder="dd/mm/aaaa" />
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const objetoOptions = [
  'Aquisição de bens/produtos',
  'Fornecimento de peças',
  'Peças originais',
  'Peças de reposição',
  'Componentes e acessórios',
  'Insumos e materiais',
  'Prestação de serviços',
  'Manutenção preventiva',
  'Manutenção corretiva',
  'Manutenção preventiva e corretiva',
  'Assistência técnica autorizada',
  'Suporte técnico especializado',
  'Outro',
];

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
const itemDescricao = ref('');
const itemQuantidade = ref('');
const itemUnidade = ref('');
const itemValorUnitario = ref('');
const itemValorTotal = ref('');
const valorTotalProcesso = ref('');
const fiscal = ref('');
const responsavel = ref('');
const responsavelCargo = ref('');
const modoData = ref('');
const dataManual = ref('');
</script>

<style scoped>
.ixfe-page { max-width: 1200px; margin: 0 auto; padding: 16px; }
.ixfe-head h1 { margin: 0; font-size: 22px; }
.ixfe-head p { margin: 6px 0 0; color: #64748b; }
.ixfe-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; margin-top: 14px; }
.ixfe-card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; background: #fff; }
.ixfe-card h2 { margin: 0 0 8px; font-size: 14px; }
.ixfe-input { width: 100%; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 10px; margin-top: 8px; }
.ixfe-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.ixfe-check { display: block; font-size: 13px; color: #334155; }
</style>
