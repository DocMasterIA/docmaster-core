import { Routes, Route } from 'react-router-dom';
import DocMasterListaCotacoes from './DocMasterListaCotacoes.jsx';
import DocMasterDetalheCotacaoFuncional from './DocMasterDetalheCotacao.jsx';
import DocMasterBuscaCompacta from './DocMasterBuscaCompacta.jsx';
import TelaResultadosComSemaforoIA from './DocMasterTelaManual.jsx';
import TelaRelatorioPesquisaPrecos from './DocMasterRelatorioPesquisaPrecos.jsx';
import TelaRelatorioFinalPesquisaPrecosPreview from '../../relatorio_final_pesquisa_precos_preview.jsx';
import PaginaInicialDocmaster from '../../pagina_inicial_docmaster_final (2) (1).jsx';
import InexigibilidadeManutencaoVeiculosArt74I from '../../1-INEXIGIBILIDADE MANUTENÇÃO VEICULOS ART 74 I.jsx';
import FornecedorExclusivoArt74I from '../../2-FORNECEDOR EXCLUIVO ART 74 I.jsx';
import ModuloDispensaArt75IINormal from '../../modulo_dispensa_art_75_ii_(DISPENSA NORMAL).jsx';
import ModuloDispensaArt75IIRapida from '../../modulo_dispensa_art_75_ii_(DISPENSA RAPIDA).jsx';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<TelaRelatorioFinalPesquisaPrecosPreview />} />
      <Route path="/cotacao" element={<DocMasterDetalheCotacaoFuncional />} />
      <Route path="/busca-item" element={<DocMasterBuscaCompacta />} />
      <Route path="/busca-manual" element={<TelaResultadosComSemaforoIA />} />
      <Route path="/relatorio-pesquisa-precos" element={<TelaRelatorioPesquisaPrecos />} />
      <Route path="/relatorio-final-preview" element={<TelaRelatorioFinalPesquisaPrecosPreview />} />
      <Route path="/pagina-inicial-docmaster" element={<PaginaInicialDocmaster />} />
      <Route
        path="/geracao/inexigibilidade-art-74-i/manutencao-veiculos-preview"
        element={<InexigibilidadeManutencaoVeiculosArt74I />}
      />
      <Route
        path="/geracao/inexigibilidade-art-74-i/fornecedor-exclusivo-preview"
        element={<FornecedorExclusivoArt74I />}
      />
      <Route
        path="/geracao/dispensa-art-75-ii/compras"
        element={<ModuloDispensaArt75IINormal />}
      />
      <Route
        path="/geracao/dispensa-art-75-ii/servicos"
        element={<ModuloDispensaArt75IINormal />}
      />
      <Route
        path="/geracao/dispensa-art-75-ii/compras-servicos-inclusos"
        element={<ModuloDispensaArt75IINormal />}
      />
      <Route
        path="/geracao/dispensa-rapida/art-75-ii/compras"
        element={<ModuloDispensaArt75IIRapida />}
      />
      <Route
        path="/geracao/dispensa-rapida/art-75-ii/servicos"
        element={<ModuloDispensaArt75IIRapida />}
      />
      <Route
        path="/geracao/dispensa-rapida/art-75-ii/compras-servicos-inclusos"
        element={<ModuloDispensaArt75IIRapida />}
      />
    </Routes>
  );
}
