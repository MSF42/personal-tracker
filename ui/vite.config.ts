import { fileURLToPath, URL } from 'node:url';

import { PrimeVueResolver } from '@primevue/auto-import-resolver';
import tailwindcss from '@tailwindcss/vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { defineConfig } from 'vite';
import vueDevTools from 'vite-plugin-vue-devtools';
import VueRouter from 'vue-router/vite';

export default defineConfig(({ mode }) => ({
    base: mode === 'production' ? './' : '/',
    plugins: [
        VueRouter({ dts: 'src/route-map.d.ts' }),
        vue(),
        tailwindcss(),
        ...(mode !== 'production' ? [vueDevTools()] : []),
        Components({
            resolvers: [PrimeVueResolver()],
        }),
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
    server: {
        port: 3099,
        proxy: {
            '/api': {
                target: 'http://localhost:8742',
                changeOrigin: true,
            },
            '/uploads': {
                target: 'http://localhost:8742',
                changeOrigin: true,
            },
        },
    },
    build: {
        target: 'es2023',
    },
}));
