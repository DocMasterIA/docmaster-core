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
        if (!id.endsWith('pagina_inicial_docmaster_final (2) (1).jsx')) {
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
    },
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        '.jsx': 'tsx',
      },
    },
  },
})
