<template>
  <div class="ife-page">
    <div class="ife-wrap">
      <div class="ife-head">
        <h1>Inexigibilidade</h1>
        <p>Fornecedor Exclusivo Geral — Bens, Serviços e Soluções (Art. 74, I)</p>
        <button type="button" class="ife-btn ife-btn-secondary" @click="drawerOpen = true">Dados fixos</button>
      </div>

      <div class="ife-grid">
        <section class="ife-card">
          <h3>Dados básicos</h3>
          <label class="ife-check"><input v-model="processoAtivo" type="checkbox" /> Informar número do processo (opcional)</label>
          <input v-if="processoAtivo" v-model="processo" class="ife-input" placeholder="Ex: 123/2026" />
          <input v-model="orgao" class="ife-input" placeholder="Órgão/Unidade responsável pelo equipamento" />
        </section>

        <section class="ife-card">
          <h3>Objeto específico</h3>
          <select v-model="objetoEspecifico" class="ife-input">
            <option value="">Selecione</option>
            <option v-for="o in objetoOptions" :key="o" :value="o">{{ o }}</option>
          </select>
          <input v-if="objetoEspecifico === 'Outro'" v-model="outroObjetoEspecifico" class="ife-input" placeholder="Descreva o objeto específico" />
        </section>

        <section class="ife-card">
          <h3>Dados do equipamento</h3>
          <input v-model="equipamento" class="ife-input" placeholder="Equipamento" />
          <input v-model="marca" class="ife-input" placeholder="Marca" />
          <input v-model="modelo" class="ife-input" placeholder="Modelo" />
        </section>

        <section class="ife-card">
          <h3>Fornecedor exclusivo</h3>
          <input v-model="fornecedor" class="ife-input" placeholder="Razão social / Nome do fornecedor" />
          <input v-model="cnpj" class="ife-input" placeholder="00.000.000/0001-00" />
        </section>

        <section class="ife-card">
          <h3>Dotação orçamentária</h3>
          <label class="ife-check"><input v-model="dotacaoAtiva" type="checkbox" /> Informar dotação orçamentária (opcional)</label>
          <textarea v-if="dotacaoAtiva" v-model="dotacao" class="ife-input" rows="3" placeholder="Ex: Órgão: 02..." />
        </section>

        <section class="ife-card">
          <h3>Itens e valores</h3>
          <div v-for="(it, i) in itens" :key="i" class="ife-item">
            <input v-model="it.descricao" class="ife-input" placeholder="Descrição" />
            <div class="ife-row">
              <input v-model="it.quantidade" class="ife-input" placeholder="Quantidade" />
              <input v-model="it.unidade" class="ife-input" placeholder="Unidade" />
            </div>
            <div class="ife-row">
              <input v-model="it.valor_unitario" class="ife-input" placeholder="Valor unitário" />
              <input v-model="it.valor_total" class="ife-input" placeholder="Valor total" />
            </div>
          </div>
          <button type="button" class="ife-btn ife-btn-secondary" @click="addItem">Adicionar item</button>
          <input v-model="valorTotalProcesso" class="ife-input" placeholder="Valor total do processo" />
        </section>

        <section class="ife-card">
          <h3>Fiscalização e assinatura</h3>
          <input v-model="fiscal" class="ife-input" placeholder="Nome do fiscal" />
          <input v-model="responsavel" class="ife-input" placeholder="Nome do responsável" />
          <input v-model="responsavelCargo" class="ife-input" placeholder="Cargo/Função" />
        </section>

        <section class="ife-card">
          <h3>Data</h3>
          <select v-model="modoData" class="ife-input">
            <option value="">Selecione</option>
            <option>Data automática</option>
            <option>Datado e assinado digitalmente</option>
            <option>Data manual</option>
          </select>
          <input v-if="modoData === 'Data manual'" v-model="dataManual" class="ife-input" placeholder="dd/mm/aaaa" />
        </section>
      </div>

      <div class="ife-actions">
        <button type="button" class="ife-btn ife-btn-primary" :disabled="isSubmitting" @click="onSubmit">
          {{ isSubmitting ? 'Gerando...' : 'Gerar documento com IA' }}
        </button>
        <p v-if="generateError" class="ife-error">{{ generateError }}</p>
        <p v-if="successMessage" class="ife-ok">{{ successMessage }}</p>
        <div v-if="documentReady" class="ife-downloads">
          <a v-if="documentTrUrl" :href="documentTrUrl" :download="documentTrFilename" class="ife-btn ife-btn-secondary">Download TR</a>
          <a v-if="documentDfdUrl" :href="documentDfdUrl" :download="documentDfdFilename" class="ife-btn ife-btn-secondary">Download DFD</a>
          <a v-if="documentOficioUrl" :href="documentOficioUrl" :download="documentOficioFilename" class="ife-btn ife-btn-secondary">Download Ofício</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const API_BASE = import.meta.dev ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');
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
const itens = ref([{ descricao: '', quantidade: '', unidade: '', valor_unitario: '', valor_total: '' }]);
const valorTotalProcesso = ref('');
const fiscal = ref('');
const responsavel = ref('');
const responsavelCargo = ref('');
const modoData = ref('');
const dataManual = ref('');
const isSubmitting = ref(false);
const generateError = ref('');
const successMessage = ref('');
const documentReady = ref(false);
const documentTrUrl = ref('');
const documentDfdUrl = ref('');
const documentOficioUrl = ref('');
const documentTrFilename = ref('termo_referencia.docx');
const documentDfdFilename = ref('dfd.docx');
const documentOficioFilename = ref('oficio.docx');

