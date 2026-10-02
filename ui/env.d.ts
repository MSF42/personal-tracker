/// <reference types="vite/client" />

interface ImportMetaEnv {
    /** API origin for packaged builds (Electron); dev uses the Vite proxy. */
    readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
