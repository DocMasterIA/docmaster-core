import { Routes, Route } from 'react-router-dom';
import DocMasterListaCotacoes from './DocMasterListaCotacoes.jsx';
import DocMasterDetalheCotacaoFuncional from './DocMasterDetalheCotacao.jsx';
import DocMasterBuscaCompacta from './DocMasterBuscaCompacta.jsx';
import TelaResultadosComSemaforoIA from './DocMasterTelaManual.jsx';
import TelaRelatorioPesquisaPrecos from './DocMasterRelatorioPesquisaPrecos.jsx';
import TelaRelatorioFinalPesquisaPrecosPreview from '../../relatorio_final_pesquisa_precos_preview.jsx';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<TelaRelatorioFinalPesquisaPrecosPreview />} />
      <Route path="/cotacao" element={<DocMasterDetalheCotacaoFuncional />} />
      <Route path="/busca-item" element={<DocMasterBuscaCompacta />} />
      <Route path="/busca-manual" element={<TelaResultadosComSemaforoIA />} />
      <Route path="/relatorio-pesquisa-precos" element={<TelaRelatorioPesquisaPrecos />} />
      <Route path="/relatorio-final-preview" element={<TelaRelatorioFinalPesquisaPrecosPreview />} />
    </Routes>
  );
}
