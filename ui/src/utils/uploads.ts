/**
 * Resolve an uploads-relative URL so it works in both dev mode (Vite proxy
 * handles `/uploads/*`) and Electron mode (page is loaded from `file://` so
 * relative paths need the full API origin prepended).
 */
export function resolveUploadsUrl(url: string): string {
    if (!url || !url.startsWith('/uploads/')) return url;
    const base = import.meta.env.VITE_API_BASE_URL;
    return base ? `${base}${url}` : url;
}
