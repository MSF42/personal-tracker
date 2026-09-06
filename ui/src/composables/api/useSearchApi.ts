import type { SearchResponse, TodayResponse } from '@/types/Search';

import { useApi } from './backends/http/useApi';

// Bespoke http-backend API client for the unified search / today endpoints.
// These features don't (yet) have a local-backend implementation — local-mode
// users will see empty results until the in-browser SQLite backend catches up.
export function useSearchApi() {
    const api = useApi();

    const search = (q: string) => api.getData<SearchResponse>('search', { q });

    const getToday = () => api.getData<TodayResponse>('today');

    return { search, getToday };
}