const objetoOptions = [
  'Aquisição de bens/produtos', 'Fornecimento de peças', 'Peças originais', 'Peças de reposição',
  'Componentes e acessórios', 'Insumos e materiais', 'Prestação de serviços', 'Manutenção preventiva',
  'Manutenção corretiva', 'Assistência técnica autorizada', 'Suporte técnico especializado', 'Outro',
];

function addItem() {
  itens.value.push({ descricao: '', quantidade: '', unidade: '', valor_unitario: '', valor_total: '' });
}

function toBlobUrl(base64, mimeType) {
  if (!base64) return '';
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mimeType }));
}

function buildSlotsOverride() {
  const o = {
    numero_processo: processoAtivo.value ? processo.value : '',
    orgao: orgao.value,
    objeto_especifico: objetoEspecifico.value === 'Outro' ? outroObjetoEspecifico.value : objetoEspecifico.value,
    equipamento: equipamento.value,
    marca: marca.value,
    modelo: modelo.value,
    fornecedor: fornecedor.value,
    cnpj_fornecedor: cnpj.value,
    valor_total: valorTotalProcesso.value,
    fiscal: fiscal.value ? { nome: fiscal.value } : undefined,
    nome_assinante_termo: responsavel.value,
    cargo_assinante_termo: responsavelCargo.value,
    itens: itens.value.filter((x) => Object.values(x).some((v) => String(v || '').trim())),
  };
  if (dotacaoAtiva.value && dotacao.value.trim()) o.dotacao = dotacao.value.trim();
  const m = String(modoData.value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  if (m === 'data automatica') {
    const now = new Date();
    o.data_termo = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
  } else if (m === 'data manual' && dataManual.value.trim()) o.data_termo = dataManual.value.trim();
  else if (m === 'datado e assinado digitalmente') o.data_termo = 'datado e assinado digitalmente';
  return o;
}

async function onSubmit() {
  isSubmitting.value = true;
  generateError.value = '';
  successMessage.value = '';
  documentReady.value = false;
  try {
    const payload = {
      user_prompt: `Inexigibilidade Art. 74 I - Fornecedor Exclusivo. Objeto: ${objetoEspecifico.value || 'não informado'}.`,
      slots_override: buildSlotsOverride(),
      slot_package_key: 'inexigibilidade_74_i_fornecedor_exclusivo',
    };
    const res = await fetch(`${API_BASE}/api/documentos/gerar-tr-e-dfd`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.error || data.detail || `Erro ${res.status}`);
    documentTrUrl.value = toBlobUrl(data.tr?.docx_base64, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    documentDfdUrl.value = toBlobUrl(data.dfd?.docx_base64, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    documentOficioUrl.value = toBlobUrl(data.oficio?.docx_base64, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    documentTrFilename.value = data.tr?.filename || 'termo_referencia.docx';
    documentDfdFilename.value = data.dfd?.filename || 'dfd.docx';
    documentOficioFilename.value = data.oficio?.filename || 'oficio.docx';
    documentReady.value = true;
    successMessage.value = 'Documentos gerados com sucesso.';
  } catch (e) {
    generateError.value = e?.message || 'Erro ao gerar documento';
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.ife-page { padding: 16px; }
.ife-wrap { max-width: 1200px; margin: 0 auto; }
.ife-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.ife-head h1 { margin: 0; font-size: 22px; }
.ife-head p { margin: 0; color: #64748b; }
.ife-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; margin-top: 12px; }
.ife-card { border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; padding: 12px; }
.ife-card h3 { margin: 0 0 8px; font-size: 14px; }
.ife-input { width: 100%; box-sizing: border-box; margin-top: 8px; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 10px; }
.ife-check { display: block; font-size: 13px; color: #334155; }
.ife-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.ife-item { border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; margin-bottom: 8px; }
.ife-actions { margin-top: 12px; display: grid; gap: 8px; }
.ife-downloads { display: flex; gap: 8px; flex-wrap: wrap; }
.ife-btn { border-radius: 8px; padding: 8px 12px; border: 1px solid #cbd5e1; text-decoration: none; cursor: pointer; }
.ife-btn-primary { background: #2563eb; border-color: #2563eb; color: #fff; }
.ife-btn-secondary { background: #fff; color: #334155; }
.ife-error { color: #b91c1c; }
.ife-ok { color: #15803d; }
</style>
