import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Ports are deliberately in the *273 family so nothing here collides with
// opik (5174/8080/3333/...) or psy/computational-learning (5211/8321/5433).
const DEV_PORT = 5273;
const API_PORT = 8273;

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": new URL("./src", import.meta.url).pathname },
  },
  server: {
    port: DEV_PORT,
    // Fail loudly instead of silently hopping to 5274 and confusing the proxy.
    strictPort: true,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${API_PORT}`,
        changeOrigin: true,
      },
    },
  },
});
