import { fileURLToPath, URL } from 'node:url';

import { PrimeVueResolver } from '@primevue/auto-import-resolver';
import tailwindcss from '@tailwindcss/vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import VueRouter from 'unplugin-vue-router/vite';
import { defineConfig } from 'vite';
import vueDevTools from 'vite-plugin-vue-devtools';

const backendDir =
    process.env.VITE_BACKEND === 'local'
        ? './src/composables/api/backends/local'
        : './src/composables/api/backends/http';

export default defineConfig({
    plugins: [
        VueRouter({ dts: true }),
        vue(),
        tailwindcss(),
        vueDevTools(),
        Components({
            resolvers: [PrimeVueResolver()],
        }),
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
            '@api-backend': fileURLToPath(
                new URL(backendDir, import.meta.url),
            ),
        },
    },
    server: {
        port: 3099,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/uploads': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
    build: {
        target: 'es2023',
    },
});
