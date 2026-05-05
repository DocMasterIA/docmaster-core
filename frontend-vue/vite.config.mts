import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        // Sem teto prático: geração de PDF pode ultrapassar o default (~2 min) do http-proxy.
        timeout: 86_400_000,
        proxyTimeout: 86_400_000,
      },
      "/media": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        timeout: 86_400_000,
        proxyTimeout: 86_400_000,
      },
    },
  },
  css: {
    devSourcemap: true,
  },
});

