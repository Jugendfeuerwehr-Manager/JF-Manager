import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import nightwatchPlugin from 'vite-plugin-nightwatch'

// https://vite.dev/config/
// Dev server proxy target. The SPA itself calls the relative /api/v1 so that
// browser, SPA and API share one origin (session and CSRF cookies).
function backendOrigin(env: Record<string, string>) {
  try {
    if (env.VITE_BACKEND_URL) return new URL(env.VITE_BACKEND_URL).origin
    // Legacy absolute API URL, e.g. http://localhost:8000/api/v1
    if (env.VITE_API_BASE_URL?.startsWith('http')) return new URL(env.VITE_API_BASE_URL).origin
  } catch {
    // fall through to the default
  }
  return 'http://localhost:8000'
}

// .env files and the shell environment; the shell wins.
const BACKEND = backendOrigin({
  ...loadEnv(process.env.NODE_ENV ?? 'development', process.cwd(), ''),
  ...process.env,
} as Record<string, string>)

export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    nightwatchPlugin(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      // Same origin for SPA and API: session and CSRF cookies need it. The
      // original Host is kept so Django's CSRF origin check matches.
      '/api': { target: BACKEND, changeOrigin: false },
      '/admin': { target: BACKEND, changeOrigin: false },
      '/static': { target: BACKEND, changeOrigin: false },
      // Proxy /uploads/ so media files work even with relative URLs
      '/uploads': { target: BACKEND, changeOrigin: true },
    },
  },
})
