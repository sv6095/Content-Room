import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load .env so VITE_API_BASE_URL is available at config time
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.VITE_API_BASE_URL?.trim();

  const proxyConfig = backendUrl
    ? {
        // All /api/* and /health requests are forwarded to the configured backend.
        "/api": {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
          // Handle presigned URLs that may have query parameters
          rewrite: (path: string) => path,
        },
        "/health": {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
        },
      }
    : undefined;

  return {
    // Base URL for deployment (supports subdirectory deployments)
    base: process.env.VITE_APP_BASE || '/',
    
    server: {
      host: "::",
      port: 8080,
      hmr: {
        overlay: false,
      },
      // Configure headers for development - improves CORS debugging
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Cache-Control': 'no-cache, no-store, must-revalidate'
      },
      ...(proxyConfig ? { proxy: proxyConfig } : {}),
      middlewareMode: false,
    },
    build: {
      // Optimize asset handling and chunk sizing
      target: 'ES2020',
      rollupOptions: {
        output: {
          // Better chunking for media/assets
          manualChunks: {
            'vendor': ['react', 'react-dom'],
          },
        },
      },
      // Disable minification of certain assets to aid debugging
      sourcemap: process.env.NODE_ENV !== 'production',
      // Cache busting for better presigned URL handling
      assetsDir: 'assets',
      assetsInlineLimit: 4096,
    },
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});