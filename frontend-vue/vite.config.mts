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
        // PDF / relatórios grandes: evita timeout do proxy em dev (default ~2 min).
        timeout: 600000,
        proxyTimeout: 600000,
      },
      "/media": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000,
      },
    },
  },
  css: {
    devSourcemap: true,
  },
});

