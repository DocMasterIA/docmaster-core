import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue(), react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@repo": fileURLToPath(new URL("..", import.meta.url)),
      "react/jsx-runtime": fileURLToPath(new URL("./node_modules/react/jsx-runtime.js", import.meta.url)),
      "react-dom/client": fileURLToPath(new URL("./node_modules/react-dom/client.js", import.meta.url)),
    },
    dedupe: ["react", "react-dom"],
  },
  server: {
    port: 5173,
    fs: {
      allow: [fileURLToPath(new URL("..", import.meta.url))],
    },
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

