/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to the FastAPI backend so the SPA and API share an origin.
// Test config (vitest) lives under `test`; defineConfig is imported from
// "vitest/config" so the block is recognized by vitest 4.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: process.env.VITE_API_URL || "http://localhost:8000", changeOrigin: true },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
