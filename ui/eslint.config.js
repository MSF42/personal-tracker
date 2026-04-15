import js from '@eslint/js';
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting';
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript';
import simpleImportSort from 'eslint-plugin-simple-import-sort';
import pluginVue from 'eslint-plugin-vue';
import globals from 'globals';

export default defineConfigWithVueTs(
    {
        name: 'app/files-to-lint',
        files: ['**/*.{ts,mts,tsx,vue}'],
    },
    {
        name: 'app/files-to-ignore',
        ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**', 'ios/**'],
    },
    js.configs.recommended,
    pluginVue.configs['flat/essential'],
    vueTsConfigs.recommended,
    skipFormatting,
    {
        plugins: {
            'simple-import-sort': simpleImportSort,
        },
        rules: {
            'simple-import-sort/imports': 'error',
            'simple-import-sort/exports': 'error',
            'vue/multi-word-component-names': 'off',
            'vue/attributes-order': ['error', { alphabetical: true }],
            'vue/define-macros-order': [
                'error',
                { order: ['defineProps', 'defineEmits'] },
            ],
            quotes: ['error', 'single', { avoidEscape: true }],
            // Allow intentionally-ignored args/variables prefixed with `_`.
            // Several stubbed interface implementations (e.g. local-backend
            // stubs that mirror the http backend signature) need this.
            '@typescript-eslint/no-unused-vars': [
                'error',
                {
                    argsIgnorePattern: '^_',
                    varsIgnorePattern: '^_',
                    caughtErrorsIgnorePattern: '^_',
                },
            ],
        },
    },
    // Electron main/preload scripts are CommonJS and run in Node, not the
    // browser. Give them Node globals and allow `require()` style imports
    // so the shared ESLint config applies cleanly to the whole repo.
    {
        name: 'app/electron',
        files: ['electron/**/*.js'],
        languageOptions: {
            globals: {
                ...globals.node,
            },
            sourceType: 'commonjs',
        },
        rules: {
            '@typescript-eslint/no-require-imports': 'off',
        },
    },
);
