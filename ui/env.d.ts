/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_BACKEND?: 'local' | 'http';
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
