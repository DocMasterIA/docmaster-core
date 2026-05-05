import path from 'node:path'
import { defineConfig, transformWithEsbuild } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'transform-pagina-inicial-docmaster',
      enforce: 'pre',
      async transform(code, id) {
        const tsxLikeExternalFiles = [
          'pagina_inicial_docmaster_final (2) (1).jsx',
          'relatorio_final_pesquisa_precos_preview.jsx',
          'copia_de_relatorio_final_pesquisa_precos_preview (1).jsx',
          '1-INEXIGIBILIDADE MANUTENÇÃO VEICULOS ART 74 I.jsx',
          '2-FORNECEDOR EXCLUIVO ART 74 I.jsx',
        ]
        const shouldTransform = tsxLikeExternalFiles.some((file) => id.endsWith(file))
        if (!shouldTransform) {
          return null
        }
        return transformWithEsbuild(code, id, {
          loader: 'tsx',
          jsx: 'automatic',
        })
      },
    },
  ],
  resolve: {
    alias: {
      react: path.resolve(__dirname, 'node_modules/react'),
      'react/jsx-runtime': path.resolve(__dirname, 'node_modules/react/jsx-runtime.js'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom'),
      'react-dom/client': path.resolve(__dirname, 'node_modules/react-dom/client.js'),
      'lucide-react': path.resolve(__dirname, 'node_modules/lucide-react'),
    },
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        '.jsx': 'tsx',
      },
    },
  },
  server: {
    fs: {
      // Permite previews via /@fs de arquivos no diretório pai (docmaster-core).
      allow: [path.resolve(__dirname, '..')],
    },
  },
})
