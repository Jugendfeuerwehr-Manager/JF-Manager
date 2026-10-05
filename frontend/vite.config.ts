import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import nightwatchPlugin from 'vite-plugin-nightwatch'

// https://vite.dev/config/
// Dev server proxy target. The SPA itself calls the relative /api/v1 so that
// browser, SPA and API share one origin (session and CSRF cookies).
const BACKEND = (() => {
  try {
    if (process.env.VITE_BACKEND_URL) return new URL(process.env.VITE_BACKEND_URL).origin
    return process.env.VITE_API_BASE_URL
      ? new URL(process.env.VITE_API_BASE_URL).origin  // legacy absolute value, e.g. http://localhost:8000
      : 'http://localhost:8000'
  } catch {
    return 'http://localhost:8000'
  }
})()

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
