import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import vueDevTools from 'vite-plugin-vue-devtools';
import nightwatchPlugin from 'vite-plugin-nightwatch';
// https://vite.dev/config/
const BACKEND = (() => {
    try {
        return process.env.VITE_API_BASE_URL
            ? new URL(process.env.VITE_API_BASE_URL).origin // e.g. http://localhost:8000
            : 'http://localhost:8000';
    }
    catch {
        return 'http://localhost:8000';
    }
})();
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
            // Proxy /uploads/ so media files work even with relative URLs
            '/uploads': { target: BACKEND, changeOrigin: true },
        },
    },
});
