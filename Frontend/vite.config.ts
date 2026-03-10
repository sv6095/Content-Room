import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load .env so VITE_API_BASE_URL is available at config time
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.VITE_API_BASE_URL?.trim();

  return {
    server: {
      host: "::",
      port: 8080,
      hmr: {
        overlay: false,
      },
      proxy: backendUrl
        ? {
            // All /api/* and /health requests are forwarded to the configured backend.
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
          }
        : {},
    },
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});