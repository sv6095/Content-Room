import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load .env so VITE_API_BASE_URL is available at config time
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.VITE_API_BASE_URL || "http://localhost:8000";

  return {
    server: {
      host: "::",
      port: 8080,
      hmr: {
        overlay: false,
      },
      proxy: {
        // All /api/* and /health requests are forwarded to the backend.
        // Target reads from VITE_API_BASE_URL (.env) — falls back to localhost:8000.
        // In the browser's Network DevTools panel they appear as same-origin
        // calls — the real backend host is never visible to the end user.
        "/api": {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
        },
        "/health": {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});